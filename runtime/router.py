"""Deterministic route classifier for Sopify runtime."""

from __future__ import annotations

from dataclasses import dataclass
import re
from .clarification import has_submitted_clarification, parse_clarification_response
from .context_snapshot import ContextResolvedSnapshot, resolve_context_snapshot, snapshot_global_execution_run, snapshot_state_conflict_artifacts
from .decision import has_submitted_decision, parse_decision_response
from .entry_guard import DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE
from sopify_contracts.core import RouteDecision, RuntimeConfig
from .action_intent import ActionProposal
from sopify_contracts.decision import ClarificationState, DecisionState
from canonical_writer import StateStore

_COMMAND_PATTERNS = (
    (re.compile(r"^~go\s+plan(?:\s+(?P<body>.+))?$", re.IGNORECASE), "~go plan"),
    (re.compile(r"^~go\s+finalize(?:\s+(?P<body>.+))?$", re.IGNORECASE), "~go finalize"),
    (re.compile(r"^~go(?:\s+(?P<body>.+))?$", re.IGNORECASE), "~go"),
)
SUPPORTED_ROUTE_NAMES = (
    "plan_only",
    "workflow",
    "light_iterate",
    "quick_fix",
    "clarification_pending",
    "clarification_resume",
    "resume_active",
    "exec_plan",
    "cancel_active",
    "archive_lifecycle",
    "decision_pending",
    "decision_resume",
    "state_conflict",
    "consult",
)

# Checkpoint reply keywords — used ONLY by checkpoint-specific classifiers
# (_classify_pending_clarification, _classify_state_conflict), never by the
# main Router.classify() ingress.  General cancel/continue intent must come
# through ActionProposal (cancel_flow / execute_existing_plan).
_CONTINUE_KEYWORDS = {"继续", "下一步", "继续执行", "继续吧", "go on", "continue", "resume", "next"}
_CANCEL_KEYWORDS = {"取消", "强制取消", "停止", "终止", "算了", "放弃", "abort", "cancel", "stop", "force cancel"}
_ARCHITECTURE_KEYWORDS = ("架构", "系统", "runtime", "workflow", "engine", "adapter", "plugin", "新功能", "重构", "refactor")
_ACTION_KEYWORDS = (
    "修复",
    "实现",
    "添加",
    "新增",
    "修改",
    "重构",
    "优化",
    "删除",
    "fix",
    "implement",
    "add",
    "update",
    "refactor",
    "remove",
    "create",
)
_QUESTION_PREFIXES = (
    "为什么",
    "如何",
    "怎么",
    "解释",
    "说明",
    "看下",
    "看看",
    "what",
    "why",
    "how",
    "是否",
    "能否",
    "可以",
)
_STRONG_INTERROGATIVE_PREFIXES = (
    "为什么",
    "为何",
    "如何",
    "怎么",
    "解释",
    "说明",
    "what",
    "why",
    "how",
)
_SHORT_ACTION_REQUEST_THRESHOLD = 80
_FOLLOWUP_ACTION_CONNECTORS = ("并", "再", "然后", "顺便", "and", "then")
_ACTION_IMPACT_QUESTION_KEYWORDS = ("影响", "风险", "后果", "依赖", "波及")
_FILE_REF_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+|[\w.-]+\.(?:ts|tsx|js|jsx|py|md|json|yaml|yml|vue|rs|go)")
_PROCESS_FORCE_KEYWORDS_EN = ("design", "develop", "decision", "checkpoint", "handoff")
_PROCESS_FORCE_KEYWORDS_ZH = ("规划", "方案设计", "开发实施", "决策", "检查点", "交接", "门禁", "蓝图")
_PROCESS_FORCE_PATTERNS = (
    re.compile(
        rf"(?<![\w-])(?:{'|'.join(re.escape(keyword) for keyword in _PROCESS_FORCE_KEYWORDS_EN)})(?![\w-])",
        re.IGNORECASE,
    ),
    re.compile(rf"(?:{'|'.join(re.escape(keyword) for keyword in _PROCESS_FORCE_KEYWORDS_ZH)})"),
)
RUNTIME_FIRST_PROTECTED_PATH_PREFIXES = (".sopify-skills/plan/",)
_PROTECTED_PLAN_ASSET_RE = re.compile(r"(^|[\s'\"`])(?:\./)?\.sopify-skills/plan/[^\s'\"`]+", re.IGNORECASE)
_TRADEOFF_FORCE_KEYWORDS = ("tradeoff", "trade-off", "取舍", "分叉", "长期", "long-term", "contract", "契约", "策略分歧")
_TRADEOFF_FORCE_PATTERNS = (
    re.compile(r"(trade[\s-]?off|取舍|分叉|长期|long[\s-]?term|contract|契约|策略分歧)", re.IGNORECASE),
)
_LONG_TERM_CONTRACT_HINTS = (
    "架构",
    "蓝图",
    "contract",
    "契约",
    "policy",
    "策略",
    "入口",
    "runtime",
    "权限",
    "catalog",
    "slo",
    "长期",
)
_ACTIVE_PLAN_META_REVIEW_CUES = (
    "review",
    "分析下",
    "评估下",
    "解释下",
    "看看",
    "critique",
    "风险",
    "risk",
    "score",
    "评分",
    "打分",
    "优化点",
    "状态",
    "当前状态",
    "现在状态",
    "状态如何",
    "有什么问题",
    "还有什么问题",
)
_ACTIVE_PLAN_FOLLOWUP_EDIT_CUES = (
    "改一下",
    "改下",
    "改成",
    "改为",
    "修改",
    "补一下",
    "补下",
    "修一下",
    "修下",
    "调整",
    "edit",
    "change",
    "update",
    "fix",
    "adjust",
    "modify",
)
_PLAN_MATERIALIZATION_META_DEBUG_PATTERNS = (
    re.compile(r"(为什么|为何|why).*(生成|创建|create).*(plan|方案)", re.IGNORECASE),
    re.compile(r"(不要|别再|不要再|stop|don't).*(生成|创建|create).*(plan|方案)", re.IGNORECASE),
    re.compile(r"(分析下|解释下|看看|review).*(命中|hit).*(guard|plan|方案)", re.IGNORECASE),
)
_LIGHT_EDIT_HINTS = ("readme", "注释", "comment", "typo", "文案", "assert", "断言", "路径说明")
@dataclass(frozen=True)
class _ComplexitySignal:
    level: str
    reason: str
    plan_level: str | None


