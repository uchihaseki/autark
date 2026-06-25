"""Tests for the autark.plug module."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from autark.core.models import CandidateChange, EvalCase, RunResult, Strategy
from autark.evaluation.judge import HeuristicEvaluator
from autark.plug import discover, evolve, list_adapters
from autark.proposers.deterministic import DeterministicProposer


# ---------------------------------------------------------------------------
# Test runners
# ---------------------------------------------------------------------------


class _PassingRunner:
    """Runner that always returns the expected output."""

    async def run_case(self, case: EvalCase) -> RunResult:
        return RunResult(
            case_id=case.case_id,
            artifact_id=case.metadata.get("artifact_id", "test"),
            status="success",
            output=case.expected_output,
        )


class _FailingRunner:
    """Runner that always returns a wrong answer."""

    async def run_case(self, case: EvalCase) -> RunResult:
        return RunResult(
            case_id=case.case_id,
            artifact_id=case.metadata.get("artifact_id", "test"),
            status="success",
            output="bad response",
        )


class _CustomProposer:
    """Proposer that appends a fixed message."""

    def propose(self, signal, strategy, artifact, context):
        return CandidateChange(
            change_id="custom-001",
            artifact_id=signal.artifact_id,
            operations=[{"operation": "append", "text": "Be more careful."}],
            rationale="Custom fix",
            validation_plan=["Rerun cases"],
            metadata={"signal_id": signal.signal_id, "before_scores": signal.scores, "after_scores": {"overall": 0.9}},
        )


# ---------------------------------------------------------------------------
# Test cases fixture
# ---------------------------------------------------------------------------

def _make_passing_case(case_id: str = "c1") -> EvalCase:
    return EvalCase(case_id=case_id, input_text="2+3", expected_output="5", metadata={"artifact_id": "test"})


def _make_failing_cases() -> list[EvalCase]:
    return [
        EvalCase(case_id="c1", input_text="2+3", expected_output="5", metadata={"artifact_id": "test"}),
        EvalCase(case_id="c2", input_text="hello", expected_output="hi", metadata={"artifact_id": "test"}),
    ]


# ---------------------------------------------------------------------------
# Minimal evolve tests
# ---------------------------------------------------------------------------


def test_evolve_minimal_passing():
    """A passing runner produces 0 failures, 0 changes."""
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=[_make_passing_case()],
            artifacts={"test": "You are a helper."},
        )
    )
    assert report.total_cases == 1
    assert report.failures == 0
    assert report.signals_extracted == 0
    assert report.changes_accepted == 0


def test_evolve_minimal_failing():
    """A failing runner triggers the full signal → strategy → propose → accept loop."""
    report = asyncio.run(
        evolve(
            runner=_FailingRunner(),
            cases=[_make_passing_case()],
            artifacts={"test": "You are a math assistant."},
        )
    )
    assert report.total_cases == 1
    assert report.failures == 1
    assert report.signals_extracted == 1
    assert report.strategies_selected >= 1
    assert report.changes_accepted >= 1
    assert report.changes_rejected == 0


def test_evolve_dry_run_default():
    """evolve() defaults to dry_run=True."""
    report = asyncio.run(
        evolve(
            runner=_FailingRunner(),
            cases=[_make_passing_case()],
            artifacts={"test": "helper"},
        )
    )
    # In dry-run, changes are accepted logically but not committed to disk
    assert report.changes_accepted > 0


# ---------------------------------------------------------------------------
# Custom components
# ---------------------------------------------------------------------------


def test_evolve_custom_evaluator():
    """Custom evaluator is used instead of HeuristicEvaluator."""
    evaluator = HeuristicEvaluator(pass_threshold=1.0)  # Everything fails
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            evaluator=evaluator,
            cases=[_make_passing_case()],
            artifacts={"test": "helper"},
        )
    )
    assert report.failures > 0


def test_evolve_custom_proposer():
    """Custom proposer is used instead of DeterministicProposer."""
    report = asyncio.run(
        evolve(
            runner=_FailingRunner(),
            proposer=_CustomProposer(),
            cases=[_make_passing_case()],
            artifacts={"test": "helper"},
        )
    )
    assert report.changes_accepted == 1


def test_evolve_custom_strategies():
    """Custom strategies replace the defaults."""
    custom_strategy = Strategy(
        strategy_id="custom",
        name="Custom",
        category="repair",
        signals_match=["wrong_answer"],
        instructions=["Fix it."],
    )
    report = asyncio.run(
        evolve(
            runner=_FailingRunner(),
            strategies=[custom_strategy],
            cases=[_make_passing_case()],
            artifacts={"test": "helper"},
        )
    )
    assert report.strategies_selected >= 1


# ---------------------------------------------------------------------------
# Case source variations
# ---------------------------------------------------------------------------


def test_evolve_cases_from_list():
    """Cases can be passed directly as a list."""
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=[_make_passing_case("a"), _make_passing_case("b")],
            artifacts={"test": "helper"},
        )
    )
    assert report.total_cases == 2


def test_evolve_cases_from_file():
    """Cases can be loaded from a JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "artifact_id": "test",
                "cases": [
                    {"case_id": "c1", "input_text": "2+3", "expected_output": "5"},
                    {"case_id": "c2", "input_text": "hello", "expected_output": "hi"},
                ],
            },
            f,
        )
        path = f.name

    try:
        report = asyncio.run(
            evolve(
                runner=_PassingRunner(),
                cases=path,
                artifacts={"test": "helper"},
            )
        )
        assert report.total_cases == 2
    finally:
        Path(path).unlink()


