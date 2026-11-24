import os

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Literal
from uuid import UUID

from database import get_db
from models import User, UserAPIKey
from security import current_user

PROVIDERS = {
    "sdu": "https://xplt.sdu.edu.cn:4000/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
# Fixed provider endpoints prevent user-controlled URLs accessing the local network.
def cipher():
    secret = os.getenv("KEY_ENCRYPTION_SECRET", "")
    try:
        return Fernet(secret.encode())
    except (ValueError, TypeError):
        raise RuntimeError("请配置 KEY_ENCRYPTION_SECRET；使用 Fernet.generate_key() 生成并安全备份")

class KeyIn(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    provider: Literal["sdu", "deepseek", "openai", "dashscope"]
    api_key: str = Field(min_length=8, max_length=512)
    model: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9:._/-]+$")
    vision_model: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9:._/-]+$")

router = APIRouter(prefix="/api/keys", tags=["API Key"])

def locked_user(db, user):
    return db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))

def public_key(row, default_id):
    return {"id": row.id, "label": row.label, "provider": row.provider, "model": row.model,
        "base_url": PROVIDERS[row.provider],
        "vision_model": row.vision_model, "masked_key": "••••••••" + row.suffix,
        "is_default": row.id == default_id, "created_at": row.created_at}

def active_config(db, user):
    row = db.scalar(select(UserAPIKey).where(UserAPIKey.id == user.default_key_id, UserAPIKey.user_id == user.id))
    if not row:
        return None
    try:
        key = cipher().decrypt(row.encrypted_key.encode()).decode()
    except InvalidToken:
        raise HTTPException(503, "服务器无法解密已保存的 Key，请联系管理员恢复加密密钥")
    return {"api_key": key, "base_url": PROVIDERS[row.provider], "model": row.model,
        "vision_model": row.vision_model, "temperature": 0.7 if row.provider == "sdu" else 0.2}

@router.get("")
def list_keys(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserAPIKey).where(UserAPIKey.user_id == user.id).order_by(UserAPIKey.created_at)).all()
    return [public_key(row, user.default_key_id) for row in rows]

@router.post("", status_code=201)
def add_key(payload: KeyIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user = locked_user(db, user)
    if len(db.scalars(select(UserAPIKey.id).where(UserAPIKey.user_id == user.id)).all()) >= 10:
        raise HTTPException(422, "每个账号最多保存 10 个 Key")
    key = payload.api_key.strip()
    label = payload.label.strip()
    if len(key) < 8 or not label or any(ch.isspace() for ch in key):
        raise HTTPException(422, "Key 或名称格式不正确")
    row = UserAPIKey(user_id=user.id, label=label, provider=payload.provider, model=payload.model,
        vision_model=payload.vision_model, encrypted_key=cipher().encrypt(key.encode()).decode(), suffix=key[-4:])
    db.add(row)
    db.flush()
    if not user.default_key_id:
        user.default_key_id = row.id
    db.commit()
    return public_key(row, user.default_key_id)

@router.post("/{key_id}/default")
def set_default(key_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user = locked_user(db, user)
    row = db.scalar(select(UserAPIKey).where(UserAPIKey.id == str(key_id), UserAPIKey.user_id == user.id))
    if not row:
        raise HTTPException(404, "Key 不存在")
    user.default_key_id = row.id
    db.commit()
    return {"ok": True}

@router.delete("/{key_id}")
def delete_key(key_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user = locked_user(db, user)
    row = db.scalar(select(UserAPIKey).where(UserAPIKey.id == str(key_id), UserAPIKey.user_id == user.id))
    if not row:
        raise HTTPException(404, "Key 不存在")
    if user.default_key_id == row.id:
        user.default_key_id = db.scalar(select(UserAPIKey.id).where(UserAPIKey.user_id == user.id,
            UserAPIKey.id != row.id).order_by(UserAPIKey.created_at).limit(1))
    db.delete(row)
    db.commit()
    return {"ok": True}