def build_runtime_first_hints() -> dict[str, object]:
    """Publish stable host-facing hints for requests that should enter via the gate."""
    return {
        "force_route_name": "workflow",
        "entry_guard_reason_code": DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE,
        "required_entry": "scripts/runtime_gate.py",
        "required_subcommand": "enter",
        "direct_entry_block_error_code": "runtime_gate_required",
        "debug_bypass_flag": "--allow-direct-entry",
        "protected_path_prefixes": list(RUNTIME_FIRST_PROTECTED_PATH_PREFIXES),
        "process_semantic_keywords": list(_PROCESS_FORCE_KEYWORDS_EN + _PROCESS_FORCE_KEYWORDS_ZH),
        "tradeoff_keywords": list(_TRADEOFF_FORCE_KEYWORDS),
        "long_term_contract_keywords": list(_LONG_TERM_CONTRACT_HINTS),
    }


def match_runtime_first_guard(text: str) -> dict[str, str] | None:
    """Return the matched runtime-first guard, if this request should not enter direct edit paths."""
    if _is_protected_plan_asset_request(text):
        return {
            "guard_kind": "protected_plan_asset",
            "reason": "Blocked direct-edit path because the request targets protected .sopify-skills/plan assets",
        }
    if _has_process_semantic_intent(text):
        return {
            "guard_kind": "process_semantic_intent",
            "reason": "Blocked direct-edit path because process-semantic keywords require runtime-first routing",
        }
    if _has_tradeoff_or_contract_split(text):
        return {
            "guard_kind": "tradeoff_contract_split",
            "reason": "Blocked direct-edit path because tradeoff or long-term contract split requires runtime-first routing",
        }
    return None


