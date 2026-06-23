# Adapter Guide

Adapters connect AUTARK's domain-neutral evolution loop to a specific agent domain.

An adapter owns all domain-specific behavior. The core engine should not know whether it is improving a prompt, workflow, policy, rubric, tool config, or another artifact type.

## Adapter Responsibilities

An adapter must provide implementations for the protocols in `autark.core.protocols`:

```python
class Adapter(Protocol):
    name: str

    def case_provider(self) -> CaseProvider: ...
    def agent_runner(self) -> AgentRunner: ...
    def evaluator(self) -> Evaluator: ...
    def signal_extractor(self) -> SignalExtractor: ...
    def strategy_selector(self) -> StrategySelector: ...
    def change_proposer(self) -> ChangeProposer: ...
    def artifact_store(self) -> ArtifactStore: ...
    def validation_gate(self) -> RerunValidationGate: ...
    def audit_store(self) -> AuditStore: ...
```

## Components

### CaseProvider

Loads evaluation cases.

```python
def load_cases(self) -> list[EvalCase]: ...
```

Cases can come from JSON, a database, an eval platform, or generated fixtures.

### AgentRunner

Runs the target agent on one case.

```python
async def run_case(self, case: EvalCase) -> RunResult: ...
```

The runner should record enough output and trajectory information for evaluators and audits to explain behavior.

### Evaluator

Scores one run result.

```python
async def evaluate(self, case: EvalCase, run_result: RunResult) -> EvalResult: ...
```

Evaluators can be exact-match, heuristic, rubric-based, model-judged, or fully domain-specific.

### SignalExtractor

Turns eval results into structured failure signals.

```python
def extract(self, eval_results: list[EvalResult], recent_signals: list[Signal] | None = None) -> list[Signal]: ...
```

A simple extractor may emit one signal per failed case. A richer extractor may deduplicate repeated failures or prioritize high-severity categories.

### StrategySelector

Maps signals to repair strategies.

```python
def select_all(self, signals: list[Signal]) -> list[tuple[Signal, Strategy]]: ...
```

Strategies should describe repair intent and validation expectations without mutating artifacts.

### ChangeProposer

Creates a candidate change for a signal and strategy.

```python
def propose(
    self,
    signal: Signal,
    strategy: Strategy,
    artifact: ArtifactSnapshot,
    context: EvolutionContext,
) -> CandidateChange: ...
```

Proposers must not commit changes directly. They return `CandidateChange` objects for AUTARK to stage, validate, and optionally commit.

### ArtifactStore

Loads and manages artifact revisions.

```python
def load(self, artifact_id: str) -> str: ...
def stage(self, artifact_id: str, candidate_change: CandidateChange) -> ArtifactRevision: ...
def commit(self, revision: ArtifactRevision) -> bool: ...
def rollback(self, revision: ArtifactRevision) -> bool: ...
```

Artifact stores should make rollback safe and predictable.

### RerunValidationGate

Validates candidate changes before commit.

```python
async def validate(
    self,
    candidate_change: CandidateChange,
    failing_cases: list[EvalCase],
    holdout_cases: list[EvalCase] | None = None,
) -> ValidationDecision: ...
```

Validation should check improvement on failing cases and avoid regressions on holdout cases where possible.

### AuditStore

Persists important cycle events.

```python
def append_event(self, event: dict[str, Any]) -> None: ...
```

JSONL is a good default because it is easy to inspect, stream, and post-process.

## Recommended Adapter Layout

```text
src/autark/adapters/my_domain/
  __init__.py
  adapter.py
  corpus.py
  runner.py
  evaluator.py
  strategies.py
  artifact_store.py
  validation.py
```

For small adapters, it is fine to keep several components in one file. Split them when tests or examples become hard to read.

## Implementation Steps

1. Define the artifact type you want to evolve.
2. Define the case format and implement a `CaseProvider`.
3. Implement an `AgentRunner` that uses the current artifact.
4. Implement or reuse an `Evaluator`.
5. Choose or implement a `SignalExtractor`.
6. Define strategies and wire a `StrategySelector`.
7. Choose a proposer, such as deterministic or external-command.
8. Implement an `ArtifactStore` with safe stage/commit/rollback behavior.
9. Implement a validation gate.
10. Add tests and an example README.

## Safety Checklist

- Dry-run works and does not modify artifacts.
- `--commit` or equivalent explicit intent is required for writes.
- Rollback is tested.
- The proposer cannot bypass staging and validation.
- External services and credentials are optional and documented.
- Audit output explains both accepted and rejected changes.
- Domain-specific logic stays outside `autark.core`.

## Existing Examples

Start with these implementations:

- `src/autark/adapters/fake.py` — compact in-memory adapter for tests.
- `src/autark/adapters/prompt_agent/` — prompt-as-artifact demo adapter.
- `examples/prompt_agent/` — runnable example cases and artifact.
