#!/usr/bin/env python3
"""Repo-local helper for runtime-backed `~go plan`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.config import ConfigError, load_runtime_config
from runtime.engine import run_runtime
from runtime.output import render_runtime_error, render_runtime_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the repo-local Sopify runtime for `~go plan`.",
    )
    parser.add_argument(
        "request",
        nargs="+",
        help="Planning request text, with or without the `~go plan` prefix.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Target workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--global-config-path",
        default=None,
        help="Optional override for the global sopify config path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw runtime result as JSON.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable title coloring in rendered output.",
    )
    return parser


def normalize_request(raw_text: str) -> str:
    """Normalize bare planning text into a `~go plan` request."""
    text = raw_text.strip()
    if not text:
        raise ValueError("Planning request cannot be empty")
    lowered = text.lower()
    if lowered.startswith("~go plan"):
        return text
    if text.startswith("~"):
        raise ValueError("go_plan_runtime only accepts bare planning text or `~go plan ...`")
    return f"~go plan {text}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    workspace_root = Path(args.workspace_root).resolve()
    raw_request = " ".join(args.request)
    config = None

    try:
        request = normalize_request(raw_request)
        config = load_runtime_config(workspace_root, global_config_path=args.global_config_path)
        result = run_runtime(
            request,
            workspace_root=workspace_root,
            global_config_path=args.global_config_path,
        )
    except (ConfigError, ValueError) as exc:
        print(
            render_runtime_error(
                str(exc),
                brand=config.brand if config is not None else "sopify-ai",
                language=config.language if config is not None else "zh-CN",
                title_color=config.title_color if config is not None else "none",
                use_color=not args.no_color,
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # pragma: no cover - safety net for manual CLI use
        print(
            render_runtime_error(
                f"Unexpected runtime failure: {exc}",
                brand=config.brand if config is not None else "sopify-ai",
                language=config.language if config is not None else "zh-CN",
                title_color=config.title_color if config is not None else "none",
                use_color=not args.no_color,
            ),
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            render_runtime_output(
                result,
                brand=config.brand,
                language=config.language,
                title_color=config.title_color,
                use_color=not args.no_color,
            )
        )

    return 0 if result.plan_artifact is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
