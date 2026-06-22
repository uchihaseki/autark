from __future__ import annotations

from autark.core.models import EvalCase, EvalResult, RunResult
from autark.evaluation.metrics import grade_from_score, weighted_overall


class HeuristicEvaluator:
    def __init__(self, pass_threshold: float = 0.5) -> None:
        self.pass_threshold = pass_threshold

    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        expected = case.expected_output.strip().lower()
        output = run_result.output.strip().lower()
        constraints = [str(item).lower() for item in case.metadata.get("constraints", [])]

        if run_result.status == "error":
            return EvalResult(
                case_id=case.case_id,
                artifact_id=run_result.artifact_id,
                status="fail",
                scores={"task_success": 0.0, "answer_quality": 0.0, "constraint_satisfaction": 0.0, "overall": 0.0},
                failure_category="execution_error",
                evidence=run_result.trajectory or "agent execution failed",
                trajectory_summary=run_result.trajectory,
                grade="C",
            )

        if not output:
            return EvalResult(
                case_id=case.case_id,
                artifact_id=run_result.artifact_id,
                status="fail",
                scores={"task_success": 0.0, "answer_quality": 0.0, "constraint_satisfaction": 0.0, "overall": 0.0},
                failure_category="empty_output",
                evidence="agent returned empty output",
                trajectory_summary=run_result.trajectory,
                grade="C",
            )

        task_success = 1.0 if expected and expected in output else (0.7 if not expected and output else 0.0)
        answer_quality = 0.8 if output else 0.0
        constraint_satisfaction = 1.0 if _constraints_satisfied(output, constraints) else 0.0
        scores = {
            "task_success": task_success,
            "answer_quality": answer_quality,
            "constraint_satisfaction": constraint_satisfaction,
        }
        scores["overall"] = weighted_overall(
            scores,
            {"task_success": 0.5, "answer_quality": 0.3, "constraint_satisfaction": 0.2},
        )
        status = "pass" if scores["overall"] >= self.pass_threshold else "fail"
        failure_category = _failure_category(status, task_success, constraint_satisfaction, output)

        return EvalResult(
            case_id=case.case_id,
            artifact_id=run_result.artifact_id,
            status=status,
            scores=scores,
            failure_category=failure_category,
            evidence="" if status == "pass" else _evidence_for(failure_category),
            trajectory_summary=run_result.trajectory,
            grade=grade_from_score(scores["overall"]),
        )


def _constraints_satisfied(output: str, constraints: list[str]) -> bool:
    if not constraints:
        return True
    for constraint in constraints:
        if "answer directly" in constraint and len(output.split()) > 8:
            return False
        if "json" in constraint and not output.strip().startswith("{"):
            return False
    return True


def _failure_category(status: str, task_success: float, constraint_satisfaction: float, output: str) -> str:
    if status == "pass":
        return "none"
    if not output:
        return "empty_output"
    if constraint_satisfaction < 1.0:
        return "missing_constraint"
    if task_success < 0.5:
        return "wrong_answer"
    return "prompt_ambiguous"


def _evidence_for(category: str) -> str:
    return {
        "wrong_answer": "expected answer was not found in agent response",
        "missing_constraint": "agent response violated an explicit case constraint",
        "format_error": "agent response did not use the required output format",
        "empty_output": "agent returned empty output",
        "execution_error": "agent execution failed",
        "prompt_ambiguous": "prompt likely underspecified the desired behavior",
    }.get(category, "evaluation failed")
