from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import pytest

from autark.cli.main import (
    _run_audit,
    _run_eval,
    _run_full_cycle,
    _run_propose,
    _run_validate,
    build_parser,
    format_cycle_summary,
    make_adapter,
)
from autark.core.models import CycleReport


# ---- parser ----

def test_parser_accepts_run_json() -> None:
    args = build_parser().parse_args(["run", "--adapter", "fake", "--json"])
    assert args.command == "run"
    assert args.adapter == "fake"
    assert args.json is True


def test_parser_accepts_eval() -> None:
    args = build_parser().parse_args(["eval", "--adapter", "fake"])
    assert args.command == "eval"


def test_parser_accepts_propose() -> None:
    args = build_parser().parse_args(["propose", "--adapter", "fake"])
    assert args.command == "propose"


def test_parser_accepts_validate() -> None:
    args = build_parser().parse_args(["validate", "--adapter", "fake"])
    assert args.command == "validate"


def test_parser_accepts_audit() -> None:
    args = build_parser().parse_args(["audit", "--output-dir", "out"])
    assert args.command == "audit"


# ---- format_cycle_summary ----

def test_format_cycle_summary_includes_errors() -> None:
    report = CycleReport(
        cycle_id="cycle-test",
        adapter_name="fake",
        total_cases=1,
        failures=1,
        signals_extracted=0,
        strategies_selected=0,
        changes_accepted=0,
        changes_rejected=0,
        errors=["case failed"],
    )
    summary = format_cycle_summary(report, dry_run=True, output_dir="out")
    assert "cycle: cycle-test" in summary
    assert "errors:" in summary
    assert "case failed" in summary


# ---- make_adapter validation ----

def test_make_adapter_rejects_missing_corpus() -> None:
    args = argparse.Namespace(
        adapter="fake",
        corpus="does-not-exist.json",
        output_dir="out",
        artifact_root="",
        proposer="deterministic",
        proposer_command="",
        proposer_timeout=120.0,
    )
    with pytest.raises(ValueError, match="--corpus does not exist"):
        make_adapter(args)


def test_make_adapter_rejects_missing_external_command() -> None:
    args = argparse.Namespace(
        adapter="prompt-agent",
        corpus="",
        output_dir="out",
        artifact_root="",
        proposer="external-command",
        proposer_command="",
        proposer_timeout=120.0,
    )
    with pytest.raises(ValueError, match="--proposer-command is required"):
        make_adapter(args)


# ---- run (full cycle) ----

def test_run_full_cycle_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["run", "--adapter", "fake", "--output-dir", str(tmp_path), "--json"])
    exit_code = asyncio.run(_run_full_cycle(args))
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert report["adapter_name"] == "fake"
    assert report["total_cases"] == 1
    assert report["changes_accepted"] == 1


def test_run_full_cycle_human_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["run", "--adapter", "fake", "--output-dir", str(tmp_path)])
    exit_code = asyncio.run(_run_full_cycle(args))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AUTARK cycle complete" in captured.out
    assert "mode: dry-run" in captured.out
    assert "dry-run mode did not write" in captured.out


# ---- eval ----

def test_eval_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["eval", "--adapter", "fake", "--output-dir", str(tmp_path), "--json"])
    exit_code = asyncio.run(_run_eval(args))
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert exit_code == 0
    assert report["adapter_name"] == "fake"
    assert report["total_cases"] == 1
    assert (tmp_path / "eval_state.json").exists()


def test_eval_human_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["eval", "--adapter", "fake", "--output-dir", str(tmp_path)])
    exit_code = asyncio.run(_run_eval(args))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "eval complete" in captured.out


# ---- propose ----

def test_propose_after_eval(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # must run eval first to create eval_state.json
    eval_args = build_parser().parse_args(["eval", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_eval(eval_args))

    propose_args = build_parser().parse_args(["propose", "--adapter", "fake", "--output-dir", str(tmp_path)])
    exit_code = asyncio.run(_run_propose(propose_args))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "propose complete" in captured.out
    assert "1 proposed" in captured.out
    assert (tmp_path / "proposals.json").exists()


def test_propose_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    eval_args = build_parser().parse_args(["eval", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_eval(eval_args))
    capsys.readouterr()  # discard eval output

    propose_args = build_parser().parse_args(["propose", "--adapter", "fake", "--output-dir", str(tmp_path), "--json"])
    exit_code = asyncio.run(_run_propose(propose_args))
    captured = capsys.readouterr()
    changes = json.loads(captured.out)
    assert exit_code == 0
    assert isinstance(changes, list)
    assert len(changes) == 1


# ---- validate ----

def test_validate_after_propose(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    eval_args = build_parser().parse_args(["eval", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_eval(eval_args))
    propose_args = build_parser().parse_args(["propose", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_propose(propose_args))

    validate_args = build_parser().parse_args(["validate", "--adapter", "fake", "--output-dir", str(tmp_path)])
    exit_code = asyncio.run(_run_validate(validate_args))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "validate complete" in captured.out
    assert (tmp_path / "decisions.json").exists()


# ---- audit ----

def test_audit_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = build_parser().parse_args(["audit", "--output-dir", str(tmp_path)])
    exit_code = _run_audit(args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "events: 0" in captured.out


def test_audit_after_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # run full cycle to produce audit events
    run_args = build_parser().parse_args(["run", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_full_cycle(run_args))

    audit_args = argparse.Namespace(output_dir=str(tmp_path), json=False, limit=0)
    exit_code = _run_audit(audit_args)
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "case_evaluated" in captured.out
    assert "validation_decision" in captured.out


def test_audit_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_args = build_parser().parse_args(["run", "--adapter", "fake", "--output-dir", str(tmp_path)])
    asyncio.run(_run_full_cycle(run_args))
    capsys.readouterr()  # discard run output

    audit_args = argparse.Namespace(output_dir=str(tmp_path), json=True, limit=0)
    exit_code = _run_audit(audit_args)
    captured = capsys.readouterr()
    events = json.loads(captured.out)
    assert exit_code == 0
    assert isinstance(events, list)
    assert len(events) > 0
