from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from autark.core.api import public_api
from autark.core.models import (
    ArtifactRevision,
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


@public_api(since="0.2.0")
@runtime_checkable
class CaseProvider(Protocol):
    def load_cases(self) -> list[EvalCase]:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class AgentRunner(Protocol):
    async def run_case(self, case: EvalCase) -> RunResult:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class Evaluator(Protocol):
    async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class SignalExtractor(Protocol):
    def extract(self, eval_results: list[EvalResult], recent_signals: list[Signal] | None = None) -> list[Signal]:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class StrategySelector(Protocol):
    def select_all(self, signals: list[Signal]) -> list[tuple[Signal, Strategy]]:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class ChangeProposer(Protocol):
    def propose(self, signal: Signal, strategy: Strategy, artifact: ArtifactSnapshot, context: EvolutionContext) -> CandidateChange:
        ...

    def propose_multi(
        self,
        signals: list[Signal],
        strategies: list[Strategy],
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> list[CandidateChange]:
        """Optional: propose changes for multiple signals at once.

        Default implementation falls back to per-signal ``propose``.
        Proposers may override to generate cross-signal repairs.
        """
        changes = []
        for signal, strategy in zip(signals, strategies):
            changes.append(self.propose(signal, strategy, artifact, context))
        return changes


@public_api(since="0.2.0")
@runtime_checkable
class ArtifactStore(Protocol):
    def load(self, artifact_id: str) -> str:
        ...

    def stage(self, artifact_id: str, candidate_change: CandidateChange) -> ArtifactRevision:
        ...

    def commit(self, revision: ArtifactRevision) -> bool:
        ...

    def rollback(self, revision: ArtifactRevision) -> bool:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class RerunValidationGate(Protocol):
    async def validate(
        self,
        candidate_change: CandidateChange,
        failing_cases: list[EvalCase],
        holdout_cases: list[EvalCase] | None = None,
    ) -> ValidationDecision:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class AuditStore(Protocol):
    def append_event(self, event: dict[str, Any]) -> None:
        ...


@public_api(since="0.2.0")
@runtime_checkable
class Adapter(Protocol):
    name: str

    def case_provider(self) -> CaseProvider:
        ...

    def agent_runner(self) -> AgentRunner:
        ...

    def evaluator(self) -> Evaluator:
        ...

    def signal_extractor(self) -> SignalExtractor:
        ...

    def strategy_selector(self) -> StrategySelector:
        ...

    def change_proposer(self) -> ChangeProposer:
        ...

    def artifact_store(self) -> ArtifactStore:
        ...

    def validation_gate(self) -> RerunValidationGate:
        ...

    def audit_store(self) -> AuditStore:
        ...
