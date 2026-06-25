from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from autark.core.api import public_api
from autark.core.models import ArtifactRevision, CandidateChange


@public_api(since="0.2.0")
def apply_text_operations(content: str, operations: list[dict]) -> str:
    updated = content
    for operation in operations:
        op_type = operation.get("operation", "replace")
        if op_type == "replace":
            old = operation.get("old", operation.get("old_section", ""))
            new = operation.get("new", operation.get("new_section", ""))
            if old and old in updated:
                updated = updated.replace(old, new, 1)
            elif new:
                updated = updated.rstrip() + "\n\n" + new
        elif op_type == "append":
            updated = updated.rstrip() + "\n\n" + operation.get("text", "")
    return updated


@public_api(since="0.2.0")
class InMemoryArtifactStore:
    def __init__(self, artifacts: dict[str, str] | None = None) -> None:
        self.artifacts = artifacts or {}
        self._staged: dict[str, ArtifactRevision] = {}

    def load(self, artifact_id: str) -> str:
        return self.artifacts.get(artifact_id, "")

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
        self.artifacts[revision.artifact_id] = revision.after_snapshot
        committed = replace(revision, status="committed")
        self._staged[revision.revision_id] = committed
        return True

    def rollback(self, revision: ArtifactRevision) -> bool:
        self._staged.pop(revision.revision_id, None)
        return True
