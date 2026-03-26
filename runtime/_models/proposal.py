"""Plan-proposal runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .core import _json_mapping


@dataclass(frozen=True)
class PlanProposalState:
    """Filesystem-backed proposal state before a plan package is materialized."""

    schema_version: str
    checkpoint_id: str
    reserved_plan_id: str
    topic_key: str
    proposed_level: str
    proposed_path: str
    analysis_summary: str
    estimated_task_count: int
    candidate_files: tuple[str, ...] = ()
    request_text: str = ""
    resume_route: str = "workflow"
    capture_mode: str = "off"
    candidate_skill_ids: tuple[str, ...] = ()
    confirmed_decision: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "reserved_plan_id": self.reserved_plan_id,
            "topic_key": self.topic_key,
            "proposed_level": self.proposed_level,
            "proposed_path": self.proposed_path,
            "analysis_summary": self.analysis_summary,
            "estimated_task_count": self.estimated_task_count,
            "candidate_files": list(self.candidate_files),
            "request_text": self.request_text,
            "resume_route": self.resume_route,
            "capture_mode": self.capture_mode,
            "candidate_skill_ids": list(self.candidate_skill_ids),
            "confirmed_decision": _json_mapping(self.confirmed_decision),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanProposalState":
        return cls(
            schema_version=str(data.get("schema_version") or "1"),
            checkpoint_id=str(data.get("checkpoint_id") or ""),
            reserved_plan_id=str(data.get("reserved_plan_id") or ""),
            topic_key=str(data.get("topic_key") or ""),
            proposed_level=str(data.get("proposed_level") or "standard"),
            proposed_path=str(data.get("proposed_path") or ""),
            analysis_summary=str(data.get("analysis_summary") or ""),
            estimated_task_count=int(data.get("estimated_task_count") or 0),
            candidate_files=tuple(str(item) for item in (data.get("candidate_files") or ()) if str(item).strip()),
            request_text=str(data.get("request_text") or ""),
            resume_route=str(data.get("resume_route") or "workflow"),
            capture_mode=str(data.get("capture_mode") or "off"),
            candidate_skill_ids=tuple(str(item) for item in (data.get("candidate_skill_ids") or ()) if str(item).strip()),
            confirmed_decision=_json_mapping(data.get("confirmed_decision")),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )
