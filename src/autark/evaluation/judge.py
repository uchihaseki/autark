from __future__ import annotations

import json as _json
from collections.abc import Awaitable, Callable

from autark.core.api import public_api
from autark.core.models import EvalCase, EvalResult, RunResult
from autark.evaluation.metrics import grade_from_score, weighted_overall
from autark.evaluation.rubrics import DEFAULT_AGENT_RUBRIC, RubricDimension


@public_api(since="0.2.0")
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


# ---------------------------------------------------------------------------
# Additional evaluators
# ---------------------------------------------------------------------------


@public_api(since="0.3.0", experimental=True)
class ExactMatchEvaluator:
    """Evaluator that checks for exact string match between output and expected.

    Args:
        pass_threshold: Score at or above which the case is considered passing.
        ignore_case: If True, compare case-insensitively.
        ignore_whitespace: If True, strip leading/trailing whitespace before comparing.
    """

    def __init__(
        self,
        pass_threshold: float = 0.5,
        ignore_case: bool = True,
        ignore_whitespace: bool = True,
    ) -> None:
        self.pass_threshold = pass_threshold
        self.ignore_case = ignore_case
        self.ignore_whitespace = ignore_whitespace

    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        if run_result.status == "error":
            return EvalResult(
                case_id=case.case_id,
                artifact_id=run_result.artifact_id,
                status="fail",
                scores={"exact_match": 0.0, "overall": 0.0},
                failure_category="execution_error",
                evidence=run_result.trajectory or "agent execution failed",
                trajectory_summary=run_result.trajectory,
                grade="C",
            )

        expected = case.expected_output
        actual = run_result.output
        if self.ignore_case:
            expected = expected.lower()
            actual = actual.lower()
        if self.ignore_whitespace:
            expected = expected.strip()
            actual = actual.strip()

        score = 1.0 if expected == actual else 0.0
        status = "pass" if score >= self.pass_threshold else "fail"
        failure_category = "none" if status == "pass" else "wrong_answer"

        return EvalResult(
            case_id=case.case_id,
            artifact_id=run_result.artifact_id,
            status=status,
            scores={"exact_match": score, "overall": score},
            failure_category=failure_category,
            evidence="" if status == "pass" else f"Expected {expected!r}, got {actual!r}",
            trajectory_summary=run_result.trajectory,
            grade=grade_from_score(score),
        )


@public_api(since="0.3.0", experimental=True)
class RubricEvaluator:
    """Evaluator that scores output against a list of RubricDimensions.

    Args:
        dimensions: List of rubric dimensions to score against.
        score_fn: Optional custom scoring function. Defaults to substring-match.
        pass_threshold: Overall score threshold for pass/fail.
    """

    def __init__(
        self,
        dimensions: list[RubricDimension],
        score_fn: Callable[[RubricDimension, str, str], float] | None = None,
        pass_threshold: float = 0.5,
    ) -> None:
        self.dimensions = dimensions
        self.score_fn = score_fn or self._default_score_fn
        self.pass_threshold = pass_threshold

    @staticmethod
    def _default_score_fn(dim: RubricDimension, output: str, expected: str) -> float:
        if not expected:
            return 1.0 if output else 0.0
        return 1.0 if expected.strip().lower() in output.strip().lower() else 0.0

    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        if run_result.status == "error":
            return EvalResult(
                case_id=case.case_id,
                artifact_id=run_result.artifact_id,
                status="fail",
                scores={"overall": 0.0},
                failure_category="execution_error",
                evidence=run_result.trajectory or "agent execution failed",
                trajectory_summary=run_result.trajectory,
                grade="C",
            )

        scores = {}
        for dim in self.dimensions:
            scores[dim.name] = self.score_fn(dim, run_result.output, case.expected_output)

        weights = {d.name: d.weight for d in self.dimensions}
        scores["overall"] = weighted_overall(scores, weights)
        status = "pass" if scores["overall"] >= self.pass_threshold else "fail"

        # Determine primary failure category from the lowest-scoring dimension
        failure_category = "none"
        if status == "fail":
            if not run_result.output:
                failure_category = "empty_output"
            else:
                worst_dim = min(self.dimensions, key=lambda d: scores.get(d.name, 0.0))
                worst_score = scores.get(worst_dim.name, 0.0)
                failure_category = "missing_constraint" if worst_score < 0.5 else "wrong_answer"

        return EvalResult(
            case_id=case.case_id,
            artifact_id=run_result.artifact_id,
            status=status,
            scores=scores,
            failure_category=failure_category,
            evidence="" if status == "pass" else f"Lowest dimension: {failure_category}",
            trajectory_summary=run_result.trajectory,
            grade=grade_from_score(scores["overall"]),
        )


