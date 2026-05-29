#!/usr/bin/env python3
"""Bootstrap or update a workspace activation marker from the global payload.

This file is copied into the host-local Sopify payload as:
`<host-root>/sopify/helpers/bootstrap_workspace.py`.

The script is intentionally self-contained so it can run after installation
without importing modules from the source repository.
"""

from __future__ import annotations

import argparse
import json
from itertools import zip_longest
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import NamedTemporaryFile
from typing import Any

try:
    from installer.outcome_contract import annotate_outcome_payload as _annotate_outcome_payload
except ModuleNotFoundError as exc:
    if not str(exc.name or "").startswith("installer"):
        raise

    # This helper is copied into the installed payload and must keep a narrow
    # outcome-contract mirror for standalone execution.
    _PRIMARY_CODE_BY_REASON = {
        "STUB_SELECTED": "stub_selected",
        "STUB_INVALID": "stub_invalid",
        "GLOBAL_BUNDLE_MISSING": "global_bundle_missing",
        "GLOBAL_BUNDLE_INCOMPATIBLE": "global_bundle_incompatible",
        "GLOBAL_INDEX_CORRUPTED": "global_index_corrupted",
        "ROOT_CONFIRM_REQUIRED": "root_confirm_required",
        "READONLY": "readonly",
        "NON_INTERACTIVE": "non_interactive",
    }
    _ACTION_LEVEL_BY_PRIMARY = {
        "stub_selected": "continue",
        "stub_invalid": "fail_closed",
        "global_bundle_missing": "fail_closed",
        "global_bundle_incompatible": "fail_closed",
        "global_index_corrupted": "fail_closed",
        "root_confirm_required": "confirm",
        "readonly": "fail_closed",
        "non_interactive": "fail_closed",
    }
    _ACTION_LEVEL_BY_REASON = {
        "BRAKE_LAYER_BLOCKED": "fail_closed",
        "FIRST_WRITE_NOT_AUTHORIZED": "fail_closed",
        "COMMAND_NOT_BOOTSTRAP_AUTHORIZED": "fail_closed",
        "CONFIRM_BOOTSTRAP_REQUIRED": "confirm",
    }

    def _primary_code_for_reason(reason_code: str | None) -> str | None:
        normalized = str(reason_code or "").strip().upper()
        if not normalized:
            return None
        return _PRIMARY_CODE_BY_REASON.get(normalized)

    def _action_level_for_reason(reason_code: str | None, *, primary_code: str | None = None) -> str | None:
        normalized_primary = str(primary_code or "").strip()
        if normalized_primary:
            return _ACTION_LEVEL_BY_PRIMARY.get(normalized_primary)
        normalized_reason = str(reason_code or "").strip().upper()
        if normalized_reason in _ACTION_LEVEL_BY_REASON:
            return _ACTION_LEVEL_BY_REASON[normalized_reason]
        fallback_primary = _primary_code_for_reason(normalized_reason)
        if fallback_primary is None:
            return None
        return _ACTION_LEVEL_BY_PRIMARY.get(fallback_primary)

    def _annotate_outcome_payload(
        payload: dict[str, Any],
        *,
        reason_code: str | None = None,
        message_hint: str | None = None,
    ) -> dict[str, Any]:
        effective_reason = str(reason_code or payload.get("reason_code") or "").strip()
        primary_code = _primary_code_for_reason(effective_reason)
        action_level = _action_level_for_reason(effective_reason, primary_code=primary_code)
        if primary_code:
            payload.setdefault("primary_code", primary_code)
        if action_level:
            payload.setdefault("action_level", action_level)
        normalized_hint = str(message_hint or payload.get("message_hint") or "").strip()
        if normalized_hint:
            payload.setdefault("message_hint", normalized_hint)
        return payload

