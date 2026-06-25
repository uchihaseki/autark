from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from autark.core.api import public_api
from autark.core.models import ArtifactSnapshot, CandidateChange, EvolutionContext, Signal, Strategy


@public_api(since="0.2.0")
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

    def propose_multi(
        self,
        signals: list[Signal],
        strategies: list[Strategy],
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> list[CandidateChange]:
        """Generate one change per signal, preserving per-signal metadata."""
        changes = []
        for signal, strategy in zip(signals, strategies):
            changes.append(self.propose(signal, strategy, artifact, context))
        return changes


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


@public_api(since="0.2.0")
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


@public_api(since="0.2.0")
class ClaudeCodeProposer:
    """Proposer that delegates to the Claude Code CLI.

    Builds a structured prompt from the signal, strategy, artifact, and
    context, invokes ``claude -p``, and parses the JSON response into a
    ``CandidateChange``.

    The Claude CLI must be installed and available on PATH.  This proposer
    is an optional integration — it is not a core dependency.
    """

    def __init__(
        self,
        claude_command: str = "claude",
        timeout: float = 300.0,
        task_file: Path | None = None,
    ) -> None:
        self.claude_command = claude_command
        self.timeout = timeout
        self.task_file = task_file

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cases_text(cases: list, label: str, max_items: int = 5) -> str:
        if not cases:
            return f"### {label}\n(none)\n"
        lines = [f"### {label}"]
        for case in cases[:max_items]:
            lines.append(f"- case_id: {case.case_id}")
            lines.append(f"  input: {case.input_text[:200]}")
            lines.append(f"  expected: {case.expected_output[:200]}")
        return "\n".join(lines)

    @staticmethod
    def _eval_results_text(results: list, max_items: int = 5) -> str:
        if not results:
            return "### Evaluation Results\n(none)\n"
        lines = ["### Evaluation Results"]
        for r in results[:max_items]:
            lines.append(f"- case_id: {r.case_id}  status: {r.status}  scores: {r.scores}  category: {r.failure_category}")
        return "\n".join(lines)

    def _build_prompt(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> str:
        parts = [
            "You are an automated agent repair system.",
            "",
            "Your task: read the failure signal, the repair strategy, the current artifact content,",
            "and the evaluation context, then produce a CandidateChange as a single JSON object.",
            "",
            "## Failure Signal",
            f"- signal_id: {signal.signal_id}",
            f"- case_id: {signal.case_id}",
            f"- artifact_id: {signal.artifact_id}",
            f"- category: {signal.category}",
            f"- evidence: {signal.evidence}",
            f"- scores: {signal.scores}",
            "",
            "## Repair Strategy",
            f"- strategy_id: {strategy.strategy_id}",
            f"- name: {strategy.name}",
            f"- instructions: {json.dumps(strategy.instructions)}",
            f"- validation plan: {json.dumps(strategy.validation)}",
            "",
            "## Current Artifact",
            f"- artifact_id: {artifact.artifact_id}",
            "```",
            artifact.content[:4000],
            "```",
            "",
            self._cases_text(context.failing_cases, "Failing Cases"),
            "",
            self._cases_text(context.holdout_cases, "Holdout Cases"),
            "",
            self._eval_results_text(context.eval_results),
            "",
            "## Required JSON Output",
            "Return ONLY a JSON object (no markdown fences, no extra text) with these fields:",
            json.dumps(
                {
                    "change_id": "<string, e.g. chg-abc123>",
                    "artifact_id": signal.artifact_id,
                    "operations": [
                        {"operation": "<append|replace>", "text": "<repair instruction or replacement text>"}
                    ],
                    "rationale": "<one sentence explaining the change>",
                    "validation_plan": strategy.validation,
                    "metadata": {
                        "signal_id": signal.signal_id,
                        "strategy_id": strategy.strategy_id,
                        "source": "claude-code",
                    },
                },
                indent=2,
            ),
            "",
            "Be concise. The operations must describe concrete, safe edits to the artifact.",
            "Only output valid JSON. Do not wrap in markdown code fences.",
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Propose
    # ------------------------------------------------------------------

    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        prompt = self._build_prompt(signal, strategy, artifact, context)

        try:
            completed = subprocess.run(
                [self.claude_command, "-p", prompt],
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Claude CLI not found at '{self.claude_command}'. "
                "Install Claude Code or use --proposer deterministic."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"ClaudeCodeProposer timed out after {self.timeout}s. "
                "Increase --proposer-timeout or use --proposer deterministic."
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Claude CLI exited with code {exc.returncode}: {exc.stderr[:500]}"
            )

        raw = completed.stdout.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract the first JSON object from the text
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    raise RuntimeError(
                        f"ClaudeCodeProposer could not parse JSON from output. "
                        f"Raw output (first 500 chars): {raw[:500]}"
                    )
            else:
                raise RuntimeError(
                    f"ClaudeCodeProposer output is not valid JSON. "
                    f"Raw output (first 500 chars): {raw[:500]}"
                )

        return CandidateChange(
            change_id=data.get("change_id", f"chg-{uuid4().hex[:8]}"),
            artifact_id=data.get("artifact_id", signal.artifact_id),
            operations=data.get("operations", []),
            rationale=data.get("rationale", f"Claude Code proposal for {signal.category}"),
            validation_plan=data.get("validation_plan", strategy.validation),
            metadata={
                **data.get("metadata", {}),
                "proposer": "claude-code",
                "signal_id": signal.signal_id,
                "strategy_id": strategy.strategy_id,
            },
        )


@public_api(since="0.3.0", experimental=True)
class PythonFunctionProposer:
    """Proposer that wraps a user-provided Python callable.

    Args:
        propose_fn: A callable ``(Signal, Strategy, ArtifactSnapshot, EvolutionContext)
            -> CandidateChange``.
    """

    def __init__(
        self,
        propose_fn: Callable[
            [Signal, Strategy, ArtifactSnapshot, EvolutionContext], CandidateChange
        ],
    ) -> None:
        self._propose_fn = propose_fn

    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        return self._propose_fn(signal, strategy, artifact, context)
