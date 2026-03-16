"""Directory-based skill discovery for Sopify runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence
import re

from ._yaml import load_yaml
from .models import RuntimeConfig, SkillMeta

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class SkillRegistry:
    """Discover skills by convention and normalize their metadata."""

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        repo_root: Path | None = None,
        user_home: Path | None = None,
    ) -> None:
        self.config = config
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent
        self.user_home = user_home or Path.home()

    def discover(self) -> tuple[SkillMeta, ...]:
        ordered_roots = self._search_roots()
        discovered: Dict[str, SkillMeta] = {}
        for root, source in ordered_roots:
            if not root.exists():
                continue
            for skill in self._discover_under_root(root, source):
                discovered.setdefault(skill.skill_id, skill)
        return tuple(discovered.values())

    def _search_roots(self) -> list[tuple[Path, str]]:
        language = "CN" if self.config.language == "zh-CN" else "EN"
        alternate = "EN" if language == "CN" else "CN"
        return [
            (self.repo_root / "Codex" / "Skills" / language / "skills", "builtin"),
            (self.repo_root / "Claude" / "Skills" / language / "skills", "builtin"),
            (self.repo_root / "Codex" / "Skills" / alternate / "skills", "builtin"),
            (self.repo_root / "Claude" / "Skills" / alternate / "skills", "builtin"),
            (self.config.workspace_root / "skills", "project"),
            (self.config.workspace_root / self.config.plan_directory / "skills", "workspace"),
            (self.user_home / ".codex" / "skills", "user"),
        ]

    def _discover_under_root(self, root: Path, source: str) -> Iterable[SkillMeta]:
        for skill_file in sorted(root.rglob("SKILL.md")):
            skill = self._read_skill(skill_file, source)
            if skill is not None:
                yield skill

    def _read_skill(self, skill_file: Path, source: str) -> Optional[SkillMeta]:
        text = skill_file.read_text(encoding="utf-8")
        front_matter = _parse_front_matter(text)
        skill_dir = skill_file.parent
        manifest = _load_manifest(skill_dir / "skill.yaml")
        skill_id = str(
            manifest.get("id")
            or front_matter.get("name")
            or skill_dir.name
        )
        name = str(front_matter.get("name") or manifest.get("name") or skill_id)
        description = str(front_matter.get("description") or manifest.get("description") or "")
        runtime_entry = _resolve_runtime_entry(skill_dir, manifest, skill_id, self.repo_root)
        mode = str(manifest.get("mode") or _infer_mode(skill_file, runtime_entry))
        triggers = tuple(manifest.get("triggers") or ())
        metadata: Mapping[str, object] = dict(manifest.get("metadata") or {})

        return SkillMeta(
            skill_id=skill_id,
            name=name,
            description=description,
            path=skill_file,
            source=source,
            mode=mode,
            runtime_entry=runtime_entry,
            triggers=triggers,
            metadata=metadata,
        )


def _parse_front_matter(text: str) -> dict[str, object]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    data = load_yaml(match.group(1))
    return data if isinstance(data, dict) else {}


def _load_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    data = load_yaml(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _resolve_runtime_entry(
    skill_dir: Path,
    manifest: Mapping[str, object],
    skill_id: str,
    repo_root: Path,
) -> Path | None:
    raw_entry = manifest.get("runtime_entry")
    if isinstance(raw_entry, str) and raw_entry:
        candidate = (skill_dir / raw_entry).resolve()
        if candidate.exists():
            return candidate
    for filename in (f"{skill_id.replace('-', '_')}_runtime.py", f"{skill_id.replace('-', '_')}.py"):
        candidate = repo_root / "scripts" / filename
        if candidate.exists():
            return candidate.resolve()
    return None


def _infer_mode(skill_file: Path, runtime_entry: Path | None) -> str:
    if runtime_entry is not None:
        return "runtime"
    parts = {part.lower() for part in skill_file.parts}
    if "sopify" in parts:
        return "workflow"
    return "advisory"
