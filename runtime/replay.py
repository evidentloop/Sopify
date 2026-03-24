"""Replay writer for Sopify runtime."""

from __future__ import annotations

import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping, Optional

from .develop_quality import DEVELOP_REVIEW_STAGES, extract_develop_quality_context, extract_develop_quality_result
from .models import DecisionCheckpoint, DecisionOption, DecisionState, PlanArtifact, ReplayEvent, RouteDecision, RunState, RuntimeConfig

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+"),
)


class ReplayWriter:
    """Append-only replay session writer."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def ensure_session(self, run_id: str) -> Path:
        session_dir = self.config.replay_root / run_id
        session_dir.mkdir(parents=True, exist_ok=True)
        events_path = session_dir / "events.jsonl"
        session_path = session_dir / "session.md"
        breakdown_path = session_dir / "breakdown.md"
        if not events_path.exists():
            events_path.write_text("", encoding="utf-8")
        if not session_path.exists():
            session_path.write_text("# Session\n", encoding="utf-8")
        if not breakdown_path.exists():
            breakdown_path.write_text("# Breakdown\n", encoding="utf-8")
        return session_dir

    def append_event(self, run_id: str, event: ReplayEvent) -> Path:
        session_dir = self.ensure_session(run_id)
        events_path = session_dir / "events.jsonl"
        payload = event.to_dict()
        payload["key_output"] = _redact_text(payload["key_output"])
        payload["decision_reason"] = _redact_text(payload["decision_reason"])
        payload["risk"] = _redact_text(payload["risk"])
        payload["highlights"] = [_redact_text(str(item)) for item in payload.get("highlights", ())]
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return session_dir

    def load_events(self, run_id: str) -> list[ReplayEvent]:
        """Load the persisted replay timeline for re-rendering session documents."""
        session_dir = self.ensure_session(run_id)
        events_path = session_dir / "events.jsonl"
        events: list[ReplayEvent] = []
        for raw_line in events_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, Mapping):
                continue
            events.append(ReplayEvent.from_dict(payload))
        return events

    def render_documents(
        self,
        run_id: str,
        *,
        run_state: Optional[RunState],
        route: RouteDecision,
        plan_artifact: Optional[PlanArtifact],
        events: Iterable[ReplayEvent],
    ) -> Path:
        session_dir = self.ensure_session(run_id)
        events_list = list(events)
        self._write_atomic(
            session_dir / "session.md",
            _render_session_markdown(run_state, route, plan_artifact, events_list),
        )
        self._write_atomic(
            session_dir / "breakdown.md",
            _render_breakdown_markdown(events_list),
        )
        return session_dir

    def _write_atomic(self, path: Path, content: str) -> None:
        with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(path)


def _redact_text(text: str) -> str:
    redacted = text
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub("<REDACTED>", redacted)
    return redacted


def _render_session_markdown(
    run_state: Optional[RunState],
    route: RouteDecision,
    plan_artifact: Optional[PlanArtifact],
    events: list[ReplayEvent],
) -> str:
    lines = ["# Session", ""]
    lines.append(f"- route: {route.route_name}")
    lines.append(f"- capture_mode: {route.capture_mode}")
    if run_state is not None:
        lines.append(f"- run_id: {run_state.run_id}")
        lines.append(f"- stage: {run_state.stage}")
    if plan_artifact is not None:
        lines.append(f"- plan: {plan_artifact.path}")
    lines.append("")
    lines.append("## Timeline")
    for event in events:
        lines.append(f"- {event.ts} | {event.phase} | {event.intent} | {event.result}")
    if events:
        lines.append("")
        lines.append("## Highlights")
        for event in events:
            lines.append(f"- {event.phase}: {_redact_text(event.key_output)}")
            for highlight in event.highlights:
                lines.append(f"- {event.phase}: {_redact_text(highlight)}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_breakdown_markdown(events: list[ReplayEvent]) -> str:
    lines = ["# Breakdown", ""]
    if not events:
        lines.append("- No events recorded yet.")
        return "\n".join(lines) + "\n"
    for index, event in enumerate(events, start=1):
        lines.append(f"## {index}. {event.phase}")
        lines.append(f"- 目标: {event.intent}")
        lines.append(f"- 动作: {event.action}")
        lines.append(f"- 摘要: {_redact_text(event.key_output)}")
        lines.append(f"- 原因: {_redact_text(event.decision_reason)}")
        lines.append(f"- 结果: {event.result}")
        if event.alternatives:
            lines.append(f"- 备选: {', '.join(event.alternatives)}")
        if event.highlights:
            for highlight in event.highlights:
                lines.append(f"- 说明: {_redact_text(highlight)}")
        if event.risk:
            lines.append(f"- 风险: {_redact_text(event.risk)}")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_decision_replay_event(
    decision_state: DecisionState,
    *,
    language: str,
    action: str,
) -> ReplayEvent:
    """Build a replay event for a decision checkpoint lifecycle step."""
    checkpoint = decision_state.active_checkpoint
    recommended_option = _option_by_id(decision_state.options, decision_state.recommended_option_id)
    selected_option = _option_by_id(decision_state.options, decision_state.selected_option_id)
    recommendation_reason = (
        checkpoint.recommendation.reason
        if checkpoint.recommendation is not None and checkpoint.recommendation.reason
        else decision_state.trigger_reason or decision_state.summary
    )
    if action == "confirmed" and selected_option is not None:
        key_output = _decision_text(language, "confirmed_output").format(option=_option_label(selected_option))
        result = "confirmed"
    else:
        key_output = _decision_text(language, "pending_output").format(count=len(decision_state.options))
        result = "pending"
    risk = ""
    if selected_option is not None and selected_option.tradeoffs:
        risk = selected_option.tradeoffs[0]
    elif recommended_option is not None and recommended_option.tradeoffs:
        risk = recommended_option.tradeoffs[0]
    return ReplayEvent(
        ts=decision_state.updated_at or decision_state.created_at,
        phase="design",
        intent=decision_state.question or decision_state.summary,
        action=f"decision:{action}",
        key_output=key_output,
        decision_reason=recommendation_reason,
        result=result,
        risk=risk,
        alternatives=tuple(_option_label(option) for option in decision_state.options),
        highlights=_decision_highlights(
            decision_state,
            checkpoint=checkpoint,
            recommended_option=recommended_option,
            selected_option=selected_option,
            language=language,
            action=action,
        ),
        artifacts=tuple(decision_state.context_files),
    )


def build_compare_replay_event(
    *,
    ts: str,
    question: str,
    contract: Mapping[str, Any],
    language: str,
) -> ReplayEvent:
    """Build a replay event summarizing compare-result convergence."""
    checkpoint_payload = contract.get("checkpoint")
    checkpoint = DecisionCheckpoint.from_dict(checkpoint_payload) if isinstance(checkpoint_payload, Mapping) else None
    recommendation = checkpoint.recommendation if checkpoint is not None else None
    recommended_option = None
    alternatives: tuple[str, ...] = ()
    if checkpoint is not None:
        primary_field = next((field for field in checkpoint.fields if field.field_id == checkpoint.primary_field_id), checkpoint.fields[0] if checkpoint.fields else None)
        if primary_field is not None:
            recommended_option = _option_by_id(primary_field.options, contract.get("recommended_option_id"))
            alternatives = tuple(_option_label(option) for option in primary_field.options)
    recommendation_reason = str(contract.get("recommendation_reason") or contract.get("summary") or "")
    highlights = [
        _compare_text(language, "result_count").format(count=int(contract.get("result_count") or 0)),
    ]
    if recommended_option is not None:
        highlights.append(_compare_text(language, "recommended").format(option=_option_label(recommended_option)))
    if recommendation_reason:
        highlights.append(_compare_text(language, "recommendation_reason").format(reason=recommendation_reason))
    return ReplayEvent(
        ts=ts,
        phase="analysis",
        intent=question,
        action="compare:decision_facade",
        key_output=str(contract.get("summary") or ""),
        decision_reason=recommendation_reason or str(contract.get("summary") or ""),
        result="ready",
        alternatives=alternatives,
        highlights=tuple(highlights),
    )


def build_develop_quality_replay_event(
    *,
    ts: str,
    payload: Mapping[str, Any],
    language: str,
) -> ReplayEvent:
    """Build a replay event summarizing the latest develop quality-loop result."""
    quality_result = extract_develop_quality_result(payload) or {}
    quality_context = extract_develop_quality_context(payload) or {}
    task_refs = tuple(str(item) for item in (quality_context.get("task_refs") or ()) if str(item).strip())
    verification_source = str(quality_result.get("verification_source") or "")
    command = str(quality_result.get("command") or "")
    result = str(quality_result.get("result") or "")
    root_cause = str(quality_result.get("root_cause") or "")
    working_summary = str(quality_context.get("working_summary") or "")

    command_label = command or _develop_quality_text(language, "not_configured")
    review_result = quality_result.get("review_result") if isinstance(quality_result.get("review_result"), Mapping) else {}
    highlights = [
        _develop_quality_text(language, "tasks").format(tasks=", ".join(task_refs) if task_refs else _develop_quality_text(language, "missing")),
        _develop_quality_text(language, "verification").format(
            source=verification_source or _develop_quality_text(language, "missing"),
            command=command_label,
        ),
    ]
    if root_cause:
        highlights.append(_develop_quality_text(language, "root_cause").format(root_cause=root_cause))
    for stage in DEVELOP_REVIEW_STAGES:
        stage_payload = review_result.get(stage) if isinstance(review_result, Mapping) else None
        if isinstance(stage_payload, Mapping):
            highlights.append(
                _develop_quality_text(language, "review_stage").format(
                    stage=stage,
                    status=str(stage_payload.get("status") or _develop_quality_text(language, "missing")),
                )
            )

    return ReplayEvent(
        ts=ts,
        phase="develop",
        intent=", ".join(task_refs) if task_refs else working_summary or _develop_quality_text(language, "intent"),
        action="develop:quality_loop",
        key_output=_develop_quality_text(language, "key_output").format(
            result=result or _develop_quality_text(language, "missing"),
            summary=working_summary or _develop_quality_text(language, "no_summary"),
        ),
        decision_reason=_develop_quality_text(language, "decision_reason").format(
            source=verification_source or _develop_quality_text(language, "missing"),
            command=command_label,
        ),
        result=result or "recorded",
        risk=root_cause,
        highlights=tuple(highlights),
        artifacts=tuple(str(item) for item in (quality_context.get("changed_files") or ()) if str(item).strip()),
    )


def _decision_highlights(
    decision_state: DecisionState,
    *,
    checkpoint: DecisionCheckpoint,
    recommended_option: DecisionOption | None,
    selected_option: DecisionOption | None,
    language: str,
    action: str,
) -> tuple[str, ...]:
    highlights: list[str] = []
    if recommended_option is not None:
        highlights.append(_decision_text(language, "recommended").format(option=_option_label(recommended_option)))
    if checkpoint.recommendation is not None and checkpoint.recommendation.reason:
        highlights.append(_decision_text(language, "recommendation_reason").format(reason=checkpoint.recommendation.reason))
    if action == "confirmed" and selected_option is not None:
        highlights.append(_decision_text(language, "selected").format(option=_option_label(selected_option)))
        if decision_state.recommended_option_id and decision_state.selected_option_id != decision_state.recommended_option_id:
            highlights.append(_decision_text(language, "override"))
        highlights.extend(_selection_constraint_highlights(decision_state, checkpoint=checkpoint, language=language))
    return tuple(highlights)


def _selection_constraint_highlights(
    decision_state: DecisionState,
    *,
    checkpoint: DecisionCheckpoint,
    language: str,
) -> tuple[str, ...]:
    selection = decision_state.selection
    if selection is None:
        return ()
    highlights: list[str] = []
    answers = selection.answers
    for field in checkpoint.fields:
        if field.field_id == checkpoint.primary_field_id:
            continue
        value = answers.get(field.field_id)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple)) and len(value) == 0:
            continue
        if field.field_type in {"input", "textarea"}:
            highlights.append(_decision_text(language, "freeform_answer").format(label=field.label))
            continue
        if field.field_type == "confirm":
            normalized = _normalize_boolean(value)
            highlights.append(
                _decision_text(language, "boolean_answer").format(
                    label=field.label,
                    value=_decision_text(language, "yes") if normalized else _decision_text(language, "no"),
                )
            )
            continue
        if field.field_type in {"select", "multi_select"}:
            highlights.append(
                _decision_text(language, "structured_answer").format(
                    label=field.label,
                    value=_stringify_answer(value),
                )
            )
    return tuple(highlights)


_DEVELOP_QUALITY_TEXT = {
    "zh-CN": {
        "intent": "develop 质量循环",
        "key_output": "质量结果={result}；摘要={summary}",
        "decision_reason": "验证来源={source}；命令={command}",
        "tasks": "任务: {tasks}",
        "verification": "验证: {source} / {command}",
        "root_cause": "根因: {root_cause}",
        "review_stage": "复审 {stage}: {status}",
        "not_configured": "<未配置稳定命令>",
        "missing": "<缺失>",
        "no_summary": "<无摘要>",
    },
    "en-US": {
        "intent": "develop quality loop",
        "key_output": "quality result={result}; summary={summary}",
        "decision_reason": "verification source={source}; command={command}",
        "tasks": "tasks: {tasks}",
        "verification": "verification: {source} / {command}",
        "root_cause": "root cause: {root_cause}",
        "review_stage": "review {stage}: {status}",
        "not_configured": "<no stable command configured>",
        "missing": "<missing>",
        "no_summary": "<no summary>",
    },
}


def _develop_quality_text(language: str, key: str) -> str:
    table = _DEVELOP_QUALITY_TEXT.get(language, _DEVELOP_QUALITY_TEXT["en-US"])
    return table[key]


def _option_by_id(options: Iterable[DecisionOption], option_id: str | None) -> DecisionOption | None:
    if not option_id:
        return None
    for option in options:
        if option.option_id == option_id:
            return option
    return None


def _option_label(option: DecisionOption) -> str:
    return f"{option.title} ({option.option_id})"


def _normalize_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().casefold()
    return normalized in {"1", "true", "yes", "y", "on", "是", "确认", "继续"}


def _stringify_answer(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _decision_text(language: str, key: str) -> str:
    locale = "en-US" if language == "en-US" else "zh-CN"
    messages = {
        "zh-CN": {
            "pending_output": "已创建决策 checkpoint，等待在 {count} 个候选中确认方向。",
            "confirmed_output": "已确认决策，最终选择 {option}。",
            "recommended": "推荐项：{option}",
            "recommendation_reason": "推荐理由：{reason}",
            "selected": "最终选择：{option}",
            "override": "最终选择没有沿用默认推荐。",
            "freeform_answer": "{label}：已提供补充说明（默认不回放原文）",
            "boolean_answer": "{label}：{value}",
            "structured_answer": "{label}：{value}",
            "yes": "是",
            "no": "否",
        },
        "en-US": {
            "pending_output": "Decision checkpoint created; waiting to confirm one path from {count} candidates.",
            "confirmed_output": "Decision confirmed; selected {option}.",
            "recommended": "Recommended: {option}",
            "recommendation_reason": "Recommendation reason: {reason}",
            "selected": "Selected: {option}",
            "override": "The final choice did not follow the default recommendation.",
            "freeform_answer": "{label}: additional free-form guidance provided (raw text omitted by default)",
            "boolean_answer": "{label}: {value}",
            "structured_answer": "{label}: {value}",
            "yes": "yes",
            "no": "no",
        },
    }
    return messages[locale][key]


def _compare_text(language: str, key: str) -> str:
    locale = "en-US" if language == "en-US" else "zh-CN"
    messages = {
        "zh-CN": {
            "result_count": "compare 成功结果数：{count}",
            "recommended": "compare 推荐结果：{option}",
            "recommendation_reason": "compare 推荐依据：{reason}",
        },
        "en-US": {
            "result_count": "Successful compare results: {count}",
            "recommended": "Recommended compare result: {option}",
            "recommendation_reason": "Compare recommendation reason: {reason}",
        },
    }
    return messages[locale][key]
