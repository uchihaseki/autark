from __future__ import annotations

import re
from dataclasses import dataclass

from autark.core.models import Signal, Strategy


@dataclass(slots=True)
class SelectionResult:
    signal: Signal
    strategy: Strategy
    score: float
    match_details: str = ""


class RegexStrategySelector:
    def __init__(self, strategies: list[Strategy] | None = None) -> None:
        self.strategies = strategies or []

    def select(self, signal: Signal) -> tuple[Signal, Strategy] | None:
        ranked = self.rank(signal)
        if not ranked:
            return None
        best = ranked[0]
        return best.signal, best.strategy

    def select_all(self, signals: list[Signal]) -> list[tuple[Signal, Strategy]]:
        selections = []
        for signal in signals:
            selected = self.select(signal)
            if selected:
                selections.append(selected)
        return selections

    def rank(self, signal: Signal) -> list[SelectionResult]:
        results = []
        for strategy in self.strategies:
            if not self._category_compatible(strategy.category, signal.signal_type):
                continue
            score = self._match_score(strategy, signal)
            if score > 0.1:
                results.append(
                    SelectionResult(
                        signal=signal,
                        strategy=strategy,
                        score=score,
                        match_details=f"category={strategy.category}, patterns={strategy.signals_match[:3]}",
                    )
                )
        results.sort(key=lambda result: result.score, reverse=True)
        return results

    @staticmethod
    def _category_compatible(strategy_category: str, signal_type: str) -> bool:
        if strategy_category == signal_type:
            return True
        if signal_type == "repair":
            return strategy_category in {"repair", "harden"}
        if signal_type == "optimize":
            return strategy_category in {"optimize", "harden"}
        if signal_type == "innovate":
            return strategy_category == "innovate"
        return True

    @staticmethod
    def _match_score(strategy: Strategy, signal: Signal) -> float:
        if not strategy.signals_match:
            return 0.3

        text = f"{signal.category} {signal.evidence}".lower()
        hits = 0
        for pattern in strategy.signals_match:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    hits += 1
            except re.error:
                if pattern.lower() in text:
                    hits += 1
        return hits / len(strategy.signals_match)
