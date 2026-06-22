from __future__ import annotations

import asyncio

from autark.core.models import CandidateChange, EvalCase
from autark.validation import MetadataScoreValidationGate


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
