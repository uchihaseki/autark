from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EvalCase:
    case_id: str
    input_text: str
    expected_output: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunResult:
    case_id: str
    artifact_id: str
    status: str
    output: str = ""
    trajectory: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvalResult:
    case_id: str
    artifact_id: str
    status: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    failure_category: str = ""
    evidence: str = ""
    trajectory_summary: str = ""
    grade: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Signal:
    signal_id: str
    case_id: str
    artifact_id: str
    signal_type: str
    category: str
    evidence: str
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Strategy:
    strategy_id: str
    name: str
    category: str
    signals_match: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    validation: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactSnapshot:
    artifact_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvolutionContext:
    cycle_id: str
    failing_cases: list[EvalCase] = field(default_factory=list)
    holdout_cases: list[EvalCase] = field(default_factory=list)
    eval_results: list[EvalResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateChange:
    change_id: str
    artifact_id: str
    operations: list[dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    validation_plan: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactRevision:
    revision_id: str
    artifact_id: str
    status: str
    before_snapshot: str = ""
    after_snapshot: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationDecision:
    decision: str
    change_id: str
    artifact_id: str
    before_scores: dict[str, float] = field(default_factory=dict)
    after_scores: dict[str, float] = field(default_factory=dict)
    regression_results: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvalReport:
    cycle_id: str
    adapter_name: str
    total_cases: int
    failures: int
    signals_extracted: int
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CycleReport:
    cycle_id: str
    adapter_name: str
    total_cases: int
    failures: int
    signals_extracted: int
    strategies_selected: int
    changes_accepted: int
    changes_rejected: int
    artifacts_modified: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