PAYLOAD_MANIFEST_FILENAME = "payload-manifest.json"
_REQUIRED_BUNDLE_FILES = (
    Path("manifest.json"),
    Path("sopify_contracts") / "__init__.py",
    Path("canonical_writer") / "__init__.py",
    Path("runtime") / "__init__.py",
    Path("runtime") / "gate.py",
    Path("scripts") / "sopify_runtime.py",
    Path("scripts") / "runtime_gate.py",
)
_IGNORE_PATTERNS = shutil.ignore_patterns(".DS_Store", "Thumbs.db", "__pycache__")
_VERSION_TOKEN_RE = re.compile(r"[0-9]+|[A-Za-z]+")
_EXACT_BUNDLE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PRERELEASE_RANK = {"dev": -4, "alpha": -3, "beta": -2, "rc": -1}
_WORKSPACE_STUB_REQUIRED_CAPABILITIES = ("runtime_gate",)
_WORKSPACE_STUB_LOCATOR_MODES = {"global_first", "global_only"}
_WORKSPACE_STUB_IGNORE_MODES = {"exclude", "gitignore", "noop"}
_SOPIFY_SKILLS_DIR = ".sopify-skills"
_SOPIFY_JSON_FILENAME = "sopify.json"
_SOPIFY_MANAGED_IGNORE_BEGIN = "# BEGIN sopify-managed"
_SOPIFY_MANAGED_IGNORE_END = "# END sopify-managed"
_SOPIFY_MANAGED_IGNORE_ENTRIES = (
    ".sopify-runtime/",
    ".sopify-skills/state/",
    ".sopify-skills/plan/_registry.yaml",
)
_SOPIFY_INSTRUCTION_BLOCK_BEGIN = "<!-- BEGIN SOPIFY MANAGED BLOCK -->"
_SOPIFY_INSTRUCTION_BLOCK_END = "<!-- END SOPIFY MANAGED BLOCK -->"
_INSTRUCTION_RESOURCES_DIR = Path("resources")
REASON_STUB_SELECTED = "STUB_SELECTED"
REASON_STUB_INVALID = "STUB_INVALID"
REASON_CONFIRM_BOOTSTRAP_REQUIRED = "CONFIRM_BOOTSTRAP_REQUIRED"
REASON_ROOT_CONFIRM_REQUIRED = "ROOT_CONFIRM_REQUIRED"
REASON_READONLY = "READONLY"
REASON_NON_INTERACTIVE = "NON_INTERACTIVE"
DIAGNOSTIC_NON_GIT_WORKSPACE = "NON_GIT_WORKSPACE"
DIAGNOSTIC_ROOT_REUSE_ANCESTOR_MARKER = "ROOT_REUSE_ANCESTOR_MARKER"
DIAGNOSTIC_INVALID_ANCESTOR_MARKER = "INVALID_ANCESTOR_MARKER"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap a workspace-local Sopify runtime bundle.")
    parser.add_argument("--workspace-root", required=True, help="Target project root that should receive Sopify workspace metadata.")
    parser.add_argument("--activation-root", default=None, help="Optional explicit activation root override.")
    parser.add_argument("--request", default="", help="Raw user request routed through host ingress.")
    parser.add_argument("--requested-root", default=None, help="Optional host-requested root for observability.")
    parser.add_argument("--host-id", default=None, help="Optional host id for observability.")
    parser.add_argument(
        "--interaction-mode",
        choices=("interactive", "non_interactive"),
        default=None,
        help="Optional host-provided interaction mode for first-write policy.",
    )
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
            interaction_mode=args.interaction_mode,
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
    interaction_mode: str | None = None,
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

    target_bundle_dir = str(payload_manifest.get("default_bundle_dir") or ".sopify-runtime")
    bundle_root = resolved_activation_root / target_bundle_dir
    current_manifest_path = resolved_activation_root / _SOPIFY_SKILLS_DIR / _SOPIFY_JSON_FILENAME
    current_manifest = _read_json(current_manifest_path) if current_manifest_path.is_file() else {}
    (
        selected_bundle_root,
        bundle_manifest_path,
        bundle_manifest,
        global_reason_code,
        global_message,
    ) = _resolve_selected_payload_bundle(
        payload_root=payload_root,
        payload_manifest=payload_manifest,
        current_manifest=current_manifest,
    )
    if not bundle_manifest and bundle_manifest_path is None:
        raise ValueError("Workspace bootstrap could not resolve a global bundle contract")

    state, reason_code, message, from_version = _classify_workspace_bundle(
        current_manifest=current_manifest,
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
        current_manifest_path=current_manifest_path,
        bundle_root=bundle_root,
        global_bundle_root=selected_bundle_root,
        global_reason_code=global_reason_code,
        global_message=global_message,
    )
    to_version = _string_or_none(bundle_manifest.get("bundle_version"))
    current_ignore_mode = _default_ignore_mode(resolved_activation_root)
    if current_manifest_path.is_file() and current_manifest:
        try:
            normalized_manifest = _normalize_workspace_stub_contract(
                current_manifest=current_manifest,
                workspace_root=resolved_activation_root,
            )
        except ValueError:
            normalized_manifest = {}
        current_ignore_mode = str(normalized_manifest.get("ignore_mode") or current_ignore_mode)
    request_authorization = _authorize_first_workspace_write(request_text)
    request_authorization_mode = str(request_authorization["mode"])
    desired_ignore_mode = _resolve_workspace_ignore_mode(
        workspace_root=resolved_activation_root,
        current_ignore_mode=current_ignore_mode,
        request_text=request_text,
        authorization_mode=request_authorization_mode,
    )

    if state in {"READY", "NEWER_THAN_GLOBAL"}:
        ignore_sync_changed = False
        if request_authorization_mode in {"explicit_allow", "explicit_confirm", "host_installer_default"}:
            ignore_sync_changed = _sync_workspace_ignore_policy(
                workspace_root=resolved_activation_root,
                current_ignore_mode=current_ignore_mode,
                desired_ignore_mode=desired_ignore_mode,
            )
            if ignore_sync_changed and current_ignore_mode != desired_ignore_mode:
                _write_workspace_stub_overlay(
                    bundle_root=bundle_root,
                    workspace_root=resolved_activation_root,
                    bundle_manifest=bundle_manifest,
                    ignore_mode=desired_ignore_mode,
                )
            instruction_changed = _sync_workspace_instruction_assets(
                host_id=host_id,
                workspace_root=resolved_activation_root,
                payload_root=payload_root,
            )
            if instruction_changed:
                ignore_sync_changed = True
        return _result(
            action="updated" if ignore_sync_changed else "skipped",
            state=state,
            reason_code=reason_code,
            workspace_root=workspace_root,
            bundle_root=bundle_root,
            from_version=from_version,
            to_version=to_version,
            message=_success_message(
                action="updated" if ignore_sync_changed else "skipped",
                activation_root=resolved_activation_root,
                ignore_mode=desired_ignore_mode,
            ),
            activation_root=resolved_activation_root,
            requested_root=requested_root,
            root_resolution_source=root_resolution_source,
            payload_root=payload_root,
            host_id=host_id,
            fallback_reason=fallback_reason,
            ignore_mode=desired_ignore_mode,
        )

    write_authorization_mode = ""
    if state == "MISSING":
        write_authorization_mode = request_authorization_mode
        if not request_authorization["allow_write"]:
            return _result(
                action="skipped",
                state=state,
                reason_code=str(request_authorization["reason_code"]),
                workspace_root=workspace_root,
                bundle_root=bundle_root,
                from_version=from_version,
                to_version=to_version,
                message=str(request_authorization["message"]),
                activation_root=resolved_activation_root,
                requested_root=requested_root,
                root_resolution_source=root_resolution_source,
                payload_root=payload_root,
                host_id=host_id,
                authorization_mode=write_authorization_mode,
                fallback_reason=fallback_reason,
                ignore_mode=desired_ignore_mode,
            )
        write_barrier = _classify_first_write_barrier(
            workspace_root=workspace_root,
            activation_root=resolved_activation_root,
            explicit_activation_root=activation_root,
            bundle_root=bundle_root,
            root_resolution_source=root_resolution_source,
            fallback_reason=fallback_reason,
            interaction_mode=interaction_mode,
            ignore_mode=desired_ignore_mode,
            authorization_mode=write_authorization_mode,
        )
        if write_barrier is not None:
            return _result(
                action="skipped",
                state=state,
                reason_code=str(write_barrier["reason_code"]),
                workspace_root=workspace_root,
                bundle_root=bundle_root,
                from_version=from_version,
                to_version=to_version,
                message=str(write_barrier["message"]),
                activation_root=resolved_activation_root,
                requested_root=requested_root,
                root_resolution_source=root_resolution_source,
                payload_root=payload_root,
                host_id=host_id,
                authorization_mode=write_authorization_mode,
                fallback_reason=fallback_reason,
                ignore_mode=desired_ignore_mode,
                extra_evidence=tuple(str(item) for item in write_barrier.get("evidence") or ()),
                expose_activation_root=bool(write_barrier.get("expose_activation_root", True)),
                expose_ignore_mode=bool(write_barrier.get("expose_ignore_mode", True)),
            )

    if global_reason_code in {"GLOBAL_BUNDLE_MISSING", "GLOBAL_BUNDLE_INCOMPATIBLE", "GLOBAL_INDEX_CORRUPTED"}:
        return _result(
            action="failed",
            state="INCOMPATIBLE",
            reason_code=global_reason_code,
            workspace_root=workspace_root,
            bundle_root=bundle_root,
            from_version=from_version,
            to_version=to_version,
            message=global_message or message,
            activation_root=resolved_activation_root,
            requested_root=requested_root,
            root_resolution_source=root_resolution_source,
            payload_root=payload_root,
            host_id=host_id,
            fallback_reason=fallback_reason,
            ignore_mode=desired_ignore_mode,
        )

    if selected_bundle_root is None:
        raise ValueError("Workspace bootstrap could not resolve a global bundle template")

    global_state, global_contract_reason_code, global_contract_message = _classify_global_bundle_contract(
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
        global_bundle_root=selected_bundle_root,
    )
    if global_state != "READY":
        return _result(
            action="failed",
            state="INCOMPATIBLE",
            reason_code=global_contract_reason_code,
            workspace_root=workspace_root,
            bundle_root=bundle_root,
            from_version=from_version,
            to_version=to_version,
            message=global_contract_message,
            activation_root=resolved_activation_root,
            requested_root=requested_root,
            root_resolution_source=root_resolution_source,
            payload_root=payload_root,
            host_id=host_id,
            fallback_reason=fallback_reason,
            ignore_mode=desired_ignore_mode,
        )

    _sync_workspace_ignore_policy(
        workspace_root=resolved_activation_root,
        current_ignore_mode=current_ignore_mode,
        desired_ignore_mode=desired_ignore_mode,
    )
    _write_workspace_stub_overlay(
        bundle_root=bundle_root,
        workspace_root=resolved_activation_root,
        bundle_manifest=bundle_manifest,
        ignore_mode=desired_ignore_mode,
    )
    _sync_workspace_instruction_assets(
        host_id=host_id,
        workspace_root=resolved_activation_root,
        payload_root=payload_root,
    )
    action = "bootstrapped" if state == "MISSING" else "updated"
    return _result(
        action=action,
        state=state,
        reason_code=REASON_STUB_SELECTED,
        workspace_root=workspace_root,
        bundle_root=bundle_root,
        from_version=from_version,
        to_version=to_version,
        message=_success_message(
            action=action,
            activation_root=resolved_activation_root,
            ignore_mode=desired_ignore_mode,
        ),
        activation_root=resolved_activation_root,
        requested_root=requested_root,
        root_resolution_source=root_resolution_source,
        payload_root=payload_root,
        host_id=host_id,
        authorization_mode=write_authorization_mode if state == "MISSING" else "",
        fallback_reason=fallback_reason,
        ignore_mode=desired_ignore_mode,
    )


