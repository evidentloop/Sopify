"""Post-install validation helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess

from installer.hosts.base import HostAdapter
from installer.models import InstallError


def validate_host_install(adapter: HostAdapter, *, home_root: Path) -> tuple[Path, ...]:
    """Ensure the expected host-side files exist after installation."""
    expected_paths = adapter.expected_paths(home_root)
    missing = [path for path in expected_paths if not path.exists()]
    if missing:
        raise InstallError(f"Host install verification failed: {missing[0]}")
    return expected_paths


def validate_bundle_install(bundle_root: Path) -> tuple[Path, ...]:
    """Ensure the synced bundle contains the minimum required assets."""
    expected_paths = (
        bundle_root / "manifest.json",
        bundle_root / "runtime" / "__init__.py",
        bundle_root / "scripts" / "sopify_runtime.py",
        bundle_root / "scripts" / "check-runtime-smoke.sh",
        bundle_root / "tests" / "test_runtime.py",
    )
    missing = [path for path in expected_paths if not path.exists()]
    if missing:
        raise InstallError(f"Bundle verification failed: {missing[0]}")
    return expected_paths


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
