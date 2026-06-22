# Prompt Agent Example

This example demonstrates AUTARK without RTD, AutoRTD, or an external LLM.

Run one dry-run cycle:

```bash
cd /data/shuo/workspace/code/autark
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

Commit accepted changes:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --commit
```
