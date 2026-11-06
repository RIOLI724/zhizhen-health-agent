"""对话接口：SSE 流式输出 agent 结果。

agent 的最终生成通过队列桥接实现真 token 流式：
模型每产出一个 token 立即下发，首字延迟可观测；
模板/兜底回答仍按块发送，越界内容会收到 replace 帧覆盖。
"""

import json
import queue
import threading
import time
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent.graph import run_agent
from app.llm.base import BaseLLM
from app.schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])

CHUNK_SIZE = 8
CHUNK_DELAY_SECONDS = 0.012


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _frames(
    payload: ChatRequest,
    tools: dict,
    llm: BaseLLM | None,
    vision: Any | None,
    metrics: Any | None = None,
) -> Iterator[str]:
    started = time.perf_counter()
    events: queue.Queue[dict] = queue.Queue()
    counters: dict[str, Any] = {"deltas": 0, "ttft_ms": None}

    def emit(event: dict) -> None:
        if event.get("type") == "delta":
            counters["deltas"] += 1
            if counters["ttft_ms"] is None:
                counters["ttft_ms"] = round(
                    (time.perf_counter() - started) * 1000
                )
        events.put(event)

    def worker() -> None:
        try:
            result = run_agent(
                payload.message,
                [message.model_dump() for message in payload.history],
                tools,
                llm,
                deep_search=payload.deep_search,
                profile=payload.profile.model_dump(),
                report_image=(
                    payload.report_image.model_dump()
                    if payload.report_image
                    else None
                ),
                vision=vision,
                emit_event=emit,
            )
            events.put({"type": "__result__", "result": result})
        except Exception as exc:  # noqa: BLE001 - 流式通道内统一转错误帧
            events.put({"type": "__error__", "detail": str(exc)})
        finally:
            events.put({"type": "__end__"})

    yield _sse({"type": "status", "stage": "thinking"})
    threading.Thread(target=worker, daemon=True).start()

    result: dict | None = None
    while True:
        event = events.get()
        kind = event.get("type")
        if kind == "__end__":
            break
        if kind == "__error__":
            if metrics is not None:
                metrics.record(
                    intent="error",
                    tools=0,
                    duration_ms=round((time.perf_counter() - started) * 1000),
                    mode=getattr(llm, "provider", "mock"),
                    ok=False,
                )
            yield _sse(
                {"type": "error", "detail": f"服务内部错误：{event['detail']}"}
            )
            return
        if kind == "__result__":
            result = event["result"]
            continue
        yield _sse(event)

    if result is None:
        yield _sse({"type": "error", "detail": "服务内部错误：没有返回结果"})
        return

    if result.get("replace_stream"):
        # 流式内容越界：覆盖为安全模板
        yield _sse({"type": "replace", "content": result.get("answer", "")})
    elif not result.get("streamed"):
        # 模板/兜底回答没有逐 token 流，这里按块补发
        answer = result.get("answer", "")
        for index in range(0, len(answer), CHUNK_SIZE):
            yield _sse(
                {"type": "delta", "content": answer[index : index + CHUNK_SIZE]}
            )
            time.sleep(CHUNK_DELAY_SECONDS)

    for call in result.get("tool_calls", []):
        yield _sse(
            {
                "type": "tool_call",
                "name": call["name"],
                "arguments": call.get("arguments", {}),
            }
        )

    if result.get("chips"):
        yield _sse({"type": "chips", "items": result["chips"]})
    if result.get("risk"):
        yield _sse({"type": "risk", "data": result["risk"]})
    if result.get("citations"):
        yield _sse({"type": "citations", "items": result["citations"]})
    if result.get("emergency"):
        yield _sse({"type": "emergency", "data": result["emergency"]})
    if result.get("report"):
        yield _sse({"type": "report", "data": result["report"]})

    if metrics is not None:
        metrics.record(
            intent=result.get("intent", ""),
            tools=max(len(result.get("tool_calls", [])) - 1, 0),
            duration_ms=round((time.perf_counter() - started) * 1000),
            mode=getattr(llm, "provider", "mock"),
            ok=True,
            ttft_ms=counters["ttft_ms"],
        )

    yield _sse({"type": "done"})


@router.post("/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _frames(
            payload,
            request.app.state.health_tools,
            request.app.state.llm,
            request.app.state.vision,
            request.app.state.metrics,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
