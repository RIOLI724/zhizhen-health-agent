"""视觉提取：把报告图片读成结构化指标（GLM-4.6V-Flash 免费档）。

图片只在内存中转成 base64 调用模型，不落盘、不回显、不存储。
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from openai import OpenAI

from app.config import Settings

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS = (0.8, 1.6)
ALLOWED_FLAGS = {"high", "low", "normal"}
MAX_ROWS = 12

EXTRACT_PROMPT = """你是体检报告识别助手。从图片中提取检验指标，只输出 JSON：
{
  "title": "报告标题，如：血常规检验报告",
  "rows": [
    {"name": "指标名", "value": "数值", "unit": "单位", "range": "参考区间", "flag": "high|low|normal"}
  ],
  "note": "一句话说明图片清晰度或缺失内容，没有则留空"
}
规则：
1. 只提取图片里能看清的指标；数值旁的箭头/H/L 用于判断 flag（↑H 为 high，↓L 为 low，无标记为 normal）；
2. 参考区间照图片抄，没有就不填；
3. 不诊断、不加建议、不编造看不清的内容；
4. 只输出 JSON，不要其他文字。"""


class ReportImageError(Exception):
    """图片无法识别时抛出，消息可直接展示给用户。"""


class VisionExtractor:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60,
        )

    @property
    def available(self) -> bool:
        return bool(self._settings.llm_api_key)

    def extract(self, image_base64: str, mime: str) -> dict[str, Any]:
        data_url = f"data:{mime};base64,{image_base64}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": EXTRACT_PROMPT},
                ],
            }
        ]

        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.vision_model,
                    messages=messages,
                    temperature=0.1,
                )
                content = (response.choices[0].message.content or "").strip()
                return _parse_report(content)
            except ReportImageError:
                raise
            except Exception as exc:  # noqa: BLE001 - 统一退避重试
                last_error = exc
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        raise ReportImageError(f"识别服务暂时不可用，请稍后再试（{last_error}）")


def _parse_report(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except Exception as exc:
        raise ReportImageError(
            "图片里没有读到有效报告，请把报告拍清楚、光线充足后再试"
        ) from exc

    rows: list[dict[str, str]] = []
    for row in data.get("rows", [])[:MAX_ROWS]:
        name = str(row.get("name", "")).strip()
        value = str(row.get("value", "")).strip()
        if not name or not value:
            continue
        flag = str(row.get("flag", "normal")).strip().lower()
        rows.append(
            {
                "name": name,
                "value": value,
                "unit": str(row.get("unit", "")).strip(),
                "range": str(row.get("range", "")).strip(),
                "flag": flag if flag in ALLOWED_FLAGS else "normal",
            }
        )
    if not rows:
        raise ReportImageError("图片里没有读到有效指标，请拍清楚一点再试")

    return {
        "title": str(data.get("title", "")).strip() or "检验报告",
        "rows": rows,
        "note": "识别自图片，仅供参考，请以医生解读为准。",
    }


def get_vision_extractor(settings: Settings) -> VisionExtractor | None:
    """无 Key 时返回 None，上传功能自动降级为样例引导。"""
    if not settings.llm_api_key:
        return None
    return VisionExtractor(settings)