class Router:
    """Classify user input into deterministic runtime routes."""

    def __init__(self, config: RuntimeConfig, *, state_store: StateStore, global_state_store: StateStore | None = None) -> None:
        self.config = config
        self.state_store = state_store
        self.global_state_store = global_state_store or state_store

    def classify(
        self,
        user_input: str,
        *,
        snapshot: ContextResolvedSnapshot | None = None,
    ) -> RouteDecision:
        text = user_input.strip()
        if snapshot is None:
            snapshot = resolve_context_snapshot(
                config=self.config,
                review_store=self.state_store,
                global_store=self.global_state_store,
            )

        current_clarification = snapshot.current_clarification
        current_decision = snapshot.current_decision
        review_active_run = snapshot.current_run
        execution_active_run = snapshot.execution_active_run
        global_active_run = execution_active_run if snapshot.preferred_state_scope == "global" else None
        if review_active_run is global_active_run:
            review_active_run = None
        execution_current_plan = snapshot.execution_current_plan
        current_plan = snapshot.current_plan
        current_last_route = snapshot.last_route

        decide_decision = _classify_decide_command(text)
        if decide_decision is not None:
            return self._with_capture(decide_decision)

        command_decision = _classify_command(text, config=self.config, snapshot=snapshot)
        if snapshot.is_conflict:
            return self._with_capture(
                _classify_state_conflict(
                    text,
                    command_decision=command_decision,
                    snapshot=snapshot,
                )
            )

        if current_clarification is not None and current_clarification.status == "pending":
            pending_clarification = _classify_pending_clarification(
                text,
                current_clarification,
                command_decision=command_decision,
            )
            if pending_clarification is not None:
                return self._with_capture(pending_clarification)

        if current_decision is not None and current_decision.status in {"pending", "collecting", "confirmed"}:
            pending_decision = _classify_pending_decision(
                text,
                current_decision,
                command_decision=command_decision,
            )
            if pending_decision is not None:
                return self._with_capture(pending_decision)

        if command_decision is not None:
            return self._with_capture(command_decision)

        plan_meta_debug_route = _classify_plan_materialization_meta_debug(
            text,
        )
        if plan_meta_debug_route is not None:
            return self._with_capture(plan_meta_debug_route)

        runtime_first_guard = match_runtime_first_guard(text)
        if runtime_first_guard is not None:
            return self._with_capture(
                RouteDecision(
                    route_name="workflow",
                    request_text=text,
                    reason=runtime_first_guard["reason"],
                    complexity="complex",
                    plan_level="standard",
                    plan_package_policy=_plan_package_policy_for_route("workflow", text, config=self.config),
                    candidate_skill_ids=("analyze", "design", "develop"),
                    artifacts={
                        "entry_guard_reason_code": DIRECT_EDIT_BLOCKED_RUNTIME_REQUIRED_REASON_CODE,
                        "direct_edit_guard_kind": runtime_first_guard["guard_kind"],
                        "direct_edit_guard_trigger": runtime_first_guard["reason"],
                    },
                )
            )

        if _is_consultation(text) and not _should_bypass_consult_for_active_plan_followup_edit(
            text,
            current_plan=current_plan,
        ):
            return RouteDecision(
                route_name="consult",
                request_text=text,
                reason="Looks like a direct question without change intent",
                complexity="simple",
            )

        signal = estimate_complexity(text)
        if signal.level == "simple":
            return self._with_capture(
                RouteDecision(
                    route_name="quick_fix",
                    request_text=text,
                    reason=signal.reason,
                    complexity=signal.level,
                    candidate_skill_ids=("develop",),
                )
            )
        if signal.level == "medium":
            return self._with_capture(
                RouteDecision(
                    route_name="light_iterate",
                    request_text=text,
                    reason=signal.reason,
                    complexity=signal.level,
                    plan_level=signal.plan_level,
                    plan_package_policy=_plan_package_policy_for_route("light_iterate", text, config=self.config),
                    candidate_skill_ids=("design", "develop"),
                )
            )
        return self._with_capture(
            RouteDecision(
                route_name="workflow",
                request_text=text,
                reason=signal.reason,
                complexity=signal.level,
                plan_level=signal.plan_level,
                plan_package_policy=_plan_package_policy_for_route("workflow", text, config=self.config),
                candidate_skill_ids=("analyze", "design", "develop"),
            )
        )

    def _with_capture(self, decision: RouteDecision) -> RouteDecision:
        # capture_mode is deprecated (replay sunset P3b); no-op passthrough.
        return decision


