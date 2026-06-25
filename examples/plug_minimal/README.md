# AUTARK Plug Minimal Demo

Minimal example showing the AUTARK plug-in API: **2 lines to integrate agent evaluation and self-improvement**.

## Quick Start

```bash
cd autark
PYTHONPATH=src python examples/plug_minimal/demo.py
```

Expected output:

```
AUTARK cycle complete
  cases: 4 total, 2 failed
  signals: 1
  changes: 1 accepted, 0 rejected
  dry-run: artifacts NOT modified (pass --commit to write)
```

The agent (`SimpleAgent`) can do `+` but fails on `-`. AUTARK detects the failure, extracts a signal, matches a repair strategy, proposes a prompt change, and validates it — all in one `evolve()` call.

## What This Shows

| Line | What It Does |
|------|-------------|
| `await evolve(runner=..., cases=..., artifacts=...)` | Full eval → signal → strategy → propose → validate cycle |
| `report.total_cases` | 4 cases ran |
| `report.failures` | 2 failed (the subtraction cases) |
| `report.changes_accepted` | 1 repair was proposed and validated |

## From Here to Real Integration

Replace `SimpleAgent` with your real agent runner:

```python
class MyRealRunner:
    def __init__(self, artifact_store):
        self._store = artifact_store

    async def run_case(self, case: EvalCase) -> RunResult:
        prompt = self._store.load(case.metadata["artifact_id"])
        # Call your LLM, CLI agent, or API:
        output = my_llm_call(prompt, case.input_text)
        return RunResult(
            case_id=case.case_id,
            artifact_id=case.metadata["artifact_id"],
            status="success",
            output=output,
        )
```

Then pass it to `evolve()`:

```python
report = await evolve(runner=MyRealRunner(store), cases="cases.json", artifacts="./prompts/")
```

## Using a CLI Agent as the Proposer

To use an LLM-powered proposer instead of the deterministic default:

```python
from autark.proposers import CodexCliProposer

report = await evolve(
    runner=MyRunner(),
    cases="cases.json",
    artifacts="./prompts/",
    proposer=CodexCliProposer(),  # or GeminiCliProposer(), ClaudeCodeProposer()
)
```

## Files

```
plug_minimal/
  demo.py          # The demo script
  cases.json       # 4 test cases (2 addition, 2 subtraction)
  artifacts/
    prompt.txt     # Initial prompt artifact
  README.md        # This file
```
