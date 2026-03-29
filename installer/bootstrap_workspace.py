#!/usr/bin/env python3
"""Bootstrap or update a workspace-local `.sopify-runtime/` from the global payload.

This file is copied into the host-local Sopify payload as:
`<host-root>/sopify/helpers/bootstrap_workspace.py`.

The script is intentionally self-contained so it can run after installation
without importing modules from the source repository.
"""

from __future__ import annotations

import argparse
import json
from itertools import zip_longest
from pathlib import Path
import re
import shutil
import sys
from tempfile import NamedTemporaryFile
from typing import Any

PAYLOAD_MANIFEST_FILENAME = "payload-manifest.json"
_REQUIRED_BUNDLE_FILES = (
    Path("manifest.json"),
    Path("runtime") / "__init__.py",
    Path("runtime") / "clarification_bridge.py",
    Path("runtime") / "cli_interactive.py",
    Path("runtime") / "develop_checkpoint.py",
    Path("runtime") / "decision_bridge.py",
    Path("runtime") / "gate.py",
    Path("runtime") / "preferences.py",
    Path("runtime") / "workspace_preflight.py",
    Path("scripts") / "sopify_runtime.py",
    Path("scripts") / "runtime_gate.py",
    Path("scripts") / "clarification_bridge_runtime.py",
    Path("scripts") / "develop_checkpoint_runtime.py",
    Path("scripts") / "decision_bridge_runtime.py",
    Path("scripts") / "preferences_preload_runtime.py",
    Path("scripts") / "check-runtime-smoke.sh",
    Path("tests") / "test_runtime.py",
)
_IGNORE_PATTERNS = shutil.ignore_patterns(".DS_Store", "Thumbs.db", "__pycache__")
_VERSION_TOKEN_RE = re.compile(r"[0-9]+|[A-Za-z]+")
_PRERELEASE_RANK = {"dev": -4, "alpha": -3, "beta": -2, "rc": -1}
_WORKSPACE_STUB_REQUIRED_CAPABILITIES = ("runtime_gate", "preferences_preload")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap a workspace-local Sopify runtime bundle.")
    parser.add_argument("--workspace-root", required=True, help="Target project root that should receive `.sopify-runtime/`.")
    parser.add_argument("--activation-root", default=None, help="Optional explicit activation root override.")
    parser.add_argument("--request", default="", help="Raw user request routed through host ingress.")
    parser.add_argument("--requested-root", default=None, help="Optional host-requested root for observability.")
    parser.add_argument("--host-id", default=None, help="Optional host id for observability.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = bootstrap_workspace(
            Path(args.workspace_root).expanduser().resolve(),
            activation_root=Path(args.activation_root).expanduser().resolve() if args.activation_root else None,
            request_text=args.request,
            requested_root=Path(args.requested_root).expanduser().resolve() if args.requested_root else None,
            host_id=args.host_id,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(
            json.dumps(
                {
                    "action": "failed",
                    "state": "INCOMPATIBLE",
                    "reason_code": "UNEXPECTED_ERROR",
                    "workspace_root": str(Path(args.workspace_root).expanduser().resolve()),
                    "bundle_root": str(Path(args.workspace_root).expanduser().resolve() / ".sopify-runtime"),
                    "from_version": None,
                    "to_version": None,
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["action"] != "failed" else 1


def bootstrap_workspace(
    workspace_root: Path,
    *,
    activation_root: Path | None = None,
    request_text: str = "",
    requested_root: Path | None = None,
    host_id: str | None = None,
) -> dict[str, Any]:
    if not workspace_root.exists():
        raise ValueError(f"Workspace does not exist: {workspace_root}")
    if not workspace_root.is_dir():
        raise ValueError(f"Workspace is not a directory: {workspace_root}")

    resolved_activation_root, root_resolution_source, fallback_reason = _resolve_activation_root(
        workspace_root=workspace_root,
        explicit_activation_root=activation_root,
    )
    requested_root = requested_root or workspace_root
    payload_root = Path(__file__).resolve().parents[1]
    payload_manifest_path = payload_root / PAYLOAD_MANIFEST_FILENAME
    payload_manifest = _read_json(payload_manifest_path)
    if not payload_manifest:
        raise ValueError(f"Missing or invalid payload manifest: {payload_manifest_path}")

    bundle_template_root = payload_root / str(payload_manifest.get("bundle_template_dir") or "bundle")
    bundle_manifest_path = bundle_template_root / "manifest.json"
    bundle_manifest = _read_json(bundle_manifest_path)
    if not bundle_manifest:
        raise ValueError(f"Missing or invalid bundle manifest: {bundle_manifest_path}")

    target_bundle_dir = str(payload_manifest.get("default_bundle_dir") or ".sopify-runtime")
    bundle_root = resolved_activation_root / target_bundle_dir
    current_manifest_path = bundle_root / "manifest.json"
    current_manifest = _read_json(current_manifest_path) if current_manifest_path.is_file() else {}

    state, reason_code, message, from_version = _classify_workspace_bundle(
        current_manifest=current_manifest,
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
        current_manifest_path=current_manifest_path,
        bundle_root=bundle_root,
    )
    to_version = _string_or_none(bundle_manifest.get("bundle_version"))

    if state in {"READY", "NEWER_THAN_GLOBAL"}:
        return _result(
            action="skipped",
            state=state,
            reason_code=reason_code,
            workspace_root=workspace_root,
            bundle_root=bundle_root,
            from_version=from_version,
            to_version=to_version,
            message=message,
            activation_root=resolved_activation_root,
            requested_root=requested_root,
            root_resolution_source=root_resolution_source,
            payload_root=payload_root,
            host_id=host_id,
            fallback_reason=fallback_reason,
        )

    if state == "MISSING":
        authorization = _authorize_first_workspace_write(request_text)
        if not authorization["allow_write"]:
            return _result(
                action="skipped",
                state=state,
                reason_code=str(authorization["reason_code"]),
                workspace_root=workspace_root,
                bundle_root=bundle_root,
                from_version=from_version,
                to_version=to_version,
                message=str(authorization["message"]),
                activation_root=resolved_activation_root,
                requested_root=requested_root,
                root_resolution_source=root_resolution_source,
                payload_root=payload_root,
                host_id=host_id,
                authorization_mode=str(authorization["mode"]),
                fallback_reason=fallback_reason,
            )

    _sync_bundle(bundle_template_root=bundle_template_root, bundle_root=bundle_root)
    _validate_bundle(bundle_root)
    _write_workspace_stub_overlay(
        bundle_root=bundle_root,
        workspace_root=resolved_activation_root,
    )
    action = "bootstrapped" if state == "MISSING" else "updated"
    return _result(
        action=action,
        state=state,
        reason_code=reason_code,
        workspace_root=workspace_root,
        bundle_root=bundle_root,
        from_version=from_version,
        to_version=to_version,
        message=message,
        activation_root=resolved_activation_root,
        requested_root=requested_root,
        root_resolution_source=root_resolution_source,
        payload_root=payload_root,
        host_id=host_id,
        authorization_mode="explicit_allow" if state == "MISSING" else "",
        fallback_reason=fallback_reason,
    )


_BLOCKED_BOOTSTRAP_COMMAND_PATTERNS = (
    re.compile(r"^~compare(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~go\s+finalize(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~go\s+exec(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~summary(?:\s|$)", re.IGNORECASE),
)
_ALLOWED_BOOTSTRAP_COMMAND_PATTERNS = (
    re.compile(r"^~go\s+plan(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~go\s+init(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~go(?:\s|$)", re.IGNORECASE),
)
_BRAKE_LAYER_PATTERNS = (
    re.compile(r"(不要改|先分析|只解释|不写文件|别写文件|先别写)", re.IGNORECASE),
    re.compile(r"(do not|don't|no need to)\s+(write|edit|modify|change)", re.IGNORECASE),
    re.compile(r"(explain-only|read-only)", re.IGNORECASE),
)


def _authorize_first_workspace_write(request_text: str) -> dict[str, object]:
    text = str(request_text or "").strip()
    if not text:
        return {
            "allow_write": True,
            "mode": "host_installer_default",
            "reason_code": "WORKSPACE_BOOTSTRAP_AUTHORIZED_DEFAULT",
            "message": "Workspace bootstrap was requested explicitly by the installer flow.",
        }

    if any(pattern.search(text) for pattern in _BLOCKED_BOOTSTRAP_COMMAND_PATTERNS):
        return {
            "allow_write": False,
            "mode": "blocked_command",
            "reason_code": "COMMAND_NOT_BOOTSTRAP_AUTHORIZED",
            "message": "Workspace bootstrap is not allowed for this command on an unactivated workspace.",
        }
    if any(pattern.search(text) for pattern in _BRAKE_LAYER_PATTERNS):
        return {
            "allow_write": False,
            "mode": "brake_layer_blocked",
            "reason_code": "BRAKE_LAYER_BLOCKED",
            "message": "Workspace bootstrap was blocked by an explicit no-write or explain-only request.",
        }
    if any(pattern.search(text) for pattern in _ALLOWED_BOOTSTRAP_COMMAND_PATTERNS):
        return {
            "allow_write": True,
            "mode": "explicit_allow",
            "reason_code": "WORKSPACE_BOOTSTRAP_AUTHORIZED_EXPLICIT",
            "message": "Workspace bootstrap is authorized for this explicit command.",
        }
    return {
        "allow_write": False,
        "mode": "no_write_consult",
        "reason_code": "FIRST_WRITE_NOT_AUTHORIZED",
        "message": "Workspace bootstrap requires an explicit `~go`, `~go plan`, or `~go init` command on first write.",
    }


def _resolve_activation_root(
    *,
    workspace_root: Path,
    explicit_activation_root: Path | None,
) -> tuple[Path, str, str]:
    if explicit_activation_root is not None:
        if not explicit_activation_root.exists():
            raise ValueError(f"Explicit activation root does not exist: {explicit_activation_root}")
        if not explicit_activation_root.is_dir():
            raise ValueError(f"Explicit activation root is not a directory: {explicit_activation_root}")
        return (explicit_activation_root, "explicit_root", "")

    for ancestor in workspace_root.parents:
        marker_path = ancestor / ".sopify-runtime" / "manifest.json"
        if not marker_path.is_file():
            continue
        if _marker_has_minimum_validity(marker_path):
            return (ancestor, "ancestor_marker", "")
        return (workspace_root, "cwd", "invalid_ancestor_marker")

    return (workspace_root, "cwd", "")


def _marker_has_minimum_validity(marker_path: Path) -> bool:
    payload = _read_json(marker_path)
    if not payload:
        return False
    return isinstance(payload.get("schema_version"), str) and bool(str(payload.get("schema_version") or "").strip())


def _classify_workspace_bundle(
    *,
    current_manifest: dict[str, Any],
    payload_manifest: dict[str, Any],
    bundle_manifest: dict[str, Any],
    current_manifest_path: Path,
    bundle_root: Path,
) -> tuple[str, str, str, str | None]:
    if not current_manifest_path.is_file():
        return ("MISSING", "MISSING_BUNDLE", "Workspace bundle is missing and will be bootstrapped.", None)

    if not current_manifest:
        return (
            "INCOMPATIBLE",
            "INVALID_WORKSPACE_MANIFEST",
            "Workspace bundle manifest is unreadable and will be replaced.",
            None,
        )

    state, reason_code, message, from_version = _classify_workspace_manifest_contract(
        current_manifest=current_manifest,
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
    )
    if state != "READY":
        return (state, reason_code, message, from_version)

    missing_files = _classify_workspace_runtime_files(bundle_root)
    if missing_files:
        return (
            "INCOMPATIBLE",
            "MISSING_REQUIRED_FILE",
            f"Workspace bundle is missing required files: {', '.join(missing_files)}.",
            from_version,
        )

    workspace_version = from_version
    desired_version = _string_or_none(bundle_manifest.get("bundle_version"))
    comparison = _compare_versions(workspace_version, desired_version)
    if comparison < 0:
        return (
            "OUTDATED_COMPATIBLE",
            "WORKSPACE_BUNDLE_OUTDATED",
            "Workspace bundle is compatible but older than the installed global payload and will be updated.",
            workspace_version,
        )
    if comparison > 0:
        return (
            "NEWER_THAN_GLOBAL",
            "WORKSPACE_BUNDLE_NEWER_THAN_GLOBAL",
            "Workspace bundle is newer than the installed global payload; bootstrap will not downgrade it.",
            workspace_version,
        )
    return (
        "READY",
        "WORKSPACE_BUNDLE_READY",
        "Workspace bundle is already compatible and up to date.",
        workspace_version,
    )


def _classify_workspace_manifest_contract(
    *,
    current_manifest: dict[str, Any],
    payload_manifest: dict[str, Any],
    bundle_manifest: dict[str, Any],
) -> tuple[str, str, str, str | None]:
    minimum_manifest = payload_manifest.get("minimum_workspace_manifest") or {}
    expected_schema = str(minimum_manifest.get("schema_version") or bundle_manifest.get("schema_version") or "1")
    workspace_schema = str(current_manifest.get("schema_version") or "")
    from_version = _string_or_none(current_manifest.get("bundle_version"))
    if workspace_schema != expected_schema:
        return (
            "INCOMPATIBLE",
            "SCHEMA_VERSION_MISMATCH",
            f"Workspace bundle schema {workspace_schema or '<missing>'} is incompatible with required schema {expected_schema}.",
            from_version,
        )

    required_capabilities = minimum_manifest.get("required_capabilities") or {}
    missing_paths = _find_missing_capabilities(required_capabilities, current_manifest.get("capabilities") or {})
    if missing_paths:
        return (
            "INCOMPATIBLE",
            "MISSING_REQUIRED_CAPABILITY",
            f"Workspace bundle is missing required capabilities: {', '.join(missing_paths)}.",
            from_version,
        )
    return ("READY", "WORKSPACE_MANIFEST_VALID", "Workspace manifest satisfies the minimum contract.", from_version)


def _classify_workspace_runtime_files(bundle_root: Path) -> list[str]:
    return _find_missing_required_files(bundle_root)


def _find_missing_capabilities(required: dict[str, Any], actual: dict[str, Any], prefix: str = "") -> list[str]:
    missing: list[str] = []
    for key, value in required.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in actual:
            missing.append(path)
            continue
        actual_value = actual[key]
        if isinstance(value, dict):
            if not isinstance(actual_value, dict):
                missing.append(path)
                continue
            missing.extend(_find_missing_capabilities(value, actual_value, path))
            continue
        if actual_value != value:
            missing.append(path)
    return missing


def _find_missing_required_files(bundle_root: Path) -> list[str]:
    return [str(path) for path in _REQUIRED_BUNDLE_FILES if not (bundle_root / path).exists()]


def _sync_bundle(*, bundle_template_root: Path, bundle_root: Path) -> None:
    if not bundle_template_root.is_dir():
        raise ValueError(f"Missing payload bundle template: {bundle_template_root}")
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_template_root, bundle_root, ignore=_IGNORE_PATTERNS)


def _validate_bundle(bundle_root: Path) -> None:
    missing = [path for path in _REQUIRED_BUNDLE_FILES if not (bundle_root / path).exists()]
    if missing:
        raise ValueError(f"Workspace bootstrap produced an incomplete bundle: {bundle_root / missing[0]}")
    # Re-write the manifest atomically to ensure the copied bundle did not pick up a partial file.
    manifest_path = bundle_root / "manifest.json"
    payload = _read_json(manifest_path)
    with NamedTemporaryFile("w", delete=False, dir=manifest_path.parent, encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(manifest_path)


def _write_workspace_stub_overlay(*, bundle_root: Path, workspace_root: Path) -> None:
    manifest_path = bundle_root / "manifest.json"
    payload = _read_json(manifest_path)
    if not payload:
        raise ValueError(f"Workspace bootstrap produced an unreadable manifest: {manifest_path}")
    payload.update(
        {
            # During the transition window the workspace manifest remains a
            # superset of the old bundle manifest plus the new thin-stub
            # contract fields. This keeps existing vendored-entry consumers
            # working while the classifier/inspection pipeline shifts to the
            # stub-first model.
            "stub_version": "1",
            "required_capabilities": list(_WORKSPACE_STUB_REQUIRED_CAPABILITIES),
            "locator_mode": "global_first",
            "legacy_fallback": False,
            "ignore_mode": _default_ignore_mode(workspace_root),
            "written_by_host": True,
        }
    )
    with NamedTemporaryFile("w", delete=False, dir=manifest_path.parent, encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(manifest_path)


def _default_ignore_mode(workspace_root: Path) -> str:
    if (workspace_root / ".git").exists():
        return "exclude"
    return "noop"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _compare_versions(left: str | None, right: str | None) -> int:
    if left == right:
        return 0
    if left is None:
        return -1
    if right is None:
        return 1
    left_key = _version_key(left)
    right_key = _version_key(right)
    for left_part, right_part in zip_longest(left_key, right_key, fillvalue=None):
        if left_part == right_part:
            continue
        if left_part is None:
            return _tail_comparison(right_key, from_index=len(left_key), default=-1)
        if right_part is None:
            return -_tail_comparison(left_key, from_index=len(right_key), default=-1)
        if left_part < right_part:
            return -1
        return 1
    return 0


def _version_key(value: str) -> list[tuple[int, int | str]]:
    key: list[tuple[int, int | str]] = []
    for token in _VERSION_TOKEN_RE.findall(value):
        if token.isdigit():
            key.append((0, int(token)))
            continue
        normalized = token.lower()
        rank = _PRERELEASE_RANK.get(normalized)
        if rank is not None:
            key.append((1, rank))
        else:
            key.append((2, normalized))
    return key


def _tail_comparison(parts: list[tuple[int, int | str]], *, from_index: int, default: int) -> int:
    for kind, value in parts[from_index:]:
        if kind == 1 and isinstance(value, int) and value < 0:
            return 1
        return default
    return 0


def _result(
    *,
    action: str,
    state: str,
    reason_code: str,
    workspace_root: Path,
    bundle_root: Path,
    from_version: str | None,
    to_version: str | None,
    message: str,
    activation_root: Path | None = None,
    requested_root: Path | None = None,
    root_resolution_source: str = "",
    payload_root: Path | None = None,
    host_id: str | None = None,
    authorization_mode: str = "",
    fallback_reason: str = "",
) -> dict[str, Any]:
    payload = {
        "action": action,
        "state": state,
        "reason_code": reason_code,
        "workspace_root": str(workspace_root),
        "bundle_root": str(bundle_root),
        "from_version": from_version,
        "to_version": to_version,
        "message": message,
    }
    if activation_root is not None:
        payload["activation_root"] = str(activation_root)
    if requested_root is not None:
        payload["requested_root"] = str(requested_root)
    if root_resolution_source:
        payload["root_resolution_source"] = root_resolution_source
    if payload_root is not None:
        payload["payload_root"] = str(payload_root)
    if host_id:
        payload["host_id"] = host_id
    if authorization_mode:
        payload["authorization_mode"] = authorization_mode
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


if __name__ == "__main__":
    raise SystemExit(main())
