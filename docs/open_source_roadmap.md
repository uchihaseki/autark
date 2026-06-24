# AUTARK Open Source Roadmap

## Purpose

AUTARK aims to become a mature open-source framework for evaluating, diagnosing, and self-improving agents through a safe, auditable evolution loop.

The project should not be positioned as a narrow prompt optimizer or an AutoRTD migration. Its long-term value is a reusable kernel that can evolve many kinds of agent artifacts:

- prompts
- policies
- workflows
- tool configurations
- rubrics
- lightweight code or configuration patches

The core promise should be:

> Run agent cases, evaluate behavior, extract failure signals, propose changes, validate them against regressions, and keep an auditable trail.

## Current Baseline

The repository has progressed well beyond the initial MVP.

**Completed (as of June 2026):**

- A domain-neutral core loop in `autark.core` with phased methods (`run_eval`, `run_propose`, `run_validate`) and intermediate state persistence.
- Protocol boundaries for all 10 extension points.
- Three working proposers: Deterministic, ExternalCommand, and ClaudeCode.
- Five CLI subcommands: `run`, `eval`, `propose`, `validate`, `audit`, all with human-readable and `--json` output.
- A runnable `prompt-agent` demo that works without RTD, AutoRTD, or an external LLM provider.
- File/in-memory artifact stores with stage/commit/rollback semantics.
- Validation gates and JSONL audit logging.
- 31 unit/integration tests passing.
- Complete open-source project infrastructure: README, LICENSE (MIT), CONTRIBUTING, SECURITY, CHANGELOG, CI config, GitHub issue/PR templates.
- Project metadata in `pyproject.toml` (classifiers, keywords, URLs).
- 8 documentation files covering architecture, quickstart, core concepts, adapter guide, external proposer contract, open-source roadmap, and a Chinese overview.


## Positioning

### Recommended Positioning

AUTARK should be described as:

> A framework for safe, auditable agent self-improvement.

It should emphasize four ideas:

1. **Evaluation-first evolution** — changes are driven by observed failures, not blind generation.
2. **Artifact-agnostic design** — the framework can improve prompts, policies, workflows, tools, rubrics, and other agent assets.
3. **Validation before commit** — proposed changes are staged, rerun, checked for regressions, and only committed when explicitly allowed.
4. **Adapter-based integration** — users can bring their own agent runner, evaluator, proposer, artifact store, and validation policy.

### What AUTARK Is Not

Avoid positioning AUTARK as:

- a general AutoML system
- a benchmark suite only
- a prompt optimizer only
- an LLM agent framework that competes directly with LangChain, CrewAI, AutoGen, or similar projects
- a Claude-Code-only wrapper

AUTARK should instead complement existing agent frameworks by adding a structured evolution and validation loop around them.

## Target Users

Primary early users:

- agent developers who need repeatable evaluation and improvement loops
- AI infra teams maintaining prompts, workflows, and tool policies
- researchers experimenting with agent self-improvement
- teams that want auditable prompt or policy changes before production rollout

Secondary users:

- open-source maintainers who want regression-tested prompt/workflow evolution
- companies building internal coding agents or support agents
- evaluation platform builders who need a pluggable evolution kernel

## Core Product Principles

1. **Safety by default**
   - Dry-run must remain the default.
   - Committing changes must require explicit user intent.
   - Proposers should never directly mutate source artifacts.
   - Validation failures should rollback staged changes.

2. **Core stays domain-neutral**
   - No RTD, AutoRTD, product-specific workflow, provider-specific SDK, or business-specific metric should leak into `autark.core`.
   - All domain behavior belongs in adapters.

3. **Everything is inspectable**
   - Reports, proposals, validation decisions, and audit logs should be human-readable.
   - CLI output should explain what changed and why.
   - Every accepted change should be traceable to cases, scores, signals, strategies, and validation results.

4. **Adapters are first-class**
   - The easiest way to adopt AUTARK should be writing an adapter.
   - Adapter interfaces need clear docs, templates, and tests.

5. **Small kernel, rich integrations**
   - Keep the kernel stable and minimal.
   - Add integrations through optional packages, examples, and adapters.

## Roadmap Overview

### Phase 0 — Repository Hygiene and Identity ✅ **DONE**

Goal: make the project presentable and understandable to a first-time GitHub visitor.

Deliverables:

- ✅ Rewrite `README.md` around the public positioning.
- ✅ Add a concise architecture diagram (Chinese overview doc).
- ✅ Add `LICENSE` (MIT).
- ✅ Add `CONTRIBUTING.md`.
- [x] Add `CODE_OF_CONDUCT.md` if community contribution is expected.
- ✅ Add `SECURITY.md` for vulnerability reporting and safe-use boundaries.
- ✅ Add GitHub issue templates (bug report, feature request, adapter proposal).
- ✅ Add PR template with testing checklist.
- [x] Add badges after CI is available (tests, package version, Python versions, license).

