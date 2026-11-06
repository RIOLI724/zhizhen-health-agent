"""质量门禁：检索与分诊指标不达标时测试失败。"""

from eval.run_eval import (
    RETRIEVAL_THRESHOLDS,
    SAFETY_THRESHOLDS,
    TRIAGE_THRESHOLDS,
    evaluate_all,
)


def test_quality_gate():
    metrics = evaluate_all()

    for key, threshold in RETRIEVAL_THRESHOLDS.items():
        assert metrics["retrieval"][key] >= threshold, key
    for key, threshold in TRIAGE_THRESHOLDS.items():
        assert metrics["triage"][key] >= threshold, key
    for key, threshold in SAFETY_THRESHOLDS.items():
        assert metrics["safety"][key] >= threshold, key
