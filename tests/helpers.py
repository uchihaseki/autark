"""Reusable test helpers for third-party AUTARK adapters.

Usage::

    from tests.helpers import AdapterTestSuite

    class TestMyAdapter(AdapterTestSuite):
        def create_adapter(self, tmp_path):
            from my_adapter import MyAdapter
            return MyAdapter(output_dir=str(tmp_path))
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from autark.core.engine import EngineConfig, EvolutionEngine
from autark.core.models import (
    ArtifactSnapshot,
    CandidateChange,
    EvalCase,
    EvalResult,
    EvolutionContext,
    RunResult,
    Signal,
    Strategy,
    ValidationDecision,
)
from autark.core.protocols import Adapter


class AdapterTestSuite:
    """Base class for adapter integration tests.

    Subclasses must implement ``create_adapter(tmp_path) -> Adapter``.
    Each ``test_*`` method verifies one component or the full cycle.
    """

    # ------------------------------------------------------------------
    # Subclass responsibility
    # ------------------------------------------------------------------

    def create_adapter(self, tmp_path: Path) -> Adapter:
        raise NotImplementedError(
            "Subclasses must implement create_adapter(self, tmp_path) -> Adapter"
        )

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_eval_case(
        case_id: str = "case-001",
        input_text: str = "test input",
        expected_output: str = "test expected",
    ) -> EvalCase:
        return EvalCase(case_id=case_id, input_text=input_text, expected_output=expected_output)

    @staticmethod
    def _make_signal(
        signal_id: str = "sig-001",
        case_id: str = "case-001",
        artifact_id: str = "artifact.txt",
        category: str = "wrong_answer",
    ) -> Signal:
        return Signal(
            signal_id=signal_id,
            case_id=case_id,
            artifact_id=artifact_id,
            signal_type="repair",
            category=category,
            evidence="Test evidence",
            scores={"overall": 0.3},
        )

    @staticmethod
    def _make_strategy(
        strategy_id: str = "strat-001",
        name: str = "Test Strategy",
    ) -> Strategy:
        return Strategy(
            strategy_id=strategy_id,
            name=name,
            category="repair",
            signals_match=["repair", "wrong_answer"],
            instructions=["Fix the issue."],
            validation=["Rerun cases."],
        )

    @staticmethod
    def _make_candidate_change(
        change_id: str = "chg-001",
        artifact_id: str = "artifact.txt",
    ) -> CandidateChange:
        return CandidateChange(
            change_id=change_id,
            artifact_id=artifact_id,
            operations=[{"operation": "append", "text": "Be more careful."}],
            rationale="Test change",
            validation_plan=["Rerun cases"],
            metadata={"before_scores": {"overall": 0.3}, "after_scores": {"overall": 0.8}},
        )

    # ------------------------------------------------------------------
    # Component tests
    # ------------------------------------------------------------------

    def test_adapter_has_name(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        assert isinstance(adapter.name, str)
        assert len(adapter.name) > 0

    def test_case_provider_returns_list(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        provider = adapter.case_provider()
        cases = provider.load_cases()
        assert isinstance(cases, list)
        if cases:
            assert isinstance(cases[0], EvalCase)

    def test_agent_runner_returns_run_result(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        runner = adapter.agent_runner()
        case = self._make_eval_case()
        run_result = asyncio.run(runner.run_case(case))
        assert isinstance(run_result, RunResult)
        assert run_result.case_id == case.case_id

    def test_evaluator_returns_eval_result(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        evaluator = adapter.evaluator()
        case = self._make_eval_case()
        run_result = RunResult(case_id=case.case_id, artifact_id="test", status="ok", output=case.expected_output)
        eval_result = asyncio.run(evaluator.evaluate(case, run_result))
        assert isinstance(eval_result, EvalResult)
        assert eval_result.case_id == case.case_id

    def test_signal_extractor_returns_signals(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        extractor = adapter.signal_extractor()
        eval_result = EvalResult(
            case_id="c1", artifact_id="a1", status="fail",
            scores={"overall": 0.2}, failure_category="wrong_answer",
        )
        signals = extractor.extract([eval_result])
        assert isinstance(signals, list)
        if signals:
            assert isinstance(signals[0], Signal)

    def test_strategy_selector_returns_pairs(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        selector = adapter.strategy_selector()
        signal = self._make_signal()
        pairs = selector.select_all([signal])
        assert isinstance(pairs, list)
        if pairs:
            assert isinstance(pairs[0], tuple)
            assert len(pairs[0]) == 2

    def test_change_proposer_returns_candidate_change(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        proposer = adapter.change_proposer()
        signal = self._make_signal()
        strategy = self._make_strategy()
        artifact = ArtifactSnapshot("test.txt", "original content")
        context = EvolutionContext(cycle_id="test-cycle")
        change = proposer.propose(signal, strategy, artifact, context)
        assert isinstance(change, CandidateChange)
        assert change.artifact_id == signal.artifact_id

    def test_artifact_store_stage_commit_rollback(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        store = adapter.artifact_store()
        change = self._make_candidate_change()

        # Stage
        revision = store.stage(change.artifact_id, change)
        assert revision is not None
        assert revision.status == "staged"

        # Rollback
        assert store.rollback(revision) is True

        # Re-stage and commit
        revision2 = store.stage(change.artifact_id, change)
        committed = store.commit(revision2)
        assert committed is True

    def test_validation_gate_returns_decision(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        gate = adapter.validation_gate()
        change = self._make_candidate_change()
        case = self._make_eval_case()
        decision = asyncio.run(
            gate.validate(change, failing_cases=[case], holdout_cases=[])
        )
        assert isinstance(decision, ValidationDecision)
        assert decision.decision in {"accepted", "rejected", "needs_watch"}

    def test_audit_store_appends_event(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        store = adapter.audit_store()
        store.append_event({"event_type": "test", "data": 1})
        # Should not raise

    def test_full_cycle_runs(self, tmp_path: Path) -> None:
        adapter = self.create_adapter(tmp_path)
        engine = EvolutionEngine(adapter, EngineConfig(
            adapter_name=adapter.name,
            dry_run=True,
            output_dir=str(tmp_path / "output"),
        ))
        report = asyncio.run(engine.run_cycle())
        assert report.total_cases >= 0
        assert report.signals_extracted >= 0
        assert isinstance(report.changes_accepted, int)
