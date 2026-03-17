"""Host adapters for Sopify installer."""

from __future__ import annotations

from .base import HostAdapter
from .claude import CLAUDE_ADAPTER
from .codex import CODEX_ADAPTER

_ADAPTERS = {
    CODEX_ADAPTER.host_name: CODEX_ADAPTER,
    CLAUDE_ADAPTER.host_name: CLAUDE_ADAPTER,
}


def get_host_adapter(host_name: str) -> HostAdapter:
    """Return the registered host adapter."""
    try:
        return _ADAPTERS[host_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported host adapter: {host_name}") from exc

