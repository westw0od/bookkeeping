from uuid import uuid4
from sqlalchemy import select
from database import SessionLocal
from models import LedgerEntry

def create(client, owner, **extra):
    body = {"id": str(uuid4()), "type": "expense", "category": "人情", "amount": "500.00", "note": "随礼", "counterparty": "张三", "event": "婚礼", "createdAt": "2026-11-21T12:00:00+08:00", **extra}
    response = client.post('/api/ledger', headers=owner['headers'], json=[body])
    assert response.status_code == 200, response.text
    return response.json()[0], body

def test_edit_preserves_identity_and_is_owner_scoped_retryable(client, account):
    owner, other = account(), account()
    original, client_body = create(client, owner)
    changes = {**original, "type": "income", "amount": "300.25", "counterparty": "李四", "event": "生日", "note": "收到礼金", "createdAt": "2026-11-20T09:10:11.999+08:00"}
    path = '/api/ledger/' + original['id']
    request = {"original": original, "changes": changes}
    assert client.put(path, json=request).status_code == 401
    assert client.put(path, headers=other['headers'], json=request).status_code == 404
    first = client.put(path, headers=owner['headers'], json=request)
    assert first.status_code == 200, first.text
    assert first.json()['record']['id'] == original['id']
    assert first.json()['record']['counterparty'] == '李四'
    assert first.json()['record']['createdAt'] == '2026-11-20T01:10:11+00:00'
    assert client.put(path, headers=owner['headers'], json=request).status_code == 200
    rows = client.get('/api/ledger', headers=owner['headers']).json()
    assert len(rows) == 1 and rows[0]['amount'] == 300.25 and rows[0]['type'] == 'income'
    with SessionLocal() as db:
        stored = db.get(LedgerEntry, original['id'])
        assert stored.client_id == client_body['id'] and stored.amount_cents == 30025

def test_stale_edit_and_deleted_record_are_never_overwritten(client, account):
    owner = account()
    original, _ = create(client, owner)
    path = '/api/ledger/' + original['id']
    update = {**original, 'amount': '600.00'}
    assert client.put(path, headers=owner['headers'], json={'original': original, 'changes': update}).status_code == 200
    stale = client.put(path, headers=owner['headers'], json={'original': original, 'changes': {**original, 'amount': '700.00'}})
    assert stale.status_code == 409
    assert client.get('/api/ledger', headers=owner['headers']).json()[0]['amount'] == 600
    assert client.delete(path, headers=owner['headers']).status_code == 200
    assert client.put(path, headers=owner['headers'], json={'original': update, 'changes': original}).status_code == 409
    assert client.get('/api/ledger', headers=owner['headers']).json() == []

def test_edit_validation_does_not_partially_change_ledger(client, account):
    owner = account()
    original, _ = create(client, owner)
    path = '/api/ledger/' + original['id']
    for changes in [{'amount': '-5'}, {'amount': '1.001'}, {'category': '   '}, {'createdAt': '2026-11-21T12:00:00'}]:
        response = client.put(path, headers=owner['headers'], json={'original': original, 'changes': {**original, **changes}})
        assert response.status_code == 422, response.text
    assert client.get('/api/ledger', headers=owner['headers']).json()[0]['amount'] == 500
