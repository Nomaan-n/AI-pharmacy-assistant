import os
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Medicine, Reminder, AuditEvent, OTPChallenge
from .security import create_otp, verify_otp, create_session, current_user, deliver_otp
from .services_medication import rxnorm_search, rxnorm_properties, interactions, fda_label, india_links
from .services_ocr import ocr_image, parse_prescription
from .services_ai import grounded_chat
from .services_notifications import send_welcome_email, send_review_request
router=APIRouter(prefix="/api")
class Identifier(BaseModel): identifier:str=Field(min_length=3,max_length=320)
class OTPVerify(BaseModel): identifier:str; code:str=Field(min_length=6,max_length=6)
class MedicineIn(BaseModel): name:str=Field(min_length=1,max_length=255); rxcui:str|None=None; ingredient:str|None=None; strength:str|None=None; notes:str|None=None
class ReminderIn(BaseModel): title:str=Field(min_length=1,max_length=255); schedule:str=Field(min_length=1,max_length=255); timezone_name:str="UTC"; medicine_id:int|None=None
class ChatIn(BaseModel): message:str=Field(min_length=1,max_length=4000); medication:str|None=None
class ReviewIn(BaseModel): request:str=Field(min_length=10,max_length=4000); medicine_names:list[str]=[]
def auth_user(authorization,db): return current_user(db,authorization)
@router.post("/auth/request-otp")
def request_otp(body:Identifier,db:Session=Depends(get_db)):
    ident=body.identifier.strip().lower(); challenge,code=create_otp(db,ident); delivery=os.getenv("OTP_DELIVERY","disabled")
    if delivery=="log": return {"status":"issued","challenge_id":challenge.id,"development_code":code}
    if delivery=="smtp":
        try: deliver_otp(ident,code)
        except Exception as exc: raise HTTPException(503,f"OTP delivery failed: {exc}")
        return {"status":"issued","challenge_id":challenge.id,"delivery":"smtp"}
    return {"status":"issued","challenge_id":challenge.id,"delivery":"not_configured","message":"Email delivery is not configured yet."}
@router.post("/auth/verify-otp")
def verify(body:OTPVerify,db:Session=Depends(get_db)):
    ident=body.identifier.strip().lower(); challenge=db.query(OTPChallenge).filter_by(identifier=ident,consumed=False).order_by(OTPChallenge.created_at.desc()).first()
    if not challenge or not verify_otp(db,challenge,body.code): raise HTTPException(401,"Invalid or expired OTP")
    user=db.query(User).filter_by(identifier=ident).first(); created=False
    if not user: user=User(identifier=ident); db.add(user); db.commit(); db.refresh(user); created=True
    if created: send_welcome_email(ident)
    return {"access_token":create_session(db,user),"token_type":"bearer","expires_in":604800}
@router.get("/me")
def me(authorization:str|None=Header(default=None),db:Session=Depends(get_db)): u=auth_user(authorization,db); return {"id":u.id,"identifier":u.identifier}
@router.post("/review")
def review(body:ReviewIn,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db); send_review_request(u.identifier,body.request,body.medicine_names); db.add(AuditEvent(user_id=u.id,event="human_review.request")); db.commit()
    return {"status":"received","price_inr":200,"service":"Human medication-information review","notice":"A professional review can help explain medication information and prepare questions for a doctor or pharmacist. It does not diagnose, prescribe, change treatment, or guarantee a medicine or doctor choice.","payment":"not_configured"}
@router.post("/cabinet")
def add_medicine(body:MedicineIn,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db); matches=rxnorm_search(body.name); rxcui=body.rxcui or (matches[0].get("rxcui") if matches else None)
    duplicate=db.query(Medicine).filter_by(user_id=u.id,active=True).filter((Medicine.rxcui==rxcui) if rxcui else (Medicine.name.ilike(body.name))).first()
    if duplicate: raise HTTPException(409,"Duplicate medication concept or name already exists in your cabinet.")
    row=Medicine(user_id=u.id,name=body.name,rxcui=rxcui,ingredient=body.ingredient,strength=body.strength,notes=body.notes); db.add(row); db.add(AuditEvent(user_id=u.id,event="cabinet.add")); db.commit(); db.refresh(row)
    return {"id":row.id,"name":row.name,"rxcui":row.rxcui,"duplicate_checked":True}
