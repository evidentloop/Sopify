"""Canonical writer: filesystem-backed state storage for Sopify runtime.

This package owns the StateStore class and its direct dependencies.
Dependency direction: canonical_writer → sopify_contracts (one-way).
"""

from .store import SESSIONS_DIRNAME, StateStore, normalize_session_id
from ._time import iso_now

__all__ = [
    "SESSIONS_DIRNAME",
    "StateStore",
    "iso_now",
    "normalize_session_id",
]
