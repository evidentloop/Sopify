# Test classification: distribution
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_FOOTER_TIME_LABELS = ("Generated At:", "生成时间:")

from installer.bootstrap_workspace import (
    _REQUIRED_BUNDLE_FILES,
    _classify_workspace_bundle,
    _resolve_payload_bundle_manifest_path as _bootstrap_resolve_payload_bundle_manifest_path,
    _write_workspace_stub_overlay,
)
from installer.hosts.base import install_host_assets
from installer.hosts.claude import CLAUDE_ADAPTER
from installer.hosts.codex import CODEX_ADAPTER
from installer.models import InstallError
from installer.outcome_contract import annotate_outcome_payload
from installer.payload import (
    _REQUIRED_BUNDLE_CAPABILITIES,
    _install_versioned_runtime_bundle,
    _payload_is_current,
    install_global_payload,
)
from installer.validate import (
    validate_bundle_install,
    validate_host_install,
    validate_payload_manifests,
    validate_workspace_bundle_manifest,
    validate_workspace_stub_manifest,
)
from runtime.engine import run_runtime
from runtime.output import render_runtime_output
from scripts.install_sopify import run_install


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _create_incomplete_payload(*, home_root: Path, version: str) -> Path:
    payload_root = CODEX_ADAPTER.payload_root(home_root)
    bundle_root = payload_root / "bundles" / version

    _write_json(
        payload_root / "payload-manifest.json",
        {
            "schema_version": "1",
            "payload_version": version,
            "bundle_version": version,
            "active_version": version,
            "bundles_dir": "bundles",
            "bundle_manifest": f"bundles/{version}/manifest.json",
            "bundle_template_dir": f"bundles/{version}",
            "helper_entry": "helpers/bootstrap_workspace.py",
        },
    )
    _write_json(
        bundle_root / "manifest.json",
        {
            "schema_version": "1",
            "bundle_version": version,
            "capabilities": {
                "bundle_role": "control_plane",
                "manifest_first": True,
                "writes_handoff_file": True,
            },
        },
    )
    helper_path = payload_root / "helpers" / "bootstrap_workspace.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return payload_root


def _run_installed_bootstrap_helper(
    *,
    helper_path: Path,
    workspace_root: Path,
    request: str = "",
    activation_root: Path | None = None,
    host_id: str | None = None,
) -> dict[str, object]:
    command = [sys.executable, str(helper_path), "--workspace-root", str(workspace_root)]
    if request:
        command.extend(["--request", request])
    if activation_root is not None:
        command.extend(["--activation-root", str(activation_root)])
    if host_id is not None:
        command.extend(["--host-id", host_id])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.strip() or completed.stdout.strip() or "bootstrap helper failed")
    return json.loads(completed.stdout)


