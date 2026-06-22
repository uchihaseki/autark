from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autark.core.models import EvalCase


class PromptCaseProvider:
    def __init__(self, corpus_path: Path | None = None) -> None:
        self.corpus_path = corpus_path

    def load_cases(self) -> list[EvalCase]:
        if self.corpus_path is None:
            return [
                EvalCase(
                    case_id="prompt-001",
                    input_text="Return the sum of 2 and 2.",
                    expected_output="4",
                    metadata={"artifact_id": "prompt.txt"},
                )
            ]
        data = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        artifact_id = data.get("artifact_id", "prompt.txt") if isinstance(data, dict) else "prompt.txt"
        items = data.get("cases", data if isinstance(data, list) else [])
        return [
            EvalCase(
                case_id=item["case_id"],
                input_text=item.get("input_text", ""),
                expected_output=item.get("expected_output", ""),
                metadata={
                    "artifact_id": item.get("artifact_id", artifact_id),
                    "constraints": item.get("constraints", []),
                    **item.get("metadata", {}),
                },
            )
            for item in items
        ]
