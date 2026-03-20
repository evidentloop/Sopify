#!/usr/bin/env python3
"""Default repo-local entry for routing raw user input through Sopify runtime."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.cli import build_runtime_parser, execute_runtime_cli
from runtime.config import ConfigError, load_runtime_config
from runtime.entry_guard import DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE
from runtime.output import render_runtime_error
from runtime.router import match_runtime_first_guard

DIRECT_ENTRY_BLOCKED_ERROR_CODE = "runtime_gate_required"


def _render_direct_entry_block(
    *,
    request: str,
    workspace_root: Path,
    global_config_path: str | None,
    no_color: bool,
    as_json: bool,
    guard: dict[str, str],
) -> int:
    message = (
        "Direct raw-request entry is blocked for runtime-first traffic. "
        "Use `scripts/runtime_gate.py enter --workspace-root <cwd> --request \"<raw user request>\"` first, "
        "or rerun with `--allow-direct-entry` for local debug only. "
        f"[reason_code={DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE}, "
        f"guard_kind={guard.get('guard_kind', '<unknown>')}, request={request}]"
    )
    if as_json:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_code": DIRECT_ENTRY_BLOCKED_ERROR_CODE,
                    "message": message,
                    "required_entry": "scripts/runtime_gate.py",
                    "entry_guard_reason_code": DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE,
                    "trigger_evidence": {
                        "direct_edit_guard_kind": guard.get("guard_kind"),
                        "direct_edit_guard_trigger": guard.get("reason"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    config = None
    try:
        config = load_runtime_config(workspace_root, global_config_path=global_config_path)
    except ConfigError:
        config = None
    print(
        render_runtime_error(
            message,
            brand=config.brand if config is not None else "sopify-ai",
            language=config.language if config is not None else "zh-CN",
            title_color=config.title_color if config is not None else "none",
            use_color=not no_color,
        )
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_runtime_parser(
        description="Run the default repo-local Sopify runtime entry for raw user input.",
        request_help="Raw user input to route through Sopify runtime.",
    )
    parser.add_argument(
        "--allow-direct-entry",
        action="store_true",
        help="Bypass runtime-first miswire protection for local debug only.",
    )
    args = parser.parse_args(argv)
    request = " ".join(args.request)
    guard = match_runtime_first_guard(request)
    workspace_root = Path(args.workspace_root).resolve()
    if guard is not None and not args.allow_direct_entry:
        return _render_direct_entry_block(
            request=request,
            workspace_root=workspace_root,
            global_config_path=args.global_config_path,
            no_color=args.no_color,
            as_json=args.json,
            guard=guard,
        )
    return execute_runtime_cli(
        request,
        workspace_root=workspace_root,
        global_config_path=args.global_config_path,
        as_json=args.json,
        no_color=args.no_color,
    )


if __name__ == "__main__":
    raise SystemExit(main())
