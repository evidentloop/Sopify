"""User-facing output rendering for Sopify runtime."""

from __future__ import annotations

import os
import sys

from .clarification import CURRENT_CLARIFICATION_RELATIVE_PATH
from .decision import CURRENT_DECISION_RELATIVE_PATH
from .handoff import CURRENT_HANDOFF_RELATIVE_PATH
from .models import RuntimeResult
from .plan_registry import extract_priority_note_event

_PHASE_LABELS = {
    "zh-CN": {
        "clarification_pending": "需求分析",
        "clarification_resume": "需求分析",
        "plan_only": "方案设计",
        "workflow": "方案设计",
        "light_iterate": "轻量迭代",
        "quick_fix": "快速修复",
        "resume_active": "开发实施",
        "exec_plan": "开发实施",
        "cancel_active": "命令完成",
        "archive_lifecycle": "命令完成",
        "decision_pending": "方案设计",
        "decision_resume": "方案设计",
        "consult": "咨询问答",
        "proposal_rejected": "操作被拒绝",
        "state_conflict": "状态冲突",
        "default": "命令完成",
    },
    "en-US": {
        "clarification_pending": "Requirements Analysis",
        "clarification_resume": "Requirements Analysis",
        "plan_only": "Solution Design",
        "workflow": "Solution Design",
        "light_iterate": "Light Iteration",
        "quick_fix": "Quick Fix",
        "resume_active": "Development",
        "exec_plan": "Development",
        "cancel_active": "Command Complete",
        "archive_lifecycle": "Command Complete",
        "decision_pending": "Solution Design",
        "decision_resume": "Solution Design",
        "consult": "Q&A",
        "proposal_rejected": "Action Rejected",
        "state_conflict": "State Conflict",
        "default": "Command Complete",
    },
}

