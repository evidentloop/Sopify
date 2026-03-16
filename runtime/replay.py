"""Replay writer for Sopify runtime."""

from __future__ import annotations

import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Iterable, Optional

from .models import PlanArtifact, ReplayEvent, RouteDecision, RunState, RuntimeConfig

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+"),
)


class ReplayWriter:
    """Append-only replay session writer."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def ensure_session(self, run_id: str) -> Path:
        session_dir = self.config.replay_root / run_id
        session_dir.mkdir(parents=True, exist_ok=True)
        events_path = session_dir / "events.jsonl"
        session_path = session_dir / "session.md"
        breakdown_path = session_dir / "breakdown.md"
        if not events_path.exists():
            events_path.write_text("", encoding="utf-8")
        if not session_path.exists():
            session_path.write_text("# Session\n", encoding="utf-8")
        if not breakdown_path.exists():
            breakdown_path.write_text("# Breakdown\n", encoding="utf-8")
        return session_dir

    def append_event(self, run_id: str, event: ReplayEvent) -> Path:
        session_dir = self.ensure_session(run_id)
        events_path = session_dir / "events.jsonl"
        payload = event.to_dict()
        payload["key_output"] = _redact_text(payload["key_output"])
        payload["decision_reason"] = _redact_text(payload["decision_reason"])
        payload["risk"] = _redact_text(payload["risk"])
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return session_dir

    def render_documents(
        self,
        run_id: str,
        *,
        run_state: Optional[RunState],
        route: RouteDecision,
        plan_artifact: Optional[PlanArtifact],
        events: Iterable[ReplayEvent],
    ) -> Path:
        session_dir = self.ensure_session(run_id)
        events_list = list(events)
        self._write_atomic(
            session_dir / "session.md",
            _render_session_markdown(run_state, route, plan_artifact, events_list),
        )
        self._write_atomic(
            session_dir / "breakdown.md",
            _render_breakdown_markdown(events_list),
        )
        return session_dir

    def _write_atomic(self, path: Path, content: str) -> None:
        with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(path)


def _redact_text(text: str) -> str:
    redacted = text
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted


def _render_session_markdown(
    run_state: Optional[RunState],
    route: RouteDecision,
    plan_artifact: Optional[PlanArtifact],
    events: list[ReplayEvent],
) -> str:
    lines = ["# Session", ""]
    lines.append(f"- route: {route.route_name}")
    lines.append(f"- capture_mode: {route.capture_mode}")
    if run_state is not None:
        lines.append(f"- run_id: {run_state.run_id}")
        lines.append(f"- stage: {run_state.stage}")
    if plan_artifact is not None:
        lines.append(f"- plan: {plan_artifact.path}")
    lines.append("")
    lines.append("## Timeline")
    for event in events:
        lines.append(f"- {event.ts} | {event.phase} | {event.intent} | {event.result}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_breakdown_markdown(events: list[ReplayEvent]) -> str:
    lines = ["# Breakdown", ""]
    if not events:
        lines.append("- No events recorded yet.")
        return "\n".join(lines) + "\n"
    for index, event in enumerate(events, start=1):
        lines.append(f"## {index}. {event.phase}")
        lines.append(f"- 目标: {event.intent}")
        lines.append(f"- 动作: {event.action}")
        lines.append(f"- 原因: {_redact_text(event.decision_reason)}")
        lines.append(f"- 结果: {event.result}")
        if event.alternatives:
            lines.append(f"- 备选: {', '.join(event.alternatives)}")
        if event.risk:
            lines.append(f"- 风险: {_redact_text(event.risk)}")
        lines.append("")
    return "\n".join(lines) + "\n"
