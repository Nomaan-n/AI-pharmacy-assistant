import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import User, Medicine, Reminder, Session as AuthSession, AuditEvent, OTPChallenge

def anonymized_id(value): return hashlib.sha256(value.encode()).hexdigest()[:16]

def delete_user_data(db: Session, user):
    db.query(Medicine).filter_by(user_id=user.id).delete()
    db.query(Reminder).filter_by(user_id=user.id).delete()
    db.query(AuthSession).filter_by(user_id=user.id).delete()
    db.query(AuditEvent).filter_by(user_id=user.id).delete()
    db.delete(user); db.commit()

def export_user_data(db: Session, user):
    return {"user":{"id":user.id,"identifier":user.identifier,"created_at":user.created_at.isoformat()},"medicines":[{"id":m.id,"name":m.name,"rxcui":m.rxcui,"ingredient":m.ingredient,"strength":m.strength,"notes":m.notes} for m in user.cabinet],"reminders":[{"id":r.id,"title":r.title,"schedule":r.schedule,"timezone":r.timezone_name,"enabled":r.enabled} for r in user.reminders],"exported_at":datetime.now(timezone.utc).isoformat()}
