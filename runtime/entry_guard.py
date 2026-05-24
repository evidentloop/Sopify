"""Shared entry-guard contracts for host/runtime checkpoint loops."""

from __future__ import annotations

from typing import Any

DEFAULT_RUNTIME_ENTRY = "scripts/sopify_runtime.py"

ENTRY_GUARD_SCHEMA_VERSION = "1"
ENTRY_GUARD_PENDING_ACTIONS = ("answer_questions", "confirm_decision", "resolve_state_conflict")
ENTRY_GUARD_BYPASS_BLOCKED_COMMANDS = ("~go exec",)
DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE = "direct_edit_blocked_runtime_required"
ENTRY_GUARD_REASON_CODES = {
    "answer_questions": "entry_guard_clarification_pending",
    "confirm_decision": "entry_guard_decision_pending",
    "resolve_state_conflict": "entry_guard_state_conflict",
}


def entry_guard_reason_code(required_host_action: str) -> str | None:
    """Return the normalized reason code for pending checkpoint guard actions."""
    return ENTRY_GUARD_REASON_CODES.get(str(required_host_action or "").strip())


def build_entry_guard_contract(*, required_host_action: str) -> dict[str, Any]:
    """Build a machine-readable host guard contract for this handoff action."""
    normalized_action = str(required_host_action or "").strip()
    reason_code = entry_guard_reason_code(normalized_action)
    pending_fail_closed = normalized_action in ENTRY_GUARD_PENDING_ACTIONS
    return {
        "schema_version": ENTRY_GUARD_SCHEMA_VERSION,
        "strict_runtime_entry": True,
        "default_runtime_entry": DEFAULT_RUNTIME_ENTRY,
        "pending_checkpoint_actions": list(ENTRY_GUARD_PENDING_ACTIONS),
        "required_host_action": normalized_action,
        "pending_checkpoint_fail_closed": pending_fail_closed,
        "reason_code": reason_code,
        "bypass_blocked_commands": list(ENTRY_GUARD_BYPASS_BLOCKED_COMMANDS) if pending_fail_closed else [],
    }
