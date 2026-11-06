"""OpenAI 兼容模型（智谱 GLM 系列 / DeepSeek / Qwen 等）。"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.llm.base import AgentTurn, BaseLLM

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS = (0.8, 1.6)

VALID_INTENTS = {
    "dizziness_intro",
    "dizziness_vertigo",
    "dizziness_unclear",
    "dizziness_meniere",
    "dizziness_bppv",
    "dizziness_lightheaded",
    "checks",
    "observe",
    "sleep",
    "sleep_meds",
    "imaging",
    "report",
    "report_result",
    "report_result_2",
    "report_result_3",
    "anemia_diet",
    "recheck",
    "fallback",
}

ROUTE_PROMPT = """你是健康助手的意图路由器。根据用户消息，只输出一个 JSON：
{"intent": "<意图>"}
可选意图：dizziness_intro（头晕初次提问）、dizziness_vertigo（天旋地转）、
dizziness_unclear（说不清）、dizziness_meniere（耳鸣/听力下降）、
dizziness_bppv（眩晕且无耳鸣/无神经症状）、dizziness_lightheaded（昏沉/眼前发黑）、
checks（问检查）、observe（问能否观察）、sleep（睡眠问题）、sleep_meds（问安眠药）、
imaging（CT / MRI / 影像）、report（想解读报告）、report_result（要求使用样例报告）、
fallback（无法判断）。
不要输出任何其他文字。"""

ANSWER_PROMPT = """你是「智诊」健康助手。只能依据下面的【参考资料】回答。

硬性规则：
1. 不诊断病名，不说“你得了 XX 病”，只能描述需要排查的方向；
2. 不开药、不给剂量、不推荐具体处方；
3. 不解读 CT / MRI / 超声影像；
4. 资料不足时直接说“资料不足，建议就医”，不要编造；
5. 不要输出 [1][2] 这类资料编号，直接把结论讲清楚。

