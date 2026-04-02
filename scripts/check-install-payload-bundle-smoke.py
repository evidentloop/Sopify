#!/usr/bin/env python3
"""Smoke-check installer, global payload bundle, and workspace thin stub in isolation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from installer.hosts import get_host_adapter
from installer.inspection import (
    build_doctor_payload,
    build_status_payload,
    inspect_payload_bundle_resolution,
    render_doctor_text,
    render_status_text,
)
from installer.models import InstallError, parse_install_target
from installer.outcome_contract import render_outcome_summary
from installer.validate import (
    resolve_payload_bundle_root,
    run_bundle_smoke_check,
    validate_bundle_install,
    validate_host_install,
    validate_payload_install,
    validate_workspace_stub_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an isolated smoke check for install -> global payload bundle -> workspace stub bootstrap."
    )
    parser.add_argument(
        "--target",
        default="codex:zh-CN",
        help="Install target in <host:lang> format. Default: codex:zh-CN",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to write the structured smoke result as JSON.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary home/workspace for inspection instead of deleting it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    temp_root = Path(tempfile.mkdtemp(prefix="sopify-install-payload-bundle."))
    try:
        result = run_smoke(target_value=args.target, temp_root=temp_root)
        if args.output_json:
            output_path = Path(args.output_json).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (InstallError, RuntimeError, ValueError) as exc:
        failure = {
            "passed": False,
            "target": args.target,
            "error": str(exc),
            "temp_root": str(temp_root),
        }
        if args.output_json:
            output_path = Path(args.output_json).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    finally:
        if args.keep_temp:
            print(f"Kept temp root: {temp_root}", file=sys.stderr)
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


def run_smoke(*, target_value: str, temp_root: Path) -> dict[str, Any]:
    target = parse_install_target(target_value)
    adapter = get_host_adapter(target.host)
    temp_home = temp_root / "home"
    workspace_root = temp_root / "workspace"
    temp_home.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)

    install_stdout = _run_install_cli(target_value=target.value, temp_home=temp_home)
    host_root = adapter.destination_root(temp_home)
    payload_root = adapter.payload_root(temp_home)
    bundle_root = workspace_root / ".sopify-runtime"
    helper_path = payload_root / "helpers" / "bootstrap_workspace.py"

    host_paths = validate_host_install(adapter, home_root=temp_home)
    payload_paths = validate_payload_install(payload_root)
    payload_bundle = inspect_payload_bundle_resolution(payload_root=payload_root, host_id=target.host)

    _require_install_surface_line(
        install_stdout,
        "payload bundle: source_kind=global_active, reason_code=PAYLOAD_BUNDLE_READY",
        label="payload bundle verification line",
    )
    _require_install_surface_line(
        install_stdout,
        "workspace: will bootstrap on first project trigger",
        label="on-demand workspace bootstrap line",
    )
    _require_install_surface_line(
        install_stdout,
        "workspace bundle: skip (WORKSPACE_NOT_REQUESTED)",
        label="workspace bundle skip line",
    )

    if bundle_root.exists():
        raise RuntimeError("Workspace bundle should not exist before trigger-time bootstrap.")
    if payload_bundle.source_kind != "global_active":
        raise RuntimeError(f"Unexpected payload bundle source_kind: {payload_bundle.source_kind!r}")
    if payload_bundle.reason_code != "PAYLOAD_BUNDLE_READY":
        raise RuntimeError(f"Unexpected payload bundle reason_code: {payload_bundle.reason_code!r}")

    bootstrap_stdout = _run_workspace_bootstrap(helper_path=helper_path, workspace_root=workspace_root)
    workspace_stub_path, workspace_manifest = validate_workspace_stub_manifest(bundle_root)
    global_bundle_root = resolve_payload_bundle_root(payload_root)
    global_bundle_paths = validate_bundle_install(global_bundle_root)
    smoke_stdout = run_bundle_smoke_check(
        global_bundle_root,
        payload_manifest_path=payload_root / "payload-manifest.json",
    )
    status_payload = build_status_payload(home_root=temp_home, workspace_root=workspace_root)
    host_status = next(
        host for host in status_payload["hosts"] if host["host_id"] == target.host
    )
    workspace_bundle = host_status.get("workspace_bundle") or {}
    bundle_manifest = json.loads((global_bundle_root / "manifest.json").read_text(encoding="utf-8"))
    default_entry = str(bundle_manifest.get("default_entry") or "")
    plan_only_entry = str(bundle_manifest.get("plan_only_entry") or "")
    runtime_gate_entry = str(bundle_manifest.get("limits", {}).get("runtime_gate_entry") or "")
    entry_guard = bundle_manifest.get("limits", {}).get("entry_guard", {})

    if default_entry != "scripts/sopify_runtime.py":
        raise RuntimeError(f"Unexpected default_entry: {default_entry!r}")
    if plan_only_entry != "scripts/go_plan_runtime.py":
        raise RuntimeError(f"Unexpected plan_only_entry: {plan_only_entry!r}")
    if runtime_gate_entry != "scripts/runtime_gate.py":
        raise RuntimeError(f"Unexpected runtime_gate_entry: {runtime_gate_entry!r}")
    if entry_guard.get("default_runtime_entry") != default_entry:
        raise RuntimeError("Manifest limits.entry_guard.default_runtime_entry drifted from default_entry.")
    if workspace_bundle.get("reason_code") != "STUB_SELECTED":
        raise RuntimeError(
            "Unexpected workspace bundle reason_code after bootstrap: {!r}".format(
                workspace_bundle.get("reason_code")
            )
        )

    legacy_fallback_visibility = _exercise_legacy_fallback_visibility(
        temp_root=temp_root,
        temp_home=temp_home,
        target_host=target.host,
        payload_root=payload_root,
        helper_path=helper_path,
    )

    return {
        "passed": True,
        "script": "scripts/check-install-payload-bundle-smoke.py",
        "target": target.value,
        "temp_root": str(temp_root),
        "temp_home": str(temp_home),
        "workspace_root": str(workspace_root),
        "host_root": str(host_root),
        "payload_root": str(payload_root),
        "bundle_root": str(bundle_root),
        "global_bundle_root": str(global_bundle_root),
        "payload_bundle": payload_bundle.to_status_dict(),
        "workspace_bundle": workspace_bundle,
        "path_summary": {
            "payload_source_kind": payload_bundle.source_kind,
            "payload_reason_code": payload_bundle.reason_code,
            "payload_outcome": render_outcome_summary(payload_bundle.to_status_dict()) or None,
            "workspace_reason_code": workspace_bundle.get("reason_code"),
            "workspace_outcome": render_outcome_summary(workspace_bundle) or None,
        },
        "install_surface": {
            "checks": {
                "install_output_exposes_global_path": True,
                "install_output_explains_on_demand_bootstrap": True,
                "install_output_surfaces_workspace_skip_reason": True,
            },
        },
        "legacy_fallback_visibility": legacy_fallback_visibility,
        "checks": {
            "single_install_command_only": True,
            "workspace_bundle_absent_before_trigger": True,
            "runtime_bootstrap_on_project_trigger": True,
            "default_runtime_entry_preserved": True,
            "plan_only_helper_preserved": True,
            "runtime_gate_entry_preserved": True,
            "workspace_stub_selected_after_bootstrap": True,
            "bundle_smoke_passed": True,
            "legacy_workspace_fallback_visible": True,
        },
        "manifest": {
            "default_entry": default_entry,
            "plan_only_entry": plan_only_entry,
            "runtime_gate_entry": runtime_gate_entry,
            "entry_guard_default_runtime_entry": entry_guard.get("default_runtime_entry"),
        },
        "install_stdout": install_stdout,
        "bootstrap_stdout": bootstrap_stdout,
        "bundle_smoke_stdout": smoke_stdout,
        "verified_paths": {
            "host": [str(path) for path in host_paths],
            "payload": [str(path) for path in payload_paths],
            "workspace_stub": [str(workspace_stub_path)],
            "global_bundle": [str(path) for path in global_bundle_paths],
        },
    }


def _exercise_legacy_fallback_visibility(
    *,
    temp_root: Path,
    temp_home: Path,
    target_host: str,
    payload_root: Path,
    helper_path: Path,
) -> dict[str, Any]:
    legacy_workspace_root = temp_root / "legacy-workspace"
    legacy_workspace_root.mkdir(parents=True, exist_ok=True)
    (legacy_workspace_root / ".git").mkdir(parents=True, exist_ok=True)
    _run_workspace_bootstrap(helper_path=helper_path, workspace_root=legacy_workspace_root)

    payload_manifest = json.loads((payload_root / "payload-manifest.json").read_text(encoding="utf-8"))
    selected_version = str(payload_manifest["active_version"])
    selected_bundle_root = payload_root / "bundles" / selected_version
    legacy_bundle_root = legacy_workspace_root / ".sopify-runtime"
    workspace_manifest_path = legacy_bundle_root / "manifest.json"
    workspace_manifest = json.loads(workspace_manifest_path.read_text(encoding="utf-8"))
    workspace_manifest["legacy_fallback"] = True
    workspace_manifest_path.write_text(
        json.dumps(workspace_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for name in ("runtime", "scripts", "tests"):
        shutil.copytree(selected_bundle_root / name, legacy_bundle_root / name)

    hidden_bundle_root = selected_bundle_root.with_name(f"{selected_bundle_root.name}.missing")
    selected_bundle_root.rename(hidden_bundle_root)
    try:
        status_payload = build_status_payload(home_root=temp_home, workspace_root=legacy_workspace_root)
        doctor_payload = build_doctor_payload(home_root=temp_home, workspace_root=legacy_workspace_root)
    finally:
        hidden_bundle_root.rename(selected_bundle_root)

    host_status = next(host for host in status_payload["hosts"] if host["host_id"] == target_host)
    workspace_bundle = host_status.get("workspace_bundle") or {}
    payload_bundle = host_status.get("payload_bundle") or {}
    if workspace_bundle.get("reason_code") != "LEGACY_FALLBACK_SELECTED":
        raise RuntimeError(
            "Legacy workspace fallback did not surface as LEGACY_FALLBACK_SELECTED: {!r}".format(
                workspace_bundle.get("reason_code")
            )
        )
    if payload_bundle.get("reason_code") != "GLOBAL_BUNDLE_MISSING":
        raise RuntimeError(
            "Legacy workspace payload diagnostics did not surface GLOBAL_BUNDLE_MISSING: {!r}".format(
                payload_bundle.get("reason_code")
            )
        )

    status_text = render_status_text(status_payload)
    doctor_text = render_doctor_text(doctor_payload)
    _require_install_surface_line(
        status_text,
        "payload_outcome: global_bundle_missing [fail_closed]",
        label="legacy status payload outcome",
    )
    _require_install_surface_line(
        status_text,
        "workspace_outcome: legacy_fallback_selected [warn]",
        label="legacy status workspace outcome",
    )
    _require_install_surface_line(
        doctor_text,
        "outcome: legacy_fallback_selected [warn]",
        label="legacy doctor workspace outcome",
    )

    return {
        "workspace_root": str(legacy_workspace_root),
        "payload_bundle": payload_bundle,
        "workspace_bundle": workspace_bundle,
        "checks": {
            "legacy_workspace_fallback_visible": True,
            "global_bundle_missing_visible": True,
            "status_surface_aligned": True,
            "doctor_surface_aligned": True,
        },
    }


def _require_install_surface_line(text: str, expected: str, *, label: str) -> None:
    if expected not in text:
        raise RuntimeError(f"Missing {label}: {expected}")


def _run_install_cli(*, target_value: str, temp_home: Path) -> str:
    env = dict(os.environ)
    env["HOME"] = str(temp_home)
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "install-sopify.sh"), "--target", target_value],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown install failure"
        raise InstallError(f"Installer CLI failed: {details}")
    return completed.stdout.strip()


def _run_workspace_bootstrap(*, helper_path: Path, workspace_root: Path) -> str:
    if not helper_path.is_file():
        raise InstallError(f"Missing installed workspace helper: {helper_path}")
    completed = subprocess.run(
        [sys.executable, str(helper_path), "--workspace-root", str(workspace_root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown bootstrap failure"
        raise InstallError(f"Workspace bootstrap helper failed: {details}")
    return completed.stdout.strip()

if __name__ == "__main__":
    raise SystemExit(main())
