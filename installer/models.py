"""Shared installer models and target parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LANGUAGE_DIRECTORY_MAP = {
    "zh-CN": "CN",
    "en-US": "EN",
}

SUPPORTED_HOSTS = {"codex", "claude"}


class InstallError(RuntimeError):
    """Raised when the installer cannot complete safely."""


@dataclass(frozen=True)
class InstallTarget:
    """Normalized installer target."""

    host: str
    language: str

    @property
    def value(self) -> str:
        return f"{self.host}:{self.language}"

    @property
    def language_directory(self) -> str:
        return LANGUAGE_DIRECTORY_MAP[self.language]


@dataclass(frozen=True)
class InstallResult:
    """Summary of a completed Sopify installation."""

    target: InstallTarget
    workspace_root: Path
    host_root: Path
    bundle_root: Path
    verified_paths: tuple[Path, ...]
    smoke_output: str


def parse_install_target(raw_value: str) -> InstallTarget:
    """Parse a CLI target like `codex:zh-CN`."""
    value = raw_value.strip()
    host, separator, language = value.partition(":")
    if not separator:
        raise InstallError("Target must use the format <host:lang>, for example codex:zh-CN")
    if host not in SUPPORTED_HOSTS:
        raise InstallError(f"Unsupported host: {host}")
    if language not in LANGUAGE_DIRECTORY_MAP:
        raise InstallError(f"Unsupported language: {language}")
    return InstallTarget(host=host, language=language)