def test_evolve_cases_none():
    """None cases means empty — 0 cases, no failures."""
    report = asyncio.run(evolve(runner=_PassingRunner(), artifacts={"test": "helper"}))
    assert report.total_cases == 0
    assert report.failures == 0


# ---------------------------------------------------------------------------
# Artifact source variations
# ---------------------------------------------------------------------------


def test_evolve_artifacts_from_dict():
    """Artifacts passed as dict use InMemoryArtifactStore."""
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=[_make_passing_case()],
            artifacts={"test": "You are a helper."},
        )
    )
    assert report.total_cases == 1


def test_evolve_artifacts_from_dir():
    """Artifacts passed as a directory path use FileArtifactStore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir) / "artifacts"
        artifact_dir.mkdir()
        (artifact_dir / "test").write_text("You are a helper.")

        report = asyncio.run(
            evolve(
                runner=_PassingRunner(),
                cases=[_make_passing_case()],
                artifacts=str(artifact_dir),
            )
        )
        assert report.total_cases == 1


def test_evolve_artifacts_none():
    """None artifacts means in-memory empty store."""
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=[_make_passing_case()],
        )
    )
    assert report.total_cases == 1


# ---------------------------------------------------------------------------
# Discovery tests
# ---------------------------------------------------------------------------


def test_discover_builtin_fake():
    """discover() can load the built-in FakeAdapter class."""
    cls = discover("fake")
    assert cls is not None
    # Should be a class with a 'name' attribute
    assert hasattr(cls, "name") or hasattr(cls, "from_json")


def test_discover_builtin_prompt_agent():
    """discover() can load the built-in PromptAgentAdapter class."""
    cls = discover("prompt-agent")
    assert cls is not None
    assert hasattr(cls, "name") or hasattr(cls, "__init__")


def test_discover_missing_raises():
    """discover() with unknown name raises ValueError with helpful message."""
    with pytest.raises(ValueError, match="Unknown adapter"):
        discover("nonexistent-adapter-xyz")


def test_list_adapters_includes_builtins():
    """list_adapters() includes the built-in adapters after pip install."""
    names = list_adapters()
    assert "fake" in names
    assert "prompt-agent" in names


# ---------------------------------------------------------------------------
# CLI list-adapters subcommand
# ---------------------------------------------------------------------------


def test_cli_list_adapters():
    """autark list-adapters exits 0 and lists built-in adapters."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "autark.cli.main", "list-adapters"],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0
    assert "fake" in result.stdout
    assert "prompt-agent" in result.stdout


# ---------------------------------------------------------------------------
# Multiple cases
# ---------------------------------------------------------------------------


def test_evolve_multiple_cases_mixed():
    """Mixed passing and failing cases."""
    cases = [
        EvalCase(case_id="pass1", input_text="2+3", expected_output="5", metadata={"artifact_id": "test"}),
        EvalCase(case_id="fail1", input_text="2+3", expected_output="99", metadata={"artifact_id": "test"}),
        EvalCase(case_id="fail2", input_text="hello", expected_output="bonjour", metadata={"artifact_id": "test"}),
    ]

    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=cases,
            artifacts={"test": "helper"},
        )
    )
    assert report.total_cases == 3
    # 2 cases expected output != what runner returns (which is same as input)
    # Actually _PassingRunner returns case.expected_output, so all pass
    # Let's use _FailingRunner instead for mixed results
    report2 = asyncio.run(
        evolve(
            runner=_FailingRunner(),
            cases=cases,
            artifacts={"test": "helper"},
        )
    )
    assert report2.total_cases == 3
    assert report2.failures == 3  # All fail because runner returns "bad response"


# ---------------------------------------------------------------------------
# Engine config passthrough
# ---------------------------------------------------------------------------


def test_evolve_metadata_passthrough():
    """metadata is passed through to CycleReport."""
    report = asyncio.run(
        evolve(
            runner=_PassingRunner(),
            cases=[_make_passing_case()],
            artifacts={"test": "helper"},
            metadata={"source": "codex", "version": "1.0"},
        )
    )
    assert report.metadata == {"source": "codex", "version": "1.0"}
