"""真实上传链路测试：视觉提取 → 检索 → 解读；降级与失败路径。"""

import json

import pytest
from fastapi.testclient import TestClient

from app.agent.graph import run_agent
from app.llm.vision import ReportImageError
from app.main import app
from tests.test_llm import FakeLLM


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

IMAGE = {"data": "aGVsbG8=", "mime": "image/png"}
REPORT = {
    "title": "血常规检验报告",
    "rows": [
        {"name": "白细胞", "value": "11.2", "unit": "×10⁹/L", "range": "3.5–9.5", "flag": "high"},
        {"name": "血红蛋白", "value": "108", "unit": "g/L", "range": "130–175", "flag": "low"},
    ],
    "note": "识别自图片，仅供参考，请以医生解读为准。",
}


class FakeVision:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def extract(self, data: str, mime: str) -> dict:
        self.calls.append((data, mime))
        if self._error:
            raise ReportImageError(self._error)
        return self._result


def _search_stub(query: str) -> dict:
    return {
        "citations": [f"《{query}指南》 · 要点"],
        "context": f"[1] 关于 {query} 的资料",
    }


def test_report_upload_without_vision_guides_to_samples():
    result = run_agent("帮我看看报告", [], {}, None, report_image=IMAGE)
    assert result["intent"] == "report_upload"
    assert result["report"] is None
    assert "样例" in result["answer"]


def test_report_upload_extracts_and_interprets():
    vision = FakeVision(result=REPORT)
    llm = FakeLLM(answer="【结论】白细胞偏高、血红蛋白偏低，提示感染可能伴轻度贫血。")
    result = run_agent(
        "",
        [],
        {"search_health_kb": _search_stub},
        llm,
        report_image=IMAGE,
        vision=vision,
    )
    assert vision.calls == [("aGVsbG8=", "image/png")]
    assert result["report"]["title"] == "血常规检验报告"
    assert "感染" in result["answer"]
    assert any("白细胞" in c for c in result["citations"])
    tool_names = [call["name"] for call in result["tool_calls"]]
    assert tool_names == ["classify", "extract_report", "search_health_kb"]


def test_report_upload_unreadable_image_reports_failure():
    vision = FakeVision(error="图片里没有读到有效指标，请拍清楚一点再试")
    result = run_agent(
        "", [], {}, None, report_image=IMAGE, vision=vision
    )
    assert result["report"] is None
    assert "识别失败" in result["answer"]


def test_chat_stream_accepts_report_image(client: TestClient):
    response = client.post(
        "/api/chat/stream",
        json={
            "message": "",
            "history": [],
            "report_image": {
                "data": "aGVsbG8=" * 10,
                "mime": "image/png",
            },
        },
    )
    assert response.status_code == 200
    body = response.text
    assert '"type": "done"' in body
    assert "样例" in body  # 测试环境无视觉服务 → 引导样例


def test_report_image_rejects_bad_mime(client: TestClient):
    response = client.post(
        "/api/chat/stream",
        json={
            "message": "",
            "report_image": {"data": "aGVsbG8=" * 10, "mime": "image/gif"},
        },
    )
    assert response.status_code == 422
    assert "JPG" in response.text


def test_report_image_normalizes_nonstandard_jpg(client: TestClient):
    """部分手机浏览器报 image/jpg，应归一化为 image/jpeg 而不是 422。"""
    response = client.post(
        "/api/chat/stream",
        json={
            "message": "",
            "report_image": {
                "data": "aGVsbG8=" * 10,
                "mime": "image/jpg",
            },
        },
    )
    assert response.status_code == 200
    assert '"type": "done"' in response.text


def test_report_row_json_shape():
    row = REPORT["rows"][0]
    assert json.dumps(row, ensure_ascii=False)
    assert row["flag"] in {"high", "low", "normal"}
