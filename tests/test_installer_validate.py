from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from installer.models import InstallError
from installer.validate import run_bundle_smoke_check


class BundleSmokeFailureDetailsTests(unittest.TestCase):
    def test_smoke_uses_explicit_payload_manifest_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle_root = root / "bundle"
            smoke_script = bundle_root / "scripts" / "check-runtime-smoke.sh"
            smoke_script.parent.mkdir(parents=True, exist_ok=True)
            smoke_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            payload_manifest = root / "payload-manifest.json"
            payload_manifest.write_text("{}", encoding="utf-8")

            passed = subprocess.CompletedProcess(
                args=["bash", str(smoke_script)],
                returncode=0,
                stdout="ok",
                stderr="",
            )
            with patch("installer.validate.subprocess.run", return_value=passed) as mock_run:
                output = run_bundle_smoke_check(bundle_root, payload_manifest_path=payload_manifest)

            self.assertEqual(output, "ok")
            env = mock_run.call_args.kwargs.get("env") or {}
            self.assertEqual(env.get("SOPIFY_PAYLOAD_MANIFEST"), str(payload_manifest))

    def test_failure_details_always_include_exit_status_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir)
            smoke_script = bundle_root / "scripts" / "check-runtime-smoke.sh"
            smoke_script.parent.mkdir(parents=True, exist_ok=True)
            smoke_script.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")

            failed = subprocess.CompletedProcess(
                args=["bash", str(smoke_script)],
                returncode=7,
                stdout="",
                stderr="Smoke check failed: missing plan directory",
            )

            with patch("installer.validate.subprocess.run", return_value=failed) as mock_run:
                with self.assertRaisesRegex(InstallError, "Bundle smoke check failed:") as exc:
                    run_bundle_smoke_check(bundle_root)

            message = str(exc.exception)
            self.assertIn("exit_status=7", message)
            self.assertIn("command=bash", message)
            self.assertIn(str(smoke_script), message)
            self.assertIn("stderr=Smoke check failed: missing plan directory", message)
            mock_run.assert_called_once()

    def test_empty_failure_details_fallback_to_xtrace_with_last_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir)
            smoke_script = bundle_root / "scripts" / "check-runtime-smoke.sh"
            smoke_script.parent.mkdir(parents=True, exist_ok=True)
            smoke_script.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")

            first_fail = subprocess.CompletedProcess(
                args=["bash", str(smoke_script)],
                returncode=1,
                stdout="",
                stderr="",
            )
            debug_fail = subprocess.CompletedProcess(
                args=["bash", "-x", str(smoke_script)],
                returncode=1,
                stdout="",
                stderr="+ python3 /tmp/runtime_entry.py --allow-direct-entry\n+ python3 /tmp/runtime_gate.py enter\n",
            )

            with patch("installer.validate.subprocess.run", side_effect=[first_fail, debug_fail]) as mock_run:
                with self.assertRaisesRegex(InstallError, "Bundle smoke check failed:") as exc:
                    run_bundle_smoke_check(bundle_root)

            message = str(exc.exception)
            self.assertIn("exit_status=1", message)
            self.assertIn("debug_exit_status=1", message)
            self.assertIn("debug_command=bash -x", message)
            self.assertIn("last_subcommand=python3 /tmp/runtime_gate.py enter", message)
            self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