def _classify_command(text: str, *, config: RuntimeConfig, snapshot: ContextResolvedSnapshot) -> RouteDecision | None:
    for pattern, command in _COMMAND_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        body = (match.groupdict().get("body") or "").strip()
        request_text = body or text
        if command == "~go plan":
            return RouteDecision(
                route_name="plan_only",
                request_text=request_text,
                reason="Matched explicit planning command",
                command=command,
                complexity="complex",
                plan_level="standard",
                plan_package_policy="immediate",
                candidate_skill_ids=("analyze", "design"),
            )
        if command == "~go finalize":
            return RouteDecision(
                route_name="archive_lifecycle",
                request_text=request_text,
                reason="Matched explicit finalize command",
                command=command,
                complexity="low",
                candidate_skill_ids=(),
            )
        if command == "~go":
            # Migration hint: ~go exec was removed; nudge user to bare ~go
            if body and body.lower() == "exec":
                return RouteDecision(
                    route_name="workflow",
                    request_text=request_text,
                    reason="`~go exec` has been removed. Use bare `~go` to auto-resume an active plan, or `~go <requirement>` for a new workflow.",
                    command=command,
                    complexity="low",
                    candidate_skill_ids=(),
                )
            # Only bare ~go (no body) auto-detects active plan for exec_plan
            active_plan = snapshot.current_plan or snapshot.execution_current_plan
            if active_plan is not None and not body:
                return RouteDecision(
                    route_name="exec_plan",
                    request_text=request_text,
                    reason="Active plan detected; auto-routing to execution",
                    command=command,
                    complexity="medium",
                    should_recover_context=True,
                    candidate_skill_ids=("develop",),
                    active_run_action="resume",
                )
            return RouteDecision(
                route_name="workflow",
                request_text=request_text,
                reason="Matched explicit workflow command",
                command=command,
                complexity="complex",
                plan_level="standard",
                plan_package_policy=_plan_package_policy_for_route("workflow", request_text, config=config),
                candidate_skill_ids=("analyze", "design", "develop"),
            )
    return None


def _classify_state_conflict(
    text: str,
    *,
    command_decision: RouteDecision | None,
    snapshot: ContextResolvedSnapshot,
) -> RouteDecision:
    normalized = _normalize(text)
    if normalized in _CANCEL_KEYWORDS:
        reason = "State conflict cleanup requested explicitly"
        active_run_action = "abort_conflict"
    else:
        reason = snapshot.conflict_message or "A conflicting runtime state blocks further routing until it is cleaned up"
        active_run_action = "inspect_conflict"
    artifacts = {
        **snapshot_state_conflict_artifacts(snapshot),
        "entry_guard_reason_code": "entry_guard_state_conflict",
    }
    return RouteDecision(
        route_name="state_conflict",
        request_text=text,
        reason=reason,
        command=command_decision.command if command_decision is not None else None,
        complexity="simple",
        should_recover_context=True,
        candidate_skill_ids=("analyze", "develop"),
        active_run_action=active_run_action,
        artifacts=artifacts,
    )


def _classify_decide_command(text: str) -> RouteDecision | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if not lowered.startswith("~decide"):
        return None
    if lowered.startswith("~decide status") or lowered == "~decide":
        return RouteDecision(
            route_name="decision_pending",
            request_text=stripped,
            reason="Matched explicit decision status command",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("design",),
            active_run_action="inspect_decision",
        )
    return RouteDecision(
        route_name="decision_resume",
        request_text=stripped,
        reason="Matched explicit decision response command",
        complexity="medium",
        should_recover_context=True,
        candidate_skill_ids=("design",),
        active_run_action="decision_response",
    )


