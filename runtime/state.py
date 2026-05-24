"""Filesystem-backed state storage for Sopify runtime.

Runtime-specific helpers that do not belong in canonical_writer.
StateStore, iso_now and normalize_session_id live in canonical_writer.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from hashlib import sha1
import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Optional

from canonical_writer.store import SESSIONS_DIRNAME
from canonical_writer import iso_now

from sopify_contracts.artifacts import PlanArtifact
from sopify_contracts.core import ExecutionGate, RouteDecision, RunState, RuntimeConfig


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


def cleanup_expired_session_state(
    config: RuntimeConfig,
    *,
    older_than_days: int = 7,
) -> tuple[str, ...]:
    """Remove stale session-state directories during gate startup."""
    sessions_root = config.state_dir / SESSIONS_DIRNAME
    if not sessions_root.exists():
        return ()

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    removed: list[str] = []
    for session_dir in sessions_root.iterdir():
        if not session_dir.is_dir():
            continue
        updated_at = _session_dir_updated_at(session_dir)
        if updated_at is None or updated_at >= cutoff:
            continue
        shutil.rmtree(session_dir, ignore_errors=True)
        removed.append(str(session_dir.relative_to(config.workspace_root)))
    return tuple(sorted(removed))


def _session_dir_updated_at(session_dir: Path) -> datetime | None:
    last_route_path = session_dir / "last_route.json"
    payload = _read_json_file(last_route_path)
    updated_at = str(payload.get("updated_at") or "").strip() if payload else ""
    if updated_at:
        parsed = _parse_iso_datetime(updated_at)
        if parsed is not None:
            return parsed
    if last_route_path.exists():
        return datetime.fromtimestamp(last_route_path.stat().st_mtime, timezone.utc)
    try:
        return datetime.fromtimestamp(session_dir.stat().st_mtime, timezone.utc)
    except FileNotFoundError:
        return None


def _parse_iso_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json_file(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


# -- Run state construction (consolidated from engine.py / _kernel_turn.py) ----


def make_run_id(request_text: str) -> str:
    """Generate a timestamp+digest run identifier."""
    timestamp = iso_now().replace(":", "").replace("-", "")[:15]
    digest = sha1(request_text.encode("utf-8")).hexdigest()[:6]
    return f"{timestamp}_{digest}"


def make_run_state(
    decision: RouteDecision,
    plan_artifact: PlanArtifact,
    *,
    stage: str = "plan_generated",
    execution_gate: ExecutionGate | None = None,
    execution_authorization_receipt: Mapping[str, Any] | None = None,
) -> RunState:
    """Construct a fresh RunState from a route decision and plan artifact."""
    now = iso_now()
    return RunState(
        run_id=make_run_id(decision.request_text),
        status="active",
        stage=stage,
        route_name=decision.route_name,
        title=plan_artifact.title,
        created_at=now,
        updated_at=now,
        plan_id=plan_artifact.plan_id,
        plan_path=plan_artifact.path,
        execution_gate=execution_gate,
        execution_authorization_receipt=execution_authorization_receipt,
        request_excerpt=summarize_request_text(decision.request_text),
        request_sha1=stable_request_sha1(decision.request_text),
        owner_session_id="",
        owner_host="",
        owner_run_id="",
    )
