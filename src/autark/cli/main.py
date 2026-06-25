from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from autark.adapters.fake import FakeAdapter
from autark.adapters.prompt_agent import PromptAgentAdapter
from autark.audit import JsonlEventLog
from autark.core.engine import EngineConfig, EvolutionEngine
from autark.core.models import CycleReport, EvalReport
from autark.plug._discovery import discover as _discover_adapter
from autark.plug._discovery import list_adapter_names as _list_adapter_names


def _add_adapter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--adapter", default="prompt-agent", help="Adapter name (built-in: fake, prompt-agent; or a registered entry-point adapter)")
    parser.add_argument("--corpus", type=str, default="")
    parser.add_argument("--artifact-root", type=str, default="")
    parser.add_argument("--output-dir", type=str, default=".autark/output")
    parser.add_argument("--proposer", default="deterministic", choices=["deterministic", "external-command", "claude-code"])
    parser.add_argument("--proposer-command", type=str, default="")
    parser.add_argument("--proposer-timeout", type=float, default=120.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AUTARK evolution kernel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- run ----
    run_parser = subparsers.add_parser("run", help="Run one full evolution cycle")
    _add_adapter_args(run_parser)
    run_parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit accepted artifact revisions. The default is dry-run.",
    )
    run_parser.add_argument("--json", action="store_true", help="Print only the machine-readable JSON cycle report")
    run_parser.add_argument("--fail-threshold", type=float, default=0.5)

    # ---- eval ----
    eval_parser = subparsers.add_parser("eval", help="Run cases + evaluate + extract signals (no changes)")
    _add_adapter_args(eval_parser)
    eval_parser.add_argument("--json", action="store_true", help="Print only the machine-readable JSON eval report")

    # ---- propose ----
    propose_parser = subparsers.add_parser("propose", help="Generate candidate changes from saved eval state")
    _add_adapter_args(propose_parser)
    propose_parser.add_argument("--json", action="store_true", help="Print only the machine-readable JSON proposal list")

    # ---- validate ----
    validate_parser = subparsers.add_parser("validate", help="Validate saved proposals (dry-run by default)")
    _add_adapter_args(validate_parser)
    validate_parser.add_argument("--commit", action="store_true", help="Commit accepted artifact revisions")
    validate_parser.add_argument("--json", action="store_true", help="Print only the machine-readable JSON decisions")

    # ---- audit ----
    audit_parser = subparsers.add_parser("audit", help="View the event log")
    audit_parser.add_argument("--output-dir", type=str, default=".autark/output")
    audit_parser.add_argument("--json", action="store_true", help="Print raw events as JSON")
    audit_parser.add_argument("--limit", type=int, default=0, help="Limit to last N events")

    # ---- list-adapters ----
    subparsers.add_parser("list-adapters", help="List all registered AUTARK adapters")

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing_file(path_value: str, option_name: str) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        raise ValueError(f"{option_name} does not exist or is not a file: {path}")
    return path


def _existing_dir(path_value: str, option_name: str) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_dir():
        raise ValueError(f"{option_name} does not exist or is not a directory: {path}")
    return path


def validate_args(args: argparse.Namespace) -> None:
    if getattr(args, "proposer", "") == "external-command" and not getattr(args, "proposer_command", ""):
        raise ValueError("--proposer-command is required when --proposer external-command is used")

    if args.adapter == "fake":
        _existing_file(args.corpus, "--corpus")
        return

    if args.adapter == "prompt-agent":
        _existing_file(args.corpus, "--corpus")
        _existing_dir(args.artifact_root, "--artifact-root")
        return

    # Try discovery for third-party adapters registered via entry points.
    try:
        _discover_adapter(args.adapter)
    except ValueError:
        available = _list_adapter_names()
        hint = f" Available: {', '.join(available)}." if available else ""
        raise ValueError(f"Unknown adapter: {args.adapter}.{hint} Use --help or 'autark list-adapters' to see registered adapters.")


