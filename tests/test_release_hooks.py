from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_script(relative_path: str, target_root: Path) -> Path:
    source = REPO_ROOT / relative_path
    target = target_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(0o755)
    return target


def _minimal_readme(version: str, *, english: bool) -> str:
    anchor = "#version-history" if english else "#版本历史"
    return textwrap.dedent(
        f"""\
        # {'Sopify Skills' if english else 'Sopify 技能'}

        [![Version](https://img.shields.io/badge/version-{version.replace('-', '--')}-orange.svg)]({anchor})
        """
    )


def _minimal_changelog(version: str, date: str) -> str:
    return textwrap.dedent(
        f"""\
        # Changelog

        ## [Unreleased]

        ## [{version}] - {date}

        ### Changed

        - Baseline release.
        """
    )


def _minimal_agents(version: str, *, claude: bool, english: bool) -> str:
    header = "CLAUDE" if claude else "AGENTS"
    body = "Note: ~/.claude/sopify/" if claude else "说明：~/.codex/sopify/"
    if english:
        body = "Note: ~/.claude/sopify/" if claude else "Note: ~/.codex/sopify/"
    return textwrap.dedent(
        f"""\
        <!-- SOPIFY_VERSION: {version} -->
        # {header}

        {body}
        """
    )


def _init_release_hook_fixture(root: Path, *, missing_claude_targets: bool = False) -> None:
    for relative in (
        "scripts/release-sync.sh",
        "scripts/release-draft-changelog.py",
        "scripts/release-preflight.sh",
        "scripts/sync-skills.sh",
        "scripts/check-skills-sync.sh",
        "scripts/check-version-consistency.sh",
        ".githooks/pre-commit",
    ):
        _copy_script(relative, root)

    old_version = "2026-03-20.183348"
    old_date = "2026-03-20"
    _write(root / "README.md", _minimal_readme(old_version, english=False))
    _write(root / "README_EN.md", _minimal_readme(old_version, english=True))
    _write(root / "CHANGELOG.md", _minimal_changelog(old_version, old_date))

    _write(root / "Codex/Skills/CN/AGENTS.md", _minimal_agents(old_version, claude=False, english=False))
    _write(root / "Codex/Skills/EN/AGENTS.md", _minimal_agents(old_version, claude=False, english=True))
    _write(root / "Codex/Skills/CN/skills/sopify/SKILL.md", "# skill\n")
    _write(root / "Codex/Skills/EN/skills/sopify/SKILL.md", "# skill\n")

    if not missing_claude_targets:
        _write(root / "Claude/Skills/CN/CLAUDE.md", _minimal_agents(old_version, claude=True, english=False))
        _write(root / "Claude/Skills/EN/CLAUDE.md", _minimal_agents(old_version, claude=True, english=True))
        _write(root / "Claude/Skills/CN/skills/sopify/SKILL.md", "# skill\n")
        _write(root / "Claude/Skills/EN/skills/sopify/SKILL.md", "# skill\n")

    _write(root / "runtime/gate.py", "print('baseline')\n")
    _write(root / "tests/test_runtime_gate.py", "print('baseline test')\n")

    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True, text=True)

    _write(root / "runtime/gate.py", "print('changed')\n")
    _write(root / "tests/test_runtime_gate.py", "print('changed test')\n")
    subprocess.run(["git", "add", "runtime/gate.py", "tests/test_runtime_gate.py"], cwd=root, check=True)


class ReleaseHookTests(unittest.TestCase):
    def test_release_draft_changelog_populates_empty_unreleased(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            changelog = root / "CHANGELOG.md"
            _write(changelog, _minimal_changelog("2026-03-20.183348", "2026-03-20"))

            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "release-draft-changelog.py"),
                    "--root",
                    str(root),
                    "--file",
                    "runtime/gate.py",
                    "--file",
                    "scripts/release-sync.sh",
                    "--file",
                    "tests/test_runtime_gate.py",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            text = changelog.read_text(encoding="utf-8")
            self.assertIn("### Changed", text)
            self.assertIn("`runtime/gate.py`", text)
            self.assertIn("`scripts/release-sync.sh`", text)
            self.assertIn("### Tests", text)
            self.assertIn("`tests/test_runtime_gate.py`", text)

    def test_release_sync_auto_drafts_unreleased_before_version_bump(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _init_release_hook_fixture(root)

            completed = subprocess.run(
                ["bash", str(root / "scripts" / "release-sync.sh"), "2026-03-21.010203", "2026-03-21"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertIn("## [2026-03-21.010203] - 2026-03-21", changelog)
            self.assertIn("`runtime/gate.py`", changelog)
            self.assertIn("`tests/test_runtime_gate.py`", changelog)
            self.assertIn("badge/version-2026--03--21.010203-orange.svg", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("<!-- SOPIFY_VERSION: 2026-03-21.010203 -->", (root / "Codex/Skills/CN/AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("<!-- SOPIFY_VERSION: 2026-03-21.010203 -->", (root / "Claude/Skills/CN/CLAUDE.md").read_text(encoding="utf-8"))

    def test_pre_commit_restores_release_managed_files_when_release_sync_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _init_release_hook_fixture(root, missing_claude_targets=True)

            original_readme = (root / "README.md").read_text(encoding="utf-8")
            original_changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
            original_agents = (root / "Codex/Skills/CN/AGENTS.md").read_text(encoding="utf-8")

            completed = subprocess.run(
                ["bash", str(root / ".githooks" / "pre-commit")],
                cwd=root,
                env={**os.environ, "SOPIFY_SKIP_RELEASE_PREFLIGHT": "1"},
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), original_readme)
            self.assertEqual((root / "CHANGELOG.md").read_text(encoding="utf-8"), original_changelog)
            self.assertEqual((root / "Codex/Skills/CN/AGENTS.md").read_text(encoding="utf-8"), original_agents)
            self.assertFalse((root / ".git" / ".sopify-release-sync-state").exists())


if __name__ == "__main__":
    unittest.main()
