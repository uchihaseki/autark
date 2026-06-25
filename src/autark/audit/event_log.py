from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from autark.core.api import public_api


@public_api(since="0.2.0")
class JsonlEventLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: dict[str, Any]) -> None:
        payload = {
            "event_id": event.get("event_id", str(uuid4())),
            "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            **event,
        }
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def read_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        with open(self.path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        if limit is not None:
            return events[-limit:]
        return events
