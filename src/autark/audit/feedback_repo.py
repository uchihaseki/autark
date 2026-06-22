from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class FeedbackRepo:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, record: dict[str, Any], run_id: str | None = None) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        run_id = run_id or str(uuid4())[:8]
        run_dir = self.base_dir / "runs" / today
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"run_{run_id}.json"
        payload = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), **record}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_decision(self, decision: dict[str, Any], decision_id: str | None = None) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        decision_id = decision_id or str(uuid4())[:8]
        decision_dir = self.base_dir / "decisions"
        decision_dir.mkdir(parents=True, exist_ok=True)
        path = decision_dir / f"{today}_decision_{decision_id}.json"
        path.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
