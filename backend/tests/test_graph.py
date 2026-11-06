"""Agent 图测试：意图路由、引用、红旗、报告。"""

from pathlib import Path

from app.agent.graph import run_agent
from app.rules.engine import assess, load_rules

RULES = load_rules(
    Path(__file__).resolve().parents[1] / "data" / "rules" / "triage_rules.json"
)


def _triage(symptom: str, answers: dict) -> dict:
    return assess(RULES, symptom, answers)


def test_dizziness_intro_returns_follow_up():
    result = run_agent("最近总是头晕，是怎么回事？", [])
    assert result["intent"] == "dizziness_intro"
    assert "天旋地转" in result["answer"]
    assert result["chips"]


def test_meniere_returns_citations():
    result = run_agent("耳鸣 / 听力下降", [])
    assert result["intent"] == "dizziness_meniere"
    assert result["citations"]
    assert "耳鼻喉科" in result["answer"]


def test_red_flag_returns_emergency():
    result = run_agent("手脚麻木 / 说话不清", [])
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"


def test_other_symptoms_trigger_emergency_rules():
    cases = [
        ("胸口压榨性疼痛，出冷汗", "胸痛"),
        ("发烧抽搐", "发热"),
        ("肚子痛呕血", "消化道出血"),
        ("突然炸裂样头痛", "头痛"),
    ]
    for message, reason in cases:
        result = run_agent(message, [], {"triage_assess": _triage})
        assert result["intent"] == "emergency"
        assert result["emergency"]["level"] == "L1"
        assert reason in result["emergency"]["desc"]


def test_report_sample_returns_report_card():
    result = run_agent("使用样例报告", [])
    assert result["intent"] == "report_result"
    assert result["report"]["rows"]


def test_three_report_samples_route_to_distinct_cards():
    cases = [
        ("血常规样例", "血常规 + 生化"),
        ("肝功能样例", "肝功能 + 血脂"),
        ("甲状腺样例", "甲状腺功能"),
    ]
    for message, title in cases:
        result = run_agent(message, [])
        assert result["report"]["title"] == title


def test_report_citations_filtered_to_matching_doc():
    def search(query: str):
        return {
            "hits": [
                {
                    "doc_id": "report-lft",
                    "source": "《血脂指南》",
                    "section": "指标解释",
                },
                {
                    "doc_id": "diz-meniere",
                    "source": "《梅尼埃指南》",
                    "section": "诊断要点",
                },
            ],
            "citations": ["噪声引用"],
        }

    result = run_agent(
        "肝功能样例", [], {"search_health_kb": search}
    )
    assert result["citations"] == ["《血脂指南》 · 指标解释"]


def test_deep_search_uses_injected_deep_tool():
    calls = []

    def deep(query: str):
        calls.append(query)
        return {
            "citations": ["《深度指南》 · 要点"],
            "context": "[1] 《深度指南》\n测试资料",
        }

    result = run_agent(
        "耳鸣 / 听力下降",
        [],
        {"deep_search": deep},
        deep_search=True,
    )
    assert calls == ["梅尼埃病 耳鸣 听力下降 眩晕"]
    assert result["citations"] == ["《深度指南》 · 要点"]
    assert result["tool_calls"][-1]["name"] == "deep_search"


def test_symptom_answer_attaches_structured_risk():
    result = run_agent(
        "耳鸣 / 听力下降",
        [],
        {
            "triage_assess": _triage,
            "search_health_kb": lambda query: {"citations": ["《测试指南》"]},
        },
    )
    risk = result.get("risk")
    assert risk is not None
    assert risk["level"] == "L3"
    assert "耳鼻喉科" in risk["department"]
    assert risk["timeframe"]


def test_no_triage_tool_skips_risk():
    result = run_agent("耳鸣 / 听力下降", [])
    assert "risk" not in result


def test_session_profile_informs_triage_answers():
    result = run_agent(
        "发烧抽搐",
        [],
        {"triage_assess": _triage},
        profile={"relation": "family", "age": 5},
    )
    call = next(
        item
        for item in result["tool_calls"]
        if item["name"] == "triage_assess"
    )
    assert call["arguments"]["answers"]["age"] == "child"


def test_pregnant_profile_triggers_ectopic_red_flag():
    result = run_agent(
        "下腹痛出血",
        [],
        {"triage_assess": _triage},
        profile={"relation": "family", "pregnant": True},
    )
    assert result["intent"] == "emergency"
    assert result["emergency"]["level"] == "L1"
    assert result["emergency"]["department"]
    assert result["emergency"]["timeframe"]


def test_checks_returns_citations():
    result = run_agent("需要做哪些检查？", [])
    assert result["intent"] == "checks"
    assert result["citations"]


def test_imaging_is_refused():
    result = run_agent("帮我看看CT片子是不是肺癌", [])
    assert result["intent"] == "imaging"
    assert "不能解读" in result["answer"]


def test_sleep_medication_is_refused():
    result = run_agent("给我开点安眠药，剂量多少", [])
    assert result["intent"] == "sleep_meds"
    assert "不能推荐" in result["answer"]


def test_retrieval_uses_injected_tools():
    calls = []

    def search(query: str):
        calls.append(query)
        return {"citations": ["《测试指南》"]}

    result = run_agent(
        "耳鸣 / 听力下降", [], {"search_health_kb": search}
    )
    assert result["citations"] == ["《测试指南》"]
    assert calls == ["梅尼埃病 耳鸣 听力下降 眩晕"]
