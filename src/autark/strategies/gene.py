from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from autark.core.models import Strategy


@dataclass(slots=True)
class StrategyPreset:
    name: str
    innovate: float
    optimize: float
    repair: float
    harden: float = 0.1
    description: str = ""


@dataclass(slots=True)
class Capsule:
    capsule_id: str
    strategy_id: str
    signal_id: str
    artifact_id: str
    status: str
    changes_applied: list[dict[str, Any]] = field(default_factory=list)
    before_scores: dict[str, float] = field(default_factory=dict)
    after_scores: dict[str, float] = field(default_factory=dict)
    validation_report: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


STRATEGY_PRESETS: dict[str, StrategyPreset] = {
    "balanced": StrategyPreset(
        name="balanced",
        innovate=0.5,
        optimize=0.3,
        repair=0.2,
        harden=0.2,
        description="Steady daily improvement.",
    ),
    "innovate": StrategyPreset(
        name="innovate",
        innovate=0.8,
        optimize=0.15,
        repair=0.05,
        harden=0.1,
        description="Prioritize capability growth.",
    ),
    "harden": StrategyPreset(
        name="harden",
        innovate=0.2,
        optimize=0.3,
        repair=0.3,
        harden=0.4,
        description="Prioritize stability and boundary cases.",
    ),
    "repair-only": StrategyPreset(
        name="repair-only",
        innovate=0.0,
        optimize=0.2,
        repair=0.8,
        harden=0.3,
        description="Emergency repair mode.",
    ),
}


def make_strategy(
    strategy_id: str,
    name: str,
    category: str,
    signals_match: list[str],
    instructions: list[str],
    **metadata: Any,
) -> Strategy:
    return Strategy(
        strategy_id=strategy_id,
        name=name,
        category=category,
        signals_match=signals_match,
        instructions=instructions,
        metadata=metadata,
    )
