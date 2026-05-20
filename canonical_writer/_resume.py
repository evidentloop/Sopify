"""Checkpoint resume validation for canonical writer state writes.

Extracted from runtime.checkpoint_request to break the runtime → canonical_writer
dependency cycle.  Only the validation contract needed by StateStore lives here;
the full CheckpointRequest schema and projection logic stays in runtime.
"""

from __future__ import annotations

from typing import Any, Mapping

DEVELOP_RESUME_CONTEXT_REQUIRED_FIELDS = (
    "active_run_stage",
    "current_plan_path",
    "task_refs",
    "changed_files",
    "working_summary",
    "verification_todo",
)
DEVELOP_RESUME_AFTER_ACTIONS = ("continue_host_develop",)


class CheckpointRequestError(ValueError):
    """Raised when a checkpoint request is malformed or incomplete."""


def develop_resume_context_issue(resume_context: Mapping[str, Any] | None) -> str | None:
    """Return a stable issue code when develop resume context is incomplete."""
    if not isinstance(resume_context, Mapping):
        return "develop_resume_context_missing"

    missing_fields = [field for field in DEVELOP_RESUME_CONTEXT_REQUIRED_FIELDS if field not in resume_context]
    if missing_fields:
        return "develop_resume_context_required_fields_missing"
    if not str(resume_context.get("active_run_stage") or "").strip():
        return "develop_resume_context_active_run_stage_missing"
    if not str(resume_context.get("current_plan_path") or "").strip():
        return "develop_resume_context_current_plan_path_missing"
    if not str(resume_context.get("working_summary") or "").strip():
        return "develop_resume_context_working_summary_missing"
    for list_field in ("task_refs", "changed_files", "verification_todo"):
        if not isinstance(resume_context.get(list_field), (list, tuple)):
            return f"develop_resume_context_{list_field}_not_array"
    resume_after = str(resume_context.get("resume_after") or "continue_host_develop")
    if resume_after not in DEVELOP_RESUME_AFTER_ACTIONS:
        return "develop_resume_context_resume_after_invalid"
    return None


def validate_develop_resume_context(
    resume_context: Mapping[str, Any] | None,
    *,
    field_prefix: str = "develop checkpoint_request.resume_context",
) -> None:
    """Raise a domain error when develop resume context violates the contract."""
    issue = develop_resume_context_issue(resume_context)
    if issue is None:
        return

    if not isinstance(resume_context, Mapping):
        raise CheckpointRequestError(f"{field_prefix} is required")
    if issue == "develop_resume_context_required_fields_missing":
        missing_fields = [field for field in DEVELOP_RESUME_CONTEXT_REQUIRED_FIELDS if field not in resume_context]
        raise CheckpointRequestError(
            f"{field_prefix} is missing required fields: {', '.join(missing_fields)}"
        )
    if issue == "develop_resume_context_active_run_stage_missing":
        raise CheckpointRequestError(f"{field_prefix}.active_run_stage is required")
    if issue == "develop_resume_context_current_plan_path_missing":
        raise CheckpointRequestError(f"{field_prefix}.current_plan_path is required")
    if issue == "develop_resume_context_working_summary_missing":
        raise CheckpointRequestError(f"{field_prefix}.working_summary is required")
    if issue == "develop_resume_context_task_refs_not_array":
        raise CheckpointRequestError(f"{field_prefix}.task_refs must be an array")
    if issue == "develop_resume_context_changed_files_not_array":
        raise CheckpointRequestError(f"{field_prefix}.changed_files must be an array")
    if issue == "develop_resume_context_verification_todo_not_array":
        raise CheckpointRequestError(f"{field_prefix}.verification_todo must be an array")
    if issue == "develop_resume_context_resume_after_invalid":
        resume_after = str(resume_context.get("resume_after") or "continue_host_develop")
        raise CheckpointRequestError(
            f"Unsupported {field_prefix}.resume_after: {resume_after or '<missing>'}"
        )
    raise CheckpointRequestError(f"{field_prefix} is invalid")