def _classify_pending_decision(
    text: str,
    current_decision: DecisionState,
    *,
    command_decision: RouteDecision | None,
) -> RouteDecision | None:
    if (
        current_decision.status in {"pending", "collecting"}
        and has_submitted_decision(current_decision)
        and (command_decision is None or command_decision.route_name != "decision_pending")
    ):
        return RouteDecision(
            route_name="decision_resume",
            request_text=text,
            reason="Structured decision submission is ready to be resumed",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("design",),
            active_run_action="resume_submitted_decision",
        )

    if command_decision is not None:
        if command_decision.route_name in {"plan_only", "light_iterate"}:
            return None
        if command_decision.route_name == "workflow":
            if command_decision.command != "~go":
                return None
            # ~go explicitly typed with pending decision: intercept
            if current_decision.status == "pending":
                return RouteDecision(
                    route_name="decision_pending",
                    request_text=text,
                    reason="Pending decision checkpoint must be resolved before workflow can continue",
                    complexity="medium",
                    should_recover_context=True,
                    candidate_skill_ids=("design",),
                    active_run_action="inspect_decision",
                )
            return RouteDecision(
                route_name="decision_resume",
                request_text=text,
                reason="Confirmed decision checkpoint is being materialized through ~go",
                command=command_decision.command,
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("design",),
                active_run_action="materialize_confirmed_decision",
            )
        if command_decision.route_name == "exec_plan":
            if current_decision.status == "pending":
                return RouteDecision(
                    route_name="decision_pending",
                    request_text=text,
                    reason="Pending decision checkpoint must be resolved before exec recovery can continue",
                    complexity="medium",
                    should_recover_context=True,
                    candidate_skill_ids=("design",),
                    active_run_action="inspect_decision",
                )
            return RouteDecision(
                route_name="decision_resume",
                request_text=text,
                reason="Confirmed decision checkpoint is being materialized through the exec recovery entry",
                command=command_decision.command,
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("design",),
                active_run_action="materialize_confirmed_decision",
            )

    response = parse_decision_response(current_decision, text)
    if response.action == "status":
        return RouteDecision(
            route_name="decision_pending",
            request_text=text,
            reason="Pending decision checkpoint is waiting for confirmation",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("design",),
            active_run_action="inspect_decision",
        )
    if response.action in {"choose", "materialize", "cancel", "invalid"}:
        return RouteDecision(
            route_name="decision_resume",
            request_text=text,
            reason="Matched a response for the pending decision checkpoint",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("design",),
            active_run_action="decision_response",
        )
    return None




def _classify_pending_clarification(
    text: str,
    current_clarification: ClarificationState,
    *,
    command_decision: RouteDecision | None,
) -> RouteDecision | None:
    if command_decision is not None:
        if command_decision.route_name in {"plan_only", "light_iterate"}:
            return None
        if command_decision.route_name == "workflow":
            # ~go with no active plan → allow new workflow (don't intercept)
            if command_decision.command != "~go":
                return None
            # ~go explicitly typed: intercept if clarification is for the current flow
            return RouteDecision(
                route_name="clarification_pending",
                request_text=text,
                reason="Pending clarification must be answered before workflow can continue",
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("analyze", "design"),
                active_run_action="inspect_clarification",
            )
        if command_decision.route_name == "exec_plan":
            return RouteDecision(
                route_name="clarification_pending",
                request_text=text,
                reason="Pending clarification must be answered before execution can continue",
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("analyze", "design"),
                active_run_action="inspect_clarification",
            )

    if has_submitted_clarification(current_clarification) and _normalize(text) in _CONTINUE_KEYWORDS:
        return RouteDecision(
            route_name="clarification_resume",
            request_text=text,
            reason="Restoring planning from structured clarification answers",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("analyze", "design"),
            active_run_action="clarification_response_from_state",
        )

    response = parse_clarification_response(current_clarification, text)
    if response.action == "status":
        return RouteDecision(
            route_name="clarification_pending",
            request_text=text,
            reason="Pending clarification is still waiting for factual details",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("analyze", "design"),
            active_run_action="inspect_clarification",
        )
    if response.action == "cancel":
        return RouteDecision(
            route_name="cancel_active",
            request_text=text,
            reason="Clarification cancelled by user",
            complexity="simple",
            should_recover_context=True,
            active_run_action="cancel",
        )
    if response.action == "answer":
        return RouteDecision(
            route_name="clarification_resume",
            request_text=text,
            reason="Received supplemental facts for the pending clarification",
            complexity="medium",
            should_recover_context=True,
            candidate_skill_ids=("analyze", "design"),
            active_run_action="clarification_response",
        )
    return RouteDecision(
        route_name="clarification_pending",
        request_text=text,
        reason=response.message or "Clarification still needs more factual details",
        complexity="medium",
        should_recover_context=True,
        candidate_skill_ids=("analyze", "design"),
        active_run_action="inspect_clarification",
    )




