from __future__ import annotations

import asyncio
from pathlib import Path

from autark.adapters.prompt_agent import PromptAgentAdapter
from autark.core.engine import EngineConfig, EvolutionEngine


def test_prompt_agent_cycle_runs(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "prompt.txt").write_text("BROKEN prompt", encoding="utf-8")

    corpus_path = tmp_path / "cases.json"
    corpus_path.write_text(
        """
{
  "artifact_id": "prompt.txt",
  "cases": [
    {
      "case_id": "math-001",
      "input_text": "What is the sum of 2 and 2?",
      "expected_output": "4",
      "constraints": ["answer directly"]
    }
  ]
}
""",
        encoding="utf-8",
    )

    adapter = PromptAgentAdapter(corpus_path=corpus_path, artifact_root=artifact_root, output_dir=tmp_path / "output")
    engine = EvolutionEngine(adapter, EngineConfig(adapter_name="prompt-agent", dry_run=True))
    report = asyncio.run(engine.run_cycle())

    assert report.total_cases == 1
    assert report.failures == 1
    assert report.signals_extracted == 1
    assert report.strategies_selected == 1
    assert report.changes_accepted == 1
    assert report.changes_rejected == 0
    assert (tmp_path / "output" / "events.jsonl").exists()
