"""接口测试：健康检查与 SSE 帧。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_stream_returns_sse_frames(client):
    response = client.post(
        "/api/chat/stream",
        json={"message": "最近总是头晕", "history": []},
    )
    assert response.status_code == 200
    body = response.text
    assert '"type": "delta"' in body
    assert '"type": "done"' in body


def test_chat_stream_attaches_risk_event(client):
    response = client.post(
        "/api/chat/stream",
        json={"message": "耳鸣 / 听力下降", "history": []},
    )
    assert response.status_code == 200
    assert '"type": "risk"' in response.text


def test_chat_stream_accepts_session_profile(client):
    response = client.post(
        "/api/chat/stream",
        json={
            "message": "最近总是头晕",
            "history": [],
            "profile": {
                "relation": "family",
                "age": 30,
                "sex": "female",
                "pregnant": False,
            },
        },
    )
    assert response.status_code == 200
    assert '"type": "done"' in response.text
