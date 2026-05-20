"""Plan and knowledge-base artifact contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PlanArtifact:
    """Generated plan package metadata."""

    plan_id: str
    title: str
    summary: str
    level: str
    path: str
    files: tuple[str, ...]
    created_at: str
    topic_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "summary": self.summary,
            "level": self.level,
            "path": self.path,
            "files": list(self.files),
            "created_at": self.created_at,
            "topic_key": self.topic_key,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanArtifact":
        return cls(
            plan_id=str(data.get("plan_id") or ""),
            title=str(data.get("title") or ""),
            summary=str(data.get("summary") or ""),
            level=str(data.get("level") or "light"),
            path=str(data.get("path") or ""),
            files=tuple(data.get("files") or ()),
            created_at=str(data.get("created_at") or ""),
            topic_key=str(data.get("topic_key") or data.get("feature_key") or ""),
        )


@dataclass(frozen=True)
class KbArtifact:
    """Minimal knowledge-base files created by the runtime."""

    mode: str
    files: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "files": list(self.files),
            "created_at": self.created_at,
        }
