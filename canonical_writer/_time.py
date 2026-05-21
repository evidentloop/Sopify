"""UTC timestamp utility for canonical writer."""

from __future__ import annotations

from datetime import datetime, timezone


def iso_now() -> str:
    """Return a stable UTC ISO timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
