"""Versioned, deterministic, per-user imports. Preview never writes records."""
import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import LedgerEntry, User, now
from security import current_user

router = APIRouter(prefix="/api/ledger/import", tags=["账单导入"])

class ImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=100)
    date: date
    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=30)
    note: str = Field(default="", max_length=2000)
    counterparty: str = Field(default="", max_length=80)
    event: str = Field(default="", max_length=120)

    @field_validator("external_id", "category", "counterparty", "event")
    @classmethod
    def clean_text(cls, value):
        return value.strip()

    @model_validator(mode="after")
    def required_nonempty(self):
        if not self.external_id or not self.category:
            raise ValueError("编号和分类不能为空")
        return self

class ImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["bookkeeping.v1"]
    source: str = Field(min_length=1, max_length=80)
    records: list[ImportRecord] = Field(min_length=1, max_length=1000)

    @field_validator("source")
    @classmethod
    def clean_source(cls, value):
        if not value.strip():
            raise ValueError("来源不能为空")
        return value.strip()

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [row.external_id for row in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("同一文件中的 external_id 不能重复")
        return self

def identity(source, external_id):
    return str(uuid5(NAMESPACE_URL, json.dumps(["bookkeeping.v1", source, external_id], ensure_ascii=False, separators=(",", ":"))))

def occurred(record):
    # A date-only historical record has no known clock time; use noon in Shanghai.
    return datetime.combine(record.date, time(12), tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(timezone.utc)

def matches(row, record):
    return (row.type == record.type and row.amount_cents == int(record.amount * 100)
        and row.category == record.category and row.note == record.note
        and row.counterparty == record.counterparty and row.event == record.event
        and row.occurred_at == occurred(record))

TEMPLATE = {
    "format": "bookkeeping.v1", "source": "历史账本-2026",
    "records": [
        {"external_id": "expense-001", "date": "2026-11-01", "type": "expense", "amount": "25.00", "category": "饮食", "note": "午餐", "counterparty": "", "event": ""},
        {"external_id": "gift-001", "date": "2026-10-01", "type": "expense", "amount": "500.00", "category": "人情", "note": "随礼", "counterparty": "张三", "event": "婚礼"},
        {"external_id": "gift-002", "date": "2026-11-08", "type": "income", "amount": "300.00", "category": "人情", "note": "收到礼金", "counterparty": "张三", "event": "生日"},
    ],
}

@router.get("/template")
def template(user: User = Depends(current_user)):
    return TEMPLATE

@router.post("")
def import_ledger(document: ImportDocument, dry_run: bool = Query(True),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not dry_run:
        # Serialize imports for one account so simultaneous retries count correctly.
        db.scalar(select(User).where(User.id == user.id).with_for_update())
    query = select(LedgerEntry).where(LedgerEntry.user_id == user.id,
        LedgerEntry.import_source == document.source,
        LedgerEntry.external_id.in_([r.external_id for r in document.records]))
    if not dry_run:
        query = query.with_for_update()
    existing = {row.external_id: row for row in db.scalars(query)}
    fresh, duplicate, removed = [], 0, 0
    for record in document.records:
        row = existing.get(record.external_id)
        if row is None:
            fresh.append(record)
        elif not matches(row, record):
            raise HTTPException(409, f"编号 {record.external_id} 已存在但内容不同，请检查来源和编号；本次未导入")
        elif row.revoked_at is not None:
            removed += 1
        else:
            duplicate += 1
    income = sum((r.amount for r in fresh if r.type == "income"), Decimal(0))
    expense = sum((r.amount for r in fresh if r.type == "expense"), Decimal(0))
    if not dry_run:
        for record in fresh:
            db.add(LedgerEntry(id=str(uuid4()), user_id=user.id, client_id=identity(document.source, record.external_id),
                type=record.type, amount_cents=int(record.amount * 100), category=record.category, note=record.note,
                counterparty=record.counterparty, event=record.event, import_source=document.source,
                external_id=record.external_id, occurred_at=occurred(record), added_at=now()))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "账单已被其他请求导入，请重新预览后再试；本次未部分导入")
    return {"format": document.format, "source": document.source, "dry_run": dry_run,
        "total_count": len(document.records), "new_count": len(fresh), "duplicate_count": duplicate,
        "removed_count": removed, "imported_count": 0 if dry_run else len(fresh),
        "income": float(income), "expense": float(expense),
        "preview": [r.model_dump(mode="json") for r in fresh[:20]]}
