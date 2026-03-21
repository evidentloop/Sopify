"""Filesystem-backed state storage for Sopify runtime."""

from __future__ import annotations

from datetime import datetime, time, timezone
from hashlib import sha1
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping, Optional

from .handoff import read_runtime_handoff
from .models import ClarificationState, DecisionState, DecisionSubmission, PlanArtifact, RouteDecision, RunState, RuntimeConfig, RuntimeHandoff


class StateStore:
    """Read and write runtime state files under `.sopify-skills/state/`."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self.root = config.state_dir
        self.current_run_path = self.root / "current_run.json"
        self.last_route_path = self.root / "last_route.json"
        self.current_plan_path = self.root / "current_plan.json"
        self.current_handoff_path = self.root / "current_handoff.json"
        self.current_clarification_path = self.root / "current_clarification.json"
        self.current_decision_path = self.root / "current_decision.json"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def get_current_run(self) -> Optional[RunState]:
        payload = self._read_json(self.current_run_path)
        return RunState.from_dict(payload) if payload else None

    def set_current_run(self, run_state: RunState) -> None:
        self.ensure()
        payload = run_state.to_dict()
        payload["observability"] = {
            "state_kind": "current_run",
            "writer": "runtime.state",
            "written_at": iso_now(),
            "workspace_root": str(self.config.workspace_root),
            "runtime_root": str(self.config.runtime_root.relative_to(self.config.workspace_root)),
            "state_path": str(self.current_run_path.relative_to(self.config.workspace_root)),
            "run_id": run_state.run_id,
            "route_name": run_state.route_name,
            "stage": run_state.stage,
            "status": run_state.status,
            "request_excerpt": run_state.request_excerpt,
            "request_sha1": run_state.request_sha1,
        }
        self._write_json(self.current_run_path, payload)

    def clear_current_run(self) -> None:
        self.current_run_path.unlink(missing_ok=True)

    def get_last_route(self) -> Optional[RouteDecision]:
        payload = self._read_json(self.last_route_path)
        return RouteDecision.from_dict(payload) if payload else None

    def set_last_route(self, decision: RouteDecision) -> None:
        self.ensure()
        payload = decision.to_dict()
        payload["updated_at"] = iso_now()
        self._write_json(self.last_route_path, payload)

    def get_current_plan(self) -> Optional[PlanArtifact]:
        payload = self._read_json(self.current_plan_path)
        return PlanArtifact.from_dict(payload) if payload else None

    def set_current_plan(self, artifact: PlanArtifact) -> None:
        self.ensure()
        self._write_json(self.current_plan_path, artifact.to_dict())

    def clear_current_plan(self) -> None:
        self.current_plan_path.unlink(missing_ok=True)

    def get_current_clarification(self) -> Optional[ClarificationState]:
        payload = self._read_json(self.current_clarification_path)
        return ClarificationState.from_dict(payload) if payload else None

    def set_current_clarification(self, clarification_state: ClarificationState) -> None:
        self.ensure()
        self._write_json(self.current_clarification_path, clarification_state.to_dict())

    def set_current_clarification_response(
        self,
        *,
        response_text: str,
        response_fields: Mapping[str, Any],
        response_source: str | None,
        response_message: str = "",
    ) -> Optional[ClarificationState]:
        """Persist host-collected clarification answers without rewriting the whole flow."""
        current = self.get_current_clarification()
        if current is None:
            return None
        updated = current.with_response(
            response_text=response_text,
            response_fields=response_fields,
            response_source=response_source,
            response_message=response_message,
            submitted_at=iso_now(),
        )
        self.set_current_clarification(updated)
        return updated

    def clear_current_clarification(self) -> None:
        self.current_clarification_path.unlink(missing_ok=True)

    def get_current_decision(self) -> Optional[DecisionState]:
        payload = self._read_json(self.current_decision_path)
        return DecisionState.from_dict(payload) if payload else None

    def set_current_decision(self, decision_state: DecisionState) -> None:
        self.ensure()
        self._write_json(self.current_decision_path, decision_state.to_dict())

    def set_current_decision_submission(self, submission: DecisionSubmission) -> Optional[DecisionState]:
        """Persist host-collected decision answers without rewriting the whole state file."""
        current = self.get_current_decision()
        if current is None:
            return None
        updated = current.with_submission(submission)
        self.set_current_decision(updated)
        return updated

    def clear_current_decision(self) -> None:
        self.current_decision_path.unlink(missing_ok=True)

    def get_current_handoff(self) -> Optional[RuntimeHandoff]:
        return read_runtime_handoff(self.current_handoff_path)

    def set_current_handoff(self, handoff: RuntimeHandoff) -> None:
        self.ensure()
        payload = handoff.to_dict()
        observability = dict(payload.get("observability") or {})
        observability.update(
            {
                "state_kind": "current_handoff",
                "writer": "runtime.state",
                "written_at": iso_now(),
                "workspace_root": str(self.config.workspace_root),
                "runtime_root": str(self.config.runtime_root.relative_to(self.config.workspace_root)),
                "state_path": str(self.current_handoff_path.relative_to(self.config.workspace_root)),
                "run_id": handoff.run_id,
                "route_name": handoff.route_name,
                "required_host_action": handoff.required_host_action,
            }
        )
        payload["observability"] = observability
        self._write_json(self.current_handoff_path, payload)

    def clear_current_handoff(self) -> None:
        self.current_handoff_path.unlink(missing_ok=True)

    def has_active_flow(self) -> bool:
        current_run = self.get_current_run()
        return current_run is not None and current_run.is_active

    def reset_active_flow(self) -> None:
        self.clear_current_run()
        self.clear_current_plan()
        self.clear_current_handoff()
        self.clear_current_clarification()
        self.clear_current_decision()

    def update_active_run(self, *, stage: Optional[str] = None, status: Optional[str] = None) -> Optional[RunState]:
        current = self.get_current_run()
        if current is None:
            return None
        updated = RunState(
            run_id=current.run_id,
            status=status or current.status,
            stage=stage or current.stage,
            route_name=current.route_name,
            title=current.title,
            created_at=current.created_at,
            updated_at=iso_now(),
            plan_id=current.plan_id,
            plan_path=current.plan_path,
            execution_gate=current.execution_gate,
            request_excerpt=current.request_excerpt,
            request_sha1=current.request_sha1,
        )
        self.set_current_run(updated)
        return updated

    def _read_json(self, path: Path) -> Optional[dict[str, Any]]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        temp_path.replace(path)


def iso_now() -> str:
    """Return a stable UTC ISO timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_request_sha1(text: str) -> str:
    """Return a short stable fingerprint for request-level observability."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return ""
    return sha1(normalized.encode("utf-8")).hexdigest()[:12]


def summarize_request_text(text: str, *, limit: int = 120) -> str:
    """Return a compact single-line excerpt for request observability."""
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    if limit <= 3:
        return compact[:limit]
    return compact[: limit - 3].rstrip() + "..."


def local_now() -> datetime:
    """Return the local wall-clock time used for user-facing timestamps."""
    return datetime.now().astimezone().replace(microsecond=0)


def local_iso_now() -> str:
    """Return a stable local ISO timestamp."""
    return local_now().isoformat()


def local_display_now() -> str:
    """Return the formatted local time shown in runtime output."""
    return local_now().strftime("%Y-%m-%d %H:%M:%S")


def local_day_now() -> str:
    """Return the current local day used by the daily summary scope."""
    return local_now().date().isoformat()


def local_timezone_name() -> str:
    """Return a stable local timezone label when available."""
    tzinfo = local_now().tzinfo
    if tzinfo is None:
        return ""
    key = getattr(tzinfo, "key", None)
    if isinstance(key, str) and key.strip():
        return key
    name = tzinfo.tzname(None)
    return str(name or "")


def local_day_start_iso(day: str) -> str:
    """Return the start timestamp for a local-day summary window."""
    base = local_now()
    target_date = datetime.fromisoformat(day).date()
    return datetime.combine(target_date, time.min, tzinfo=base.tzinfo).isoformat()
