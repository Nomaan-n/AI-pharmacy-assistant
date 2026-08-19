from typing import Any
from urllib.parse import quote_plus
import os
import re
import secrets
import hashlib
import hmac
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

RXNORM = "https://rxnav.nlm.nih.gov/REST"
OPENFDA = "https://api.fda.gov/drug/label.json"
router = APIRouter(prefix="/api")


def _get(url: str, params: dict[str, Any], timeout: float = 7.0) -> dict[str, Any]:
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return {}


def rxnorm_candidates(term: str) -> list[dict[str, Any]]:
    data = _get(f"{RXNORM}/approximateTerm.json", {"term": term, "maxEntries": 8})
    return [{"rxcui": x["rxcui"], "name": x.get("name"), "score": x.get("score")} for x in data.get("approximateGroup", {}).get("candidate", []) or [] if x.get("rxcui")]


def rxnorm_exact(term: str) -> list[dict[str, Any]]:
    data = _get(f"{RXNORM}/drugs.json", {"name": term})
    out=[]
    for group in data.get("drugGroup", {}).get("conceptGroup", []) or []:
        for c in group.get("conceptProperties", []) or []:
            if c.get("rxcui") and c.get("name"):
                out.append({"rxcui":c["rxcui"],"name":c["name"],"tty":c.get("tty")})
    return out[:25]


def rxnorm_products(term: str) -> list[dict[str, Any]]:
    data = _get(f"{RXNORM}/Prescribe/drugs.json", {"name": term, "expand": "psn,tty"})
    out=[]
    for group in data.get("drugGroup", {}).get("conceptGroup", []) or []:
        for c in group.get("conceptProperties", []) or []:
            if c.get("rxcui") and c.get("name"):
                out.append({"rxcui":c["rxcui"],"name":c["name"],"tty":c.get("tty")})
    return out[:25]


def fda_label(term: str) -> dict[str, Any]:
    escaped=term.replace('"','\\"')
    data=_get(OPENFDA,{"search":f'(openfda.generic_name:"{escaped}" OR openfda.brand_name:"{escaped}")',"limit":3})
    results=data.get("results") or []
    if not results:
        data=_get(OPENFDA,{"search":f'openfda.substance_name:"{escaped}"',"limit":3}); results=data.get("results") or []
    if not results:return {}
    r=results[0]; of=r.get("openfda",{})
    return {"brand_names":(of.get("brand_name") or [])[:8],"generic_names":(of.get("generic_name") or [])[:8],"manufacturer":(of.get("manufacturer_name") or [])[:8],"route":(of.get("route") or [])[:8],"dosage_form":(of.get("dosage_form") or [])[:8],"indications":(r.get("indications_and_usage") or [])[:2],"warnings":(r.get("warnings") or [])[:2],"contraindications":(r.get("contraindications") or [])[:2],"adverse_reactions":(r.get("adverse_reactions") or [])[:2],"drug_interactions":(r.get("drug_interactions") or [])[:2],"source":"openFDA drug labeling"}


def _db_path() -> Path:
    path=Path(os.getenv("DATABASE_PATH","data/pharmacy.db")); path.parent.mkdir(parents=True,exist_ok=True); return path


def _db() -> sqlite3.Connection:
    con=sqlite3.connect(_db_path()); con.row_factory=sqlite3.Row; con.execute("PRAGMA foreign_keys=ON"); return con


