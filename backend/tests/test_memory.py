"""会话记忆测试：症状提取、注入生成提示、记忆兜底红旗。"""

from pathlib import Path

from app.agent.graph import run_agent
from app.agent.memory import build_memory, memory_note
from app.rules.engine import assess, load_rules
from tests.test_llm import FakeLLM

RULES = load_rules(
    Path(__file__).resolve().parents[1] / "data" / "rules" / "triage_rules.json"
)


def _triage(symptom: str, answers: dict) -> dict:
    return assess(RULES, symptom, answers)


def test_build_memory_extracts_symptoms_across_turns():
    history = [
        {"role": "user", "content": "最近总是头晕，天旋地转"},
        {"role": "assistant", "content": "有没有耳鸣？"},
        {"role": "user", "content": "有耳鸣"},
    ]
    memory = build_memory(history, "而且最近睡不好")
    assert memory["symptoms"] == ["vertigo", "tinnitus", "sleep"]


def test_memory_note_rendering():
    assert memory_note({"symptoms": ["vertigo", "tinnitus"]}) == (
        "【会话记忆】用户本次会话已提到：天旋地转、耳鸣/听力下降"
    )
    assert memory_note({"symptoms": []}) == ""
    assert memory_note(None) == ""


def test_memory_injected_into_agent_system_prompt():
    llm = FakeLLM(answer="生成回答")
    run_agent(
        "还是睡不好",
        [{"role": "user", "content": "我有耳鸣"}],
        {"search_health_kb": lambda query: {"citations": [], "context": ""}},
        llm,
    )
    assert llm.tool_messages
    system_content = llm.tool_messages[0][0]["content"]
    assert "耳鸣/听力下降" in system_content


def test_memory_upgrades_red_flag_in_later_turn():
    result = run_agent(
        "最近又有点头晕",
        [{"role": "user", "content": "之前手脚麻木说话不清"}],
        {"triage_assess": _triage},
    )
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"


def test_memory_alone_does_not_trigger_emergency():
    result = run_agent("最近总是睡不好", [{"role": "user", "content": "手脚麻木"}])
    assert result["intent"] == "sleep"
