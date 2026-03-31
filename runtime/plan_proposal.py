"""Plan-proposal helpers for proposal-first planning materialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Mapping

from .checkpoint_cancel import is_checkpoint_cancel_intent
from .models import DecisionState, PlanProposalState, RouteDecision

CURRENT_PLAN_PROPOSAL_FILENAME = "current_plan_proposal.json"
CURRENT_PLAN_PROPOSAL_RELATIVE_PATH = f".sopify-skills/state/{CURRENT_PLAN_PROPOSAL_FILENAME}"

_STATUS_ALIASES = {"status", "查看状态", "查看 proposal", "proposal status", "inspect"}
_CONFIRM_ALIASES = {"继续", "继续吧", "下一步", "continue", "next", "resume"}
_CANCEL_ALIASES = {"取消", "停止", "终止", "cancel", "stop", "abort"}
_FILE_REF_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+|[\w.-]+\.(?:ts|tsx|js|jsx|py|md|json|yaml|yml|vue|rs|go)")
_NATURAL_CONFIRM_FRAGMENT_PATTERNS = (
    re.compile(r"^继续按(?:这个|该|当前)方案(?:吧|走)?$", re.IGNORECASE),
    re.compile(r"^continue with this(?: plan)?$", re.IGNORECASE),
)
_RETOPIC_REVISION_PATTERNS = (
    re.compile(r"^\s*(?:把)?(?:(?:这个|该|当前)\s*)?方案(?:改成|改为|换成|换为)\s*.+?\s*$", re.IGNORECASE),
    re.compile(r"^\s*改成新的方案[:：]?\s*.+?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:change|switch)\s+(?:(?:this|the|current)\s+)?plan\s+to\s+.+?\s*$", re.IGNORECASE),
)
_QUESTION_LIKE_RETOPIC_PATTERNS = (
    re.compile(
        r"^\s*(?:能不能|可不可以|是否|是不是)\s*(?:把)?(?:(?:这个|该|当前)\s*)?方案(?:改成|改为|换成|换为)\s*.+?(?P<tail>\s*(?:然后|再|并且|并)\s*.*)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:把)?(?:(?:这个|该|当前)\s*)?方案\s*(?:能不能|可不可以|是否|是不是)\s*(?:改成|改为|换成|换为)\s*.+?(?P<tail>\s*(?:然后|再|并且|并)\s*.*)?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:can we|should we)\s+(?:change|switch)\s+(?:(?:this|the|current)\s+)?plan\s+to\s+.+?(?P<tail>\s+(?:and|then)\s+.*)?\s*$",
        re.IGNORECASE,
    ),
)
_EXPLICIT_REVISION_VERB_PATTERNS = (
    re.compile(r"(改成|改为|调整|补充|增加|新增|删除|移除|去掉|展开|收敛|拆成|拆分|纳入|加入|补一下|改一下|补下|改下)", re.IGNORECASE),
    re.compile(r"\b(change|update|revise|edit|adjust|add|remove|drop|expand|split|include|exclude)\b", re.IGNORECASE),
)
_EXPLICIT_REVISION_TARGET_PATTERNS = (
    re.compile(r"(level|path|summary|risk|scope|background|design|task(?:s)?|proposal|package|file|files|module)", re.IGNORECASE),
    re.compile(r"(级别|路径|摘要|概要|风险|范围|背景|设计|任务|方案|方案包|文件|模块|拆分)", re.IGNORECASE),
)
_CONSTRAINT_REVISION_CUES = (
    "按这个",
    "继续按",
    "最小范围",
    "不要过度设计",
    "直接进",
    "先做",
    "go straight to",
    "continue with",
    "move forward with",
    "keep it minimal",
    "don't overdesign",
    "do this first",
    "start with",
)
_QUESTION_SHORT_CIRCUIT_CUES = (
    "为什么",
    "为何",
    "怎么",
    "是否",
    "是不是",
    "可以吗",
    "可不可以",
    "能不能",
    "why",
    "how",
    "whether",
    "can we",
    "should we",
)
_SEGMENT_SPLIT_CHARS = ",，;；:：\n"
_QUESTION_SEGMENT_SPLIT_CHARS = "?？"
_REVISION_MARKERS = ("修订意见:", "revision feedback:")
_HAS_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_CONSTRAINT_FOLLOWUP_QUESTION_PATTERNS = (
    re.compile(r"(?:会有|会有什么|有什么|有哪些)(?:[^,，;；:：.!！？?\n]{0,16})(?:风险|问题)", re.IGNORECASE),
    re.compile(r"(?:风险|问题)(?:[^,，;；:：.!！？?\n]{0,12})(?:是什么|有哪些|在哪|在哪里)", re.IGNORECASE),
)
_LEVEL_LABELS_ZH = {"light": "轻量", "standard": "标准", "full": "完整"}
_LEVEL_LABELS_EN = {"light": "light", "standard": "standard", "full": "full"}


@dataclass(frozen=True)
class PlanProposalResponse:
    """Normalized interpretation of a proposal-pending user reply."""

    action: str
    message: str = ""


def parse_plan_proposal_response(user_input: str) -> PlanProposalResponse:
    """Interpret a raw user reply while a plan proposal is pending."""
    text = str(user_input or "").strip()
    if not text:
        return PlanProposalResponse(action="inspect", message="Empty proposal response")
    normalized = text.casefold()
    if normalized in {alias.casefold() for alias in _CONFIRM_ALIASES}:
        return PlanProposalResponse(action="confirm")
    if normalized in {alias.casefold() for alias in _STATUS_ALIASES}:
        return PlanProposalResponse(action="inspect")
    if is_checkpoint_cancel_intent(text, cancel_aliases=_CANCEL_ALIASES):
        return PlanProposalResponse(action="cancel")
    if _looks_like_natural_confirm_feedback(text):
        return PlanProposalResponse(action="confirm")
    if _looks_like_question_like_natural_confirm_feedback(text):
        return PlanProposalResponse(action="inspect", message="Question-like natural confirm stays fail-closed")
    if _has_local_revision_feedback(text):
        return PlanProposalResponse(action="revise")
    if _looks_like_question_feedback(text):
        return PlanProposalResponse(action="inspect", message="Question-like feedback stays fail-closed")
    if _looks_like_revision_feedback(text):
        return PlanProposalResponse(action="revise")
    return PlanProposalResponse(action="inspect", message="No explicit revision intent detected")


def merge_plan_proposal_request(proposal_state: PlanProposalState, feedback_text: str) -> str:
    """Merge the original planning request with revision feedback."""
    original = proposal_state.request_text.strip()
    feedback = str(feedback_text or "").strip()
    if not original:
        return feedback
    if not feedback:
        return original
    return f"{original}\n\n修订意见:\n{feedback}"


def build_plan_proposal_state(
    route: RouteDecision,
    *,
    request_text: str,
    proposed_level: str,
    checkpoint_id: str,
    reserved_plan_id: str,
    topic_key: str,
    proposed_path: str,
    confirmed_decision: DecisionState | None = None,
    created_at: str | None = None,
) -> PlanProposalState:
    """Create the persistent proposal state before a plan package is materialized."""
    now = created_at or iso_now()
    normalized_request = " ".join(str(request_text or "").split()).strip()
    candidate_files = extract_candidate_files(normalized_request)
    return PlanProposalState(
        schema_version="1",
        checkpoint_id=checkpoint_id,
        reserved_plan_id=reserved_plan_id,
        topic_key=topic_key,
        proposed_level=proposed_level,
        proposed_path=proposed_path,
        analysis_summary=build_plan_proposal_summary(
            normalized_request,
            proposed_level=proposed_level,
            candidate_files=candidate_files,
        ),
        estimated_task_count=estimate_task_count(proposed_level),
        candidate_files=candidate_files,
        request_text=normalized_request,
        resume_route=route.route_name,
        capture_mode=route.capture_mode,
        candidate_skill_ids=route.candidate_skill_ids,
        confirmed_decision=confirmed_decision.to_dict() if confirmed_decision is not None else {},
        created_at=now,
        updated_at=now,
    )


def refresh_plan_proposal_state(
    current: PlanProposalState,
    *,
    request_text: str,
    proposed_level: str,
) -> PlanProposalState:
    """Refresh proposal content without drifting proposal identity/path."""
    normalized_request = " ".join(str(request_text or "").split()).strip()
    candidate_files = extract_candidate_files(normalized_request)
    return PlanProposalState(
        schema_version=current.schema_version,
        checkpoint_id=current.checkpoint_id,
        reserved_plan_id=current.reserved_plan_id,
        topic_key=current.topic_key,
        proposed_level=proposed_level,
        proposed_path=current.proposed_path,
        analysis_summary=build_plan_proposal_summary(
            normalized_request,
            proposed_level=proposed_level,
            candidate_files=candidate_files,
        ),
        estimated_task_count=estimate_task_count(proposed_level),
        candidate_files=candidate_files,
        request_text=normalized_request,
        resume_route=current.resume_route,
        capture_mode=current.capture_mode,
        candidate_skill_ids=current.candidate_skill_ids,
        confirmed_decision=dict(current.confirmed_decision),
        created_at=current.created_at,
        updated_at=iso_now(),
    )


def extract_candidate_files(request_text: str) -> tuple[str, ...]:
    """Return stable file candidates mentioned in the request text."""
    seen: list[str] = []
    for match in _FILE_REF_RE.findall(str(request_text or "")):
        candidate = str(match).strip()
        if candidate and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)


def _looks_like_revision_feedback(text: str) -> bool:
    if _looks_like_retopic_revision_feedback(text):
        return True
    if not any(pattern.search(text) is not None for pattern in _EXPLICIT_REVISION_VERB_PATTERNS):
        return False
    if _FILE_REF_RE.search(text) is not None:
        return True
    return any(pattern.search(text) is not None for pattern in _EXPLICIT_REVISION_TARGET_PATTERNS)


def _looks_like_retopic_revision_feedback(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return False
    return any(pattern.match(normalized) is not None for pattern in _RETOPIC_REVISION_PATTERNS)


def _looks_like_question_feedback(text: str) -> bool:
    fragments = _split_feedback_fragments(text)
    if not fragments:
        return False
    return all(_classify_feedback_fragment(fragment) == "question" for fragment in fragments)


def _looks_like_natural_confirm_feedback(text: str) -> bool:
    fragments = _split_feedback_fragments(text)
    if not fragments:
        return False
    return all(_is_natural_confirm_fragment(fragment) for fragment in fragments)


def _looks_like_question_like_natural_confirm_feedback(text: str) -> bool:
    fragments = _split_feedback_fragments(text)
    if not fragments:
        return False
    return all(_is_question_like_natural_confirm_fragment(fragment) for fragment in fragments)


def _has_local_revision_feedback(text: str) -> bool:
    return any(_classify_feedback_fragment(fragment) == "revise" for fragment in _split_feedback_fragments(text))


def _looks_like_constraint_revision_feedback(text: str) -> bool:
    lowered = str(text or "").casefold()
    positions = [
        lowered.find(cue.casefold())
        for cue in _CONSTRAINT_REVISION_CUES
        if lowered.find(cue.casefold()) >= 0
    ]
    if not positions:
        return False
    first_constraint = min(positions)
    first_question = _first_question_cue_position(lowered)
    return first_question == -1 or first_constraint < first_question


def _classify_feedback_fragment(fragment: str) -> str:
    normalized = str(fragment or "").strip()
    if not normalized:
        return "neutral"
    if _has_question_like_retopic_followup_revision(normalized):
        return "revise"
    if _is_question_like_retopic_fragment(normalized):
        return "question"
    if _is_constraint_followup_question_fragment(normalized):
        return "question"
    if _is_question_like_constraint_fragment(normalized):
        return "question"
    if _looks_like_constraint_revision_feedback(normalized) or _looks_like_revision_feedback(normalized):
        return "revise"
    if _is_question_fragment(normalized):
        return "question"
    return "neutral"


def _is_question_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip()
    if not normalized:
        return False
    lowered = normalized.casefold()
    if normalized.endswith(("?", "？")):
        return True
    return _first_question_cue_position(lowered) != -1


def _is_constraint_followup_question_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip()
    if not normalized:
        return False
    if not _looks_like_constraint_revision_feedback(normalized):
        return False
    if any(pattern.search(normalized) is not None for pattern in _EXPLICIT_REVISION_VERB_PATTERNS):
        return False
    if _FILE_REF_RE.search(normalized) is not None:
        return False
    return any(pattern.search(normalized) is not None for pattern in _CONSTRAINT_FOLLOWUP_QUESTION_PATTERNS)


def _is_question_like_retopic_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip()
    if not normalized:
        return False
    if any(pattern.match(normalized) is not None for pattern in _QUESTION_LIKE_RETOPIC_PATTERNS):
        return True
    if not _looks_like_retopic_revision_feedback(normalized):
        return False
    if normalized.endswith(("?", "？")):
        return True
    candidate = normalized.rstrip("。.!！").strip()
    return candidate.endswith(("吗", "么"))


def _has_question_like_retopic_followup_revision(fragment: str) -> bool:
    tail = _question_like_retopic_followup_tail(fragment)
    if tail is None:
        return False
    return _looks_like_constraint_revision_feedback(tail) or _looks_like_revision_feedback(tail)


def _question_like_retopic_followup_tail(fragment: str) -> str | None:
    normalized = str(fragment or "").strip()
    if not normalized:
        return None
    for pattern in _QUESTION_LIKE_RETOPIC_PATTERNS:
        match = pattern.match(normalized)
        if match is None:
            continue
        tail = str(match.groupdict().get("tail") or "").strip()
        if not tail:
            continue
        stripped = _strip_question_like_retopic_tail_connector(tail)
        if stripped:
            return stripped
    return None


def _strip_question_like_retopic_tail_connector(tail: str) -> str:
    normalized = str(tail or "").strip()
    if not normalized:
        return ""
    for connector in ("然后", "并且", "并", "再"):
        if normalized.startswith(connector):
            return normalized[len(connector) :].strip()
    lowered = normalized.casefold()
    for connector in ("and ", "then "):
        if lowered.startswith(connector):
            return normalized[len(connector) :].strip()
    return normalized


def _is_question_like_constraint_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip()
    lowered = normalized.casefold()
    if not normalized:
        return False
    if not (normalized.endswith(("?", "？")) or _first_question_cue_position(lowered) != -1):
        return False
    if not _looks_like_constraint_revision_feedback(normalized):
        return False
    if any(pattern.search(normalized) is not None for pattern in _EXPLICIT_REVISION_VERB_PATTERNS):
        return False
    if _FILE_REF_RE.search(normalized) is not None:
        return False
    if _has_non_constraint_revision_target(normalized):
        return False
    return True


def _is_natural_confirm_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip().rstrip("。.!！")
    if not normalized:
        return False
    return any(pattern.search(normalized) is not None for pattern in _NATURAL_CONFIRM_FRAGMENT_PATTERNS)


def _is_question_like_natural_confirm_fragment(fragment: str) -> bool:
    normalized = str(fragment or "").strip()
    if not normalized or not normalized.endswith(("?", "？")):
        return False
    candidate = normalized.rstrip("?？").strip()
    if candidate.endswith("吗"):
        candidate = candidate[:-1].strip()
    return _is_natural_confirm_fragment(candidate)


def _first_question_cue_position(lowered_text: str) -> int:
    positions = [
        lowered_text.find(cue.casefold())
        for cue in _QUESTION_SHORT_CIRCUIT_CUES
        if lowered_text.find(cue.casefold()) >= 0
    ]
    if not positions:
        return -1
    return min(positions)


def _has_non_constraint_revision_target(text: str) -> bool:
    source = str(text or "")
    lowered = source.casefold()
    constraint_spans: list[tuple[int, int]] = []
    for cue in _CONSTRAINT_REVISION_CUES:
        cue_lower = cue.casefold()
        start = lowered.find(cue_lower)
        while start != -1:
            constraint_spans.append((start, start + len(cue_lower)))
            start = lowered.find(cue_lower, start + 1)

    for pattern in _EXPLICIT_REVISION_TARGET_PATTERNS:
        for match in pattern.finditer(source):
            start, end = match.span()
            overlaps_constraint = any(not (end <= cue_start or start >= cue_end) for cue_start, cue_end in constraint_spans)
            if not overlaps_constraint:
                return True
    return False


def _split_feedback_fragments(text: str) -> tuple[str, ...]:
    fragments: list[str] = []
    current: list[str] = []
    for char in str(text or ""):
        if char in _QUESTION_SEGMENT_SPLIT_CHARS:
            current.append(char)
            fragment = "".join(current).strip()
            if fragment:
                fragments.append(fragment)
            current = []
            continue
        if char in _SEGMENT_SPLIT_CHARS:
            fragment = "".join(current).strip()
            if fragment:
                fragments.append(fragment)
            current = []
            continue
        current.append(char)
    fragment = "".join(current).strip()
    if fragment:
        fragments.append(fragment)
    return tuple(fragments)


def build_plan_proposal_summary(
    request_text: str,
    *,
    proposed_level: str,
    candidate_files: tuple[str, ...],
) -> str:
    """Render a stable human summary for proposal confirmation checkpoints."""
    headline = _proposal_headline(request_text)
    revised = _contains_revision_feedback(request_text)
    if _HAS_CJK_RE.search(request_text):
        summary = f"围绕“{headline}”准备{_LEVEL_LABELS_ZH.get(proposed_level, '标准')}方案包"
        scope = _scope_summary_zh(candidate_files)
        if scope:
            summary = f"{summary}，重点涉及 {scope}"
        if revised:
            summary = f"{summary}，并纳入修订意见"
        return summary

    summary = f"Prepare a {_LEVEL_LABELS_EN.get(proposed_level, 'standard')} plan package for {headline}"
    scope = _scope_summary_en(candidate_files)
    if scope:
        summary = f"{summary}; focus on {scope}"
    if revised:
        summary = f"{summary}; includes updated revision feedback"
    return summary


def _proposal_headline(request_text: str) -> str:
    cleaned = str(request_text or "").strip()
    if not cleaned:
        return "the requested change"
    lowered = cleaned.casefold()
    cut = len(cleaned)
    for marker in _REVISION_MARKERS:
        position = lowered.find(marker.casefold())
        if position != -1:
            cut = min(cut, position)
    cleaned = cleaned[:cut].strip(" \n:;,.") or str(request_text or "").strip()
    return _summarize_text(cleaned, limit=48) or "the requested change"


def _contains_revision_feedback(request_text: str) -> bool:
    lowered = str(request_text or "").casefold()
    return any(marker.casefold() in lowered for marker in _REVISION_MARKERS)


def _scope_summary_zh(candidate_files: tuple[str, ...]) -> str:
    if not candidate_files:
        return ""
    if len(candidate_files) <= 3:
        return "、".join(candidate_files)
    return f"{'、'.join(candidate_files[:3])} 等 {len(candidate_files)} 个文件"


def _scope_summary_en(candidate_files: tuple[str, ...]) -> str:
    if not candidate_files:
        return ""
    if len(candidate_files) == 1:
        return candidate_files[0]
    if len(candidate_files) <= 3:
        return ", ".join(candidate_files)
    return f"{', '.join(candidate_files[:3])}, and {len(candidate_files) - 3} more files"


def _summarize_text(text: str, *, limit: int) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    if limit <= 3:
        return compact[:limit]
    return compact[: limit - 3].rstrip() + "..."


def estimate_task_count(plan_level: str) -> int:
    """Keep proposal summaries stable before the real scaffold exists."""
    return {
        "light": 3,
        "standard": 5,
        "full": 7,
    }.get(str(plan_level or "standard"), 5)


def confirmed_decision_from_proposal(proposal_state: PlanProposalState) -> DecisionState | None:
    """Rehydrate confirmed decision context carried through proposal state."""
    payload = proposal_state.confirmed_decision
    if not isinstance(payload, Mapping) or not payload:
        return None
    decision_state = DecisionState.from_dict(payload)
    if decision_state.status != "confirmed" or decision_state.selection is None:
        return None
    return decision_state


def iso_now() -> str:
    """Return a stable UTC ISO timestamp without importing runtime.state."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
