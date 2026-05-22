#!/usr/bin/env python3
"""Initialize a Sopify workspace in an external repository.

Creates the minimal activation markers:
  - .sopify-skills/sopify.json  (workspace marker)
  - .gitignore managed block    (ignore transient state)
  - Copilot instruction files   (if resources available)

Usage:
  python3 scripts/sopify_init.py init --workspace .
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

REPO_ROOT = Path(__file__).resolve().parent.parent

_SOPIFY_SKILLS_DIR = ".sopify-skills"
_SOPIFY_JSON_FILENAME = "sopify.json"
_WORKSPACE_CAPABILITIES = ["runtime_gate"]

_LOGO_LINES = [
    "███████╗ █████╗ ██████╗ ██╗███████╗██╗   ██╗",
    "██╔════╝██╔══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝",
    "███████╗██║  ██║██████╔╝██║█████╗   ╚████╔╝",
    "╚════██║██║  ██║██╔═══╝ ██║██╔══╝    ╚██╔╝",
    "███████║╚█████╔╝██║     ██║██║        ██║",
    "╚══════╝ ╚════╝ ╚═╝     ╚═╝╚═╝        ╚═╝",
]
_LOGO_COLOR = "\033[38;2;154;137;235m"  # #9a89eb
_LOGO_RESET = "\033[0m"

_MANAGED_IGNORE_BEGIN = "# BEGIN sopify-managed"
_MANAGED_IGNORE_END = "# END sopify-managed"
_MANAGED_IGNORE_ENTRIES = (
    ".sopify-runtime/",
    ".sopify-skills/state/",
    ".sopify-skills/plan/_registry.yaml",
)

_INSTRUCTION_BLOCK_BEGIN = "<!-- BEGIN SOPIFY MANAGED BLOCK -->"
_INSTRUCTION_BLOCK_END = "<!-- END SOPIFY MANAGED BLOCK -->"
_COPILOT_INSTRUCTIONS_RELPATH = Path(".github") / "copilot-instructions.md"
_COPILOT_INSTRUCTION_FILE_RELPATH = Path(".github") / "instructions" / "sopify.instructions.md"

_SOPIFY_VERSION_RE = re.compile(r"^<!--\s*SOPIFY_VERSION:\s*(?P<version>.+?)\s*-->$", re.MULTILINE)


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_source_version() -> str | None:
    """Read the embedded Sopify version from the source host header."""
    for candidate in (
        REPO_ROOT / "Codex" / "Skills" / "EN" / "AGENTS.md",
        REPO_ROOT / "Codex" / "Skills" / "CN" / "AGENTS.md",
    ):
        if candidate.is_file():
            match = _SOPIFY_VERSION_RE.search(candidate.read_text(encoding="utf-8"))
            if match:
                return match.group("version").strip()
    return None


def _resolve_git_dir(workspace_root: Path) -> Path | None:
    dot_git = workspace_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if not dot_git.is_file():
        return None
    try:
        first_line = dot_git.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError):
        return None
    prefix = "gitdir:"
    if not first_line.lower().startswith(prefix):
        return None
    raw_value = first_line[len(prefix):].strip()
    if not raw_value:
        return None
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = (workspace_root / candidate).resolve()
    return candidate


def _write_text_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return True


def _ensure_trailing_newline(content: str) -> str:
    if not content:
        return ""
    return f"{content.rstrip()}\n"


# ── sopify.json ──────────────────────────────────────────────────────────


def _write_sopify_json(workspace_root: Path, *, source_version: str | None) -> bool:
    sopify_json_dir = workspace_root / _SOPIFY_SKILLS_DIR
    sopify_json_path = sopify_json_dir / _SOPIFY_JSON_FILENAME

    # Preserve existing fields if sopify.json already exists
    existing = {}
    if sopify_json_path.is_file():
        try:
            existing = json.loads(sopify_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    payload = {
        "schema_version": str(existing.get("schema_version") or "1"),
        "workspace_kind": existing.get("workspace_kind") or "external",
        "bundle_version": existing.get("bundle_version") or source_version,
        "locator_mode": "global_first",
        "capabilities": list(_WORKSPACE_CAPABILITIES),
    }

    sopify_json_dir.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return _write_text_if_changed(sopify_json_path, content)


# ── .gitignore managed block ────────────────────────────────────────────


def _render_managed_ignore_block() -> str:
    return "\n".join((_MANAGED_IGNORE_BEGIN, *_MANAGED_IGNORE_ENTRIES, _MANAGED_IGNORE_END))


def _write_managed_ignore_block(path: Path) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = _render_managed_ignore_block()
    if _MANAGED_IGNORE_BEGIN in existing and _MANAGED_IGNORE_END in existing:
        new_content = re.sub(
            rf"{re.escape(_MANAGED_IGNORE_BEGIN)}.*?{re.escape(_MANAGED_IGNORE_END)}",
            block,
            existing,
            count=1,
            flags=re.DOTALL,
        )
    else:
        base = existing.rstrip("\n")
        separator = "\n\n" if base else ""
        new_content = f"{base}{separator}{block}"
    return _write_text_if_changed(path, _ensure_trailing_newline(new_content))


# ── Copilot instructions ────────────────────────────────────────────────


def _write_managed_instruction_block(path: Path, content: str) -> bool:
    block = "\n".join((_INSTRUCTION_BLOCK_BEGIN, content.strip(), _INSTRUCTION_BLOCK_END))
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _INSTRUCTION_BLOCK_BEGIN in existing and _INSTRUCTION_BLOCK_END in existing:
        new_content = re.sub(
            rf"{re.escape(_INSTRUCTION_BLOCK_BEGIN)}.*?{re.escape(_INSTRUCTION_BLOCK_END)}",
            block,
            existing,
            count=1,
            flags=re.DOTALL,
        )
    else:
        base = existing.rstrip("\n")
        separator = "\n\n" if base else ""
        new_content = f"{base}{separator}{block}"
    return _write_text_if_changed(path, _ensure_trailing_newline(new_content))


def _write_copilot_instruction_file(workspace_root: Path, content: str) -> bool:
    target = workspace_root / _COPILOT_INSTRUCTION_FILE_RELPATH
    return _write_text_if_changed(target, _ensure_trailing_newline(content))


def _sync_copilot_instructions(workspace_root: Path, *, source_root: Path) -> bool:
    resource_dir = source_root / "installer" / "resources" / "copilot"
    lightweight_path = resource_dir / "lightweight.md"
    if not lightweight_path.is_file():
        return False
    lightweight = lightweight_path.read_text(encoding="utf-8")
    changed = _write_managed_instruction_block(
        workspace_root / _COPILOT_INSTRUCTIONS_RELPATH, lightweight,
    )
    full_path = resource_dir / "full.md"
    if full_path.is_file():
        full = full_path.read_text(encoding="utf-8")
        changed = _write_copilot_instruction_file(workspace_root, full) or changed
    return changed


# ── Main ─────────────────────────────────────────────────────────────────


def init_workspace(
    workspace: Path,
    *,
    source_root: Path = REPO_ROOT,
    copilot: bool = True,
) -> dict:
    workspace = workspace.resolve()
    if not workspace.is_dir():
        return {"action": "failed", "reason_code": "WORKSPACE_NOT_FOUND", "message": f"Not a directory: {workspace}"}

    source_version = _read_source_version()
    results: list[str] = []

    # 1. Write sopify.json
    if _write_sopify_json(workspace, source_version=source_version):
        results.append("sopify.json created")
    else:
        results.append("sopify.json unchanged")

    # 2. Write .gitignore managed block
    git_dir = _resolve_git_dir(workspace)
    if git_dir is not None:
        gitignore_path = workspace / ".gitignore"
        if _write_managed_ignore_block(gitignore_path):
            results.append(".gitignore updated")
        else:
            results.append(".gitignore unchanged")
    else:
        results.append(".gitignore skipped (not a git repo)")

    # 3. Copilot instructions (if resources available)
    if copilot:
        if _sync_copilot_instructions(workspace, source_root=source_root):
            results.append("copilot instructions synced")
        else:
            results.append("copilot instructions unchanged")

    sopify_json_path = workspace / _SOPIFY_SKILLS_DIR / _SOPIFY_JSON_FILENAME
    return {
        "action": "initialized",
        "workspace": str(workspace),
        "sopify_json": str(sopify_json_path),
        "bundle_version": source_version,
        "details": results,
    }


def _render_user_output(result: dict, *, language: str = "en-US") -> str:
    if result.get("action") == "failed":
        reason = result.get("reason_code", "UNKNOWN")
        message = result.get("message", "")
        if language == "zh-CN":
            return f"Sopify 初始化失败：{message}\n  reason_code: {reason}"
        return f"Sopify init failed: {message}\n  reason_code: {reason}"

    lines: list[str] = []
    version = result.get("bundle_version") or "unknown"
    workspace = result.get("workspace", ".")
    if language == "zh-CN":
        lines.append(f"✓ Sopify 工作区已就绪")
        lines.append(f"  位置：{workspace}")
        lines.append(f"  版本：{version}")
        lines.append("")
        lines.append("下一步：")
        lines.append("  在此目录打开 AI 宿主（Copilot / Codex / Claude），开始使用 Sopify。")
    else:
        lines.append(f"✓ Sopify workspace ready")
        lines.append(f"  path:    {workspace}")
        lines.append(f"  version: {version}")
        lines.append("")
        lines.append("Next steps:")
        lines.append("  Open an AI host (Copilot / Codex / Claude) in this directory to start using Sopify.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a Sopify workspace in an external repository.",
    )
    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser(
        "init",
        help="Create workspace activation markers (.sopify-skills/sopify.json + .gitignore).",
    )
    init_parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Target project directory (default: current directory).",
    )
    init_parser.add_argument(
        "--no-copilot",
        action="store_true",
        help="Skip Copilot instruction file distribution.",
    )
    init_parser.add_argument(
        "--language",
        choices=("en-US", "zh-CN"),
        default=None,
        help="Output language (default: auto-detect from LANG).",
    )
    return parser


def _detect_language(explicit: str | None) -> str:
    if explicit:
        return explicit
    lang_env = os.environ.get("LANG", "")
    if "zh" in lang_env.lower():
        return "zh-CN"
    return "en-US"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "init":
        parser.print_help()
        return 1

    workspace = Path(args.workspace).expanduser().resolve()
    language = _detect_language(args.language)

    result = init_workspace(
        workspace,
        source_root=REPO_ROOT,
        copilot=not args.no_copilot,
    )

    if sys.stdout.isatty() and result.get("action") != "failed":
        use_color = os.environ.get("NO_COLOR") is None
        for line in _LOGO_LINES:
            if use_color:
                print(f"{_LOGO_COLOR}{line}{_LOGO_RESET}")
            else:
                print(line)
        print()
    print(_render_user_output(result, language=language))
    return 0 if result.get("action") != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
