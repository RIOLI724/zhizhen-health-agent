"""Agent 工具循环测试：模型自选工具、多轮检索、安全兜底。"""

from app.agent.graph import run_agent
from app.data.content import REPLIES
from tests.test_llm import FakeLLM


def _search_stub(query: str) -> dict:
    return {
        "citations": [f"《{query}指南》 · 要点"],
        "context": f"[1] 《{query}指南》\n关于 {query} 的资料",
    }


def _deep_stub(query: str) -> dict:
    return {
        "citations": [f"《深度{query}共识》 · 证据"],
        "context": f"[1] 《深度{query}共识》\n{query} 的深度证据",
    }


def test_open_report_request_asks_for_sample_not_fake_interpretation():
    llm = FakeLLM(
        answer="演示版暂不支持上传，回复「血常规样例 / 肝功能样例 / 甲状腺样例」可体验解读。"
    )
    result = run_agent(
        "帮我看看体检报告",
        [],
        {"interpret_report": lambda rid: {"title": "不该被调用", "rows": []}},
        llm,
    )
    assert result["report"] is None
    assert "样例" in result["answer"]


def test_named_report_type_is_deterministic_even_with_model():
    llm = FakeLLM(answer="不应被调用")
    result = run_agent("帮我看看血常规的化验单", [], {}, llm)
    assert result["report"]["title"] == "血常规 + 生化"
    assert llm.tool_requests == []


def test_report_intro_stays_deterministic_without_model():
    result = run_agent("帮我看看体检报告", [], {})
    assert "样例" in result["answer"]
    assert result["report"] is None


def test_report_sample_chip_never_enters_model_loop():
    llm = FakeLLM(answer="不应被调用")
    result = run_agent("肝功能样例", [], {}, llm)
    assert result["report"]["title"] == "肝功能 + 血脂"
    assert llm.tool_requests == []


def test_deep_search_toggle_steers_model_prompt():
    llm = FakeLLM(answer="好的")
    run_agent(
        "耳鸣查一下",
        [],
        {"search_health_kb": _search_stub},
        llm,
        deep_search=True,
    )
    system_message = llm.tool_messages[0][0]["content"]
    assert "深度搜索已开启" in system_message


def test_model_runs_iterative_deep_search():
    llm = FakeLLM(
        answer="综合两轮检索，你的情况建议耳鼻喉科评估。",
        tool_script=[
            [("deep_search", {"query": "头晕 耳鸣"})],
            [("deep_search", {"query": "梅尼埃 检查"})],
        ],
    )
    result = run_agent(
        "最近头晕还有耳鸣，帮我仔细查查",
        [],
        {"deep_search": _deep_stub, "search_health_kb": _search_stub},
        llm,
    )
    deep_calls = [
        call for call in result["tool_calls"] if call["name"] == "deep_search"
    ]
    assert len(deep_calls) == 2
    assert deep_calls[0]["arguments"]["query"] == "头晕 耳鸣"
    assert deep_calls[1]["arguments"]["query"] == "梅尼埃 检查"
    assert any("深度头晕 耳鸣共识" in c for c in result["citations"])
    assert any("深度梅尼埃 检查共识" in c for c in result["citations"])


def test_agent_loop_respects_max_turns():
    endless = [[("search_health_kb", {"query": f"第{i}轮"})] for i in range(10)]
    llm = FakeLLM(answer="永远到不了", tool_script=endless)
    result = run_agent("耳鸣", [], {"search_health_kb": _search_stub}, llm)
    assert len(llm.tool_requests) == 4
    assert result["answer"] == REPLIES["dizziness_meniere"]["text"]


def test_model_direct_answer_without_tools():
    llm = FakeLLM(answer="你的问题太模糊了，能具体描述一下吗？")
    result = run_agent("白天总是没精神", [], {}, llm)
    assert result["answer"].startswith("你的问题太模糊")
    assert result["citations"] == []


def test_text_tool_call_is_coerced_not_displayed():
    llm = FakeLLM(
        answer='search_health_kb {"query": "头晕 耳鸣"}',
        tool_script=[],
    )
    result = run_agent(
        "最近头晕还有耳鸣，帮我仔细查查",
        [],
        {"search_health_kb": _search_stub},
        llm,
    )
    assert "search_health_kb" not in result["answer"]
    assert any("头晕 耳鸣" in c for c in result["citations"])


def test_function_style_text_call_is_coerced():
    llm = FakeLLM(
        answer='interpret_report(report_id="sample-1")',
        tool_script=[],
    )
    result = run_agent(
        "帮我看看体检报告",
        [],
        {"interpret_report": lambda rid: {"title": "血常规 + 生化", "rows": [], "note": "n"}},
        llm,
    )
    assert result["report"]["title"] == "血常规 + 生化"
    assert "interpret_report" not in result["answer"]


def test_unparsable_tool_text_never_displayed():
    llm = FakeLLM(answer="interpret_report(???")
    result = run_agent("帮我看看体检报告", [], {}, llm)
    assert "interpret_report" not in result["answer"]
    assert "样例" in result["answer"]


def test_unsafe_model_output_falls_back_to_template():
    llm = FakeLLM(
        answer="你得了梅尼埃病，建议服用地西泮 5mg。",
        tool_script=[[("search_health_kb", {"query": "耳鸣"})]],
    )
    result = run_agent(
        "耳鸣 / 听力下降", [], {"search_health_kb": _search_stub}, llm
    )
    assert result["answer"] == REPLIES["dizziness_meniere"]["text"]


def test_agent_streams_tokens_via_callback():
    events: list[dict] = []
    llm = FakeLLM(answer="流式回答内容")
    result = run_agent(
        "耳鸣", [], {}, llm, emit_event=events.append
    )
    deltas = [event for event in events if event["type"] == "delta"]
    assert deltas
    assert "".join(event["content"] for event in deltas) == "流式回答内容"
    assert result["streamed"] is True


def test_unsafe_streamed_output_requests_replacement():
    events: list[dict] = []
    llm = FakeLLM(answer="你得了梅尼埃病，建议服用地西泮 5mg。")
    result = run_agent(
        "耳鸣", [], {}, llm, emit_event=events.append
    )
    assert result["replace_stream"] is True
    assert result["answer"] == REPLIES["dizziness_meniere"]["text"]


def test_agent_system_prompt_carries_profile_and_memory():
    llm = FakeLLM(answer="结合你提到的耳鸣，建议耳鼻喉科评估。")
    run_agent(
        "那需要做什么检查？",
        [{"role": "user", "content": "我有耳鸣"}],
        {"search_health_kb": _search_stub},
        llm,
        profile={"relation": "family", "age": 60},
    )
    system_message = llm.tool_messages[0][0]["content"]
    assert "会话记忆" in system_message
    assert "耳鸣/听力下降" in system_message
    assert "家人" in system_message
    assert "60 岁" in system_message
