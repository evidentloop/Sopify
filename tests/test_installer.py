from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallerCliTests(unittest.TestCase):
    def _run_installer(
        self,
        *,
        target: str,
        home_root: Path,
        workspace_root: Path | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = ["bash", str(REPO_ROOT / "scripts" / "install-sopify.sh"), "--target", target]
        if workspace_root is not None:
            command.extend(["--workspace", str(workspace_root)])
        env = dict(os.environ)
        env["HOME"] = str(home_root)
        return subprocess.run(
            command,
            cwd=str(cwd or REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_installs_codex_cn_with_explicit_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            home_root = temp_root / "home"
            workspace_root = temp_root / "workspace"
            home_root.mkdir()
            workspace_root.mkdir()

            completed = self._run_installer(
                target="codex:zh-CN",
                home_root=home_root,
                workspace_root=workspace_root,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn("target: codex:zh-CN", completed.stdout)
            self.assertTrue((home_root / ".codex" / "AGENTS.md").exists())
            self.assertTrue((home_root / ".codex" / "skills" / "sopify" / "analyze" / "SKILL.md").exists())
            self.assertTrue((workspace_root / ".sopify-runtime" / "manifest.json").exists())
            self.assertTrue((workspace_root / ".sopify-runtime" / "scripts" / "sopify_runtime.py").exists())
            self.assertTrue((workspace_root / ".sopify-runtime" / "tests" / "test_runtime.py").exists())

    def test_installs_claude_en_using_current_directory_workspace_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            home_root = temp_root / "home"
            workspace_root = temp_root / "workspace"
            home_root.mkdir()
            workspace_root.mkdir()

            completed = self._run_installer(
                target="claude:en-US",
                home_root=home_root,
                cwd=workspace_root,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertIn(f"workspace: {workspace_root.resolve()}", completed.stdout)
            self.assertTrue((home_root / ".claude" / "CLAUDE.md").exists())
            self.assertTrue((home_root / ".claude" / "skills" / "sopify" / "design" / "SKILL.md").exists())
            self.assertTrue((workspace_root / ".sopify-runtime" / "runtime" / "__init__.py").exists())
            manifest = json.loads((workspace_root / ".sopify-runtime" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["default_entry"], "scripts/sopify_runtime.py")
            self.assertEqual(manifest["capabilities"]["bundle_role"], "control_plane")
            self.assertTrue(manifest["capabilities"]["writes_handoff_file"])
            self.assertIn("Runtime smoke check passed:", completed.stdout)

    def test_rejects_invalid_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            home_root = temp_root / "home"
            workspace_root = temp_root / "workspace"
            home_root.mkdir()
            workspace_root.mkdir()

            completed = self._run_installer(
                target="codex",
                home_root=home_root,
                workspace_root=workspace_root,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Target must use the format <host:lang>", completed.stderr)


if __name__ == "__main__":
    unittest.main()
