"""Mock 模型：不生成内容，全部交给规则与模板。"""

from __future__ import annotations

from app.llm.base import BaseLLM


class MockLLM(BaseLLM):
    @property
    def provider(self) -> str:
        return "mock"
