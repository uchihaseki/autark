from __future__ import annotations

from pathlib import Path

from autark.artifacts import FileArtifactStore
from autark.core.models import CandidateChange


def test_file_artifact_stage_commit_rollback(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    (tmp_path / "prompt.txt").write_text("BROKEN prompt", encoding="utf-8")
    change = CandidateChange(
        change_id="chg-1",
        artifact_id="prompt.txt",
        operations=[{"operation": "append", "text": "Always compute and verify the answer before responding."}],
        rationale="repair prompt",
        validation_plan=["rerun"],
    )

    revision = store.stage("prompt.txt", change)
    assert "Always compute" in revision.after_snapshot
    store.commit(revision)
    assert "Always compute" in (tmp_path / "prompt.txt").read_text(encoding="utf-8")
