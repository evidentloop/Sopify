"""Kernel orchestration entry point (internal).

Guarantees achieved:
  - gate.py imports execute_kernel_turn() from this module instead of
    engine.run_runtime().
  - engine.run_runtime() is a deprecated lazy-import wrapper.
  - No runtime.models bridge consumption — types come from sopify_contracts.
  - Kernel-path helpers are inlined (A1 complete) — no engine.py
    implementation coupling for the core orchestration pipeline.

Remaining engine dependency:
  - 10 non-kernel route handlers still imported from engine.py.
    A2 contract audit determined 9 retain + 1 deleted (skill execution sidecar).
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping, Optional
from uuid import uuid4

# -- Kernel module imports (retained) -----------------------------------------
from .action_intent import (
    ActionProposal,
    ActionValidator,
    DECISION_AUTHORIZE,
    DECISION_REJECT,
    ExecutionAuthorizationReceipt,
    ValidationContext,
    generate_proposal_id,
)
from .config import load_runtime_config
from .context_recovery import recover_context
from .context_snapshot import ContextResolvedSnapshot, resolve_context_snapshot
from .execution_gate import evaluate_execution_gate
from .handoff import build_runtime_handoff
from .router import Router
from .state import stable_request_sha1, summarize_request_text
from canonical_writer import StateStore, iso_now
from canonical_writer.invariants import stamp_handoff_resolution_id
from sopify_contracts.artifacts import KbArtifact, PlanArtifact
from sopify_contracts.core import (
    ExecutionGate, RouteDecision, RunState, RuntimeConfig, SkillMeta,
)
from sopify_contracts.decision import ClarificationState, DecisionState
from sopify_contracts.handoff import (
    RecoveredContext, RuntimeHandoff, RuntimeResult, SkillActivation,
)

# -- Non-kernel leaf imports (Package A: remove these) ------------------------
from .archive_lifecycle import (
    ARCHIVE_STATUS_ALREADY_ARCHIVED,
    ARCHIVE_STATUS_BLOCKED,
    apply_archive_subject,
    archive_status_payload,
    check_archive_subject,
    resolve_archive_subject,
)
from .clarification import stale_clarification
from .decision import build_execution_gate_decision_state, stale_decision
from .kb import bootstrap_kb
from .skill_registry import SkillRegistry

# -- Kernel-path constants & helpers (A1: inlined from engine.py) -------------

_HOST_FACING_TRUTH_KIND_ENGINE_RUNTIME_HANDOFF = "engine_runtime_handoff"
_HOST_FACING_TRUTH_KIND_PROMOTION_GLOBAL_EXECUTION = "promotion_global_execution"
_GLOBAL_EXECUTION_ROUTES = frozenset({"resume_active", "exec_plan", "archive_lifecycle"})
_PROMOTABLE_REVIEW_STAGES = frozenset({"plan_generated", "ready_for_execution", "develop_pending"})


def _new_resolution_id() -> str:
    return uuid4().hex


def _make_run_id(request_text: str) -> str:
    timestamp = iso_now().replace(":", "").replace("-", "")[:15]
    digest = sha1(request_text.encode("utf-8")).hexdigest()[:6]
    return f"{timestamp}_{digest}"


def _make_run_state(
    decision: RouteDecision,
    plan_artifact: PlanArtifact,
    *,
    stage: str = "plan_generated",
    execution_gate: ExecutionGate | None = None,
    execution_authorization_receipt: Mapping[str, Any] | None = None,
) -> RunState:
    now = iso_now()
    return RunState(
        run_id=_make_run_id(decision.request_text),
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


def _with_route_artifacts(decision: RouteDecision, artifacts: Mapping[str, Any]) -> RouteDecision:
    merged = {**dict(decision.artifacts), **dict(artifacts)}
    return replace(decision, artifacts=merged)


def _is_zero_write_conflict_inspect(route: RouteDecision) -> bool:
    return route.route_name == "state_conflict" and route.active_run_action != "abort_conflict"


def _pending_required_host_action(snapshot) -> str:  # noqa: ANN001
    if snapshot.current_clarification is not None and snapshot.current_clarification.status in {"pending", "collecting"}:
        return "answer_questions"
    if snapshot.current_decision is not None and snapshot.current_decision.status in {"pending", "collecting", "confirmed", "cancelled", "timed_out"}:
        return "confirm_decision"
    return ""


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


def _with_global_handoff_ownership(
    handoff: RuntimeHandoff,
    *,
    current_run: RunState | None,
    session_id: str | None,
) -> RuntimeHandoff:
    observability = dict(handoff.observability)
    owner_session_id = ""
    if current_run is not None:
        owner_session_id = current_run.owner_session_id
    if not owner_session_id:
        owner_session_id = str(session_id or "").strip()
    if owner_session_id:
        observability["owner_session_id"] = owner_session_id
    if current_run is not None:
        if current_run.owner_host:
            observability["owner_host"] = current_run.owner_host
        if current_run.owner_run_id:
            observability["owner_run_id"] = current_run.owner_run_id
    return RuntimeHandoff(
        schema_version=handoff.schema_version,
        route_name=handoff.route_name,
        run_id=handoff.run_id,
        plan_id=handoff.plan_id,
        plan_path=handoff.plan_path,
        handoff_kind=handoff.handoff_kind,
        required_host_action=handoff.required_host_action,
        recommended_skill_ids=handoff.recommended_skill_ids,
        artifacts=handoff.artifacts,
        notes=handoff.notes,
        observability=observability,
        resolution_id=handoff.resolution_id,
    )


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


def _derived_resolution_id(
    *,
    resolved_resolution_id: str = "",
    current_run: RunState | None = None,
    current_handoff: RuntimeHandoff | None = None,
) -> str:
    for candidate in (
        resolved_resolution_id,
        current_run.resolution_id if current_run is not None else "",
        current_handoff.resolution_id if current_handoff is not None else "",
    ):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return _new_resolution_id()


def _snapshot_has_global_execution_truth(snapshot: ContextResolvedSnapshot | None) -> bool:
    if snapshot is None:
        return False
    return snapshot.preferred_state_scope == "global" and snapshot.execution_active_run is not None


def _snapshot_global_execution_run(snapshot: ContextResolvedSnapshot | None) -> RunState | None:
    if not _snapshot_has_global_execution_truth(snapshot):
        return None
    return snapshot.execution_active_run


def _snapshot_review_run(snapshot: ContextResolvedSnapshot | None) -> RunState | None:
    if snapshot is None or snapshot.current_run is None:
        return None
    global_run = _snapshot_global_execution_run(snapshot)
    if global_run is not None and snapshot.current_run == global_run:
        return None
    return snapshot.current_run


def _recovery_store_for_route(
    decision: RouteDecision,
    *,
    review_store: StateStore,
    global_store: StateStore,
    snapshot: ContextResolvedSnapshot | None = None,
) -> StateStore:
    if decision.route_name == "state_conflict" and snapshot is not None and snapshot.preferred_state_scope == "global":
        return global_store
    if decision.route_name in _GLOBAL_EXECUTION_ROUTES and _snapshot_has_global_execution_truth(snapshot):
        return global_store
    return review_store


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


def _promote_review_state_to_global_execution(
    *,
    review_store: StateStore,
    global_store: StateStore,
    review_plan: PlanArtifact | None,
    review_run: RunState | None,
    review_handoff: RuntimeHandoff | None,
    existing_global_run: RunState | None,
    session_id: str | None,
    resolution_id: str,
) -> tuple[bool, list[str]]:
    if review_store is global_store:
        return (False, [])
    if review_plan is None or review_run is None:
        return (False, [])
    if review_run.stage not in _PROMOTABLE_REVIEW_STAGES:
        return (False, [])

    notes: list[str] = []
    owner_warning = _soft_execution_ownership_warning(existing_global_run=existing_global_run, session_id=session_id)
    if owner_warning is not None:
        notes.append(owner_warning)

    global_store.set_current_plan(review_plan)
    global_run = _with_global_run_ownership(review_run, session_id=session_id)
    if review_handoff is not None:
        global_run, _ = global_store.set_host_facing_truth(
            run_state=global_run,
            handoff=_with_global_handoff_ownership(
                review_handoff,
                current_run=global_run,
                session_id=session_id,
            ),
            resolution_id=_derived_resolution_id(
                resolved_resolution_id=resolution_id,
                current_run=global_run,
                current_handoff=review_handoff,
            ),
            truth_kind=_HOST_FACING_TRUTH_KIND_PROMOTION_GLOBAL_EXECUTION,
        )
    else:
        global_store.set_current_run(global_run)
    notes.append(f"Promoted session review state to global execution truth from {review_store.root.name}")
    return (True, notes)


def _resolve_execution_state_store(
    decision: RouteDecision,
    *,
    config: RuntimeConfig,
    review_store: StateStore,
    global_store: StateStore,
    recovered_context: RecoveredContext,
    session_id: str | None,
) -> tuple[StateStore, Any, list[str]]:
    global_execution_context = recover_context(
        decision,
        config=config,
        state_store=global_store,
        global_state_store=global_store,
    )
    if global_execution_context.current_run is not None and global_execution_context.current_plan is not None:
        return (global_store, global_execution_context, [])
    promoted, promotion_notes = _promote_review_state_to_global_execution(
        review_store=review_store,
        global_store=global_store,
        review_plan=recovered_context.current_plan,
        review_run=recovered_context.current_run,
        review_handoff=recovered_context.current_handoff,
        existing_global_run=global_execution_context.current_run,
        session_id=session_id,
        resolution_id=recovered_context.resolution_id,
    )
    recovery_store = global_store if promoted else review_store
    recovered = recover_context(
        decision,
        config=config,
        state_store=recovery_store,
        global_state_store=global_store,
    )
    return (recovery_store, recovered, promotion_notes)


def _result_state_store_for_route(
    decision: RouteDecision,
    *,
    review_store: StateStore,
    global_store: StateStore,
    canceled_store: StateStore | None,
    preserved_review_after_cancel: bool = False,
    current_clarification: ClarificationState | None = None,
    current_decision: DecisionState | None = None,
    snapshot: ContextResolvedSnapshot | None = None,
) -> StateStore:
    if canceled_store is not None:
        if canceled_store is global_store and preserved_review_after_cancel:
            return review_store
        return canceled_store
    if decision.route_name == "state_conflict" and snapshot is not None and snapshot.preferred_state_scope == "global":
        return global_store
    if decision.route_name in _GLOBAL_EXECUTION_ROUTES:
        return global_store
    if decision.route_name in {"decision_pending", "decision_resume"}:
        if current_decision is not None and current_decision.phase in {"execution_gate", "develop"}:
            return global_store
        return review_store
    if decision.route_name in {"clarification_pending", "clarification_resume"}:
        if current_clarification is not None and current_clarification.phase == "develop":
            return global_store
        return review_store
    return review_store


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


def _build_route_native_gate_decision_state(
    decision: RouteDecision,
    *,
    gate: ExecutionGate,
    current_plan: PlanArtifact,
    current_run: RunState | None,
    config: RuntimeConfig,
) -> DecisionState | None:
    """Create execution-bound gate decisions without downcasting their phase."""
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


# -- Engine helpers: non-kernel route handlers (A2: audit before removing) ----
# These implement route-specific dispatch for non-kernel routes (archive,
# planning, cancel, clarification/decision resume, activation metadata).
# A2 confirmed all remaining imports are live contract consumers.
from .engine import (
    _PlanningContext,
    _advance_planning_route,
    _archive_state_store_for_current_plan,
    _augment_generated_files,
    _build_skill_activation,
    _derive_route_from_authorized_proposal,
    _handle_cancel_active,
    _handle_clarification_resume,
    _handle_decision_resume,
    _handle_state_conflict,
)


def execute_kernel_turn(
    user_input: str,
    *,
    workspace_root: str | Path = ".",
    global_config_path: str | Path | None = None,
    session_id: str | None = None,
    user_home: Path | None = None,
    runtime_payloads: Optional[Mapping[str, Mapping[str, Any]]] = None,
    action_proposal: ActionProposal | None = None,
) -> RuntimeResult:
    """Execute the kernel orchestration pipeline for a single turn.

    Args:
        user_input: Raw user input.
        workspace_root: Project root.
        global_config_path: Optional global config override.
        user_home: Optional home override for tests.
        runtime_payloads: Optional runtime-skill payload map keyed by skill id.
        action_proposal: Optional ActionProposal from the host LLM. When
            provided the pre-route validator may override or constrain
            the route before the Router runs.

    Returns:
        Standardized runtime result.
    """
    config = load_runtime_config(workspace_root, global_config_path=global_config_path)
    review_store = StateStore(config, session_id=session_id)
    global_store = StateStore(config)
    review_store.ensure()
    global_store.ensure()
    kb_artifact: KbArtifact | None = bootstrap_kb(config)

    skills = SkillRegistry(config, user_home=user_home).discover()
    router = Router(config, state_store=review_store, global_state_store=global_store)
    snapshot = resolve_context_snapshot(
        config=config,
        review_store=review_store,
        global_store=global_store,
    )

    # --- P0: ActionProposal pre-route interceptor ---
    # When the host provides a validated ActionProposal, run it through the
    # ActionValidator *before* the Router.  If the validator returns an
    # authoritative route_override (e.g. "consult"), construct a synthetic
    # RouteDecision and skip Router classification entirely.
    proposal_override_route: RouteDecision | None = None
    plan_materialization_authorized = False
    execution_auth_receipt: ExecutionAuthorizationReceipt | None = None
    _receipt_ingredients: dict[str, str] | None = None
    if action_proposal is not None:
        validator = ActionValidator()
        _run = snapshot.current_run
        _handoff = snapshot.current_handoff
        active_plan_for_validator = snapshot.execution_current_plan or snapshot.current_plan
        required_host_action = getattr(_handoff, "required_host_action", "") or "" if _handoff else ""
        if not required_host_action:
            required_host_action = _pending_required_host_action(snapshot)
        ctx = ValidationContext(
            stage=getattr(_run, "stage", "") or "" if _run else "",
            required_host_action=required_host_action,
            current_plan_path=getattr(active_plan_for_validator, "path", "") or "" if active_plan_for_validator else "",
            state_conflict=snapshot.is_conflict,
            workspace_root=str(config.workspace_root) if config is not None else None,
            existing_receipt=getattr(_run, "execution_authorization_receipt", None) if _run else None,
            current_gate_status=getattr(getattr(_run, "execution_gate", None), "gate_status", None) if _run else None,
        )
        validation_decision = validator.validate(action_proposal, ctx)
        if validation_decision.decision == DECISION_REJECT:
            # P1.5-A: validator explicitly rejected — independent reject surface.
            # No state mutation on reject: stale receipt stays until an explicit
            # re-authorization path (e.g. new planning flow) replaces it.
            proposal_override_route = RouteDecision(
                route_name="proposal_rejected",
                request_text=user_input,
                reason=f"action_proposal_rejected: {validation_decision.reason_code}",
                complexity="simple",
                should_recover_context=False,
                artifacts={"reject_reason_code": validation_decision.reason_code},
            )
        elif validation_decision.route_override:
            proposal_override_route = RouteDecision(
                route_name=validation_decision.route_override,
                request_text=user_input,
                reason=f"action_proposal_validator: {validation_decision.reason_code}",
                complexity="simple",
                should_recover_context=validation_decision.route_override == "archive_lifecycle",
                candidate_skill_ids=("develop", "kb") if validation_decision.route_override == "archive_lifecycle" else (),
                active_run_action="archive" if validation_decision.route_override == "archive_lifecycle" else None,
                artifacts=validation_decision.artifacts,
            )
        # P1.5: derive plan materialization authorization from Validator result.
        if (
            validation_decision.decision == DECISION_AUTHORIZE
            and action_proposal.side_effect == "write_plan_package"
        ):
            plan_materialization_authorized = True
        # P1.5-B: capture receipt ingredients for execute_existing_plan.
        # Actual receipt creation is deferred to after evaluate_execution_gate()
        # so that gate_status reflects the final truth of THIS turn.
        if (
            validation_decision.decision == DECISION_AUTHORIZE
            and action_proposal.action_type == "execute_existing_plan"
            and action_proposal.plan_subject is not None
        ):
            _plan_subject = action_proposal.plan_subject
            _proposal_id = generate_proposal_id(
                action_type=action_proposal.action_type,
                side_effect=action_proposal.side_effect,
                subject_ref=_plan_subject.subject_ref,
                revision_digest=_plan_subject.revision_digest,
                request_hash=stable_request_sha1(user_input),
            )
            _receipt_ingredients = {
                "plan_path": _plan_subject.subject_ref,
                "revision_digest": _plan_subject.revision_digest,
                "proposal_id": _proposal_id,
                "request_sha1": stable_request_sha1(user_input),
            }

    if proposal_override_route is not None:
        classified_route = proposal_override_route
    elif action_proposal is not None and validation_decision.decision == DECISION_AUTHORIZE:
        classified_route = _derive_route_from_authorized_proposal(
            action_proposal, user_input, skills=skills, config=config, snapshot=snapshot,
        )
    else:
        # Legacy text-classification path: used when no ActionProposal is
        # provided (bare text requests).  Will be removed when all hosts
        # emit ActionProposal.
        classified_route = router.classify(user_input, skills=skills, snapshot=snapshot)
    recovered = recover_context(
        classified_route,
        config=config,
        state_store=_recovery_store_for_route(
            classified_route,
            review_store=review_store,
            global_store=global_store,
            snapshot=snapshot,
        ),
        global_state_store=global_store,
        snapshot=snapshot,
    )

    notes: list[str] = list(snapshot.notes)
    plan_artifact: PlanArtifact | None = None
    skill_result: Mapping[str, Any] | None = None
    handoff: RuntimeHandoff | None = None
    activation: SkillActivation | None = None
    generated_files: tuple[str, ...] = ()
    effective_route = classified_route
    registry_changed_hint = False

    current_clarification = recovered.current_clarification
    if (
        current_clarification is not None
        and effective_route.route_name in {"plan_only", "workflow", "light_iterate"}
        and effective_route.route_name not in {"clarification_pending", "clarification_resume"}
    ):
        # A new planning request supersedes the previous pending clarification.
        stale_state = stale_clarification(current_clarification)
        review_store.set_current_clarification(stale_state)
        review_store.clear_current_clarification()
        notes.append(f"Superseded pending clarification: {stale_state.clarification_id}")
        current_clarification = None

    current_decision = recovered.current_decision
    if (
        current_decision is not None
        and effective_route.route_name in {"plan_only", "workflow", "light_iterate"}
        and effective_route.route_name not in {"decision_pending", "decision_resume"}
    ):
        # A new planning request supersedes the previous pending checkpoint.
        stale_state = stale_decision(current_decision)
        review_store.set_current_decision(stale_state)
        review_store.clear_current_decision()
        notes.append(f"Superseded pending decision checkpoint: {stale_state.decision_id}")
        current_decision = None

    canceled_store: StateStore | None = None
    preserved_review_after_cancel = False
    if effective_route.route_name == "cancel_active":
        canceled_store, preserved_review_after_cancel, cancel_notes = _handle_cancel_active(
            effective_route,
            review_store=review_store,
            global_store=global_store,
            review_run=_snapshot_review_run(snapshot),
            global_run=_snapshot_global_execution_run(snapshot),
        )
        notes.extend(cancel_notes)
    elif effective_route.route_name == "archive_lifecycle":
        archive_state_store = _archive_state_store_for_current_plan(
            current_plan=recovered.current_plan,
            review_store=review_store,
            global_store=global_store,
        )
        archive_subject = resolve_archive_subject(
            effective_route.artifacts.get("archive_subject"),
            config=config,
            state_store=archive_state_store,
            current_plan=recovered.current_plan,
        )
        archive_check = check_archive_subject(archive_subject, config=config)
        archive_payload: Mapping[str, Any]
        if archive_check.status == "ready":
            archive_result = apply_archive_subject(archive_subject, config=config, state_store=archive_state_store)
            plan_artifact = archive_result.archived_plan
            registry_changed_hint = archive_result.registry_updated
            if archive_result.kb_artifact is not None:
                kb_artifact = archive_result.kb_artifact
            notes.extend(archive_result.notes)
            archive_payload = archive_status_payload(
                status=archive_result.status,
                subject=archive_subject,
                notes=archive_result.notes,
                state_cleared=archive_result.state_cleared,
                knowledge_sync_result=archive_result.knowledge_sync_result,
            )
        elif archive_check.status == "migration_required":
            notes.extend(archive_check.notes)
            archive_payload = archive_status_payload(
                status=archive_check.status,
                subject=archive_subject,
                notes=archive_check.notes,
            )
        elif archive_check.status == "already_archived":
            notes.extend(archive_check.notes)
            plan_artifact = archive_subject.artifact
            archive_payload = archive_status_payload(
                status=ARCHIVE_STATUS_ALREADY_ARCHIVED,
                subject=archive_subject,
                notes=archive_check.notes,
            )
        else:
            notes.extend(archive_check.notes)
            archive_payload = archive_status_payload(
                status=archive_check.status or ARCHIVE_STATUS_BLOCKED,
                subject=archive_subject,
                notes=archive_check.notes,
                knowledge_sync_result=archive_check.knowledge_sync_result,
            )
        effective_route = _with_route_artifacts(
            effective_route,
            {"archive_lifecycle": archive_payload},
        )
    elif effective_route.route_name == "clarification_resume":
        effective_route, plan_artifact, clarification_notes, kb_artifact = _handle_clarification_resume(
            effective_route,
            state_store=review_store,
            current_clarification=recovered.current_clarification,
            current_decision=recovered.current_decision,
            current_plan=recovered.current_plan,
            current_run=recovered.current_run,
            config=config,
            kb_artifact=kb_artifact,
        )
        notes.extend(clarification_notes)
    elif effective_route.route_name == "decision_resume":
        effective_route, plan_artifact, decision_notes, kb_artifact, _ = _handle_decision_resume(
            effective_route,
            state_store=review_store,
            current_decision=recovered.current_decision,
            current_plan=recovered.current_plan,
            current_run=recovered.current_run,
            config=config,
            kb_artifact=kb_artifact,
        )
        notes.extend(decision_notes)
    elif effective_route.route_name == "state_conflict":
        result_store, snapshot, conflict_notes = _handle_state_conflict(
            effective_route,
            review_store=review_store,
            global_store=global_store,
            snapshot=snapshot,
        )
        recovered = recover_context(
            effective_route,
            config=config,
            state_store=result_store,
            global_state_store=global_store,
            snapshot=snapshot,
        )
        notes.extend(conflict_notes)
    elif effective_route.route_name in {"plan_only", "workflow", "light_iterate"}:
        effective_route, plan_artifact, planning_notes, kb_artifact = _advance_planning_route(
            effective_route,
            state_store=review_store,
            config=config,
            kb_artifact=kb_artifact,
            planning_context=_PlanningContext(
                current_run=recovered.current_run,
                current_plan=recovered.current_plan,
                current_clarification=recovered.current_clarification,
                current_decision=recovered.current_decision,
                last_route=recovered.last_route,
            ),
            plan_materialization_authorized=plan_materialization_authorized,
        )
        notes.extend(planning_notes)
    elif effective_route.route_name in {"resume_active", "exec_plan"}:
        execution_store, execution_recovered, promotion_notes = _resolve_execution_state_store(
            effective_route,
            config=config,
            review_store=review_store,
            global_store=global_store,
            recovered_context=recovered,
            session_id=session_id,
        )
        notes.extend(promotion_notes)
        if execution_recovered.current_clarification is not None:
            effective_route = _clarification_pending_route(
                effective_route,
                reason="Pending clarification must be answered before execution can continue",
            )
            notes.append("Blocked execution because clarification is still pending")
        else:
            current_plan = execution_recovered.current_plan
            if current_plan is None:
                if effective_route.route_name == "exec_plan":
                    effective_route = _exec_plan_unavailable_route(
                        effective_route,
                        reason="Advanced exec recovery is unavailable because no active plan or confirmed recovery state exists",
                    )
                    notes.append("Rejected ~go exec because no active plan or confirmed recovery state is available")
                else:
                    notes.append("No active plan available to resume")
            else:
                gate = evaluate_execution_gate(
                    decision=effective_route,
                    plan_artifact=current_plan,
                    current_clarification=None,
                    current_decision=(
                        execution_recovered.current_decision
                        if execution_recovered.current_decision is not None
                        and execution_recovered.current_decision.status == "confirmed"
                        and execution_recovered.current_decision.selection is not None
                        else None
                    ),
                    config=config,
                )
                # P1.5-B: generate receipt AFTER gate eval so gate_status is final truth.
                if _receipt_ingredients is not None:
                    execution_auth_receipt = ExecutionAuthorizationReceipt.create(
                        plan_path=_receipt_ingredients["plan_path"],
                        plan_revision_digest=_receipt_ingredients["revision_digest"],
                        gate_status=gate.gate_status,
                        action_proposal_id=_receipt_ingredients["proposal_id"],
                        request_sha1=_receipt_ingredients["request_sha1"],
                    )
                # Resolve receipt dict: new receipt wins; otherwise carry forward.
                _prev_run = execution_recovered.current_run
                _receipt_dict = (
                    execution_auth_receipt.to_dict()
                    if execution_auth_receipt is not None
                    else (_prev_run.execution_authorization_receipt if _prev_run is not None else None)
                )
                if gate.gate_status == "decision_required" and gate.blocking_reason != "unresolved_decision":
                    current_run = execution_recovered.current_run
                    next_run_state = RunState(
                        run_id=current_run.run_id if current_run is not None else _make_run_id(effective_route.request_text),
                        status="active",
                        stage="decision_pending",
                        route_name=effective_route.route_name,
                        title=current_plan.title,
                        created_at=current_run.created_at if current_run is not None else current_plan.created_at,
                        updated_at=iso_now(),
                        plan_id=current_plan.plan_id,
                        plan_path=current_plan.path,
                        execution_gate=gate,
                        execution_authorization_receipt=_receipt_dict,
                        request_excerpt=summarize_request_text(effective_route.request_text),
                        request_sha1=stable_request_sha1(effective_route.request_text),
                    )
                    gate_decision = _build_route_native_gate_decision_state(
                        effective_route,
                        gate=gate,
                        current_plan=current_plan,
                        current_run=next_run_state,
                        config=config,
                    )
                    if gate_decision is not None:
                        _set_execution_run_state(
                            execution_store,
                            next_run_state,
                            session_id=session_id,
                        )
                        execution_store.set_current_decision(gate_decision)
                        effective_route = _decision_pending_route(
                            effective_route,
                            reason="Execution gate found a blocking risk that still requires confirmation",
                        )
                        notes.extend(gate.notes)
                        notes.append(f"Execution gate requested a new decision: {gate_decision.decision_id}")
                    else:
                        notes.append("Execution gate requires a decision before develop can continue")
                elif gate.gate_status != "ready":
                    _set_execution_run_state(
                        execution_store,
                        _make_run_state(
                            effective_route,
                            current_plan,
                            stage="plan_generated",
                            execution_gate=gate,
                            execution_authorization_receipt=_receipt_dict,
                        ),
                        session_id=session_id,
                    )
                    notes.extend(gate.notes)
                    notes.append("Blocked execution because the execution gate is not ready")
                else:
                    current_run = execution_recovered.current_run
                    _set_execution_run_state(
                        execution_store,
                        RunState(
                            run_id=current_run.run_id if current_run is not None else _make_run_id(effective_route.request_text),
                            status="active",
                            stage="develop_pending",
                            route_name=effective_route.route_name,
                            title=current_plan.title,
                            created_at=current_run.created_at if current_run is not None else current_plan.created_at,
                            updated_at=iso_now(),
                            plan_id=current_plan.plan_id,
                            plan_path=current_plan.path,
                            execution_gate=gate,
                            execution_authorization_receipt=_receipt_dict,
                            request_excerpt=current_run.request_excerpt if current_run is not None else summarize_request_text(effective_route.request_text),
                            request_sha1=current_run.request_sha1 if current_run is not None else stable_request_sha1(effective_route.request_text),
                        ),
                        session_id=session_id,
                    )
                    notes.extend(gate.notes)
                    notes.append("Active run resumed")
        recovered = execution_recovered

    if not _is_zero_write_conflict_inspect(effective_route):
        review_store.set_last_route(effective_route)

    # Resolve once after all route-side mutations, then let store selection,
    # handoff, and output consume the same fresh post-route truth.
    result_snapshot = resolve_context_snapshot(
        config=config,
        review_store=review_store,
        global_store=global_store,
    )
    result_store = _result_state_store_for_route(
        effective_route,
        review_store=review_store,
        global_store=global_store,
        canceled_store=canceled_store,
        preserved_review_after_cancel=preserved_review_after_cancel,
        current_clarification=result_snapshot.current_clarification,
        current_decision=result_snapshot.current_decision,
        snapshot=result_snapshot,
    )
    resolved_result_context = recover_context(
        effective_route,
        config=config,
        state_store=result_store,
        global_state_store=global_store,
    )

    activation = _build_skill_activation(
        decision=effective_route,
        run_state=resolved_result_context.current_run,
        current_clarification=resolved_result_context.current_clarification,
        current_decision=resolved_result_context.current_decision,
    )

    if effective_route.route_name == "cancel_active":
        handoff = None
    else:
        current_run = resolved_result_context.current_run
        current_plan = plan_artifact or resolved_result_context.current_plan
        if effective_route.route_name == "archive_lifecycle" and current_plan is None:
            # A blocked archive lifecycle may still need to expose the review-scoped plan
            # that prevented archival, even though the host-facing handoff is
            # persisted under the global execution store.
            current_plan = recovered.current_plan
        archive_lifecycle_payload = effective_route.artifacts.get("archive_lifecycle")
        archive_cleared_active_state = (
            isinstance(archive_lifecycle_payload, Mapping)
            and bool(archive_lifecycle_payload.get("state_cleared", False))
        )
        if effective_route.route_name == "archive_lifecycle" and plan_artifact is not None and archive_cleared_active_state:
            # Archiving the active plan clears active-flow state. Archiving another
            # plan must keep the active run/handoff intact and write a receipt.
            current_run = None
            current_plan = plan_artifact
        handoff_context = (
            replace(resolved_result_context, current_run=None)
            if effective_route.route_name == "archive_lifecycle"
            else resolved_result_context
        )
        handoff = build_runtime_handoff(
            config=config,
            decision=effective_route,
            run_id=(
                _make_run_id(effective_route.request_text)
                if effective_route.route_name == "archive_lifecycle"
                else (current_run.run_id if current_run is not None else _make_run_id(effective_route.request_text))
            ),
            resolved_context=handoff_context,
            current_plan=current_plan,
            kb_artifact=kb_artifact,
            skill_result=skill_result,
            notes=notes,
        )
        if handoff is not None:
            if result_store is global_store:
                handoff = _with_global_handoff_ownership(
                    handoff,
                    current_run=current_run,
                    session_id=session_id,
                )
            derived_resolution_id = _derived_resolution_id(
                resolved_resolution_id=resolved_result_context.resolution_id,
                current_run=current_run,
                current_handoff=handoff,
            )
            if effective_route.route_name == "state_conflict":
                if effective_route.active_run_action == "abort_conflict":
                    if current_run is not None:
                        current_run, handoff = result_store.set_host_facing_truth(
                            run_state=current_run,
                            handoff=handoff,
                            resolution_id=derived_resolution_id,
                            truth_kind=_HOST_FACING_TRUTH_KIND_ENGINE_RUNTIME_HANDOFF,
                        )
                    else:
                        # Conflict abort must still persist a stable handoff even
                        # when no run truth survives the cleanup. Otherwise the
                        # gate sees a current-request handoff with no persisted
                        # carrier and fail-closes as current_request_not_persisted.
                        handoff = stamp_handoff_resolution_id(
                            handoff,
                            resolution_id=derived_resolution_id,
                        )
                        result_store.set_current_handoff(handoff)
                else:
                    # Conflict inspection must remain strictly read-only so the
                    # host can inspect the exact skew that triggered routing.
                    pass
            elif effective_route.route_name == "archive_lifecycle":
                handoff = stamp_handoff_resolution_id(
                    handoff,
                    resolution_id=derived_resolution_id,
                )
                if current_run is None:
                    # Archiving the active plan clears global active-flow truth, so
                    # the archive handoff becomes the new host-facing handoff.
                    result_store.clear_current_archive_receipt()
                    result_store.set_current_handoff(handoff)
                else:
                    # Archiving some other plan must not evict the current active
                    # workflow handoff; persist a route-scoped receipt instead.
                    result_store.set_current_archive_receipt(handoff)
            elif current_run is not None:
                current_run, handoff = result_store.set_host_facing_truth(
                    run_state=current_run,
                    handoff=handoff,
                    resolution_id=derived_resolution_id,
                    truth_kind=_HOST_FACING_TRUTH_KIND_ENGINE_RUNTIME_HANDOFF,
                )
            else:
                handoff = stamp_handoff_resolution_id(
                    handoff,
                    resolution_id=derived_resolution_id,
                )
                result_store.set_current_handoff(handoff)
        else:
            result_store.clear_current_handoff()

    generated_files = _augment_generated_files(
        generated_files,
        config=config,
        route_name=effective_route.route_name,
        plan_artifact=plan_artifact,
        notes=tuple(notes),
        registry_changed_hint=registry_changed_hint,
    )
    # Re-resolve once after persisting the handoff so callers observe the
    # stamped host-facing truth (including paired-write resolution ids).
    latest_context = recover_context(
        effective_route,
        config=config,
        state_store=result_store,
        global_state_store=global_store,
    )
    return RuntimeResult(
        route=effective_route,
        recovered_context=latest_context,
        discovered_skills=skills,
        kb_artifact=kb_artifact,
        plan_artifact=plan_artifact,
        skill_result=skill_result,
        handoff=handoff,
        activation=activation,
        generated_files=generated_files,
        notes=tuple(notes),
    )

