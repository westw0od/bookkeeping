"""Integration tests use a dedicated real MySQL database, never the live ledger."""
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
settings = dotenv_values(BACKEND / ".env")
source = os.environ.get("TEST_DATABASE_URL") or settings.get("DATABASE_URL", "")
url = make_url(source).set(database="bookkeeping_test")
assert url.drivername == "mysql+pymysql" and url.database == "bookkeeping_test"
os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
os.environ.setdefault("KEY_ENCRYPTION_SECRET", settings.get("KEY_ENCRYPTION_SECRET", ""))

from database import SessionLocal
from models import User
from main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def schema():
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")

@pytest.fixture
def client(schema):
    with TestClient(app) as value:
        yield value

@pytest.fixture
def account(client):
    ids = []
    def create():
        username = "test_" + uuid4().hex[:15]
        credentials = {"username": username, "password": "test-password-12345"}
        result = client.post("/api/auth/register", json=credentials)
        assert result.status_code == 201, result.text
        data = result.json()
        ids.append(data["user"]["id"])
        return {"headers": {"Authorization": "Bearer " + data["access_token"]},
                "credentials": credentials, "id": data["user"]["id"]}
    yield create
    with SessionLocal() as db:
        db.execute(delete(User).where(User.id.in_(ids)))
        db.commit()