### Phase 1 — Reliable MVP ✅ **DONE**

Goal: make the existing prompt-agent path robust enough that users can clone the repo and reliably run it.

Deliverables:

- ✅ `pytest -q` passes (83 tests).
- ✅ CI config for Python 3.10, 3.11, and 3.12 (`.github/workflows/ci.yml`).
- ✅ Type checking with `mypy`.
- ✅ Formatting/linting with `ruff`.
- ✅ Generated files (`.autark/output`, caches, egg-info) are ignored in `.gitignore`.
- ✅ Integration test that runs the prompt-agent demo end-to-end.

CLI improvements:

- ✅ `autark run` as the main full-cycle command, plus `eval`/`propose`/`validate`/`audit`.
- ✅ Clearer dry-run / commit semantics in help text.
- ✅ Human-readable cycle summary + `--json` for machine-readable output.
- ✅ Graceful errors when corpus or artifact paths are missing.

Documentation improvements:

- ✅ `docs/quickstart.md`.
- ✅ `docs/core-concepts.md`.
- ✅ `docs/adapter-guide.md`.
- ✅ `docs/external-proposer-contract.md`.

### Phase 2 — Public API and Extension Model 🔄 **PARTIAL**

Goal: make AUTARK easy to extend without reading all internals.

Deliverables:

- ✅ Protocol interfaces defined and documented in adapter guide.
- ✅ Adapter template under `examples/adapter_template/`.
- ✅ Tests that third-party adapters can copy.
- ✅ Serialization formats for cases, eval results, signals, strategies, candidate changes, validation decisions, cycle reports (used in engine state persistence).
- ✅ Schema docs and JSON Schema files under `schemas/`.

Important design decisions:

- ✅ `0.2.x` public API defined (protocols, models, CLI).
- [ ] Keep experimental APIs clearly marked.
- ✅ Avoid provider-specific dependencies in the default install.
- [x] Use extras for integrations (`autark[anthropic]`, `autark[dev]`).
- ✅ `autark[dev]` extra exists.

### Phase 3 — Stronger Evaluation and Validation

Goal: make the improvement loop trustworthy rather than merely runnable.

Deliverables:

- Add richer evaluator abstractions:
  - heuristic evaluator
  - exact-match evaluator
  - rubric evaluator
  - LLM judge evaluator as optional integration
  - custom Python callback evaluator
- Add regression-aware validation policies:
  - minimum improvement threshold
  - holdout regression threshold
  - confidence / needs-watch mode
  - max changed artifact size
  - allowed operation types
- Add validation reports that compare before/after case outcomes.
- Add support for multiple failing cases per proposal, not only one signal at a time.
- Add configurable batching and parallel execution.
- Add repeat-run support for flaky agents.

Safety requirements:

- Default to no commit.
- Add a clear staged-change preview.
- Add a way to export proposals without applying them.
- Add rollback tests for every artifact store.

### Phase 4 — Proposers and Integrations

Goal: let users plug in real repair engines while keeping the core safe.

Deliverables:

- Improve `ExternalCommandProposer` documentation and examples.
- Define a stable JSON contract for external proposers.
- Add example proposers:
  - deterministic prompt repair
  - shell script proposer
  - Python function proposer
  - optional LLM proposer
- Implement `ClaudeCodeProposer` only as an optional integration, not a core dependency.
- Consider adding `CodexCliProposer`, `GeminiCliProposer`, or generic CLI-agent examples only if they can share the same external-command contract.

Important constraints:

- Proposers return `CandidateChange`; they must not commit directly.
- Proposers should include rationale and validation plan.
- Proposers should be sandbox-friendly and auditable.
- Network/API dependencies should be opt-in.

### Phase 5 — More Real-World Examples

Goal: prove AUTARK is artifact-agnostic and useful beyond the toy prompt-agent demo.

Recommended examples:

1. **Prompt agent**
   - Current demo.
   - Keep it simple and dependency-free.

2. **Tool-use agent policy**
   - Artifact: tool policy or system prompt.
   - Cases: tool selection, refusal, formatting, constraints.

3. **Workflow YAML agent**
   - Artifact: workflow config.
   - Cases: expected steps or outputs.
   - Validation: rerun workflow and compare metrics.

4. **Rubric evolution**
   - Artifact: evaluation rubric.
   - Cases: labeled examples.
   - Validation: agreement with gold labels.

5. **Coding-agent repair loop**
   - Artifact: instruction file or coding policy.
   - Cases: small repo tasks.
   - Validation: tests pass and no regressions.

Each example should include:

- README
- cases
- artifacts
- expected command
- expected output summary
- test coverage

### Phase 6 — Packaging and Releases

Goal: make AUTARK installable and versioned like a normal open-source Python project.

Deliverables:

