from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
import json

from sqlalchemy import select
from database import SessionLocal
from key_management import cipher
from models import LedgerEntry, LoginSession, User, UserAPIKey, now
import main

def add_key(client, owner, secret="sk-test-do-not-use-1111", **extra):
    payload = {"label": "测试 Key", "provider": "openai", "api_key": secret,
               "model": "gpt-4o-mini", "vision_model": "gpt-4o-mini", **extra}
    response = client.post("/api/keys", json=payload, headers=owner["headers"])
    assert response.status_code == 201, response.text
    assert secret not in response.text
    return response.json()

def entry(amount="0.10"):
    return {"id": str(uuid4()), "type": "expense", "category": "饮食", "amount": amount,
            "note": "午餐", "createdAt": "2026-11-20T12:30:00+08:00"}

def test_login_logout_password_revocation(client, account):
    owner = account()
    assert client.get("/api/ledger").status_code == 401
    assert client.post("/api/auth/login", json={**owner["credentials"], "password": "wrong-password"}).status_code == 401
    login = client.post("/api/auth/login", json=owner["credentials"])
    other_session = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.post("/api/auth/logout", headers=other_session).status_code == 200
    assert client.get("/api/ledger", headers=other_session).status_code == 401
    with SessionLocal() as db:
        stored = db.get(User, owner["id"])
        assert stored.password_hash != owner["credentials"]["password"]
        assert stored.password_hash.startswith("pbkdf2_sha256$")
    change = client.post("/api/auth/password", headers=owner["headers"],
        json={"current_password": owner["credentials"]["password"], "new_password": "changed-password-12345"})
    assert change.status_code == 200
    assert client.get("/api/ledger", headers=owner["headers"]).status_code == 401
    assert client.post("/api/auth/login", json=owner["credentials"]).status_code == 401
    assert client.post("/api/auth/login", json={**owner["credentials"], "password": "changed-password-12345"}).status_code == 200

def test_session_expiry_and_duplicate_username(client, account):
    owner = account()
    assert client.post("/api/auth/register", json=owner["credentials"]).status_code == 409
    with SessionLocal() as db:
        session = db.scalar(select(LoginSession).where(LoginSession.user_id == owner["id"]))
        session.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/auth/me", headers=owner["headers"]).status_code == 401

def test_ledger_isolation_precision_retry_and_validation(client, account):
    alice, bob = account(), account()
    original = entry()
    created = client.post("/api/ledger", headers=alice["headers"], json=[{**original, "user_id": bob["id"]}, entry("0.20")])
    assert created.status_code == 200, created.text
    assert client.get("/api/ledger", headers=bob["headers"]).json() == []
    assert client.post("/api/ledger", headers=alice["headers"], json=[original]).status_code == 200
    ledger = client.get("/api/ledger", headers=alice["headers"]).json()
    assert len(ledger) == 2
    assert client.post("/api/ledger", headers=alice["headers"], json=[{**original, "amount": "99.99"}]).status_code == 409
    assert sum(Decimal(str(row["amount"])) for row in ledger) == Decimal("0.30")
    with SessionLocal() as db:
        assert sorted(db.scalars(select(LedgerEntry.amount_cents).where(LedgerEntry.user_id == alice["id"]))) == [10, 20]
    victim_id = ledger[0]["id"]
    assert client.delete(f"/api/ledger/{victim_id}", headers=bob["headers"]).status_code == 404
    assert client.delete(f"/api/ledger/{victim_id}", headers=alice["headers"]).status_code == 200
    assert client.post("/api/ledger", headers=alice["headers"], json=[entry("0.001")]).status_code == 422
    assert client.post("/api/ledger", headers=alice["headers"], json=[entry("-1")]).status_code == 422
    assert client.post("/api/ledger", headers=alice["headers"], json=[{**entry(), "createdAt": "2026-11-20T12:00:00"}]).status_code == 422

