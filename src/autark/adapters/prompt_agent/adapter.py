from __future__ import annotations

from pathlib import Path
from typing import Any

from autark.adapters.prompt_agent.artifact_store import PromptArtifactStore
from autark.adapters.prompt_agent.corpus import PromptCaseProvider
from autark.adapters.prompt_agent.evaluator import PromptAgentEvaluator
from autark.adapters.prompt_agent.runner import PromptAgentRunner
from autark.adapters.prompt_agent.strategies import PROMPT_AGENT_STRATEGIES
from autark.adapters.prompt_agent.validation import PromptAgentValidationGate
from autark.audit import JsonlEventLog
from autark.proposers import ClaudeCodeProposer, DeterministicProposer, ExternalCommandProposer
from autark.signals import ThresholdSignalExtractor
from autark.strategies import RegexStrategySelector


class PromptAgentAdapter:
    name = "prompt-agent"

    def __init__(
        self,
        corpus_path: Path | None = None,
        artifact_root: Path | None = None,
        output_dir: Path | None = None,
        proposer_name: str = "deterministic",
        proposer_command: str | None = None,
        proposer_timeout: float = 120.0,
    ) -> None:
        self._corpus_path = corpus_path
        self._artifact_root = artifact_root or Path.cwd()
        self._output_dir = output_dir or Path(".autark/output")
        self._audit = JsonlEventLog(self._output_dir / "events.jsonl")
        self._artifact_store = PromptArtifactStore(self._artifact_root)
        self._proposer = self._build_proposer(proposer_name, proposer_command, proposer_timeout)

    def _build_proposer(self, proposer_name: str, proposer_command: str | None, proposer_timeout: float):
        if proposer_name == "external-command":
            if not proposer_command:
                raise ValueError("proposer_command is required for external-command proposer")
            return ExternalCommandProposer(proposer_command, timeout=proposer_timeout)
        if proposer_name == "claude-code":
            return ClaudeCodeProposer(
                claude_command=proposer_command or "claude",
                timeout=proposer_timeout,
            )
        return DeterministicProposer()

    def case_provider(self) -> PromptCaseProvider:
        return PromptCaseProvider(self._corpus_path)

    def agent_runner(self) -> PromptAgentRunner:
        return PromptAgentRunner(self._artifact_store)

    def evaluator(self) -> PromptAgentEvaluator:
        return PromptAgentEvaluator()

    def signal_extractor(self) -> ThresholdSignalExtractor:
        return ThresholdSignalExtractor()

    def strategy_selector(self) -> RegexStrategySelector:
        return RegexStrategySelector(PROMPT_AGENT_STRATEGIES)

    def change_proposer(self):
        return self._proposer

    def artifact_store(self) -> PromptArtifactStore:
        return self._artifact_store

    def validation_gate(self) -> PromptAgentValidationGate:
        return PromptAgentValidationGate(self._artifact_store)

    def audit_store(self) -> JsonlEventLog:
        return self._audit
