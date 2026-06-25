"""Minimal adapter template for AUTARK.

Copy this directory and customize the components to create your own adapter.
"""

from __future__ import annotations

from pathlib import Path

from autark.adapters.prompt_agent.corpus import PromptCaseProvider
from autark.adapters.prompt_agent.runner import PromptAgentRunner
from autark.artifacts.filesystem import FileArtifactStore
from autark.audit.event_log import JsonlEventLog
from autark.core.models import CandidateChange, RunResult
from autark.evaluation.judge import HeuristicEvaluator
from autark.proposers.deterministic import DeterministicProposer
from autark.signals.extractor import ThresholdSignalExtractor
from autark.strategies.selector import RegexStrategySelector
from autark.strategies.gene import make_strategy
from autark.validation.gate import MetadataScoreValidationGate


# -- Custom strategy catalog --
# Replace with your own strategies or use the built-in presets.
MINIMAL_STRATEGIES = [
    make_strategy(
        strategy_id="minimal-repair",
        name="Minimal Repair",
        category="repair",
        signals_match=["repair", "wrong_answer", "missing_constraint"],
        instructions=["Add a missing constraint or instruction to fix the failing case."],
        validation=["Rerun all cases and check for regressions."],
    ),
]


class MinimalAdapter:
    """A minimal adapter that reuses built-in AUTARK components.

    This adapter uses the prompt-agent runner and heuristic evaluator. Replace
    any component to fit your own agent, evaluator, or store.
    """

    name = "minimal"

    def __init__(
        self,
        corpus_path: Path | None = None,
        artifact_root: Path | None = None,
        output_dir: str = ".autark/output",
    ) -> None:
        self._corpus_path = corpus_path
        self._artifact_root = artifact_root
        self._output_dir = output_dir

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    def case_provider(self):
        return PromptCaseProvider(self._corpus_path)

    def agent_runner(self):
        return PromptAgentRunner(self.artifact_store())

    def evaluator(self):
        return HeuristicEvaluator()

    def signal_extractor(self):
        return ThresholdSignalExtractor()

    def strategy_selector(self):
        return RegexStrategySelector(MINIMAL_STRATEGIES)

    def change_proposer(self):
        return DeterministicProposer()

    def artifact_store(self):
        return FileArtifactStore(self._artifact_root or Path("."))

    def validation_gate(self):
        return MetadataScoreValidationGate()

    def audit_store(self):
        return JsonlEventLog(str(Path(self._output_dir) / "events.jsonl"))
