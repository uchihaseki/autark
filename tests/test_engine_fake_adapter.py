from __future__ import annotations

import asyncio
from pathlib import Path

from autark.adapters.fake import FakeAdapter
from autark.core.engine import EngineConfig, EvolutionEngine


def test_fake_adapter_cycle_accepts_change(tmp_path: Path) -> None:
    adapter = FakeAdapter(output_dir=tmp_path)
    engine = EvolutionEngine(adapter, EngineConfig(adapter_name="fake", dry_run=True))

    report = asyncio.run(engine.run_cycle())

    assert report.total_cases == 1
    assert report.failures == 1
    assert report.signals_extracted == 1
    assert report.strategies_selected == 1
    assert report.changes_accepted == 1
    assert report.changes_rejected == 0
    assert (tmp_path / "events.jsonl").exists()
