# Core Concepts

AUTARK models agent improvement as an auditable evolution cycle.

```text
EvalCase -> RunResult -> EvalResult -> Signal -> Strategy -> CandidateChange -> ValidationDecision -> Audit
```

## EvalCase

An `EvalCase` describes one task or scenario that an agent should handle.

It usually includes:

- `case_id`
- input text or structured input
- expected output or target behavior
- metadata such as constraints, labels, or split information

## RunResult

A `RunResult` captures what happened when an agent ran on one case.

It can include:

- status
- output
- trajectory or trace summary
- artifact id used for the run
- runtime metadata

## EvalResult

An `EvalResult` scores a `RunResult` against the case.

It can include:

- pass/fail status
- score dimensions
- failure category
- evidence
- grade
- trajectory summary

Evaluators can be heuristic, exact-match, rubric-based, model-judged, or domain-specific.

## Signal

A `Signal` is a structured improvement opportunity extracted from evaluation results.

Signals answer:

- which case failed;
- which artifact was involved;
- what category of failure occurred;
- what evidence supports the diagnosis;
- which scores indicate the severity.

## Strategy

A `Strategy` describes how AUTARK should attempt to repair a category of failure.

Strategies can include:

- matching rules for signals;
- repair instructions;
- constraints;
- validation requirements;
- metadata for adapter-specific behavior.

## CandidateChange

A `CandidateChange` is a proposed change to an artifact.

It includes:

- `change_id`
- target `artifact_id`
- operations such as append or replace
- rationale
- validation plan
- metadata linking the change to signals, strategies, or cycle context

Proposers create candidate changes, but they should not commit artifacts directly.

## ValidationDecision

A `ValidationDecision` records whether a candidate change should be accepted, rejected, or watched.

Validation can compare:

- before and after scores;
- failing case improvement;
- holdout case regressions;
- operation safety;
- adapter-specific constraints.

## Artifact

An artifact is the asset AUTARK may improve.

Examples:

- prompt
- agent policy
- workflow config
- tool config
- rubric
- lightweight code or configuration patch

Artifact stores are responsible for loading, staging, committing, and rolling back revisions.

## Adapter

An adapter wires AUTARK into a domain. It provides the concrete implementations for running cases, evaluating outputs, proposing changes, validating revisions, and writing audit events.

The core stays domain-neutral; adapters own domain-specific logic.

## Audit

Audit stores persist important cycle events, such as case evaluations and validation decisions.

Audit logs should make it possible to understand:

- what was evaluated;
- what failed;
- what change was proposed;
- why a change was accepted or rejected;
- which artifact was modified when commits are enabled.
