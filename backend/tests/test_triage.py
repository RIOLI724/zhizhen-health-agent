"""分诊规则引擎测试。"""

from pathlib import Path

from app.rules.engine import assess, load_rules

RULES_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "rules" / "triage_rules.json"
)
RULES = load_rules(RULES_PATH)


def test_dizziness_with_neuro_signal_is_l1():
    result = assess(
        RULES,
        "dizziness",
        {"nature": "vertigo", "associated": ["neuro"]},
    )
    assert result["level"] == "L1"
    assert result["department"] == "急诊科"


def test_fever_without_flags_is_l3():
    result = assess(
        RULES,
        "fever",
        {
            "age": "adult",
            "temp": "38to39",
            "duration": "1to3d",
            "associated": ["none"],
        },
    )
    assert result["level"] == "L3"


def test_chest_pain_over_15_minutes_is_l1():
    result = assess(
        RULES,
        "chest_pain",
        {"duration": "gt15m", "associated": ["none"]},
    )
    assert result["level"] == "L1"


def test_abdominal_pain_mild_is_l3():
    result = assess(
        RULES,
        "abdominal_pain",
        {"severity": "mild", "associated": ["none"]},
    )
    assert result["level"] == "L3"
