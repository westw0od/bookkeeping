"""Exercise the actual key routes with an isolated in-memory database."""
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import key_management as keys
from models import Base, User, UserAPIKey


@pytest.fixture
def connection(monkeypatch):
    monkeypatch.setenv('KEY_ENCRYPTION_SECRET', Fernet.generate_key().decode())
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        owner = User(username='owner', password_hash='fixture')
        other = User(username='other', password_hash='fixture')
        db.add_all([owner, other])
        db.commit()
        current = [owner]
        app = FastAPI()
        app.include_router(keys.router)
        app.dependency_overrides[keys.get_db] = lambda: db
        app.dependency_overrides[keys.current_user] = lambda: current[0]
        with TestClient(app) as client:
            saved = client.post('/api/keys', json=dict(label='school', provider='sdu',
                api_key='sk-fake-fixture-secret', model='SDU-AI/DeepSeek-V4-Flash')).json()
            yield client, db, current, owner, other, saved
    engine.dispose()


def test_switch_keeps_secret_default_and_dispatches_exact_gateway_id(connection):
    client, db, current, owner, other, saved = connection
    row = db.get(UserAPIKey, saved['id'])
    encrypted = row.encrypted_key
    model = 'Ali-dashscope/Qwen3.6-Plus'
    response = client.patch('/api/keys/' + saved['id'], json=dict(label='Qwen', model=model, vision_model=model))
    assert response.status_code == 200
    assert response.json()['is_default'] is True
    assert response.json()['base_url'] == keys.PROVIDERS['sdu']
    assert 'sk-fake-fixture-secret' not in response.text
    db.refresh(row)
    assert row.encrypted_key == encrypted
    assert keys.active_config(db, owner)['api_key'] == 'sk-fake-fixture-secret'
    assert keys.active_config(db, owner)['vision_model'] == model
    assert keys.active_config(db, owner)['model'] == model
    text = 'ByteDance-volcengine/DeepSeek-V4.1-Flash'
    assert client.patch('/api/keys/' + saved['id'], json=dict(label='text', model=text, vision_model=None)).status_code == 200
    assert keys.active_config(db, owner)['vision_model'] is None
    current[0] = other
    assert client.patch('/api/keys/' + saved['id'], json=dict(label='attack', model=text)).status_code == 404
    db.refresh(row)
    assert row.label == 'text' and row.encrypted_key == encrypted


@pytest.mark.parametrize('payload', [dict(label=' ', model='valid'), dict(label='x', model='invalid model'), dict(label='x', model='valid', vision_model='bad?')])
def test_invalid_edits_do_not_change_saved_key(connection, payload):
    client, db, current, owner, other, saved = connection
    assert client.patch('/api/keys/' + saved['id'], json=payload).status_code == 422
    assert db.get(UserAPIKey, saved['id']).model == 'SDU-AI/DeepSeek-V4-Flash'
