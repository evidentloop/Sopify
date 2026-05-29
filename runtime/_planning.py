"""Planning pipeline: plan creation, resolution, checkpoint gates, and resume."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Mapping

from .checkpoint_materializer import materialize_checkpoint_request
from .checkpoint_request import checkpoint_request_from_clarification_state, checkpoint_request_from_decision_state
from .clarification import build_clarification_state, has_submitted_clarification, merge_clarification_request, parse_clarification_response
from .decision import (
    ACTIVE_PLAN_ATTACH_OPTION_ID,
    ACTIVE_PLAN_BINDING_DECISION_TYPE,
    ACTIVE_PLAN_NEW_OPTION_ID,
    build_active_plan_binding_decision_state,
    build_decision_state,
    build_execution_gate_decision_state,
    confirm_decision,
    consume_decision,
    has_submitted_decision,
    parse_decision_response,
    response_from_submission,
)
from .execution_gate import evaluate_execution_gate
from .action_intent import ExecutionAuthorizationReceipt
from .kb import ensure_blueprint_index, ensure_blueprint_scaffold
from sopify_contracts.artifacts import KbArtifact, PlanArtifact
from sopify_contracts.core import ExecutionGate, RouteDecision, RunState, RuntimeConfig
from sopify_contracts.decision import ClarificationState, DecisionState
from .plan.registry import (
    PlanRegistryError,
    encode_priority_note_event,
    priority_note_for_plan,
    upsert_plan_entry,
)
from .plan.scaffold import create_plan_scaffold
from .plan.lookup import find_plan_by_request_reference
from .plan.intent import request_explicitly_wants_new_plan
from canonical_writer import StateStore, iso_now
from .state import (
    make_run_id,
    make_run_state,
    stable_request_sha1,
    summarize_request_text,
)

_CURRENT_PLAN_ANCHOR_PATTERNS = (
    re.compile(r"(当前|这个|该)\s*(plan|方案)", re.IGNORECASE),
    re.compile(r"(current|active)\s+plan", re.IGNORECASE),
    re.compile(r"(继续|回到|基于|沿用|挂到|并入|写进|写入).*(plan|方案)", re.IGNORECASE),
)

def is_develop_callback_state(_state: object) -> bool:
    """Fail-close — develop callback path retired."""
    if hasattr(_state, 'resume_context') and isinstance(getattr(_state, 'resume_context', None), dict):
        if _state.resume_context.get("source") == "develop_callback":
            raise RuntimeError(
                "develop_callback state detected but develop_callback is retired; "
                "clear the stale current_clarification/current_decision to proceed"
            )
    return False


def develop_resume_after(_resume_context: object) -> object:
    """Fail-close — develop callback path retired."""
    raise RuntimeError("develop_callback is retired; develop_resume_after should not be reached")


@dataclass(frozen=True)
class _PlanSelection:
    """Describe whether planning should reuse an existing plan or create a new one."""

    action: str
    plan_artifact: PlanArtifact | None = None
    reason_note: str = ""


@dataclass(frozen=True)
class _PlanningContext:
    """Single captured planning truth used by deep planning helpers.

    Main runtime flow should pass this explicitly from recovered context so the
    helper chain does not re-open state files mid-decision. A capture helper
    remains only as a narrow compatibility bridge for direct helper tests and
    internal restart points that must intentionally refresh local state once.
    """

    current_run: RunState | None = None
    current_plan: PlanArtifact | None = None
    current_clarification: ClarificationState | None = None
    current_decision: DecisionState | None = None
    last_route: RouteDecision | None = None


def _capture_planning_context(state_store: StateStore) -> _PlanningContext:
    return _PlanningContext(
        current_run=state_store.get_current_run(),
        current_plan=state_store.get_current_plan(),
        current_clarification=state_store.get_current_clarification(),
        current_decision=state_store.get_current_decision(),
        last_route=state_store.get_last_route(),
    )




def _soft_execution_ownership_warning(
    *,
    existing_global_run: RunState | None,
    session_id: str | None,
) -> str | None:
    if (
        existing_global_run is not None
        and existing_global_run.owner_session_id
        and session_id
        and existing_global_run.owner_session_id != session_id
    ):
        return (
            f"Soft ownership warning: overwriting global execution context "
            f"owned by session {existing_global_run.owner_session_id}"
        )
    return None


def _set_execution_run_state(
    state_store: StateStore,
    run_state: RunState,
    *,
    session_id: str | None,
) -> None:
    if state_store.session_id is not None:
        state_store.set_current_run(run_state)
        return
    state_store.set_current_run(_with_global_run_ownership(run_state, session_id=session_id))


def _persist_execution_gate_checkpoint(
    *,
    state_store: StateStore,
    config: RuntimeConfig,
    current_plan: PlanArtifact,
    next_run_state: RunState,
    gate_decision: DecisionState,
) -> tuple[StateStore, list[str]]:
    # Execution-gate checkpoints are part of the single execution truth used by
    # confirm/resume flows. When planning runs inside a session review scope, we
    # still persist the gate checkpoint globally so later recovery does not see
    # a session-scoped execution decision that fails provenance loading.
    notes: list[str] = []
    execution_store = state_store
    if state_store.session_id is not None:
        execution_store = StateStore(config)
        execution_store.ensure()
        owner_warning = _soft_execution_ownership_warning(
            existing_global_run=execution_store.get_current_run(),
            session_id=state_store.session_id,
        )
        if owner_warning is not None:
            notes.append(owner_warning)
        execution_store.set_current_plan(current_plan)
    _set_execution_run_state(
        execution_store,
        next_run_state,
        session_id=state_store.session_id,
    )
    execution_store.set_current_decision(gate_decision)
    if execution_store is not state_store:
        # Once execution truth is promoted globally, the review-scoped run and
        # handoff are stale carriers. Keeping them would let snapshot recovery
        # pick a checkpoint from the session side while a global checkpoint
        # already exists, which could fail-close into a state conflict.
        state_store.clear_current_run()
        state_store.clear_current_handoff()
    return (execution_store, notes)


def _with_global_run_ownership(run_state: RunState, *, session_id: str | None) -> RunState:
    owner_session_id = str(session_id or run_state.owner_session_id or "").strip()
    return RunState(
        run_id=run_state.run_id,
        status=run_state.status,
        stage=run_state.stage,
        route_name=run_state.route_name,
        title=run_state.title,
        created_at=run_state.created_at,
        updated_at=run_state.updated_at,
        plan_id=run_state.plan_id,
        plan_path=run_state.plan_path,
        execution_gate=run_state.execution_gate,
        execution_authorization_receipt=run_state.execution_authorization_receipt,
        request_excerpt=run_state.request_excerpt,
        request_sha1=run_state.request_sha1,
        owner_session_id=owner_session_id,
        owner_host=run_state.owner_host or "runtime",
        owner_run_id=run_state.owner_run_id or run_state.run_id,
        resolution_id=run_state.resolution_id,
    )


def _default_plan_level(decision: RouteDecision) -> str:
    if decision.complexity == "medium":
        return "light"
    return "standard"


def _make_decision_run_state(decision: RouteDecision, decision_state: DecisionState, *, execution_gate: ExecutionGate | None = None) -> RunState:
    now = iso_now()
    return RunState(
        run_id=make_run_id(decision.request_text),
        status="active",
        stage="decision_pending",
        route_name=decision_state.resume_route or decision.route_name,
        title=decision_state.question,
        created_at=now,
        updated_at=now,
        plan_id=None,
        plan_path=None,
        execution_gate=execution_gate,
        request_excerpt=summarize_request_text(decision.request_text),
        request_sha1=stable_request_sha1(decision.request_text),
        owner_session_id="",
        owner_host="",
        owner_run_id="",
    )


def _make_clarification_run_state(
    decision: RouteDecision,
    clarification_state: ClarificationState,
    *,
    execution_gate: ExecutionGate | None = None,
) -> RunState:
    now = iso_now()
    return RunState(
        run_id=make_run_id(decision.request_text),
        status="active",
        stage="clarification_pending",
        route_name=clarification_state.resume_route or decision.route_name,
        title=clarification_state.summary,
        created_at=now,
        updated_at=now,
        plan_id=None,
        plan_path=None,
        execution_gate=execution_gate,
        request_excerpt=summarize_request_text(decision.request_text),
        request_sha1=stable_request_sha1(decision.request_text),
        owner_session_id="",
        owner_host="",
        owner_run_id="",
    )




def _handle_clarification_resume(
    decision: RouteDecision,
    *,
    state_store: StateStore,
    current_clarification: ClarificationState | None,
    current_decision: DecisionState | None,
    current_plan: PlanArtifact | None,
    current_run: RunState | None,
    config: RuntimeConfig,
    kb_artifact: KbArtifact | None,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None]:
    notes: list[str] = []
    if current_clarification is None:
        return (
            _clarification_pending_route(decision, reason="No pending clarification was found"),
            None,
            ["No pending clarification to resume"],
            kb_artifact,
        )

    if decision.active_run_action == "clarification_response_from_state" and has_submitted_clarification(current_clarification):
        resumed_request = merge_clarification_request(current_clarification, current_clarification.response_text or "")
        notes.append("Clarification response restored from structured submission")
    else:
        response = parse_clarification_response(current_clarification, decision.request_text)
        if response.action == "status":
            return (_clarification_pending_route(decision, reason="Clarification is still waiting for factual details"), None, notes, kb_artifact)

        if response.action == "cancel":
            state_store.reset_active_flow()
            return (
                RouteDecision(
                    route_name="cancel_active",
                    request_text=decision.request_text,
                    reason="Clarification cancelled by user",
                    complexity="simple",
                    should_recover_context=True,
                ),
                None,
                ["Clarification cancelled"],
                kb_artifact,
            )

        if response.action != "answer":
            notes.append(response.message or "Invalid clarification response")
            return (_clarification_pending_route(decision, reason="Clarification still requires factual details"), None, notes, kb_artifact)

        resumed_request = merge_clarification_request(current_clarification, response.text)
    if is_develop_callback_state(current_clarification):
        return _resume_from_develop_clarification(
            state_store=state_store,
            current_clarification=current_clarification,
            current_plan=current_plan,
            current_run=current_run,
            resumed_request=resumed_request,
            notes=notes,
            kb_artifact=kb_artifact,
        )

    resumed_route = RouteDecision(
        route_name=current_clarification.resume_route or "plan_only",
        request_text=resumed_request,
        reason="Clarification answered and planning resumed",
        command=None,
        complexity="complex",
        plan_level=current_clarification.requested_plan_level,
        candidate_skill_ids=current_clarification.candidate_skill_ids,
        should_recover_context=False,
        plan_package_policy=current_clarification.plan_package_policy,
        capture_mode=current_clarification.capture_mode,
        artifacts={"planning_resume_source": "clarification"},
    )
    state_store.clear_current_clarification()
    confirmed_decision = (
        current_decision
        if current_decision is not None and current_decision.status == "confirmed" and current_decision.selection is not None
        else None
    )
    planning_route, plan_artifact, planning_notes, kb_artifact = _advance_planning_route(
        resumed_route,
        state_store=state_store,
        config=config,
        kb_artifact=kb_artifact,
        confirmed_decision=confirmed_decision,
        planning_context=_PlanningContext(
            current_run=current_run,
            current_plan=current_plan,
            current_decision=current_decision,
        ),
        plan_materialization_authorized=True,
    )
    notes.extend(planning_notes)
    return (planning_route, plan_artifact, notes, kb_artifact)


def _handle_decision_resume(
    decision: RouteDecision,
    *,
    state_store: StateStore,
    current_decision: DecisionState | None,
    current_plan: PlanArtifact | None,
    current_run: RunState | None,
    config: RuntimeConfig,
    kb_artifact: KbArtifact | None,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None, DecisionState | None]:
    notes: list[str] = []
    if current_decision is None:
        return (
            _decision_pending_route(decision, reason="No pending decision checkpoint was found"),
            None,
            ["No pending decision checkpoint to resume"],
            kb_artifact,
            None,
        )

    if decision.active_run_action == "materialize_confirmed_decision":
        response_action = "materialize"
        response_option_id = None
        response_source = "command_override"
        response_message = ""
    else:
        response = None
        if current_decision.status in {"pending", "collecting", "cancelled", "timed_out"} and has_submitted_decision(current_decision):
            response = response_from_submission(current_decision)
            if response is not None:
                notes.append("Decision response restored from structured submission")
        if response is None:
            response = parse_decision_response(current_decision, decision.request_text)
        response_action = response.action
        response_option_id = response.option_id
        response_source = response.source
        response_message = response.message

    if response_action == "status":
        return (_decision_pending_route(decision, reason="Decision checkpoint is still waiting for confirmation"), None, notes, kb_artifact, None)

    if response_action == "cancel":
        state_store.reset_active_flow()
        return (
            RouteDecision(
                route_name="cancel_active",
                request_text=decision.request_text,
                reason="Decision checkpoint cancelled by user",
                complexity="simple",
                should_recover_context=True,
            ),
            None,
            ["Decision checkpoint cancelled"],
            kb_artifact,
            None,
        )

    if response_action == "invalid":
        notes.append(response_message or "Invalid decision response")
        return (_decision_pending_route(decision, reason="Decision checkpoint still requires a valid selection"), None, notes, kb_artifact, None)

    if response_action == "choose":
        raw_input = decision.request_text
        if current_decision.submission is not None and response_source == current_decision.submission.source:
            raw_input = current_decision.submission.raw_input or raw_input
        current_decision = confirm_decision(
            current_decision,
            option_id=response_option_id or "",
            source=response_source,
            raw_input=raw_input,
        )
        state_store.set_current_decision(current_decision)
        notes.append(f"Decision confirmed: {current_decision.selected_option_id}")

    if current_decision.status != "confirmed" or current_decision.selection is None:
        notes.append("Decision checkpoint has not reached a confirmed state yet")
        return (_decision_pending_route(decision, reason="Decision checkpoint is still pending"), None, notes, kb_artifact, None)

    if is_develop_callback_state(current_decision):
        return _resume_from_develop_decision(
            state_store=state_store,
            current_decision=current_decision,
            current_plan=current_plan,
            current_run=current_run,
            notes=notes,
            kb_artifact=kb_artifact,
        )

    if current_decision.decision_type == ACTIVE_PLAN_BINDING_DECISION_TYPE:
        return _resume_from_active_plan_binding_decision(
            state_store=state_store,
            current_decision=current_decision,
            current_plan=current_plan,
            notes=notes,
            kb_artifact=kb_artifact,
            config=config,
        )

    confirmed_decision = current_decision
    planning_route, plan_artifact, planning_notes, kb_artifact = _advance_planning_route(
        RouteDecision(
            route_name=current_decision.resume_route or "plan_only",
            request_text=current_decision.request_text,
            reason="Decision confirmed and planning resumed",
            command=None,
            complexity="complex",
            plan_level=current_decision.requested_plan_level,
            candidate_skill_ids=current_decision.candidate_skill_ids,
            should_recover_context=False,
            plan_package_policy=current_decision.plan_package_policy,
            capture_mode=current_decision.capture_mode,
        ),
        state_store=state_store,
        config=config,
        kb_artifact=kb_artifact,
        confirmed_decision=current_decision,
        planning_context=_PlanningContext(
            current_run=current_run,
            current_plan=current_plan,
            current_decision=current_decision,
        ),
        plan_materialization_authorized=True,
    )
    notes.extend(planning_notes)
    return (planning_route, plan_artifact, notes, kb_artifact, confirmed_decision)


def _resume_from_develop_clarification(
    *,
    state_store: StateStore,
    current_clarification: ClarificationState,
    current_plan: PlanArtifact | None,
    current_run: RunState | None,
    resumed_request: str,
    notes: list[str],
    kb_artifact: KbArtifact | None,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None]:
    if current_plan is None or current_run is None:
        notes.append("Develop clarification could not resume because the active run context is missing")
        return (_clarification_pending_route(RouteDecision(route_name="clarification_resume", request_text=resumed_request, reason="missing develop context"), reason="Develop clarification still requires an active plan context"), None, notes, kb_artifact)

    resume_after = develop_resume_after(current_clarification.resume_context)
    resume_route = str((current_clarification.resume_context or {}).get("resume_route") or "").strip()
    state_store.clear_current_clarification()
    if resume_route == "plan_only":
        run_state = _copy_run_state(current_run, stage="plan_generated")
        state_store.set_current_run(run_state)
        notes.append("Develop clarification answered; host must review the plan before continuing")
        return (
            RouteDecision(
                route_name="plan_only",
                request_text=resumed_request,
                reason="Develop clarification changed scope and returned the flow to plan review",
                complexity="complex",
                plan_level=current_plan.level,
                candidate_skill_ids=("design", "develop"),
                should_recover_context=False,
                should_create_plan=False,
                capture_mode=current_clarification.capture_mode,
            ),
            current_plan,
            notes,
            kb_artifact,
        )

    run_state = _copy_run_state(
        current_run,
        stage=str(current_clarification.resume_context.get("active_run_stage") or "executing"),
    )
    state_store.set_current_run(run_state)
    notes.append("Develop clarification answered; host-side implementation may continue")
    return (
        RouteDecision(
            route_name="resume_active",
            request_text=resumed_request,
            reason="Develop clarification answered and host-side implementation may continue",
            complexity="medium",
            plan_level=current_plan.level,
            candidate_skill_ids=current_clarification.candidate_skill_ids or ("develop",),
            should_recover_context=True,
            should_create_plan=False,
            capture_mode=current_clarification.capture_mode,
            active_run_action="resume",
        ),
        current_plan,
        notes,
        kb_artifact,
    )




def _resume_from_develop_decision(
    *,
    state_store: StateStore,
    current_decision: DecisionState,
    current_plan: PlanArtifact | None,
    current_run: RunState | None,
    notes: list[str],
    kb_artifact: KbArtifact | None,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None, DecisionState | None]:
    if current_plan is None or current_run is None:
        notes.append("Develop decision could not resume because the active run context is missing")
        return (_decision_pending_route(RouteDecision(route_name="decision_resume", request_text=current_decision.request_text, reason="missing develop context"), reason="Develop decision still requires an active plan context"), None, notes, kb_artifact, None)

    resume_after = develop_resume_after(current_decision.resume_context)
    resume_route = str((current_decision.resume_context or {}).get("resume_route") or "").strip()
    _consume_current_decision(state_store, current_decision)
    if resume_route == "plan_only":
        run_state = _copy_run_state(current_run, stage="plan_generated")
        state_store.set_current_run(run_state)
        notes.append("Develop decision confirmed; host must review the plan before continuing")
        return (
            RouteDecision(
                route_name="plan_only",
                request_text=current_decision.request_text,
                reason="Develop decision changed scope and returned the flow to plan review",
                complexity="complex",
                plan_level=current_plan.level,
                candidate_skill_ids=("design", "develop"),
                should_recover_context=False,
                should_create_plan=False,
                capture_mode=current_decision.capture_mode,
            ),
            current_plan,
            notes,
            kb_artifact,
            current_decision,
        )

    run_state = _copy_run_state(
        current_run,
        stage=str(current_decision.resume_context.get("active_run_stage") or "executing"),
    )
    state_store.set_current_run(run_state)
    notes.append("Develop decision confirmed; host-side implementation may continue")
    return (
        RouteDecision(
            route_name="resume_active",
            request_text=current_decision.request_text,
            reason="Develop decision confirmed and host-side implementation may continue",
            complexity="medium",
            plan_level=current_plan.level,
            candidate_skill_ids=current_decision.candidate_skill_ids or ("develop",),
            should_recover_context=True,
            should_create_plan=False,
            capture_mode=current_decision.capture_mode,
            active_run_action="resume",
        ),
        current_plan,
        notes,
        kb_artifact,
        current_decision,
    )


def _resume_from_active_plan_binding_decision(
    *,
    state_store: StateStore,
    current_decision: DecisionState,
    current_plan: PlanArtifact | None,
    notes: list[str],
    kb_artifact: KbArtifact | None,
    config: RuntimeConfig,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None, DecisionState | None]:
    selected_option_id = current_decision.selected_option_id or ""
    resume_route = current_decision.resume_route or "plan_only"
    _consume_current_decision(state_store, current_decision)
    notes.append(f"Active-plan routing decision confirmed: {selected_option_id or '<unknown>'}")

    resumed_route = RouteDecision(
        route_name=resume_route,
        request_text=current_decision.request_text,
        reason="Active-plan routing decision confirmed and planning resumed",
        complexity="complex",
        plan_level=current_decision.requested_plan_level,
        candidate_skill_ids=current_decision.candidate_skill_ids or ("design", "develop"),
        should_recover_context=False,
        plan_package_policy=current_decision.plan_package_policy,
        capture_mode=current_decision.capture_mode,
        artifacts={
            "active_plan_binding_selection": selected_option_id,
        },
    )
    planning_route, plan_artifact, planning_notes, kb_artifact = _advance_planning_route(
        resumed_route,
        state_store=state_store,
        config=config,
        kb_artifact=kb_artifact,
        planning_context=_PlanningContext(
            current_plan=current_plan,
        ),
        plan_materialization_authorized=True,
    )
    notes.extend(planning_notes)
    return (planning_route, plan_artifact, notes, kb_artifact, current_decision)



def _clarification_pending_route(decision: RouteDecision, *, reason: str) -> RouteDecision:
    return RouteDecision(
        route_name="clarification_pending",
        request_text=decision.request_text,
        reason=reason,
        command=decision.command,
        complexity=decision.complexity,
        plan_level=decision.plan_level,
        candidate_skill_ids=decision.candidate_skill_ids,
        should_recover_context=True,
        should_create_plan=False,
        capture_mode=decision.capture_mode,
        runtime_skill_id=None,
        active_run_action="inspect_clarification",
        artifacts=decision.artifacts,
    )


def _decision_pending_route(decision: RouteDecision, *, reason: str) -> RouteDecision:
    return RouteDecision(
        route_name="decision_pending",
        request_text=decision.request_text,
        reason=reason,
        command=decision.command,
        complexity=decision.complexity,
        plan_level=decision.plan_level,
        candidate_skill_ids=decision.candidate_skill_ids,
        should_recover_context=True,
        should_create_plan=False,
        capture_mode=decision.capture_mode,
        runtime_skill_id=None,
        active_run_action="inspect_decision",
        artifacts=decision.artifacts,
    )


def _plan_review_route(
    decision: RouteDecision,
    *,
    reason: str,
    plan_level: str | None,
) -> RouteDecision:
    return RouteDecision(
        route_name="plan_only",
        request_text=decision.request_text,
        reason=reason,
        command=decision.command,
        complexity=decision.complexity,
        plan_level=plan_level,
        candidate_skill_ids=decision.candidate_skill_ids or ("design", "develop"),
        should_recover_context=False,
        plan_package_policy="none",
        should_create_plan=False,
        capture_mode=decision.capture_mode,
        runtime_skill_id=None,
        artifacts=decision.artifacts,
    )


def _normalized_plan_package_policy(decision: RouteDecision, *, config: RuntimeConfig) -> str:
    """Fail closed: unknown or missing policy → none. No implicit immediate."""
    policy = str(decision.plan_package_policy or "none").strip() or "none"
    return policy


def _copy_run_state(
    current_run: RunState,
    *,
    stage: str,
    execution_gate: ExecutionGate | None | object = None,
) -> RunState:
    next_execution_gate = current_run.execution_gate if execution_gate is None else execution_gate
    return RunState(
        run_id=current_run.run_id,
        status=current_run.status,
        stage=stage,
        route_name=current_run.route_name,
        title=current_run.title,
        created_at=current_run.created_at,
        updated_at=iso_now(),
        plan_id=current_run.plan_id,
        plan_path=current_run.plan_path,
        execution_gate=next_execution_gate,
        execution_authorization_receipt=current_run.execution_authorization_receipt,
        request_excerpt=current_run.request_excerpt,
        request_sha1=current_run.request_sha1,
        owner_session_id=current_run.owner_session_id,
        owner_host=current_run.owner_host,
        owner_run_id=current_run.owner_run_id,
    )


def _advance_planning_route(
    decision: RouteDecision,
    *,
    state_store: StateStore,
    config: RuntimeConfig,
    kb_artifact: KbArtifact | None,
    confirmed_decision: DecisionState | None = None,
    planning_context: _PlanningContext | None = None,
    plan_materialization_authorized: bool = False,
) -> tuple[RouteDecision, PlanArtifact | None, list[str], KbArtifact | None]:
    notes: list[str] = []
    context = planning_context or _capture_planning_context(state_store)
    plan_package_policy = _normalized_plan_package_policy(decision, config=config)
    kb_artifact = _merge_kb_artifacts(kb_artifact, ensure_blueprint_scaffold(config), config=config)

    pending_clarification = _build_route_native_clarification_state(decision, config=config)
    if pending_clarification is not None:
        state_store.set_current_clarification(pending_clarification)
        _preserve_or_clear_current_plan_for_pending_planning_checkpoint(
            decision,
            current_plan=context.current_plan,
            state_store=state_store,
            config=config,
        )
        clarification_gate = evaluate_execution_gate(
            decision=decision,
            plan_artifact=None,
            current_clarification=pending_clarification,
            current_decision=None,
            config=config,
        )
        state_store.set_current_run(
            _make_clarification_run_state(
                decision,
                pending_clarification,
                execution_gate=clarification_gate,
            )
        )
        if confirmed_decision is not None and confirmed_decision.status == "confirmed":
            state_store.set_current_decision(confirmed_decision)
        notes.append(f"Clarification created: {pending_clarification.clarification_id}")
        return (
            _clarification_pending_route(
                decision,
                reason="Detected missing factual details that must be clarified before planning can continue",
            ),
            None,
            notes,
            kb_artifact,
        )

    if confirmed_decision is None:
        current_plan = context.current_plan
        if current_plan is not None and _should_create_active_plan_binding_decision(
            decision,
            current_plan=current_plan,
            config=config,
        ):
            pending_decision = build_active_plan_binding_decision_state(
                decision,
                current_plan=current_plan,
                config=config,
            )
            state_store.set_current_decision(pending_decision)
            current_run = context.current_run
            state_store.set_current_run(
                RunState(
                    run_id=current_run.run_id if current_run is not None else make_run_id(decision.request_text),
                    status="active",
                    stage="decision_pending",
                    route_name=decision.route_name,
                    title=pending_decision.question,
                    created_at=current_run.created_at if current_run is not None else iso_now(),
                    updated_at=iso_now(),
                    plan_id=current_plan.plan_id,
                    plan_path=current_plan.path,
                    execution_gate=current_run.execution_gate if current_run is not None else None,
                    request_excerpt=summarize_request_text(decision.request_text),
                    request_sha1=stable_request_sha1(decision.request_text),
                )
            )
            notes.append(f"Decision checkpoint created: {pending_decision.decision_id}")
            return (
                _decision_pending_route(
                    decision,
                    reason="A non-anchored complex request arrived while another plan is active",
                ),
                None,
                notes,
                kb_artifact,
            )

        pending_decision = _build_route_native_decision_state(decision, config=config)
        if pending_decision is not None:
            state_store.set_current_decision(pending_decision)
            _preserve_or_clear_current_plan_for_pending_planning_checkpoint(
                decision,
                current_plan=context.current_plan,
                state_store=state_store,
                config=config,
            )
            decision_gate = evaluate_execution_gate(
                decision=decision,
                plan_artifact=None,
                current_clarification=None,
                current_decision=pending_decision,
                config=config,
            )
            state_store.set_current_run(
                _make_decision_run_state(
                    decision,
                    pending_decision,
                    execution_gate=decision_gate,
                )
            )
            notes.append(f"Decision checkpoint created: {pending_decision.decision_id}")
            return (
                _decision_pending_route(decision, reason="Detected an explicit design split that requires confirmation"),
                None,
            notes,
            kb_artifact,
        )

    level = decision.plan_level or _default_plan_level(decision)
    selection = _resolve_plan_for_request(
        decision,
        current_plan=context.current_plan,
        state_store=state_store,
        config=config,
        confirmed_decision=confirmed_decision,
    )
    if selection.action == "reuse_existing":
        plan_artifact = selection.plan_artifact
        if plan_artifact is None:
            raise RuntimeError("Plan selection resolved to reuse_existing without an artifact")
        state_store.set_current_plan(plan_artifact)
        if selection.reason_note:
            notes.append(selection.reason_note)
        routed_decision, plan_artifact, gate_notes = _apply_execution_gate_to_plan(
            decision,
            plan_artifact=plan_artifact,
            state_store=state_store,
            config=config,
            decision_context=confirmed_decision,
        )
        notes.extend(gate_notes)
        return (routed_decision, plan_artifact, notes, kb_artifact)

    # Authorization boundary: authorized_only blocks plan materialization
    # unless the Validator explicitly authorized write_plan_package.
    # When blocked, downgrade to consult so handoff reflects reality.
    if plan_package_policy == "authorized_only" and not plan_materialization_authorized:
        notes.append("Plan materialization blocked: policy is authorized_only but no authorization present")
        # Preserve guard artifacts (e.g. direct_edit_guard_kind) from the
        # original decision so the gate contract still surfaces them.
        blocked_artifacts: dict[str, Any] = {}
        orig_artifacts = decision.artifacts or {}
        for key in ("entry_guard_reason_code", "direct_edit_guard_kind", "direct_edit_guard_trigger"):
            val = orig_artifacts.get(key)
            if val:
                blocked_artifacts[key] = val
        blocked_decision = RouteDecision(
            route_name="consult",
            request_text=decision.request_text,
            reason=f"Plan materialization not authorized (original route: {decision.route_name})",
            complexity=decision.complexity,
            should_recover_context=False,
            plan_package_policy="none",
            artifacts=blocked_artifacts or {},
        )
        return (blocked_decision, None, notes, kb_artifact)

    created = create_plan_scaffold(
        decision.request_text,
        config=config,
        level=level,
        decision_state=confirmed_decision,
    )
    try:
        upsert_plan_entry(
            config=config,
            artifact=created,
            request_text=decision.request_text,
        )
    except PlanRegistryError:
        pass
    state_store.set_current_plan(created)
    kb_artifact = _merge_kb_artifacts(kb_artifact, ensure_blueprint_index(config), config=config)
    notes.extend(
        _created_plan_notes(
            created,
            config=config,
            base_note=_created_plan_base_note(created.path, selection.reason_note),
        )
    )

    routed_decision, plan_artifact, gate_notes = _apply_execution_gate_to_plan(
        decision,
        plan_artifact=created,
        state_store=state_store,
        config=config,
        decision_context=confirmed_decision,
    )
    notes.extend(gate_notes)
    return (routed_decision, plan_artifact, notes, kb_artifact)


def _resolve_plan_for_request(
    decision: RouteDecision,
    *,
    current_plan: PlanArtifact | None,
    state_store: StateStore,
    config: RuntimeConfig,
    confirmed_decision: DecisionState | None,
) -> _PlanSelection:
    active_plan_binding_selection = str(decision.artifacts.get("active_plan_binding_selection") or "").strip()

    if confirmed_decision is not None:
        if confirmed_decision.decision_type == ACTIVE_PLAN_BINDING_DECISION_TYPE:
            selected_option_id = confirmed_decision.selected_option_id or ""
            if selected_option_id == ACTIVE_PLAN_ATTACH_OPTION_ID and current_plan is not None:
                return _PlanSelection(
                    action="reuse_existing",
                    plan_artifact=current_plan,
                    reason_note=f"Attached the request back to active plan {current_plan.path} after decision confirmation",
                )
            if selected_option_id == ACTIVE_PLAN_NEW_OPTION_ID or current_plan is None:
                return _PlanSelection(
                    action="create_new",
                    reason_note="after active-plan routing confirmation",
                )

        if current_plan is not None:
            return _PlanSelection(
                action="reuse_existing",
                plan_artifact=current_plan,
                reason_note=f"Reused active plan {current_plan.path} after decision confirmation",
            )
        return _PlanSelection(
            action="create_new",
            reason_note="after decision confirmation",
        )

    explicit_plan = find_plan_by_request_reference(decision.request_text, config=config)
    explicit_new_plan = request_explicitly_wants_new_plan(decision.request_text)

    if active_plan_binding_selection == ACTIVE_PLAN_NEW_OPTION_ID:
        return _PlanSelection(
            action="create_new",
            reason_note="(selected new-plan routing)",
        )

    if explicit_plan is not None:
        if current_plan is not None and explicit_plan.plan_id == current_plan.plan_id:
            return _PlanSelection(
                action="reuse_existing",
                plan_artifact=current_plan,
                reason_note=f"Reused active plan {current_plan.path} (explicit self-reference)",
            )
        return _PlanSelection(
            action="reuse_existing",
            plan_artifact=explicit_plan,
            reason_note=f"Rebound planning context to existing plan {explicit_plan.path} (explicit plan reference)",
        )

    if explicit_new_plan:
        return _PlanSelection(
            action="create_new",
            reason_note="(explicit new-plan request)",
        )

    if current_plan is not None:
        if active_plan_binding_selection == ACTIVE_PLAN_ATTACH_OPTION_ID:
            return _PlanSelection(
                action="reuse_existing",
                plan_artifact=current_plan,
                reason_note=f"Reused active plan {current_plan.path} (selected current-plan routing)",
            )
        if _request_anchors_current_plan(decision.request_text, current_plan=current_plan):
            return _PlanSelection(
                action="reuse_existing",
                plan_artifact=current_plan,
                reason_note=f"Reused active plan {current_plan.path} (implicit current-plan anchor)",
            )
        return _PlanSelection(
            action="reuse_existing",
            plan_artifact=current_plan,
            reason_note=f"Reused active plan {current_plan.path} under strict single-active-plan policy",
        )

    return _PlanSelection(
        action="create_new",
        reason_note="",
    )


def _created_plan_notes(created: PlanArtifact, *, config: RuntimeConfig, base_note: str) -> list[str]:
    notes = [base_note]
    priority_note = priority_note_for_plan(
        config=config,
        plan_id=created.plan_id,
        language=config.language,
    )
    if priority_note:
        notes.append(encode_priority_note_event(priority_note))
    return notes


def _created_plan_base_note(plan_path: str, reason_note: str) -> str:
    base = f"Plan scaffold created at {plan_path}"
    if reason_note:
        return f"{base} {reason_note}"
    return base


def _should_create_active_plan_binding_decision(
    decision: RouteDecision,
    *,
    current_plan: PlanArtifact,
    config: RuntimeConfig,
) -> bool:
    if decision.route_name not in {"plan_only", "workflow", "light_iterate"}:
        return False
    if decision.complexity != "complex":
        return False
    if str(decision.artifacts.get("active_plan_binding_selection") or "").strip():
        return False
    if str(decision.artifacts.get("planning_resume_source") or "").strip():
        return False
    if find_plan_by_request_reference(decision.request_text, config=config) is not None:
        return False
    if request_explicitly_wants_new_plan(decision.request_text):
        return False
    return not _request_anchors_current_plan(decision.request_text, current_plan=current_plan)


def _request_anchors_current_plan(request_text: str, *, current_plan: PlanArtifact) -> bool:
    text = request_text.strip()
    if not text:
        return False

    lowered = text.casefold()
    for anchor in (current_plan.plan_id, current_plan.path, current_plan.title):
        candidate = str(anchor or "").strip().casefold()
        if candidate and candidate in lowered:
            return True

    compact = lowered.replace(" ", "")
    if any(token in compact for token in ("当前plan", "这个plan", "该plan", "activeplan", "currentplan")):
        return True
    if any(token in compact for token in ("当前方案", "这个方案", "该方案")):
        return True
    return any(pattern.search(text) is not None for pattern in _CURRENT_PLAN_ANCHOR_PATTERNS)


def _preserve_or_clear_current_plan_for_pending_planning_checkpoint(
    decision: RouteDecision,
    *,
    current_plan: PlanArtifact | None,
    state_store: StateStore,
    config: RuntimeConfig,
) -> None:
    if current_plan is None:
        return

    explicit_plan = find_plan_by_request_reference(decision.request_text, config=config)
    if explicit_plan is not None and explicit_plan.plan_id != current_plan.plan_id:
        state_store.set_current_plan(explicit_plan)
        return

    if request_explicitly_wants_new_plan(decision.request_text):
        state_store.clear_current_plan()
        return


def _apply_execution_gate_to_plan(
    decision: RouteDecision,
    *,
    plan_artifact: PlanArtifact,
    state_store: StateStore,
    config: RuntimeConfig,
    decision_context: DecisionState | None,
) -> tuple[RouteDecision, PlanArtifact, list[str]]:
    review_route = _plan_review_route(
        decision,
        reason="Plan materialized and is waiting for review before execution",
        plan_level=plan_artifact.level,
    )
    if str(decision.artifacts.get("active_plan_binding_selection") or "").strip() == ACTIVE_PLAN_ATTACH_OPTION_ID:
        gate = ExecutionGate(
            gate_status="blocked",
            blocking_reason="missing_info",
            plan_completion="incomplete",
            next_required_action="continue_host_develop",
            notes=("Attached the new request to the current plan; review and update that plan before execution continues.",),
        )
        state_store.set_current_run(
            make_run_state(
                _plan_review_route(
                    decision,
                    reason="Attached request to the current plan and returned it to plan review",
                    plan_level=decision.plan_level or plan_artifact.level,
                ),
                plan_artifact,
                stage="plan_generated",
                execution_gate=gate,
            )
        )
        return (
            _plan_review_route(
                decision,
                reason="Attached request to the current plan and returned it to plan review",
                plan_level=decision.plan_level or plan_artifact.level,
            ),
            plan_artifact,
            list(gate.notes),
        )

    gate = evaluate_execution_gate(
        decision=decision,
        plan_artifact=plan_artifact,
        current_clarification=None,
        current_decision=decision_context,
        config=config,
    )
    notes = list(gate.notes)

    if decision_context is not None and decision_context.status == "confirmed" and decision_context.selection is not None:
        _consume_current_decision(state_store, decision_context)
        notes.append(f"Decision consumed: {decision_context.decision_id}")

    if gate.gate_status == "decision_required" and gate.blocking_reason != "unresolved_decision":
        next_run_state = RunState(
            run_id=make_run_id(decision.request_text),
            status="active",
            stage="decision_pending",
            route_name=decision.route_name,
            title=plan_artifact.title,
            created_at=plan_artifact.created_at,
            updated_at=iso_now(),
            plan_id=plan_artifact.plan_id,
            plan_path=plan_artifact.path,
            execution_gate=gate,
            request_excerpt=summarize_request_text(decision.request_text),
            request_sha1=stable_request_sha1(decision.request_text),
        )
        gate_decision = _build_route_native_gate_decision_state(
            decision,
            gate=gate,
            current_plan=plan_artifact,
            current_run=next_run_state,
            config=config,
        )
        if gate_decision is not None:
            checkpoint_store, checkpoint_notes = _persist_execution_gate_checkpoint(
                state_store=state_store,
                config=config,
                current_plan=plan_artifact,
                next_run_state=next_run_state,
                gate_decision=gate_decision,
            )
            notes.extend(checkpoint_notes)
            if checkpoint_store is not state_store:
                notes.append("Promoted execution gate checkpoint to global execution truth")
            notes.append(f"Execution gate requested a new decision: {gate_decision.decision_id}")
            return (
                _decision_pending_route(decision, reason="Execution gate found a blocking risk that still requires confirmation"),
                plan_artifact,
                notes,
            )

    stage = "ready_for_execution" if gate.gate_status == "ready" else "plan_generated"
    state_store.set_current_run(
        make_run_state(
            review_route,
            plan_artifact,
            stage=stage,
            execution_gate=gate,
        )
    )
    return (
        review_route,
        plan_artifact,
        notes,
    )


def _consume_current_decision(state_store: StateStore, decision_state: DecisionState) -> None:
    consumed = consume_decision(decision_state)
    state_store.set_current_decision(consumed)
    state_store.clear_current_decision()


def _merge_kb_artifacts(kb_artifact: KbArtifact | None, extra_files: tuple[str, ...], *, config: RuntimeConfig) -> KbArtifact | None:
    if kb_artifact is None and not extra_files:
        return None
    base_files = kb_artifact.files if kb_artifact is not None else ()
    merged_files = tuple(dict.fromkeys((*base_files, *extra_files)))
    return KbArtifact(
        mode=config.kb_init,
        files=merged_files,
        created_at=kb_artifact.created_at if kb_artifact is not None else iso_now(),
    )


def _build_route_native_clarification_state(
    decision: RouteDecision,
    *,
    config: RuntimeConfig,
) -> ClarificationState | None:
    """Route planning-mode clarification through the generic checkpoint contract."""
    clarification_state = build_clarification_state(decision, config=config)
    if clarification_state is None:
        return None
    request = checkpoint_request_from_clarification_state(
        clarification_state,
        config=config,
        source_route=decision.route_name,
    )
    materialized = materialize_checkpoint_request(request.to_dict(), config=config)
    return materialized.clarification_state


def _build_route_native_decision_state(
    decision: RouteDecision,
    *,
    config: RuntimeConfig,
) -> DecisionState | None:
    """Route planning-mode design decisions through the generic checkpoint contract."""
    decision_state = build_decision_state(decision, config=config)
    if decision_state is None:
        return None
    request = checkpoint_request_from_decision_state(
        decision_state,
        source_route=decision.route_name,
    )
    materialized = materialize_checkpoint_request(request.to_dict(), config=config)
    return materialized.decision_state


def _build_route_native_gate_decision_state(
    decision: RouteDecision,
    *,
    gate: ExecutionGate,
    current_plan: PlanArtifact,
    current_run: RunState | None,
    config: RuntimeConfig,
) -> DecisionState | None:
    """Create execution-bound gate decisions without downcasting their phase.

    Generic checkpoint requests only expose public source stages like design /
    develop. Execution-gate decisions are internal execution-bound checkpoints,
    so routing them through the generic materializer would both reject the
    source stage and erase the execution-gate phase we need for liveness.
    """
    decision_state = build_execution_gate_decision_state(
        decision,
        gate=gate,
        current_plan=current_plan,
        config=config,
    )
    if decision_state is None:
        return None
    return replace(
        decision_state,
        resume_context=_execution_gate_decision_resume_context(
            decision_state=decision_state,
            current_plan=current_plan,
            current_run=current_run,
            gate=gate,
        ),
    )


def _execution_gate_decision_resume_context(
    *,
    decision_state: DecisionState,
    current_plan: PlanArtifact,
    current_run: RunState | None,
    gate: ExecutionGate,
) -> Mapping[str, Any]:
    resume_context = dict(decision_state.resume_context)
    resume_context.setdefault("active_run_stage", current_run.stage if current_run is not None else "decision_pending")
    resume_context.setdefault("current_plan_path", current_plan.path)
    resume_context["task_refs"] = list(resume_context.get("task_refs") or [])
    resume_context["changed_files"] = list(resume_context.get("changed_files") or [])
    resume_context.setdefault(
        "working_summary",
        f"Execution gate is waiting for a blocking-risk decision before develop continues: {gate.blocking_reason}",
    )
    resume_context["verification_todo"] = list(resume_context.get("verification_todo") or [])
    resume_context.setdefault("resume_after", "continue_host_develop")
    return resume_context


# ---------------------------------------------------------------------------
# Execution resume: gate evaluation + state mutation for resumed runs
# ---------------------------------------------------------------------------

def _exec_plan_unavailable_route(decision: RouteDecision, *, reason: str) -> RouteDecision:
    return RouteDecision(
        route_name="exec_plan",
        request_text=decision.request_text,
        reason=reason,
        command=decision.command,
        complexity=decision.complexity,
        plan_level=decision.plan_level,
        candidate_skill_ids=decision.candidate_skill_ids or ("develop",),
        should_recover_context=True,
        should_create_plan=False,
        capture_mode=decision.capture_mode,
        runtime_skill_id=None,
        active_run_action="inspect_exec_recovery",
        artifacts=decision.artifacts,
    )


def resolve_execution_resume(
    decision: RouteDecision,
    *,
    execution_store: StateStore,
    current_clarification: Any,
    current_decision: DecisionState | None,
    current_plan: PlanArtifact | None,
    current_run: RunState | None,
    config: RuntimeConfig,
    session_id: str | None,
    receipt_ingredients: dict[str, str] | None = None,
    prior_receipt: ExecutionAuthorizationReceipt | None = None,
) -> tuple[RouteDecision, list[str], ExecutionAuthorizationReceipt | None]:
    """Resolve execution resume: clarification check, gate eval, state mutation.

    Returns (possibly overridden route, notes, updated receipt).
    """
    notes: list[str] = []

    if current_clarification is not None:
        return (
            _clarification_pending_route(
                decision,
                reason="Pending clarification must be answered before execution can continue",
            ),
            ["Blocked execution because clarification is still pending"],
            prior_receipt,
        )

    if current_plan is None:
        if decision.route_name == "exec_plan":
            return (
                _exec_plan_unavailable_route(
                    decision,
                    reason="Advanced exec recovery is unavailable because no active plan or confirmed recovery state exists",
                ),
                ["Rejected ~go because no active plan or confirmed recovery state is available"],
                prior_receipt,
            )
        return decision, ["No active plan available to resume"], prior_receipt

    # Gate evaluation
    confirmed_decision = (
        current_decision
        if current_decision is not None
        and current_decision.status == "confirmed"
        and current_decision.selection is not None
        else None
    )
    gate = evaluate_execution_gate(
        decision=decision,
        plan_artifact=current_plan,
        current_clarification=None,
        current_decision=confirmed_decision,
        config=config,
    )

    # Receipt: generate after gate eval so gate_status is final truth.
    receipt = prior_receipt
    if receipt_ingredients is not None:
        receipt = ExecutionAuthorizationReceipt.create(
            plan_path=receipt_ingredients["plan_path"],
            plan_revision_digest=receipt_ingredients["revision_digest"],
            gate_status=gate.gate_status,
            action_proposal_id=receipt_ingredients["proposal_id"],
            request_sha1=receipt_ingredients["request_sha1"],
        )
    receipt_dict = (
        receipt.to_dict()
        if receipt is not None
        else (current_run.execution_authorization_receipt if current_run is not None else None)
    )

    # Gate branching + state mutation
    if gate.gate_status == "decision_required" and gate.blocking_reason != "unresolved_decision":
        next_run_state = RunState(
            run_id=current_run.run_id if current_run is not None else make_run_id(decision.request_text),
            status="active",
            stage="decision_pending",
            route_name=decision.route_name,
            title=current_plan.title,
            created_at=current_run.created_at if current_run is not None else current_plan.created_at,
            updated_at=iso_now(),
            plan_id=current_plan.plan_id,
            plan_path=current_plan.path,
            execution_gate=gate,
            execution_authorization_receipt=receipt_dict,
            request_excerpt=summarize_request_text(decision.request_text),
            request_sha1=stable_request_sha1(decision.request_text),
        )
        gate_decision = _build_route_native_gate_decision_state(
            decision,
            gate=gate,
            current_plan=current_plan,
            current_run=next_run_state,
            config=config,
        )
        if gate_decision is not None:
            _set_execution_run_state(execution_store, next_run_state, session_id=session_id)
            execution_store.set_current_decision(gate_decision)
            decision = _decision_pending_route(
                decision,
                reason="Execution gate found a blocking risk that still requires confirmation",
            )
            notes.extend(gate.notes)
            notes.append(f"Execution gate requested a new decision: {gate_decision.decision_id}")
        else:
            notes.append("Execution gate requires a decision before develop can continue")
    elif gate.gate_status != "ready":
        _set_execution_run_state(
            execution_store,
            make_run_state(
                decision,
                current_plan,
                stage="plan_generated",
                execution_gate=gate,
                execution_authorization_receipt=receipt_dict,
            ),
            session_id=session_id,
        )
        notes.extend(gate.notes)
        notes.append("Blocked execution because the execution gate is not ready")
    else:
        _set_execution_run_state(
            execution_store,
            RunState(
                run_id=current_run.run_id if current_run is not None else make_run_id(decision.request_text),
                status="active",
                stage="develop_pending",
                route_name=decision.route_name,
                title=current_plan.title,
                created_at=current_run.created_at if current_run is not None else current_plan.created_at,
                updated_at=iso_now(),
                plan_id=current_plan.plan_id,
                plan_path=current_plan.path,
                execution_gate=gate,
                execution_authorization_receipt=receipt_dict,
                request_excerpt=current_run.request_excerpt if current_run is not None else summarize_request_text(decision.request_text),
                request_sha1=current_run.request_sha1 if current_run is not None else stable_request_sha1(decision.request_text),
            ),
            session_id=session_id,
        )
        notes.extend(gate.notes)
        notes.append("Active run resumed")

    return decision, notes, receipt
