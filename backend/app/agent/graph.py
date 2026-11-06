"""LangGraph 图：意图识别 → 追问 / 检索 / 急救 / 报告 / 上传解读 → 回答。"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.llm.base import BaseLLM


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify", nodes.classify)
    graph.add_node("follow_up", nodes.follow_up)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("answer", nodes.answer)
    graph.add_node("agent", nodes.agent)
    graph.add_node("emergency", nodes.emergency)
    graph.add_node("report", nodes.report)
    graph.add_node("report_upload", nodes.report_upload)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        nodes.route_after_classify,
        {
            "follow_up": "follow_up",
            "retrieve": "retrieve",
            "agent": "agent",
            "emergency": "emergency",
            "report": "report",
            "report_upload": "report_upload",
        },
    )

    graph.add_edge("follow_up", END)
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    graph.add_edge("agent", END)
    graph.add_edge("emergency", END)
    graph.add_edge("report", END)
    graph.add_edge("report_upload", END)

    return graph.compile()


AGENT_GRAPH = build_graph()


def run_agent(
    message: str,
    history: list[dict[str, str]],
    tools: dict | None = None,
    llm: BaseLLM | None = None,
    deep_search: bool = False,
    profile: dict | None = None,
    report_image: dict | None = None,
    vision: Any = None,
    emit_event: Any = None,
    stream_state: dict | None = None,
) -> dict:
    """执行一次 agent 图，返回完整状态。"""
    return dict(
        AGENT_GRAPH.invoke(
            {
                "message": message,
                "history": history,
                "tools": tools or {},
                "llm": llm,
                "vision": vision,
                "deep_search": deep_search,
                "profile": profile or {},
                "report_image": report_image,
                "emit_event": emit_event,
                "stream_state": stream_state,
            }
        )
    )
