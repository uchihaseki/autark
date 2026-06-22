from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from autark.adapters.fake import FakeAdapter
from autark.adapters.prompt_agent import PromptAgentAdapter
from autark.core.engine import EngineConfig, EvolutionEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AUTARK evolution kernel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one evolution cycle")
    run_parser.add_argument("--adapter", default="prompt-agent", choices=["prompt-agent", "fake"])
    run_parser.add_argument("--corpus", type=str, default="")
    run_parser.add_argument("--artifact-root", type=str, default="")
    run_parser.add_argument("--output-dir", type=str, default=".autark/output")
    run_parser.add_argument("--commit", action="store_true", help="Commit accepted artifact revisions")
    run_parser.add_argument("--fail-threshold", type=float, default=0.5)
    run_parser.add_argument("--proposer", default="deterministic", choices=["deterministic", "external-command", "claude-code"])
    run_parser.add_argument("--proposer-command", type=str, default="")
    run_parser.add_argument("--proposer-timeout", type=float, default=120.0)
    return parser


def make_adapter(args: argparse.Namespace):
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
    raise ValueError(f"Unsupported adapter: {args.adapter}")


async def run_async(args: argparse.Namespace) -> int:
    adapter = make_adapter(args)
    engine = EvolutionEngine(
        adapter=adapter,
        config=EngineConfig(adapter_name=adapter.name, dry_run=not args.commit),
    )
    report = await engine.run_cycle()
    print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
    return 0 if not report.errors else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_async(args)))


if __name__ == "__main__":
    main()
