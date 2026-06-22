from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from autark.core.models import Strategy


class JsonStrategyStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[Strategy]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        items = data.get("strategies", data if isinstance(data, list) else [])
        return [Strategy(**item) for item in items]

    def save(self, strategies: list[Strategy]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "strategies": [asdict(strategy) for strategy in strategies]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
