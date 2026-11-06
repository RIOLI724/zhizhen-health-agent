"""真实健康工具：指南检索、分诊、报告解读。

工具通过闭包注入 RAG 管线与规则，Agent 节点只依赖工具名。
"""

from __future__ import annotations

from typing import Any, Callable

from app.data.content import REPORTS
from app.rag.pipeline import RAGPipeline
from app.rules.engine import assess

Tool = Callable[..., Any]


def build_health_tools(
    pipeline: RAGPipeline, rules: dict[str, Any]
) -> dict[str, Tool]:
    def _result(hits, **extra: Any) -> dict[str, Any]:
        # 同一文档只保留一次引用，保证 [1][2] 与引用列表一一对应。
        unique_hits = []
        seen: set[str] = set()
        for hit in hits:
            if hit.citation in seen:
                continue
            seen.add(hit.citation)
            unique_hits.append(hit)

        citations = [hit.citation for hit in unique_hits]
        context = "\n\n".join(
            f"[{index}] {hit.doc_name}（{hit.source}）\n{hit.text}"
            for index, hit in enumerate(unique_hits, 1)
        )
        return {
            "hits": [
                {
                    "doc_id": hit.doc_id,
                    "doc_name": hit.doc_name,
                    "text": hit.text,
                    "score": hit.score,
                    "source": hit.source,
                    "section": hit.section,
                }
                for hit in unique_hits
            ],
            "citations": citations,
            "context": context,
            **extra,
        }

    def search_health_kb(query: str) -> dict[str, Any]:
        return _result(pipeline.retrieve(query))

    def deep_search(query: str) -> dict[str, Any]:
        """多查询扩展 + RRF 融合，返回更广的指南证据。"""
        subqueries = [
            query,
            f"{query} 指南",
            f"{query} 红旗信号",
            f"{query} 处理",
        ]
        ranks: dict[str, float] = {}
        chunks: dict[str, Any] = {}

        for subquery in subqueries:
            for rank, hit in enumerate(
                pipeline.retrieve(subquery, top_k=4), 1
            ):
                key = hit.citation
                chunks.setdefault(key, hit)
                ranks[key] = ranks.get(key, 0.0) + 1.0 / (60 + rank)

        ordered = sorted(
            chunks.values(), key=lambda hit: ranks[hit.citation], reverse=True
        )[:5]
        return _result(ordered, strategy="multi_query", queries=subqueries)

    def triage_assess(symptom: str, answers: dict[str, Any]) -> dict[str, Any]:
        return assess(rules, symptom, answers)

    def interpret_report(report_id: str) -> dict[str, Any]:
        return dict(REPORTS.get(report_id, REPORTS["sample-1"]))

    return {
        "search_health_kb": search_health_kb,
        "deep_search": deep_search,
        "triage_assess": triage_assess,
        "interpret_report": interpret_report,
    }