def estimate_complexity(text: str) -> _ComplexitySignal:
    lowered = text.lower()
    file_refs = len(_FILE_REF_RE.findall(text))
    has_arch = any(keyword.lower() in lowered for keyword in _ARCHITECTURE_KEYWORDS)
    has_action = any(keyword.lower() in lowered for keyword in _ACTION_KEYWORDS)

    if has_action and any(token in lowered for token in _LIGHT_EDIT_HINTS):
        return _ComplexitySignal("simple", "Detected a bounded docs/tests wording tweak", None)
    if has_arch or file_refs > 5:
        plan_level = "full" if has_arch and any(token in lowered for token in ("架构", "system", "plugin", "adapter")) else "standard"
        return _ComplexitySignal("complex", "Detected architecture-scale or broad change intent", plan_level)
    if has_action and 3 <= file_refs <= 5:
        return _ComplexitySignal("medium", "Detected multi-file but bounded implementation request", "light")
    if has_action and file_refs == 0:
        if len(text.strip()) < _SHORT_ACTION_REQUEST_THRESHOLD:
            return _ComplexitySignal("medium", "Short action request without explicit file scope", "light")
        return _ComplexitySignal("complex", "Detected change intent without bounded file scope", "standard")
    if has_action:
        return _ComplexitySignal("simple", "Detected focused implementation request with limited scope", None)
    return _ComplexitySignal("medium", "Defaulted to medium because the request is action-oriented but underspecified", "light")



def _classify_plan_materialization_meta_debug(
    text: str,
) -> RouteDecision | None:
    if not any(pattern.search(text) is not None for pattern in _PLAN_MATERIALIZATION_META_DEBUG_PATTERNS):
        return None
    return RouteDecision(
        route_name="consult",
        request_text=text,
        reason="Matched plan-materialization meta-debug intent and bypassed workflow routing",
        complexity="simple",
        should_recover_context=False,
        candidate_skill_ids=("analyze",),
    )


