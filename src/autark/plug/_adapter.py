"""SyntheticAdapter — auto-wires plug-in components with sensible defaults.

Internal implementation detail.  Users should call ``evolve()`` rather than
instantiate ``SyntheticAdapter`` directly.
"""

from __future__ import annotations

from pathlib import Path

from autark.audit.event_log import JsonlEventLog
from autark.core.models import Strategy
from autark.core.protocols import (
    ArtifactStore,
    AuditStore,
    CaseProvider,
    ChangeProposer,
    Evaluator,
    RerunValidationGate,
    SignalExtractor,
    StrategySelector,
)
from autark.signals.extractor import ThresholdSignalExtractor
from autark.strategies.selector import RegexStrategySelector
from autark.validation.gate import MetadataScoreValidationGate


class SyntheticAdapter:
    """Adapter that composes user-provided and default components.

    Only ``runner`` is required.  Every other component falls back to a
    sensible default so users can start with a single line and customize
    incrementally.
    """

    name = "synthetic"

    def __init__(
        self,
        *,
        runner,
        case_provider: CaseProvider,
        evaluator: Evaluator,
        proposer: ChangeProposer,
        strategies: list[Strategy],
        artifact_store: ArtifactStore,
        output_dir: str | Path = ".autark/output",
    ) -> None:
        self._runner = runner
        self._case_provider = case_provider
        self._evaluator = evaluator
        self._proposer = proposer
        self._strategies = strategies
        self._artifact_store = artifact_store
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self._audit = JsonlEventLog(output_path / "events.jsonl")

    # -- Adapter protocol ---------------------------------------------------

    def case_provider(self) -> CaseProvider:
        return self._case_provider

    def agent_runner(self):
        return self._runner

    def evaluator(self) -> Evaluator:
        return self._evaluator

    def signal_extractor(self) -> SignalExtractor:
        return ThresholdSignalExtractor()

    def strategy_selector(self) -> StrategySelector:
        return RegexStrategySelector(list(self._strategies))

    def change_proposer(self) -> ChangeProposer:
        return self._proposer

    def artifact_store(self) -> ArtifactStore:
        return self._artifact_store

    def validation_gate(self) -> RerunValidationGate:
        return MetadataScoreValidationGate()

    def audit_store(self) -> AuditStore:
        return self._audit