def _write_bundle_layout(
    bundle_root: Path,
    *,
    manifest: dict[str, object],
    missing_paths: tuple[Path, ...] = (),
) -> None:
    _write_json(bundle_root / "manifest.json", manifest)
    missing = set(missing_paths)
    for relative_path in _REQUIRED_BUNDLE_FILES:
        if relative_path == Path("manifest.json") or relative_path in missing:
            continue
        path = bundle_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def _load_module_without_repo_installer(module_path: Path, *, module_name: str):
    original_sys_path = list(sys.path)
    saved_modules = {
        name: sys.modules.pop(name)
        for name in tuple(sys.modules)
        if name == "installer" or name.startswith("installer.")
    }
    try:
        filtered_sys_path: list[str] = []
        for entry in original_sys_path:
            candidate = Path.cwd() if entry == "" else Path(entry)
            try:
                if candidate.resolve() == REPO_ROOT:
                    continue
            except OSError:
                pass
            filtered_sys_path.append(entry)
        sys.path[:] = filtered_sys_path
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise AssertionError(f"Failed to load module spec: {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = original_sys_path
        for name in tuple(sys.modules):
            if name == "installer" or name.startswith("installer."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)


class PayloadInstallTests(unittest.TestCase):
    def test_payload_is_current_rejects_incomplete_bundle_even_when_versions_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")

            self.assertFalse(_payload_is_current(payload_root, "2026-02-13"))

    def test_payload_is_current_rejects_versioned_layout_without_active_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "bundles_dir": "bundles",
                    "bundle_manifest": "bundles/2026-02-13/manifest.json",
                    "bundle_template_dir": "bundles/2026-02-13",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )

            self.assertFalse(_payload_is_current(payload_root, "2026-02-13"))

    def test_payload_is_current_returns_false_for_legacy_layout_with_invalid_payload_bundle_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            CODEX_ADAPTER.destination_root(home_root).mkdir(parents=True, exist_ok=True)
            install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)

            payload_root = CODEX_ADAPTER.payload_root(home_root)
            payload_manifest_path = payload_root / "payload-manifest.json"
            payload_manifest = json.loads(payload_manifest_path.read_text(encoding="utf-8"))
            active_version = payload_manifest["active_version"]
            shutil.copytree(payload_root / "bundles" / active_version, payload_root / "bundle")
            payload_manifest.pop("bundles_dir", None)
            payload_manifest.pop("active_version", None)
            payload_manifest["bundle_manifest"] = "bundle/manifest.json"
            payload_manifest["bundle_template_dir"] = "bundle"
            payload_manifest["bundle_version"] = "latest"
            payload_manifest_path.write_text(json.dumps(payload_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            self.assertFalse(_payload_is_current(payload_root, active_version))

            result = install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)

            self.assertEqual(result.action, "updated")

    def test_install_global_payload_updates_incomplete_existing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")

            result = install_global_payload(
                CODEX_ADAPTER,
                repo_root=REPO_ROOT,
                home_root=home_root,
            )

            self.assertEqual(result.action, "updated")
            self.assertEqual(result.root, payload_root)
            payload_manifest = json.loads((payload_root / "payload-manifest.json").read_text(encoding="utf-8"))
            bundle_root = payload_root / "bundles" / payload_manifest["active_version"]
            self.assertTrue((bundle_root / "scripts" / "preferences_preload_runtime.py").exists())
            self.assertTrue((bundle_root / "scripts" / "runtime_gate.py").exists())
            self.assertEqual(payload_manifest["bundle_manifest"], f"bundles/{payload_manifest['active_version']}/manifest.json")
            self.assertEqual(payload_manifest["dependency_model"]["mode"], "stdlib_only")
            self.assertTrue(payload_manifest["minimum_workspace_manifest"]["required_capabilities"]["runtime_gate"])
            self.assertTrue(payload_manifest["minimum_workspace_manifest"]["required_capabilities"]["runtime_entry_guard"])

    def test_install_versioned_runtime_bundle_rejects_invalid_manifest_bundle_version_before_rename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host_root = Path(temp_dir)
            bundle_root = host_root / "sopify" / "bundles" / "2026-02-13"
            bundle_root.mkdir(parents=True, exist_ok=True)
            _write_json(
                bundle_root / "manifest.json",
                {
                    "schema_version": "1",
                    "bundle_version": "../escape",
                },
            )

            with patch("installer.payload.sync_runtime_bundle", return_value=bundle_root):
                with self.assertRaisesRegex(InstallError, "bundle_version"):
                    _install_versioned_runtime_bundle(
                        repo_root=REPO_ROOT,
                        host_root=host_root,
                        desired_bundle_version="2026-02-13",
                    )

            self.assertTrue(bundle_root.exists())
            self.assertFalse((host_root / "sopify" / "escape").exists())

    def test_install_versioned_runtime_bundle_rejects_invalid_desired_bundle_version_before_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host_root = Path(temp_dir)

            with patch("installer.payload.sync_runtime_bundle") as sync_runtime_bundle:
                with self.assertRaisesRegex(InstallError, "bundle_version"):
                    _install_versioned_runtime_bundle(
                        repo_root=REPO_ROOT,
                        host_root=host_root,
                        desired_bundle_version="../escape",
                    )

            sync_runtime_bundle.assert_not_called()


class WorkspaceBootstrapCompatibilityTests(unittest.TestCase):
    def test_same_version_bundle_missing_required_bridge_file_is_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "bundle_version": "2026-02-13",
                "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
            }
            _write_json(current_manifest_path, current_manifest)
            global_bundle_root = workspace_root / "payload-bundles" / "2026-02-13"
            _write_bundle_layout(
                global_bundle_root,
                manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            for relative_path in _REQUIRED_BUNDLE_FILES:
                if relative_path == Path("runtime") / "gate.py":
                    continue  # intentionally skip to create incomplete workspace bundle
                path = bundle_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=global_bundle_root,
            )

            self.assertEqual(state, "READY")
            self.assertEqual(reason_code, "STUB_SELECTED")
            self.assertIn("selected global bundle", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_same_version_bundle_missing_required_capability_is_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "bundle_version": "2026-02-13",
                "capabilities": {
                    "bundle_role": "control_plane",
                    "manifest_first": True,
                    "writes_handoff_file": True,
                    "clarification_bridge": True,
                },
            }
            _write_json(current_manifest_path, current_manifest)
            global_bundle_root = workspace_root / "payload-bundles" / "2026-02-13"
            _write_bundle_layout(
                global_bundle_root,
                manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            for relative_path in _REQUIRED_BUNDLE_FILES:
                path = bundle_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=global_bundle_root,
            )

            self.assertEqual(state, "READY")
            self.assertEqual(reason_code, "STUB_SELECTED")
            self.assertIn("selected global bundle", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_stub_only_workspace_is_ready_when_stub_and_selected_global_bundle_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "stub_version": "1",
                "bundle_version": "2026-02-13",
                "locator_mode": "global_first",
                "required_capabilities": ["runtime_gate"],
                "ignore_mode": "noop",
                "written_by_host": True,
            }
            _write_json(current_manifest_path, current_manifest)
            global_bundle_root = workspace_root / "payload-bundles" / "2026-02-13"
            _write_bundle_layout(
                global_bundle_root,
                manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={"schema_version": "1", "bundle_version": "2026-02-13", "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES)},
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=global_bundle_root,
            )

            self.assertEqual(state, "READY")
            self.assertEqual(reason_code, "STUB_SELECTED")
            self.assertIn("selected global bundle", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_global_only_workspace_does_not_fallback_when_selected_global_bundle_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "stub_version": "1",
                "bundle_version": "2026-02-13",
                "locator_mode": "global_only",
                "required_capabilities": ["runtime_gate"],
                "ignore_mode": "noop",
                "written_by_host": True,
            }
            _write_json(current_manifest_path, current_manifest)

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=None,
                global_reason_code="GLOBAL_BUNDLE_MISSING",
                global_message="Selected global bundle is missing.",
            )

            self.assertEqual(state, "INCOMPATIBLE")
            self.assertEqual(reason_code, "GLOBAL_BUNDLE_MISSING")
            self.assertIn("missing", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_global_first_workspace_without_legacy_fallback_does_not_fallback_when_selected_global_bundle_is_incompatible(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "stub_version": "1",
                "bundle_version": "2026-02-13",
                "locator_mode": "global_first",
                "legacy_fallback": False,
                "required_capabilities": ["runtime_gate"],
                "ignore_mode": "noop",
                "written_by_host": True,
            }
            _write_json(current_manifest_path, current_manifest)

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=None,
                global_reason_code="GLOBAL_BUNDLE_INCOMPATIBLE",
                global_message="Selected global bundle is incompatible.",
            )

            self.assertEqual(state, "INCOMPATIBLE")
            self.assertEqual(reason_code, "GLOBAL_BUNDLE_INCOMPATIBLE")
            self.assertIn("incompatible", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_global_first_workspace_with_legacy_fallback_returns_ready_when_legacy_runtime_is_complete_and_global_bundle_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "stub_version": "1",
                "bundle_version": "2026-02-13",
                "locator_mode": "global_first",
                "legacy_fallback": True,
                "required_capabilities": ["runtime_gate"],
                "ignore_mode": "noop",
                "written_by_host": True,
                "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
            }
            _write_json(current_manifest_path, current_manifest)
            for relative_path in _REQUIRED_BUNDLE_FILES:
                if relative_path == Path("manifest.json"):
                    continue
                path = bundle_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=None,
                global_reason_code="GLOBAL_BUNDLE_MISSING",
                global_message="Selected global bundle is missing.",
            )

            self.assertEqual(state, "READY")
            self.assertEqual(reason_code, "LEGACY_FALLBACK_SELECTED")
            self.assertIn("legacy", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_global_first_workspace_with_legacy_fallback_fail_closes_when_legacy_runtime_is_incomplete_and_global_bundle_is_incompatible(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            current_manifest_path = bundle_root / "manifest.json"
            current_manifest = {
                "schema_version": "1",
                "stub_version": "1",
                "bundle_version": "2026-02-13",
                "locator_mode": "global_first",
                "legacy_fallback": True,
                "required_capabilities": ["runtime_gate"],
                "ignore_mode": "noop",
                "written_by_host": True,
                "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
            }
            _write_json(current_manifest_path, current_manifest)
            for relative_path in _REQUIRED_BUNDLE_FILES:
                if relative_path in {Path("manifest.json"), Path("scripts") / "runtime_gate.py"}:
                    continue
                path = bundle_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            state, reason_code, message, from_version = _classify_workspace_bundle(
                current_manifest=current_manifest,
                payload_manifest={
                    "minimum_workspace_manifest": {
                        "schema_version": "1",
                        "required_capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    }
                },
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
                current_manifest_path=current_manifest_path,
                bundle_root=bundle_root,
                global_bundle_root=None,
                global_reason_code="GLOBAL_BUNDLE_INCOMPATIBLE",
                global_message="Selected global bundle is incompatible.",
            )

            self.assertEqual(state, "INCOMPATIBLE")
            self.assertEqual(reason_code, "GLOBAL_BUNDLE_INCOMPATIBLE")
            self.assertIn("incompatible", message)
            self.assertEqual(from_version, "2026-02-13")

    def test_validate_bundle_install_requires_runtime_bridge_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)

            for relative_path in _REQUIRED_BUNDLE_FILES:
                path = bundle_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            # Remove a kernel module to verify bundle validation catches it.
            missing_runtime_module = bundle_root / "runtime" / "gate.py"
            missing_runtime_module.unlink()

            with self.assertRaisesRegex(Exception, "gate.py"):
                validate_bundle_install(bundle_root)

    def test_validate_workspace_bundle_manifest_only_requires_manifest_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            resolved_path, manifest = validate_workspace_bundle_manifest(bundle_root)
            self.assertEqual(resolved_path, manifest_path)
            self.assertEqual(manifest["schema_version"], "1")

    def test_validate_workspace_stub_manifest_applies_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            resolved_path, manifest = validate_workspace_stub_manifest(bundle_root)
            self.assertEqual(resolved_path, manifest_path)
            self.assertEqual(manifest["locator_mode"], "global_first")
            self.assertEqual(manifest["required_capabilities"], ["runtime_gate"])
            self.assertEqual(manifest["ignore_mode"], "noop")
            self.assertFalse(manifest["legacy_fallback"])

    def test_write_workspace_stub_overlay_writes_frozen_stub_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            _write_workspace_stub_overlay(bundle_root=bundle_root, workspace_root=workspace_root)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "1")
            self.assertEqual(manifest["stub_version"], "1")
            self.assertEqual(manifest["bundle_version"], "2026-02-13")
            self.assertEqual(manifest["required_capabilities"], ["runtime_gate"])
            self.assertEqual(manifest["locator_mode"], "global_first")
            self.assertFalse(manifest["legacy_fallback"])
            self.assertEqual(manifest["ignore_mode"], "noop")
            self.assertTrue(manifest["written_by_host"])

    def test_write_workspace_stub_overlay_materializes_stub_from_global_bundle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"

            _write_workspace_stub_overlay(
                bundle_root=bundle_root,
                workspace_root=workspace_root,
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                },
            )

            manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "1")
            self.assertEqual(manifest["stub_version"], "1")
            self.assertEqual(manifest["bundle_version"], "2026-02-13")
            self.assertEqual(manifest["required_capabilities"], ["runtime_gate"])
            self.assertEqual(manifest["locator_mode"], "global_first")
            self.assertEqual(manifest["ignore_mode"], "noop")
            self.assertTrue(manifest["written_by_host"])
            self.assertFalse((bundle_root / "scripts").exists())

    def test_write_workspace_stub_overlay_drops_bundle_only_contract_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"

            _write_workspace_stub_overlay(
                bundle_root=bundle_root,
                workspace_root=workspace_root,
                bundle_manifest={
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": dict(_REQUIRED_BUNDLE_CAPABILITIES),
                    "default_entry": "scripts/sopify_runtime.py",
                    "limits": {"runtime_gate_entry": "scripts/runtime_gate.py"},
                },
            )

            manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                set(manifest.keys()),
                {
                    "bundle_version",
                    "ignore_mode",
                    "legacy_fallback",
                    "locator_mode",
                    "required_capabilities",
                    "schema_version",
                    "stub_version",
                    "written_by_host",
                },
            )

    def test_validate_workspace_stub_manifest_rejects_invalid_bundle_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "bundle_version": "latest",
                    "locator_mode": "global_first",
                    "required_capabilities": ["runtime_gate"],
                },
            )

            with self.assertRaisesRegex(Exception, "bundle_version"):
                validate_workspace_stub_manifest(bundle_root)

    def test_validate_workspace_stub_manifest_treats_null_bundle_version_as_host_delegated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "stub_version": "1",
                    "bundle_version": None,
                    "required_capabilities": ["runtime_gate"],
                },
            )

            _resolved_path, manifest = validate_workspace_stub_manifest(bundle_root)
            self.assertIsNone(manifest["bundle_version"])
            self.assertEqual(manifest["locator_mode"], "global_first")

    def test_validate_workspace_stub_manifest_rejects_empty_string_bundle_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "stub_version": "1",
                    "bundle_version": "",
                    "required_capabilities": ["runtime_gate"],
                },
            )

            with self.assertRaisesRegex(Exception, "bundle_version"):
                validate_workspace_stub_manifest(bundle_root)

    def test_validate_workspace_stub_manifest_rejects_missing_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "stub_version": "1",
                    "bundle_version": "2026-02-13",
                    "required_capabilities": ["runtime_gate"],
                },
            )

            with self.assertRaisesRegex(Exception, "schema_version"):
                validate_workspace_stub_manifest(bundle_root)

    def test_validate_workspace_stub_manifest_rejects_global_only_legacy_fallback_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bundle_root = workspace_root / ".sopify-runtime"
            bundle_root.mkdir(parents=True, exist_ok=True)
            manifest_path = bundle_root / "manifest.json"
            _write_json(
                manifest_path,
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "locator_mode": "global_only",
                    "legacy_fallback": True,
                    "required_capabilities": ["runtime_gate"],
                },
            )

            with self.assertRaisesRegex(Exception, str(manifest_path)):
                validate_workspace_stub_manifest(bundle_root)


