from __future__ import annotations

import asyncio

from autark.core.models import CandidateChange, EvalCase
from autark.validation import (
    AllowedOperationGate,
    CompositeValidationGate,
    MaxChangeSizeGate,
    MetadataScoreValidationGate,
    compare_case_outcomes,
    format_validation_report,
)

# ---------------------------------------------------------------------------
# MetadataScoreValidationGate
# ---------------------------------------------------------------------------

def test_metadata_score_validation_gate_accepts_improving_change() -> None:
    gate = MetadataScoreValidationGate(min_improvement=0.05)
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="prompt.txt",
        operations=[],
        metadata={"before_scores": {"overall": 0.2}, "after_scores": {"overall": 0.8}},
    )
    decision = asyncio.run(gate.validate(change, [EvalCase(case_id="c1", input_text="x")], []))
    assert decision.decision == "accepted"


def test_metadata_score_validation_gate_rejects_no_improvement() -> None:
    gate = MetadataScoreValidationGate(min_improvement=0.05)
    change = CandidateChange(
        change_id="chg-2",
        artifact_id="p.txt",
        operations=[],
        metadata={"before_scores": {"overall": 0.5}, "after_scores": {"overall": 0.5}},
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "rejected"


def test_metadata_score_validation_gate_needs_watch_marginal() -> None:
    gate = MetadataScoreValidationGate(min_improvement=0.05)
    change = CandidateChange(
        change_id="chg-3",
        artifact_id="p.txt",
        operations=[],
        metadata={"before_scores": {"overall": 0.5}, "after_scores": {"overall": 0.51}},
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "needs_watch"


# ---------------------------------------------------------------------------
# CompositeValidationGate
# ---------------------------------------------------------------------------

def test_composite_gate_all_accept() -> None:
    gate = CompositeValidationGate([
        MaxChangeSizeGate(max_bytes=1000),
        AllowedOperationGate({"append"}),
    ])
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "append", "text": "test"}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "accepted"


def test_composite_gate_rejects_on_first_rejection() -> None:
    gate = CompositeValidationGate([
        AllowedOperationGate({"append"}),
        MaxChangeSizeGate(max_bytes=1),
    ])
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "replace", "text": "x", "old": "y"}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "rejected"


def test_composite_gate_needs_watch_aggregation() -> None:
    gate1 = MetadataScoreValidationGate(min_improvement=0.5)
    gate2 = AllowedOperationGate()
    gate = CompositeValidationGate([gate1, gate2])
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "append", "text": "test"}],
        metadata={"before_scores": {"overall": 0.5}, "after_scores": {"overall": 0.52}},
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "needs_watch"


# ---------------------------------------------------------------------------
# MaxChangeSizeGate
# ---------------------------------------------------------------------------

def test_max_change_size_gate_rejects_large() -> None:
    gate = MaxChangeSizeGate(max_bytes=5)
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "append", "text": "this is too long"}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "rejected"


def test_max_change_size_gate_accepts_small() -> None:
    gate = MaxChangeSizeGate(max_bytes=100)
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "append", "text": "ok"}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "accepted"


# ---------------------------------------------------------------------------
# AllowedOperationGate
# ---------------------------------------------------------------------------

def test_allowed_operation_rejects_disallowed() -> None:
    gate = AllowedOperationGate({"append"})
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "delete", "text": ""}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "rejected"


def test_allowed_operation_accepts_allowed() -> None:
    gate = AllowedOperationGate({"append", "replace"})
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="a",
        operations=[{"operation": "replace", "old": "a", "new": "b"}],
    )
    decision = asyncio.run(gate.validate(change, [], []))
    assert decision.decision == "accepted"


# ---------------------------------------------------------------------------
# Case outcome comparisons and validation reports
# ---------------------------------------------------------------------------

def test_compare_case_outcomes():
    cases = [
        EvalCase(case_id="c1", input_text=""),
        EvalCase(case_id="c2", input_text=""),
    ]
    before = {"c1": 0.3, "c2": 0.8}
    after = {"c1": 0.9, "c2": 0.75}

    results = compare_case_outcomes(cases, before, after)
    assert len(results) == 2

    improved = [c for c in results if c.case_id == "c1"][0]
    assert improved.status == "improved"
    assert improved.delta == round(0.9 - 0.3, 4)

    regressed = [c for c in results if c.case_id == "c2"][0]
    assert regressed.status == "regressed"
    assert regressed.delta == round(0.75 - 0.8, 4)


def test_compare_case_outcomes_unchanged():
    cases = [EvalCase(case_id="c1", input_text="")]
    before = {"c1": 0.5}
    after = {"c1": 0.505}
    results = compare_case_outcomes(cases, before, after)
    assert results[0].status == "unchanged"


def test_compare_case_outcomes_fallback_to_overall():
    cases = [EvalCase(case_id="c1", input_text="")]
    before = {"overall": 0.3}
    after = {"overall": 0.9}
    results = compare_case_outcomes(cases, before, after)
    assert results[0].delta == 0.6


def test_format_validation_report():
    from autark.core.models import ValidationDecision
    decision = ValidationDecision(
        decision="accepted",
        change_id="chg-1",
        artifact_id="prompt.txt",
        before_scores={"overall": 0.3},
        after_scores={"overall": 0.9},
        reason="Score improved 0.30 -> 0.90",
    )
    comparisons = compare_case_outcomes(
        [EvalCase(case_id="c1", input_text="")],
        {"overall": 0.3},
        {"overall": 0.9},
    )
    report = format_validation_report(decision, comparisons)
    assert "Validation Report" in report
    assert "accepted" in report
    assert "c1" in report
    assert "improved" in report
