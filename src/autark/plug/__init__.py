"""AUTARK Plug — one-line agent evaluation and self-improvement.

The ``evolve()`` function is the primary entry point.  Provide your agent
runner and test cases, and AUTARK handles the rest: evaluation, failure
signal extraction, strategy selection, change proposal, validation, and
audit logging.

Minimal usage::

    import asyncio
    from autark.plug import evolve
    from autark.core.models import EvalCase, RunResult

    class MyRunner:
        async def run_case(self, case: EvalCase) -> RunResult:
            output = my_agent(case.input_text)
            return RunResult(case_id=case.case_id, artifact_id="main",
                             status="success", output=output)

    report = asyncio.run(evolve(
        runner=MyRunner(),
        cases=[EvalCase(case_id="1", input_text="2+3", expected_output="5")],
    ))
    print(f"{report.changes_accepted} changes accepted")

See ``examples/plug_minimal/`` for a complete runnable example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autark.core.api import public_api
from autark.core.engine import EngineConfig, EvolutionEngine
from autark.core.models import CycleReport, EvalCase, Strategy
from autark.evaluation.judge import HeuristicEvaluator
from autark.proposers.deterministic import DeterministicProposer
from autark.plug._adapter import SyntheticAdapter
from autark.plug._defaults import (
    DEFAULT_STRATEGIES,
    _artifact_store_from,
    _case_provider_from,
)
from autark.plug._discovery import discover as _discover
from autark.plug._discovery import list_adapter_names as _list_adapter_names


@public_api(since="0.3.0", experimental=True)
def discover(name: str):
    """Load an adapter class registered under ``autark.adapters`` entry points.

    Example::

        AdapterCls = discover("my-adapter")
        adapter = AdapterCls(corpus_path=..., artifact_root=...)
    """
    return _discover(name)


@public_api(since="0.3.0", experimental=True)
def list_adapters() -> list[str]:
    """Return sorted list of all registered adapter names."""
    return _list_adapter_names()


@public_api(since="0.3.0", experimental=True)
async def evolve(
    runner,
    *,
    evaluator=None,
    cases: list[EvalCase] | str | Path | None = None,
    artifacts: str | Path | dict[str, str] | None = None,
    proposer=None,
    strategies: list[Strategy] | None = None,
    output_dir: str = ".autark/output",
    dry_run: bool = True,
    max_concurrency: int = 5,
    retry_count: int = 0,
    retry_delay: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> CycleReport:
    """Run a full evolution cycle against an agent with minimal boilerplate.

    Parameters
    ----------
    runner:
        **Required.**  An object implementing the ``AgentRunner`` protocol
        (``async def run_case(self, case: EvalCase) -> RunResult``).
    evaluator:
        An ``Evaluator`` instance.  Defaults to ``HeuristicEvaluator()``.
    cases:
        Test cases as a ``list[EvalCase]``, a path to a JSON corpus file,
        or ``None`` (no cases).  See ``EvalCase`` for the expected shape.
    artifacts:
        Agent artifacts as a directory path (filesystem), a ``dict`` of
        ``{name: content}`` (in-memory), or ``None`` (empty store).
    proposer:
        A ``ChangeProposer`` instance.  Defaults to ``DeterministicProposer()``.
    strategies:
        List of ``Strategy`` objects for signal-to-strategy matching.
        Defaults to ``DEFAULT_STRATEGIES`` (8 built-in strategies).
    output_dir:
        Directory for intermediate state files and audit logs.
        Defaults to ``".autark/output"``.
    dry_run:
        If ``True`` (default), changes are staged and validated but **not**
        committed to disk.
    max_concurrency:
        Maximum number of cases to run in parallel when ``parallel_cases``
        is enabled.
    retry_count:
        Number of retries per case on transient failures (0 = no retry).
    retry_delay:
        Seconds between retries.
    metadata:
        Arbitrary metadata attached to the engine config.

    Returns
    -------
    CycleReport
        Summary of the cycle: total cases, failures, signals, accepted
        and rejected changes, etc.
    """
    evaluator = evaluator or HeuristicEvaluator()
    proposer = proposer or DeterministicProposer()
    strategies = list(strategies) if strategies is not None else list(DEFAULT_STRATEGIES)

    case_provider = _case_provider_from(cases)
    artifact_store = _artifact_store_from(artifacts)

    adapter = SyntheticAdapter(
        runner=runner,
        case_provider=case_provider,
        evaluator=evaluator,
        proposer=proposer,
        strategies=strategies,
        artifact_store=artifact_store,
        output_dir=output_dir,
    )

    engine = EvolutionEngine(
        adapter=adapter,
        config=EngineConfig(
            adapter_name="synthetic",
            dry_run=dry_run,
            max_concurrency=max_concurrency,
            retry_count=retry_count,
            retry_delay=retry_delay,
            output_dir=output_dir,
            metadata=metadata or {},
        ),
    )
    return await engine.run_cycle()