def _is_consultation(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    has_action = any(keyword.lower() in normalized for keyword in _ACTION_KEYWORDS)
    if has_action:
        if normalized.startswith(("解释", "说明")) and _has_followup_action_clause(normalized):
            return False
        if normalized.startswith(_STRONG_INTERROGATIVE_PREFIXES):
            return True
        if (text.endswith("?") or text.endswith("？")) and _looks_like_action_impact_question(normalized):
            return True
        return False
    if text.endswith("?") or text.endswith("？"):
        return True
    return normalized.startswith(_QUESTION_PREFIXES)


def _has_followup_action_clause(normalized: str) -> bool:
    for connector in _FOLLOWUP_ACTION_CONNECTORS:
        index = normalized.find(connector)
        if index >= 0:
            tail = normalized[index + len(connector) :]
            if any(keyword.lower() in tail for keyword in _ACTION_KEYWORDS):
                return True
    return False


def _looks_like_action_impact_question(normalized: str) -> bool:
    return any(keyword in normalized for keyword in _ACTION_IMPACT_QUESTION_KEYWORDS)


def _is_protected_plan_asset_request(text: str) -> bool:
    return _PROTECTED_PLAN_ASSET_RE.search(text) is not None


def _has_process_semantic_intent(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _PROCESS_FORCE_PATTERNS)


def _plan_package_policy_for_route(route_name: str, request_text: str, *, config: RuntimeConfig) -> str:
    if route_name == "plan_only":
        return "authorized_only"
    if route_name not in {"workflow", "light_iterate"}:
        return "none"
    return "authorized_only"


def _has_tradeoff_or_contract_split(text: str) -> bool:
    lowered = text.lower()
    if any(pattern.search(text) is not None for pattern in _TRADEOFF_FORCE_PATTERNS):
        return True
    split_signal = "还是" in text or "二选一" in text or "vs" in lowered or " or " in lowered
    if not split_signal:
        return False
    return any(token in lowered for token in _LONG_TERM_CONTRACT_HINTS)



def _active_plan_meta_review_has_followup_edit(text: str) -> bool:
    fragments = _split_active_plan_review_fragments(text)
    review_seen = False
    edit_seen = False
    for fragment in fragments:
        lowered = fragment.casefold()
        has_review = any(cue.casefold() in lowered for cue in _ACTIVE_PLAN_META_REVIEW_CUES)
        has_edit = any(cue.casefold() in lowered for cue in _ACTIVE_PLAN_FOLLOWUP_EDIT_CUES)
        if has_review and has_edit:
            return True
        if (review_seen and has_edit) or (edit_seen and has_review):
            return True
        review_seen = review_seen or has_review
        edit_seen = edit_seen or has_edit
    return False


def _should_bypass_consult_for_active_plan_followup_edit(text: str, *, current_plan) -> bool:
    if current_plan is None:
        return False
    return _active_plan_meta_review_has_followup_edit(text)


def _split_active_plan_review_fragments(text: str) -> tuple[str, ...]:
    fragments: list[str] = []
    current: list[str] = []
    for char in str(text or ""):
        if char in ",，;；:：.!！？?\n":
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




def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())




# -- Authorized proposal → route derivation (moved from engine.py in 6.2) ----

_ACTION_TYPE_TO_ROUTE: dict[str, str] = {
    "consult_readonly": "consult",
    "execute_existing_plan": "resume_active",
    # cancel_flow handled inline (needs snapshot for cancel_scope).
    # propose_plan handled inline (needs complexity analysis for plan_level).
}


def _derive_route_from_authorized_proposal(
    proposal: ActionProposal,
    user_input: str,
    *,
    config: RuntimeConfig,
    snapshot: ContextResolvedSnapshot | None,
) -> RouteDecision:
    """Deterministically map an authorized ActionProposal to a RouteDecision.

    Called only when ``validation_decision.decision == DECISION_AUTHORIZE``
    and there is no ``route_override``.  Falls through to Router.classify()
    is NOT expected — every recognized action_type produces a route here.
    """
    action = proposal.action_type

    # --- cancel_flow: snapshot-driven cancel_scope ---
    if action == "cancel_flow":
        has_global = snapshot_global_execution_run(snapshot) is not None
        route = RouteDecision(
            route_name="cancel_active",
            request_text=user_input,
            reason="action_proposal_derive: cancel_flow",
            complexity="simple",
            should_recover_context=True,
            active_run_action="cancel",
            artifacts={"cancel_scope": "global" if has_global else "session"},
        )
    # --- checkpoint_response: snapshot-driven ---
    elif action == "checkpoint_response":
        route = _derive_checkpoint_response_route(user_input, snapshot=snapshot)
    # --- modify_files: complexity-driven ---
    elif action == "modify_files":
        route = _derive_modify_files_route(user_input)
    # --- propose_plan: complexity for plan_level, immediate materialization ---
    elif action == "propose_plan":
        signal = estimate_complexity(user_input)
        route = RouteDecision(
            route_name="plan_only",
            request_text=user_input,
            reason=f"action_proposal_derive: propose_plan ({signal.reason})",
            complexity="complex",
            plan_level=signal.plan_level or "standard",
            plan_package_policy="immediate",
            candidate_skill_ids=("analyze", "design"),
        )
    else:
        # --- static mappings ---
        route_name = _ACTION_TYPE_TO_ROUTE.get(action)
        if route_name is not None:
            route = _build_static_route(route_name, action, user_input)
        else:
            # Unreachable for valid ACTION_TYPES (archive_plan handled by route_override).
            route = RouteDecision(
                route_name="consult",
                request_text=user_input,
                reason=f"action_proposal_derive: unknown action_type {action!r}, falling back to consult",
                complexity="simple",
            )

    return route