_LABELS = {
    "zh-CN": {
        "plan": "方案",
        "summary": "概要",
        "route": "路由",
        "reason": "原因",
        "status": "状态",
        "archive": "归档",
        "question": "问题",
        "questions": "问题",
        "options": "选项",
        "decision": "决策",
        "handoff": "交接",
        "conflict_code": "冲突码",
        "quarantined": "隔离",
        "current_plan": "当前方案",
        "stage": "阶段",
        "task_count": "任务数",
        "risk_level": "风险级别",
        "risk": "关键风险",
        "mitigation": "缓解",
        "entry_guard_reason": "守卫原因码",
        "execution_gate": "门禁",
        "missing_facts": "缺口",
        "missing": "未生成",
        "none": "无",
        "cleared": "已清理当前活跃流程",
        "clarification_handoff": "已进入澄清等待，当前请求仍缺进入规划所需的事实信息",
        "workflow_handoff": "已生成方案骨架，后续开发仍需宿主继续",
        "light_handoff": "已生成 light 方案，后续改动仍需宿主继续",
        "quick_fix_handoff": "已准备进入快速修复，请在宿主会话中继续完成代码修改",
        "consult_handoff": "已进入咨询问答，请在宿主会话中继续回答",
        "resume_handoff": "已恢复当前流程，当前 repo-local runtime 未执行 develop bridge",
        "exec_handoff": "已进入 ~go exec 高级恢复入口，当前仅用于检查或恢复已有 plan，不作为普通开发主链路",
        "archive_success": "已完成方案归档",
        "archive_blocked": "当前无法完成归档 lifecycle",
        "default_handoff": "已识别路由，当前 repo-local runtime 未执行后续动作",
        "decision_pending_handoff": "已进入决策确认，正式 plan 会在用户拍板后生成",
        "gate_ready_status": "plan 已通过机器执行门禁，后续可进入执行确认",
        "gate_blocked_status": "plan 已生成，但机器执行门禁仍阻断后续执行",
        "gate_decision_status": "plan 已生成，但仍有阻塞性风险需要继续拍板",
        "next_retry": "检查输入、配置或运行时状态后重试",
        "next_answer_questions": "回复补充信息继续规划，或输入 取消 终止本轮设计",
        "next_plan": "在宿主会话中继续评审或执行方案，或直接回复修改意见",
        "next_workflow": "在宿主会话中继续执行后续阶段，或显式使用 ~go plan 只规划",
        "next_exec": "仅在已有活动 plan 或恢复态时使用 ~go exec；普通开发流继续按宿主会话推进",
        "next_cancel": "如需继续，重新发起 ~go plan 或 ~go",
        "next_archive_success": "请验证 blueprint 索引与 history 归档结果",
        "next_archive_retry": "补齐 blueprint 更新或切换到 metadata-managed plan 后重试",
        "next_consult": "在宿主会话中继续问答，或改成明确变更请求",
        "next_decision": "回复 1/2（或 ~decide choose <option_id>）确认方案，或输入 取消 终止本轮设计",
        "handoff_answer_questions": "已写入 clarification handoff，宿主应先补齐缺失事实信息",
        "handoff_continue_host_develop": "已写入 develop handoff，后续开发需宿主继续",
        "handoff_confirm_decision": "已写入 decision handoff，宿主应先确认当前设计分叉",
        "handoff_continue_host_consult": "已进入咨询问答，请在宿主会话中继续回答",
        "reject_status": "操作被拒绝，请查看原因",
        "next_reject": "操作被拒绝，请查看原因后重新提交",
        "handoff_resolve_state_conflict": "已检测到运行态冲突，当前需先放弃当前协商再继续",
        "state_conflict_detected": "检测到运行态冲突",
        "state_conflict_cleared": "已放弃当前协商并恢复到稳定主线",
        "state_conflict_remaining": "冲突清理后仍有残留冲突，需继续检查",
        "next_state_conflict": "回复 取消 / 强制取消 以放弃当前协商并脱困",
    },
    "en-US": {
        "plan": "Plan",
        "summary": "Summary",
        "route": "Route",
        "reason": "Reason",
        "status": "Status",
        "archive": "Archive",
        "question": "Question",
        "questions": "Questions",
        "options": "Options",
        "decision": "Decision",
        "handoff": "Handoff",
        "conflict_code": "Conflict Code",
        "quarantined": "Quarantined",
        "current_plan": "Current Plan",
        "stage": "Stage",
        "task_count": "Task Count",
        "risk_level": "Risk Level",
        "risk": "Key Risk",
        "mitigation": "Mitigation",
        "entry_guard_reason": "Entry Guard Reason",
        "execution_gate": "Gate",
        "missing_facts": "Missing Facts",
        "missing": "not generated",
        "none": "none",
        "cleared": "active flow cleared",
        "clarification_handoff": "Clarification is pending because the current request still lacks the minimum facts needed for planning",
        "workflow_handoff": "Plan scaffold generated; downstream development still needs the host flow",
        "light_handoff": "Light plan generated; downstream changes still need the host flow",
        "quick_fix_handoff": "Ready for quick fix; continue the code change in the host session",
        "consult_handoff": "Consult mode is ready; continue the answer in the host session",
        "resume_handoff": "Active flow restored; the repo-local runtime has not executed the develop bridge",
        "exec_handoff": "~go exec entered the advanced recovery entry; it is only used to inspect or recover an existing plan, not as the default implementation path",
        "archive_success": "The plan has been archived",
        "archive_blocked": "The archive lifecycle could not be completed",
        "default_handoff": "Route recognized; the repo-local runtime has not executed the downstream action",
        "decision_pending_handoff": "Decision checkpoint is pending; the formal plan will be created after user confirmation",
        "gate_ready_status": "The plan passed the machine execution gate and may move toward execution confirmation",
        "gate_blocked_status": "The plan was generated, but the machine execution gate still blocks downstream execution",
        "gate_decision_status": "The plan was generated, but a blocking risk still needs a decision",
        "next_retry": "Check the input, config, or runtime state and retry",
        "next_answer_questions": "Reply with the missing facts to continue planning, or type cancel to stop this round",
        "next_plan": "Continue plan review or execution in the host session, or reply with feedback",
        "next_workflow": "Continue the downstream stages in the host session, or use ~go plan for planning only",
        "next_exec": "Use ~go exec only when an active plan or recovery state already exists; otherwise continue through the host flow",
        "next_cancel": "Start a new ~go plan or ~go flow when ready",
        "next_archive_success": "Review the blueprint index refresh and the history archive",
        "next_archive_retry": "Update the blueprint or switch to a metadata-managed plan and retry",
        "next_consult": "Continue the discussion in the host session, or restate it as a change request",
        "next_decision": "Reply with 1/2 (or `~decide choose <option_id>`) to confirm, or type cancel to abort this design round",
        "handoff_answer_questions": "clarification handoff written; the host should gather the missing factual details first",
        "handoff_continue_host_develop": "develop handoff written; downstream implementation still needs the host flow",
        "handoff_confirm_decision": "decision handoff written; the host should confirm the current design split first",
        "handoff_continue_host_consult": "Consult mode is ready; continue the answer in the host session",
        "reject_status": "Action rejected; review the reason",
        "next_reject": "Action rejected; review the reason and resubmit",
        "handoff_resolve_state_conflict": "A runtime state conflict was detected; abandon the current negotiation before continuing",
        "state_conflict_detected": "A runtime state conflict was detected",
        "state_conflict_cleared": "The current negotiation was abandoned and the stable mainline was restored",
        "state_conflict_remaining": "Conflict cleanup completed, but another conflict still requires inspection",
        "next_state_conflict": "Reply with cancel / force cancel to abandon the current negotiation and recover",
    },
}

