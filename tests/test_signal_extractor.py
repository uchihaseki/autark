from __future__ import annotations

from autark.core.models import EvalResult
from autark.signals import ThresholdSignalExtractor


def test_signal_extractor_deduplicates_and_sorts() -> None:
    extractor = ThresholdSignalExtractor()
    eval_results = [
        EvalResult(
            case_id="case-1", artifact_id="prompt.txt", status="fail",
            scores={"overall": 0.1}, failure_category="wrong_answer", evidence="bad",
        ),
        EvalResult(
            case_id="case-2", artifact_id="prompt.txt", status="fail",
            scores={"overall": 0.2}, failure_category="wrong_answer", evidence="bad2",
        ),
        EvalResult(
            case_id="case-3", artifact_id="prompt.txt", status="fail",
            scores={"overall": 0.05}, failure_category="missing_constraint", evidence="missing",
        ),
    ]

    signals = extractor.extract(eval_results, recent_signals=[])

    assert len(signals) == 2
    assert signals[0].category == "missing_constraint"
    assert signals[1].category == "wrong_answer"
