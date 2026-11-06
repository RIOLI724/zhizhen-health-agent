"""质量面板与就医准备单接口。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.agent.memory import SYMPTOM_LABELS, build_memory
from app.schemas import ChatMessage, SessionProfile

router = APIRouter(prefix="/api", tags=["assistant"])

EVAL_REPORT_PATH = Path(__file__).resolve().parents[2] / "eval" / "report.json"


@router.get("/quality")
def quality(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    rules = request.app.state.triage_rules
    red_flags = sum(
        len(symptom.get("red_flags", []))
        for symptom in rules.get("symptoms", {}).values()
    )
    entries: list[dict[str, Any]] = []
    if settings.knowledge_path.exists():
        entries = json.loads(settings.knowledge_path.read_text(encoding="utf-8"))

    eval_report = None
    if EVAL_REPORT_PATH.exists():
        eval_report = json.loads(EVAL_REPORT_PATH.read_text(encoding="utf-8"))

    return {
        "app": settings.app_name,
        "mode": settings.llm_model if settings.llm_api_key else "mock",
        "vision": settings.vision_model if settings.llm_api_key else None,
        "knowledge_entries": len(entries),
        "red_flag_rules": red_flags,
        "eval": eval_report,
        "metrics": request.app.state.metrics.summary(),
    }


class VisitPrepRequest(BaseModel):
    history: list[ChatMessage] = []
    profile: SessionProfile = SessionProfile()


@router.post("/visit-prep")
def visit_prep(payload: VisitPrepRequest) -> dict[str, str]:
    """根据会话生成可复制的就医准备单（纯本地规则，不调用模型）。"""
    history = [message.model_dump() for message in payload.history]
    memory = build_memory(history, "")
    symptoms = [SYMPTOM_LABELS[s] for s in memory["symptoms"] if s in SYMPTOM_LABELS]
    recent = [
        message["content"].strip()
        for message in history
        if message["role"] == "user" and message["content"].strip()
    ][-3:]

    profile = payload.profile
    who = "本人" if profile.relation == "self" else "家人"
    details = []
    if profile.age:
        details.append(f"{profile.age} 岁")
    if profile.sex:
        details.append({"male": "男", "female": "女", "other": "其他"}[profile.sex])
    if profile.pregnant:
        details.append("孕产期")

    lines = [
        "【就诊人】" + who + ("（" + "，".join(details) + "）" if details else ""),
        "【主要症状】" + ("、".join(symptoms) if symptoms else "（会话中未整理出明确症状）"),
        "【最近描述】",
    ]
    if recent:
        lines.extend(f"{index}. {text}" for index, text in enumerate(recent, 1))
    else:
        lines.append("（暂无）")
    lines.extend(
        [
            "【建议向医生确认】",
            "- 症状出现的时间、频率、诱因与缓解方式",
            "- 已做过的检查、正在服用的药物",
            "- 需要补充哪些检查、多久复查",
        ]
    )
    return {"text": "\n".join(lines)}
