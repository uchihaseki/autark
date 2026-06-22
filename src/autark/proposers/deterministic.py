from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from autark.core.models import ArtifactSnapshot, CandidateChange, EvolutionContext, Signal, Strategy


class DeterministicProposer:
    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        instruction = _instruction_for(signal.category)
        before_score = signal.scores.get("overall", 0.0)
        return CandidateChange(
            change_id=f"chg-{uuid4().hex[:8]}",
            artifact_id=signal.artifact_id,
            operations=[{"operation": "append", "text": instruction}],
            rationale=f"Apply deterministic repair for {signal.category} using {strategy.name}.",
            validation_plan=strategy.validation,
            metadata={
                "signal_id": signal.signal_id,
                "strategy_id": strategy.strategy_id,
                "before_scores": signal.scores,
                "after_scores": {"overall": min(1.0, max(before_score + 0.2, 0.8))},
                "context_cycle_id": context.cycle_id,
            },
        )


def _instruction_for(category: str) -> str:
    if category == "wrong_answer":
        return "Always compute and verify the answer before responding."
    if category == "missing_constraint":
        return "Follow all listed constraints explicitly before answering."
    if category == "format_error":
        return "Use the required output format exactly."
    if category == "empty_output":
        return "Never return an empty answer."
    if category == "prompt_ambiguous":
        return "Prefer concrete, direct, and testable instructions over vague guidance."
    return "Improve the artifact to satisfy the failing case while preserving existing behavior."


class ExternalCommandProposer:
    def __init__(self, command: str, timeout: float = 120.0) -> None:
        self.command = command
        self.timeout = timeout

    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        payload = {
            "signal": asdict(signal),
            "strategy": asdict(strategy),
            "artifact": asdict(artifact),
            "context": asdict(context),
        }
        completed = subprocess.run(
            self.command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            shell=True,
            capture_output=True,
            timeout=self.timeout,
            check=True,
        )
        data = json.loads(completed.stdout)
        return CandidateChange(
            change_id=data.get("change_id", f"chg-{uuid4().hex[:8]}"),
            artifact_id=data.get("artifact_id", signal.artifact_id),
            operations=data.get("operations", []),
            rationale=data.get("rationale", "external command proposal"),
            validation_plan=data.get("validation_plan", strategy.validation),
            metadata=data.get("metadata", {}),
        )


class ClaudeCodeProposer:
    def __init__(self, task_file: Path | None = None) -> None:
        self.task_file = task_file

    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        raise NotImplementedError(
            "ClaudeCodeProposer is a planned backend. Use deterministic or external-command for now."
        )
