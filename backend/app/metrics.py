"""请求指标：内存环形缓冲，用于质量面板实时展示（不落盘、不含用户内容）。"""

from __future__ import annotations

import statistics
import time
from collections import deque
from typing import Any


class MetricsStore:
    def __init__(self, limit: int = 100):
        self._records: deque[dict[str, Any]] = deque(maxlen=limit)

    def record(
        self,
        intent: str,
        tools: int,
        duration_ms: int,
        mode: str,
        ok: bool = True,
        ttft_ms: int | None = None,
    ) -> None:
        self._records.appendleft(
            {
                "intent": intent,
                "tools": tools,
                "duration_ms": duration_ms,
                "mode": mode,
                "ok": ok,
                "ttft_ms": ttft_ms,
                "at": time.strftime("%H:%M:%S"),
            }
        )

    def summary(self) -> dict[str, Any]:
        records = list(self._records)
        durations = [r["duration_ms"] for r in records]
        ttfts = [r["ttft_ms"] for r in records if r.get("ttft_ms") is not None]
        return {
            "total": len(records),
            "avg_duration_ms": round(statistics.mean(durations)) if durations else 0,
            "p95_duration_ms": (
                sorted(durations)[int(len(durations) * 0.95) - 1]
                if durations
                else 0
            ),
            "avg_ttft_ms": round(statistics.mean(ttfts)) if ttfts else 0,
            "ok_rate": (
                round(sum(1 for r in records if r["ok"]) / len(records), 3)
                if records
                else 1.0
            ),
            "recent": records[:10],
        }
