"""
Minimal AUTARK Plug Demo — 2-line agent evaluation and self-improvement.

Usage::

    PYTHONPATH=src python examples/plug_minimal/demo.py

This demo shows the simplest possible integration: provide an agent runner
and test cases, and AUTARK handles the rest.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from autark.core.models import EvalCase, RunResult
from autark.plug import evolve


class SimpleAgent:
    """A toy agent that parses arithmetic from its prompt artifact.

    In a real integration, this would call your LLM, CLI agent, or API.
    """

    def __init__(self, prompt: str) -> None:
        self._prompt = prompt

    async def run_case(self, case: EvalCase) -> RunResult:
        # Simulate: the agent reads the prompt artifact and produces output.
        # A real agent would send self._prompt + case.input_text to an LLM.
        output = self._compute(case.input_text)
        return RunResult(
            case_id=case.case_id,
            artifact_id=case.metadata.get("artifact_id", "prompt.txt"),
            status="success",
            output=output,
        )

    @staticmethod
    def _compute(text: str) -> str:
        """Naive arithmetic parser — fails on subtraction and complex queries."""
        parts = text.split()
        if len(parts) >= 3 and parts[1] == "+":
            try:
                return str(int(parts[0]) + int(parts[2]))
            except ValueError:
                pass
        return "bad response"


async def main() -> None:
    # Load the initial prompt artifact
    prompt_path = Path(__file__).resolve().parent / "artifacts" / "prompt.txt"
    prompt = prompt_path.read_text()

    # The ONLY things you need to provide:
    # 1. An agent runner
    # 2. Test cases (as a list, file path, or None)
    # Everything else is auto-wired with sensible defaults.
    report = await evolve(
        runner=SimpleAgent(prompt),
        cases=str(Path(__file__).resolve().parent / "cases.json"),
        artifacts=str(Path(__file__).resolve().parent / "artifacts"),
    )

    print(f"AUTARK cycle complete")
    print(f"  cases: {report.total_cases} total, {report.failures} failed")
    print(f"  signals: {report.signals_extracted}")
    print(f"  changes: {report.changes_accepted} accepted, {report.changes_rejected} rejected")
    print(f"  dry-run: artifacts NOT modified (pass --commit to write)")


if __name__ == "__main__":
    asyncio.run(main())
