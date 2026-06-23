from __future__ import annotations

import json
import sys

import pytest

from autark.core.models import (
    ArtifactSnapshot,
    EvalCase,
    EvalResult,
    EvolutionContext,
    Signal,
    Strategy,
)
from autark.proposers import ClaudeCodeProposer, DeterministicProposer, ExternalCommandProposer


def _make_signal() -> Signal:
    return Signal(
        signal_id="sig-1",
        case_id="case-1",
        artifact_id="prompt.txt",
        signal_type="failure",
        category="wrong_answer",
        evidence="Expected 4, got 5.",
        scores={"overall": 0.2},
    )


def _make_strategy() -> Strategy:
    return Strategy(
        strategy_id="strat-1",
        name="Repair wrong answer",
        category="repair",
        signals_match=["wrong_answer"],
        instructions=["Compute and verify correct answer before responding."],
        validation=["Rerun failing cases, check holdout regression."],
    )


def _make_artifact() -> ArtifactSnapshot:
    return ArtifactSnapshot(
        artifact_id="prompt.txt",
        content="You are a helpful assistant. Answer concisely.",
    )


def _make_context() -> EvolutionContext:
    return EvolutionContext(
        cycle_id="cycle-test",
        failing_cases=[
            EvalCase(case_id="case-1", input_text="What is 2+2?", expected_output="4"),
        ],
        holdout_cases=[
            EvalCase(case_id="case-2", input_text="What is 3+3?", expected_output="6"),
        ],
        eval_results=[
            EvalResult(
                case_id="case-1",
                artifact_id="prompt.txt",
                status="fail",
                scores={"overall": 0.2},
                failure_category="wrong_answer",
                evidence="Expected 4, got 5.",
            ),
        ],
    )


# ---- DeterministicProposer ----

def test_deterministic_proposer_returns_change() -> None:
    proposer = DeterministicProposer()
    change = proposer.propose(_make_signal(), _make_strategy(), _make_artifact(), _make_context())

    assert change.change_id.startswith("chg-")
    assert change.artifact_id == "prompt.txt"
    assert len(change.operations) == 1
    assert change.operations[0]["operation"] == "append"
    assert "deterministic" in change.rationale


def test_deterministic_proposer_different_categories() -> None:
    proposer = DeterministicProposer()

    for category in ["wrong_answer", "missing_constraint", "format_error", "empty_output", "prompt_ambiguous", "unknown"]:
        signal = _make_signal()
        object.__setattr__(signal, "category", category)
        change = proposer.propose(signal, _make_strategy(), _make_artifact(), _make_context())
        assert len(change.operations) >= 1


# ---- ExternalCommandProposer ----

def test_external_command_proposer_json_contract(tmp_path) -> None:
    """Simulate an external proposer via a Python script."""
    script = tmp_path / "proposer.py"
    script.write_text("""
import json, sys
payload = json.load(sys.stdin)
change = {
    "artifact_id": payload["signal"]["artifact_id"],
    "operations": [{"operation": "append", "text": "Be more accurate."}],
    "rationale": "test",
    "validation_plan": payload["strategy"].get("validation", []),
    "metadata": {"source": "test-script"},
}
print(json.dumps(change))
""")
    proposer = ExternalCommandProposer(f"{sys.executable} {script}", timeout=10)
    change = proposer.propose(_make_signal(), _make_strategy(), _make_artifact(), _make_context())

    assert change.artifact_id == "prompt.txt"
    assert change.operations[0]["text"] == "Be more accurate."
    assert change.rationale == "test"


# ---- ClaudeCodeProposer (prompt building, no CLI needed) ----

def test_claude_code_proposer_builds_prompt() -> None:
    proposer = ClaudeCodeProposer()
    prompt = proposer._build_prompt(_make_signal(), _make_strategy(), _make_artifact(), _make_context())

    assert "wrong_answer" in prompt
    assert "Repair wrong answer" in prompt
    assert "You are a helpful assistant" in prompt
    assert "case-1" in prompt
    assert "case-2" in prompt
    assert "Expected 4, got 5" in prompt
    assert '"operation"' in prompt
    assert "signal_id" in prompt


def test_claude_code_proposer_prompt_contains_json_schema() -> None:
    proposer = ClaudeCodeProposer()
    prompt = proposer._build_prompt(_make_signal(), _make_strategy(), _make_artifact(), _make_context())

    assert "Required JSON Output" in prompt or "JSON" in prompt
    assert "change_id" in prompt
    assert "artifact_id" in prompt
    assert "operations" in prompt
    assert "rationale" in prompt


def test_claude_code_proposer_missing_cli_raises() -> None:
    """When the CLI binary does not exist, propose() should raise RuntimeError."""
    proposer = ClaudeCodeProposer(claude_command="nonexistent-claude-cli-xyz", timeout=2)

    with pytest.raises(RuntimeError, match="Claude CLI not found"):
        proposer.propose(_make_signal(), _make_strategy(), _make_artifact(), _make_context())


def test_claude_code_proposer_cases_text_truncation() -> None:
    """Long case lists should be truncated at max_items."""
    proposer = ClaudeCodeProposer()
    many_cases = [
        EvalCase(case_id=f"case-{i}", input_text=f"Input {i}" * 50, expected_output=f"Output {i}")
        for i in range(10)
    ]
    text = proposer._cases_text(many_cases, "Test Cases", max_items=3)

    assert "case-0" in text
    assert "case-1" in text
    assert "case-2" in text
    assert "case-9" not in text
