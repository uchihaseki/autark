# Changelog

All notable changes to AUTARK will be documented in this file.

The project follows semantic versioning once the public API stabilizes. Before `1.0.0`, protocol and CLI changes may still be breaking.

## Unreleased

- Added open-source readiness documentation and GitHub project templates.
- Added quickstart, core concepts, adapter guide, and external proposer contract docs.
- Added GitHub Actions CI configuration.
- Improved `autark run` with human-readable summaries, `--json` output, safer dry-run messaging, and friendlier input validation.
- Added `autark eval`, `autark propose`, `autark validate`, and `autark audit` subcommands for step-by-step evolution cycles.
- Refactored `EvolutionEngine` into phase methods with intermediate state persistence via `output_dir`.
- Implemented `ClaudeCodeProposer` — delegates change generation to Claude Code CLI via structured prompt and JSON parsing.
- Added project metadata to `pyproject.toml`: classifiers, keywords, URLs.
- Cleaned generated egg-info from tracking; confirmed `.gitignore` coverage.

## 0.1.0

- Initial domain-agnostic AUTARK kernel.
- Added the core evolution loop: cases, runs, evaluation, signals, strategies, proposals, validation, and audit events.
- Added prompt-agent demo with deterministic self-evolution.
- Added fake adapter and in-memory/file artifact stores.
- Added deterministic and external-command proposer paths.
- Added initial tests for the engine, prompt-agent cycle, artifacts, signals, strategies, and validation.
