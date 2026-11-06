"""症状自查向导、质量面板、就医准备单接口测试。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_list_symptoms(client: TestClient):
    response = client.get("/api/triage/symptoms")
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [
        "dizziness",
        "fever",
        "chest_pain",
        "abdominal_pain",
        "headache",
    ]
    assert all(item["questions"] for item in data)


def test_assess_returns_red_flag(client: TestClient):
    response = client.post(
        "/api/triage/assess",
        json={
            "symptom": "dizziness",
            "answers": {"nature": "vertigo", "associated": ["neuro"]},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "L1"
    assert "急诊" in body["department"]
    assert body["evidence"]


def test_assess_unknown_symptom_returns_400(client: TestClient):
    response = client.post(
        "/api/triage/assess",
        json={"symptom": "unknown", "answers": {}},
    )
    assert response.status_code == 400


def test_quality_panel(client: TestClient):
    response = client.get("/api/quality")
    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_entries"] > 0
    assert body["red_flag_rules"] >= 25
    assert "metrics" in body


def test_visit_prep_includes_profile_and_symptoms(client: TestClient):
    response = client.post(
        "/api/visit-prep",
        json={
            "history": [
                {"role": "user", "content": "天旋地转，还有耳鸣"},
            ],
            "profile": {
                "relation": "family",
                "age": 62,
                "sex": "female",
                "pregnant": False,
            },
        },
    )
    assert response.status_code == 200
    text = response.json()["text"]
    assert "家人" in text
    assert "62" in text
    assert "耳鸣" in text
    assert "建议向医生确认" in text
