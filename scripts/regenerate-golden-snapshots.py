#!/usr/bin/env python3
"""Regenerate tests/golden-snapshots.json from current source files.

Golden snapshots detect unintended changes to installer output.
This script is the single source of truth for regeneration, called by:
  - release-sync.sh (after version bump)
  - release-preflight.sh (auto-fix during pre-commit)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from installer.hosts.base import HEADER_TEMPLATE_NAME, render_single_file  # noqa: E402
    from installer.hosts.claude import CLAUDE_ADAPTER  # noqa: E402
    from installer.hosts.codex import CODEX_ADAPTER  # noqa: E402
    from installer.hosts.copilot import COPILOT_ADAPTER  # noqa: E402
    from installer.models import language_to_source_dir  # noqa: E402
except ImportError:
    # Gracefully skip when run outside the full repo (e.g. test fixtures).
    sys.exit(0)

GOLDEN = ROOT / "tests/golden-snapshots.json"
IGNORE = {".DS_Store", "Thumbs.db", "__pycache__"}

# Each adapter produces a different header file; hash = sha256(filename + content)
ADAPTERS = [
    (CODEX_ADAPTER, "CN", "zh-CN"),
    (CODEX_ADAPTER, "EN", "en-US"),
    (CLAUDE_ADAPTER, "CN", "zh-CN"),
    (CLAUDE_ADAPTER, "EN", "en-US"),
]
DIRECTIONS = [("CN", "zh-CN"), ("EN", "en-US")]


def _header_hash(adapter, direction: str) -> str:
    """Hash the rendered header template for a host adapter."""
    source = adapter.source_root(ROOT, direction)
    content = (source / HEADER_TEMPLATE_NAME).read_text()
    content = content.replace("{{config_dir}}", adapter.config_dir or "")
    return hashlib.sha256(f"{adapter.header_filename}\x00{content}".encode()).hexdigest()


def _tree_hash(direction: str) -> str:
    """Hash all skill files to detect content drift."""
    skill_root = ROOT / "skills" / language_to_source_dir(direction) / "skills" / "sopify"
    parts = [
        f.relative_to(skill_root).as_posix().encode() + b"\x00" + f.read_bytes()
        for f in sorted(skill_root.rglob("*"))
        if f.is_file() and f.name not in IGNORE
    ]
    return hashlib.sha256(b"\n".join(parts)).hexdigest()


def _payload_hash(direction: str) -> str:
    """Hash the fully rendered Copilot managed block payload."""
    source = COPILOT_ADAPTER.source_root(ROOT, direction)
    rendered = render_single_file(
        source / HEADER_TEMPLATE_NAME, source / "skills" / "sopify", COPILOT_ADAPTER
    )
    return hashlib.sha256(rendered.encode()).hexdigest()


def main() -> int:
    if not GOLDEN.exists():
        return 0

    snapshots: dict[str, str] = {}
    for adapter, direction, locale in ADAPTERS:
        snapshots[f"{adapter.host_name}:{locale}:header"] = _header_hash(adapter, direction)

    for direction, locale in DIRECTIONS:
        snapshots[f"copilot:{locale}:managed_block_payload"] = _payload_hash(direction)
        snapshots[f"skills:{locale}:tree"] = _tree_hash(direction)

    golden = json.loads(GOLDEN.read_text())
    golden["snapshots"] = snapshots
    GOLDEN.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n")
    print(f"  Golden snapshots regenerated ({len(snapshots)} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
