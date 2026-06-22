from __future__ import annotations

from autark.artifacts.base import apply_text_operations
from autark.core.models import CandidateChange, EvalCase, RunResult, ValidationDecision
from autark.core.protocols import Evaluator


class RerunValidationGate:
    def __init__(self, artifact_store, evaluator: Evaluator, min_improvement: float = 0.05, regression_threshold: float = 0.05) -> None:
        self.artifact_store = artifact_store
        self.evaluator = evaluator
        self.min_improvement = min_improvement
        self.regression_threshold = regression_threshold

    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        before_scores = candidate_change.metadata.get("before_scores", {"overall": 0.0})
        patched_artifact = self._patched_artifact(candidate_change)
        after_scores = await self._score_cases(candidate_change.artifact_id, patched_artifact, failing_cases)
        regression_results = await self._score_holdout(candidate_change.artifact_id, patched_artifact, holdout_cases or [])
        decision, reason = self._decide(before_scores, after_scores, regression_results)

        return ValidationDecision(
            decision=decision,
            change_id=candidate_change.change_id,
            artifact_id=candidate_change.artifact_id,
            before_scores=before_scores,
            after_scores=after_scores,
            regression_results=regression_results,
            reason=reason,
        )

    def _patched_artifact(self, candidate_change: CandidateChange) -> str:
        current = self.artifact_store.load(candidate_change.artifact_id)
        return apply_text_operations(current, candidate_change.operations)

    async def _score_cases(self, artifact_id: str, artifact_text: str, cases: list[EvalCase]) -> dict[str, float]:
        if not cases:
            return {"overall": 0.0}
        scores = []
        for case in cases:
            run_result = await self._run_case_with_artifact(artifact_id, artifact_text, case)
            eval_result = await self.evaluator.evaluate(case, run_result)
            scores.append(eval_result.scores.get("overall", 0.0))
        return {"overall": round(sum(scores) / len(scores), 4)}

    async def _score_holdout(self, artifact_id: str, artifact_text: str, cases: list[EvalCase]) -> list[dict]:
        results = []
        for case in cases:
            score = await self._score_cases(artifact_id, artifact_text, [case])
            results.append({"case_id": case.case_id, "scores": score})
        return results

    async def _run_case_with_artifact(self, artifact_id: str, artifact_text: str, case: EvalCase) -> RunResult:
        raise NotImplementedError

    def _decide(
        self,
        before_scores: dict[str, float],
        after_scores: dict[str, float],
        regression_results: list[dict],
    ) -> tuple[str, str]:
        before_overall = before_scores.get("overall", 0.0)
        after_overall = after_scores.get("overall", 0.0)
        improvement = after_overall - before_overall
        regressed = [
            result for result in regression_results
            if result.get("scores", {}).get("overall", 1.0) < before_overall - self.regression_threshold
        ]

        if regressed:
            return "rejected", f"Regression detected in {len(regressed)} holdout case(s)"
        if improvement >= self.min_improvement:
            return "accepted", f"Score improved {before_overall:.2f} -> {after_overall:.2f}"
        if improvement > 0:
            return "needs_watch", f"Marginal improvement {before_overall:.2f} -> {after_overall:.2f}"
        return "rejected", f"No improvement {before_overall:.2f} -> {after_overall:.2f}"


class MetadataScoreValidationGate:
    def __init__(self, min_improvement: float = 0.05, regression_threshold: float = 0.05) -> None:
        self.min_improvement = min_improvement
        self.regression_threshold = regression_threshold

    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        before_scores = candidate_change.metadata.get("before_scores", {"overall": 0.0})
        after_scores = candidate_change.metadata.get("after_scores", {"overall": 1.0})
        before_overall = before_scores.get("overall", 0.0)
        after_overall = after_scores.get("overall", 0.0)
        improvement = after_overall - before_overall

        if improvement >= self.min_improvement:
            decision = "accepted"
            reason = f"Score improved {before_overall:.2f} -> {after_overall:.2f}"
        elif improvement > 0:
            decision = "needs_watch"
            reason = f"Marginal improvement {before_overall:.2f} -> {after_overall:.2f}"
        else:
            decision = "rejected"
            reason = f"No improvement {before_overall:.2f} -> {after_overall:.2f}"

        return ValidationDecision(
            decision=decision,
            change_id=candidate_change.change_id,
            artifact_id=candidate_change.artifact_id,
            before_scores=before_scores,
            after_scores=after_scores,
            reason=reason,
        )
