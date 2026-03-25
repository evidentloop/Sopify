#!/usr/bin/env python3
"""Render stable release installer assets from the dev/default root scripts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

_TEMPLATES = (
    (
        REPO_ROOT / "install.sh",
        {
            'SOURCE_CHANNEL="dev"': 'SOURCE_CHANNEL="stable"',
            'SOURCE_REF="main"': '__RENDERED_SHELL_SOURCE_REF__',
        },
    ),
    (
        REPO_ROOT / "install.ps1",
        {
            '$SourceChannel = "dev"': '$SourceChannel = "stable"',
            '$SourceRef = "main"': '$SourceRef = "__RENDERED_RELEASE_TAG__"',
        },
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render stable release install.sh/install.ps1 assets for a release tag.")
    parser.add_argument("--release-tag", required=True, help="Release tag to embed into the stable assets.")
    parser.add_argument("--output-dir", required=True, help="Directory where the rendered assets should be written.")
    return parser


def render_release_installers(*, release_tag: str, output_dir: Path) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []
    for source_path, replacements in _TEMPLATES:
        rendered = source_path.read_text(encoding="utf-8")
        for old_value, new_value in replacements.items():
            replacement_value = (
                new_value.replace("__RENDERED_SHELL_SOURCE_REF__", f'SOURCE_REF="{release_tag}"')
                .replace("__RENDERED_RELEASE_TAG__", release_tag)
            )
            if rendered.count(old_value) != 1:
                raise ValueError(f"Expected exactly one marker [{old_value}] in {source_path}")
            rendered = rendered.replace(old_value, replacement_value)
        destination = output_dir / source_path.name
        destination.write_text(rendered, encoding="utf-8")
        written_paths.append(destination)
    return tuple(written_paths)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    release_tag = args.release_tag.strip()
    if not release_tag:
        print("Release tag must not be empty.", file=sys.stderr)
        return 1
    paths = render_release_installers(
        release_tag=release_tag,
        output_dir=Path(args.output_dir).expanduser().resolve(),
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