# ---------------------------------------------------------------------------
# Custom / LLM evaluators
# ---------------------------------------------------------------------------


@public_api(since="0.3.0", experimental=True)
class PythonCallbackEvaluator:
    """Evaluator that wraps a user-provided async callback function.

    Args:
        callback: An async function ``(EvalCase, RunResult) -> dict[str, float]``.
        pass_threshold: Overall score threshold for pass/fail.
    """

    def __init__(
        self,
        callback: Callable[[EvalCase, RunResult], Awaitable[dict[str, float]]],
        pass_threshold: float = 0.5,
    ) -> None:
        self.callback = callback
        self.pass_threshold = pass_threshold

    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        scores = await self.callback(case, run_result)
        overall = scores.get("overall", sum(scores.values()) / max(len(scores), 1))
        scores.setdefault("overall", overall)
        status = "pass" if overall >= self.pass_threshold else "fail"
        failure_category = "none" if status == "pass" else "prompt_ambiguous"

        return EvalResult(
            case_id=case.case_id,
            artifact_id=run_result.artifact_id,
            status=status,
            scores=scores,
            failure_category=failure_category,
            evidence="" if status == "pass" else f"Scores: {scores}",
            trajectory_summary=run_result.trajectory,
            grade=grade_from_score(overall),
        )


@public_api(since="0.3.0", experimental=True)
class LLMJudgeEvaluator:
    """Evaluator that uses an LLM (Claude) to judge output quality against a rubric.

    Requires ``pip install autark[anthropic]``.

    Args:
        model: Anthropic model ID to use for judging.
        max_tokens: Maximum tokens in the judge response.
        api_key: Anthropic API key. Defaults to ``ANTHROPIC_API_KEY`` env var.
        rubric: List of rubric dimensions. Defaults to ``DEFAULT_AGENT_RUBRIC``.
        pass_threshold: Overall score threshold for pass/fail.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 256,
        api_key: str | None = None,
        rubric: list[RubricDimension] | None = None,
        pass_threshold: float = 0.5,
    ) -> None:
        try:
            import anthropic as _anthropic  # noqa: F401
        except ImportError:
            raise ImportError(
                "LLMJudgeEvaluator requires the 'anthropic' package. "
                "Install with: pip install autark[anthropic]"
            )
        self.model = model
        self.max_tokens = max_tokens
        self.client = _make_client(api_key)
        self.rubric = rubric or list(DEFAULT_AGENT_RUBRIC)
        self.pass_threshold = pass_threshold

    def _build_judge_prompt(self, case: EvalCase, run_result: RunResult) -> str:
        dims_text = "\n".join(
            f"- {d.name} (weight={d.weight}): {d.description}" for d in self.rubric
        )
        prompt = (
            "You are an evaluation judge. Score the agent's output against the rubric.\n\n"
            "## Rubric\n"
            f"{dims_text}\n\n"
            "## Task Input\n"
            f"{case.input_text}\n\n"
            "## Expected Output\n"
            f"{case.expected_output}\n\n"
            "## Agent Output\n"
            f"{run_result.output}\n\n"
            "## Instructions\n"
            "For each rubric dimension, assign a score from 0.0 to 1.0. "
            "Return ONLY a JSON object (no markdown, no extra text) with dimension "
            "names as keys and float scores as values."
        )
        return prompt

    def _parse_scores(self, raw: str) -> dict[str, float]:
        """Extract JSON scores from LLM response, handling markdown fences."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return _json.loads(text)
        except _json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return _json.loads(match.group(0))
            raise RuntimeError(
                f"LLMJudgeEvaluator could not parse JSON scores. Response: {raw[:500]}"
            )

    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        prompt = self._build_judge_prompt(case, run_result)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        scores = self._parse_scores(response.content[0].text)
        weights = {d.name: d.weight for d in self.rubric}
        scores["overall"] = weighted_overall(scores, weights)
        status = "pass" if scores["overall"] >= self.pass_threshold else "fail"

        failure_category = "none"
        if status == "fail":
            worst_dim = min(
                (d for d in self.rubric if d.name in scores),
                key=lambda d: scores.get(d.name, 0.0),
                default=None,
            )
            if worst_dim:
                failure_category = (
                    "missing_constraint"
                    if scores.get(worst_dim.name, 0.0) < 0.5
                    else "wrong_answer"
                )

        return EvalResult(
            case_id=case.case_id,
            artifact_id=run_result.artifact_id,
            status=status,
            scores=scores,
            failure_category=failure_category,
            evidence="" if status == "pass" else f"LLM judge scores: {scores}",
            trajectory_summary=run_result.trajectory,
            grade=grade_from_score(scores["overall"]),
        )


def _make_client(api_key: str | None = None):
    import anthropic
    return anthropic.Anthropic(api_key=api_key)