def make_adapter(args: argparse.Namespace):
    validate_args(args)
    if args.adapter == "fake":
        return FakeAdapter.from_json(
            corpus_path=Path(args.corpus) if args.corpus else None,
            output_dir=Path(args.output_dir),
        )
    if args.adapter == "prompt-agent":
        return PromptAgentAdapter(
            corpus_path=Path(args.corpus) if args.corpus else None,
            artifact_root=Path(args.artifact_root) if args.artifact_root else None,
            output_dir=Path(args.output_dir),
            proposer_name=args.proposer,
            proposer_command=args.proposer_command or None,
            proposer_timeout=args.proposer_timeout,
        )

    # Third-party adapter via entry-point discovery.
    # Instantiate with standard adapter constructor signature.
    adapter_cls = _discover_adapter(args.adapter)
    return adapter_cls(
        corpus_path=Path(args.corpus) if args.corpus else None,
        artifact_root=Path(args.artifact_root) if args.artifact_root else None,
        output_dir=args.output_dir,
        proposer_name=getattr(args, "proposer", "deterministic"),
        proposer_command=getattr(args, "proposer_command", None) or None,
        proposer_timeout=getattr(args, "proposer_timeout", 120.0),
    )


def format_phase_title(label: str) -> str:
    return f"AUTARK {label}"


def format_eval_summary(report: EvalReport, *, output_dir: str) -> str:
    lines = [
        format_phase_title("eval complete"),
        f"  cycle: {report.cycle_id}",
        f"  adapter: {report.adapter_name}",
        f"  cases: {report.total_cases} total, {report.failures} failed",
        f"  signals: {report.signals_extracted} extracted",
        f"  state saved: {Path(output_dir) / 'eval_state.json'}",
    ]
    if report.errors:
        lines.append("  errors:")
        lines.extend(f"    - {e}" for e in report.errors)
    return "\n".join(lines)


def format_propose_summary(changes: list[dict], *, output_dir: str) -> str:
    lines = [
        format_phase_title("propose complete"),
        f"  changes: {len(changes)} proposed",
    ]
    for c in changes:
        lines.append(f"    - {c.get('change_id', '?')} -> {c.get('artifact_id', '?')} ({c.get('rationale', '')[:60]})")
    lines.append(f"  proposals saved: {Path(output_dir) / 'proposals.json'}")
    return "\n".join(lines)


def format_validate_summary(decisions: list[dict], accepted: int, rejected: int, *, dry_run: bool, output_dir: str) -> str:
    mode = "dry-run" if dry_run else "commit"
    lines = [
        format_phase_title("validate complete"),
        f"  mode: {mode}",
        f"  decisions: {accepted} accepted, {rejected} rejected",
    ]
    for d in decisions:
        lines.append(f"    - {d.get('change_id', '?')}: {d.get('decision', '?')}")
    lines.append(f"  decisions saved: {Path(output_dir) / 'decisions.json'}")
    if dry_run and accepted:
        lines.append("  note: dry-run mode did not write accepted artifact revisions; pass --commit to write them")
    return "\n".join(lines)