class WorkspaceBootstrapIgnorePolicyTests(unittest.TestCase):
    def test_installed_helper_writes_managed_block_to_git_exclude_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir) / "home"
            workspace_root = Path(temp_dir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            CODEX_ADAPTER.destination_root(home_root).mkdir(parents=True, exist_ok=True)
            exclude_path = workspace_root / ".git" / "info" / "exclude"
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            exclude_path.write_text("user-entry\n", encoding="utf-8")

            payload_phase = install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)
            helper_path = payload_phase.root / "helpers" / "bootstrap_workspace.py"

            result = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go plan 补 runtime gate 骨架",
            )

            self.assertEqual(result["action"], "bootstrapped")
            self.assertEqual(result["reason_code"], "STUB_SELECTED")
            self.assertEqual(result["ignore_mode"], "exclude")
            self.assertEqual(Path(result["ignore_target"]).resolve(), exclude_path.resolve())
            manifest = json.loads((workspace_root / ".sopify-runtime" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["ignore_mode"], "exclude")
            exclude_content = exclude_path.read_text(encoding="utf-8")
            self.assertIn("user-entry\n", exclude_content)
            self.assertIn("# BEGIN sopify-managed", exclude_content)
            self.assertIn(".sopify-runtime/", exclude_content)
            self.assertIn(".sopify-skills/state/", exclude_content)
            self.assertFalse((workspace_root / ".gitignore").exists())

    def test_installed_helper_keeps_commit_lock_sticky_until_explicit_go_init_switches_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir) / "home"
            workspace_root = Path(temp_dir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            CODEX_ADAPTER.destination_root(home_root).mkdir(parents=True, exist_ok=True)
            (workspace_root / ".git" / "info").mkdir(parents=True, exist_ok=True)

            payload_phase = install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)
            helper_path = payload_phase.root / "helpers" / "bootstrap_workspace.py"
            exclude_path = workspace_root / ".git" / "info" / "exclude"
            gitignore_path = workspace_root / ".gitignore"

            first = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go init commit-lock",
            )

            self.assertEqual(first["action"], "bootstrapped")
            self.assertEqual(first["ignore_mode"], "gitignore")
            self.assertEqual(Path(first["ignore_target"]).resolve(), gitignore_path.resolve())
            self.assertIn("# BEGIN sopify-managed", gitignore_path.read_text(encoding="utf-8"))
            self.assertFalse(exclude_path.exists())

            sticky = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go plan 继续开发",
            )

            self.assertEqual(sticky["action"], "skipped")
            self.assertEqual(sticky["ignore_mode"], "gitignore")
            manifest = json.loads((workspace_root / ".sopify-runtime" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["ignore_mode"], "gitignore")
            self.assertIn("# BEGIN sopify-managed", gitignore_path.read_text(encoding="utf-8"))

            switched = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go init",
            )

            self.assertEqual(switched["action"], "updated")
            self.assertEqual(switched["ignore_mode"], "exclude")
            self.assertEqual(Path(switched["ignore_target"]).resolve(), exclude_path.resolve())
            manifest = json.loads((workspace_root / ".sopify-runtime" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["ignore_mode"], "exclude")
            self.assertFalse(gitignore_path.exists())
            self.assertIn("# BEGIN sopify-managed", exclude_path.read_text(encoding="utf-8"))

    def test_installed_helper_repairs_missing_managed_block_for_ready_git_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir) / "home"
            workspace_root = Path(temp_dir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            CODEX_ADAPTER.destination_root(home_root).mkdir(parents=True, exist_ok=True)
            (workspace_root / ".git" / "info").mkdir(parents=True, exist_ok=True)

            payload_phase = install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)
            helper_path = payload_phase.root / "helpers" / "bootstrap_workspace.py"
            exclude_path = workspace_root / ".git" / "info" / "exclude"

            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go plan 初始化",
            )
            exclude_path.write_text("user-entry\n", encoding="utf-8")

            repaired = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go plan 继续开发",
            )

            self.assertEqual(repaired["action"], "updated")
            self.assertEqual(repaired["ignore_mode"], "exclude")
            exclude_content = exclude_path.read_text(encoding="utf-8")
            self.assertIn("user-entry\n", exclude_content)
            self.assertIn("# BEGIN sopify-managed", exclude_content)

    def test_validate_payload_manifests_returns_both_payload_and_bundle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")

            payload_manifest_path, payload_manifest, bundle_manifest_path, bundle_manifest = validate_payload_manifests(payload_root)
            self.assertEqual(payload_manifest_path, payload_root / "payload-manifest.json")
            self.assertEqual(bundle_manifest_path, payload_root / "bundles" / "2026-02-13" / "manifest.json")
            self.assertEqual(payload_manifest["payload_version"], "2026-02-13")
            self.assertEqual(bundle_manifest["bundle_version"], "2026-02-13")

    def test_validate_payload_manifests_supports_exact_bundle_version_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-14")
            _write_json(
                payload_root / "bundles" / "2026-02-13" / "manifest.json",
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": {
                        "bundle_role": "control_plane",
                        "manifest_first": True,
                        "writes_handoff_file": True,
                    },
                },
            )

            _payload_manifest_path, _payload_manifest, bundle_manifest_path, bundle_manifest = validate_payload_manifests(
                payload_root,
                bundle_version="2026-02-13",
            )

            self.assertEqual(bundle_manifest_path, payload_root / "bundles" / "2026-02-13" / "manifest.json")
            self.assertEqual(bundle_manifest["bundle_version"], "2026-02-13")

    def test_validate_payload_manifests_requires_active_version_for_host_delegated_versioned_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "bundles_dir": "bundles",
                    "bundle_manifest": "bundles/2026-02-13/manifest.json",
                    "bundle_template_dir": "bundles/2026-02-13",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )

            with self.assertRaisesRegex(InstallError, "active_version"):
                validate_payload_manifests(payload_root)

    def test_validate_payload_manifests_supports_exact_lookup_against_legacy_bundle_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = CODEX_ADAPTER.payload_root(home_root)
            legacy_bundle_root = payload_root / "bundle"
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "bundle_manifest": "bundle/manifest.json",
                    "bundle_template_dir": "bundle",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )
            _write_json(
                legacy_bundle_root / "manifest.json",
                {
                    "schema_version": "1",
                    "bundle_version": "2026-02-13",
                    "capabilities": {
                        "bundle_role": "control_plane",
                        "manifest_first": True,
                        "writes_handoff_file": True,
                    },
                },
            )
            helper_path = payload_root / "helpers" / "bootstrap_workspace.py"
            helper_path.parent.mkdir(parents=True, exist_ok=True)
            helper_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            _payload_manifest_path, _payload_manifest, bundle_manifest_path, bundle_manifest = validate_payload_manifests(
                payload_root,
                bundle_version="2026-02-13",
            )

            self.assertEqual(bundle_manifest_path, legacy_bundle_root / "manifest.json")
            self.assertEqual(bundle_manifest["bundle_version"], "2026-02-13")

    def test_bootstrap_resolver_supports_exact_lookup_against_legacy_bundle_layout_with_active_version_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = CODEX_ADAPTER.payload_root(home_root)

            resolved_path = _bootstrap_resolve_payload_bundle_manifest_path(
                payload_root=payload_root,
                payload_manifest={
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "active_version": "2026-02-13",
                    "bundle_manifest": "bundle/manifest.json",
                    "bundle_template_dir": "bundle",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
                bundle_version="2026-02-13",
            )

            self.assertEqual(resolved_path, payload_root / "bundle" / "manifest.json")

    def test_validate_payload_manifests_rejects_escaping_bundles_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "active_version": "2026-02-13",
                    "bundles_dir": "..",
                    "bundle_manifest": "bundles/2026-02-13/manifest.json",
                    "bundle_template_dir": "bundles/2026-02-13",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )

            with self.assertRaisesRegex(InstallError, "bundles_dir"):
                validate_payload_manifests(payload_root)

    def test_validate_payload_manifests_rejects_bundles_dir_with_parent_segments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "active_version": "2026-02-13",
                    "bundles_dir": "bundles/../bundles",
                    "bundle_manifest": "bundles/2026-02-13/manifest.json",
                    "bundle_template_dir": "bundles/2026-02-13",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )

            with self.assertRaisesRegex(InstallError, "bundles_dir"):
                validate_payload_manifests(payload_root)

    def test_validate_payload_manifests_rejects_escaping_legacy_bundle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            payload_root = _create_incomplete_payload(home_root=home_root, version="2026-02-13")
            _write_json(
                payload_root / "payload-manifest.json",
                {
                    "schema_version": "1",
                    "payload_version": "2026-02-13",
                    "bundle_version": "2026-02-13",
                    "bundle_manifest": "../outside/manifest.json",
                    "bundle_template_dir": "bundle",
                    "helper_entry": "helpers/bootstrap_workspace.py",
                },
            )

            with self.assertRaisesRegex(InstallError, "bundle_manifest"):
                validate_payload_manifests(payload_root)


