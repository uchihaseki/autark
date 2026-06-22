from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from autark.core.models import EvalResult, Signal


class ThresholdSignalExtractor:
    def __init__(
        self,
        fail_threshold: float = 0.5,
        category_to_type: dict[str, str] | None = None,
    ) -> None:
        self.fail_threshold = fail_threshold
        self.category_to_type = category_to_type or {
            "wrong_answer": "repair",
            "missing_constraint": "repair",
            "format_error": "repair",
            "empty_output": "repair",
            "execution_error": "repair",
            "capability_gap": "innovate",
            "prompt_ambiguous": "optimize",
            "boundary_case": "harden",
            "none": "",
        }

    def extract(
        self,
        eval_results: list[EvalResult],
        recent_signals: list[Signal] | None = None,
    ) -> list[Signal]:
        recent_signals = recent_signals or []
        failures = [result for result in eval_results if self._is_failure(result)]
        deduped = self._deduplicate(failures, recent_signals)
        signals = []

        for result in deduped:
            signal_type = self.category_to_type.get(result.failure_category, "repair")
            if not signal_type:
                continue
            signals.append(
                Signal(
                    signal_id=f"sig-{uuid4().hex[:8]}",
                    case_id=result.case_id,
                    artifact_id=result.artifact_id,
                    signal_type=signal_type,
                    category=result.failure_category or "unknown",
                    evidence=result.evidence,
                    scores=result.scores,
                    metadata={
                        "trajectory_summary": result.trajectory_summary,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        signals.sort(key=lambda signal: signal.scores.get("overall", 1.0))
        return signals

    def _is_failure(self, result: EvalResult) -> bool:
        if result.status == "fail":
            return True
        return result.scores.get("overall", 1.0) < self.fail_threshold

    @staticmethod
    def _deduplicate(failures: list[EvalResult], recent_signals: list[Signal]) -> list[EvalResult]:
        covered = {(signal.artifact_id, signal.category) for signal in recent_signals}
        groups: dict[tuple[str, str], list[EvalResult]] = {}

        for failure in failures:
            key = (failure.artifact_id, failure.failure_category)
            if key in covered:
                continue
            groups.setdefault(key, []).append(failure)

        deduped = []
        for group in groups.values():
            group.sort(key=lambda result: result.scores.get("overall", 1.0))
            deduped.append(group[0])
        return deduped
