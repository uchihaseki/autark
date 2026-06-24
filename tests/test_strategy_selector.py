from __future__ import annotations

from autark.core.models import Signal, Strategy
from autark.strategies import RegexStrategySelector


def test_strategy_selector_matches_by_category_and_regex() -> None:
    strategies = [
        Strategy(strategy_id="s1", name="repair answer", category="repair", signals_match=["wrong_answer", "incorrect"], instructions=[]),
        Strategy(strategy_id="s2", name="harden", category="harden", signals_match=["empty_output"], instructions=[]),
    ]
    selector = RegexStrategySelector(strategies)
    signal = Signal(
        signal_id="sig-1", case_id="case-1", artifact_id="prompt.txt",
        signal_type="repair", category="wrong_answer",
        evidence="expected answer missing", scores={"overall": 0.1},
    )

    selected = selector.select(signal)

    assert selected is not None
    assert selected[1].strategy_id == "s1"
