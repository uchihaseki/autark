from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from autark.core.models import ArtifactSnapshot, CycleReport, EvolutionContext
from autark.core.protocols import Adapter


@dataclass(slots=True)
class EngineConfig:
    adapter_name: str = ""
    review_mode: bool = False
    dry_run: bool = True
    max_parallel_cases: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)


class EvolutionEngine:
    def __init__(self, adapter: Adapter, config: EngineConfig | None = None) -> None:
        self.adapter = adapter
        self.config = config or EngineConfig(adapter_name=getattr(adapter, "name", "adapter"))

    async def run_cycle(self) -> CycleReport:
        cycle_id = f"cycle-{uuid4().hex[:8]}"
        errors: list[str] = []

        case_provider = self.adapter.case_provider()
        runner = self.adapter.agent_runner()
        evaluator = self.adapter.evaluator()
        signal_extractor = self.adapter.signal_extractor()
        selector = self.adapter.strategy_selector()
        proposer = self.adapter.change_proposer()
        artifact_store = self.adapter.artifact_store()
        validation_gate = self.adapter.validation_gate()
        audit_store = self.adapter.audit_store()

        cases = case_provider.load_cases()
        eval_results = []

        for case in cases:
            try:
                run_result = await runner.run_case(case)
                eval_result = await evaluator.evaluate(case, run_result)
                eval_results.append(eval_result)
                audit_store.append_event(
                    {
                        "event_type": "case_evaluated",
                        "cycle_id": cycle_id,
                        "case_id": case.case_id,
                        "artifact_id": run_result.artifact_id,
                        "status": eval_result.status,
                        "scores": eval_result.scores,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as exc:
                errors.append(f"case {getattr(case, 'case_id', '?')}: {exc}")

        failures = [result for result in eval_results if result.status == "fail"]
        signals = signal_extractor.extract(eval_results, recent_signals=[])
        selections = selector.select_all(signals)

        accepted = 0
        rejected = 0
        artifacts_modified: list[str] = []

        for signal, strategy in selections:
            artifact_text = artifact_store.load(signal.artifact_id)
            failing_cases = [case for case in cases if case.case_id == signal.case_id]
            holdout_cases = [case for case in cases if case.case_id != signal.case_id]
            context = EvolutionContext(
                cycle_id=cycle_id,
                failing_cases=failing_cases,
                holdout_cases=holdout_cases,
                eval_results=eval_results,
                metadata=self.config.metadata,
            )
            change = proposer.propose(
                signal,
                strategy,
                ArtifactSnapshot(signal.artifact_id, artifact_text),
                context,
            )
            revision = artifact_store.stage(signal.artifact_id, change)
            decision = await validation_gate.validate(change, failing_cases, holdout_cases)

            audit_store.append_event(
                {
                    "event_type": "validation_decision",
                    "cycle_id": cycle_id,
                    "artifact_id": signal.artifact_id,
                    "change_id": change.change_id,
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            if decision.decision in {"accepted", "needs_watch"}:
                if not self.config.dry_run:
                    artifact_store.commit(revision)
                    artifacts_modified.append(signal.artifact_id)
                accepted += 1
            else:
                artifact_store.rollback(revision)
                rejected += 1

        return CycleReport(
            cycle_id=cycle_id,
            adapter_name=getattr(self.adapter, "name", self.config.adapter_name or "adapter"),
            total_cases=len(cases),
            failures=len(failures),
            signals_extracted=len(signals),
            strategies_selected=len(selections),
            changes_accepted=accepted,
            changes_rejected=rejected,
            artifacts_modified=artifacts_modified,
            errors=errors,
            metadata=self.config.metadata,
        )
