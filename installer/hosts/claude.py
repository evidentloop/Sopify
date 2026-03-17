"""Claude host adapter."""

from __future__ import annotations

from .base import HostAdapter

CLAUDE_ADAPTER = HostAdapter(
    host_name="claude",
    source_dirname="Claude",
    destination_dirname=".claude",
    header_filename="CLAUDE.md",
)