@router.get("/cabinet")
def cabinet(authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db); return {"medicines":[{"id":m.id,"name":m.name,"rxcui":m.rxcui,"ingredient":m.ingredient,"strength":m.strength,"notes":m.notes} for m in u.cabinet if m.active]}
@router.delete("/cabinet/{medicine_id}")
def delete_medicine(medicine_id:int,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db); m=db.query(Medicine).filter_by(id=medicine_id,user_id=u.id).first()
    if not m: raise HTTPException(404,"Medicine not found")
    m.active=False; db.add(AuditEvent(user_id=u.id,event="cabinet.delete")); db.commit(); return {"deleted":True}
@router.post("/reminders")
def add_reminder(body:ReminderIn,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db)
    if body.medicine_id and not db.query(Medicine).filter_by(id=body.medicine_id,user_id=u.id,active=True).first(): raise HTTPException(404,"Medicine not found")
    r=Reminder(user_id=u.id,medicine_id=body.medicine_id,title=body.title,schedule=body.schedule,timezone_name=body.timezone_name); db.add(r); db.add(AuditEvent(user_id=u.id,event="reminder.create")); db.commit(); db.refresh(r); return {"id":r.id,"title":r.title,"schedule":r.schedule,"enabled":r.enabled,"delivery":"worker_ready_provider_required"}
@router.get("/reminders")
def reminders(authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    u=auth_user(authorization,db); return {"reminders":[{"id":r.id,"title":r.title,"schedule":r.schedule,"timezone":r.timezone_name,"enabled":r.enabled} for r in u.reminders]}
@router.post("/ocr/image")
async def image_ocr(file:UploadFile=File(...)):
    try:return ocr_image(await file.read())
    except Exception as e:raise HTTPException(400,str(e))
@router.post("/ocr/prescription")
async def prescription_ocr(file:UploadFile=File(...)):
    try:return parse_prescription(ocr_image(await file.read())["text"])
    except Exception as e:raise HTTPException(400,str(e))
@router.post("/identify/photo")
async def identify_photo(file:UploadFile=File(...)):
    try: ocr=ocr_image(await file.read())
    except Exception as e:raise HTTPException(400,str(e))
    candidates=[]
    for med in parse_prescription(ocr.get("text","")).get("medications",[]):candidates.append({**med,"rxnorm_candidates":rxnorm_search(med["candidate_name"])[:5],"verified":False})
    return {"status":"candidate_identification","ocr":ocr,"candidates":candidates,"notice":"Photo identification is candidate generation only. Confirm the original label/package before treating a medicine as identified."}
@router.post("/verify")
def verify_medication(name:str):
    matches=rxnorm_search(name)
    if not matches:return {"status":"not_verified","query":name,"candidates":[]}
    top=matches[0]; props=rxnorm_properties(top["rxcui"]) if top.get("rxcui") else {}; label=fda_label(top["name"])
    return {"status":"candidate_verified","candidate":top,"properties":props,"label_evidence":label,"verification":{"rxnorm_concept":bool(props),"physical_product":False,"prescription":False,"patient_specific_suitability":False}}
@router.post("/interactions")
def check_interactions(names:list[str]):
    recognized=[]
    for name in names[:20]:
        ms=rxnorm_search(name)
        if ms:recognized.append({"input":name,**ms[0]})
    return {"recognized":recognized,"result":interactions([x.get("rxcui") for x in recognized])}
@router.get("/india/medicines/{name}")
def india_medicine(name:str):return {"query":name,"global_concepts":rxnorm_search(name)[:10],"india_resources":india_links(name),"notice":"India availability, brand identity, prescription status and pricing require verification against the local product/package and authorized pharmacy/regulatory sources."}
@router.post("/chat")
def chat(body:ChatIn):return grounded_chat(body.message,body.medication)