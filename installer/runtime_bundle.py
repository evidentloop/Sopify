"""Helpers for syncing the Sopify runtime bundle into a workspace."""

from __future__ import annotations

import os
from pathlib import Path
import shutil

from installer.models import InstallError
from runtime.manifest import write_bundle_manifest

DEFAULT_BUNDLE_DIRNAME = ".sopify-runtime"

_DIRECTORY_ASSETS = ("runtime", "sopify_contracts", "canonical_writer")
_SCRIPT_ASSETS = ("sopify_runtime.py", "runtime_gate.py", "check-runtime-smoke.sh")
_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def sync_runtime_bundle(repo_root: Path, workspace_root: Path, *, bundle_dirname: str = DEFAULT_BUNDLE_DIRNAME) -> Path:
    """Sync the runtime bundle into the target workspace without shelling out."""
    resolved_repo_root = repo_root.resolve()
    resolved_workspace_root = workspace_root.resolve()
    if not resolved_workspace_root.is_dir():
        raise InstallError(f"Target root does not exist: {workspace_root}")

    bundle_path = Path(bundle_dirname)
    bundle_root = bundle_path if bundle_path.is_absolute() else resolved_workspace_root / bundle_path

    required_sources = (
        *(resolved_repo_root / name for name in _DIRECTORY_ASSETS),
        *(resolved_repo_root / "scripts" / name for name in _SCRIPT_ASSETS),
        resolved_repo_root / "tests" / "test_bundle_smoke.py",
    )
    missing_sources = [path for path in required_sources if not path.exists()]
    if missing_sources:
        raise InstallError(f"Missing required source asset: {missing_sources[0]}")

    try:
        bundle_root.mkdir(parents=True, exist_ok=True)
        for name in _DIRECTORY_ASSETS:
            _replace_tree(resolved_repo_root / name, bundle_root / name)

        scripts_root = _reset_directory(bundle_root / "scripts")
        for script_name in _SCRIPT_ASSETS:
            destination = scripts_root / script_name
            shutil.copy2(resolved_repo_root / "scripts" / script_name, destination)
            os.chmod(destination, destination.stat().st_mode | 0o111)

        tests_root = _reset_directory(bundle_root / "tests")
        shutil.copy2(resolved_repo_root / "tests" / "test_bundle_smoke.py", tests_root / "test_runtime.py")

        write_bundle_manifest(bundle_root=bundle_root, source_root=resolved_repo_root)
    except OSError as exc:
        raise InstallError(f"Runtime bundle sync failed: {exc}") from exc

    required_paths = (
        bundle_root / "manifest.json",
        bundle_root / "sopify_contracts" / "__init__.py",
        bundle_root / "canonical_writer" / "__init__.py",
        bundle_root / "runtime" / "__init__.py",
        bundle_root / "scripts" / "sopify_runtime.py",
        bundle_root / "scripts" / "runtime_gate.py",
        bundle_root / "scripts" / "check-runtime-smoke.sh",
        bundle_root / "tests" / "test_runtime.py",
    )
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        raise InstallError(f"Runtime bundle sync incomplete: {missing[0]}")
    return bundle_root


def _replace_tree(source_root: Path, destination_root: Path) -> None:
    _remove_existing_path(destination_root)
    shutil.copytree(source_root, destination_root, ignore=_COPY_IGNORE)


def _reset_directory(path: Path) -> Path:
    _remove_existing_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _remove_existing_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()
