from __future__ import annotations

import re

from autark.artifacts import FileArtifactStore
from autark.core.models import EvalCase, RunResult


class PromptAgentRunner:
    def __init__(self, artifact_store: FileArtifactStore) -> None:
        self.artifact_store = artifact_store

    async def run_case(self, case: EvalCase) -> RunResult:
        artifact_id = case.metadata.get("artifact_id", "prompt.txt")
        prompt = self.artifact_store.load(artifact_id)
        output = _run_prompt(prompt, case.input_text)
        return RunResult(
            case_id=case.case_id,
            artifact_id=artifact_id,
            status="success" if output else "error",
            output=output,
            trajectory=f"prompt-agent used {artifact_id}",
            metadata={"prompt_length": len(prompt)},
        )


def _run_prompt(prompt: str, input_text: str) -> str:
    if "Always compute and verify" in prompt:
        maybe_sum = _solve_addition(input_text)
        if maybe_sum is not None:
            return str(maybe_sum)
    if "Never return an empty answer" in prompt and not input_text.strip():
        return "I need more information."
    if "BROKEN" in prompt:
        return "bad response"
    maybe_sum = _solve_addition(input_text)
    return str(maybe_sum) if maybe_sum is not None and "compute" in prompt.lower() else "bad response"


def _solve_addition(text: str) -> int | None:
    numbers = [int(item) for item in re.findall(r"\d+", text)]
    if len(numbers) >= 2 and any(token in text.lower() for token in ["sum", "+", "add"]):
        return sum(numbers[:2])
    return None
