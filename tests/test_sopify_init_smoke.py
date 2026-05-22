# Test classification: smoke
"""Smoke tests for scripts/sopify_init.py (standalone workspace initializer).

Covers the end-to-end bootstrap chain added in P7 S5:
  - Fresh workspace init (with and without Copilot)
  - Idempotency (re-run produces no errors)
  - Output structure verification (sopify.json, .gitignore, instruction files)
  - CLI error handling
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "scripts" / "sopify_init.py"
BOOTSTRAP_SH = REPO_ROOT / "bootstrap.sh"


def _run_init(
    workspace: Path,
    *,
    extra_args: list[str] | None = None,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(INIT_SCRIPT), "init", "--workspace", str(workspace)]
    if extra_args:
        cmd.extend(extra_args)
    env = os.environ.copy()
    env["LANG"] = "en_US.UTF-8"
    if env_override:
        env.update(env_override)
    return subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)


class SopifyInitSmokeTests(unittest.TestCase):
    """End-to-end tests for sopify_init.py."""

    def test_fresh_workspace_creates_marker_and_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / ".git").mkdir()  # simulate git repo
            result = _run_init(workspace)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Sopify workspace ready", result.stdout)

            marker = workspace / ".sopify-skills" / "sopify.json"
            self.assertTrue(marker.exists(), "sopify.json should be created")
            data = json.loads(marker.read_text(encoding="utf-8"))
            self.assertIn("bundle_version", data)
            self.assertIn("capabilities", data)
            self.assertEqual(data["schema_version"], "1")
            self.assertEqual(data["workspace_kind"], "external")

            gitignore = workspace / ".gitignore"
            self.assertTrue(gitignore.exists(), ".gitignore should be created or updated")
            content = gitignore.read_text(encoding="utf-8")
            self.assertIn("# BEGIN sopify-managed", content)
            self.assertIn("# END sopify-managed", content)
            self.assertIn(".sopify-runtime/", content)

    def test_fresh_workspace_creates_copilot_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            result = _run_init(workspace)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            instructions = workspace / ".github" / "copilot-instructions.md"
            self.assertTrue(instructions.exists(), "copilot-instructions.md should be created")
            content = instructions.read_text(encoding="utf-8")
            self.assertIn("Sopify", content)

            owned = workspace / ".github" / "instructions" / "sopify.instructions.md"
            self.assertTrue(owned.exists(), "sopify.instructions.md should be created")
            owned_content = owned.read_text(encoding="utf-8")
            self.assertIn("applyTo", owned_content)

    def test_no_copilot_skips_instruction_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            result = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            self.assertFalse(
                (workspace / ".github" / "copilot-instructions.md").exists(),
                "--no-copilot should skip copilot-instructions.md",
            )
            self.assertFalse(
                (workspace / ".github" / "instructions" / "sopify.instructions.md").exists(),
                "--no-copilot should skip sopify.instructions.md",
            )

            marker = workspace / ".sopify-skills" / "sopify.json"
            self.assertTrue(marker.exists(), "sopify.json should still be created")

    def test_idempotent_reinit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / ".git").mkdir()  # simulate git repo

            r1 = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(r1.returncode, 0, msg=r1.stderr)
            marker = workspace / ".sopify-skills" / "sopify.json"
            data1 = json.loads(marker.read_text(encoding="utf-8"))

            r2 = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(r2.returncode, 0, msg=r2.stderr)
            data2 = json.loads(marker.read_text(encoding="utf-8"))

            self.assertEqual(data1["bundle_version"], data2["bundle_version"])
            self.assertEqual(data1["capabilities"], data2["capabilities"])

            gitignore = workspace / ".gitignore"
            content = gitignore.read_text(encoding="utf-8")
            begin_count = content.count("# BEGIN sopify-managed")
            self.assertEqual(begin_count, 1, "Managed block should not duplicate on re-run")

    def test_existing_gitignore_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / ".git").mkdir()  # simulate git repo
            gitignore = workspace / ".gitignore"
            gitignore.write_text("node_modules/\n.env\n", encoding="utf-8")

            result = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            content = gitignore.read_text(encoding="utf-8")
            self.assertIn("node_modules/", content)
            self.assertIn(".env", content)
            self.assertIn("# BEGIN sopify-managed", content)

    def test_non_git_workspace_skips_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            result = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertFalse(
                (workspace / ".gitignore").exists(),
                ".gitignore should not be created in non-git workspace",
            )
            self.assertTrue(
                (workspace / ".sopify-skills" / "sopify.json").exists(),
                "sopify.json should still be created",
            )

    def test_chinese_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            result = _run_init(
                workspace,
                extra_args=["--no-copilot", "--language", "zh-CN"],
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("工作区已就绪", result.stdout)

    def test_missing_command_shows_help(self) -> None:
        result = subprocess.run(
            [sys.executable, str(INIT_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)

    def test_no_logo_when_piped(self) -> None:
        """Logo should be suppressed when stdout is not a TTY (piped)."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            result = _run_init(workspace, extra_args=["--no-copilot"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertNotIn("███", result.stdout, "Logo should not appear in piped output")


class BootstrapShSmokeTests(unittest.TestCase):
    """Validate bootstrap.sh script structure (no network, syntax only)."""

    def test_bootstrap_sh_syntax_valid(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(BOOTSTRAP_SH)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_bootstrap_sh_has_required_markers(self) -> None:
        content = BOOTSTRAP_SH.read_text(encoding="utf-8")
        self.assertIn('SOURCE_CHANNEL="dev"', content)
        self.assertIn('SOURCE_REF="main"', content)
        self.assertIn("install.sh", content)
        self.assertIn("--target copilot", content)

    def test_bootstrap_sh_help_flag(self) -> None:
        result = subprocess.run(
            ["bash", str(BOOTSTRAP_SH), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("bootstrap.sh", result.stdout)
        self.assertIn("--workspace", result.stdout)


if __name__ == "__main__":
    unittest.main()
