# External Proposer Contract

AUTARK can delegate change generation to an external command through `ExternalCommandProposer`.

The external command receives a JSON payload on stdin and must print a JSON object representing a `CandidateChange` on stdout.

This allows AUTARK to integrate with shell scripts, local tools, internal agents, or optional LLM-powered repair engines without making them core dependencies.

## Invocation

The proposer is selected through the CLI:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --proposer external-command \
  --proposer-command "python path/to/proposer.py"
```

The command is executed with JSON stdin and captured stdout.

## Input Payload

The input payload has this shape:

```json
{
  "signal": {
    "signal_id": "sig-123",
    "case_id": "case-1",
    "artifact_id": "prompt.txt",
    "signal_type": "failure",
    "category": "wrong_answer",
    "evidence": "Expected 4, got 5.",
    "scores": {"overall": 0.2},
    "metadata": {}
  },
  "strategy": {
    "strategy_id": "strategy-1",
    "name": "Improve correctness",
    "category": "repair",
    "signals_match": ["wrong_answer"],
    "instructions": ["Compute and verify the answer."],
    "constraints": {},
    "validation": ["Rerun failing and holdout cases."],
    "preconditions": [],
    "metadata": {}
  },
  "artifact": {
    "artifact_id": "prompt.txt",
    "content": "Current artifact content",
    "metadata": {}
  },
  "context": {
    "cycle_id": "cycle-123",
    "failing_cases": [],
    "holdout_cases": [],
    "eval_results": [],
    "metadata": {}
  }
}
```

The exact fields follow the dataclasses in `autark.core.models`.

## Output Payload

The command must print a JSON object that can be converted into `CandidateChange`:

```json
{
  "change_id": "chg-custom-001",
  "artifact_id": "prompt.txt",
  "operations": [
    {
      "operation": "append",
      "text": "Always compute and verify the answer before responding."
    }
  ],
  "rationale": "The failing case indicates an arithmetic correctness issue.",
  "validation_plan": [
    "Rerun the failing case.",
    "Check holdout cases for regressions."
  ],
  "metadata": {
    "source": "external-command"
  }
}
```

If `change_id` is omitted, AUTARK generates one. If `artifact_id` is omitted, AUTARK uses the signal artifact id. If `validation_plan` is omitted, AUTARK uses the selected strategy validation plan.

## Supported Text Operations

The current file artifact helpers support simple text operations such as:

- `append` — append text to the artifact.
- `replace` — replace matching text.

Check `autark.artifacts` for the exact operation behavior before relying on advanced patch formats.

## Exit Codes and Errors

- Exit code `0` means stdout should contain valid JSON.
- Non-zero exit codes are treated as proposer failures.
- Invalid JSON is treated as proposer failure.
- Timeouts are controlled by `--proposer-timeout`.

## Safety Requirements

External proposers should:

- return candidate changes only;
- never commit or overwrite artifacts directly;
- include a clear rationale;
- include a validation plan;
- avoid network calls unless explicitly configured by the user;
- avoid reading secrets unless clearly documented and authorized;
- keep output deterministic when possible;
- fail closed when uncertain.

## Minimal Python Example

```python
import json
import sys

payload = json.load(sys.stdin)
signal = payload["signal"]
strategy = payload["strategy"]

change = {
    "artifact_id": signal["artifact_id"],
    "operations": [
        {
            "operation": "append",
            "text": "Follow the task constraints explicitly before answering."
        }
    ],
    "rationale": f"Repair {signal['category']} using {strategy['name']}.",
    "validation_plan": strategy.get("validation", []),
    "metadata": {"source": "minimal-example"},
}

print(json.dumps(change))
```