def test_key_encryption_isolation_default_persistence_and_delete(client, account):
    alice, bob = account(), account()
    one = add_key(client, alice)
    two = add_key(client, alice, secret="sk-test-do-not-use-2222")
    assert one["is_default"] and not two["is_default"]
    assert client.get("/api/keys", headers=bob["headers"]).json() == []
    for suffix, method in [("/default", "post"), ("", "delete")]:
        assert getattr(client, method)("/api/keys/" + one["id"] + suffix, headers=bob["headers"]).status_code == 404
    with SessionLocal() as db:
        row = db.get(UserAPIKey, one["id"])
        assert "sk-test" not in row.encrypted_key
        assert cipher().decrypt(row.encrypted_key.encode()).decode() == "sk-test-do-not-use-1111"
    assert client.post(f"/api/keys/{two['id']}/default", headers=alice["headers"]).status_code == 200
    new_login = client.post("/api/auth/login", json=alice["credentials"]).json()
    renewed = {"Authorization": "Bearer " + new_login["access_token"]}
    rows = client.get("/api/keys", headers=renewed).json()
    assert next(row for row in rows if row["is_default"])["id"] == two["id"]
    assert client.delete(f"/api/keys/{two['id']}", headers=renewed).status_code == 200
    assert client.get("/api/keys", headers=renewed).json()[0]["is_default"]
    assert client.delete(f"/api/keys/{one['id']}", headers=renewed).status_code == 200
    assert not client.get("/api/features", headers=renewed).json()["text_ai"]
    rejected = client.post("/api/keys", headers=renewed, json={"api_key": "raw-secret-value"})
    assert rejected.status_code == 422 and "raw-secret-value" not in rejected.text

def test_ai_uses_only_owners_default_key_without_app_daily_quota(client, account, monkeypatch):
    alice, bob = account(), account()
    assert client.post("/api/agent/text", headers=alice["headers"], json={"text": "午餐20元"}).status_code == 503
    add_key(client, alice)
    add_key(client, bob, secret="sk-bob-secret-3333")
    used = []
    async def fake_completion(messages, config, vision=False):
        used.append(config["api_key"])
        return json.dumps({"records": [{"type": "expense", "category": "饮食", "amount": 20}], "analysis": "请确认"})
    monkeypatch.setattr(main, "call_chat_completion", fake_completion)
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    def call(_):
        return client.post("/api/agent/text", headers=alice["headers"], json={"text": "午餐20元"}).status_code
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(call, range(8)))
    assert statuses == [200] * 8
    assert used == ["sk-test-do-not-use-1111"] * 8
    features = client.get("/api/features", headers=alice["headers"]).json()
    assert "ai_daily_limit" not in features and "ai_used" not in features
    assert client.post("/api/agent/text", headers=bob["headers"], json={"text": "午餐20元"}).status_code == 200
    assert used[-1] == "sk-bob-secret-3333"
    assert client.get("/api/ledger", headers=alice["headers"]).json() == []  # Drafts never auto-save.

def test_provider_429_is_reported_without_leaking_provider_response(client, account, monkeypatch):
    import httpx
    owner = account()
    add_key(client, owner)
    async def limited(messages, config, vision=False):
        request = httpx.Request("POST", "https://provider.example/chat/completions")
        response = httpx.Response(429, request=request, text="private-provider-error-body")
        raise httpx.HTTPStatusError("provider limit", request=request, response=response)
    monkeypatch.setattr(main, "call_chat_completion", limited)
    response = client.post("/api/agent/text", headers=owner["headers"], json={"text": "午餐20元"})
    assert response.status_code == 429
    assert "服务商" in response.json()["detail"]
    assert "private-provider-error-body" not in response.text

def test_image_access_is_private_and_old_public_path_closed(client, account, monkeypatch):
    alice, bob = account(), account()
    add_key(client, alice)
    async def fake_extract(path, mime, config):
        return {"type": "expense", "amount": 20, "category": "饮食", "occurred_at": "2026-11-20"}
    monkeypatch.setattr(main, "ai_extract_transaction", fake_extract)
    assert client.post("/api/agent/receipt", headers=alice["headers"], files={"file": ("evil.png", b"not-an-image", "image/png")}).status_code == 415
    response = client.post("/api/agent/receipt", headers=alice["headers"], files={"file": ("receipt.png", b"\x89PNG\r\n\x1a\nmock-image", "image/png")})
    assert response.status_code == 200
    path = response.json()["image_path"]
    assert client.get(path, headers=alice["headers"]).status_code == 200
    assert client.get(path, headers=bob["headers"]).status_code == 404
    assert client.get(path).status_code == 401
    assert client.get("/uploads/" + path.rsplit("/", 1)[1] + ".png").status_code == 404
    image_id = path.rsplit("/", 1)[1]
    (main.UPLOAD_DIR / (image_id + ".png")).unlink(missing_ok=True)
