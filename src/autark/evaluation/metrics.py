from __future__ import annotations

from autark.core.api import public_api


@public_api(since="0.2.0")
def weighted_overall(scores: dict[str, float], weights: dict[str, float]) -> float:
    if not weights:
        return scores.get("overall", 0.0)
    total_weight = sum(weights.values()) or 1.0
    total = sum(scores.get(name, 0.0) * weight for name, weight in weights.items())
    return round(total / total_weight, 4)


@public_api(since="0.2.0")
def grade_from_score(overall: float) -> str:
    if overall >= 0.8:
        return "A"
    if overall >= 0.5:
        return "B"
    return "C"
