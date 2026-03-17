"""Base host adapter and shared install helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from installer.models import InstallError

_IGNORE_PATTERNS = shutil.ignore_patterns(".DS_Store", "Thumbs.db", "__pycache__")


@dataclass(frozen=True)
class HostAdapter:
    """Host-specific layout for Sopify prompt-layer assets."""

    host_name: str
    source_dirname: str
    destination_dirname: str
    header_filename: str

    def source_root(self, repo_root: Path, language_directory: str) -> Path:
        return repo_root / self.source_dirname / "Skills" / language_directory

    def destination_root(self, home_root: Path) -> Path:
        return home_root / self.destination_dirname

    def expected_paths(self, home_root: Path) -> tuple[Path, ...]:
        root = self.destination_root(home_root)
        return (
            root / self.header_filename,
            root / "skills" / "sopify" / "analyze" / "SKILL.md",
            root / "skills" / "sopify" / "design" / "SKILL.md",
        )


def install_host_assets(
    adapter: HostAdapter,
    *,
    repo_root: Path,
    home_root: Path,
    language_directory: str,
) -> tuple[Path, ...]:
    """Install or update Sopify prompt-layer assets for one host."""
    source_root = adapter.source_root(repo_root, language_directory)
    header_source = source_root / adapter.header_filename
    skills_source = source_root / "skills" / "sopify"
    if not header_source.is_file():
        raise InstallError(f"Missing source header file: {header_source}")
    if not skills_source.is_dir():
        raise InstallError(f"Missing source skills directory: {skills_source}")

    destination_root = adapter.destination_root(home_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    header_destination = destination_root / adapter.header_filename
    shutil.copy2(header_source, header_destination)

    skills_destination = destination_root / "skills" / "sopify"
    if skills_destination.exists():
        shutil.rmtree(skills_destination)
    skills_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skills_source, skills_destination, ignore=_IGNORE_PATTERNS)

    return adapter.expected_paths(home_root)

