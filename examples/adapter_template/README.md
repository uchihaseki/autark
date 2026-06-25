# Adapter Template

A minimal AUTARK adapter you can copy and customize for your own agent artifact.

## Quick Start

```bash
cd autark

# Run a full evolution cycle with the minimal adapter
python -c "
import asyncio
from pathlib import Path
from examples.adapter_template.adapter import MinimalAdapter
from autark.core.engine import EvolutionEngine, EngineConfig

adapter = MinimalAdapter(
    corpus_path=Path('examples/adapter_template/cases.json'),
    artifact_root=Path('examples/adapter_template/artifacts'),
    output_dir='.autark/output',
)
engine = EvolutionEngine(adapter, EngineConfig(
    adapter_name='minimal',
    dry_run=True,
    output_dir='.autark/output',
))
report = asyncio.run(engine.run_cycle())
print(f'Cycle {report.cycle_id}: {report.failures} failures, '
      f'{report.changes_accepted} accepted, {report.changes_rejected} rejected')
"
```

## Directory Structure

```
adapter_template/
  adapter.py       # MinimalAdapter class — swap components here
  cases.json       # Evaluation cases
  artifacts/       # Artifact files to evolve
  test_adapter.py  # Example test using shared AdapterTestSuite
  README.md        # This file
```

## Customizing

Replace each factory method in `MinimalAdapter` with your own implementation:

| Method | What to Change |
|--------|---------------|
| `case_provider()` | Load cases from your own format (JSON, CSV, DB) |
| `agent_runner()` | Invoke your actual agent or model |
| `evaluator()` | Score outputs against your own criteria |
| `signal_extractor()` | Custom failure signal extraction logic |
| `strategy_selector()` | Map your own strategies to signal categories |
| `change_proposer()` | Use DeterministicProposer, ExternalCommandProposer, or write your own |
| `artifact_store()` | Switch to InMemoryArtifactStore for testing |
| `validation_gate()` | Use MetadataScoreValidationGate or subclass RerunValidationGate |
| `audit_store()` | Point to a different log file or database |

## Testing

See `test_adapter.py` for an example using the shared `AdapterTestSuite` from
`tests/helpers.py`.