回答结构：先给结论方向，再列需要警惕的情况，最后给就医建议。用简体中文，简洁。"""

UNSAFE_PATTERNS = (
    re.compile(r"你(已经)?(得了|患了|确诊为)"),
    re.compile(r"建议(服用|口服|使用).{0,12}(药|mg|毫克|片)"),
    re.compile(r"每次.{0,8}(片|粒|mg|毫克)"),
    re.compile(r"剂量为"),
)


class OpenAICompatibleLLM(BaseLLM):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=30,
        )

    @property
    def provider(self) -> str:
        return self._settings.llm_model

    @property
    def supports_tools(self) -> bool:
        return True

    def _chat(self, messages: list[dict[str, str]], temperature: float) -> str | None:
        """带重试的对话补全；限流/抖动时自动退避重试。"""
        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=messages,
                    temperature=temperature,
                )
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:  # noqa: BLE001 - 统一退避重试
                last_error = exc
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        logger.warning("LLM 调用失败（%s 次重试后）：%s", MAX_ATTEMPTS, last_error)
        return None

    def route_intent(
        self, message: str, history: list[dict[str, str]]
    ) -> str | None:
        messages = [
            {"role": "system", "content": ROUTE_PROMPT},
            *history[-4:],
            {"role": "user", "content": message},
        ]
        content = self._chat(messages, temperature=0)
        if content is None:
            return None
        try:
            data = _parse_json(content)
            intent = str(data.get("intent", "")).strip()
            return intent if intent in VALID_INTENTS else None
        except Exception as exc:  # noqa: BLE001 - 解析失败回退规则
            logger.warning("LLM 意图路由解析失败，回退规则：%s", exc)
            return None

    def generate_answer(
        self,
        message: str,
        history: list[dict[str, str]],
        context: str,
        citations: list[str],
    ) -> str | None:
        user_content = f"【参考资料】\n{context}\n\n【用户问题】\n{message}"
        messages = [
            {"role": "system", "content": ANSWER_PROMPT},
            *history[-4:],
            {"role": "user", "content": user_content},
        ]
        content = self._chat(messages, self._settings.llm_temperature)
        if not content or is_unsafe(content):
            return None
        return content

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_delta: Callable[[str], None] | None = None,
    ) -> AgentTurn:
        """OpenAI 兼容 function calling；传 on_delta 时逐 token 流式生成。"""
        payload_tools = [
            {"type": "function", "function": tool} for tool in tools
        ]
        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                if on_delta is None:
                    response = self._client.chat.completions.create(
                        model=self._settings.llm_model,
                        messages=messages,
                        tools=payload_tools,
                        tool_choice="auto",
                        temperature=self._settings.llm_temperature,
                    )
                    return _turn_from_message(response.choices[0].message)

                stream = self._client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=messages,
                    tools=payload_tools,
                    tool_choice="auto",
                    temperature=self._settings.llm_temperature,
                    stream=True,
                )
                content_parts: list[str] = []
                tool_acc: dict[int, dict[str, str]] = {}
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content_parts.append(delta.content)
                        on_delta(delta.content)
                    for call in delta.tool_calls or []:
                        acc = tool_acc.setdefault(
                            call.index,
                            {"id": "", "name": "", "arguments": ""},
                        )
                        if call.id:
                            acc["id"] = call.id
                        function = getattr(call, "function", None)
                        if function and function.name:
                            acc["name"] += function.name
                        if function and function.arguments:
                            acc["arguments"] += function.arguments

                content = "".join(content_parts)
                if not content and not tool_acc:
                    raise RuntimeError("流式响应为空")
                return _turn_from_accumulated(content, tool_acc)
            except Exception as exc:  # noqa: BLE001 - 统一退避重试
                last_error = exc
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        logger.warning("LLM 工具调用失败（%s 次重试后）：%s", MAX_ATTEMPTS, last_error)
        return AgentTurn()


def _turn_from_message(message: Any) -> AgentTurn:
    raw_calls = list(message.tool_calls or [])
    tool_calls = []
    for call in raw_calls:
        try:
            arguments = json.loads(call.function.arguments or "{}")
        except Exception:  # noqa: BLE001 - 参数损坏按空处理
            arguments = {}
        tool_calls.append(
            {
                "id": call.id,
                "name": call.function.name,
                "arguments": arguments,
            }
        )
    return AgentTurn(
        content=(message.content or None),
        tool_calls=tool_calls,
        assistant_message={
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments or "{}",
                    },
                }
                for call in raw_calls
            ],
        },
    )


def _turn_from_accumulated(
    content: str, tool_acc: dict[int, dict[str, str]]
) -> AgentTurn:
    tool_calls = []
    raw_calls = []
    for index in sorted(tool_acc):
        acc = tool_acc[index]
        if not acc["name"]:
            continue
        try:
            arguments = json.loads(acc["arguments"] or "{}")
        except Exception:  # noqa: BLE001 - 流式片段拼接失败按空处理
            arguments = {}
        call_id = acc["id"] or f"call-{index}"
        tool_calls.append(
            {"id": call_id, "name": acc["name"], "arguments": arguments}
        )
        raw_calls.append(
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": acc["name"],
                    "arguments": acc["arguments"] or "{}",
                },
            }
        )
    return AgentTurn(
        content=(content or None),
        tool_calls=tool_calls,
        assistant_message={
            "role": "assistant",
            "content": content or None,
            "tool_calls": raw_calls,
        },
    )


def _parse_json(content: str) -> dict:
    """兼容模型偶尔返回的 ```json 代码块。"""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def is_unsafe(content: str) -> bool:
    return any(pattern.search(content) for pattern in UNSAFE_PATTERNS)


def get_llm(settings: Settings) -> BaseLLM:
    from app.llm.mock import MockLLM

    provider = (settings.llm_provider or "mock").strip().lower()
    if settings.llm_api_key and provider in {"mock", "openai_compatible"}:
        return OpenAICompatibleLLM(settings)
    return MockLLM()
