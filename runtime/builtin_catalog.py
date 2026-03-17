"""Builtin Sopify skill catalog owned by the runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .models import SkillMeta

_DEFAULT_CONTRACT_VERSION = "1"
_SOPIFY_DOC_ROOT = ("Codex", "Skills")
_LANGUAGE_DIRS = {
    "zh-CN": ("CN", "EN"),
    "en-US": ("EN", "CN"),
}


@dataclass(frozen=True)
class _BuiltinSkillSpec:
    skill_id: str
    names: Mapping[str, str]
    descriptions: Mapping[str, str]
    mode: str = "workflow"
    runtime_entry: str | None = None
    entry_kind: str | None = None
    handoff_kind: str | None = None
    contract_version: str = _DEFAULT_CONTRACT_VERSION
    supports_routes: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


_BUILTIN_SPECS: tuple[_BuiltinSkillSpec, ...] = (
    _BuiltinSkillSpec(
        skill_id="analyze",
        names={"zh-CN": "analyze", "en-US": "analyze"},
        descriptions={
            "zh-CN": "需求分析阶段详细规则；用于需求评分、追问与范围判断。",
            "en-US": "Detailed requirements-analysis rules for scoring, clarification, and scope checks.",
        },
        handoff_kind="analysis",
        supports_routes=("workflow", "plan_only"),
    ),
    _BuiltinSkillSpec(
        skill_id="design",
        names={"zh-CN": "design", "en-US": "design"},
        descriptions={
            "zh-CN": "方案设计阶段详细规则；用于方案生成与任务拆分。",
            "en-US": "Detailed design-stage rules for solution generation and task breakdown.",
        },
        handoff_kind="plan",
        supports_routes=("workflow", "plan_only", "light_iterate"),
    ),
    _BuiltinSkillSpec(
        skill_id="develop",
        names={"zh-CN": "develop", "en-US": "develop"},
        descriptions={
            "zh-CN": "开发实施阶段详细规则；用于代码执行、验证与知识库同步。",
            "en-US": "Detailed implementation-stage rules for code execution, validation, and KB sync.",
        },
        handoff_kind="develop",
        supports_routes=("workflow", "light_iterate", "quick_fix", "resume_active", "exec_plan"),
    ),
    _BuiltinSkillSpec(
        skill_id="kb",
        names={"zh-CN": "kb", "en-US": "kb"},
        descriptions={
            "zh-CN": "知识库管理技能；用于初始化、更新与同步知识库。",
            "en-US": "Knowledge-base management skill for bootstrap, updates, and synchronization.",
        },
        handoff_kind="kb",
    ),
    _BuiltinSkillSpec(
        skill_id="templates",
        names={"zh-CN": "templates", "en-US": "templates"},
        descriptions={
            "zh-CN": "文档模板集合；用于生成方案与知识库文档。",
            "en-US": "Template collection for plan and knowledge-base documents.",
        },
        handoff_kind="template",
    ),
    _BuiltinSkillSpec(
        skill_id="model-compare",
        names={"zh-CN": "model-compare", "en-US": "model-compare"},
        descriptions={
            "zh-CN": "多模型并发对比子技能；由 runtime 负责 compare 路由执行。",
            "en-US": "Multi-model comparison sub-skill executed by the runtime compare route.",
        },
        mode="runtime",
        runtime_entry="scripts/model_compare_runtime.py",
        entry_kind="python",
        handoff_kind="compare",
        supports_routes=("compare",),
        triggers=("~compare", "对比分析：", "compare:"),
    ),
    _BuiltinSkillSpec(
        skill_id="workflow-learning",
        names={"zh-CN": "workflow-learning", "en-US": "workflow-learning"},
        descriptions={
            "zh-CN": "工作流学习子技能；用于回放、复盘与决策解释。",
            "en-US": "Workflow-learning sub-skill for replay, review, and decision explanation.",
        },
        handoff_kind="replay",
        supports_routes=("replay",),
        triggers=("回放", "复盘", "为什么这么做", "replay", "review the implementation"),
    ),
)


def load_builtin_skills(*, repo_root: Path, language: str) -> tuple[SkillMeta, ...]:
    """Build builtin skill metadata without scanning bundled skill directories."""
    skills: list[SkillMeta] = []
    for spec in _BUILTIN_SPECS:
        runtime_entry = _resolve_runtime_entry(repo_root, spec.runtime_entry)
        entry_kind = spec.entry_kind if runtime_entry is not None else None
        path = _resolve_instruction_path(repo_root, language, spec.skill_id)
        metadata = dict(spec.metadata)
        metadata.setdefault("catalog", "builtin")

        skills.append(
            SkillMeta(
                skill_id=spec.skill_id,
                name=_localized(spec.names, language, fallback=spec.skill_id),
                description=_localized(spec.descriptions, language, fallback=""),
                path=path,
                source="builtin",
                mode=spec.mode,
                runtime_entry=runtime_entry,
                triggers=spec.triggers,
                metadata=metadata,
                entry_kind=entry_kind,
                handoff_kind=spec.handoff_kind,
                contract_version=spec.contract_version,
                supports_routes=spec.supports_routes,
            )
        )
    return tuple(skills)


def _localized(values: Mapping[str, str], language: str, *, fallback: str) -> str:
    return values.get(language) or values.get("en-US") or next(iter(values.values()), fallback)


def _resolve_runtime_entry(repo_root: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    candidate = (repo_root / relative_path).resolve()
    if candidate.exists():
        return candidate
    return None


def _resolve_instruction_path(repo_root: Path, language: str, skill_id: str) -> Path:
    language_dirs = _LANGUAGE_DIRS.get(language, _LANGUAGE_DIRS["en-US"])
    candidates: list[Path] = []
    for language_dir in language_dirs:
        candidates.append(
            repo_root / _SOPIFY_DOC_ROOT[0] / _SOPIFY_DOC_ROOT[1] / language_dir / "skills" / "sopify" / skill_id / "SKILL.md"
        )
        candidates.append(
            repo_root / "Claude" / "Skills" / language_dir / "skills" / "sopify" / skill_id / "SKILL.md"
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    # Vendored bundles do not ship the builtin prompt docs; the catalog remains the local source of truth.
    return (repo_root / "runtime" / "builtin_catalog.py").resolve()
