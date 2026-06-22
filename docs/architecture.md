# AUTARK Architecture

AUTARK separates the self-evolution loop into a domain-agnostic kernel and domain adapters.

## Loop

`EvalCase -> RunResult -> EvalResult -> Signal -> Strategy -> CandidateChange -> ValidationDecision -> Audit`

## Layers

### core

Protocols, dataclasses, and `EvolutionEngine` orchestration. The engine wires an `Adapter` and runs
a full cycle: load cases, run + evaluate, extract signals, select strategies, propose changes,
rerun-validate, and audit decisions.

Key types (all in `autark.core`):

- **Protocols** (`protocols.py`):
  `CaseProvider` / `AgentRunner` / `Evaluator` / `SignalExtractor` /
  `StrategySelector` / `ChangeProposer` / `ArtifactStore` /
  `RerunValidationGate` / `AuditStore` / `Adapter`
- **Models** (`models.py`):
  `EvalCase`, `RunResult`, `EvalResult`, `Signal`, `Strategy`,
  `ArtifactSnapshot`, `EvolutionContext`, `CandidateChange`,
  `ArtifactRevision`, `ValidationDecision`, `CycleReport`
- **Engine** (`engine.py`):
  `EngineConfig`, `EvolutionEngine`
- **Errors** (`exceptions.py`):
  `AutarkError`, `AdapterError`, `ValidationError`

The core must **not** import RTD, SKILL.md, AutoRTD, or any specific business workflow.

### evaluation

Reusable evaluators, metrics, and rubric helpers (`autark.evaluation`).

- `HeuristicEvaluator` — rule-based scoring with task-success / answer-quality / constraint-satisfaction dimensions.
- `weighted_overall()` / `grade_from_score()` — scoring utilities.
- `RubricDimension`, `DEFAULT_AGENT_RUBRIC`, `DEFAULT_FAILURE_CATEGORIES` — configurable rubrics.

### signals

Failure signal extraction and prioritization (`autark.signals`).

- `ThresholdSignalExtractor` — converts failed `EvalResult`s into `Signal` objects based on score thresholds.

### strategies

Strategy matching and reusable evolution policies (`autark.strategies`).

- `RegexStrategySelector` — matches failure signals to strategies by signal category.
- `JsonStrategyStore` — loads strategies from JSON.
- `Capsule` / `StrategyPreset` / `make_strategy()` — strategy definition helpers.

### proposers

Change generation backends (`autark.proposers`). Each proposer receives
`Signal + Strategy + ArtifactSnapshot + EvolutionContext` and returns a `CandidateChange`.
Proposers must not commit changes directly — AUTARK stages, validates, and only commits when
explicitly allowed.

- `DeterministicProposer` — rule-based prompt patch generation. Default, no LLM dependency.
- `ExternalCommandProposer` — delegates to an external CLI via JSON stdin/stdout.
- `ClaudeCodeProposer` — stub for future Claude Code integration; not a core dependency.

### artifacts

Artifact read / stage / commit / rollback (`autark.artifacts`).

- `FileArtifactStore` — file-system backed store with staging.
- `InMemoryArtifactStore` — in-memory store for testing and the fake adapter.
- `apply_text_operations()` — applies replace/append operations to artifact text.

### validation

Reusable rerun and score gates, and accept/reject decisions (`autark.validation`).

- `RerunValidationGate` — generic rerun gate: patches an artifact, reruns failing and holdout
  cases through an injected evaluator, then decides accept / needs-watch / reject based on
  score improvement and holdout regression.
- `MetadataScoreValidationGate` — lightweight gate that compares `before_scores` / `after_scores`
  from change metadata without re-executing cases. Used by the fake adapter.

Adapter-specific subclasses:

- `PromptAgentValidationGate` (in `adapters/prompt_agent/`) — extends `RerunValidationGate`,
  overriding `_run_case_with_artifact` to exercise the patched prompt through the prompt-agent runner.

The validation gate is plugged in per adapter via `Adapter.validation_gate() -> RerunValidationGate`.

### audit

JSONL event log and feedback persistence (`autark.audit`).

- `JsonlEventLog` — appends event dicts to a JSONL file.
- `FeedbackRepo` — structured feedback storage.

### adapters

Domain-specific wiring (`autark.adapters`). Each adapter provides a full set of components
satisfying the core protocols:

- `FakeAdapter` — minimal in-memory adapter for testing. Uses
  `StaticCaseProvider`, `FakeRunner`, `HeuristicEvaluator`,
  `ThresholdSignalExtractor`, `RegexStrategySelector`,
  `DeterministicProposer`, `InMemoryArtifactStore`,
  `MetadataScoreValidationGate`, `JsonlEventLog`.
- `PromptAgentAdapter` — prompt-as-artifact evolution adapter. Uses
  `PromptCaseProvider`, `PromptAgentRunner`, `PromptAgentEvaluator`,
  `ThresholdSignalExtractor`, `RegexStrategySelector` (with `PROMPT_AGENT_STRATEGIES`),
  configurable proposer, `PromptArtifactStore`, `PromptAgentValidationGate`,
  `JsonlEventLog`.

### cli

Entry point (`autark.cli.main`). The `autark` console script dispatches `run` with adapter,
corpus, artifact-root, output-dir, and dry-run / commit flags.

## Filesystem layout

```
src/autark/
  __init__.py
  core/           models.py, protocols.py, engine.py, exceptions.py
  evaluation/     judge.py, metrics.py, rubrics.py
  signals/        extractor.py
  strategies/     selector.py, store.py, gene.py
  proposers/      deterministic.py
  artifacts/      base.py, filesystem.py
  validation/     gate.py
  audit/          event_log.py, feedback_repo.py
  adapters/       fake.py, prompt_agent/
  cli/            main.py
```

## Constraint summary

- Core must not import RTD, SKILL.md, AutoRTD, or any specific business workflow.
- Proposers must not commit directly.
- Claude Code / external code agents are proposer backends only, not framework dependencies.
- Each adapter owns its runner, evaluator, artifact store, strategy pack, and validation gate.