_BLOCKED_BOOTSTRAP_COMMAND_PATTERNS = (
    re.compile(r"^~go\s+finalize(?:\s|$)", re.IGNORECASE),
)
_CONFIRM_BOOTSTRAP_COMMAND_PATTERNS = (
    re.compile(r"^~go\s+init(?:\s|$)", re.IGNORECASE),
)
_ALLOWED_BOOTSTRAP_COMMAND_PATTERNS = (
    re.compile(r"^~go\s+plan(?:\s|$)", re.IGNORECASE),
    re.compile(r"^~go(?:\s|$)", re.IGNORECASE),
)
_BRAKE_LAYER_PATTERNS = (
    re.compile(r"(不要改|先分析|只解释|不写文件|别写文件|先别写)", re.IGNORECASE),
    re.compile(r"(do not|don't|no need to)\s+(write|edit|modify|change)", re.IGNORECASE),
    re.compile(r"(explain-only|read-only)", re.IGNORECASE),
)
_COMMIT_LOCK_PATTERN = re.compile(r"(?<![A-Za-z0-9])commit(?:-| )lock(?![A-Za-z0-9])", re.IGNORECASE)


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
    if any(pattern.search(text) for pattern in _CONFIRM_BOOTSTRAP_COMMAND_PATTERNS):
        return {
            "allow_write": True,
            "mode": "explicit_confirm",
            "reason_code": "WORKSPACE_BOOTSTRAP_AUTHORIZED_CONFIRM",
            "message": "Workspace bootstrap is authorized by the explicit `~go init` confirmation command.",
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


def _classify_first_write_barrier(
    *,
    workspace_root: Path,
    activation_root: Path,
    explicit_activation_root: Path | None,
    bundle_root: Path,
    root_resolution_source: str,
    fallback_reason: str,
    interaction_mode: str | None,
    ignore_mode: str,
    authorization_mode: str,
) -> dict[str, object] | None:
    if interaction_mode == "non_interactive":
        return {
            "reason_code": REASON_NON_INTERACTIVE,
            "message": "This is a non-interactive session. Open an interactive session before enabling Sopify here.",
        }

    if explicit_activation_root is None and root_resolution_source == "cwd" and not fallback_reason:
        repo_root = _find_git_ancestor_root(workspace_root)
        if repo_root is not None and repo_root != workspace_root:
            # Root disambiguation intentionally runs before the non-git confirm.
            # A nested package may still need a follow-up `~go init` confirm on
            # the next pass when the caller explicitly chooses a non-git target.
            return {
                "reason_code": REASON_ROOT_CONFIRM_REQUIRED,
                "message": "Sopify needs you to confirm which directory to enable in this repository. Retry with `activation_root` set to the current directory to enable only this package, or to the repository root to enable the whole repo. You may also provide another directory manually.",
                "expose_activation_root": False,
                "expose_ignore_mode": False,
                "evidence": (
                    f"repo_root={repo_root}",
                    f"recommended_activation_root={workspace_root}",
                    f"alternate_activation_root={repo_root}",
                    "manual_activation_root_allowed=true",
                ),
            }

    if not _can_write_bootstrap_target(bundle_root, workspace_root=activation_root, ignore_mode=ignore_mode):
        return {
            "reason_code": REASON_READONLY,
            "message": "Sopify cannot enable this directory because it is not writable. Fix permissions and retry.",
            "evidence": (f"target_root={activation_root}",),
        }

    if ignore_mode == "noop" and authorization_mode not in {"explicit_confirm", "host_installer_default"}:
        return {
            "reason_code": REASON_CONFIRM_BOOTSTRAP_REQUIRED,
            "message": _confirm_bootstrap_message(
                activation_root=activation_root,
                root_resolution_source=root_resolution_source,
                fallback_reason=fallback_reason,
            ),
        }
    return None


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
        new_marker = ancestor / _SOPIFY_SKILLS_DIR / _SOPIFY_JSON_FILENAME
        if new_marker.is_file() and _marker_has_minimum_validity(new_marker):
            return (ancestor, "ancestor_marker", "")

    return (workspace_root, "cwd", "")


def _find_git_ancestor_root(workspace_root: Path) -> Path | None:
    if _resolve_git_dir(workspace_root) is not None:
        return workspace_root
    for ancestor in workspace_root.parents:
        if _resolve_git_dir(ancestor) is not None:
            return ancestor
    return None


def _can_write_bootstrap_target(bundle_root: Path, *, workspace_root: Path | None = None, ignore_mode: str = "") -> bool:
    candidates = [_writable_probe_path(bundle_root)]
    if workspace_root is not None and ignore_mode:
        ignore_target = _resolve_ignore_target(workspace_root=workspace_root, ignore_mode=ignore_mode)
        if ignore_target is not None:
            candidates.append(_writable_probe_path(ignore_target))
    return all(os.access(candidate, os.W_OK | os.X_OK) for candidate in candidates)


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
    global_bundle_root: Path | None,
    global_reason_code: str | None = None,
    global_message: str | None = None,
) -> tuple[str, str, str, str | None]:
    if not current_manifest_path.is_file():
        return ("MISSING", "MISSING_BUNDLE", "Workspace bundle is missing and will be bootstrapped.", None)

    if not current_manifest:
        return (
            "INCOMPATIBLE",
            REASON_STUB_INVALID,
            "Workspace stub manifest is unreadable and will be replaced.",
            None,
        )

    state, reason_code, message, normalized_manifest = _classify_workspace_stub_contract(
        current_manifest=current_manifest,
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
        workspace_root=bundle_root.parent,
    )
    if state != "READY":
        return (state, reason_code, message, _string_or_none(current_manifest.get("bundle_version")))

    from_version = _string_or_none(normalized_manifest.get("bundle_version")) or _string_or_none(bundle_manifest.get("bundle_version"))

    if global_reason_code:
        return ("INCOMPATIBLE", global_reason_code, global_message or "Selected global bundle is unavailable.", from_version)

    state, reason_code, message = _classify_global_bundle_contract(
        payload_manifest=payload_manifest,
        bundle_manifest=bundle_manifest,
        global_bundle_root=global_bundle_root,
    )
    if state != "READY":
        return (state, reason_code, message, from_version)

    return (
        "READY",
        REASON_STUB_SELECTED,
        "Workspace stub resolves to the selected global bundle.",
        from_version,
    )


