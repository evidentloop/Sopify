"""Kernel orchestration entry point (internal, Package B transition).

Guarantees achieved:
  - gate.py / cli.py / plan_orchestrator.py import execute_kernel_turn()
    from this module instead of engine.run_runtime().
  - engine.run_runtime() is a deprecated lazy-import wrapper.
  - No runtime.models bridge consumption — types come from sopify_contracts.

NOT yet achieved:
  - This module still imports ~18 kernel-path helpers and ~11 non-kernel
    route handlers from engine.py.  The engine implementation dependency
    is NOT severed — only the caller-facing symbol is.
  - Package A must: (1) inline kernel helpers into this module,
    (2) delete non-kernel handler imports + their call sites,
    (3) delete engine.py.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Optional

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
from .decision import stale_decision
from .kb import bootstrap_kb
from .skill_registry import SkillRegistry
from .skill_runner import SkillExecutionError, run_runtime_skill

# -- Engine helpers: kernel path (Package A: inline into this module) ---------
# These are shared utilities used by the retained kernel orchestration path.
# They remain in engine.py because non-kernel route handlers also reference
# them, creating cross-dependencies that prevent a clean move without a third
# shared module.  Package A must inline/migrate these FIRST before deleting
# engine.py.
from .engine import (
    _HOST_FACING_TRUTH_KIND_ENGINE_RUNTIME_HANDOFF,
    _build_route_native_gate_decision_state,
    _clarification_pending_route,
    _decision_pending_route,
    _derived_resolution_id,
    _exec_plan_unavailable_route,
    _is_zero_write_conflict_inspect,
    _make_run_id,
    _make_run_state,
    _pending_required_host_action,
    _recovery_store_for_route,
    _resolve_execution_state_store,
    _result_state_store_for_route,
    _set_execution_run_state,
    _snapshot_global_execution_run,
    _snapshot_review_run,
    _with_global_handoff_ownership,
    _with_route_artifacts,
)

# -- Engine helpers: non-kernel route handlers (Package A: delete) ------------
# These implement route-specific dispatch for non-kernel routes (archive,
# planning, cancel, clarification/decision resume, skill execution).
# When Package A deletes engine.py and the leaf modules they depend on,
# the corresponding call sites in execute_kernel_turn() are also removed.
from .engine import (
    _PlanningContext,
    _advance_planning_route,
    _archive_state_store_for_current_plan,
    _augment_generated_files,
    _build_skill_activation,
    _derive_route_from_authorized_proposal,
    _find_skill,
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

    if effective_route.runtime_skill_id is not None:
        skill = _find_skill(skills, effective_route.runtime_skill_id)
        payload = dict((runtime_payloads or {}).get(effective_route.runtime_skill_id, {}))
        if skill is None:
            notes.append(f"Runtime skill not found: {effective_route.runtime_skill_id}")
        elif not payload:
            notes.append(f"Runtime payload missing for skill: {effective_route.runtime_skill_id}")
        else:
            try:
                skill_result = run_runtime_skill(skill, payload=payload)
            except SkillExecutionError as exc:
                notes.append(str(exc))

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

