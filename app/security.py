import hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session as DBSession
from .models import User, Session, OTPChallenge

OTP_TTL=timedelta(minutes=5)
SESSION_TTL=timedelta(days=7)
MAX_OTP_ATTEMPTS=5

def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def create_otp(db: DBSession, identifier: str):
    code=f"{secrets.randbelow(1_000_000):06d}"
    challenge=OTPChallenge(identifier=identifier.lower().strip(), code_hash=hash_value(code),
                            expires_at=datetime.now(timezone.utc)+OTP_TTL)
    db.add(challenge); db.commit(); db.refresh(challenge)
    return challenge, code

def verify_otp(db: DBSession, challenge: OTPChallenge, code: str):
    now=datetime.now(timezone.utc)
    if challenge.consumed or challenge.expires_at < now or challenge.attempts >= MAX_OTP_ATTEMPTS:
        return False
    challenge.attempts += 1
    ok=hmac.compare_digest(challenge.code_hash, hash_value(code.strip()))
    if ok: challenge.consumed=True
    db.commit()
    return ok

def create_session(db: DBSession, user: User):
    raw=secrets.token_urlsafe(48)
    row=Session(user_id=user.id, token_hash=hash_value(raw), expires_at=datetime.now(timezone.utc)+SESSION_TTL)
    db.add(row); db.commit()
    return raw

def current_user(db: DBSession, authorization: str|None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Authentication required")
    token=authorization.split(" ",1)[1].strip()
    row=db.query(Session).filter_by(token_hash=hash_value(token)).first()
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(401,"Invalid or expired session")
    user=db.get(User,row.user_id)
    if not user: raise HTTPException(401,"User not found")
    return user
