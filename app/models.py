from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    identifier: Mapped[str]=mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    cabinet = relationship("Medicine", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")

class OTPChallenge(Base):
    __tablename__="otp_challenges"
    id: Mapped[int]=mapped_column(primary_key=True)
    identifier: Mapped[str]=mapped_column(String(320), index=True)
    code_hash: Mapped[str]=mapped_column(String(128))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    attempts: Mapped[int]=mapped_column(Integer, default=0)
    consumed: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Session(Base):
    __tablename__="sessions"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str]=mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)

class Medicine(Base):
    __tablename__="medicines"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(255))
    rxcui: Mapped[str|None]=mapped_column(String(32), nullable=True, index=True)
    ingredient: Mapped[str|None]=mapped_column(String(255), nullable=True)
    strength: Mapped[str|None]=mapped_column(String(100), nullable=True)
    notes: Mapped[str|None]=mapped_column(Text, nullable=True)
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    user = relationship("User", back_populates="cabinet")

class Reminder(Base):
    __tablename__="reminders"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    medicine_id: Mapped[int|None]=mapped_column(ForeignKey("medicines.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str]=mapped_column(String(255))
    schedule: Mapped[str]=mapped_column(String(255))
    timezone_name: Mapped[str]=mapped_column(String(64), default="UTC")
    next_run_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
    user = relationship("User", back_populates="reminders")
    medicine = relationship("Medicine")

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event: Mapped[str]=mapped_column(String(100), index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=now)
