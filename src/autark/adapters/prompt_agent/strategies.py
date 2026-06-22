from autark.core.models import Strategy

PROMPT_AGENT_STRATEGIES = [
    Strategy(
        strategy_id="repair_wrong_answer",
        name="Repair wrong answer",
        category="repair",
        signals_match=["wrong_answer", "expected answer", "incorrect"],
        instructions=["Make the prompt require answer verification before responding."],
        validation=["rerun failing case", "rerun holdout cases"],
    ),
    Strategy(
        strategy_id="repair_missing_constraint",
        name="Repair missing constraint",
        category="repair",
        signals_match=["missing_constraint", "constraint", "violated"],
        instructions=["Make the prompt explicitly follow all case constraints."],
        validation=["rerun constrained cases"],
    ),
    Strategy(
        strategy_id="repair_format_error",
        name="Repair format error",
        category="repair",
        signals_match=["format_error", "json", "format"],
        instructions=["Make the prompt enforce the required output format."],
        validation=["rerun format-sensitive cases"],
    ),
    Strategy(
        strategy_id="optimize_prompt_clarity",
        name="Optimize prompt clarity",
        category="optimize",
        signals_match=["prompt_ambiguous", "ambiguous", "unclear"],
        instructions=["Rewrite vague instructions as concrete, testable rules."],
        validation=["rerun ambiguous cases"],
    ),
    Strategy(
        strategy_id="harden_boundary_case",
        name="Harden boundary case",
        category="harden",
        signals_match=["boundary_case", "empty_output", "edge_case"],
        instructions=["Add guardrails for empty or malformed input."],
        validation=["rerun boundary cases"],
    ),
    Strategy(
        strategy_id="innovate_capability_gap",
        name="Innovate capability gap",
        category="innovate",
        signals_match=["capability_gap", "missing capability"],
        instructions=["Add new task capability while preserving existing behavior."],
        validation=["run new capability cases", "run regression cases"],
    ),
]