def _derive_checkpoint_response_route(
    user_input: str,
    *,
    snapshot: ContextResolvedSnapshot | None,
) -> RouteDecision:
    """Route checkpoint_response based on active checkpoint state in snapshot.

    Only pending/collecting checkpoints are routable.  confirmed/cancelled/
    timed_out checkpoints are terminal and will not accept further free-text
    responses.

    NOTE: ActionProposal admission for checkpoint_response may still carry a
    plan_subject field, but the actual routing decision depends solely on
    the active checkpoint truth in the snapshot, not on plan_subject.
    """
    if snapshot is not None:
        clarification = snapshot.current_clarification
        if clarification is not None and clarification.status == "pending":
            return RouteDecision(
                route_name="clarification_resume",
                request_text=user_input,
                reason="action_proposal_derive: checkpoint_response with pending clarification",
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("analyze", "design"),
                active_run_action="clarification_response",
            )
        decision = snapshot.current_decision
        if decision is not None and decision.status in {"pending", "collecting"}:
            return RouteDecision(
                route_name="decision_resume",
                request_text=user_input,
                reason="action_proposal_derive: checkpoint_response with active decision",
                complexity="medium",
                should_recover_context=True,
                candidate_skill_ids=("design",),
                active_run_action="decision_response",
            )
    # No active checkpoint → REJECT (fail-closed)
    return RouteDecision(
        route_name="proposal_rejected",
        request_text=user_input,
        reason="action_proposal_derive: checkpoint_response but no active pending/collecting checkpoint",
        complexity="simple",
        should_recover_context=False,
        artifacts={"reject_reason_code": "checkpoint_response.no_active_checkpoint"},
    )


def _derive_modify_files_route(
    user_input: str,
) -> RouteDecision:
    """Route modify_files based on text complexity analysis."""
    signal = estimate_complexity(user_input)
    if signal.level == "simple":
        return RouteDecision(
            route_name="quick_fix",
            request_text=user_input,
            reason=f"action_proposal_derive: modify_files ({signal.reason})",
            complexity=signal.level,
            candidate_skill_ids=("develop",),
        )
    if signal.level == "medium":
        return RouteDecision(
            route_name="light_iterate",
            request_text=user_input,
            reason=f"action_proposal_derive: modify_files ({signal.reason})",
            complexity=signal.level,
            plan_level=signal.plan_level,
            plan_package_policy="authorized_only",
            candidate_skill_ids=("design", "develop"),
        )
    return RouteDecision(
        route_name="workflow",
        request_text=user_input,
        reason=f"action_proposal_derive: modify_files ({signal.reason})",
        complexity=signal.level,
        plan_level=signal.plan_level,
        plan_package_policy="authorized_only",
        candidate_skill_ids=("analyze", "design", "develop"),
    )


def _build_static_route(
    route_name: str,
    action_type: str,
    user_input: str,
) -> RouteDecision:
    """Build a RouteDecision for action types with a fixed route mapping.

    Only handles routes reachable via _ACTION_TYPE_TO_ROUTE:
    resume_active (execute_existing_plan) and consult (consult_readonly).
    cancel_flow is handled inline in _derive_route_from_authorized_proposal.
    """
    if route_name == "resume_active":
        return RouteDecision(
            route_name="resume_active",
            request_text=user_input,
            reason=f"action_proposal_derive: {action_type}",
            complexity="medium",
            should_recover_context=True,
            active_run_action="resume",
            candidate_skill_ids=("develop",),
        )
    # consult_readonly
    return RouteDecision(
        route_name="consult",
        request_text=user_input,
        reason=f"action_proposal_derive: {action_type}",
        complexity="simple",
    )


