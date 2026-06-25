# Quickstart

> 中文版：[快速开始](quickstart-zh.md)

This guide runs AUTARK's dependency-light prompt-agent demo from a local checkout.

## Requirements

- Python 3.10 or newer
- `pip`
- A shell environment that can run Python commands

The current demo does not require an external LLM provider.

## Install

```bash
git clone https://github.com/uchihaseki/autark.git
cd autark
pip install -e ".[dev]"
```

This installs the `autark` CLI in your environment.

## Run the Prompt-Agent Demo

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

This runs one full evolution cycle:

```text
load cases -> run agent -> evaluate -> extract signals -> select strategies -> propose changes -> validate -> audit
```

## Dry-Run by Default

AUTARK defaults to dry-run mode. It can stage and validate candidate changes, but it does not overwrite artifacts unless you explicitly pass `--commit`.

Use dry-run while developing adapters, evaluators, proposers, and validation policies.

## Commit Accepted Changes

Only use `--commit` when you want accepted revisions written back to the artifact store:

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --commit
```

## Output

By default, the command prints a human-readable cycle summary:

```text
AUTARK cycle complete
  adapter: prompt-agent
  mode: dry-run
  cases: 3 total, 1 failed
  changes: 1 accepted, 0 rejected
```

Use `--json` when scripts or CI need the machine-readable cycle report:

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --json
```

Audit events are written under the configured output directory, for example:

```text
.autark/output/events.jsonl
```

The output directory is generated runtime state and should not be committed.

## Step-by-Step Commands

AUTARK supports running the loop in separate phases:

```bash
# Evaluate — run cases, score outputs, extract failure signals
autark eval \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# Propose — generate candidate changes from the saved eval state
autark propose \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# Validate — rerun and score proposed changes (dry-run by default)
autark validate \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# Audit — view the event log
autark audit --output-dir .autark/output
```

Use `--json` with any command for machine-readable output.

## Alternative: Run from Source (No Install)

If you prefer not to install the package, you can run directly with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

## Run Tests

```bash
pytest -q
```

## Troubleshooting

### Import errors

If Python cannot import `autark`, install the package in editable mode:

```bash
pip install -e ".[dev]"
```

### Missing corpus or artifact files

Check that the paths passed to `--corpus` and `--artifact-root` exist relative to the repository root.

### No artifact changes

By default, dry-run mode does not commit accepted revisions. Pass `--commit` only when you intentionally want to write accepted artifact changes.