_ROUTE_FAMILIES = {
    "completion": frozenset({"plan_only", "archive_lifecycle", "cancel_active"}),
    "pending": frozenset({"clarification_pending", "decision_pending"}),
    "action": frozenset({"workflow", "light_iterate", "quick_fix", "consult", "resume_active", "exec_plan"}),
    "conflict": frozenset({"state_conflict"}),
    "rejection": frozenset({"proposal_rejected"}),
}

# Canonical family → symbol mapping (P4c-3a.1).
# Hosts can predict the status symbol from the route family alone.
_FAMILY_SYMBOL: dict[str, str] = {
    "completion": "✓",
    "pending": "?",
    "action": "!",
    "conflict": "!",
    "rejection": "!",
}

_ROUTE_TO_FAMILY: dict[str, str] = {
    route: family for family, routes in _ROUTE_FAMILIES.items() for route in routes
}

_GATE_STATUS_DISPLAY = {
    "zh-CN": {"ready": "就绪", "blocked": "阻断", "decision_required": "待决策"},
    "en-US": {"ready": "Ready", "blocked": "Blocked", "decision_required": "Decision Required"},
}

_TITLE_COLORS = {
    "green": "\033[32m",
    "blue": "\033[34m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
}
_RESET = "\033[0m"


def render_runtime_output(
    result: RuntimeResult,
    *,
    brand: str,
    language: str,
    title_color: str = "none",
    use_color: bool | None = None,
) -> str:
    """Render a runtime result into the Sopify summary format."""
    locale = _normalize_language(language)
    labels = _LABELS[locale]
    phase = _phase_label(result, locale)
    status = _status_symbol(result)
    title = _colorize(f"[{brand}] {phase} {status}", title_color=title_color, use_color=use_color)
    changes = _collect_changes(result)
    body = _core_lines(result, locale)
    next_hint = _next_hint(result, locale)

    context_files = _collect_context_files(result)

    lines = [title, ""]
    lines.extend(body)
    if context_files:
        lines.extend(["", f"Context: {len(context_files)} files"])
        lines.extend(f"  - {path}" for path in context_files)
    lines.extend(["", "---", f"Changes: {len(changes)} files"])
    if changes:
        lines.extend(f"  - {path}" for path in changes)
    else:
        lines.append(f"  - {labels['none']}")
    lines.extend(["", f"Next: {next_hint}"])
    return "\n".join(lines)


def render_runtime_error(
    message: str,
    *,
    brand: str,
    language: str,
    title_color: str = "none",
    use_color: bool | None = None,
) -> str:
    """Render a non-runtime exception into the same summary format."""
    locale = _normalize_language(language)
    labels = _LABELS[locale]
    phase = _PHASE_LABELS[locale]["default"]
    title = _colorize(f"[{brand}] {phase} ×", title_color=title_color, use_color=use_color)
    lines = [
        title,
        "",
        f"{labels['reason']}: {message}",
        "",
        "---",
        "Changes: 0 files",
        f"  - {labels['none']}",
        "",
        f"Next: {labels['next_retry']}",
    ]
    return "\n".join(lines)