def format_audit_summary(events: list[dict], *, path: str) -> str:
    lines = [
        format_phase_title("audit"),
        f"  source: {path}",
        f"  events: {len(events)}",
    ]
    if not events:
        return "\n".join(lines)
    for ev in events[-10:]:
        eid = ev.get("event_id", "")[:8]
        etype = ev.get("event_type", "?")
        ts = ev.get("timestamp", "")[:19]
        lines.append(f"  [{ts}] {etype} ({eid})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def _run_eval(args: argparse.Namespace) -> int:
    adapter = make_adapter(args)
    engine = EvolutionEngine(adapter, EngineConfig(
        adapter_name=adapter.name,
        dry_run=True,
        output_dir=args.output_dir,
    ))
    report = await engine.run_eval()
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print(format_eval_summary(report, output_dir=args.output_dir))
    return 0 if not report.errors else 1


async def _run_propose(args: argparse.Namespace) -> int:
    adapter = make_adapter(args)
    engine = EvolutionEngine(adapter, EngineConfig(
        adapter_name=adapter.name,
        dry_run=True,
        output_dir=args.output_dir,
    ))
    changes = await engine.run_propose()
    changes_dicts = [asdict(c) for c in changes]
    if args.json:
        print(json.dumps(changes_dicts, ensure_ascii=False, indent=2))
    else:
        print(format_propose_summary(changes_dicts, output_dir=args.output_dir))
    return 0


async def _run_validate(args: argparse.Namespace) -> int:
    adapter = make_adapter(args)
    engine = EvolutionEngine(adapter, EngineConfig(
        adapter_name=adapter.name,
        dry_run=not getattr(args, "commit", False),
        output_dir=args.output_dir,
    ))
    decisions, accepted, rejected = await engine.run_validate()
    decisions_dicts = [asdict(d) for d in decisions]
    if args.json:
        print(json.dumps({"accepted": accepted, "rejected": rejected, "decisions": decisions_dicts}, ensure_ascii=False, indent=2))
    else:
        print(format_validate_summary(decisions_dicts, accepted, rejected, dry_run=not getattr(args, "commit", False), output_dir=args.output_dir))
    return 0


def _run_audit(args: argparse.Namespace) -> int:
    log = JsonlEventLog(args.output_dir + "/events.jsonl")
    events = log.read_all(limit=args.limit or None)
    if args.json:
        print(json.dumps(events, ensure_ascii=False, indent=2))
    else:
        print(format_audit_summary(events, path=str(Path(args.output_dir) / "events.jsonl")))
    return 0


def format_cycle_summary(report: CycleReport, *, dry_run: bool, output_dir: str) -> str:
    mode = "dry-run" if dry_run else "commit"
    lines = [
        "AUTARK cycle complete",
        f"  cycle: {report.cycle_id}",
        f"  adapter: {report.adapter_name}",
        f"  mode: {mode}",
        f"  cases: {report.total_cases} total, {report.failures} failed",
        f"  signals: {report.signals_extracted} extracted",
        f"  strategies: {report.strategies_selected} selected",
        f"  changes: {report.changes_accepted} accepted, {report.changes_rejected} rejected",
        f"  artifacts modified: {', '.join(report.artifacts_modified) if report.artifacts_modified else 'none'}",
        f"  audit: {Path(output_dir) / 'events.jsonl'}",
    ]

    if dry_run and report.changes_accepted:
        lines.append("  note: dry-run mode did not write accepted artifact revisions; pass --commit to write them")
    elif not dry_run and report.changes_accepted:
        lines.append("  note: accepted artifact revisions were committed")

    if report.errors:
        lines.append("  errors:")
        lines.extend(f"    - {error}" for error in report.errors)

    return "\n".join(lines)


async def _run_full_cycle(args: argparse.Namespace) -> int:
    adapter = make_adapter(args)
    engine = EvolutionEngine(
        adapter=adapter,
        config=EngineConfig(
            adapter_name=adapter.name,
            dry_run=not args.commit,
            output_dir=args.output_dir,
        ),
    )
    report = await engine.run_cycle()
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print(format_cycle_summary(report, dry_run=not args.commit, output_dir=args.output_dir))
    return 0 if not report.errors else 1


def _run_list_adapters(_args: argparse.Namespace) -> int:
    names = _list_adapter_names()
    if not names:
        print("No adapters registered.")
        print("Install a package with an 'autark.adapters' entry point, or use built-in adapters: fake, prompt-agent.")
        return 0
    print("Registered adapters:")
    for name in names:
        print(f"  - {name}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def dispatch(args: argparse.Namespace) -> int:
    if args.command == "run":
        return await _run_full_cycle(args)
    if args.command == "eval":
        return await _run_eval(args)
    if args.command == "propose":
        return await _run_propose(args)
    if args.command == "validate":
        return await _run_validate(args)
    if args.command == "audit":
        return _run_audit(args)
    if args.command == "list-adapters":
        return _run_list_adapters(args)
    return 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(dispatch(args)))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
