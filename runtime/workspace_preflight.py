"""Shared workspace preflight/bootstrap helpers for Sopify host entries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


class WorkspacePreflightError(RuntimeError):
    """Raised when workspace runtime preflight cannot complete safely."""


_HOST_PAYLOAD_SUFFIXES = {
    "codex": Path(".codex") / "sopify",
    "claude": Path(".claude") / "sopify",
}


def preflight_workspace_runtime(
    workspace_root: Path,
    *,
    request_text: str = "",
    payload_manifest_path: str | Path | None = None,
    activation_root: str | Path | None = None,
    payload_root: str | Path | None = None,
    host_id: str | None = None,
    requested_root: str | Path | None = None,
    user_home: Path | None = None,
) -> Mapping[str, Any]:
    """Best-effort repo-local workspace preflight using the installed payload helper.

    The vendored bundle flow should already have been selected by the host via
    manifest-first preflight, so a bundle-local entry intentionally skips
    self-updating the workspace bundle it is currently executing from.
    """

    resolved_workspace_root = workspace_root.resolve()
    activation_root_path = Path(activation_root).expanduser().resolve() if activation_root is not None else resolved_workspace_root
    repo_root = Path(__file__).resolve().parents[1]
    bundle_root = resolved_workspace_root / ".sopify-runtime"
    requested_root_path = Path(requested_root).expanduser().resolve() if requested_root is not None else resolved_workspace_root
    root_resolution_source = "cwd"
    if repo_root == bundle_root:
        return {
            "action": "skipped",
            "reason_code": "RUNNING_FROM_WORKSPACE_BUNDLE",
            "message": "Current entry is already running from the workspace bundle; host preflight remains authoritative.",
            "activation_root": str(activation_root_path),
            "requested_root": str(requested_root_path),
            "root_resolution_source": root_resolution_source,
        }

    payload_manifest = None
    payload_manifest_file = None
    detected_host_id = str(host_id or "").strip() or None
    home_root = Path(user_home).expanduser().resolve() if user_home is not None else Path.home()
    if payload_manifest_path is not None:
        explicit_path = Path(payload_manifest_path).expanduser().resolve()
        payload_manifest, payload_manifest_file, inferred_host_id = _load_explicit_payload_manifest(explicit_path)
        detected_host_id = detected_host_id or inferred_host_id
    elif payload_root is not None:
        explicit_payload_root = Path(payload_root).expanduser().resolve()
        payload_manifest, payload_manifest_file = _load_payload_manifest_from_root(explicit_payload_root)
    else:
        if detected_host_id:
            payload_manifest, payload_manifest_file = _load_payload_manifest_from_root(
                _payload_root_for_host(home_root=home_root, host_id=detected_host_id)
            )
        else:
            env_manifest = (os.environ.get("SOPIFY_PAYLOAD_MANIFEST") or "").strip()
            manifest_candidates: list[tuple[Path, str | None]] = []
            if env_manifest:
                env_path = Path(env_manifest).expanduser().resolve()
                manifest_candidates.append((env_path, _infer_host_id_from_manifest_path(env_path)))
            manifest_candidates.extend(
                [
                    (home_root / ".codex" / "sopify" / "payload-manifest.json", "codex"),
                    (home_root / ".claude" / "sopify" / "payload-manifest.json", "claude"),
                ]
            )
            payload_manifest, payload_manifest_file, detected_host_id = _discover_payload_manifest(manifest_candidates)
            if payload_manifest is None or payload_manifest_file is None:
                return {
                    "action": "skipped",
                    "reason_code": "PAYLOAD_MANIFEST_NOT_FOUND",
                    "message": "No installed host payload was found; continuing with repo-local entry.",
                    "activation_root": str(activation_root_path),
                    "requested_root": str(requested_root_path),
                    "root_resolution_source": root_resolution_source,
                }

    if payload_manifest is None or payload_manifest_file is None:
        raise WorkspacePreflightError("Payload manifest resolution failed unexpectedly")
    helper_entry = str(payload_manifest.get("helper_entry") or "").strip()
    if not helper_entry:
        raise WorkspacePreflightError(f"Payload manifest is missing helper_entry: {payload_manifest_file}")
    payload_root = payload_manifest_file.parent
    bundle_manifest_path = _resolve_bundle_manifest_path(payload_root=payload_root, payload_manifest=payload_manifest)
    _read_json_object(bundle_manifest_path, error_prefix="Invalid bundle manifest")
    global_bundle_root = bundle_manifest_path.parent
    helper_path = _resolve_helper_path(payload_root=payload_root, helper_entry=helper_entry)
    if not helper_path.is_file():
        raise WorkspacePreflightError(f"Workspace bootstrap helper is missing: {helper_path}")

    command = [sys.executable, str(helper_path), "--workspace-root", str(resolved_workspace_root), "--request", request_text]
    if activation_root is not None:
        command.extend(["--activation-root", str(activation_root_path)])
    if detected_host_id:
        command.extend(["--host-id", detected_host_id])
    if requested_root is not None:
        command.extend(["--requested-root", str(requested_root_path)])
    completed, helper_argv_mode = _run_bootstrap_helper_with_compatibility(
        helper_path=helper_path,
        workspace_root=resolved_workspace_root,
        command=command,
    )
    stdout = completed.stdout.strip()
    try:
        result = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        detail = stdout or completed.stderr.strip()
        raise WorkspacePreflightError(f"Workspace bootstrap returned invalid JSON: {detail}") from exc

    if not isinstance(result, Mapping):
        raise WorkspacePreflightError("Workspace bootstrap returned a non-object JSON payload")

    if completed.returncode != 0 or str(result.get("action") or "").strip() == "failed":
        message = str(result.get("message") or completed.stderr.strip() or stdout or "unknown bootstrap failure")
        raise WorkspacePreflightError(f"Workspace preflight failed: {message}")
    payload = dict(result)
    payload.setdefault("activation_root", str(activation_root_path))
    payload.setdefault("requested_root", str(requested_root_path))
    payload.setdefault("root_resolution_source", root_resolution_source)
    payload.setdefault("payload_root", str(payload_root))
    payload.setdefault("bundle_manifest_path", str(bundle_manifest_path))
    payload.setdefault("global_bundle_root", str(global_bundle_root))
    payload.setdefault("helper_path", str(helper_path))
    payload.setdefault("helper_argv_mode", helper_argv_mode)
    if detected_host_id:
        payload.setdefault("host_id", detected_host_id)
    return payload


def _infer_host_id_from_manifest_path(path: Path) -> str | None:
    normalized_parts = {part.lower() for part in path.parts}
    if ".codex" in normalized_parts:
        return "codex"
    if ".claude" in normalized_parts:
        return "claude"
    return None


def _load_explicit_payload_manifest(path: Path) -> tuple[dict[str, Any], Path, str | None]:
    if not path.exists() or not path.is_file():
        raise WorkspacePreflightError(f"Explicit payload manifest not found: {path}")
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkspacePreflightError(f"Explicit payload manifest not found: {path}") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise WorkspacePreflightError(f"Explicit payload manifest is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise WorkspacePreflightError(f"Explicit payload manifest must be a JSON object: {path}")
    helper_entry = payload.get("helper_entry")
    if not isinstance(helper_entry, str) or not helper_entry.strip():
        raise WorkspacePreflightError(f"Explicit payload manifest is missing helper_entry: {path}")
    return (payload, path, _infer_host_id_from_manifest_path(path))


def _load_payload_manifest_from_root(payload_root: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = payload_root / "payload-manifest.json"
    payload = _read_json_object(manifest_path, error_prefix="Invalid payload manifest")
    helper_entry = payload.get("helper_entry")
    if not isinstance(helper_entry, str) or not helper_entry.strip():
        raise WorkspacePreflightError(f"Payload manifest is missing helper_entry: {manifest_path}")
    return (payload, manifest_path)


def _discover_payload_manifest(
    manifest_candidates: list[tuple[Path, str | None]],
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    payload_manifest = None
    payload_manifest_file = None
    detected_host_id = None
    for candidate, host_id in manifest_candidates:
        if not candidate.is_file():
            continue
        try:
            payload_manifest = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkspacePreflightError(f"Invalid payload manifest: {candidate}") from exc
        if isinstance(payload_manifest, dict):
            payload_manifest_file = candidate
            detected_host_id = host_id
            break
    return (payload_manifest, payload_manifest_file, detected_host_id)


def _resolve_helper_path(*, payload_root: Path, helper_entry: str) -> Path:
    normalized_entry = str(helper_entry or "").strip()
    if not normalized_entry:
        raise WorkspacePreflightError(f"Invalid helper_entry: helper_entry=<empty>, payload_root={payload_root}")
    helper_candidate = Path(normalized_entry)
    if helper_candidate.is_absolute():
        resolved = helper_candidate.resolve()
        raise WorkspacePreflightError(
            f"Invalid helper_entry: helper_entry={normalized_entry}, resolved_helper_path={resolved}, payload_root={payload_root}"
        )
    resolved = (payload_root / helper_candidate).resolve()
    try:
        resolved.relative_to(payload_root.resolve())
    except ValueError as exc:
        raise WorkspacePreflightError(
            f"Invalid helper_entry: helper_entry={normalized_entry}, resolved_helper_path={resolved}, payload_root={payload_root}"
        ) from exc
    return resolved


def _resolve_bundle_manifest_path(*, payload_root: Path, payload_manifest: Mapping[str, Any]) -> Path:
    bundle_manifest = str(payload_manifest.get("bundle_manifest") or "bundle/manifest.json").strip()
    if not bundle_manifest:
        raise WorkspacePreflightError(f"Invalid bundle_manifest path: payload_root={payload_root}")
    bundle_candidate = Path(bundle_manifest)
    if bundle_candidate.is_absolute():
        raise WorkspacePreflightError(f"Invalid bundle_manifest path: {bundle_candidate}")
    resolved = (payload_root / bundle_candidate).resolve()
    try:
        resolved.relative_to(payload_root.resolve())
    except ValueError as exc:
        raise WorkspacePreflightError(f"Invalid bundle_manifest path: {resolved}") from exc
    return resolved


def _payload_manifest_path_for_host(*, home_root: Path, host_id: str) -> Path:
    normalized_host_id = str(host_id or "").strip()
    suffix = _HOST_PAYLOAD_SUFFIXES.get(normalized_host_id)
    if suffix is None:
        raise WorkspacePreflightError(f"Unsupported host id for payload discovery: {normalized_host_id or '<empty>'}")
    return home_root / suffix / "payload-manifest.json"


def _payload_root_for_host(*, home_root: Path, host_id: str) -> Path:
    return _payload_manifest_path_for_host(home_root=home_root, host_id=host_id).parent


def _read_json_object(path: Path, *, error_prefix: str) -> dict[str, Any]:
    if not path.is_file():
        raise WorkspacePreflightError(f"{error_prefix}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspacePreflightError(f"{error_prefix}: {path}") from exc
    if not isinstance(payload, dict):
        raise WorkspacePreflightError(f"{error_prefix}: {path}")
    return payload


def _run_bootstrap_helper_with_compatibility(
    *,
    helper_path: Path,
    workspace_root: Path,
    command: list[str],
) -> tuple[subprocess.CompletedProcess[str], str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if not _looks_like_legacy_argparse_error(completed):
        return (completed, "contract_v2")

    request_preserving_command = _drop_cli_arg_pairs(command, {"--host-id", "--requested-root"})
    if request_preserving_command != command:
        request_preserving_completed = subprocess.run(
            request_preserving_command,
            capture_output=True,
            text=True,
            check=False,
        )
        if not _looks_like_legacy_argparse_error(request_preserving_completed):
            return (request_preserving_completed, "legacy_request_preserved")
        if not _stderr_mentions_unrecognized_argument(request_preserving_completed, "--request"):
            return (request_preserving_completed, "legacy_request_preserved")

    legacy_command = [sys.executable, str(helper_path), "--workspace-root", str(workspace_root)]
    legacy_completed = subprocess.run(
        legacy_command,
        capture_output=True,
        text=True,
        check=False,
    )
    return (legacy_completed, "legacy_fallback")


def _looks_like_legacy_argparse_error(completed: subprocess.CompletedProcess[str]) -> bool:
    if completed.returncode == 0:
        return False
    stderr = (completed.stderr or "").strip()
    return "unrecognized arguments:" in stderr and (
        _stderr_mentions_unrecognized_argument(completed, "--request")
        or _stderr_mentions_unrecognized_argument(completed, "--host-id")
        or _stderr_mentions_unrecognized_argument(completed, "--requested-root")
    )


def _stderr_mentions_unrecognized_argument(completed: subprocess.CompletedProcess[str], argument: str) -> bool:
    stderr = (completed.stderr or "").strip()
    return "unrecognized arguments:" in stderr and argument in stderr


def _drop_cli_arg_pairs(command: list[str], unsupported_args: set[str]) -> list[str]:
    if len(command) <= 2:
        return list(command)

    arg_tokens = command[2:]
    if len(arg_tokens) % 2 != 0:
        return list(command)

    trimmed_command = list(command[:2])
    for index in range(0, len(arg_tokens), 2):
        flag = arg_tokens[index]
        value = arg_tokens[index + 1]
        if flag in unsupported_args:
            continue
        trimmed_command.extend([flag, value])
    return trimmed_command


__all__ = ["WorkspacePreflightError", "preflight_workspace_runtime"]