def _core_lines(result: RuntimeResult, language: str) -> list[str]:
    labels = _LABELS[language]
    route_name = result.route.route_name

    if route_name == "plan_only" and result.plan_artifact is not None:
        current_run = result.recovered_context.current_run
        lines = [
            f"{labels['plan']}: {result.plan_artifact.path}",
            f"{labels['summary']}: {result.plan_artifact.summary}",
        ]
        priority_note = _priority_note(result)
        if priority_note is not None:
            lines.append(priority_note)
        lines.extend(
            [
                f"{labels['stage']}: {current_run.stage if current_run is not None else labels['missing']}",
                _execution_gate_line(result, language),
                f"{labels['handoff']}: {_handoff_label(result, language)}",
            ]
        )
        return lines

    if route_name == "clarification_pending" and result.recovered_context.current_clarification is not None:
        current_clarification = result.recovered_context.current_clarification
        question_text = " | ".join(
            f"[{index}] {question}"
            for index, question in enumerate(current_clarification.questions, start=1)
        )
        missing_facts = ", ".join(current_clarification.missing_facts) or labels["missing"]
        lines = [
            f"{labels['summary']}: {current_clarification.summary}",
            f"{labels['missing_facts']}: {missing_facts}",
            f"{labels['questions']}: {question_text or labels['missing']}",
        ]
        return lines

    if route_name == "decision_pending" and result.recovered_context.current_decision is not None:
        current_decision = result.recovered_context.current_decision
        recommended = current_decision.recommended_option_id or labels["missing"]
        option_text = " | ".join(
            f"[{index}] {option.title}"
            for index, option in enumerate(current_decision.options, start=1)
        )
        lines = [
            f"{labels['question']}: {current_decision.question}",
            f"{labels['options']}: {option_text or labels['missing']}",
            f"{labels['status']}: {_decision_pending_status(language, recommended)}",
        ]
        return lines

    if route_name == "state_conflict":
        conflict = _state_conflict_payload(result)
        quarantined_items = _quarantined_items(result)
        lines: list[str] = []
        if result.route.active_run_action == "abort_conflict" and not conflict:
            lines.append(f"{labels['summary']}: {labels['state_conflict_cleared']}")
        else:
            lines.extend(
                [
                    f"{labels['conflict_code']}: {str(conflict.get('code') or labels['missing'])}",
                    f"{labels['reason']}: {str(conflict.get('message') or _diagnostic_reason(result))}",
                ]
            )
        lines.append(f"{labels['quarantined']}: {len(quarantined_items)}")
        return lines

    if route_name == "archive_lifecycle":
        if result.plan_artifact is not None:
            return [
                f"{labels['archive']}: {result.plan_artifact.path}",
                f"{labels['summary']}: {result.plan_artifact.summary}",
                f"{labels['status']}: {labels['archive_success']}",
            ]
        return [
            f"{labels['status']}: {labels['archive_blocked']}",
            f"{labels['reason']}: {_diagnostic_reason(result)}",
        ]

    if route_name in {"workflow", "light_iterate"} and result.plan_artifact is not None:
        current_run = result.recovered_context.current_run
        lines = [
            f"{labels['plan']}: {result.plan_artifact.path}",
            f"{labels['summary']}: {result.plan_artifact.summary}",
        ]
        priority_note = _priority_note(result)
        if priority_note is not None:
            lines.append(priority_note)
        lines.extend(
            [
                f"{labels['stage']}: {current_run.stage if current_run is not None else labels['missing']}",
                _execution_gate_line(result, language),
                f"{labels['status']}: {_status_message(result, language)}",
            ]
        )
        return lines

    if route_name in {"resume_active", "exec_plan"} and result.recovered_context.current_run is not None:
        current_plan = result.recovered_context.current_plan
        return [
            f"{labels['current_plan']}: {current_plan.path if current_plan is not None else labels['missing']}",
            f"{labels['stage']}: {result.recovered_context.current_run.stage}",
            _execution_gate_line(result, language),
            f"{labels['status']}: {_status_message(result, language)}",
        ]

    if route_name == "cancel_active":
        return [
            f"{labels['status']}: {labels['cleared']}",
        ]

    return [
        f"{labels['status']}: {_status_message(result, language)}",
        f"{labels['reason']}: {_diagnostic_reason(result)}",
    ]


