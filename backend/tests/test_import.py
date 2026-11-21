from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import select
from database import SessionLocal
from models import LedgerEntry

def document(**extra):
    return {"format": "bookkeeping.v1", "source": "历史人情账本", "records": [
        {"external_id": "gift-1", "date": "2026-10-01", "type": "expense", "amount": "500.00", "category": "人情", "counterparty": "张三", "event": "婚礼", "note": "随礼"},
        {"external_id": "gift-2", "date": "2026-11-01", "type": "income", "amount": "300.00", "category": "人情", "counterparty": "张三", "event": "生日", "note": "收到礼金"},
    ], **extra}

def test_preview_commit_retry_and_user_isolation(client, account):
    alice, bob = account(), account()
    body = document()
    preview = client.post("/api/ledger/import", headers=alice["headers"], json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["dry_run"] and preview.json()["new_count"] == 2
    assert preview.json()["income"] == 300 and preview.json()["expense"] == 500
    assert client.get("/api/ledger", headers=alice["headers"]).json() == []
    url = "/api/ledger/import?dry_run=false"
    first = client.post(url, headers=alice["headers"], json=body)
    assert first.status_code == 200 and first.json()["imported_count"] == 2
    repeat = client.post(url, headers=alice["headers"], json=body)
    assert repeat.json()["imported_count"] == 0 and repeat.json()["duplicate_count"] == 2
    rows = client.get("/api/ledger", headers=alice["headers"]).json()
    assert len(rows) == 2 and rows[0]["counterparty"] == "张三"
    assert "2026-11-01" in rows[0]["createdAt"]
    assert client.get("/api/ledger", headers=bob["headers"]).json() == []
    assert client.post(url, headers=bob["headers"], json=body).json()["imported_count"] == 2
    assert client.post(url, json=body).status_code == 401

def test_invalid_or_conflicting_batch_never_partly_imports_and_deleted_rows_stay_deleted(client, account):
    owner = account()
    body = document()
    url = "/api/ledger/import?dry_run=false"
    bad = document(records=[body["records"][0], {**body["records"][1], "amount": "-1"}])
    assert client.post(url, headers=owner["headers"], json=bad).status_code == 422
    assert client.get("/api/ledger", headers=owner["headers"]).json() == []
    assert client.post(url, headers=owner["headers"], json=body).status_code == 200
    rows = client.get("/api/ledger", headers=owner["headers"]).json()
    assert client.delete(f"/api/ledger/{rows[0]['id']}", headers=owner["headers"]).status_code == 200
    preview = client.post("/api/ledger/import", headers=owner["headers"], json=body).json()
    assert preview["removed_count"] == 1 and preview["duplicate_count"] == 1
    assert client.post(url, headers=owner["headers"], json=body).json()["imported_count"] == 0
    conflict = document(records=[{**body["records"][0], "external_id": "new-3"}, {**body["records"][1], "amount": "999.00"}])
    assert client.post(url, headers=owner["headers"], json=conflict).status_code == 409
    with SessionLocal() as db:
        assert len(db.scalars(select(LedgerEntry).where(LedgerEntry.user_id == owner["id"])).all()) == 2
    assert client.post(url, headers=owner["headers"], json=document(records=[body["records"][0]] * 2)).status_code == 422

def test_concurrent_imports_deduplicate_and_template_is_versioned(client, account):
    owner = account()
    assert client.get("/api/ledger/import/template", headers=owner["headers"]).json()["format"] == "bookkeeping.v1"
    def submit(_):
        response = client.post("/api/ledger/import?dry_run=false", headers=owner["headers"], json=document())
        assert response.status_code == 200, response.text
        return response.json()["imported_count"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        counts = list(pool.map(submit, range(3)))
    assert sum(counts) == 2
    assert len(client.get("/api/ledger", headers=owner["headers"]).json()) == 2