def init_db() -> None:
    with _db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cabinet (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, rxcui TEXT, dose TEXT, frequency TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, medicine_id INTEGER, medicine_name TEXT NOT NULL, remind_at TEXT NOT NULL, instructions TEXT, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS otp_challenges (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, used INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        """)


def _now(): return datetime.now(timezone.utc)
def _iso(dt): return dt.astimezone(timezone.utc).isoformat()


def _user(email: str) -> int:
    email=email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): raise HTTPException(400,"A valid email address is required.")
    with _db() as con:
        con.execute("INSERT OR IGNORE INTO users(email,created_at) VALUES(?,?)",(email,_iso(_now())))
        return int(con.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone()[0])


def _session_secret():
    secret=os.getenv("SESSION_SECRET") or os.getenv("OTP_SECRET")
    if not secret: raise HTTPException(503,"Authentication is not configured. Set SESSION_SECRET or OTP_SECRET.")
    return secret


def _session_token(email: str, issued: int | None=None) -> str:
    issued=issued or int(_now().timestamp()); payload=f"{email.lower()}:{issued}"; sig=hmac.new(_session_secret().encode(),payload.encode(),hashlib.sha256).hexdigest(); return f"{payload}:{sig}"


def _require_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401,"Bearer session token required.")
    token=authorization[7:]; parts=token.split(":")
    if len(parts)!=3: raise HTTPException(401,"Invalid session token.")
    email,issued,sig=parts
    try: issued_i=int(issued)
    except ValueError: raise HTTPException(401,"Invalid session token.")
    if _now().timestamp()-issued_i>86400: raise HTTPException(401,"Session expired.")
    if not hmac.compare_digest(sig,hmac.new(_session_secret().encode(),f"{email}:{issued}".encode(),hashlib.sha256).hexdigest()): raise HTTPException(401,"Invalid session token.")
    return email.lower()


def _otp_hash(email,code):
    secret=os.getenv("OTP_SECRET")
    if not secret: raise HTTPException(503,"OTP delivery is not configured. Set OTP_SECRET before enabling authentication.")
    return hmac.new(secret.encode(),f"{email}:{code}".encode(),hashlib.sha256).hexdigest()


def _extract_text(raw: bytes):
    try:
        from PIL import Image
        import pytesseract, io
        text=pytesseract.image_to_string(Image.open(io.BytesIO(raw))).strip()
        return text,"tesseract"
    except Exception as exc: return "",f"ocr_unavailable:{type(exc).__name__}"


def parse_prescription(text: str):
    lines=[x.strip() for x in text.splitlines() if x.strip()]; candidates=[]
    patterns=[re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9 .-]{2,60})\s+(?P<dose>\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|mL|%))\s*(?P<frequency>once|twice|thrice|daily|bid|tid|qid|od|bd|tds|qds)?",re.I),re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9 .-]{2,60})\s+(?P<frequency>once|twice|thrice|daily|bid|tid|qid|od|bd|tds|qds)",re.I)]
    for line in lines:
        for pat in patterns:
            m=pat.search(line)
            if m:
                candidates.append({"raw":line,"name_candidate":m.group("name").strip(),"dose":(m.groupdict().get("dose") or "").strip(),"frequency":(m.groupdict().get("frequency") or "").strip()}); break
    return {"raw_text":text,"lines":lines,"medication_candidates":candidates,"verified":False,"notice":"OCR and parsing produce candidates only. Handwritten or uncertain prescription text must be manually verified against the original prescription."}


def register(app):
    init_db()
    @app.post("/api/ocr/image")
    async def ocr_image(file: UploadFile=File(...)):
        if not (file.content_type or "").startswith("image/"): raise HTTPException(415,"Upload an image file.")
        raw=await file.read()
        if len(raw)>10*1024*1024: raise HTTPException(413,"Image is too large. Maximum is 10 MB.")
        text,engine=_extract_text(raw)
        return {"filename":file.filename,"ocr_status":"text_extracted" if text else "unavailable_or_empty","engine":engine,"text":text,"notice":"OCR output is unverified and must not be treated as a confirmed medicine or prescription."}

    @app.post("/api/ocr/prescription")
    async def ocr_prescription(file: UploadFile=File(...)):
        if not (file.content_type or "").startswith("image/"): raise HTTPException(415,"Upload a prescription image.")
        raw=await file.read(); text,engine=_extract_text(raw)
        parsed=parse_prescription(text) if text else {"raw_text":"","lines":[],"medication_candidates":[],"verified":False,"notice":"No OCR text was obtained."}
        return {"filename":file.filename,"engine":engine,**parsed}

    @app.get("/api/identify")
    def identify(text:str=Query(min_length=2,max_length=300)):
        return {"query":text,"candidates":rxnorm_candidates(text),"products":rxnorm_products(text),"confidence_note":"Approximate matches are candidates for manual verification, especially for OCR or handwritten prescriptions.","source":"NIH/NLM RxNorm"}

    @app.get("/api/verify")
    def verify(text:str=Query(min_length=2,max_length=200)):
        exact=rxnorm_exact(text); approx=rxnorm_candidates(text); best=exact[0] if exact else (approx[0] if approx else None); label=fda_label(text) if best else {}
        return {"query":text,"status":"verified_concept" if exact else ("candidate" if best else "not_found"),"verified":bool(exact),"match":best,"alternatives":approx[1:5],"authoritative_sources":["NIH/NLM RxNorm"]+(["U.S. FDA openFDA"] if label else []),"label":label,"notice":"Verified means a medication concept matched an authoritative database. It does not verify a photographed package, prescription, dose, authenticity, or patient-specific suitability."}

    @app.get("/api/drug-profile/{medicine_name}")
    def drug_profile(medicine_name:str):
        c=rxnorm_candidates(medicine_name); f=fda_label(medicine_name); return {"query":medicine_name,"match":c[0] if c else None,"alternatives":c[1:5],"label":f,"sources":["NIH/NLM RxNorm","U.S. FDA openFDA"] if f else ["NIH/NLM RxNorm"],"last_checked":_iso(_now())}

    @app.get("/api/safety-check")
    def safety_check(medicines:str=Query(min_length=2,max_length=500)):
        names=[x.strip() for x in medicines.split(",") if x.strip()][:12]; profiles=[{"query":n,"best_match":(rxnorm_candidates(n) or [None])[0]} for n in names]; rxcuis=[p["best_match"]["rxcui"] for p in profiles if p["best_match"] and p["best_match"].get("rxcui")]; interaction=_get(f"{RXNORM}/interaction/list.json",{"rxcuis":"+".join(rxcuis)}) if len(rxcuis)>=2 else {}; pairs=[]
        for group in interaction.get("fullInteractionTypeGroup",[]) or []:
            for typ in group.get("fullInteractionType",[]) or []:
                for pair in typ.get("fullInteractionPair",[]) or []: pairs.append({"description":pair.get("description"),"severity":pair.get("severity"),"source":typ.get("comment") or group.get("sourceName")})
        return {"medicines":profiles,"interaction_status":"checked" if len(rxcuis)>=2 and interaction else "not_checked_or_unavailable","interactions":pairs[:50],"source":"NIH/NLM RxNorm","notice":"This is database interaction information, not individualized medical advice."}

    @app.post("/api/cabinet")
    def cabinet_add(name:str=Form(...), email:str|None=Form(None), authorization:str|None=Header(None), dose:str=Form(""), frequency:str=Form(""), notes:str=Form("")):
        email=_require_auth(authorization); uid=_user(email); c=rxnorm_candidates(name); rxcui=c[0].get("rxcui") if c else None
        with _db() as con:
            cur=con.execute("INSERT INTO cabinet(user_id,name,rxcui,dose,frequency,notes,created_at) VALUES(?,?,?,?,?,?,?)",(uid,name.strip(),rxcui,dose,frequency,notes,_iso(_now())))
            return {"id":cur.lastrowid,"name":name.strip(),"rxcui":rxcui,"verified_concept":bool(rxcui),"notice":"A matched RxCUI is a concept match, not confirmation of the physical medicine or prescription."}

    @app.get("/api/cabinet")
    def cabinet_list(authorization:str|None=Header(None)):
        email=_require_auth(authorization); uid=_user(email)
        with _db() as con: rows=[dict(x) for x in con.execute("SELECT * FROM cabinet WHERE user_id=? ORDER BY created_at DESC",(uid,)).fetchall()]
        return {"medicines":rows,"count":len(rows)}

    @app.delete("/api/cabinet/{medicine_id}")
    def cabinet_delete(medicine_id:int,authorization:str|None=Header(None)):
        email=_require_auth(authorization); uid=_user(email)
        with _db() as con: cur=con.execute("DELETE FROM cabinet WHERE id=? AND user_id=?",(medicine_id,uid))
        return {"deleted":cur.rowcount>0}

    @app.get("/api/cabinet/duplicates")
    def cabinet_duplicates(authorization:str|None=Header(None)):
        email=_require_auth(authorization); uid=_user(email)
        with _db() as con: rows=[dict(x) for x in con.execute("SELECT * FROM cabinet WHERE user_id=? AND rxcui IS NOT NULL ORDER BY rxcui,id",(uid,)).fetchall()]
        groups={}
        for row in rows: groups.setdefault(row["rxcui"],[]).append(row)
        return {"duplicate_groups":[v for v in groups.values() if len(v)>1],"count":sum(1 for v in groups.values() if len(v)>1),"notice":"Duplicate detection is based on RxCUI concept matches and is not a clinical duplication-of-therapy judgment."}

    @app.post("/api/reminders")
    def reminder_add(medicine_name:str=Form(...),remind_at:str=Form(...),instructions:str=Form(""),medicine_id:int|None=Form(None),authorization:str|None=Header(None)):
        email=_require_auth(authorization); uid=_user(email)
        try: datetime.fromisoformat(remind_at.replace("Z","+00:00"))
        except ValueError: raise HTTPException(400,"remind_at must be ISO-8601 datetime.")
        with _db() as con:
            cur=con.execute("INSERT INTO reminders(user_id,medicine_id,medicine_name,remind_at,instructions,created_at) VALUES(?,?,?,?,?,?)",(uid,medicine_id,medicine_name.strip(),remind_at,instructions,_iso(_now())))
        return {"id":cur.lastrowid,"scheduled":True,"notice":"Reminder stored. Push/email/SMS delivery requires a configured scheduler and notification provider."}

    @app.get("/api/reminders")
    def reminders(authorization:str|None=Header(None)):
        email=_require_auth(authorization); uid=_user(email)
        with _db() as con: rows=[dict(x) for x in con.execute("SELECT * FROM reminders WHERE user_id=? ORDER BY remind_at",(uid,)).fetchall()]
        return {"reminders":rows,"count":len(rows)}

    @app.post("/api/auth/otp/request")
    def otp_request(email:str=Form(...)):
        email=email.strip().lower(); _user(email); code=f"{secrets.randbelow(1_000_000):06d}"; digest=_otp_hash(email,code)
        with _db() as con:
            con.execute("UPDATE otp_challenges SET used=1 WHERE email=? AND used=0",(email,)); con.execute("INSERT INTO otp_challenges(email,code_hash,expires_at,created_at) VALUES(?,?,?,?)",(email,digest,_iso(_now()+timedelta(minutes=5)),_iso(_now())))
        mode=os.getenv("OTP_DELIVERY_MODE")
        if mode=="console": print(f"OTP for {email}: {code}")
        elif not os.getenv("OTP_DELIVERY_URL"): raise HTTPException(503,"OTP challenge created but no delivery provider is configured. Set OTP_DELIVERY_MODE=console for development or OTP_DELIVERY_URL for production delivery.")
        return {"sent":bool(os.getenv("OTP_DELIVERY_URL") or mode=="console"),"expires_in_seconds":300,"delivery":"console" if mode=="console" else "external_provider"}

    @app.post("/api/auth/otp/verify")
    def otp_verify(email:str=Form(...),code:str=Form(...)):
        email=email.strip().lower()
        with _db() as con:
            row=con.execute("SELECT * FROM otp_challenges WHERE email=? AND used=0 ORDER BY id DESC LIMIT 1",(email,)).fetchone()
            if not row: raise HTTPException(401,"Invalid or expired OTP.")
            if row["attempts"]>=5: raise HTTPException(429,"Too many OTP attempts.")
            con.execute("UPDATE otp_challenges SET attempts=attempts+1 WHERE id=?",(row["id"],))
            if _now()>datetime.fromisoformat(row["expires_at"]): raise HTTPException(401,"OTP expired.")
            if not hmac.compare_digest(row["code_hash"],_otp_hash(email,code.strip())): raise HTTPException(401,"Invalid OTP.")
            con.execute("UPDATE otp_challenges SET used=1 WHERE id=?",(row["id"],))
        return {"authenticated":True,"email":email,"session_token":_session_token(email),"expires_in_seconds":86400}

    @app.post("/api/chat")
    def chat(message:str=Form(...)):
        text=message.strip()
        if not text: raise HTTPException(400,"Message is required.")
        c=rxnorm_candidates(text)
        if c:
            name=c[0].get("name") or text; label=fda_label(name)
            return {"mode":"grounded_retrieval","answer":f"I found a medication concept matching '{name}'. I can show verified database information, but I won't infer a dose or patient-specific treatment from this match.","evidence":{"rxnorm":c[:3],"fda_label":label},"safety_notice":"Do not treat OCR or database matches as confirmation of a prescription or individualized medical advice."}
        return {"mode":"grounded_retrieval","answer":"I couldn't establish an authoritative medication match from that message. Please provide the exact medicine name or a clear package label. I won't invent medication facts.","evidence":[],"safety_notice":"No authoritative match means no medication conclusion is made."}
