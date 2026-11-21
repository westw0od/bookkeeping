import hashlib
import hmac
import re
import secrets
import time
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from database import get_db
from models import AuthAttempt, LoginSession, User, now

bearer = HTTPBearer(auto_error=False)
ITERATIONS = 600_000

def normalize_username(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[\w.@+-]{3,40}", value):
        raise HTTPException(422, "用户名需为 3–40 个字母、数字、汉字或 ._@+-")
    return value

def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

# Use equivalent work for unknown usernames to avoid a fast username-existence oracle.
DUMMY_HASH = password_hash(secrets.token_urlsafe(24))

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def new_session(db: Session, user: User):
    token = secrets.token_urlsafe(32)
    expiry = now() + timedelta(days=7)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=expiry))
    db.execute(delete(LoginSession).where(LoginSession.expires_at < now()))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expiry,
            "user": {"id": user.id, "username": user.username}}

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "请先登录", headers={"WWW-Authenticate": "Bearer"})
    session = db.get(LoginSession, token_hash(credentials.credentials))
    if not session or session.expires_at <= now():
        raise HTTPException(401, "登录已过期，请重新登录", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "请重新登录")
    return user

def throttle_auth(db: Session, request: Request, username: str):
    bucket = int(time.time() // 900)
    address = request.client.host if request.client else "unknown"
    # Do not trust a client-supplied X-Forwarded-For header.
    for scope, limit in [(f"ip:{address}", 80), (f"user:{username}", 20)]:
        key = hashlib.sha256(scope.encode()).hexdigest()
        stmt = insert(AuthAttempt).values(key=key, bucket=bucket, count=1)
        stmt = stmt.on_duplicate_key_update(count=AuthAttempt.count + 1)
        db.execute(stmt)
        count = db.scalar(select(AuthAttempt.count).where(AuthAttempt.key == key, AuthAttempt.bucket == bucket).with_for_update())
        db.commit()
        if count > limit:
            raise HTTPException(429, "尝试过于频繁，请 15 分钟后再试")
    db.execute(delete(AuthAttempt).where(AuthAttempt.bucket < bucket - 1))
    db.commit()