- Decide package manager workflow: `uv`, `pip`, or both.
- Add build validation with `python -m build`.
- Publish test package to TestPyPI before PyPI.
- Adopt semantic versioning.
- Add `CHANGELOG.md`.
- Tag releases in GitHub.
- Add release notes template.
- Define compatibility policy for public protocols.

Suggested release milestones:

- ✅ `0.1.0` — runnable MVP, prompt-agent demo, deterministic proposer.
- ✅ `0.2.0` — stable CLI, docs, CI, adapter guide, external proposer contract, ClaudeCode proposer.
- `0.3.0` — stronger validation, more examples, LLM judge evaluator, real adapter.
- `0.4.0` — richer evaluators, parallel execution, flaky handling.
- `1.0.0` — stable public protocols, production-quality docs, multiple real examples, compatibility policy.

### Phase 7 — Community and Governance

Goal: make contribution and maintenance sustainable.

Deliverables:

- Add clear contribution paths:
  - add adapter
  - add evaluator
  - add proposer
  - improve docs
  - add example
- Label GitHub issues:
  - `good first issue`
  - `help wanted`
  - `adapter`
  - `evaluator`
  - `proposer`
  - `docs`
  - `safety`
- Add a maintainer checklist for reviewing adapters.
- Add project principles to avoid scope creep.
- Document security and misuse boundaries.

Review checklist for new integrations:

- Does it keep core domain-neutral?
- Does it preserve dry-run safety?
- Does it avoid committing directly from a proposer?
- Does it include tests?
- Does it document required credentials or external services?
- Does it produce auditable output?

## Recommended Near-Term Backlog

### Highest Priority

1. ✅ Rewrite `README.md` for public GitHub users.
2. ✅ Add `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and PR/issue templates.
3. ✅ Make tests and demo pass from a clean clone.
4. ✅ Add GitHub Actions CI.
5. ✅ Add `docs/quickstart.md` and `docs/adapter-guide.md`.
6. [ ] Publish to PyPI (TestPyPI first).
7. ✅ Add `CODE_OF_CONDUCT.md`.

### Medium Priority

1. ✅ Add `autark eval`, `autark propose`, `autark validate`, and `autark audit` commands.
2. ✅ Add `--json` output mode and better human-readable summaries.
3. ✅ Define JSON contracts for external proposers and cycle reports.
4. ✅ Implement ClaudeCodeProposer.
5. ✅ Add project metadata to `pyproject.toml`.
6. [ ] Add at least one more realistic adapter example.

### Later Priority

1. [ ] Optional LLM judge integration.
2. ✅ Claude Code proposer integration implemented (needs real-environment testing).
3. [ ] Parallel case execution.
4. [ ] Flaky-run handling.
5. [ ] Web dashboard or report viewer.
6. [ ] Plugin discovery system.

## Documentation Structure

Recommended `docs/` layout:

```text
docs/
  quickstart.md
  core-concepts.md
  architecture.md
  adapter-guide.md
  evaluator-guide.md
  proposer-guide.md
  validation-guide.md
  external-proposer-contract.md
  examples.md
  safety-model.md
  open_source_roadmap.md
```

Recommended root files:

```text
README.md
LICENSE
CHANGELOG.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
SECURITY.md
.github/workflows/ci.yml
.github/ISSUE_TEMPLATE/bug_report.md
.github/ISSUE_TEMPLATE/feature_request.md
.github/ISSUE_TEMPLATE/adapter_proposal.md
.github/pull_request_template.md
```

## Maturity Checklist

- ✅ A new user can understand the project from the README in under five minutes.
- ✅ A new user can run the demo in under ten minutes.
- ✅ CI runs tests on supported Python versions, plus lint (ruff) and type-check (mypy).
- ✅ The public extension interfaces are documented.
- ✅ At least two non-trivial examples exist (prompt-agent, shell_proposer, adapter_template).
- ✅ Dry-run and commit behavior are obvious and safe.
- ✅ Proposals and validation decisions are auditable.
- ✅ Phase 0 (repository hygiene) and Phase 1 (reliable MVP) are fully complete.
- ✅ Phase 2 (public API, extension model) is substantially complete — schema files, adapter template, extras, and dev tooling in place.
- [ ] Package can be installed from PyPI.
- [ ] Release notes and compatibility expectations are clear.

## Success Metrics

Early project health can be measured by:

- Time to first successful demo run.
- Number of documented adapters/examples.
- Test coverage of the core loop and artifact rollback behavior.
- Number of issues that external contributors can pick up without maintainer context.
- Stability of public protocol interfaces across releases.
- Quality of audit output for accepted and rejected changes.

## Suggested Next Step

Start with a `0.2.0` milestone focused on open-source readiness rather than new intelligence:

1. Public README and docs.
2. CI and clean test workflow.
3. Adapter guide and example template.
4. Safer CLI output and JSON mode.
5. External proposer contract.
6. One additional realistic example beyond prompt-agent.

This sequence will make AUTARK easier to trust, easier to try, and easier for outside contributors to extend.
