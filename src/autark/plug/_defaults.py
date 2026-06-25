"""Default strategies and factory helpers for the plug-and-play API.

These are internal implementation details used by ``evolve()``.
Third-party users should not import from this module directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autark.artifacts import InMemoryArtifactStore, FileArtifactStore
from autark.core.models import EvalCase, Strategy


# ---------------------------------------------------------------------------
# Default strategies — one per standard failure category
# ---------------------------------------------------------------------------

DEFAULT_STRATEGIES: list[Strategy] = [
    Strategy(
        strategy_id="plug_repair_wrong_answer",
        name="Repair wrong answer",
        category="repair",
        signals_match=["wrong_answer", "expected answer", "incorrect"],
        instructions=["Verify the answer against expectations before responding."],
        validation=["rerun failing case", "rerun holdout cases"],
    ),
    Strategy(
        strategy_id="plug_repair_missing_constraint",
        name="Repair missing constraint",
        category="repair",
        signals_match=["missing_constraint", "constraint", "violated"],
        instructions=["Follow all listed constraints explicitly before answering."],
        validation=["rerun constrained cases"],
    ),
    Strategy(
        strategy_id="plug_repair_format_error",
        name="Repair format error",
        category="repair",
        signals_match=["format_error", "json", "format", "output format"],
        instructions=["Enforce the required output format exactly."],
        validation=["rerun format-sensitive cases"],
    ),
    Strategy(
        strategy_id="plug_repair_empty_output",
        name="Repair empty output",
        category="repair",
        signals_match=["empty_output", "empty", "no output"],
        instructions=["Never return an empty answer. Always produce meaningful output."],
        validation=["rerun empty-input cases"],
    ),
    Strategy(
        strategy_id="plug_repair_execution_error",
        name="Repair execution error",
        category="repair",
        signals_match=["execution_error", "runtime error", "agent execution failed"],
        instructions=["Handle runtime errors gracefully and provide fallback behavior."],
        validation=["rerun error cases"],
    ),
    Strategy(
        strategy_id="plug_optimize_prompt_clarity",
        name="Optimize prompt clarity",
        category="optimize",
        signals_match=["prompt_ambiguous", "ambiguous", "unclear", "vague"],
        instructions=["Rewrite vague instructions as concrete, testable rules."],
        validation=["rerun ambiguous cases"],
    ),
    Strategy(
        strategy_id="plug_harden_boundary_case",
        name="Harden boundary case",
        category="harden",
        signals_match=["boundary_case", "edge_case", "edge case"],
        instructions=["Add guardrails for empty, malformed, or edge-case input."],
        validation=["rerun boundary cases"],
    ),
    Strategy(
        strategy_id="plug_innovate_capability_gap",
        name="Innovate capability gap",
        category="innovate",
        signals_match=["capability_gap", "missing capability", "cannot"],
        instructions=["Add new task capability while preserving existing behavior."],
        validation=["run new capability cases", "run regression cases"],
    ),
]


# ---------------------------------------------------------------------------
# CaseProvider factory
# ---------------------------------------------------------------------------

class _ListCaseProvider:
    """CaseProvider backed by an in-memory list."""

    def __init__(self, cases: list[EvalCase]) -> None:
        self._cases = cases

    def load_cases(self) -> list[EvalCase]:
        return list(self._cases)


class _JsonFileCaseProvider:
    """CaseProvider that reads from a JSON corpus file.

    Supports two formats:
      - ``{"artifact_id": "...", "cases": [...]}``
      - ``[...]`` (plain list)
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._default_artifact_id = "artifact.txt"

    def load_cases(self) -> list[EvalCase]:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [self._make_case(item, self._default_artifact_id) for item in data]
        artifact_id = data.get("artifact_id", self._default_artifact_id)
        items = data.get("cases", [])
        return [self._make_case(item, artifact_id) for item in items]

    @staticmethod
    def _make_case(item: dict[str, Any], default_artifact_id: str) -> EvalCase:
        return EvalCase(
            case_id=item["case_id"],
            input_text=item.get("input_text", ""),
            expected_output=item.get("expected_output", ""),
            metadata={
                "artifact_id": item.get("artifact_id", default_artifact_id),
                "constraints": item.get("constraints", []),
                **item.get("metadata", {}),
            },
        )


def _case_provider_from(source: list[EvalCase] | str | Path | None):
    """Return a CaseProvider from a list, path, or None.

    - ``list[EvalCase]`` → ``_ListCaseProvider``
    - ``str`` / ``Path`` → ``_JsonFileCaseProvider``
    - ``None`` → ``_ListCaseProvider([])`` (empty — no cases to evaluate)
    """
    if source is None:
        return _ListCaseProvider([])
    if isinstance(source, (str, Path)):
        return _JsonFileCaseProvider(Path(source))
    if isinstance(source, list):
        return _ListCaseProvider(source)
    raise TypeError(f"cases must be list[EvalCase], str, Path, or None; got {type(source).__name__}")


# ---------------------------------------------------------------------------
# ArtifactStore factory
# ---------------------------------------------------------------------------

def _artifact_store_from(source: str | Path | dict[str, str] | None):
    """Return an ArtifactStore from a path, dict, or None.

    - ``str`` / ``Path`` → ``FileArtifactStore(root)``
    - ``dict[str, str]`` → ``InMemoryArtifactStore(artifacts)``
    - ``None`` → ``InMemoryArtifactStore()`` (empty)
    """
    if source is None:
        return InMemoryArtifactStore()
    if isinstance(source, dict):
        return InMemoryArtifactStore(source)
    if isinstance(source, (str, Path)):
        return FileArtifactStore(Path(source))
    raise TypeError(f"artifacts must be str, Path, dict, or None; got {type(source).__name__}")
