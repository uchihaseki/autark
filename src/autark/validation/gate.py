from __future__ import annotations

from dataclasses import dataclass

from autark.artifacts.base import apply_text_operations
from autark.core.api import public_api
from autark.core.models import CandidateChange, EvalCase, RunResult, ValidationDecision
from autark.core.protocols import Evaluator


@public_api(since="0.2.0")
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


@public_api(since="0.2.0")
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


# ---------------------------------------------------------------------------
# Enhanced validation gates (Phase 3)
# ---------------------------------------------------------------------------


@public_api(since="0.3.0", experimental=True)
class CompositeValidationGate:
    """Chains multiple validation gates. Short-circuits on the first rejection.

    Args:
        gates: List of validation gate instances to chain.
    """

    def __init__(self, gates: list) -> None:
        self.gates = gates

    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        decisions: list[ValidationDecision] = []
        for gate in self.gates:
            d = await gate.validate(candidate_change, failing_cases, holdout_cases)
            decisions.append(d)
            if d.decision == "rejected":
                return ValidationDecision(
                    decision="rejected",
                    change_id=candidate_change.change_id,
                    artifact_id=candidate_change.artifact_id,
                    reason=f"Composite gate rejected: {d.reason}",
                )

        reasons = "; ".join(d.reason for d in decisions)
        if any(d.decision == "needs_watch" for d in decisions):
            return ValidationDecision(
                decision="needs_watch",
                change_id=candidate_change.change_id,
                artifact_id=candidate_change.artifact_id,
                reason=reasons,
            )
        return ValidationDecision(
            decision="accepted",
            change_id=candidate_change.change_id,
            artifact_id=candidate_change.artifact_id,
            reason=reasons,
        )


@public_api(since="0.3.0", experimental=True)
class MaxChangeSizeGate:
    """Rejects changes whose total text operations exceed a byte limit.

    Args:
        max_bytes: Maximum allowed total byte size of operation text.
    """

    def __init__(self, max_bytes: int = 10240) -> None:
        self.max_bytes = max_bytes

    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        total_size = sum(
            len(op.get("text", "").encode("utf-8")) for op in candidate_change.operations
        )
        if total_size > self.max_bytes:
            return ValidationDecision(
                decision="rejected",
                change_id=candidate_change.change_id,
                artifact_id=candidate_change.artifact_id,
                reason=(
                    f"Change size {total_size} bytes exceeds max {self.max_bytes} bytes"
                ),
            )
        return ValidationDecision(
            decision="accepted",
            change_id=candidate_change.change_id,
            artifact_id=candidate_change.artifact_id,
            reason=f"Change size {total_size} bytes within limit",
        )


@public_api(since="0.3.0", experimental=True)
class AllowedOperationGate:
    """Rejects changes with operations not in an allowlist.

    Args:
        allowed_operations: Set of allowed operation type strings.
            Defaults to ``{"append", "replace"}``.
    """

    def __init__(self, allowed_operations: set[str] | None = None) -> None:
        self.allowed_operations = allowed_operations or {"append", "replace"}

    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        for op in candidate_change.operations:
            op_type = op.get("operation", "")
            if op_type not in self.allowed_operations:
                return ValidationDecision(
                    decision="rejected",
                    change_id=candidate_change.change_id,
                    artifact_id=candidate_change.artifact_id,
                    reason=(
                        f"Operation '{op_type}' not in allowlist: "
                        f"{self.allowed_operations}"
                    ),
                )
        return ValidationDecision(
            decision="accepted",
            change_id=candidate_change.change_id,
            artifact_id=candidate_change.artifact_id,
            reason="All operations allowed",
        )


# ---------------------------------------------------------------------------
# Validation reports (Phase 3)
# ---------------------------------------------------------------------------


@public_api(since="0.3.0", experimental=True)
@dataclass(slots=True)
class CaseOutcomeComparison:
    """Before/after score comparison for a single case.

    Attributes:
        case_id: The case identifier.
        before_score: Overall score before the change.
        after_score: Overall score after the change.
        delta: Score difference (after - before).
        status: ``"improved"``, ``"regressed"``, or ``"unchanged"``.
    """

    case_id: str
    before_score: float
    after_score: float
    delta: float
    status: str  # "improved", "regressed", "unchanged"


@public_api(since="0.3.0", experimental=True)
def compare_case_outcomes(
    failing_cases: list[EvalCase],
    before_scores: dict[str, float],
    after_scores: dict[str, float],
) -> list[CaseOutcomeComparison]:
    """Build a before/after comparison list from scores.

    Args:
        failing_cases: The cases tested.
        before_scores: Per-case or overall scores before the change.
        after_scores: Per-case or overall scores after the change.

    Returns:
        A list of ``CaseOutcomeComparison`` sorted by delta descending.
    """
    comparisons = []
    for case in failing_cases:
        before = before_scores.get(case.case_id, before_scores.get("overall", 0.0))
        after = after_scores.get(case.case_id, after_scores.get("overall", 0.0))
        delta = round(after - before, 4)
        if delta > 0.01:
            status = "improved"
        elif delta < -0.01:
            status = "regressed"
        else:
            status = "unchanged"
        comparisons.append(
            CaseOutcomeComparison(
                case_id=case.case_id,
                before_score=before,
                after_score=after,
                delta=delta,
                status=status,
            )
        )
    comparisons.sort(key=lambda c: c.delta, reverse=True)
    return comparisons


@public_api(since="0.3.0", experimental=True)
def format_validation_report(
    decision: ValidationDecision,
    comparisons: list[CaseOutcomeComparison] | None = None,
) -> str:
    """Produce a human-readable validation report.

    Args:
        decision: The validation decision.
        comparisons: Optional before/after case comparisons.

    Returns:
        A formatted multi-line string.
    """
    lines = [
        "Validation Report",
        "=================",
        f"Change: {decision.change_id}",
        f"Artifact: {decision.artifact_id}",
        f"Decision: {decision.decision} ({decision.reason})",
    ]

    if decision.before_scores:
        lines.append(f"Before scores: {decision.before_scores}")
    if decision.after_scores:
        lines.append(f"After scores: {decision.after_scores}")

    if comparisons:
        lines.append("")
        lines.append("Case Outcomes:")
        lines.append(f"  {'case_id':<16} {'before':>8} {'after':>8} {'delta':>8}   status")
        lines.append(f"  {'-'*16} {'-'*8} {'-'*8} {'-'*8}   {'-'*12}")
        for c in comparisons:
            sign = "+" if c.delta > 0 else ""
            lines.append(
                f"  {c.case_id:<16} {c.before_score:>8.2f} {c.after_score:>8.2f} "
                f"{sign}{c.delta:>7.2f}   {c.status}"
            )

    return "\n".join(lines)
