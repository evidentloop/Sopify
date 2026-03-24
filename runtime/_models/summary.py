"""Daily summary contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SummaryScope:
    """Canonical scope for a per-day workspace summary."""

    local_day: str
    workspace_root: str
    workspace_label: str = "当前工作区"
    timezone: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_day": self.local_day,
            "workspace_root": self.workspace_root,
            "workspace_label": self.workspace_label,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryScope":
        return cls(
            local_day=str(data.get("local_day") or ""),
            workspace_root=str(data.get("workspace_root") or ""),
            workspace_label=str(data.get("workspace_label") or "当前工作区"),
            timezone=str(data.get("timezone") or ""),
        )


@dataclass(frozen=True)
class SummarySourceWindow:
    """Time window covered by a generated summary."""

    from_ts: str
    to_ts: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_ts,
            "to": self.to_ts,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummarySourceWindow":
        return cls(
            from_ts=str(data.get("from") or ""),
            to_ts=str(data.get("to") or ""),
        )


@dataclass(frozen=True)
class SummarySourceRefFile:
    """Filesystem source consumed while assembling a summary."""

    path: str
    kind: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummarySourceRefFile":
        return cls(
            path=str(data.get("path") or ""),
            kind=str(data.get("kind") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass(frozen=True)
class SummaryGitCommitRef:
    """Git commit reference cited by a summary."""

    sha: str
    title: str
    authored_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "title": self.title,
            "authored_at": self.authored_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryGitCommitRef":
        return cls(
            sha=str(data.get("sha") or ""),
            title=str(data.get("title") or ""),
            authored_at=str(data.get("authored_at") or ""),
        )


@dataclass(frozen=True)
class SummaryGitRefs:
    """Git-derived references for summary generation."""

    base_ref: str = "HEAD"
    changed_files: tuple[str, ...] = ()
    commits: tuple[SummaryGitCommitRef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_ref": self.base_ref,
            "changed_files": list(self.changed_files),
            "commits": [commit.to_dict() for commit in self.commits],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryGitRefs":
        return cls(
            base_ref=str(data.get("base_ref") or "HEAD"),
            changed_files=tuple(data.get("changed_files") or ()),
            commits=tuple(SummaryGitCommitRef.from_dict(commit) for commit in (data.get("commits") or ())),
        )


@dataclass(frozen=True)
class SummaryReplaySessionRef:
    """Optional replay session reference used by summary generation."""

    run_id: str
    path: str
    used_for: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "path": self.path,
            "used_for": self.used_for,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryReplaySessionRef":
        return cls(
            run_id=str(data.get("run_id") or ""),
            path=str(data.get("path") or ""),
            used_for=str(data.get("used_for") or ""),
        )


@dataclass(frozen=True)
class SummarySourceRefs:
    """Collected source references for deterministic summary generation."""

    plan_files: tuple[SummarySourceRefFile, ...] = ()
    state_files: tuple[SummarySourceRefFile, ...] = ()
    handoff_files: tuple[SummarySourceRefFile, ...] = ()
    git_refs: SummaryGitRefs = field(default_factory=SummaryGitRefs)
    replay_sessions: tuple[SummaryReplaySessionRef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_files": [entry.to_dict() for entry in self.plan_files],
            "state_files": [entry.to_dict() for entry in self.state_files],
            "handoff_files": [entry.to_dict() for entry in self.handoff_files],
            "git_refs": self.git_refs.to_dict(),
            "replay_sessions": [entry.to_dict() for entry in self.replay_sessions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummarySourceRefs":
        git_refs = data.get("git_refs")
        return cls(
            plan_files=tuple(SummarySourceRefFile.from_dict(entry) for entry in (data.get("plan_files") or ())),
            state_files=tuple(SummarySourceRefFile.from_dict(entry) for entry in (data.get("state_files") or ())),
            handoff_files=tuple(SummarySourceRefFile.from_dict(entry) for entry in (data.get("handoff_files") or ())),
            git_refs=SummaryGitRefs.from_dict(git_refs) if isinstance(git_refs, Mapping) else SummaryGitRefs(),
            replay_sessions=tuple(SummaryReplaySessionRef.from_dict(entry) for entry in (data.get("replay_sessions") or ())),
        )


@dataclass(frozen=True)
class SummaryGoalFact:
    """Goal or intent captured in a daily summary."""

    fact_id: str
    summary: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fact_id,
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryGoalFact":
        return cls(
            fact_id=str(data.get("id") or ""),
            summary=str(data.get("summary") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryDecisionFact:
    """Decision confirmed or observed during the day."""

    fact_id: str
    summary: str
    reason: str
    status: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fact_id,
            "summary": self.summary,
            "reason": self.reason,
            "status": self.status,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryDecisionFact":
        return cls(
            fact_id=str(data.get("id") or ""),
            summary=str(data.get("summary") or ""),
            reason=str(data.get("reason") or ""),
            status=str(data.get("status") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryCodeChangeFact:
    """Code or document change captured in the daily summary."""

    path: str
    change_type: str
    summary: str
    reason: str
    verification: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "summary": self.summary,
            "reason": self.reason,
            "verification": self.verification,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryCodeChangeFact":
        return cls(
            path=str(data.get("path") or ""),
            change_type=str(data.get("change_type") or ""),
            summary=str(data.get("summary") or ""),
            reason=str(data.get("reason") or ""),
            verification=str(data.get("verification") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryIssueFact:
    """Open or resolved issue noted in the summary."""

    fact_id: str
    summary: str
    status: str
    resolution: str = ""
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fact_id,
            "summary": self.summary,
            "status": self.status,
            "resolution": self.resolution,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryIssueFact":
        return cls(
            fact_id=str(data.get("id") or ""),
            summary=str(data.get("summary") or ""),
            status=str(data.get("status") or ""),
            resolution=str(data.get("resolution") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryLessonFact:
    """Reusable lesson extracted from the day's work."""

    fact_id: str
    summary: str
    reusable_pattern: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fact_id,
            "summary": self.summary,
            "reusable_pattern": self.reusable_pattern,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryLessonFact":
        return cls(
            fact_id=str(data.get("id") or ""),
            summary=str(data.get("summary") or ""),
            reusable_pattern=str(data.get("reusable_pattern") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryNextStepFact:
    """Actionable next step carried forward from the summary."""

    fact_id: str
    summary: str
    priority: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fact_id,
            "summary": self.summary,
            "priority": self.priority,
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryNextStepFact":
        return cls(
            fact_id=str(data.get("id") or ""),
            summary=str(data.get("summary") or ""),
            priority=str(data.get("priority") or ""),
            evidence_refs=tuple(data.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class SummaryFacts:
    """All structured facts rendered into a daily summary."""

    headline: str = ""
    goals: tuple[SummaryGoalFact, ...] = ()
    decisions: tuple[SummaryDecisionFact, ...] = ()
    code_changes: tuple[SummaryCodeChangeFact, ...] = ()
    issues: tuple[SummaryIssueFact, ...] = ()
    lessons: tuple[SummaryLessonFact, ...] = ()
    next_steps: tuple[SummaryNextStepFact, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "goals": [fact.to_dict() for fact in self.goals],
            "decisions": [fact.to_dict() for fact in self.decisions],
            "code_changes": [fact.to_dict() for fact in self.code_changes],
            "issues": [fact.to_dict() for fact in self.issues],
            "lessons": [fact.to_dict() for fact in self.lessons],
            "next_steps": [fact.to_dict() for fact in self.next_steps],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryFacts":
        return cls(
            headline=str(data.get("headline") or ""),
            goals=tuple(SummaryGoalFact.from_dict(fact) for fact in (data.get("goals") or ())),
            decisions=tuple(SummaryDecisionFact.from_dict(fact) for fact in (data.get("decisions") or ())),
            code_changes=tuple(SummaryCodeChangeFact.from_dict(fact) for fact in (data.get("code_changes") or ())),
            issues=tuple(SummaryIssueFact.from_dict(fact) for fact in (data.get("issues") or ())),
            lessons=tuple(SummaryLessonFact.from_dict(fact) for fact in (data.get("lessons") or ())),
            next_steps=tuple(SummaryNextStepFact.from_dict(fact) for fact in (data.get("next_steps") or ())),
        )


@dataclass(frozen=True)
class SummaryQualityChecks:
    """Quality and fallback markers for generated summaries."""

    replay_optional: bool = True
    summary_runs_per_day: str = "1-2"
    required_sections_present: bool = False
    missing_inputs: tuple[str, ...] = ()
    fallback_used: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_optional": self.replay_optional,
            "summary_runs_per_day": self.summary_runs_per_day,
            "required_sections_present": self.required_sections_present,
            "missing_inputs": list(self.missing_inputs),
            "fallback_used": list(self.fallback_used),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SummaryQualityChecks":
        return cls(
            replay_optional=bool(data.get("replay_optional", True)),
            summary_runs_per_day=str(data.get("summary_runs_per_day") or "1-2"),
            required_sections_present=bool(data.get("required_sections_present", False)),
            missing_inputs=tuple(data.get("missing_inputs") or ()),
            fallback_used=tuple(data.get("fallback_used") or ()),
        )


@dataclass(frozen=True)
class DailySummaryArtifact:
    """Canonical machine-readable summary for a local day and workspace."""

    summary_key: str
    scope: SummaryScope
    revision: int
    generated_at: str
    source_window: SummarySourceWindow
    source_refs: SummarySourceRefs
    facts: SummaryFacts
    quality_checks: SummaryQualityChecks
    schema_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "summary_key": self.summary_key,
            "scope": self.scope.to_dict(),
            "revision": self.revision,
            "generated_at": self.generated_at,
            "source_window": self.source_window.to_dict(),
            "source_refs": self.source_refs.to_dict(),
            "facts": self.facts.to_dict(),
            "quality_checks": self.quality_checks.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DailySummaryArtifact":
        scope = data.get("scope")
        source_window = data.get("source_window")
        source_refs = data.get("source_refs")
        facts = data.get("facts")
        quality_checks = data.get("quality_checks")
        return cls(
            schema_version=str(data.get("schema_version") or "1"),
            summary_key=str(data.get("summary_key") or ""),
            scope=SummaryScope.from_dict(scope) if isinstance(scope, Mapping) else SummaryScope(local_day="", workspace_root=""),
            revision=int(data.get("revision") or 0),
            generated_at=str(data.get("generated_at") or ""),
            source_window=(
                SummarySourceWindow.from_dict(source_window)
                if isinstance(source_window, Mapping)
                else SummarySourceWindow(from_ts="", to_ts="")
            ),
            source_refs=SummarySourceRefs.from_dict(source_refs) if isinstance(source_refs, Mapping) else SummarySourceRefs(),
            facts=SummaryFacts.from_dict(facts) if isinstance(facts, Mapping) else SummaryFacts(),
            quality_checks=(
                SummaryQualityChecks.from_dict(quality_checks)
                if isinstance(quality_checks, Mapping)
                else SummaryQualityChecks()
            ),
        )
