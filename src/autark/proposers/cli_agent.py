"""Proposers that delegate to external CLI agent tools.

Each proposer builds a structured prompt, invokes a CLI agent command,
and parses the JSON response into a ``CandidateChange``.

The CLI tools must be installed and available on PATH. These proposers
are optional integrations — they are not core dependencies.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from autark.core.api import public_api
from autark.core.models import ArtifactSnapshot, CandidateChange, EvolutionContext, Signal, Strategy


class CliAgentProposer:
    """Base class for proposers that delegate to a CLI agent via structured prompts.

    Subclasses override ``_build_prompt`` to customize the agent-specific
    prompt format. The base class handles subprocess invocation, JSON
    response parsing, markdown fence stripping, and error handling.

    Args:
        command: The CLI command and arguments as a list.
        timeout: Maximum seconds to wait for the CLI agent.
        task_file: Optional path to a task file passed to the CLI.
    """

    def __init__(
        self,
        command: list[str],
        timeout: float = 300.0,
        task_file: Path | None = None,
    ) -> None:
        self.command = command
        self.timeout = timeout
        self.task_file = task_file

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> str:
        raise NotImplementedError("Subclasses must implement _build_prompt")

    def _proposer_name(self) -> str:
        return self.__class__.__name__.lower().replace("proposer", "")

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw_output: str) -> dict:
        """Extract a JSON object from the CLI output.

        Handles markdown code fences and fallback regex extraction.
        """
        raw = raw_output.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise RuntimeError(
                "Could not parse JSON from proposer output. "
                f"Raw output (first 500 chars): {raw_output[:500]}"
            )

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
                self.command + [prompt],
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"CLI not found at '{self.command[0]}'. "
                f"Please install the required CLI tool or use a different proposer."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Proposer '{self._proposer_name()}' timed out after {self.timeout}s. "
                "Increase timeout or use a different proposer."
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"CLI exited with code {exc.returncode}: {exc.stderr[:500]}"
            )

        data = self._parse_response(completed.stdout)
        return CandidateChange(
            change_id=data.get("change_id", f"chg-{uuid4().hex[:8]}"),
            artifact_id=data.get("artifact_id", signal.artifact_id),
            operations=data.get("operations", []),
            rationale=data.get("rationale", f"{self._proposer_name()} proposal"),
            validation_plan=data.get("validation_plan", strategy.validation),
            metadata={
                **data.get("metadata", {}),
                "proposer": self._proposer_name(),
                "signal_id": signal.signal_id,
                "strategy_id": strategy.strategy_id,
            },
        )

    # Static helpers usable by subclasses in _build_prompt
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
            lines.append(
                f"- case_id: {r.case_id}  status: {r.status}  "
                f"scores: {r.scores}  category: {r.failure_category}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Concrete CLI-agent proposers
# ---------------------------------------------------------------------------


@public_api(since="0.3.0", experimental=True)
class GeminiCliProposer(CliAgentProposer):
    """Proposer that delegates to the Google Gemini CLI.

    Requires the Gemini CLI installed and available on PATH.
    """

    def __init__(
        self,
        gemini_command: str = "gemini",
        timeout: float = 300.0,
    ) -> None:
        super().__init__([gemini_command, "chat", "--prompt"], timeout=timeout)

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
                        {
                            "operation": "<append|replace>",
                            "text": "<repair instruction or replacement text>",
                        }
                    ],
                    "rationale": "<one sentence explaining the change>",
                    "validation_plan": strategy.validation,
                    "metadata": {
                        "signal_id": signal.signal_id,
                        "strategy_id": strategy.strategy_id,
                        "source": "gemini-cli",
                    },
                },
                indent=2,
            ),
            "",
            "Be concise. The operations must describe concrete, safe edits to the artifact.",
            "Only output valid JSON. Do not wrap in markdown code fences.",
        ]
        return "\n".join(parts)


@public_api(since="0.3.0", experimental=True)
class CodexCliProposer(CliAgentProposer):
    """Proposer that delegates to the OpenAI Codex CLI.

    Requires the Codex CLI installed and available on PATH.
    """

    def __init__(
        self,
        codex_command: str = "codex",
        timeout: float = 300.0,
    ) -> None:
        super().__init__([codex_command, "exec"], timeout=timeout)

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
                        {
                            "operation": "<append|replace>",
                            "text": "<repair instruction or replacement text>",
                        }
                    ],
                    "rationale": "<one sentence explaining the change>",
                    "validation_plan": strategy.validation,
                    "metadata": {
                        "signal_id": signal.signal_id,
                        "strategy_id": strategy.strategy_id,
                        "source": "codex-cli",
                    },
                },
                indent=2,
            ),
            "",
            "Be concise. The operations must describe concrete, safe edits to the artifact.",
            "Only output valid JSON. Do not wrap in markdown code fences.",
        ]
        return "\n".join(parts)
