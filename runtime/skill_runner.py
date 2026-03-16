"""Runtime skill invocation helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping

from .models import SkillMeta


class SkillExecutionError(RuntimeError):
    """Raised when a runtime skill cannot be executed safely."""


def run_runtime_skill(skill: SkillMeta, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Invoke a runtime skill through a strict Python entry convention.

    The runtime only supports Python modules exposing either `run_skill` or
    `run_<skill_id>_runtime`.
    """
    if skill.mode != "runtime" or skill.runtime_entry is None:
        raise SkillExecutionError(f"Skill is not executable at runtime: {skill.skill_id}")
    if skill.runtime_entry.suffix != ".py":
        raise SkillExecutionError(f"Unsupported runtime entry type: {skill.runtime_entry}")

    module = _load_module(skill.runtime_entry, skill.skill_id)
    candidate_names = ("run_skill", f"run_{skill.skill_id.replace('-', '_')}_runtime")
    for name in candidate_names:
        entry = getattr(module, name, None)
        if callable(entry):
            result = entry(**payload)
            if isinstance(result, Mapping):
                return dict(result)
            if hasattr(result, "to_dict"):
                return result.to_dict()
            return {"result": result}
    raise SkillExecutionError(
        f"Runtime entry missing supported callable for {skill.skill_id}: {', '.join(candidate_names)}"
    )


def _load_module(path: Path, skill_id: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"sopify_runtime_{skill_id.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise SkillExecutionError(f"Unable to load runtime entry: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
