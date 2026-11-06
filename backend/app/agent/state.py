"""LangGraph 状态定义。"""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, str]]
    intent: str
    answer: str
    chips: list[str]
    citations: list[str]
    context: str
    streamed: bool
    replace_stream: bool
    emergency: dict[str, Any] | None
    emergency_symptom: str
    emergency_answers: dict[str, Any]
    risk: dict[str, Any] | None
    report: dict[str, Any] | None
    tool_calls: list[dict[str, Any]]
    tools: dict[str, Any]
    llm: Any
    vision: Any
    profile: dict[str, Any]
    memory: dict[str, Any]
    report_image: dict[str, Any] | None
    deep_search: bool
    emit_event: Any
    stream_state: dict[str, Any] | None
