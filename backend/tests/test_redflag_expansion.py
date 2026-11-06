"""数值型红旗与急症状态扩展测试：血糖/血压/血氧、独立出血、意识/吞咽。"""

from pathlib import Path

from app.agent.graph import run_agent
from app.agent.memory import build_memory, memory_note
from app.rules.engine import assess, load_rules

RULES = load_rules(
    Path(__file__).resolve().parents[1] / "data" / "rules" / "triage_rules.json"
)


def _triage(symptom: str, answers: dict) -> dict:
    return assess(RULES, symptom, answers)


def test_high_glucose_triggers_red_flag():
    result = run_agent("血糖 18，一直口渴", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"
    assert "血糖" in result["emergency"]["desc"]


def test_low_glucose_triggers_red_flag():
    result = run_agent("血糖 3.2，手在抖", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"


def test_normal_glucose_does_not_trigger():
    result = run_agent("血糖 6.5 严重吗", [])
    assert result["intent"] != "emergency"


def test_high_blood_pressure_triggers_red_flag():
    result = run_agent("血压 190/110 头晕", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"
    assert "血压" in result["emergency"]["desc"]


def test_normal_blood_pressure_does_not_trigger():
    result = run_agent("血压 175/95 要紧吗", [])
    assert result["intent"] != "emergency"


def test_low_spo2_triggers_red_flag():
    result = run_agent("血氧 88，有点喘", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"


def test_standalone_vomiting_blood_triggers_red_flag():
    result = run_agent("突然呕血了", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"
    assert "消化道出血" in result["emergency"]["desc"]


def test_standalone_blood_in_stool_triggers_l2():
    result = run_agent("便血不止", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L2"


def test_dysphagia_triggers_red_flag():
    result = run_agent("突然吞咽困难", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"
    assert "吞咽困难" in result["emergency"]["desc"]


def test_unconscious_triggers_red_flag():
    result = run_agent("老人叫不醒了", [], {"triage_assess": _triage})
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"


def test_memory_covers_expanded_symptoms():
    memory = build_memory(
        [{"role": "user", "content": "这两天恶心心悸，还拉肚子"}], ""
    )
    assert set(memory["symptoms"]) == {
        "vomiting",
        "palpitation",
        "diarrhea",
    }
    assert "恶心呕吐" in memory_note(memory)


def test_memory_note_uses_new_labels():
    assert "吞咽困难" in memory_note({"symptoms": ["dysphagia"]})
    assert "呕血/黑便/便血" in memory_note({"symptoms": ["bleeding"]})
