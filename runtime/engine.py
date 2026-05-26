"""Legacy compatibility wrapper + non-kernel route handlers (conflict, cancel, archive)."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping, Optional

from .context_snapshot import (
    ContextResolvedSnapshot,
    resolve_context_snapshot,
    snapshot_has_global_execution_truth,
    snapshot_review_run,
)
from .archive_lifecycle import (
    ARCHIVE_STATUS_ALREADY_ARCHIVED,
    ARCHIVE_STATUS_BLOCKED,
    archive_status_payload,
    apply_archive_subject,
    check_archive_subject,
    resolve_archive_subject,
)
from .handoff import build_runtime_handoff
from .kb import bootstrap_kb
from sopify_contracts.artifacts import PlanArtifact
from sopify_contracts.core import RouteDecision, RunState, RuntimeConfig, SkillMeta
from sopify_contracts.decision import ClarificationState, DecisionState
from sopify_contracts.handoff import RuntimeHandoff, RuntimeResult, SkillActivation
from .plan.registry import (
    PlanRegistryError,
    get_plan_entry,
    registry_relative_path,
)
from .router import Router
from .action_intent import (
    ActionProposal,
)
from canonical_writer import StateStore, iso_now
from .state import (
    local_day_now,
    local_display_now,
    local_iso_now,
    local_timezone_name,
    make_run_id,
)

_ABORTABLE_CLARIFICATION_STATUSES = frozenset({"pending", "collecting"})
_ABORTABLE_DECISION_STATUSES = frozenset({"pending", "collecting", "cancelled", "timed_out"})
_ABORTABLE_HANDOFF_ACTIONS = frozenset(
    {
        "answer_questions",
        "confirm_decision",
        "resolve_state_conflict",
    }
)
_ABORTABLE_RUN_STAGES = frozenset(
    {
        "clarification_pending",
        "decision_pending",
    }
)

def _handle_cancel_active(
    decision: RouteDecision,
    *,
    review_store: StateStore,
    global_store: StateStore,
    review_run: RunState | None,
    global_run: RunState | None,
) -> tuple[StateStore, bool, list[str]]:
    cancel_scope = str(decision.artifacts.get("cancel_scope") or "").strip()
    if cancel_scope != "session" and global_run is not None:
        global_store.reset_active_flow()
        if review_store is global_store or review_run is None:
            return (global_store, False, ["Global execution flow cleared"])
        return (global_store, True, ["Global execution flow cleared; session review state preserved"])
    review_store.reset_active_flow()
    return (review_store, False, ["Session review flow cleared"])


def _handle_state_conflict(
    decision: RouteDecision,
    *,
    review_store: StateStore,
    global_store: StateStore,
    snapshot: ContextResolvedSnapshot,
) -> tuple[StateStore, ContextResolvedSnapshot, list[str]]:
    # `state_conflict` only models user-recoverable resolved-state skew.
    # Writer-side contract breaks must keep surfacing as invariant errors
    # instead of being silently downcast into this cleanup path.
    target_store = global_store if snapshot.preferred_state_scope == "global" else review_store
    if decision.active_run_action != "abort_conflict":
        return (target_store, snapshot, list(snapshot.notes))

    notes = ["Conflict cleanup started via explicit abort"]
    processed_roots: set[str] = set()
    for store in (review_store, global_store):
        root_key = str(store.root)
        if root_key in processed_roots:
            continue
        processed_roots.add(root_key)
        notes.extend(_clear_conflict_carriers(store, snapshot=snapshot))
        notes.extend(_clear_abortable_negotiation_state(store))

    next_snapshot = resolve_context_snapshot(
        config=review_store.config,
        review_store=review_store,
        global_store=global_store,
    )
    notes.append("Conflict cleanup completed")
    if next_snapshot.is_conflict:
        notes.append("Conflict cleanup left a remaining conflict that still requires inspection")
    return (
        global_store if next_snapshot.preferred_state_scope == "global" else review_store,
        next_snapshot,
        notes,
    )


def _clear_abortable_negotiation_state(store: StateStore) -> list[str]:
    notes: list[str] = []
    clarification = store.get_current_clarification()
    if _is_abortable_clarification(clarification):
        store.clear_current_clarification()
        notes.append(f"Cleared pending clarification from {store.scope} scope")
    decision = store.get_current_decision()
    if _is_abortable_decision(decision):
        store.clear_current_decision()
        notes.append(f"Cleared unconsumed decision from {store.scope} scope")
    elif decision is not None and decision.status == "confirmed" and decision.selection is not None:
        # A confirmed decision can be the last valid user-owned checkpoint after
        # a crash or session restart. Abort should abandon the live negotiation
        # state around it, but not erase the confirmed choice itself.
        notes.append(f"Preserved confirmed decision in {store.scope} scope")
    handoff = store.get_current_handoff()
    if handoff is not None and handoff.required_host_action in _ABORTABLE_HANDOFF_ACTIONS:
        store.clear_current_handoff()
        notes.append(f"Cleared checkpoint handoff from {store.scope} scope")
    current_run = store.get_current_run()
    current_plan = store.get_current_plan()
    if current_run is not None and current_run.stage in _ABORTABLE_RUN_STAGES:
        if current_plan is None:
            store.clear_current_run()
            notes.append(f"Cleared orphaned negotiation run from {store.scope} scope")
        else:
            store.set_current_run(_normalize_run_after_abort(current_run))
            notes.append(f"Normalized run stage back to stable planning truth in {store.scope} scope")
    return notes


def _clear_conflict_carriers(store: StateStore, *, snapshot: ContextResolvedSnapshot) -> list[str]:
    notes: list[str] = []
    conflict_paths = {
        detail.path
        for detail in snapshot.conflict_items
        if detail.state_scope == store.scope and detail.path
    }
    handoff_path = store.relative_path(store.current_handoff_path)
    if handoff_path in conflict_paths and store.get_current_handoff() is not None:
        # The handoff is a derived carrier for route/run truth. When the
        # snapshot proves it is the conflicted file, we clear only that carrier
        # so the next pass can rebuild a fresh pair without wiping plan/run.
        store.clear_current_handoff()
        notes.append(f"Tombstoned conflicting handoff carrier from {store.scope} scope")
    return notes


def _is_abortable_clarification(clarification: ClarificationState | None) -> bool:
    if clarification is None:
        return False
    return clarification.status in _ABORTABLE_CLARIFICATION_STATUSES


def _is_abortable_decision(decision: DecisionState | None) -> bool:
    if decision is None:
        return False
    return decision.status in _ABORTABLE_DECISION_STATUSES


def _normalize_run_after_abort(current_run: RunState) -> RunState:
    gate = current_run.execution_gate
    stable_stage = "ready_for_execution" if gate is not None and gate.gate_status == "ready" else "plan_generated"
    return RunState(
        run_id=current_run.run_id,
        status=current_run.status,
        stage=stable_stage,
        route_name=current_run.route_name,
        title=current_run.title,
        created_at=current_run.created_at,
        updated_at=iso_now(),
        plan_id=current_run.plan_id,
        plan_path=current_run.plan_path,
        execution_gate=current_run.execution_gate,
        execution_authorization_receipt=current_run.execution_authorization_receipt,
        request_excerpt=current_run.request_excerpt,
        request_sha1=current_run.request_sha1,
        owner_session_id=current_run.owner_session_id,
        owner_host=current_run.owner_host,
        owner_run_id=current_run.owner_run_id,
        resolution_id=current_run.resolution_id,
    )


def run_runtime(
    user_input: str,
    *,
    workspace_root: str | Path = ".",
    global_config_path: str | Path | None = None,
    session_id: str | None = None,
    user_home: Path | None = None,
    runtime_payloads: Optional[Mapping[str, Mapping[str, Any]]] = None,
    action_proposal: ActionProposal | None = None,
) -> RuntimeResult:
    """Run the Sopify runtime pipeline for a single input.

    .. deprecated::
        Legacy wrapper — delegates to ``_orchestration.execute_kernel_turn()``.
        Direct callers should import from ``_orchestration`` instead.
        Kept for backward-compatible test imports (50+ callers use this path).
    """
    from ._orchestration import execute_kernel_turn  # lazy to avoid circular

    return execute_kernel_turn(
        user_input,
        workspace_root=workspace_root,
        global_config_path=global_config_path,
        session_id=session_id,
        user_home=user_home,
        runtime_payloads=runtime_payloads,
        action_proposal=action_proposal,
    )


def _same_plan_artifact(left: PlanArtifact | None, right: PlanArtifact | None) -> bool:
    return left is not None and right is not None and left.plan_id == right.plan_id and left.path == right.path


def _archive_state_store_for_current_plan(
    *,
    current_plan: PlanArtifact | None,
    review_store: StateStore,
    global_store: StateStore,
) -> StateStore:
    if _same_plan_artifact(current_plan, global_store.get_current_plan()):
        return global_store
    if _same_plan_artifact(current_plan, review_store.get_current_plan()):
        return review_store
    return global_store


def _augment_generated_files(
    generated_files: tuple[str, ...],
    *,
    config: RuntimeConfig,
    route_name: str,
    plan_artifact: PlanArtifact | None,
    notes: tuple[str, ...],
    registry_changed_hint: bool = False,
) -> tuple[str, ...]:
    items = list(generated_files)
    if _registry_file_should_be_reported(
        config=config,
        route_name=route_name,
        plan_artifact=plan_artifact,
        notes=notes,
        registry_changed_hint=registry_changed_hint,
    ):
        registry_file = registry_relative_path(config)
        if registry_file not in items:
            items.append(registry_file)
    return tuple(items)


def _registry_file_should_be_reported(
    *,
    config: RuntimeConfig,
    route_name: str,
    plan_artifact: PlanArtifact | None,
    notes: tuple[str, ...],
    registry_changed_hint: bool,
) -> bool:
    if route_name == "archive_lifecycle":
        return registry_changed_hint
    if plan_artifact is None:
        return False
    if not any(note.startswith("Plan scaffold created at ") for note in notes):
        return False
    try:
        # Only surface the registry as a changed artifact when the new plan entry
        # is actually observable after the scaffold step.
        entry_result = get_plan_entry(config=config, plan_id=plan_artifact.plan_id)
    except PlanRegistryError:
        return False
    return entry_result.entry is not None


def _build_skill_activation(
    *,
    decision: RouteDecision,
    run_state: RunState | None,
    current_clarification: ClarificationState | None,
    current_decision: DecisionState | None,
) -> SkillActivation:
    skill_id, skill_name = _activation_target(
        decision=decision,
        current_clarification=current_clarification,
        current_decision=current_decision,
    )
    return SkillActivation(
        skill_id=skill_id,
        skill_name=skill_name,
        activated_at=local_iso_now(),
        activated_local_day=local_day_now(),
        display_time=local_display_now(),
        activation_source="runtime_skill" if decision.runtime_skill_id else "route_phase",
        run_id=run_state.run_id if run_state is not None else make_run_id(decision.request_text),
        route_name=decision.route_name,
        timezone=local_timezone_name(),
    )


def _activation_target(
    *,
    decision: RouteDecision,
    current_clarification: ClarificationState | None,
    current_decision: DecisionState | None,
) -> tuple[str, str]:
    if decision.route_name in {"resume_active", "exec_plan", "quick_fix", "archive_lifecycle"}:
        return ("develop", "开发实施")
    if decision.route_name in {"clarification_pending", "clarification_resume"}:
        if current_clarification is not None and current_clarification.phase == "develop":
            return ("develop", "开发实施")
        return ("analyze", "需求分析")
    if decision.route_name in {"decision_pending", "decision_resume"}:
        if current_decision is not None and current_decision.phase == "develop":
            return ("develop", "开发实施")
        return ("design", "方案设计")
    if decision.route_name in {"plan_only", "workflow", "light_iterate"}:
        return ("design", "方案设计")
    return ("consult", "咨询问答")


