"""规则引擎：红旗筛查与风险分级。

规则只认 JSON，不依赖模型；返回结构供 API / Agent 直接使用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assess(
    rules: dict[str, Any], symptom_id: str, answers: dict[str, Any]
) -> dict[str, Any]:
    """根据症状与回答返回风险等级、科室、时限、原因和依据。"""
    symptom = rules["symptoms"].get(symptom_id)
    if symptom is None:
        raise ValueError(f"未知症状：{symptom_id}")

    flags = [
        flag
        for flag in symptom.get("red_flags", [])
        if _matches(flag["when"], answers)
    ]

    if flags:
        flags.sort(key=lambda flag: LEVEL_ORDER.get(flag["level"], 99))
        chosen = flags[0]
        return {
            "symptom": symptom["name"],
            "level": chosen["level"],
            "department": chosen["department"],
            "timeframe": chosen["timeframe"],
            "reasons": _unique(flag["reason"] for flag in flags),
            "evidence": _unique(
                flag.get("evidence", "")
                for flag in flags
                if flag.get("evidence")
            ),
        }

    base = symptom["base"]
    return {
        "symptom": symptom["name"],
        "level": base["level"],
        "department": base["department"],
        "timeframe": base["timeframe"],
        "reasons": [base["reason"]],
        "evidence": [base["evidence"]] if base.get("evidence") else [],
    }


def _matches(when: dict[str, list[str]], answers: dict[str, Any]) -> bool:
    """when 里的每个问题都必须命中；同一问题的多个值之间是 OR。"""
    for question_id, expected in when.items():
        raw = answers.get(question_id)
        selected = raw if isinstance(raw, list) else [raw] if raw else []
        if not any(value in selected for value in expected):
            return False
    return True


def _unique(items) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
