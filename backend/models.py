"""MySQL schema. Money is stored as integer cents, never floating point."""
from datetime import datetime, timezone, date
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True
    def process_bind_param(self, value, dialect):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value else None
    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value else None

DEFAULT_CATEGORIES = {
    "expense": ["饮食", "购物", "娱乐", "出行", "旅游", "教育", "医疗", "人情", "水电", "其他"],
    "income": ["工资", "补贴", "兼职", "人情", "幸运", "奖金", "投资", "其他"],
}

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    default_key_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id"),
        CheckConstraint("amount_cents > 0"),
        CheckConstraint("type IN ('income', 'expense')"),
        Index("ix_ledger_entries_user_revoked", "user_id", "revoked_at"),
        UniqueConstraint("user_id", "import_source", "external_id", name="uq_ledger_import_record"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str] = mapped_column(String(36))
    type: Mapped[str] = mapped_column(String(7))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    added_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    counterparty: Mapped[str] = mapped_column(String(80), default="")
    event: Mapped[str] = mapped_column(String(120), default="")
    import_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

class PersonalCategory(Base):
    __tablename__ = "personal_categories"
    __table_args__ = (UniqueConstraint("user_id", "type", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(7))
    name: Mapped[str] = mapped_column(String(30))

class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(80))
    mime: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

class UserAPIKey(Base):
    __tablename__ = "user_api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    vision_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    encrypted_key: Mapped[str] = mapped_column(Text)
    suffix: Mapped[str] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now)

class AIUsage(Base):
    __tablename__ = "ai_usage"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

class AuthAttempt(Base):
    __tablename__ = "auth_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    bucket: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
