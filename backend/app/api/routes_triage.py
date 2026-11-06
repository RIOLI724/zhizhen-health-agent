"""症状自查向导：返回症状问卷，按规则引擎给出分诊结果。"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.rules.engine import assess

router = APIRouter(prefix="/api/triage", tags=["triage"])

# 面向用户的五类症状（vitals / general_redflag 是对话内部的数值与状态规则）
WIZARD_SYMPTOMS = ("dizziness", "fever", "chest_pain", "abdominal_pain", "headache")


class AssessRequest(BaseModel):
    symptom: str
    answers: dict[str, Any] = {}


@router.get("/symptoms")
def list_symptoms(request: Request) -> list[dict[str, Any]]:
    rules = request.app.state.triage_rules
    symptoms = rules.get("symptoms", {})
    return [
        {
            "id": symptom_id,
            "name": symptoms[symptom_id].get("name", symptom_id),
            "questions": symptoms[symptom_id].get("questions", []),
        }
        for symptom_id in WIZARD_SYMPTOMS
        if symptom_id in symptoms
    ]


@router.post("/assess")
def assess_symptom(payload: AssessRequest, request: Request) -> dict[str, Any]:
    rules = request.app.state.triage_rules
    try:
        return assess(rules, payload.symptom, payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
