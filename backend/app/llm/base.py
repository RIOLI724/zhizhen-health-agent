"""LLM 抽象层。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTurn:
    """一次工具对话轮次：纯文本回复或工具调用。"""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    assistant_message: dict[str, Any] | None = None


class BaseLLM(ABC):
    """对话模型能力：路由意图、基于资料生成回答、工具循环。"""

    @property
    @abstractmethod
    def provider(self) -> str: ...

    @property
    def supports_tools(self) -> bool:
        """是否支持 function calling 工具循环；Mock 默认不支持。"""
        return False

    def route_intent(
        self, message: str, history: list[dict[str, str]]
    ) -> str | None:
        """返回意图；无法判断时返回 None，由规则兜底。"""
        return None

    def generate_answer(
        self,
        message: str,
        history: list[dict[str, str]],
        context: str,
        citations: list[str],
    ) -> str | None:
        """基于检索资料生成回答；不可用时返回 None，由模板兜底。"""
        return None

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_delta: Callable[[str], None] | None = None,
    ) -> AgentTurn:
        """工具循环中的一轮；默认不支持，交给确定性流程。"""
        return AgentTurn()
