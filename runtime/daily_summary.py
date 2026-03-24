"""Deterministic daily summary generation for the `~summary` route."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import NamedTemporaryFile
from typing import Iterable, Mapping, Sequence

from .models import (
    DailySummaryArtifact,
    SkillActivation,
    SummaryCodeChangeFact,
    SummaryDecisionFact,
    SummaryFacts,
    SummaryGitCommitRef,
    SummaryGitRefs,
    SummaryGoalFact,
    SummaryIssueFact,
    SummaryLessonFact,
    SummaryNextStepFact,
    SummaryQualityChecks,
    SummaryReplaySessionRef,
    SummaryScope,
    SummarySourceRefFile,
    SummarySourceRefs,
    SummarySourceWindow,
)
from .state import StateStore, local_day_start_iso, local_timezone_name

SUMMARY_MD_FILENAME = "summary.md"
SUMMARY_JSON_FILENAME = "summary.json"

_HEADING_RE = re.compile(r"^(#{2,6})\s*(.+?)\s*$")
_TASK_RE = re.compile(r"^\s*-\s*\[(?P<status>[^\]]+)\]\s*(?P<body>.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(?P<body>.+?)\s*$")
_FUNC_RE = re.compile(r"^[+-]\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
_CLASS_RE = re.compile(r"^[+-]\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|:)", re.MULTILINE)

_DECISION_SECTION_KEYWORDS = ("已收敛结论", "关键决策", "Decisions", "Decision", "Converged Decisions")
_LESSON_SECTION_KEYWORDS = (
    "稳定性策略",
    "可复用经验",
    "推荐策略",
    "新增信息的落盘要求",
    "Reusable Lessons",
    "Lessons",
    "Recommended Strategy",
    "Stability Strategy",
    "Persistence Requirements",
)

_SUMMARY_TEXT = {
    "zh-CN": {
        "note_uncommitted": "说明: 默认已纳入未提交改动；replay 仅作为增强输入。",
        "note_existing_summary_invalid": "说明: 检测到旧版摘要文件损坏，已直接重建当前版本。",
        "overview_empty": "今天暂无可提炼事实。",
        "goal_empty": "暂无明确目标记录。",
        "decision_empty": "暂无结构化决策记录。",
        "code_change_empty": "今天没有检测到代码或文档改动。",
        "issue_empty": "今日没有新的阻塞问题。",
        "lesson_empty": "暂无可复用经验沉淀。",
        "next_step_empty": "暂无新的后续事项。",
        "headline_plan_git": "今天围绕当前方案推进了 {count} 项代码或文档变更，并同步沉淀到可复盘摘要。",
        "headline_plan_only": "今天主要围绕当前方案整理了结构化事实，并准备好后续实现与复盘入口。",
        "headline_git_only": "今天检测到 {count} 项代码或文档变更，摘要已按当前工作区汇总。",
        "headline_replay_only": "今天暂无显式代码改动，但已记录可用于复盘的会话轨迹。",
        "headline_fallback": "今天暂无足够的结构化事实，摘要主要基于当前状态文件生成。",
        "decision_doc_reason": "来自当前方案文档中的已收敛结论。",
        "decision_selected_reason": "{reason}（选择: {selected}）",
        "issue_clarification_resolution": "待补充事实信息后恢复主链路。",
        "issue_decision_resolution": "待用户拍板后继续推进。",
        "issue_gate_summary": "执行门禁当前为 {status} / {reason}",
        "next_run_stage": "继续处理当前运行阶段: {stage}",
        "change_design_doc": "更新方案设计文档，收敛本轮实现边界与数据契约。",
        "change_tasks_doc": "更新任务清单，补齐实施顺序与验收口径。",
        "change_blueprint_doc": "同步蓝图文档，收口长期口径。",
        "change_test_runtime": "补充或调整自动化测试，锁定运行时行为。",
        "change_runtime_models_facade_with_names": "调整 runtime models facade: {names}。",
        "change_runtime_models_facade": "调整 runtime models facade，固定公开 re-export surface。",
        "change_runtime_models_internal_with_names": "调整 runtime 内部 models 模块: {names}。",
        "change_runtime_models_internal": "调整 runtime 内部 models 模块，拆分契约实现边界。",
        "change_runtime_bundle_smoke": "调整 bundle smoke 测试，保持对外测试路径兼容。",
        "change_runtime_test_suite": "拆分 repo-local runtime 测试套件，收敛 discover 入口与共享 support。",
        "change_runtime_models_with_names": "扩展运行时模型契约: {names}。",
        "change_runtime_models": "扩展运行时模型契约，补齐结构化事实字段。",
        "change_runtime_output": "调整用户可见输出，补齐时间尾注与摘要渲染。",
        "change_runtime_engine": "接入运行时主链路改动，补齐摘要生成或状态推进逻辑。",
        "change_runtime_router": "调整路由分类逻辑，补齐命令入口或分流规则。",
        "change_python_with_names": "调整 Python 模块实现: {names}。",
        "change_python": "调整 Python 模块实现。",
        "change_markdown": "更新说明文档或方案文档。",
        "change_generic": "记录 {change_type} 变更。",
        "reason_sopify": "保证当前方案、蓝图和任务状态与真实实现保持一致。",
        "reason_runtime": "把设计口径落到实际 runtime 主链路，避免后续依赖聊天上下文。",
        "reason_tests": "为新增行为补保护，避免后续回归破坏。",
        "reason_commit": "延续今日提交方向: {commit_title}",
        "reason_generic": "纳入今天、当前工作区的真实改动。",
    },
    "en-US": {
        "note_uncommitted": "Note: uncommitted changes are included by default; replay is only an optional enhancer.",
        "note_existing_summary_invalid": "Note: an invalid prior summary was detected and rebuilt in place.",
        "overview_empty": "No summary facts were collected for today.",
        "goal_empty": "No goal facts were collected.",
        "decision_empty": "No structured decisions were collected.",
        "code_change_empty": "No code or doc changes were detected today.",
        "issue_empty": "No blocking issues were detected today.",
        "lesson_empty": "No reusable lessons were extracted.",
        "next_step_empty": "No follow-up steps were collected.",
        "headline_plan_git": "Today advanced the active plan with {count} code or documentation changes, and rolled them into a replayable summary.",
        "headline_plan_only": "Today focused on structuring facts around the active plan and preparing the next implementation and replay entry points.",
        "headline_git_only": "Today detected {count} code or documentation changes, and summarized them for the current workspace.",
        "headline_replay_only": "Today had no explicit code changes, but replay sessions were available for recap.",
        "headline_fallback": "Today did not have enough structured facts; the summary was generated mainly from current state files.",
        "decision_doc_reason": "Derived from converged decisions in the current plan documents.",
        "decision_selected_reason": "{reason} (selected: {selected})",
        "issue_clarification_resolution": "Resume the main flow after the missing facts are supplied.",
        "issue_decision_resolution": "Continue after the user confirms the pending decision.",
        "issue_gate_summary": "The execution gate is currently {status} / {reason}",
        "next_run_stage": "Continue the current run stage: {stage}",
        "change_design_doc": "Updated the solution-design document to narrow the implementation boundary and data contract.",
        "change_tasks_doc": "Updated the task list to clarify execution order and acceptance criteria.",
        "change_blueprint_doc": "Synchronized blueprint docs to keep the long-term contract aligned.",
        "change_test_runtime": "Added or adjusted automated tests to lock runtime behavior.",
        "change_runtime_models_facade_with_names": "Adjusted the runtime models facade: {names}.",
        "change_runtime_models_facade": "Adjusted the runtime models facade to lock the public re-export surface.",
        "change_runtime_models_internal_with_names": "Adjusted internal runtime model modules: {names}.",
        "change_runtime_models_internal": "Adjusted internal runtime model modules to split implementation boundaries.",
        "change_runtime_bundle_smoke": "Adjusted the bundle smoke test while keeping the exported test path stable.",
        "change_runtime_test_suite": "Split the repo-local runtime test suite and aligned it around discover plus shared support.",
        "change_runtime_models_with_names": "Extended runtime model contracts: {names}.",
        "change_runtime_models": "Extended runtime model contracts with additional structured fact fields.",
        "change_runtime_output": "Adjusted user-facing output to add timestamp tails and summary rendering.",
        "change_runtime_engine": "Updated the runtime main flow to integrate summary generation or state progression logic.",
        "change_runtime_router": "Adjusted route classification to add command entry or dispatch rules.",
        "change_python_with_names": "Adjusted Python module behavior: {names}.",
        "change_python": "Adjusted Python module behavior.",
        "change_markdown": "Updated docs or plan content.",
        "change_generic": "Recorded a {change_type} change.",
        "reason_sopify": "Keeps plans, blueprints, and task state aligned with the real implementation.",
        "reason_runtime": "Moves the design contract into the actual runtime flow so later work does not depend on chat memory.",
        "reason_tests": "Adds regression protection for the new behavior.",
        "reason_commit": "Continues today's commit direction: {commit_title}",
        "reason_generic": "Includes the real changes from today in the current workspace.",
    },
}


@dataclass(frozen=True)
class DailySummaryBuildResult:
    artifact: DailySummaryArtifact
    markdown: str
    generated_files: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class _GitChange:
    path: str
    change_type: str
    commit_title: str = ""


def build_daily_summary(
    *,
    config,
    state_store: StateStore,
    activation: SkillActivation,
) -> DailySummaryBuildResult:
    """Generate and persist the canonical per-day summary for the current workspace."""
    local_day = activation.activated_local_day
    generated_at = activation.activated_at
    timezone_name = activation.timezone or local_timezone_name()
    summary_dir = config.runtime_root / "replay" / "daily" / local_day[:7] / local_day
    summary_json_path = summary_dir / SUMMARY_JSON_FILENAME
    summary_md_path = summary_dir / SUMMARY_MD_FILENAME
    summary_key = f"{local_day}::{config.workspace_root}"

    previous, existing_summary_fallback = _read_existing_summary(summary_json_path)
    revision = previous.revision + 1 if previous is not None and previous.summary_key == summary_key else 1

    plan_files = _collect_plan_file_refs(config=config, local_day=local_day)
    state_files = _collect_state_file_refs(config=config, local_day=local_day)
    handoff_files = _collect_handoff_file_refs(config=config, local_day=local_day)
    replay_sessions = _collect_replay_sessions(config=config, local_day=local_day)
    git_refs, git_changes, git_fallbacks = _collect_git_refs(
        workspace_root=config.workspace_root,
        local_day=local_day,
        generated_summary_dir=summary_dir,
        generated_at=generated_at,
    )

    source_refs = SummarySourceRefs(
        plan_files=tuple(plan_files),
        state_files=tuple(state_files),
        handoff_files=tuple(handoff_files),
        git_refs=git_refs,
        replay_sessions=tuple(replay_sessions),
    )
    evidence = _build_evidence_map(source_refs)

    facts = SummaryFacts(
        headline=_build_headline(
            plan_files=plan_files,
            git_changes=git_changes,
            replay_sessions=replay_sessions,
            language=config.language,
        ),
        goals=tuple(
            _build_goal_facts(
                config=config,
                state_store=state_store,
                plan_files=plan_files,
                evidence=evidence,
            )
        ),
        decisions=tuple(
            _build_decision_facts(
                config=config,
                state_store=state_store,
                plan_files=plan_files,
                evidence=evidence,
                language=config.language,
            )
        ),
        code_changes=tuple(
            _build_code_change_facts(
                workspace_root=config.workspace_root,
                git_changes=git_changes,
                evidence=evidence,
                language=config.language,
            )
        ),
        issues=tuple(
            _build_issue_facts(
                config=config,
                state_store=state_store,
                evidence=evidence,
                language=config.language,
            )
        ),
        lessons=tuple(
            _build_lesson_facts(
                config=config,
                plan_files=plan_files,
                evidence=evidence,
            )
        ),
        next_steps=tuple(
            _build_next_step_facts(
                config=config,
                state_store=state_store,
                plan_files=plan_files,
                evidence=evidence,
                language=config.language,
            )
        ),
    )

    missing_inputs: list[str] = []
    if not plan_files:
        missing_inputs.append("plan_files")
    if not state_files:
        missing_inputs.append("state_files")
    if not git_refs.changed_files:
        missing_inputs.append("git_refs.changed_files")
    fallback_used = list(git_fallbacks)
    if existing_summary_fallback is not None:
        fallback_used.insert(0, existing_summary_fallback)

    artifact = DailySummaryArtifact(
        schema_version="1",
        summary_key=summary_key,
        scope=SummaryScope(
            local_day=local_day,
            workspace_root=str(config.workspace_root),
            workspace_label="Current Workspace" if config.language == "en-US" else "当前工作区",
            timezone=timezone_name,
        ),
        revision=revision,
        generated_at=generated_at,
        source_window=SummarySourceWindow(
            from_ts=local_day_start_iso(local_day),
            to_ts=generated_at,
        ),
        source_refs=source_refs,
        facts=facts,
        quality_checks=SummaryQualityChecks(
            replay_optional=True,
            summary_runs_per_day="1-2",
            required_sections_present=bool(facts.headline and facts.goals and facts.code_changes and facts.next_steps),
            missing_inputs=tuple(missing_inputs),
            fallback_used=tuple(fallback_used),
        ),
    )
    markdown = render_daily_summary_markdown(artifact=artifact, language=config.language)

    _write_json(summary_json_path, artifact.to_dict())
    _write_text(summary_md_path, markdown)
    generated_files = (
        str(summary_json_path.relative_to(config.workspace_root)),
        str(summary_md_path.relative_to(config.workspace_root)),
    )
    notes = []
    if existing_summary_fallback is not None:
        notes.append("Existing summary artifact was invalid and rebuilt in place")
    if git_fallbacks:
        notes.append("Git facts fell back to state/plan-only inputs")
    return DailySummaryBuildResult(
        artifact=artifact,
        markdown=markdown,
        generated_files=generated_files,
        notes=tuple(notes),
    )


def render_daily_summary_markdown(*, artifact: DailySummaryArtifact, language: str) -> str:
    """Render a human-readable summary without duplicating the runtime title."""
    zh = language != "en-US"
    note_lines = [_summary_text(language, "note_uncommitted")]
    if "existing_summary_invalid" in artifact.quality_checks.fallback_used:
        note_lines.append(_summary_text(language, "note_existing_summary_invalid"))
    lines = [
        f"范围: {artifact.scope.local_day} · {artifact.scope.workspace_label}" if zh else f"Scope: {artifact.scope.local_day} · {artifact.scope.workspace_label}",
        f"生成于: {artifact.generated_at}" if zh else f"Generated At: {artifact.generated_at}",
        f"工作区: {artifact.scope.workspace_root}" if zh else f"Workspace: {artifact.scope.workspace_root}",
        *note_lines,
        "",
        "## 今日概览" if zh else "## Daily Overview",
        artifact.facts.headline or _summary_text(language, "overview_empty"),
        "",
        "## 今日目标与上下文" if zh else "## Goals And Context",
        *_render_goal_lines(artifact.facts.goals, language=language),
        "",
        "## 关键决策" if zh else "## Decisions",
        *_render_decision_lines(artifact.facts.decisions, language=language),
        "",
        "## 代码变更详解" if zh else "## Code Changes",
        *_render_code_change_lines(artifact.facts.code_changes, language=language),
        "",
        "## 问题与风险" if zh else "## Issues And Risks",
        *_render_issue_lines(artifact.facts.issues, language=language),
        "",
        "## 可复用经验" if zh else "## Reusable Lessons",
        *_render_lesson_lines(artifact.facts.lessons, language=language),
        "",
        "## 下一步" if zh else "## Next Steps",
        *_render_next_step_lines(artifact.facts.next_steps, language=language),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_goal_lines(items: Sequence[SummaryGoalFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'goal_empty')}"]
    return [f"- {item.summary}" for item in items]


def _render_decision_lines(items: Sequence[SummaryDecisionFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'decision_empty')}"]
    lines: list[str] = []
    for item in items:
        prefix = "原因" if language != "en-US" else "Reason"
        status = "状态" if language != "en-US" else "Status"
        lines.append(f"- {item.summary}")
        lines.append(f"  {prefix}: {item.reason}")
        lines.append(f"  {status}: {item.status}")
    return lines


def _render_code_change_lines(items: Sequence[SummaryCodeChangeFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'code_change_empty')}"]
    lines: list[str] = []
    for item in items:
        change_label = "变更" if language != "en-US" else "Change"
        reason_label = "原因" if language != "en-US" else "Reason"
        verify_label = "验证" if language != "en-US" else "Verification"
        lines.append(f"- [{item.change_type}] {item.path}")
        lines.append(f"  {change_label}: {item.summary}")
        lines.append(f"  {reason_label}: {item.reason}")
        lines.append(f"  {verify_label}: {item.verification}")
    return lines


def _render_issue_lines(items: Sequence[SummaryIssueFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'issue_empty')}"]
    lines: list[str] = []
    for item in items:
        status_label = "状态" if language != "en-US" else "Status"
        resolution_label = "处理" if language != "en-US" else "Resolution"
        lines.append(f"- {item.summary}")
        lines.append(f"  {status_label}: {item.status}")
        if item.resolution:
            lines.append(f"  {resolution_label}: {item.resolution}")
    return lines


def _render_lesson_lines(items: Sequence[SummaryLessonFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'lesson_empty')}"]
    lines: list[str] = []
    for item in items:
        pattern_label = "模式" if language != "en-US" else "Pattern"
        lines.append(f"- {item.summary}")
        lines.append(f"  {pattern_label}: {item.reusable_pattern}")
    return lines


def _render_next_step_lines(items: Sequence[SummaryNextStepFact], *, language: str) -> list[str]:
    if not items:
        return [f"- {_summary_text(language, 'next_step_empty')}"]
    return [f"- [{item.priority}] {item.summary}" for item in items]


def _build_headline(
    *,
    plan_files: Sequence[SummarySourceRefFile],
    git_changes: Sequence[_GitChange],
    replay_sessions: Sequence[SummaryReplaySessionRef],
    language: str,
) -> str:
    if plan_files and git_changes:
        return _summary_text(language, "headline_plan_git", count=len(git_changes))
    if plan_files:
        return _summary_text(language, "headline_plan_only")
    if git_changes:
        return _summary_text(language, "headline_git_only", count=len(git_changes))
    if replay_sessions:
        return _summary_text(language, "headline_replay_only")
    return _summary_text(language, "headline_fallback")


def _build_goal_facts(*, config, state_store: StateStore, plan_files: Sequence[SummarySourceRefFile], evidence: Mapping[str, str]) -> list[SummaryGoalFact]:
    goals: list[SummaryGoalFact] = []
    current_plan = state_store.get_current_plan()
    if current_plan is not None and current_plan.summary.strip():
        goal_ref = evidence.get(current_plan.path) or _first_plan_ref(evidence)
        goals.append(
            SummaryGoalFact(
                fact_id="goal-current-plan",
                summary=current_plan.summary.strip(),
                evidence_refs=(goal_ref,) if goal_ref else (),
            )
        )
    if not goals:
        for ref in plan_files:
            title = _extract_first_title(config.workspace_root / ref.path)
            if title:
                goals.append(
                    SummaryGoalFact(
                        fact_id="goal-plan-title",
                        summary=title,
                        evidence_refs=(evidence.get(ref.path),) if evidence.get(ref.path) else (),
                    )
                )
                break
    return goals[:3]


def _build_decision_facts(
    *,
    config,
    state_store: StateStore,
    plan_files: Sequence[SummarySourceRefFile],
    evidence: Mapping[str, str],
    language: str,
) -> list[SummaryDecisionFact]:
    decisions: list[SummaryDecisionFact] = []
    current_decision = state_store.get_current_decision()
    if current_decision is not None and current_decision.question.strip():
        selected = current_decision.selected_option_id or current_decision.recommended_option_id or current_decision.default_option_id or ""
        reason = current_decision.trigger_reason or current_decision.summary or current_decision.question
        if selected:
            reason = _summary_text(language, "decision_selected_reason", reason=reason, selected=selected)
        evidence_ref = evidence.get(_state_relative_path(config, "current_decision.json"))
        decisions.append(
            SummaryDecisionFact(
                fact_id=current_decision.decision_id or "decision-current",
                summary=current_decision.question,
                reason=reason,
                status=current_decision.status,
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    if decisions:
        return decisions[:5]

    for ref in plan_files:
        text = _safe_read_text(config.workspace_root / ref.path)
        for index, item in enumerate(_extract_section_items(text, keywords=_DECISION_SECTION_KEYWORDS), start=1):
            evidence_ref = evidence.get(ref.path)
            decisions.append(
                SummaryDecisionFact(
                    fact_id=f"decision-doc-{index}",
                    summary=item,
                    reason=_summary_text(language, "decision_doc_reason"),
                    status="confirmed",
                    evidence_refs=(evidence_ref,) if evidence_ref else (),
                )
            )
            if len(decisions) >= 5:
                return decisions
    return decisions


def _build_code_change_facts(
    *,
    workspace_root: Path,
    git_changes: Sequence[_GitChange],
    evidence: Mapping[str, str],
    language: str,
) -> list[SummaryCodeChangeFact]:
    facts: list[SummaryCodeChangeFact] = []
    for change in git_changes[:12]:
        summary = _summarize_changed_file(
            workspace_root=workspace_root,
            path=change.path,
            change_type=change.change_type,
            commit_title=change.commit_title,
            language=language,
        )
        reason = _reason_for_path(change.path, commit_title=change.commit_title, language=language)
        evidence_ref = evidence.get(change.path) or _git_changed_file_evidence(evidence, change.path)
        facts.append(
            SummaryCodeChangeFact(
                path=change.path,
                change_type=change.change_type,
                summary=summary,
                reason=reason,
                verification="not_run",
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    return facts


def _build_issue_facts(
    *,
    config,
    state_store: StateStore,
    evidence: Mapping[str, str],
    language: str,
) -> list[SummaryIssueFact]:
    issues: list[SummaryIssueFact] = []
    current_clarification = state_store.get_current_clarification()
    if current_clarification is not None and current_clarification.status == "pending":
        evidence_ref = evidence.get(_state_relative_path(config, "current_clarification.json"))
        issues.append(
            SummaryIssueFact(
                fact_id=current_clarification.clarification_id or "clarification-pending",
                summary=current_clarification.summary,
                status="open",
                resolution=_summary_text(language, "issue_clarification_resolution"),
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    current_decision = state_store.get_current_decision()
    if current_decision is not None and current_decision.status in {"pending", "collecting"}:
        evidence_ref = evidence.get(_state_relative_path(config, "current_decision.json"))
        issues.append(
            SummaryIssueFact(
                fact_id=current_decision.decision_id or "decision-pending",
                summary=current_decision.summary or current_decision.question,
                status="open",
                resolution=_summary_text(language, "issue_decision_resolution"),
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    current_run = state_store.get_current_run()
    if current_run is not None and current_run.execution_gate is not None and current_run.execution_gate.gate_status != "ready":
        evidence_ref = evidence.get(_state_relative_path(config, "current_run.json"))
        issues.append(
            SummaryIssueFact(
                fact_id=f"gate-{current_run.execution_gate.blocking_reason}",
                summary=_summary_text(
                    language,
                    "issue_gate_summary",
                    status=current_run.execution_gate.gate_status,
                    reason=current_run.execution_gate.blocking_reason,
                ),
                status="open",
                resolution=current_run.execution_gate.next_required_action,
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    return issues[:5]


def _build_lesson_facts(*, config, plan_files: Sequence[SummarySourceRefFile], evidence: Mapping[str, str]) -> list[SummaryLessonFact]:
    lessons: list[SummaryLessonFact] = []
    for ref in plan_files:
        text = _safe_read_text(config.workspace_root / ref.path)
        candidates = _extract_section_items(text, keywords=_LESSON_SECTION_KEYWORDS)
        for index, item in enumerate(candidates, start=1):
            evidence_ref = evidence.get(ref.path)
            lessons.append(
                SummaryLessonFact(
                    fact_id=f"lesson-doc-{index}",
                    summary=item,
                    reusable_pattern=item,
                    evidence_refs=(evidence_ref,) if evidence_ref else (),
                )
            )
            if len(lessons) >= 5:
                return lessons
    return lessons


def _build_next_step_facts(
    *,
    config,
    state_store: StateStore,
    plan_files: Sequence[SummarySourceRefFile],
    evidence: Mapping[str, str],
    language: str,
) -> list[SummaryNextStepFact]:
    next_steps: list[SummaryNextStepFact] = []
    current_run = state_store.get_current_run()
    if current_run is not None and current_run.stage.strip():
        evidence_ref = evidence.get(_state_relative_path(config, "current_run.json"))
        next_steps.append(
            SummaryNextStepFact(
                fact_id="next-run-stage",
                summary=_summary_text(language, "next_run_stage", stage=current_run.stage),
                priority="medium",
                evidence_refs=(evidence_ref,) if evidence_ref else (),
            )
        )
    for ref in plan_files:
        if not ref.path.endswith("tasks.md"):
            continue
        text = _safe_read_text(config.workspace_root / ref.path)
        for index, item in enumerate(_extract_pending_tasks(text), start=1):
            evidence_ref = evidence.get(ref.path)
            next_steps.append(
                SummaryNextStepFact(
                    fact_id=f"next-task-{index}",
                    summary=item,
                    priority="high" if index == 1 else "medium",
                    evidence_refs=(evidence_ref,) if evidence_ref else (),
                )
            )
            if len(next_steps) >= 5:
                return next_steps
    return next_steps[:5]


def _collect_plan_file_refs(*, config, local_day: str) -> list[SummarySourceRefFile]:
    refs: list[SummarySourceRefFile] = []
    for path in sorted(config.plan_root.rglob("*.md")):
        if not path.is_file():
            continue
        if _path_local_day(path) != local_day:
            continue
        refs.append(
            SummarySourceRefFile(
                path=str(path.relative_to(config.workspace_root)),
                kind="plan",
                updated_at=_path_updated_at(path),
            )
        )
    return refs[:20]


def _collect_state_file_refs(*, config, local_day: str) -> list[SummarySourceRefFile]:
    refs: list[SummarySourceRefFile] = []
    for path in sorted(config.state_dir.glob("*.json")):
        if not path.is_file():
            continue
        if _path_local_day(path) != local_day:
            continue
        if path.name == "current_handoff.json":
            continue
        refs.append(
            SummarySourceRefFile(
                path=str(path.relative_to(config.workspace_root)),
                kind="state",
                updated_at=_path_updated_at(path),
            )
        )
    return refs[:20]


def _collect_handoff_file_refs(*, config, local_day: str) -> list[SummarySourceRefFile]:
    path = config.state_dir / "current_handoff.json"
    if not path.exists() or _path_local_day(path) != local_day:
        return []
    return [
        SummarySourceRefFile(
            path=str(path.relative_to(config.workspace_root)),
            kind="handoff",
            updated_at=_path_updated_at(path),
        )
    ]


def _collect_replay_sessions(*, config, local_day: str) -> list[SummaryReplaySessionRef]:
    sessions: list[SummaryReplaySessionRef] = []
    if not config.replay_root.exists():
        return sessions
    for session_dir in sorted(config.replay_root.iterdir()):
        events_path = session_dir / "events.jsonl"
        if not events_path.exists():
            continue
        used = _session_used_for(events_path, local_day=local_day)
        if not used:
            continue
        sessions.append(
            SummaryReplaySessionRef(
                run_id=session_dir.name,
                path=str(session_dir.relative_to(config.workspace_root)),
                used_for="timeline",
            )
        )
    return sessions[:10]


def _collect_git_refs(
    *,
    workspace_root: Path,
    local_day: str,
    generated_summary_dir: Path,
    generated_at: str,
) -> tuple[SummaryGitRefs, list[_GitChange], list[str]]:
    fallbacks: list[str] = []
    if not _is_git_workspace(workspace_root):
        fallbacks.append("git_unavailable")
        return (SummaryGitRefs(base_ref="HEAD"), [], fallbacks)

    status_map = _git_status_map(workspace_root)
    commit_refs, committed_files = _git_commits_for_day(
        workspace_root=workspace_root,
        since_iso=local_day_start_iso(local_day),
        until_iso=generated_at,
    )
    changed_files: list[str] = []
    changes: list[_GitChange] = []
    commit_title_by_file: dict[str, str] = {}
    for commit_ref, files in committed_files:
        for path in files:
            commit_title_by_file.setdefault(path, commit_ref.title)
    seen: set[str] = set()
    generated_root = generated_summary_dir.parent.parent.relative_to(workspace_root)
    excluded_prefix = str(generated_root).rstrip("/") + "/"

    def include(path: str) -> bool:
        # The summary should describe the day's work, not the files generated by `~summary` itself.
        if not path or path.startswith(excluded_prefix):
            return False
        return True

    for path, change_type in status_map.items():
        if include(path) and path not in seen:
            seen.add(path)
            changed_files.append(path)
            changes.append(_GitChange(path=path, change_type=change_type, commit_title=commit_title_by_file.get(path, "")))
    for path in commit_title_by_file:
        if include(path) and path not in seen:
            seen.add(path)
            changed_files.append(path)
            changes.append(_GitChange(path=path, change_type="modified", commit_title=commit_title_by_file[path]))

    return (
        SummaryGitRefs(
            base_ref="HEAD",
            changed_files=tuple(changed_files),
            commits=tuple(commit_refs),
        ),
        changes,
        fallbacks,
    )


def _git_status_map(workspace_root: Path) -> dict[str, str]:
    payload = _run_git(workspace_root, "status", "--porcelain=v1", "--untracked-files=all")
    status_map: dict[str, str] = {}
    for line in payload.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        status_map[path] = _normalize_change_type(code)
    return status_map


def _git_commits_for_day(*, workspace_root: Path, since_iso: str, until_iso: str) -> tuple[list[SummaryGitCommitRef], list[tuple[SummaryGitCommitRef, list[str]]]]:
    output = _run_git(
        workspace_root,
        "log",
        f"--since={since_iso}",
        f"--until={until_iso}",
        "--date=iso-strict",
        "--pretty=format:__COMMIT__%x09%H%x09%s%x09%ad",
        "--name-only",
    )
    commit_refs: list[SummaryGitCommitRef] = []
    file_refs: list[tuple[SummaryGitCommitRef, list[str]]] = []
    current_commit: SummaryGitCommitRef | None = None
    current_files: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if line.startswith("__COMMIT__\t"):
            if current_commit is not None:
                file_refs.append((current_commit, current_files))
            _, sha, title, authored_at = line.split("\t", 3)
            current_commit = SummaryGitCommitRef(sha=sha, title=title, authored_at=authored_at)
            commit_refs.append(current_commit)
            current_files = []
            continue
        if current_commit is not None:
            current_files.append(line.strip())
    if current_commit is not None:
        file_refs.append((current_commit, current_files))
    return (commit_refs[:10], file_refs)


def _normalize_change_type(code: str) -> str:
    if code.startswith("??"):
        return "untracked"
    if "D" in code:
        return "deleted"
    if "A" in code:
        return "added"
    return "modified"


def _summarize_changed_file(*, workspace_root: Path, path: str, change_type: str, commit_title: str, language: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.endswith("/design.md"):
        return _summary_text(language, "change_design_doc")
    if normalized.endswith("/tasks.md"):
        return _summary_text(language, "change_tasks_doc")
    if normalized.startswith(".sopify-skills/blueprint/"):
        return _summary_text(language, "change_blueprint_doc")
    if normalized == "runtime/models.py":
        names = _diff_symbol_excerpt(workspace_root=workspace_root, path=path)
        if names:
            return _summary_text(language, "change_runtime_models_facade_with_names", names=names)
        return _summary_text(language, "change_runtime_models_facade")
    if normalized.startswith("runtime/_models/"):
        names = _diff_symbol_excerpt(workspace_root=workspace_root, path=path)
        if names:
            return _summary_text(language, "change_runtime_models_internal_with_names", names=names)
        return _summary_text(language, "change_runtime_models_internal")
    if normalized == "tests/runtime_test_support.py" or re.match(r"^tests/test_runtime_[^/]+\.py$", normalized):
        return _summary_text(language, "change_runtime_test_suite")
    if normalized == "tests/test_bundle_smoke.py" or normalized == "tests/test_runtime.py" or normalized.endswith("/tests/test_runtime.py"):
        return _summary_text(language, "change_runtime_bundle_smoke")
    if normalized.endswith("runtime/output.py"):
        return _summary_text(language, "change_runtime_output")
    if normalized.endswith("runtime/engine.py"):
        return _summary_text(language, "change_runtime_engine")
    if normalized.endswith("runtime/router.py"):
        return _summary_text(language, "change_runtime_router")
    if normalized.endswith(".py"):
        names = _diff_symbol_excerpt(workspace_root=workspace_root, path=path)
        if names:
            return _summary_text(language, "change_python_with_names", names=names)
        return _summary_text(language, "change_python")
    if normalized.endswith(".md"):
        return _summary_text(language, "change_markdown")
    if commit_title:
        return commit_title
    return _summary_text(language, "change_generic", change_type=change_type)


def _reason_for_path(path: str, *, commit_title: str, language: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith(".sopify-skills/"):
        return _summary_text(language, "reason_sopify")
    if normalized.startswith("runtime/"):
        return _summary_text(language, "reason_runtime")
    if normalized.startswith("tests/"):
        return _summary_text(language, "reason_tests")
    if commit_title:
        return _summary_text(language, "reason_commit", commit_title=commit_title)
    return _summary_text(language, "reason_generic")


def _diff_symbol_excerpt(*, workspace_root: Path, path: str) -> str:
    diff_text = _run_git(workspace_root, "diff", "--cached", "--unified=0", "--", path)
    diff_text += "\n" + _run_git(workspace_root, "diff", "--unified=0", "--", path)
    names = list(dict.fromkeys(_CLASS_RE.findall(diff_text) + _FUNC_RE.findall(diff_text)))
    if not names:
        return ""
    return ", ".join(names[:4])


def _session_used_for(events_path: Path, *, local_day: str) -> bool:
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(payload.get("ts") or "").startswith(local_day):
            return True
        metadata = payload.get("metadata")
        activation = metadata.get("activation") if isinstance(metadata, Mapping) else None
        if isinstance(activation, Mapping) and str(activation.get("activated_local_day") or "") == local_day:
            return True
    return False


def _build_evidence_map(source_refs: SummarySourceRefs) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for index, entry in enumerate(source_refs.plan_files):
        evidence[entry.path] = f"plan_files[{index}]"
    for index, entry in enumerate(source_refs.state_files):
        evidence[entry.path] = f"state_files[{index}]"
    for index, entry in enumerate(source_refs.handoff_files):
        evidence[entry.path] = f"handoff_files[{index}]"
    for index, path in enumerate(source_refs.git_refs.changed_files):
        evidence[path] = f"git_refs.changed_files[{index}]"
    for index, entry in enumerate(source_refs.replay_sessions):
        evidence[entry.path] = f"replay_sessions[{index}]"
    return evidence


def _git_changed_file_evidence(evidence: Mapping[str, str], path: str) -> str | None:
    return evidence.get(path)


def _first_plan_ref(evidence: Mapping[str, str]) -> str | None:
    for key, value in evidence.items():
        if value.startswith("plan_files["):
            return value
    return None


def _extract_first_title(path: Path) -> str:
    text = _safe_read_text(path)
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_section_items(text: str, *, keywords: Iterable[str]) -> list[str]:
    lines = text.splitlines()
    items: list[str] = []
    current_heading = ""
    collecting = False
    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            current_heading = heading_match.group(2).strip()
            collecting = any(keyword in current_heading for keyword in keywords)
            continue
        if not collecting:
            continue
        task_match = _TASK_RE.match(line)
        if task_match:
            body = task_match.group("body").strip()
            if body:
                items.append(body)
            continue
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            body = bullet_match.group("body").strip()
            if body:
                items.append(body)
            continue
        if line.strip() == "":
            continue
        if current_heading:
            # Keep inline explanatory lines from the active section as reusable facts.
            items.append(line.strip())
    return _unique(items)


def _extract_pending_tasks(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        match = _TASK_RE.match(line)
        if not match:
            continue
        if match.group("status").strip().lower() == "x":
            continue
        body = match.group("body").strip()
        if body:
            items.append(body)
    return _unique(items)


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _safe_read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _workspace_matches_current_git_env(workspace_root: Path) -> bool:
    work_tree = (os.environ.get("GIT_WORK_TREE") or "").strip()
    if work_tree:
        try:
            return Path(work_tree).resolve() == workspace_root.resolve()
        except OSError:
            return False

    git_dir = (os.environ.get("GIT_DIR") or "").strip()
    if git_dir:
        try:
            return Path(git_dir).resolve() == (workspace_root / ".git").resolve()
        except OSError:
            return False
    return False


def _git_command_env(workspace_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    if _workspace_matches_current_git_env(workspace_root):
        return env
    # When Sopify runs under a Git hook, Git exports repo-local environment
    # variables. Clear them so `git -C <workspace>` always targets the intended
    # workspace, even if the current process was started from another repo.
    for key in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_GRAFT_FILE",
        "GIT_IMPLICIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_SUPER_PREFIX",
        "GIT_WORK_TREE",
    ):
        env.pop(key, None)
    return env


def _is_git_workspace(workspace_root: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace_root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
            env=_git_command_env(workspace_root),
        )
    except FileNotFoundError:
        return False
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _run_git(workspace_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(workspace_root), *args],
            capture_output=True,
            text=True,
            check=False,
            env=_git_command_env(workspace_root),
        )
    except FileNotFoundError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _path_updated_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().replace(microsecond=0).isoformat()


def _path_local_day(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().date().isoformat()


def _read_existing_summary(path: Path) -> tuple[DailySummaryArtifact | None, str | None]:
    if not path.exists():
        return (None, None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return (None, "existing_summary_invalid")
    if not isinstance(payload, Mapping):
        return (None, "existing_summary_invalid")
    try:
        return (DailySummaryArtifact.from_dict(payload), None)
    except (TypeError, ValueError):
        return (None, "existing_summary_invalid")


def _state_relative_path(config, filename: str) -> str:
    return str((config.state_dir / filename).relative_to(config.workspace_root))


def _summary_text(language: str, key: str, **kwargs: object) -> str:
    locale = "en-US" if language == "en-US" else "zh-CN"
    return _SUMMARY_TEXT[locale][key].format(**kwargs)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)
