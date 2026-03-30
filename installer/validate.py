"""Post-install validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from installer.hosts.base import HostAdapter
from installer.models import InstallError

_STUB_LOCATOR_MODES = {"global_first", "global_only"}
_STUB_IGNORE_MODES = {"exclude", "gitignore", "noop"}
_STUB_REQUIRED_CAPABILITIES = {"runtime_gate", "preferences_preload"}
_EXACT_BUNDLE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_DEFAULT_VERSIONED_BUNDLES_DIR = Path("bundles")
_LEGACY_BUNDLE_MANIFEST_PATH = Path("bundle") / "manifest.json"


def validate_host_install(adapter: HostAdapter, *, home_root: Path) -> tuple[Path, ...]:
    """Ensure the expected host-side files exist after installation."""
    expected_paths = adapter.expected_paths(home_root)
    missing = [path for path in expected_paths if not path.exists()]
    if missing:
        raise InstallError(f"Host install verification failed: {missing[0]}")
    return expected_paths


def validate_bundle_install(bundle_root: Path) -> tuple[Path, ...]:
    """Ensure the synced bundle contains the minimum required assets."""
    expected_paths = expected_bundle_paths(bundle_root)
    missing = [path for path in expected_paths if not path.exists()]
    if missing:
        raise InstallError(f"Bundle verification failed: {missing[0]}")
    return expected_paths


def validate_payload_install(payload_root: Path) -> tuple[Path, ...]:
    """Ensure the host-local Sopify payload contains its manifest, helper, and bundle template."""
    payload_manifest_path, _payload_manifest, bundle_manifest_path, _bundle_manifest = validate_payload_manifests(payload_root)
    return (
        payload_manifest_path,
        payload_root / "helpers" / "bootstrap_workspace.py",
        bundle_manifest_path,
        *validate_bundle_install(bundle_manifest_path.parent),
    )


def run_bundle_smoke_check(bundle_root: Path) -> str:
    """Run the vendored bundle smoke check and return its stdout."""
    smoke_script = bundle_root / "scripts" / "check-runtime-smoke.sh"
    if not smoke_script.is_file():
        raise InstallError(f"Missing bundle smoke script: {smoke_script}")

    completed = subprocess.run(
        ["bash", str(smoke_script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown smoke failure"
        raise InstallError(f"Bundle smoke check failed: {details}")
    return completed.stdout.strip()


def expected_bundle_paths(bundle_root: Path) -> tuple[Path, ...]:
    """Return the stable set of files every Sopify bundle must contain."""
    return (
        bundle_root / "manifest.json",
        bundle_root / "runtime" / "__init__.py",
        bundle_root / "runtime" / "clarification_bridge.py",
        bundle_root / "runtime" / "cli_interactive.py",
        bundle_root / "runtime" / "develop_checkpoint.py",
        bundle_root / "runtime" / "decision_bridge.py",
        bundle_root / "runtime" / "gate.py",
        bundle_root / "runtime" / "preferences.py",
        bundle_root / "runtime" / "workspace_preflight.py",
        bundle_root / "scripts" / "sopify_runtime.py",
        bundle_root / "scripts" / "runtime_gate.py",
        bundle_root / "scripts" / "clarification_bridge_runtime.py",
        bundle_root / "scripts" / "develop_checkpoint_runtime.py",
        bundle_root / "scripts" / "decision_bridge_runtime.py",
        bundle_root / "scripts" / "preferences_preload_runtime.py",
        bundle_root / "scripts" / "check-runtime-smoke.sh",
        bundle_root / "tests" / "test_runtime.py",
    )


def validate_payload_manifests(
    payload_root: Path,
    bundle_version: str | None = None,
) -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
    """Load the top-level payload manifest plus the global bundle manifest."""
    payload_manifest_path = payload_root / "payload-manifest.json"
    helper_path = payload_root / "helpers" / "bootstrap_workspace.py"
    if not payload_manifest_path.exists():
        raise InstallError(f"Payload verification failed: {payload_manifest_path}")
    if not helper_path.exists():
        raise InstallError(f"Payload verification failed: {helper_path}")
    payload_manifest = _read_json_object(payload_manifest_path)
    bundle_manifest_path = _resolve_payload_bundle_manifest_path(
        payload_root,
        payload_manifest,
        bundle_version=bundle_version,
    )
    bundle_manifest = _read_json_object(bundle_manifest_path)
    return (payload_manifest_path, payload_manifest, bundle_manifest_path, bundle_manifest)


def resolve_payload_bundle_root(payload_root: Path, *, bundle_version: str | None = None) -> Path:
    """Resolve the concrete payload bundle root for the active or requested version."""
    _payload_manifest_path, payload_manifest = _load_payload_manifest(payload_root)
    return _resolve_payload_bundle_manifest_path(payload_root, payload_manifest, bundle_version=bundle_version).parent


def validate_workspace_bundle_manifest(bundle_root: Path) -> tuple[Path, dict[str, Any]]:
    """Load the workspace-local control-plane manifest without asserting full bundle contents."""
    manifest_path = bundle_root / "manifest.json"
    manifest = _read_json_object(manifest_path)
    return (manifest_path, manifest)


def validate_workspace_stub_manifest(bundle_root: Path) -> tuple[Path, dict[str, Any]]:
    """Validate and normalize the thin-stub contract embedded in the workspace manifest."""
    manifest_path, manifest = validate_workspace_bundle_manifest(bundle_root)
    workspace_root = bundle_root.parent
    normalized = dict(manifest)
    normalized["stub_version"] = str(normalized.get("stub_version") or "1")
    normalized["locator_mode"] = _normalize_locator_mode(normalized.get("locator_mode"))
    normalized["bundle_version"] = _normalize_bundle_version(normalized.get("bundle_version"))
    normalized["required_capabilities"] = _normalize_required_capabilities(normalized.get("required_capabilities"))
    normalized["legacy_fallback"] = bool(normalized.get("legacy_fallback", False))
    if normalized["locator_mode"] == "global_only" and normalized["legacy_fallback"]:
        raise InstallError(f"Stub verification failed: {manifest_path}")
    normalized["ignore_mode"] = _normalize_ignore_mode(normalized.get("ignore_mode"), workspace_root=workspace_root)
    normalized["written_by_host"] = bool(normalized.get("written_by_host", False))
    return (manifest_path, normalized)


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise InstallError(f"Payload verification failed: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"JSON verification failed: {path}") from exc
    if not isinstance(payload, dict):
        raise InstallError(f"JSON verification failed: {path}")
    return payload


def _load_payload_manifest(payload_root: Path) -> tuple[Path, dict[str, Any]]:
    payload_manifest_path = payload_root / "payload-manifest.json"
    payload_manifest = _read_json_object(payload_manifest_path)
    return (payload_manifest_path, payload_manifest)


def _resolve_payload_bundle_manifest_path(
    payload_root: Path,
    payload_manifest: dict[str, Any],
    *,
    bundle_version: str | None = None,
) -> Path:
    requested_version = _normalize_payload_bundle_version(bundle_version) if bundle_version is not None else None
    bundles_dir = _bundles_dir_from_manifest(payload_root, payload_manifest)
    active_version = _payload_active_version(payload_manifest)
    if requested_version is not None:
        if bundles_dir is not None:
            return payload_root / bundles_dir / requested_version / "manifest.json"
        if active_version == requested_version:
            return _legacy_bundle_manifest_path(payload_root, payload_manifest)
        return payload_root / _DEFAULT_VERSIONED_BUNDLES_DIR / requested_version / "manifest.json"
    if bundles_dir is not None:
        if active_version is None:
            raise InstallError("Payload verification failed: active_version")
        return payload_root / bundles_dir / active_version / "manifest.json"
    return _legacy_bundle_manifest_path(payload_root, payload_manifest)


def _bundles_dir_from_manifest(payload_root: Path, payload_manifest: dict[str, Any]) -> Path | None:
    return _resolve_payload_relative_path(payload_root, payload_manifest.get("bundles_dir"), field_name="bundles_dir")


def _payload_active_version(payload_manifest: dict[str, Any]) -> str | None:
    if "active_version" in payload_manifest:
        return _normalize_payload_bundle_version(payload_manifest.get("active_version"))
    if "bundle_version" in payload_manifest:
        return _normalize_payload_bundle_version(payload_manifest.get("bundle_version"))
    return None


def _legacy_bundle_manifest_path(payload_root: Path, payload_manifest: dict[str, Any]) -> Path:
    relative = _resolve_payload_relative_path(payload_root, payload_manifest.get("bundle_manifest"), field_name="bundle_manifest")
    if relative:
        return payload_root / relative
    return payload_root / _LEGACY_BUNDLE_MANIFEST_PATH


def _resolve_payload_relative_path(payload_root: Path, value: Any, *, field_name: str) -> Path | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    candidate = Path(normalized)
    if candidate.is_absolute():
        raise InstallError(f"Payload verification failed: {field_name}")
    if ".." in candidate.parts:
        raise InstallError(f"Payload verification failed: {field_name}")
    resolved_root = payload_root.resolve()
    resolved_candidate = (resolved_root / candidate).resolve()
    try:
        return resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise InstallError(f"Payload verification failed: {field_name}") from exc


def _normalize_payload_bundle_version(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized == "latest" or not _EXACT_BUNDLE_VERSION_RE.match(normalized):
        raise InstallError("Payload verification failed: bundle_version")
    return normalized


def _normalize_locator_mode(value: Any) -> str:
    normalized = str(value or "global_first").strip() or "global_first"
    if normalized not in _STUB_LOCATOR_MODES:
        raise InstallError("Stub verification failed: locator_mode")
    return normalized


def _normalize_bundle_version(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized == "latest" or not _EXACT_BUNDLE_VERSION_RE.match(normalized):
        raise InstallError("Stub verification failed: bundle_version")
    return normalized


def _normalize_required_capabilities(value: Any) -> list[str]:
    if value in (None, ""):
        return ["runtime_gate", "preferences_preload"]
    if not isinstance(value, (list, tuple)):
        raise InstallError("Stub verification failed: required_capabilities")
    normalized: list[str] = []
    for item in value:
        capability = str(item or "").strip()
        if capability not in _STUB_REQUIRED_CAPABILITIES or capability in normalized:
            raise InstallError("Stub verification failed: required_capabilities")
        normalized.append(capability)
    return normalized or ["runtime_gate", "preferences_preload"]


def _normalize_ignore_mode(value: Any, *, workspace_root: Path) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "exclude" if (workspace_root / ".git").exists() else "noop"
    if normalized not in _STUB_IGNORE_MODES:
        raise InstallError("Stub verification failed: ignore_mode")
    return normalized
