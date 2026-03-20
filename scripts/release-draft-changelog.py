#!/usr/bin/env python3
"""Auto-draft root CHANGELOG [Unreleased] notes from staged release-relevant files."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


UNRELEASED_HEADER = "## [Unreleased]"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Draft CHANGELOG.md [Unreleased] notes from staged files.")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--changelog-path",
        default=None,
        help="Optional explicit changelog path. Defaults to <root>/CHANGELOG.md.",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Explicit changed file path. Repeatable. When omitted, reads staged files from git.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    changelog_path = Path(args.changelog_path).resolve() if args.changelog_path else root / "CHANGELOG.md"

    changed_files = [path for path in args.file if str(path).strip()]
    if not changed_files:
        changed_files = staged_files(root)

    result = draft_changelog(changelog_path, changed_files)
    print(result)
    return 0


def staged_files(root: Path) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMRDTUXB",
            "--",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "Failed to collect staged files.")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def draft_changelog(changelog_path: Path, changed_files: list[str]) -> str:
    if not changelog_path.is_file():
        raise SystemExit(f"Missing changelog: {changelog_path}")

    text = changelog_path.read_text(encoding="utf-8")
    start, end = unreleased_bounds(text)
    unreleased_body = text[start:end].strip()
    if unreleased_body:
        return "CHANGELOG [Unreleased] already has content. Skipped auto-draft."

    normalized_files = dedupe_paths(changed_files)
    if not normalized_files:
        return "No changed files found. Skipped auto-draft."

    draft = render_draft(normalized_files)
    updated = text[:start] + "\n\n" + draft + "\n" + text[end:]
    changelog_path.write_text(updated, encoding="utf-8")
    return f"Auto-drafted CHANGELOG [Unreleased] from {len(normalized_files)} changed files."


def unreleased_bounds(text: str) -> tuple[int, int]:
    header_start = text.find(UNRELEASED_HEADER)
    if header_start < 0:
        raise SystemExit(f"Missing section: {UNRELEASED_HEADER}")
    body_start = header_start + len(UNRELEASED_HEADER)
    next_header = text.find("\n## [", body_start)
    if next_header < 0:
        next_header = len(text)
    return body_start, next_header


def dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in paths:
        path = str(raw).strip().replace("\\", "/")
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


def render_draft(changed_files: list[str]) -> str:
    changed_non_tests = [path for path in changed_files if not path.startswith("tests/")]
    test_files = [path for path in changed_files if path.startswith("tests/")]

    blocks: list[str] = []
    if changed_non_tests:
        blocks.append(render_section("Changed", "Updated release-relevant files", changed_non_tests))
    if test_files:
        blocks.append(render_section("Tests", "Updated automated coverage", test_files))
    if not blocks:
        blocks.append(render_section("Changed", "Updated release-relevant files", changed_files))
    return "\n\n".join(blocks)


def render_section(title: str, summary: str, paths: list[str]) -> str:
    lines = [f"### {title}", "", f"- {summary}:"]
    lines.extend(f"  - `{path}`" for path in paths)
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
