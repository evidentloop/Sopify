"""Reusable decision checkpoint templates."""

from __future__ import annotations

from dataclasses import dataclass

from sopify_contracts.decision import (
    DecisionCheckpoint,
    DecisionCondition,
    DecisionField,
    DecisionOption,
    DecisionRecommendation,
)

PRIMARY_OPTION_FIELD_ID = "selected_option_id"
CUSTOM_OPTION_ID = "custom"


@dataclass(frozen=True)
class StrategyPickTemplate:
    """Rendered template payload reused by decision runtime state."""

    options: tuple[DecisionOption, ...]
    checkpoint: DecisionCheckpoint
    recommended_option_id: str | None
    default_option_id: str | None


def build_strategy_pick_template(
    *,
    checkpoint_id: str,
    question: str,
    summary: str,
    options: tuple[DecisionOption, ...],
    language: str,
    recommended_option_id: str | None,
    default_option_id: str | None,
    allow_custom_option: bool = False,
    custom_option_id: str = CUSTOM_OPTION_ID,
    custom_option_title: str | None = None,
    custom_option_summary: str | None = None,
    custom_reason_field_id: str = "custom_reason",
    constraint_field_type: str | None = None,
    constraint_field_id: str = "implementation_constraint",
    constraint_label: str | None = None,
    constraint_description: str = "",
) -> StrategyPickTemplate:
    """Build the v1 strategy-pick checkpoint contract."""
    normalized_options = list(options)
    if allow_custom_option:
        # Keep the runtime contract host-agnostic: a custom branch is still just
        # one extra option plus a conditional free-text field.
        normalized_options.append(
            DecisionOption(
                option_id=custom_option_id,
                title=custom_option_title or _text(language, "custom_option_title"),
                summary=custom_option_summary or _text(language, "custom_option_summary"),
                tradeoffs=(_text(language, "custom_option_tradeoff"),),
                impacts=(_text(language, "custom_option_impact"),),
                recommended=False,
            )
        )

    fields = [
        DecisionField(
            field_id=PRIMARY_OPTION_FIELD_ID,
            field_type="select",
            label=_text(language, "select_label"),
            description=summary,
            required=True,
            options=tuple(normalized_options),
            default_value=default_option_id,
        )
    ]

    if allow_custom_option:
        fields.append(
            DecisionField(
                field_id=custom_reason_field_id,
                field_type="textarea",
                label=_text(language, "custom_reason_label"),
                description=_text(language, "custom_reason_description"),
                required=True,
                when=(
                    DecisionCondition(
                        field_id=PRIMARY_OPTION_FIELD_ID,
                        operator="equals",
                        value=custom_option_id,
                    ),
                ),
            )
        )

    if constraint_field_type is not None:
        if constraint_field_type not in {"confirm", "input"}:
            raise ValueError(f"Unsupported strategy-pick constraint field: {constraint_field_type}")
        # v1 intentionally caps constraint capture to one lightweight tail field
        # so hosts can bridge the checkpoint serially.
        fields.append(
            DecisionField(
                field_id=constraint_field_id,
                field_type=constraint_field_type,
                label=constraint_label or _text(language, "constraint_label"),
                description=constraint_description or _text(language, "constraint_description"),
                required=False,
            )
        )

    if len(fields) > 3:
        raise ValueError("strategy_pick template supports at most 3 fields")

    recommendation = None
    if recommended_option_id:
        recommendation = DecisionRecommendation(
            field_id=PRIMARY_OPTION_FIELD_ID,
            option_id=recommended_option_id,
            summary=summary,
            reason=summary,
        )

    return StrategyPickTemplate(
        options=tuple(normalized_options),
        checkpoint=DecisionCheckpoint(
            checkpoint_id=checkpoint_id,
            title=question,
            message=summary,
            fields=tuple(fields),
            primary_field_id=PRIMARY_OPTION_FIELD_ID,
            recommendation=recommendation,
            blocking=True,
            allow_text_fallback=True,
        ),
        recommended_option_id=recommended_option_id,
        default_option_id=default_option_id,
    )


def _text(language: str, key: str) -> str:
    locale = "en-US" if language == "en-US" else "zh-CN"
    messages = {
        "zh-CN": {
            "select_label": "请选择方案方向",
            "custom_option_title": "自定义方案",
            "custom_option_summary": "当前候选都不够合适，需要补充新的方向说明。",
            "custom_option_tradeoff": "会引入未比较过的新方向，需要补充上下文再继续。",
            "custom_option_impact": "runtime 会等待宿主把补充说明写回 submission 后再恢复。",
            "custom_reason_label": "补充你的方案说明",
            "custom_reason_description": "说明为什么现有候选不合适，以及你希望 runtime 按什么方向继续。",
            "constraint_label": "补充约束",
            "constraint_description": "如有必须遵守的边界、风险或落地限制，可在这里补充。",
        },
        "en-US": {
            "select_label": "Choose a path",
            "custom_option_title": "Custom path",
            "custom_option_summary": "None of the current candidates fit; provide a better direction.",
            "custom_option_tradeoff": "Introduces a new path that still needs explicit context before planning resumes.",
            "custom_option_impact": "Runtime will wait for the host to write back the extra explanation before resuming.",
            "custom_reason_label": "Explain your preferred path",
            "custom_reason_description": "Describe why the listed candidates do not fit and what direction runtime should take instead.",
            "constraint_label": "Additional constraint",
            "constraint_description": "Add any boundary, risk, or implementation constraint that runtime should preserve.",
        },
    }
    return messages[locale][key]
