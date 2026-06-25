from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from autark.core.api import public_api
from autark.core.models import (
    ArtifactSnapshot,
    CandidateChange,
    CycleReport,
    EvalCase,
    EvalReport,
    EvalResult,
    EvolutionContext,
    Signal,
    Strategy,
    ValidationDecision,
)
from autark.core.protocols import Adapter


@public_api(since="0.2.0")
@dataclass(slots=True)
class EngineConfig:
    adapter_name: str = ""
    review_mode: bool = False
    dry_run: bool = True
    max_parallel_cases: int = 5   # Deprecated: use max_concurrency
    max_concurrency: int = 5
    parallel_cases: bool = False  # Opt-in: run cases concurrently
    retry_count: int = 0          # Number of retries for flaky agents (0 = no retry)
    retry_delay: float = 0.5      # Seconds between retries
    output_dir: str = ".autark/output"
    metadata: dict[str, Any] = field(default_factory=dict)


@public_api(since="0.2.0")
class EvolutionEngine:
    def __init__(self, adapter: Adapter, config: EngineConfig | None = None) -> None:
        self.adapter = adapter
        self.config = config or EngineConfig(adapter_name=getattr(adapter, "name", "adapter"))
        self._output_path = Path(self.config.output_dir)

    def _ensure_output_dir(self) -> None:
        self._output_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_json(self, filename: str, payload: Any) -> None:
        self._ensure_output_dir()
        path = self._output_path / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _load_json(self, filename: str) -> Any:
        path = self._output_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing state file: {path}. Run 'autark eval' first.")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _serialize_case(case: EvalCase) -> dict:
        return asdict(case)

    @staticmethod
    def _deserialize_case(data: dict) -> EvalCase:
        return EvalCase(**data)

    @staticmethod
    def _serialize_eval_result(result: EvalResult) -> dict:
        return asdict(result)

    @staticmethod
    def _deserialize_eval_result(data: dict) -> EvalResult:
        return EvalResult(**data)

    @staticmethod
    def _serialize_signal(signal: Signal) -> dict:
        return asdict(signal)

    @staticmethod
    def _deserialize_signal(data: dict) -> Signal:
        return Signal(**data)

    @staticmethod
    def _serialize_candidate_change(change: CandidateChange) -> dict:
        return asdict(change)

    @staticmethod
    def _deserialize_candidate_change(data: dict) -> CandidateChange:
        return CandidateChange(**data)

    def _save_eval_state(self, cycle_id: str, eval_results: list[EvalResult], signals: list[Signal], cases: list[EvalCase]) -> None:
        self._save_json("eval_state.json", {
            "cycle_id": cycle_id,
            "eval_results": [self._serialize_eval_result(r) for r in eval_results],
            "signals": [self._serialize_signal(s) for s in signals],
            "cases": [self._serialize_case(c) for c in cases],
        })

    def _load_eval_state(self) -> dict:
        raw = self._load_json("eval_state.json")
        return {
            "cycle_id": raw["cycle_id"],
            "eval_results": [self._deserialize_eval_result(r) for r in raw["eval_results"]],
            "signals": [self._deserialize_signal(s) for s in raw["signals"]],
            "cases": [self._deserialize_case(c) for c in raw["cases"]],
        }

    def _save_proposals(self, changes: list[CandidateChange]) -> None:
        self._save_json("proposals.json", {
            "changes": [self._serialize_candidate_change(c) for c in changes],
        })

    def _load_proposals(self) -> list[CandidateChange]:
        raw = self._load_json("proposals.json")
        return [self._deserialize_candidate_change(c) for c in raw["changes"]]

    def _save_decisions(self, decisions: list[ValidationDecision]) -> None:
        self._save_json("decisions.json", {
            "decisions": [asdict(d) for d in decisions],
        })

    # ------------------------------------------------------------------
    # Phase methods
    # ------------------------------------------------------------------

    async def _run_one_case(
        self,
        runner,
        evaluator,
        case: EvalCase,
        cycle_id: str,
        audit_store,
    ) -> tuple[EvalResult | None, str | None]:
        """Run + evaluate one case, with retry."""
        last_error = None
        for attempt in range(self.config.retry_count + 1):
            try:
                run_result = await runner.run_case(case)
                eval_result = await evaluator.evaluate(case, run_result)
                audit_store.append_event({
                    "event_type": "case_evaluated",
                    "cycle_id": cycle_id,
                    "case_id": case.case_id,
                    "artifact_id": run_result.artifact_id,
                    "status": eval_result.status,
                    "scores": eval_result.scores,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                return eval_result, None
            except Exception as exc:
                last_error = f"case {getattr(case, 'case_id', '?')}: {exc}"
                if attempt < self.config.retry_count:
                    await asyncio.sleep(self.config.retry_delay)
        return None, last_error

    async def run_eval(self, cycle_id: str | None = None) -> EvalReport:
        if cycle_id is None:
            cycle_id = f"cycle-{uuid4().hex[:8]}"
        errors: list[str] = []

        case_provider = self.adapter.case_provider()
        runner = self.adapter.agent_runner()
        evaluator = self.adapter.evaluator()
        signal_extractor = self.adapter.signal_extractor()
        audit_store = self.adapter.audit_store()

        cases = case_provider.load_cases()

        if self.config.parallel_cases and len(cases) > 1:
            semaphore = asyncio.Semaphore(self.config.max_concurrency)

            async def run_with_semaphore(case: EvalCase):
                async with semaphore:
                    return await self._run_one_case(runner, evaluator, case, cycle_id, audit_store)

            results = await asyncio.gather(*[run_with_semaphore(c) for c in cases])
        else:
            results = []
            for case in cases:
                results.append(
                    await self._run_one_case(runner, evaluator, case, cycle_id, audit_store)
                )

        eval_results: list[EvalResult] = []
        for eval_result, error in results:
            if error is not None:
                errors.append(error)
            elif eval_result is not None:
                eval_results.append(eval_result)

        signals = signal_extractor.extract(eval_results, recent_signals=[])
        self._save_eval_state(cycle_id, eval_results, signals, cases)

        failures = sum(1 for r in eval_results if r.status == "fail")
        return EvalReport(
            cycle_id=cycle_id,
            adapter_name=getattr(self.adapter, "name", self.config.adapter_name or "adapter"),
            total_cases=len(cases),
            failures=failures,
            signals_extracted=len(signals),
            errors=errors,
        )

    async def run_propose(self, cycle_id: str | None = None) -> list[CandidateChange]:
        state = self._load_eval_state()
        if cycle_id is None:
            cycle_id = state["cycle_id"]

        eval_results: list[EvalResult] = state["eval_results"]
        signals: list[Signal] = state["signals"]
        cases: list[EvalCase] = state["cases"]

        selector = self.adapter.strategy_selector()
        proposer = self.adapter.change_proposer()
        artifact_store = self.adapter.artifact_store()

        selections = selector.select_all(signals)

        # Group selections by artifact_id for multi-signal proposals
        groups: dict[str, list[tuple[Signal, Strategy]]] = defaultdict(list)
        for signal, strategy in selections:
            groups[signal.artifact_id].append((signal, strategy))

        changes: list[CandidateChange] = []

        for artifact_id, pairs in groups.items():
            artifact_text = artifact_store.load(artifact_id)
            signals_group = [s for s, _ in pairs]
            strategies_group = [st for _, st in pairs]

            # Collect all failing case IDs for this artifact group
            failing_case_ids = {s.case_id for s in signals_group}
            failing_cases = [c for c in cases if c.case_id in failing_case_ids]
            holdout_cases = [c for c in cases if c.case_id not in failing_case_ids]

            context = EvolutionContext(
                cycle_id=cycle_id,
                failing_cases=failing_cases,
                holdout_cases=holdout_cases,
                eval_results=eval_results,
                metadata=self.config.metadata,
            )

            if hasattr(proposer, "propose_multi") and len(pairs) > 1:
                multi_changes = proposer.propose_multi(
                    signals_group,
                    strategies_group,
                    ArtifactSnapshot(artifact_id, artifact_text),
                    context,
                )
                changes.extend(multi_changes)
            else:
                for signal, strategy in pairs:
                    change = proposer.propose(
                        signal,
                        strategy,
                        ArtifactSnapshot(artifact_id, artifact_text),
                        context,
                    )
                    changes.append(change)

        self._save_proposals(changes)
        return changes

    async def run_validate(self, cycle_id: str | None = None) -> tuple[list[ValidationDecision], int, int]:
        state = self._load_eval_state()
        if cycle_id is None:
            cycle_id = state["cycle_id"]

        cases: list[EvalCase] = state["cases"]
        signals: list[Signal] = state["signals"]
        changes = self._load_proposals()

        # Build signal lookup: signal_id -> Signal
        signal_by_id: dict[str, Signal] = {s.signal_id: s for s in signals}

        validation_gate = self.adapter.validation_gate()
        artifact_store = self.adapter.artifact_store()
        audit_store = self.adapter.audit_store()

        decisions: list[ValidationDecision] = []
        accepted = 0
        rejected = 0
        artifacts_modified: list[str] = []

        for change in changes:
            if not change.change_id:
                continue
            # Match change back to its signal (via metadata.signal_id) then to the failing case
            sid = change.metadata.get("signal_id", "")
            matched_signal = signal_by_id.get(sid)
            if matched_signal:
                failing_cases = [c for c in cases if c.case_id == matched_signal.case_id]
                holdout_cases = [c for c in cases if c.case_id != matched_signal.case_id]
            else:
                failing_cases = []
                holdout_cases = cases

            revision = artifact_store.stage(change.artifact_id, change)
            decision = await validation_gate.validate(change, failing_cases, holdout_cases)

            audit_store.append_event({
                "event_type": "validation_decision",
                "cycle_id": cycle_id,
                "artifact_id": change.artifact_id,
                "change_id": change.change_id,
                "decision": decision.decision,
                "reason": decision.reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if decision.decision in {"accepted", "needs_watch"}:
                if not self.config.dry_run:
                    artifact_store.commit(revision)
                    artifacts_modified.append(change.artifact_id)
                accepted += 1
            else:
                artifact_store.rollback(revision)
                rejected += 1

            decisions.append(decision)

        self._save_decisions(decisions)
        return decisions, accepted, rejected

    async def run_cycle(self) -> CycleReport:
        eval_report = await self.run_eval()
        state = self._load_eval_state()

        changes = await self.run_propose(eval_report.cycle_id)
        decisions, accepted, rejected = await self.run_validate(eval_report.cycle_id)

        return CycleReport(
            cycle_id=eval_report.cycle_id,
            adapter_name=eval_report.adapter_name,
            total_cases=eval_report.total_cases,
            failures=eval_report.failures,
            signals_extracted=eval_report.signals_extracted,
            strategies_selected=len(changes),
            changes_accepted=accepted,
            changes_rejected=rejected,
            artifacts_modified=state.get("artifacts_modified", []),
            errors=eval_report.errors,
            metadata=self.config.metadata,
        )
