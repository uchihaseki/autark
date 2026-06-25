"""Public API marker for AUTARK.

Usage::

    from autark.core.api import public_api

    @public_api(since="0.2.0")
    class MyEvaluator:
        ...

    @public_api(since="0.3.0", experimental=True)
    def experimental_function():
        ...
"""

from __future__ import annotations


def public_api(since: str = "0.2.0", experimental: bool = False):
    """Mark a class or function as stable public API.

    This is a documentation-only marker. It does not change runtime behavior.
    The decorator appends a visibility note to the object's ``__doc__``.

    Args:
        since: The version in which this API was first declared stable.
        experimental: If True, the API may change without notice.
    """
    def decorator(obj):
        obj._autark_public_api = True
        obj._autark_api_since = since
        obj._autark_api_experimental = experimental

        note = f"\n\n*Public API (since {since})*"
        if experimental:
            note += " — **experimental**, may change in future releases."
        if obj.__doc__:
            obj.__doc__ += note
        else:
            obj.__doc__ = note.strip()
        return obj
    return decorator
