import asyncio, logging
from datetime import datetime, timezone
from .db import SessionLocal
from .models import Reminder
log=logging.getLogger("pharmacy.reminders")

async def reminder_worker():
    while True:
        db=SessionLocal()
        try:
            now=datetime.now(timezone.utc)
            due=db.query(Reminder).filter_by(enabled=True).filter(Reminder.next_run_at != None).filter(Reminder.next_run_at <= now).all()
            for r in due:
                log.info("reminder_due id=%s user_id=%s title=%s schedule=%s",r.id,r.user_id,r.title,r.schedule)
                r.next_run_at=None
            db.commit()
        except Exception:
            log.exception("reminder_worker_error")
        finally:
            db.close()
        await asyncio.sleep(30)
