import hashlib, hmac, secrets, os, smtplib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session as DBSession
from fastapi import HTTPException
from .models import User, Session, OTPChallenge
OTP_TTL=timedelta(minutes=5)
SESSION_TTL=timedelta(days=7)
MAX_OTP_ATTEMPTS=5
def hash_value(value:str)->str: return hashlib.sha256(value.encode()).hexdigest()
def create_otp(db:DBSession,identifier:str):
    code=f"{secrets.randbelow(1_000_000):06d}"; challenge=OTPChallenge(identifier=identifier.lower().strip(),code_hash=hash_value(code),expires_at=datetime.now(timezone.utc)+OTP_TTL); db.add(challenge); db.commit(); db.refresh(challenge); return challenge,code
def verify_otp(db:DBSession,challenge:OTPChallenge,code:str):
    if challenge.consumed or challenge.expires_at < datetime.now(timezone.utc) or challenge.attempts >= MAX_OTP_ATTEMPTS: return False
    challenge.attempts+=1; ok=hmac.compare_digest(challenge.code_hash,hash_value(code.strip())); challenge.consumed=ok; db.commit(); return ok
def create_session(db:DBSession,user:User):
    raw=secrets.token_urlsafe(48); db.add(Session(user_id=user.id,token_hash=hash_value(raw),expires_at=datetime.now(timezone.utc)+SESSION_TTL)); db.commit(); return raw
def current_user(db:DBSession,authorization:str|None):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401,"Authentication required")
    row=db.query(Session).filter_by(token_hash=hash_value(authorization.split(" ",1)[1].strip())).first()
    if not row or row.expires_at < datetime.now(timezone.utc): raise HTTPException(401,"Invalid or expired session")
    user=db.get(User,row.user_id)
    if not user: raise HTTPException(401,"User not found")
    return user
def deliver_otp(identifier:str,code:str):
    if "@" not in identifier: raise RuntimeError("SMTP OTP delivery requires an email identifier")
    host=os.getenv("SMTP_HOST"); user=os.getenv("SMTP_USER"); password=os.getenv("SMTP_PASSWORD"); sender=os.getenv("SMTP_FROM") or user
    if not host or not sender: raise RuntimeError("SMTP_HOST and SMTP_FROM/SMTP_USER are required")
    msg=f"From: {sender}\\nTo: {identifier}\\nSubject: AI Pharmacy Assistant verification code\\n\\nYour verification code is {code}. It expires in 5 minutes."
    with smtplib.SMTP(host,int(os.getenv("SMTP_PORT","587")),timeout=10) as smtp:
        if os.getenv("SMTP_TLS","true").lower()=="true": smtp.starttls()
        if user and password: smtp.login(user,password)
        smtp.sendmail(sender,[identifier],msg)
