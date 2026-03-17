"""Codex host adapter."""

from __future__ import annotations

from .base import HostAdapter

CODEX_ADAPTER = HostAdapter(
    host_name="codex",
    source_dirname="Codex",
    destination_dirname=".codex",
    header_filename="AGENTS.md",
)