def _classify_workspace_stub_contract(
    *,
    current_manifest: dict[str, Any],
    payload_manifest: dict[str, Any],
    bundle_manifest: dict[str, Any],
    workspace_root: Path,
) -> tuple[str, str, str, dict[str, Any]]:
    minimum_manifest = payload_manifest.get("minimum_workspace_manifest") or {}
    expected_schema = str(minimum_manifest.get("schema_version") or bundle_manifest.get("schema_version") or "1")
    workspace_schema = str(current_manifest.get("schema_version") or "")
    if workspace_schema != expected_schema:
        return (
            "INCOMPATIBLE",
            REASON_STUB_INVALID,
            f"Workspace bundle schema {workspace_schema or '<missing>'} is incompatible with required schema {expected_schema}.",
            {},
        )
    try:
        normalized_manifest = _normalize_workspace_stub_contract(current_manifest=current_manifest, workspace_root=workspace_root)
    except ValueError as exc:
        return (
            "INCOMPATIBLE",
            REASON_STUB_INVALID,
            str(exc),
            {},
        )
    return ("READY", REASON_STUB_SELECTED, "Sopify is enabled for this project and points to the selected global bundle.", normalized_manifest)


def _classify_global_bundle_contract(
    *,
    payload_manifest: dict[str, Any],
    bundle_manifest: dict[str, Any],
    global_bundle_root: Path | None,
) -> tuple[str, str, str]:
    if global_bundle_root is None or not bundle_manifest:
        return ("INCOMPATIBLE", "GLOBAL_BUNDLE_MISSING", "Selected global bundle is missing.")
    minimum_manifest = payload_manifest.get("minimum_workspace_manifest") or {}
    required_capabilities = minimum_manifest.get("required_capabilities") or {}
    missing_capabilities = _find_missing_capabilities(required_capabilities, bundle_manifest.get("capabilities") or {})
    if missing_capabilities:
        return (
            "INCOMPATIBLE",
            "GLOBAL_BUNDLE_INCOMPATIBLE",
            f"Selected global bundle is missing required capabilities: {', '.join(missing_capabilities)}.",
        )
    missing_files = _find_missing_required_files(global_bundle_root)
    if missing_files:
        return (
            "INCOMPATIBLE",
            "GLOBAL_BUNDLE_INCOMPATIBLE",
            f"Selected global bundle is missing required files: {', '.join(missing_files)}.",
        )
    return ("READY", "PAYLOAD_BUNDLE_READY", "Selected global bundle is available.")


