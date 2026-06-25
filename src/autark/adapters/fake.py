from __future__ import annotations

import json
from pathlib import Path

from autark.artifacts import InMemoryArtifactStore
from autark.audit import JsonlEventLog
from autark.core.models import EvalCase, RunResult, Strategy
from autark.evaluation import HeuristicEvaluator
from autark.proposers import DeterministicProposer
from autark.signals import ThresholdSignalExtractor
from autark.strategies import RegexStrategySelector
from autark.validation import MetadataScoreValidationGate


class StaticCaseProvider:
    def __init__(self, cases: list[EvalCase]) -> None:
        self.cases = cases

    def load_cases(self) -> list[EvalCase]:
        return self.cases


class FakeRunner:
    def __init__(self, artifact_store: InMemoryArtifactStore, artifact_id: str = "prompt.txt") -> None:
        self.artifact_store = artifact_store
        self.artifact_id = artifact_id

    async def run_case(self, case: EvalCase) -> RunResult:
        artifact_text = self.artifact_store.load(self.artifact_id)
        output = "bad response" if "BROKEN" in artifact_text else case.expected_output or "ok"
        return RunResult(
            case_id=case.case_id,
            artifact_id=self.artifact_id,
            status="success",
            output=output,
            trajectory=f"fake runner used {self.artifact_id}",
        )


class FakeAdapter:
    name = "fake"

    def __init__(
        self,
        cases: list[EvalCase] | None = None,
        artifacts: dict[str, str] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._artifact_store = InMemoryArtifactStore(artifacts or {"prompt.txt": "BROKEN prompt"})
        self._cases = cases or [
            EvalCase(case_id="fake-1", input_text="say ok", expected_output="ok"),
        ]
        self._audit = JsonlEventLog((output_dir or Path(".autark/output")) / "events.jsonl")
        self._strategies = [
            Strategy(
                strategy_id="repair-wrong-answer",
                name="Repair wrong answer",
                category="repair",
                signals_match=["wrong_answer", "expected answer"],
                instructions=["Make the artifact produce the expected output."],
                validation=["fake validation"],
            )
        ]

    @classmethod
    def from_json(cls, corpus_path: Path | None = None, output_dir: Path | None = None) -> FakeAdapter:
        if not corpus_path:
            return cls(output_dir=output_dir)
        data = json.loads(corpus_path.read_text(encoding="utf-8"))
        cases = [
            EvalCase(
                case_id=item["case_id"],
                input_text=item.get("input_text", ""),
                expected_output=item.get("expected_output", ""),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("cases", data if isinstance(data, list) else [])
        ]
        artifacts = data.get("artifacts", {"prompt.txt": "BROKEN prompt"}) if isinstance(data, dict) else None
        return cls(cases=cases, artifacts=artifacts, output_dir=output_dir)

    def case_provider(self) -> StaticCaseProvider:
        return StaticCaseProvider(self._cases)

    def agent_runner(self) -> FakeRunner:
        return FakeRunner(self._artifact_store)

    def evaluator(self) -> HeuristicEvaluator:
        return HeuristicEvaluator()

    def signal_extractor(self) -> ThresholdSignalExtractor:
        return ThresholdSignalExtractor()

    def strategy_selector(self) -> RegexStrategySelector:
        return RegexStrategySelector(self._strategies)

    def change_proposer(self) -> DeterministicProposer:
        return DeterministicProposer()

    def artifact_store(self) -> InMemoryArtifactStore:
        return self._artifact_store

    def validation_gate(self) -> MetadataScoreValidationGate:
        return MetadataScoreValidationGate(min_improvement=0.05)

    def audit_store(self) -> JsonlEventLog:
        return self._audit
