from __future__ import annotations


class AutarkError(Exception):
    pass


class AdapterError(AutarkError):
    pass


class ValidationError(AutarkError):
    pass
