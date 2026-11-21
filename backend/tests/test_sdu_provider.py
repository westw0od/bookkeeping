import asyncio
import json

import httpx
from sqlalchemy import select
from database import SessionLocal
from key_management import active_config
from models import User
import ai

def test_sdu_key_dispatch_matches_supplied_openai_format(client, account, monkeypatch):
    owner = account()
    secret = "sk-sdu-fake-testing-only"
    saved = client.post("/api/keys", headers=owner["headers"], json={
        "label": "山大 AI", "provider": "sdu", "api_key": secret,
        "model": "SDU-AI/DeepSeek-V4-Flash", "vision_model": None})
    assert saved.status_code == 201
    assert secret not in saved.text
    assert saved.json()["base_url"] == "https://xplt.sdu.edu.cn:4000/v1"
    with SessionLocal() as db:
        config = active_config(db, db.get(User, owner["id"]))
    assert config["model"] == "SDU-AI/DeepSeek-V4-Flash"
    observed = []
    def transport(request):
        observed.append(request)
        assert str(request.url) == "https://xplt.sdu.edu.cn:4000/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer " + secret
        payload = json.loads(request.content)
        assert payload["model"] == "SDU-AI/DeepSeek-V4-Flash"
        assert payload["temperature"] == .7
        assert payload["stream"] is False
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "records": [{"type": "expense", "category": "饮食", "amount": 25}], "analysis": "午餐支出 25 元"})}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs))
    response = client.post("/api/agent/text", headers=owner["headers"], json={"text": "今天午餐花了25元"})
    assert response.status_code == 200, response.text
    assert len(observed) == 1
    assert float(response.json()["records"][0]["amount"]) == 25
    assert client.get("/api/features", headers=owner["headers"]).json()["image_ai"] is False
    assert client.get("/api/ledger", headers=owner["headers"]).json() == []