def _collect_changes(result: RuntimeResult) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in result.kb_artifact.files if result.kb_artifact is not None else ():
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    for path in result.plan_artifact.files if result.plan_artifact is not None else ():
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    for path in result.generated_files:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    if result.recovered_context.current_clarification is not None and CURRENT_CLARIFICATION_RELATIVE_PATH not in seen:
        seen.add(CURRENT_CLARIFICATION_RELATIVE_PATH)
        ordered.append(CURRENT_CLARIFICATION_RELATIVE_PATH)
    if result.recovered_context.current_decision is not None and CURRENT_DECISION_RELATIVE_PATH not in seen:
        seen.add(CURRENT_DECISION_RELATIVE_PATH)
        ordered.append(CURRENT_DECISION_RELATIVE_PATH)
    if result.handoff is not None and CURRENT_HANDOFF_RELATIVE_PATH not in seen:
        seen.add(CURRENT_HANDOFF_RELATIVE_PATH)
        ordered.append(CURRENT_HANDOFF_RELATIVE_PATH)
    return ordered


def _collect_context_files(result: RuntimeResult) -> list[str]:
    """Return loaded context files that are not part of generated changes."""
    return list(result.recovered_context.loaded_files)


def _next_hint(result: RuntimeResult, language: str) -> str:
    labels = _LABELS[language]
    if result.handoff is not None:
        return _handoff_next_hint(result, language)
    route_name = result.route.route_name
    if route_name == "archive_lifecycle":
        return labels["next_archive_success"] if result.plan_artifact is not None else labels["next_archive_retry"]
    if route_name in _ROUTE_FAMILIES["pending"]:
        return labels["next_answer_questions"] if route_name == "clarification_pending" else labels["next_decision"]
    if route_name in _ROUTE_FAMILIES["conflict"]:
        return labels["next_state_conflict"]
    if route_name == "exec_plan":
        return labels["next_exec"]
    if route_name == "cancel_active":
        return labels["next_cancel"]
    return labels["next_retry"]


def _status_symbol(result: RuntimeResult) -> str:
    route_name = result.route.route_name
    family = _ROUTE_TO_FAMILY.get(route_name)
    if family is not None:
        symbol = _FAMILY_SYMBOL[family]
        # Completion: missing expected artifact downgrades to warning
        if family == "completion" and route_name in {"plan_only", "archive_lifecycle"} and result.plan_artifact is None:
            return "!"
        # Conflict: fully resolved upgrades to success
        if family == "conflict" and result.route.active_run_action == "abort_conflict" and not _state_conflict_payload(result):
            return "✓"
        return symbol
    # Unclassified route: warning if notes, else success
    return "!" if result.notes else "✓"


def _status_message(result: RuntimeResult, language: str) -> str:
    labels = _LABELS[language]
    route_name = result.route.route_name
    if route_name == "state_conflict":
        if result.route.active_run_action == "abort_conflict":
            return labels["state_conflict_remaining"] if _state_conflict_payload(result) else labels["state_conflict_cleared"]
        return labels["handoff_resolve_state_conflict"]
    if route_name == "proposal_rejected":
        return labels["reject_status"]
    if result.handoff is not None:
        key = f"handoff_{result.handoff.required_host_action}"
        if key in labels:
            return labels[key]
    current_gate = _execution_gate(result)
    if current_gate is not None:
        if current_gate.gate_status == "ready":
            return labels["gate_ready_status"]
        if current_gate.gate_status == "decision_required":
            return labels["gate_decision_status"]
        if current_gate.gate_status == "blocked":
            return labels["gate_blocked_status"]
    if route_name == "workflow":
        return labels["workflow_handoff"]
    if route_name == "light_iterate":
        return labels["light_handoff"]
    if route_name == "clarification_pending":
        return labels["clarification_handoff"]
    if route_name == "quick_fix":
        return labels["quick_fix_handoff"]
    if route_name == "consult":
        return labels["consult_handoff"]
    if route_name == "decision_pending":
        return labels["decision_pending_handoff"]
    if route_name == "resume_active":
        return labels["resume_handoff"]
    if route_name == "exec_plan":
        return labels["exec_handoff"]
    if route_name == "archive_lifecycle":
        return labels["archive_success"] if result.plan_artifact is not None else labels["archive_blocked"]
    return labels["default_handoff"]


def _handoff_label(result: RuntimeResult, language: str) -> str:
    if result.handoff is None:
        return _LABELS[language]["missing"]
    return CURRENT_HANDOFF_RELATIVE_PATH


_HANDOFF_KIND_HINT = {
    "plan": "next_plan",
    "develop": "next_workflow",
    "clarification": "next_answer_questions",
    "decision": "next_decision",
    "consult": "next_consult",
    "reject": "next_reject",
}


