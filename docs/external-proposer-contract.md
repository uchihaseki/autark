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

## Testing Your External Proposer

### Manual Validation

Before wiring the proposer into a full AUTARK cycle, validate it manually:

```bash
# Construct a test payload and pipe it to your proposer
python3 -c "
import json
payload = {
    'signal': {
        'signal_id': 'sig-001',
        'case_id': 'case-001',
        'artifact_id': 'prompt.txt',
        'category': 'wrong_answer',
        'evidence': 'Expected 5, got 3',
        'scores': {'overall': 0.2}
    },
    'strategy': {
        'strategy_id': 'strat-001',
        'name': 'Repair Wrong Answer',
        'instructions': ['Fix the prompt.'],
        'validation': ['Rerun cases.']
    },
    'artifact': {
        'artifact_id': 'prompt.txt',
        'content': 'You are a helpful assistant.'
    },
    'context': {
        'cycle_id': 'test-cycle',
        'failing_cases': [],
        'holdout_cases': []
    }
}
print(json.dumps(payload))
" | python your_proposer.py | python -m json.tool
```

The output must be valid JSON with at minimum `artifact_id` and `operations` fields.

### Dry-Run Test

Run a full AUTARK cycle in dry-run mode:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --proposer external-command \
  --proposer-command "python your_proposer.py" \
  --output-dir .autark/output
```

Dry-run means no artifacts are actually modified. Check `.autark/output/decisions.json`
to see validation results.

### Automated Test

Write a pytest that exercises the JSON contract:

```python
import sys
import json
import subprocess
from autark.proposers import ExternalCommandProposer

# Build test fixtures (signal, strategy, artifact, context)
# ...

proposer = ExternalCommandProposer(f"{sys.executable} your_proposer.py", timeout=10)
change = proposer.propose(signal, strategy, artifact, context)

assert change.artifact_id == "prompt.txt"
assert len(change.operations) >= 1
assert change.operations[0]["operation"] in {"append", "replace"}
```

## Troubleshooting

### JSON Parse Error

If AUTARK reports "could not parse JSON from output", your proposer may be
outputting extra text before or after the JSON object. Ensure:

- Your proposer prints **only** the JSON object to stdout
- Debug messages go to stderr (e.g., `print("debug", file=sys.stderr)`)
- No trailing commas in JSON output
- Strings are properly escaped

### Timeout

If the proposer times out, increase the timeout:

```bash
autark run --proposer-timeout 600 ...
```

Or optimize the proposer to return faster (reduce model calls, simplify logic).

### Exit Code Non-Zero

A non-zero exit code means the proposer failed. AUTARK reports the stderr.
Common causes:

- Missing Python dependencies in the proposer script
- Permission errors when reading/writing files
- Shell script syntax errors (use `bash -x proposer.sh` to debug)

### Proposer Command Not Found

If you see "CLI not found", verify the command is executable:

```bash
which python  # or the command you're using
chmod +x your_proposer.sh  # if using a shell script
```

Use an absolute path to the proposer script if relative paths don't work.

## Shell Script Example

See `examples/shell_proposer/proposer.sh` for a complete bash implementation
that reads JSON from stdin and outputs a `CandidateChange` to stdout.

## Key Constraints

External proposers must follow these rules to work correctly with AUTARK:

1. **Read from stdin, write to stdout** — no files, no network (unless configured)
2. **Exit code 0 on success** — anything else is treated as failure
3. **Output valid JSON only** — no logging, no progress bars on stdout
4. **Include `after_scores` in metadata** — used by MetadataScoreValidationGate
5. **Include `signal_id` in metadata** — used by the engine to match changes to cases
6. **Fail closed when uncertain** — return an error exit code rather than a low-quality change
