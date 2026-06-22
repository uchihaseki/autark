from __future__ import annotations

from autark.core.models import EvalCase, RunResult
from autark.adapters.prompt_agent.evaluator import PromptAgentEvaluator
from autark.adapters.prompt_agent.runner import _run_prompt
from autark.validation import RerunValidationGate


class PromptAgentValidationGate(RerunValidationGate):
    def __init__(self, artifact_store, min_improvement: float = 0.05, regression_threshold: float = 0.05) -> None:
        super().__init__(
            artifact_store,
            PromptAgentEvaluator(),
            min_improvement=min_improvement,
            regression_threshold=regression_threshold,
        )

    async def _run_case_with_artifact(self, artifact_id: str, artifact_text: str, case: EvalCase) -> RunResult:
        output = _run_prompt(artifact_text, case.input_text)
        return RunResult(
            case_id=case.case_id,
            artifact_id=artifact_id,
            status="success" if output else "error",
            output=output,
            trajectory="validation rerun with patched prompt",
        )
