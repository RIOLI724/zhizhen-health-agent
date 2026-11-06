"""LLM 层测试：Mock 回退、路由、生成与安全护栏。"""

import json

from app.agent.graph import run_agent
from app.llm.base import AgentTurn, BaseLLM
from app.llm.mock import MockLLM
from app.llm.openai_compatible import is_unsafe


class FakeLLM(BaseLLM):
    """脚本化假模型：可编排工具调用轮次，用于测试 agent 循环。"""

    def __init__(
        self,
        intent: str | None = None,
        answer: str | None = None,
        tool_script: list[list[tuple[str, dict]]] | None = None,
    ):
        self._intent = intent
        self._answer = answer
        self._tool_script = list(tool_script or [])
        self.turn_index = 0
        self.routed_messages: list[str] = []
        self.generated_messages: list[str] = []
        self.tool_requests: list[list[str]] = []
        self.tool_messages: list[list[dict]] = []

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def supports_tools(self) -> bool:
        return True

    def route_intent(self, message, history):
        self.routed_messages.append(message)
        return self._intent

    def generate_answer(self, message, history, context, citations):
        self.generated_messages.append(message)
        return self._answer

    def chat_with_tools(self, messages, tools, on_delta=None):
        self.tool_messages.append(messages)
        self.tool_requests.append(
            [tool["function"]["name"] for tool in tools]
        )
        if self.turn_index < len(self._tool_script):
            calls = self._tool_script[self.turn_index]
            self.turn_index += 1
            if calls:
                parsed = [
                    {
                        "id": f"call-{self.turn_index}-{index}",
                        "name": name,
                        "arguments": arguments,
                    }
                    for index, (name, arguments) in enumerate(calls)
                ]
                return AgentTurn(
                    tool_calls=parsed,
                    assistant_message={
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call["id"],
                                "type": "function",
                                "function": {
                                    "name": call["name"],
                                    "arguments": json.dumps(call["arguments"]),
                                },
                            }
                            for call in parsed
                        ],
                    },
                )
        if on_delta is not None and self._answer:
            for token in self._answer:
                on_delta(token)
        return AgentTurn(
            content=self._answer,
            assistant_message={"role": "assistant", "content": self._answer},
        )


def test_mock_llm_returns_none():
    llm = MockLLM()
    assert llm.provider == "mock"
    assert llm.route_intent("最近没精神", []) is None
    assert llm.generate_answer("头晕", [], "资料", []) is None


def test_llm_routes_fallback_message():
    llm = FakeLLM(intent="sleep")
    result = run_agent("最近白天总是没精神", [], {}, llm)

    assert result["intent"] == "sleep"
    assert llm.routed_messages == ["最近白天总是没精神"]


def test_rule_intent_wins_over_llm():
    llm = FakeLLM(intent="sleep")
    result = run_agent("我头晕", [], {}, llm)

    assert result["intent"] == "dizziness_intro"
    assert llm.routed_messages == []


def test_llm_answer_used_when_context_available():
    def search(query):
        return {
            "citations": ["《测试指南》 · 要点"],
            "context": "[1] 《测试指南》\n测试资料",
        }

    llm = FakeLLM(
        answer="这是基于资料的生成回答。",
        tool_script=[[("search_health_kb", {"query": "睡不好"})]],
    )
    result = run_agent("最近总是睡不好", [], {"search_health_kb": search}, llm)

    assert result["answer"] == "这是基于资料的生成回答。"
    assert result["citations"] == ["《测试指南》 · 要点"]


def test_template_fallback_without_llm():
    result = run_agent("最近总是睡不好", [], {})
    assert "睡眠" in result["answer"] or "睡不好" in result["answer"]


def test_unsafe_output_detection():
    assert is_unsafe("你得了梅尼埃病")
    assert is_unsafe("建议服用地西泮 5mg")
    assert not is_unsafe("建议到耳鼻喉科就诊，由医生评估")
