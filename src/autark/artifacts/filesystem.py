from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from autark.artifacts.base import apply_text_operations
from autark.core.api import public_api
from autark.core.models import ArtifactRevision, CandidateChange


@public_api(since="0.2.0")
class FileArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._staged: dict[str, ArtifactRevision] = {}

    def load(self, artifact_id: str) -> str:
        path = self._path_for(artifact_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def stage(self, artifact_id: str, candidate_change: CandidateChange) -> ArtifactRevision:
        before = self.load(artifact_id)
        after = apply_text_operations(before, candidate_change.operations)
        revision = ArtifactRevision(
            revision_id=f"rev-{uuid4().hex[:8]}",
            artifact_id=artifact_id,
            status="staged",
            before_snapshot=before,
            after_snapshot=after,
            metadata={"change_id": candidate_change.change_id},
        )
        self._staged[revision.revision_id] = revision
        return revision

    def commit(self, revision: ArtifactRevision) -> bool:
        path = self._path_for(revision.artifact_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(revision.after_snapshot, encoding="utf-8")
        return True

    def rollback(self, revision: ArtifactRevision) -> bool:
        self._staged.pop(revision.revision_id, None)
        return True

    def _path_for(self, artifact_id: str) -> Path:
        normalized = artifact_id.lstrip("/")
        return self.root / normalized
