from __future__ import annotations

from dataclasses import dataclass

from autark.core.api import public_api


@public_api(since="0.2.0")
@dataclass(frozen=True, slots=True)
class RubricDimension:
    name: str
    weight: float
    description: str = ""


DEFAULT_AGENT_RUBRIC = [
    RubricDimension("task_success", 0.5, "The answer satisfies the task intent."),
    RubricDimension("answer_quality", 0.3, "The answer is useful, correct, and concise."),
    RubricDimension("constraint_satisfaction", 0.2, "The answer follows explicit constraints."),
]

DEFAULT_FAILURE_CATEGORIES = {
    "wrong_answer",
    "missing_constraint",
    "format_error",
    "empty_output",
    "execution_error",
    "capability_gap",
    "prompt_ambiguous",
    "none",
}
