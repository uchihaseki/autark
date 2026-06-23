# AUTARK

AUTARK (Autonomous-Turing Adaptive Reinforcement Kernel) is a framework for safe, auditable agent self-improvement.

It helps teams run agent cases, evaluate behavior, extract failure signals, select improvement strategies, propose artifact changes, validate them against regressions, and keep an audit trail for every cycle.

```text
EvalCase -> RunResult -> EvalResult -> Signal -> Strategy -> CandidateChange -> ValidationDecision -> Audit
```

## Why AUTARK

Agent systems often improve through scattered prompt edits, ad hoc evals, and manual regression checks. AUTARK turns that process into a repeatable loop:

- **Evaluation-first evolution** — improvements are driven by observed failures.
- **Artifact-agnostic design** — artifacts can be prompts, policies, workflows, tool configs, rubrics, or other agent assets.
- **Validation before commit** — changes are staged, rerun, checked for regressions, and only committed when explicitly requested.
- **Auditable history** — every run can record cases, scores, signals, proposals, and validation decisions.
- **Adapter-based integration** — bring your own runner, evaluator, proposer, artifact store, validation gate, and audit store.

## Current Status

AUTARK is currently an early `0.1.0` MVP. The first runnable path is a dependency-light prompt-agent demo that does not require AutoRTD, RTD business logic, `SKILL.md`, or an external LLM provider.

The core APIs are useful but still evolving. Expect breaking changes before `1.0.0`.

## Quick Start

```bash
git clone <your-autark-repo-url>
cd autark
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

The default behavior is dry-run: accepted changes are staged and validated, but artifacts are not overwritten. By default the command prints a human-readable cycle summary.

Use `--json` when scripts or CI need the machine-readable cycle report:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --json
```

To commit accepted artifact revisions, pass `--commit` explicitly:

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --commit
```

### Step-by-Step Commands

The loop can also run in separate phases:

```bash
# Evaluate only — run cases, score outputs, extract failure signals
autark eval --adapter prompt-agent --corpus cases.json --artifact-root artifacts/ --output-dir .autark/output

# Propose — generate candidate artifact changes from saved eval state
autark propose --adapter prompt-agent --corpus cases.json --artifact-root artifacts/ --output-dir .autark/output

# Validate — rerun and score proposed changes (dry-run by default)
autark validate --adapter prompt-agent --corpus cases.json --artifact-root artifacts/ --output-dir .autark/output

# Audit — view the event log
autark audit --output-dir .autark/output
```

Use `--json` with any command for machine-readable output.

## Core Concepts

- **EvalCase** — an input, expected behavior, and metadata for one evaluation case.
- **RunResult** — output and trajectory from running an agent on a case.
- **EvalResult** — scores, status, category, and evidence for a run.
- **Signal** — a structured failure or improvement opportunity extracted from eval results.
- **Strategy** — a policy for how to repair a class of failure.
- **CandidateChange** — a proposed patch to an artifact, with rationale and validation plan.
- **ValidationDecision** — accept, reject, or watch decision after rerunning checks.
- **Audit** — persisted event history for the cycle.

See `docs/core-concepts.md` for details.

## Architecture

AUTARK keeps the core domain-neutral. Domain-specific behavior belongs in adapters.

```text
src/autark/
  core/           protocols, dataclasses, engine, exceptions
  evaluation/     reusable evaluators, metrics, rubrics
  signals/        failure signal extraction
  strategies/     strategy matching and reusable policies
  proposers/      deterministic and external change proposers
  artifacts/      artifact staging, commit, rollback
  validation/     rerun and score gates
  audit/          JSONL event log and feedback persistence
  adapters/       domain-specific wiring
  cli/            command-line entry point
```

Read more in `docs/architecture.md`.

## Extending AUTARK

The main extension point is an adapter. An adapter wires together:

- `CaseProvider`
- `AgentRunner`
- `Evaluator`
- `SignalExtractor`
- `StrategySelector`
- `ChangeProposer`
- `ArtifactStore`
- `RerunValidationGate`
- `AuditStore`

Start with `docs/adapter-guide.md`, then inspect `src/autark/adapters/fake.py` and `src/autark/adapters/prompt_agent/`.

## External Proposers

AUTARK can delegate change generation to an external command. The command receives JSON on stdin and must return a `CandidateChange` JSON object on stdout.

See `docs/external-proposer-contract.md` for the contract and safety expectations.

## Documentation

- `docs/quickstart.md` — install and run the prompt-agent demo.
- `docs/core-concepts.md` — model and loop terminology.
- `docs/architecture.md` — package layout and boundaries.
- `docs/adapter-guide.md` — how to integrate a new agent domain.
- `docs/external-proposer-contract.md` — JSON contract for CLI-based proposers.
- `docs/open_source_roadmap.md` — roadmap toward a mature open-source project.

## Development

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

## Safety Model

AUTARK is designed to make agent improvement safer and more inspectable:

- dry-run is the default;
- proposers return candidate changes instead of committing directly;
- artifact stores stage changes before commit;
- validation gates can reject regressions;
- accepted and rejected decisions are auditable.

Do not use AUTARK to perform destructive actions, unauthorized testing, credential misuse, stealth, evasion, or mass targeting. See `SECURITY.md`.

## Roadmap

Near-term priorities:

1. Improve public docs and examples.
2. Stabilize adapter and external proposer contracts.
3. Add richer CLI modes such as `eval`, `propose`, `validate`, and `audit`.
4. Add more realistic adapters beyond the prompt-agent demo.
5. Strengthen validation and regression reporting.

See `docs/open_source_roadmap.md` for the full roadmap.

## Contributing

Contributions are welcome. Good starting areas include docs, adapters, evaluators, proposers, validation policies, and examples.

Read `CONTRIBUTING.md` before opening a pull request.

## License

MIT. See `LICENSE`.
