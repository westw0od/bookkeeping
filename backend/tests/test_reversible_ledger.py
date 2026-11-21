from uuid import uuid4
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from database import SessionLocal
from models import LedgerEntry
import main


@pytest.mark.parametrize("timestamp", [
    "2026-11-21T20:16:20.001+08:00",
    "2026-11-21T20:16:20.499+08:00",
    "2026-11-21T20:16:20.500+08:00",
    "2026-11-21T23:59:59.999999+08:00",
])
def test_fractional_seconds_save_and_retry_without_false_conflict(client, account, timestamp):
    owner = account()
    payload = {"id": str(uuid4()), "type": "expense", "category": "饮食", "amount": "93.00",
        "note": "晚饭吃饭", "createdAt": timestamp}
    expected = datetime.fromisoformat(timestamp).astimezone(timezone.utc).replace(microsecond=0)
    first = client.post("/api/ledger", headers=owner["headers"], json=[payload])
    assert first.status_code == 200, first.text
    assert datetime.fromisoformat(first.json()[0]["createdAt"]) == expected
    retry = client.post("/api/ledger", headers=owner["headers"], json=[payload])
    assert retry.status_code == 200, retry.text
    assert retry.json()[0]["id"] == first.json()[0]["id"]
    conflict = client.post("/api/ledger", headers=owner["headers"], json=[{**payload, "amount": "94.00"}])
    assert conflict.status_code == 409
    records = client.get("/api/ledger", headers=owner["headers"]).json()
    assert len(records) == 1 and records[0]["amount"] == 93

def save(client, owner, **extra):
    payload = {"id": str(uuid4()), "type": "expense", "category": "人情", "amount": "200.00",
        "note": "张三：生日礼金", "createdAt": "2026-11-21T12:00:00+08:00", **extra}
    response = client.post("/api/ledger", headers=owner["headers"], json=[payload])
    assert response.status_code == 200
    return payload, response.json()[0]

def test_delete_is_recoverable_idempotent_and_owner_scoped(client, account):
    alice, bob = account(), account()
    payload, saved = save(client, alice)
    path = f"/api/ledger/{saved['id']}"
    assert client.delete(path, headers=bob["headers"]).status_code == 404
    assert client.post(path + "/restore", headers=bob["headers"]).status_code == 404
    assert client.delete(path).status_code == 401
    first = client.delete(path, headers=alice["headers"])
    assert first.status_code == 200 and first.json()["record"]["revokedAt"]
    repeated = client.delete(path, headers=alice["headers"])
    assert repeated.json()["record"]["revokedAt"] == first.json()["record"]["revokedAt"]
    assert client.get("/api/ledger", headers=alice["headers"]).json() == []
    removed = client.get("/api/ledger/revoked", headers=alice["headers"]).json()
    assert [row["id"] for row in removed] == [saved["id"]]
    assert client.get("/api/ledger/revoked", headers=bob["headers"]).json() == []
    with SessionLocal() as db:
        row = db.get(LedgerEntry, saved["id"])
        assert row is not None and row.amount_cents == 20000 and row.note == "张三：生日礼金"
    assert client.post("/api/ledger", headers=alice["headers"], json=[payload]).status_code == 409
    assert client.post(path + "/restore", headers=alice["headers"]).status_code == 200
    assert client.post(path + "/restore", headers=alice["headers"]).status_code == 200
    restored = client.get("/api/ledger", headers=alice["headers"]).json()
    assert len(restored) == 1 and restored[0]["id"] == saved["id"]
    assert restored[0]["revokedAt"] is None and restored[0]["amount"] == 200
    assert client.get("/api/ledger/revoked", headers=alice["headers"]).json() == []

def test_revoked_records_are_excluded_from_analysis_and_failed_batch_is_atomic(client, account, monkeypatch):
    owner = account()
    old_payload, revoked = save(client, owner, note="已经删除的礼金")
    _, active = save(client, owner, amount="50.00", note="保留的礼金")
    client.delete(f"/api/ledger/{revoked['id']}", headers=owner["headers"])
    new_payload = {**old_payload, "id": str(uuid4()), "note": "不应部分写入"}
    assert client.post("/api/ledger", headers=owner["headers"], json=[new_payload, old_payload]).status_code == 409
    assert len(client.get("/api/ledger", headers=owner["headers"]).json()) == 1
    client.post("/api/keys", headers=owner["headers"], json={"provider": "sdu", "label": "测试", "api_key": "fake-model-key-only", "model": "SDU-AI/DeepSeek-V4-Flash"})
    messages_seen = []
    async def analyze(messages, config, vision=False):
        messages_seen.extend(messages)
        return "测试分析"
    monkeypatch.setattr(main, "call_chat_completion", analyze)
    assert client.post("/api/analysis", headers=owner["headers"], json={}).status_code == 200
    assert "保留的礼金" in messages_seen[-1]["content"]
    assert "已经删除的礼金" not in messages_seen[-1]["content"]
