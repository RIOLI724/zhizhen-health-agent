"""Mock 工具：接口与真实工具保持一致，后续替换实现即可。"""

from app.data.content import CITATIONS, EMERGENCY, REPORTS


def search_health_kb(query: str) -> list[str]:
    """模拟指南检索，返回引用列表。"""
    return list(CITATIONS.get(query, CITATIONS.get("fallback", [])))


def deep_search(query: str) -> list[str]:
    """模拟多步检索；垂直切片先复用单步结果。"""
    return search_health_kb(query)


def triage_assess(message: str) -> dict:
    """模拟红旗分诊；真实版本由规则引擎返回。"""
    return dict(EMERGENCY)


def interpret_report(report_id: str = "sample-1") -> dict:
    """模拟报告解读；真实版本接 OCR / 视觉模型。"""
    return dict(REPORTS.get(report_id, REPORTS["sample-1"]))