def _normalize_workspace_stub_contract(*, current_manifest: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    normalized = dict(current_manifest)
    normalized["schema_version"] = _normalize_stub_schema_version(normalized.get("schema_version"))
    normalized["stub_version"] = _normalize_stub_version(normalized.get("stub_version"))
    normalized["locator_mode"] = _normalize_locator_mode(normalized.get("locator_mode"))
    normalized["bundle_version"] = _normalize_optional_bundle_version(normalized.get("bundle_version"), field_name="bundle_version")
    # Handle sopify.json field mapping: "capabilities" (list) → "required_capabilities"
    raw_capabilities = normalized.get("required_capabilities")
    if raw_capabilities is None:
        sopify_json_caps = normalized.get("capabilities")
        if isinstance(sopify_json_caps, (list, tuple)):
            raw_capabilities = sopify_json_caps
    normalized["required_capabilities"] = _normalize_required_capabilities(raw_capabilities)
    normalized["ignore_mode"] = _normalize_ignore_mode(normalized.get("ignore_mode"), workspace_root=workspace_root)
    normalized["written_by_host"] = bool(normalized.get("written_by_host", False))
    return normalized


def _resolve_selected_payload_bundle(
    *,
    payload_root: Path,
    payload_manifest: dict[str, Any],
    current_manifest: dict[str, Any],
) -> tuple[Path | None, Path | None, dict[str, Any], str | None, str | None]:
    requested_version = _coerce_workspace_bundle_version(current_manifest.get("bundle_version"))
    try:
        bundle_manifest_path = _resolve_payload_bundle_manifest_path(
            payload_root=payload_root,
            payload_manifest=payload_manifest,
            bundle_version=requested_version,
        )
    except ValueError as exc:
        return (None, None, {}, "GLOBAL_INDEX_CORRUPTED", str(exc))
    bundle_root = bundle_manifest_path.parent
    if not bundle_manifest_path.is_file():
        message = _stale_stub_diagnostic(
            requested_version=requested_version,
            payload_manifest=payload_manifest,
            payload_root=payload_root,
            bundle_manifest_path=bundle_manifest_path,
        )
        return (
            bundle_root,
            bundle_manifest_path,
            {},
            "GLOBAL_BUNDLE_MISSING",
            message,
        )
    bundle_manifest = _read_json(bundle_manifest_path)
    if not bundle_manifest:
        return (
            bundle_root,
            bundle_manifest_path,
            {},
            "GLOBAL_BUNDLE_INCOMPATIBLE",
            f"Selected global bundle manifest is unreadable: {bundle_manifest_path}",
        )
    return (bundle_root, bundle_manifest_path, bundle_manifest, None, None)


def _stale_stub_diagnostic(
    *,
    requested_version: str | None,
    payload_manifest: dict[str, Any],
    payload_root: Path,
    bundle_manifest_path: Path,
) -> str:
    """Build a diagnostic message distinguishing stale stub from truly missing bundle."""
    active_version = _legacy_payload_bundle_version(payload_manifest)
    if requested_version and active_version and requested_version != active_version:
        return (
            f"Workspace stub requests bundle version {requested_version}, "
            f"but the active version is {active_version} "
            f"(payload_root: {payload_root}). "
            f"The workspace stub is stale. "
            f"Reinstall for this workspace or update .sopify-skills/sopify.json."
        )
    return f"Selected global bundle is missing: {bundle_manifest_path} (payload_root: {payload_root})"


def _resolve_payload_bundle_manifest_path(
    *,
    payload_root: Path,
    payload_manifest: dict[str, Any],
    bundle_version: str | None,
) -> Path:
    bundles_dir = _resolve_payload_relative_path(payload_root, payload_manifest.get("bundles_dir"), field_name="bundles_dir")
    if bundles_dir is not None:
        if bundle_version is not None:
            return payload_root / bundles_dir / bundle_version / "manifest.json"
        active_version = _normalize_optional_bundle_version(payload_manifest.get("active_version"), field_name="active_version")
        if active_version is None:
            raise ValueError("Payload verification failed: active_version")
        return payload_root / bundles_dir / active_version / "manifest.json"
    if bundle_version is not None:
        legacy_version = _legacy_payload_bundle_version(payload_manifest)
        if legacy_version == bundle_version:
            return _legacy_bundle_manifest_path(payload_root, payload_manifest)
        return payload_root / "bundles" / bundle_version / "manifest.json"
    return _legacy_bundle_manifest_path(payload_root, payload_manifest)


def _legacy_payload_bundle_version(payload_manifest: dict[str, Any]) -> str | None:
    if "bundle_version" in payload_manifest:
        return _normalize_optional_bundle_version(payload_manifest.get("bundle_version"), field_name="bundle_version")
    if "active_version" in payload_manifest:
        return _normalize_optional_bundle_version(payload_manifest.get("active_version"), field_name="active_version")
    return None


def _legacy_bundle_manifest_path(payload_root: Path, payload_manifest: dict[str, Any]) -> Path:
    relative = _resolve_payload_relative_path(payload_root, payload_manifest.get("bundle_manifest"), field_name="bundle_manifest")
    if relative is not None:
        return payload_root / relative
    return payload_root / "bundle" / "manifest.json"


def _resolve_payload_relative_path(payload_root: Path, value: Any, *, field_name: str) -> Path | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Payload verification failed: {field_name}")
    resolved_root = payload_root.resolve()
    resolved_candidate = (resolved_root / candidate).resolve()
    try:
        return resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Payload verification failed: {field_name}") from exc


def _normalize_stub_schema_version(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("Workspace stub contract is invalid: schema_version is required.")
    return normalized


def _normalize_stub_version(value: Any) -> str:
    normalized = str(value or "1").strip()
    if not normalized:
        raise ValueError("Workspace stub contract is invalid: stub_version is required.")
    return normalized


def _normalize_locator_mode(value: Any) -> str:
    normalized = str(value or "global_first").strip() or "global_first"
    if normalized not in _WORKSPACE_STUB_LOCATOR_MODES:
        raise ValueError(f"Workspace stub contract is invalid: locator_mode={normalized!r}.")
    return normalized


def _normalize_optional_bundle_version(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"Payload verification failed: {field_name}" if field_name == "active_version" else f"Workspace stub contract is invalid: {field_name}.")
    if normalized == "latest" or not _EXACT_BUNDLE_VERSION_RE.match(normalized):
        raise ValueError(f"Payload verification failed: {field_name}" if field_name == "active_version" else f"Workspace stub contract is invalid: {field_name}.")
    return normalized


def _coerce_workspace_bundle_version(value: Any) -> str | None:
    try:
        return _normalize_optional_bundle_version(value, field_name="bundle_version")
    except ValueError:
        return None


def _normalize_required_capabilities(value: Any) -> list[str]:
    if value in (None, ""):
        return list(_WORKSPACE_STUB_REQUIRED_CAPABILITIES)
    if not isinstance(value, (list, tuple)):
        raise ValueError("Workspace stub contract is invalid: required_capabilities.")
    normalized: list[str] = []
    for item in value:
        capability = str(item or "").strip()
        if capability not in _WORKSPACE_STUB_REQUIRED_CAPABILITIES or capability in normalized:
            raise ValueError("Workspace stub contract is invalid: required_capabilities.")
        normalized.append(capability)
    return normalized or list(_WORKSPACE_STUB_REQUIRED_CAPABILITIES)


def _normalize_ignore_mode(value: Any, *, workspace_root: Path) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "exclude" if _resolve_git_dir(workspace_root) is not None else "noop"
    if normalized not in _WORKSPACE_STUB_IGNORE_MODES:
        raise ValueError("Workspace stub contract is invalid: ignore_mode.")
    return normalized


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


def _write_workspace_stub_overlay(
    *,
    bundle_root: Path,
    workspace_root: Path,
    bundle_manifest: dict[str, Any] | None = None,
    ignore_mode: str | None = None,
) -> None:
    sopify_json_dir = workspace_root / _SOPIFY_SKILLS_DIR
    sopify_json_path = sopify_json_dir / _SOPIFY_JSON_FILENAME
    source_payload = _read_json(sopify_json_path)
    if not source_payload:
        legacy_manifest = bundle_root / "manifest.json"
        source_payload = _read_json(legacy_manifest)
    if not source_payload:
        source_payload = dict(bundle_manifest or {})
    if not source_payload:
        raise ValueError(f"Workspace bootstrap produced an unreadable manifest for: {workspace_root}")
    sopify_json_payload = {
        "schema_version": str(source_payload.get("schema_version") or "1"),
        "stub_version": "1",
        "workspace_kind": "deep" if (workspace_root / _SOPIFY_SKILLS_DIR / "blueprint").is_dir() else "external",
        "bundle_version": _string_or_none(source_payload.get("bundle_version")),
        "locator_mode": "global_first",
        "capabilities": list(_WORKSPACE_STUB_REQUIRED_CAPABILITIES),
        "ignore_mode": ignore_mode or _default_ignore_mode(workspace_root),
        "written_by_host": True,
    }
    sopify_json_dir.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=sopify_json_dir, encoding="utf-8") as handle:
        json.dump(sopify_json_payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(sopify_json_path)


def _default_ignore_mode(workspace_root: Path) -> str:
    if _resolve_git_dir(workspace_root) is not None:
        return "exclude"
    return "noop"


def _resolve_workspace_ignore_mode(
    *,
    workspace_root: Path,
    current_ignore_mode: str,
    request_text: str,
    authorization_mode: str,
) -> str:
    if _resolve_git_dir(workspace_root) is None:
        return "noop"
    if authorization_mode == "explicit_confirm":
        return "gitignore" if _COMMIT_LOCK_PATTERN.search(str(request_text or "").strip()) else "exclude"
    return current_ignore_mode or "exclude"


def _sync_workspace_ignore_policy(
    *,
    workspace_root: Path,
    current_ignore_mode: str,
    desired_ignore_mode: str,
) -> bool:
    changed = False
    current_target = _resolve_ignore_target(workspace_root=workspace_root, ignore_mode=current_ignore_mode)
    desired_target = _resolve_ignore_target(workspace_root=workspace_root, ignore_mode=desired_ignore_mode)
    if current_target is not None and current_target != desired_target:
        changed = _remove_managed_ignore_block(current_target) or changed
    if desired_target is not None:
        changed = _write_managed_ignore_block(desired_target) or changed
    return changed


def _resolve_ignore_target(*, workspace_root: Path, ignore_mode: str) -> Path | None:
    if ignore_mode == "exclude":
        git_dir = _resolve_git_dir(workspace_root)
        if git_dir is None:
            return None
        return git_dir / "info" / "exclude"
    if ignore_mode == "gitignore":
        return workspace_root / ".gitignore"
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
    raw_value = first_line[len(prefix) :].strip()
    if not raw_value:
        return None
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = (workspace_root / candidate).resolve()
    return candidate


def _nearest_existing_path(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return candidate


def _writable_probe_path(path: Path) -> Path:
    candidate = _nearest_existing_path(path)
    if candidate.is_dir():
        return candidate
    return candidate.parent


def _render_managed_ignore_block() -> str:
    return "\n".join((_SOPIFY_MANAGED_IGNORE_BEGIN, *_SOPIFY_MANAGED_IGNORE_ENTRIES, _SOPIFY_MANAGED_IGNORE_END))


def _write_managed_ignore_block(path: Path) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = _render_managed_ignore_block()
    if _SOPIFY_MANAGED_IGNORE_BEGIN in existing and _SOPIFY_MANAGED_IGNORE_END in existing:
        new_content = re.sub(
            rf"{re.escape(_SOPIFY_MANAGED_IGNORE_BEGIN)}.*?{re.escape(_SOPIFY_MANAGED_IGNORE_END)}",
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


def _remove_managed_ignore_block(path: Path) -> bool:
    if not path.exists():
        return False
    existing = path.read_text(encoding="utf-8")
    if _SOPIFY_MANAGED_IGNORE_BEGIN not in existing or _SOPIFY_MANAGED_IGNORE_END not in existing:
        return False
    new_content = re.sub(
        rf"(?:\n)?{re.escape(_SOPIFY_MANAGED_IGNORE_BEGIN)}.*?{re.escape(_SOPIFY_MANAGED_IGNORE_END)}(?:\n)?",
        "\n",
        existing,
        count=1,
        flags=re.DOTALL,
    )
    normalized = _normalize_ignore_file_content(new_content)
    if path.name == ".gitignore" and not normalized:
        path.unlink()
        return True
    return _write_text_if_changed(path, _ensure_trailing_newline(normalized) if normalized else "")


def _normalize_ignore_file_content(content: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", content).strip("\n")


def _ensure_trailing_newline(content: str) -> str:
    if not content:
        return ""
    return f"{content.rstrip()}\n"


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


# ── Workspace-scope instruction managed block helpers ─────────────────────


def _read_instruction_resource(payload_root: Path, host_name: str, filename: str) -> str | None:
    """Read a pre-distributed instruction resource file for a workspace-scope host."""
    resource_path = payload_root / _INSTRUCTION_RESOURCES_DIR / host_name / filename
    if not resource_path.is_file():
        return None
    return resource_path.read_text(encoding="utf-8")


def _write_managed_instruction_block(path: Path, content: str) -> bool:
    """Upsert a managed instruction block into a Markdown file."""
    block = "\n".join((_SOPIFY_INSTRUCTION_BLOCK_BEGIN, content.strip(), _SOPIFY_INSTRUCTION_BLOCK_END))
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _SOPIFY_INSTRUCTION_BLOCK_BEGIN in existing and _SOPIFY_INSTRUCTION_BLOCK_END in existing:
        new_content = re.sub(
            rf"{re.escape(_SOPIFY_INSTRUCTION_BLOCK_BEGIN)}.*?{re.escape(_SOPIFY_INSTRUCTION_BLOCK_END)}",
            lambda _: block,
            existing,
            count=1,
            flags=re.DOTALL,
        )
    else:
        base = existing.rstrip("\n")
        separator = "\n\n" if base else ""
        new_content = f"{base}{separator}{block}"
    return _write_text_if_changed(path, _ensure_trailing_newline(new_content))


def _remove_managed_instruction_block(path: Path) -> bool:
    """Remove the managed instruction block from a Markdown file."""
    if not path.exists():
        return False
    existing = path.read_text(encoding="utf-8")
    if _SOPIFY_INSTRUCTION_BLOCK_BEGIN not in existing or _SOPIFY_INSTRUCTION_BLOCK_END not in existing:
        return False
    new_content = re.sub(
        rf"(?:\n)?{re.escape(_SOPIFY_INSTRUCTION_BLOCK_BEGIN)}.*?{re.escape(_SOPIFY_INSTRUCTION_BLOCK_END)}(?:\n)?",
        "\n",
        existing,
        count=1,
        flags=re.DOTALL,
    )
    normalized = _normalize_ignore_file_content(new_content)
    if not normalized:
        path.unlink()
        return True
    return _write_text_if_changed(path, _ensure_trailing_newline(normalized))


def _sync_workspace_instruction_assets(*, host_id: str | None, workspace_root: Path, payload_root: Path) -> bool:
    """Sync instruction files for workspace-scope hosts from payload into the workspace.

    Reads resource manifest (written by payload.py) to discover target path.
    This file is self-contained and does not import installer modules.
    """
    if not host_id:
        return False
    manifest_path = payload_root / _INSTRUCTION_RESOURCES_DIR / host_id / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(manifest, dict):
        return False
    dest_dir = manifest.get("destination_dirname", "")
    header_file = manifest.get("header_filename", "")
    if not dest_dir or not header_file or not isinstance(dest_dir, str) or not isinstance(header_file, str):
        return False
    # Path safety: reject absolute paths or traversal
    if os.path.isabs(dest_dir) or ".." in Path(dest_dir).parts:
        return False
    if os.path.isabs(header_file) or ".." in Path(header_file).parts:
        return False
    target_path = (workspace_root / dest_dir / header_file).resolve()
    if not str(target_path).startswith(str(workspace_root.resolve()) + os.sep) and target_path != workspace_root.resolve():
        return False
    full = _read_instruction_resource(payload_root, host_id, "full.md")
    if full is None:
        return False
    return _write_managed_instruction_block(target_path, full)


def _confirm_bootstrap_message(
    *,
    activation_root: Path,
    root_resolution_source: str,
    fallback_reason: str,
) -> str:
    parts = [
        "Current directory is not a Git repository.",
        "Continuing will not add ignore rules automatically.",
        f"Target root: {activation_root}.",
        f"Root resolution: {root_resolution_source or 'cwd'}.",
    ]
    if fallback_reason:
        parts.append(f"Fallback reason: {fallback_reason}.")
    parts.append("Run `~go init` to confirm, or initialize Git and retry.")
    return " ".join(parts)


def _success_message(
    *,
    action: str,
    activation_root: Path,
    ignore_mode: str,
) -> str:
    if ignore_mode == "noop":
        return (
            f"Sopify is enabled at {activation_root}. "
            "Current directory is not a Git repository, so ignore rules remain manual."
        )
    if action == "skipped":
        return "Sopify is enabled for this project and points to the selected global bundle."
    ignore_target = _resolve_ignore_target(workspace_root=activation_root, ignore_mode=ignore_mode)
    return f"Sopify is enabled at {activation_root}. Managed ignore rules are synced via {ignore_target}."


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
    ignore_mode: str = "",
    extra_evidence: tuple[str, ...] = (),
    expose_activation_root: bool = True,
    expose_ignore_mode: bool = True,
) -> dict[str, Any]:
    target_root = activation_root or workspace_root
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
    if expose_activation_root and activation_root is not None:
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
    effective_ignore_mode = ignore_mode if expose_ignore_mode else ""
    if effective_ignore_mode:
        payload["ignore_mode"] = effective_ignore_mode
        ignore_target = _resolve_ignore_target(workspace_root=target_root, ignore_mode=effective_ignore_mode)
        if ignore_target is not None:
            payload["ignore_target"] = str(ignore_target)
    evidence = _result_evidence(
        workspace_root=target_root,
        ignore_mode=effective_ignore_mode,
        root_resolution_source=root_resolution_source,
        fallback_reason=fallback_reason,
        extra_evidence=extra_evidence,
    )
    if evidence:
        payload["evidence"] = evidence
    return _annotate_outcome_payload(payload, reason_code=reason_code, message_hint=message)


def _result_evidence(
    *,
    workspace_root: Path,
    ignore_mode: str,
    root_resolution_source: str,
    fallback_reason: str,
    extra_evidence: tuple[str, ...],
) -> list[str]:
    evidence: list[str] = [str(item) for item in extra_evidence if str(item or "").strip()]
    evidence.append(f"workspace_kind={'git' if _resolve_git_dir(workspace_root) is not None else 'non_git'}")
    if root_resolution_source == "ancestor_marker":
        evidence.append(DIAGNOSTIC_ROOT_REUSE_ANCESTOR_MARKER)
    if fallback_reason == "invalid_ancestor_marker":
        evidence.append(DIAGNOSTIC_INVALID_ANCESTOR_MARKER)
    if ignore_mode == "noop" and _resolve_git_dir(workspace_root) is None:
        evidence.append(DIAGNOSTIC_NON_GIT_WORKSPACE)
        evidence.append("ignore_mode=noop")
    elif ignore_mode:
        evidence.append(f"ignore_mode={ignore_mode}")
        ignore_target = _resolve_ignore_target(workspace_root=workspace_root, ignore_mode=ignore_mode)
        if ignore_target is not None:
            evidence.append(f"manual_disable=remove .sopify-skills/sopify.json and the sopify-managed block from {ignore_target}")
    return evidence


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None
if __name__ == "__main__":
    raise SystemExit(main())
