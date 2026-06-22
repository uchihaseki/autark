# AUTARK

Autonomous-Turing Adaptive Reinforcement Kernel.

AUTARK is a general-purpose agent evaluation and self-evolution framework.
It provides a reusable loop for running cases, evaluating outputs, extracting signals,
selecting strategies, proposing changes, rerun-validating revisions, and auditing the cycle.

## Current focus

The first runnable path is a domain-neutral prompt-agent demo. It does not depend on
AutoRTD, RTD business logic, SKILL.md, or any external LLM provider.

## Quick start

```bash
cd /data/shuo/workspace/code/autark
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

The default mode is dry-run. Add `--commit` to write accepted changes to artifacts.