def _handoff_next_hint(result: RuntimeResult, language: str) -> str:
    labels = _LABELS[language]
    handoff = result.handoff
    if handoff is None:
        return labels["next_retry"]
    kind = handoff.handoff_kind
    if kind == "archive":
        receipt_status = str((handoff.artifacts or {}).get("archive_receipt_status", "")).strip()
        return labels["next_archive_success"] if receipt_status == "completed" else labels["next_archive_retry"]
    if kind == "state_conflict":
        action = str(handoff.required_host_action or "").strip()
        return labels["next_state_conflict"] if action == "resolve_state_conflict" else labels["next_workflow"]
    hint_key = _HANDOFF_KIND_HINT.get(kind)
    return labels[hint_key] if hint_key else labels["next_retry"]


def _diagnostic_reason(result: RuntimeResult) -> str:
    if result.notes:
        return result.notes[0]
    if result.route.reason:
        return result.route.reason
    return "—"


def _execution_gate(result: RuntimeResult):
    if result.handoff is None:
        return None
    execution_gate = result.handoff.artifacts.get("execution_gate")
    return execution_gate if isinstance(execution_gate, dict) else None


def _priority_note(result: RuntimeResult) -> str | None:
    for note in result.notes:
        structured = extract_priority_note_event(note)
        if structured is not None:
            return structured
        if note.startswith("优先级:") or note.startswith("Priority:"):
            return note
    return None


def _append_entry_guard_reason_line(lines: list[str], *, result: RuntimeResult, language: str) -> None:
    reason_code = _entry_guard_reason_code(result)
    if not reason_code:
        return
    labels = _LABELS[language]
    lines.append(f"{labels['entry_guard_reason']}: {reason_code}")


def _entry_guard_reason_code(result: RuntimeResult) -> str | None:
    handoff = result.handoff
    if handoff is None:
        return None
    value = handoff.artifacts.get("entry_guard_reason_code")
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _execution_gate_line(result: RuntimeResult, language: str) -> str:
    labels = _LABELS[language]
    current_gate = _execution_gate(result)
    if current_gate is None:
        return f"{labels['execution_gate']}: {labels['missing']}"
    if hasattr(current_gate, "gate_status"):
        gate_status = current_gate.gate_status
    else:
        gate_status = str(current_gate.get("gate_status") or "blocked")
    display_map = _GATE_STATUS_DISPLAY.get(language, _GATE_STATUS_DISPLAY["en-US"])
    display = display_map.get(gate_status, display_map["blocked"])
    return f"{labels['execution_gate']}: {display}"


def _decision_pending_status(language: str, recommended_option_id: str) -> str:
    if language == "en-US":
        return f"awaiting confirmation (recommended `{recommended_option_id}`)"
    return f"等待确认（推荐 `{recommended_option_id}`）"


def _phase_label(result: RuntimeResult, language: str) -> str:
    route_name = result.route.route_name
    labels = _PHASE_LABELS[language]
    if route_name in {"clarification_pending", "clarification_resume"}:
        current_clarification = result.recovered_context.current_clarification
        if current_clarification is not None and current_clarification.phase == "develop":
            return labels["resume_active"]
    if route_name in {"decision_pending", "decision_resume"}:
        current_decision = result.recovered_context.current_decision
        if current_decision is not None and current_decision.phase == "develop":
            return labels["resume_active"]
    return labels.get(route_name, labels["default"])


def _state_conflict_payload(result: RuntimeResult) -> dict[str, object]:
    if result.handoff is not None:
        payload = result.handoff.artifacts.get("state_conflict")
        if isinstance(payload, dict):
            return dict(payload)
    return {}


def _quarantined_items(result: RuntimeResult) -> list[dict[str, object]]:
    if result.handoff is not None:
        payload = result.handoff.artifacts.get("quarantined_items")
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
    return []


def _normalize_language(language: str) -> str:
    return "en-US" if language == "en-US" else "zh-CN"


def _colorize(text: str, *, title_color: str, use_color: bool | None) -> str:
    if title_color == "none":
        return text
    if use_color is None:
        use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    if not use_color:
        return text
    color_code = _TITLE_COLORS.get(title_color)
    if color_code is None:
        return text
    return f"{color_code}{text}{_RESET}"
