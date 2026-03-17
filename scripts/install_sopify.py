#!/usr/bin/env python3
"""Install Sopify host prompts and runtime bundle into a workspace."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from installer.hosts import get_host_adapter
from installer.hosts.base import install_host_assets
from installer.models import InstallError, InstallResult, parse_install_target
from installer.runtime_bundle import sync_runtime_bundle
from installer.validate import run_bundle_smoke_check, validate_bundle_install, validate_host_install


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install Sopify into a target workspace and host environment.")
    parser.add_argument(
        "--target",
        required=True,
        help="Install target in <host:lang> format. Supported: codex:zh-CN, codex:en-US, claude:zh-CN, claude:en-US",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Target workspace root. Defaults to the current directory.",
    )
    return parser


def run_install(*, target_value: str, workspace_value: str, repo_root: Path, home_root: Path | None = None) -> InstallResult:
    target = parse_install_target(target_value)
    workspace_root = Path(workspace_value).expanduser().resolve()
    if not workspace_root.exists():
        raise InstallError(f"Workspace does not exist: {workspace_root}")
    if not workspace_root.is_dir():
        raise InstallError(f"Workspace is not a directory: {workspace_root}")

    resolved_home = (home_root or Path.home()).expanduser().resolve()
    adapter = get_host_adapter(target.host)

    host_paths = install_host_assets(
        adapter,
        repo_root=repo_root,
        home_root=resolved_home,
        language_directory=target.language_directory,
    )
    bundle_root = sync_runtime_bundle(repo_root, workspace_root)
    bundle_paths = validate_bundle_install(bundle_root)
    verified_host_paths = validate_host_install(adapter, home_root=resolved_home)
    smoke_output = run_bundle_smoke_check(bundle_root)

    verified_paths = tuple(dict.fromkeys((*host_paths, *verified_host_paths, *bundle_paths)))
    return InstallResult(
        target=target,
        workspace_root=workspace_root,
        host_root=adapter.destination_root(resolved_home),
        bundle_root=bundle_root,
        verified_paths=verified_paths,
        smoke_output=smoke_output,
    )


def render_result(result: InstallResult) -> str:
    lines = [
        "Installed Sopify successfully:",
        f"  target: {result.target.value}",
        f"  workspace: {result.workspace_root}",
        f"  host root: {result.host_root}",
        f"  bundle root: {result.bundle_root}",
        "",
        "Verified:",
    ]
    lines.extend(f"  - {path}" for path in result.verified_paths)
    lines.extend(
        [
            "",
            "Smoke check:",
            f"  {result.smoke_output}",
            "",
            "Next:",
            "  Reopen the target workspace in the selected host and use Sopify commands or plain requests.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_install(
            target_value=args.target,
            workspace_value=args.workspace,
            repo_root=REPO_ROOT,
        )
    except InstallError as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    print(render_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

