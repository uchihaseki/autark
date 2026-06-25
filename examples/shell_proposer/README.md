# Shell-Script Proposer Example

A minimal example showing how to write an external proposer as a bash script.

## How It Works

AUTARK's `ExternalCommandProposer` sends a JSON payload to the configured command
via stdin. The command must:

1. Read the JSON from stdin
2. Parse the signal, strategy, artifact, and context
3. Output a `CandidateChange` JSON object on stdout

The JSON schema for both input and output is documented in
`docs/external-proposer-contract.md`.

## Usage

```bash
# Run a full cycle using the shell proposer
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --proposer external-command \
  --proposer-command "bash examples/shell_proposer/proposer.sh" \
  --output-dir .autark/output
```

## Testing Manually

```bash
# Test the proposer with a sample JSON input
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
        'instructions': ['Fix the prompt to compute correctly.'],
        'validation': ['Rerun math cases.']
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
" | bash examples/shell_proposer/proposer.sh
```

## Customizing

Copy `proposer.sh` and modify the `case` statement to handle your own failure
categories and repair strategies. For more complex logic, consider writing the
proposer in Python using `PythonFunctionProposer` instead.