class HostPromptContractTests(unittest.TestCase):
    def _assert_no_footer_time_labels(self, content: str) -> None:
        for label in _FOOTER_TIME_LABELS:
            self.assertNotIn(label, content)

    def _assert_footer_contract_block(
        self,
        content: str,
        *,
        next_line: str,
    ) -> None:
        self.assertIn(next_line, content)
        self._assert_no_footer_time_labels(content)

    def _assert_footer_contract_tail(
        self,
        content: str,
        *,
        next_prefix: str,
    ) -> None:
        lines = content.rstrip().splitlines()
        self.assertGreaterEqual(len(lines), 1)
        self.assertTrue(lines[-1].startswith(next_prefix), msg=content)
        self._assert_no_footer_time_labels(content)

    def _assert_rendered_footer_contract(
        self,
        rendered: str,
        *,
        next_prefix: str,
    ) -> None:
        lines = rendered.rstrip().splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[-2], "", msg=rendered)
        self.assertTrue(lines[-1].startswith(next_prefix), msg=rendered)
        self._assert_no_footer_time_labels(rendered)

    def _assert_installed_footer_contract(
        self,
        *,
        adapter,
        language_directory: str,
        next_template_line: str,
        footer_contract_line: str,
        runtime_language: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)

            install_host_assets(
                adapter,
                repo_root=REPO_ROOT,
                home_root=home_root,
                language_directory=language_directory,
            )
            validate_host_install(adapter, home_root=home_root)

            prompt_root = home_root / adapter.destination_dirname
            prompt = (prompt_root / adapter.header_filename).read_text(encoding="utf-8")
            self._assert_footer_contract_block(
                prompt,
                next_line=next_template_line,
            )
            self.assertIn(footer_contract_line, prompt)

            asset_paths = (
                Path("skills/sopify/analyze/assets/question-output.md"),
                Path("skills/sopify/analyze/assets/success-output.md"),
                Path("skills/sopify/design/assets/output-summary.md"),
                Path("skills/sopify/develop/assets/output-success.md"),
                Path("skills/sopify/develop/assets/output-quick-fix.md"),
                Path("skills/sopify/develop/assets/output-partial.md"),
            )
            for relative_path in asset_paths:
                content = (prompt_root / relative_path).read_text(encoding="utf-8")
                self._assert_footer_contract_tail(
                    content,
                    next_prefix="Next:",
                )

            workspace = home_root / "workspace"
            result = run_runtime("~go plan 补 runtime 骨架", workspace_root=workspace, user_home=home_root / "runtime-home")
            rendered = render_runtime_output(
                result,
                brand="demo-ai",
                language=runtime_language,
                title_color="none",
                use_color=False,
            )
            self._assert_rendered_footer_contract(
                rendered,
                next_prefix="Next:",
            )

    def test_codex_cn_prompt_install_keeps_workspace_preflight_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)

            install_host_assets(
                CODEX_ADAPTER,
                repo_root=REPO_ROOT,
                home_root=home_root,
                language_directory="CN",
            )
            validate_host_install(CODEX_ADAPTER, home_root=home_root)

            prompt = (home_root / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            # Gate-first obligation (§8.1)
            self.assertIn("runtime gate", prompt)
            self.assertIn("protocol.md §8.1", prompt)
            self.assertIn("allowed_response_mode", prompt)
            # Handoff-first obligation (§8.2)
            self.assertIn("current_handoff.json", prompt)
            self.assertIn("protocol.md §8.2", prompt)
            self.assertIn("required_host_action", prompt)
            # No self-routing / no truth-writing (§8.3)
            self.assertIn("protocol.md §8.3", prompt)
            # Host Integration Contract ref (§8)
            self.assertIn("protocol.md §8", prompt)
            # Runtime helper index ref (§8.4–8.5)
            self.assertIn("protocol.md §8.4", prompt)

    def test_codex_cn_installed_prompt_assets_keep_footer_contract(self) -> None:
        # Footer contract aligned: replay reference removed from source and assertion.
        self._assert_installed_footer_contract(
            adapter=CODEX_ADAPTER,
            language_directory="CN",
            next_template_line="Next: {下一步提示}",
            footer_contract_line="- footer 不展示生成时间；若需要机器可审计时间戳，内部摘要文件可继续使用 ISO 8601（可带时区）。",
            runtime_language="zh-CN",
        )

    def test_claude_en_prompt_install_keeps_workspace_preflight_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)

            install_host_assets(
                CLAUDE_ADAPTER,
                repo_root=REPO_ROOT,
                home_root=home_root,
                language_directory="EN",
            )
            validate_host_install(CLAUDE_ADAPTER, home_root=home_root)

            prompt = (home_root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            # Gate-first obligation (§8.1)
            self.assertIn("runtime gate", prompt)
            self.assertIn("protocol.md §8.1", prompt)
            self.assertIn("allowed_response_mode", prompt)
            # Handoff-first obligation (§8.2)
            self.assertIn("current_handoff.json", prompt)
            self.assertIn("protocol.md §8.2", prompt)
            self.assertIn("required_host_action", prompt)
            # No self-routing / no truth-writing (§8.3)
            self.assertIn("protocol.md §8.3", prompt)
            # Host Integration Contract ref (§8)
            self.assertIn("protocol.md §8", prompt)
            # Runtime helper index ref (§8.4–8.5)
            self.assertIn("protocol.md §8.4", prompt)

    def test_claude_en_installed_prompt_assets_keep_footer_contract(self) -> None:
        # Footer contract aligned: replay reference removed from source and assertion.
        self._assert_installed_footer_contract(
            adapter=CLAUDE_ADAPTER,
            language_directory="EN",
            next_template_line="Next: {Next step hint}",
            footer_contract_line="- the footer does not display generated time; if a machine-auditable timestamp is needed, internal summary files may keep ISO 8601 timestamps with timezone data.",
            runtime_language="en-US",
        )


class InstallRenderTests(unittest.TestCase):
    def test_run_install_rejects_retired_host_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_root = Path(temp_dir)
            retired_host = "tr" + "ae-cn"

            with self.assertRaisesRegex(InstallError, f"Unsupported host: {retired_host}"):
                run_install(
                    target_value=f"{retired_host}:zh-CN",
                    workspace_value=None,
                    repo_root=REPO_ROOT,
                    home_root=home_root,
                )

    def test_bootstrap_helper_fallback_keeps_outcome_contract_in_sync(self) -> None:
        standalone_module = _load_module_without_repo_installer(
            REPO_ROOT / "installer" / "bootstrap_workspace.py",
            module_name="bootstrap_workspace_fallback_test",
        )
        reason_codes = (
            "STUB_SELECTED",
            "STUB_INVALID",
            "GLOBAL_BUNDLE_MISSING",
            "GLOBAL_BUNDLE_INCOMPATIBLE",
            "GLOBAL_INDEX_CORRUPTED",
            "LEGACY_FALLBACK_SELECTED",
            "ROOT_CONFIRM_REQUIRED",
            "READONLY",
            "NON_INTERACTIVE",
            "CONFIRM_BOOTSTRAP_REQUIRED",
            "BRAKE_LAYER_BLOCKED",
            "FIRST_WRITE_NOT_AUTHORIZED",
            "COMMAND_NOT_BOOTSTRAP_AUTHORIZED",
            "UNKNOWN_REASON",
        )

        for reason_code in reason_codes:
            with self.subTest(reason_code=reason_code):
                expected = annotate_outcome_payload(
                    {"reason_code": reason_code},
                    reason_code=reason_code,
                    message_hint="retry",
                )
                actual = standalone_module._annotate_outcome_payload(
                    {"reason_code": reason_code},
                    reason_code=reason_code,
                    message_hint="retry",
                )

                self.assertEqual(actual.get("primary_code"), expected.get("primary_code"))
                self.assertEqual(actual.get("action_level"), expected.get("action_level"))
                self.assertEqual(actual.get("message_hint"), expected.get("message_hint"))


class CopilotInstructionSyncTests(unittest.TestCase):
    """Tests for Copilot instruction file sync during workspace bootstrap."""

    def _setup_workspace_with_payload(self, temp_dir: str) -> tuple[Path, Path, Path]:
        home_root = Path(temp_dir) / "home"
        workspace_root = Path(temp_dir) / "workspace"
        workspace_root.mkdir(parents=True, exist_ok=True)
        CODEX_ADAPTER.destination_root(home_root).mkdir(parents=True, exist_ok=True)
        (workspace_root / ".git" / "info").mkdir(parents=True, exist_ok=True)
        payload_phase = install_global_payload(CODEX_ADAPTER, repo_root=REPO_ROOT, home_root=home_root)
        helper_path = payload_phase.root / "helpers" / "bootstrap_workspace.py"
        return home_root, workspace_root, helper_path

    def test_copilot_host_creates_instruction_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)
            result = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="copilot",
            )
            self.assertEqual(result["action"], "bootstrapped")
            instructions_path = workspace_root / ".github" / "copilot-instructions.md"
            self.assertTrue(instructions_path.exists(), "copilot-instructions.md should be created")
            content = instructions_path.read_text(encoding="utf-8")
            self.assertIn("<!-- BEGIN SOPIFY MANAGED BLOCK -->", content)
            self.assertIn("<!-- END SOPIFY MANAGED BLOCK -->", content)
            self.assertIn("Sopify", content)

            owned_path = workspace_root / ".github" / "instructions" / "sopify.instructions.md"
            self.assertTrue(owned_path.exists(), "sopify.instructions.md should be created")
            owned_content = owned_path.read_text(encoding="utf-8")
            self.assertIn("applyTo:", owned_content)

    def test_codex_host_does_not_create_instruction_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)
            result = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="codex",
            )
            self.assertEqual(result["action"], "bootstrapped")
            self.assertFalse(
                (workspace_root / ".github" / "copilot-instructions.md").exists(),
                "Codex should not create copilot-instructions.md",
            )
            self.assertFalse(
                (workspace_root / ".github" / "instructions" / "sopify.instructions.md").exists(),
                "Codex should not create sopify.instructions.md",
            )

    def test_copilot_instruction_upserts_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)
            github_dir = workspace_root / ".github"
            github_dir.mkdir(parents=True, exist_ok=True)
            instructions_path = github_dir / "copilot-instructions.md"
            instructions_path.write_text("# My project rules\n\nDo not change tests.\n", encoding="utf-8")

            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="copilot",
            )

            content = instructions_path.read_text(encoding="utf-8")
            self.assertIn("# My project rules", content, "User content should be preserved")
            self.assertIn("Do not change tests.", content, "User content should be preserved")
            self.assertIn("<!-- BEGIN SOPIFY MANAGED BLOCK -->", content, "Managed block should be added")

    def test_copilot_instruction_replaces_existing_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)
            github_dir = workspace_root / ".github"
            github_dir.mkdir(parents=True, exist_ok=True)
            instructions_path = github_dir / "copilot-instructions.md"
            instructions_path.write_text(
                "# Rules\n\n"
                "<!-- BEGIN SOPIFY MANAGED BLOCK -->\nold content\n<!-- END SOPIFY MANAGED BLOCK -->\n",
                encoding="utf-8",
            )

            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="copilot",
            )

            content = instructions_path.read_text(encoding="utf-8")
            self.assertIn("# Rules", content)
            self.assertNotIn("old content", content, "Old managed block content should be replaced")
            self.assertIn("Sopify", content, "New managed block content should be present")

    def test_non_copilot_host_does_not_remove_existing_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)

            # First bootstrap with copilot to create instruction files
            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="copilot",
            )
            self.assertTrue((workspace_root / ".github" / "copilot-instructions.md").exists())

            # Second bootstrap with codex should not remove them
            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="codex",
            )
            self.assertTrue(
                (workspace_root / ".github" / "copilot-instructions.md").exists(),
                "Codex bootstrap should not remove Copilot instruction files",
            )
            self.assertTrue(
                (workspace_root / ".github" / "instructions" / "sopify.instructions.md").exists(),
                "Codex bootstrap should not remove owned instruction file",
            )

    def test_copilot_instruction_sync_on_ready_workspace(self) -> None:
        """Verify instruction sync works on the READY/NEWER_THAN_GLOBAL path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)

            # First bootstrap to create workspace
            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="codex",
            )
            self.assertFalse((workspace_root / ".github" / "copilot-instructions.md").exists())

            # Second bootstrap with copilot on already-ready workspace
            result = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="copilot",
            )
            self.assertIn(result["action"], {"updated", "skipped"})
            self.assertTrue(
                (workspace_root / ".github" / "copilot-instructions.md").exists(),
                "Copilot instruction files should be created on ready workspace",
            )

    def test_copilot_instruction_not_synced_without_authorization(self) -> None:
        """READY path: unauthorized request should NOT trigger instruction sync."""
        with tempfile.TemporaryDirectory() as temp_dir:
            _home, workspace_root, helper_path = self._setup_workspace_with_payload(temp_dir)

            # First bootstrap to create workspace (authorized)
            _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="~go",
                host_id="codex",
            )

            # Second bootstrap with copilot but unauthorized request
            result = _run_installed_bootstrap_helper(
                helper_path=helper_path,
                workspace_root=workspace_root,
                request="hello explain this code",
                host_id="copilot",
            )
            self.assertFalse(
                (workspace_root / ".github" / "copilot-instructions.md").exists(),
                "Unauthorized request should NOT create Copilot instruction files on READY workspace",
            )


if __name__ == "__main__":
    unittest.main()
