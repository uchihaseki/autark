"""Adapter discovery via ``importlib.metadata`` entry points.

Third-party adapters register under the ``"autark.adapters"`` group::

    [project.entry-points."autark.adapters"]
    my-adapter = "my_package.adapter:MyAdapter"

These are internal helpers used by the ``plug`` public API and CLI.
"""

from __future__ import annotations

import sys
from importlib.metadata import EntryPoint, entry_points
from typing import Any


def _get_entry_points() -> dict[str, EntryPoint]:
    """Return all registered entry points in the ``autark.adapters`` group."""
    if sys.version_info >= (3, 10):
        eps = entry_points(group="autark.adapters")
        return {ep.name: ep for ep in eps}
    # Python < 3.10 compat
    all_eps = entry_points()
    selected = all_eps.get("autark.adapters", [])
    return {ep.name: ep for ep in selected}


def list_adapter_names() -> list[str]:
    """Return sorted list of all registered adapter names."""
    return sorted(_get_entry_points().keys())


def discover(name: str) -> Any:
    """Load and return an adapter **class** by registered name.

    Raises ``ValueError`` if the name is not registered, with a helpful
    message listing all available adapters.
    """
    adapters = _get_entry_points()
    if name not in adapters:
        available = ", ".join(sorted(adapters.keys())) if adapters else "(none registered)"
        raise ValueError(
            f"Unknown adapter '{name}'. Available: {available}. "
            f"Register via [project.entry-points.\"autark.adapters\"] in pyproject.toml."
        )
    return adapters[name].load()
