"""Runtime configuration loading and validation."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping, Optional

from ._yaml import YamlParseError, load_yaml
from .models import RuntimeConfig

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None


class ConfigError(ValueError):
    """Raised when a config file is malformed or unsupported."""


DEFAULT_CONFIG: dict[str, Any] = {
    "brand": "auto",
    "language": "zh-CN",
    "output_style": "minimal",
    "title_color": "green",
    "workflow": {
        "mode": "adaptive",
        "require_score": 7,
        "auto_decide": False,
        "learning": {"auto_capture": "by_requirement"},
    },
    "plan": {
        "level": "auto",
        "directory": ".sopify-skills",
    },
    "multi_model": {
        "enabled": False,
        "trigger": "manual",
        "timeout_sec": 25,
        "max_parallel": 3,
        "include_default_model": True,
    },
    "advanced": {
        "ehrb_level": "normal",
        "kb_init": "progressive",
        "cache_project": True,
    },
}

_ALLOWED_TOP_LEVEL = {"brand", "language", "output_style", "title_color", "workflow", "plan", "multi_model", "advanced"}
_ALLOWED_WORKFLOW = {"mode", "require_score", "auto_decide", "learning"}
_ALLOWED_LEARNING = {"auto_capture"}
_ALLOWED_PLAN = {"level", "directory"}
_ALLOWED_MULTI_MODEL = {"enabled", "trigger", "timeout_sec", "max_parallel", "include_default_model", "context_bridge", "candidates"}
_ALLOWED_ADVANCED = {"ehrb_level", "kb_init", "cache_project"}

_ALLOWED_LANGUAGES = {"zh-CN", "en-US"}
_ALLOWED_OUTPUT_STYLES = {"minimal", "classic"}
_ALLOWED_TITLE_COLORS = {"green", "blue", "yellow", "cyan", "none"}
_ALLOWED_WORKFLOW_MODES = {"strict", "adaptive", "minimal"}
_ALLOWED_CAPTURE_MODES = {"always", "by_requirement", "manual", "off"}
_ALLOWED_PLAN_LEVELS = {"auto", "light", "standard", "full"}
_ALLOWED_MULTI_MODEL_TRIGGER = {"manual"}
_ALLOWED_EHRB_LEVELS = {"strict", "normal", "relaxed"}
_ALLOWED_KB_INIT = {"full", "progressive"}


def load_runtime_config(
    workspace_root: str | Path,
    *,
    global_config_path: str | Path | None = None,
) -> RuntimeConfig:
    """Load and validate runtime configuration.

    Args:
        workspace_root: Project root.
        global_config_path: Optional explicit global config path.

    Returns:
        A normalized runtime config.
    """
    workspace = Path(workspace_root).resolve()
    project_path = workspace / "sopify.config.yaml"
    global_path = (
        Path(global_config_path).expanduser().resolve()
        if global_config_path is not None
        else (Path.home() / ".codex" / "sopify.config.yaml")
    )

    merged = deepcopy(DEFAULT_CONFIG)
    project_data = _load_config_file(project_path)
    global_data = _load_config_file(global_path)

    if global_data:
        _deep_merge(merged, global_data)
    if project_data:
        _deep_merge(merged, project_data)

    _validate_config(merged, source_paths=(global_path if global_data else None, project_path if project_data else None))

    return RuntimeConfig(
        workspace_root=workspace,
        project_config_path=project_path if project_data else None,
        global_config_path=global_path if global_data else None,
        brand=_resolve_brand(str(merged["brand"]), workspace),
        language=str(merged["language"]),
        output_style=str(merged["output_style"]),
        title_color=str(merged["title_color"]),
        workflow_mode=str(merged["workflow"]["mode"]),
        require_score=int(merged["workflow"]["require_score"]),
        auto_decide=bool(merged["workflow"]["auto_decide"]),
        workflow_learning_auto_capture=str(merged["workflow"]["learning"]["auto_capture"]),
        plan_level=str(merged["plan"]["level"]),
        plan_directory=str(merged["plan"]["directory"]),
        multi_model_enabled=bool(merged["multi_model"]["enabled"]),
        multi_model_trigger=str(merged["multi_model"]["trigger"]),
        multi_model_timeout_sec=int(merged["multi_model"]["timeout_sec"]),
        multi_model_max_parallel=int(merged["multi_model"]["max_parallel"]),
        multi_model_include_default_model=bool(merged["multi_model"]["include_default_model"]),
        ehrb_level=str(merged["advanced"]["ehrb_level"]),
        kb_init=str(merged["advanced"]["kb_init"]),
        cache_project=bool(merged["advanced"]["cache_project"]),
    )


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise ConfigError(f"Config path is not a file: {path}")
    raw_text = path.read_text(encoding="utf-8")
    data = _parse_yaml(raw_text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return data


def _parse_yaml(text: str) -> Any:
    if yaml is not None:  # pragma: no branch
        try:
            return yaml.safe_load(text)
        except Exception as exc:  # pragma: no cover - fallback path is tested
            raise ConfigError(str(exc)) from exc
    try:
        return load_yaml(text)
    except YamlParseError as exc:
        raise ConfigError(str(exc)) from exc


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, Mapping):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _validate_config(config: Mapping[str, Any], *, source_paths: tuple[Optional[Path], Optional[Path]]) -> None:
    _assert_allowed_keys(config, _ALLOWED_TOP_LEVEL, path="root")

    if config["language"] not in _ALLOWED_LANGUAGES:
        raise ConfigError(f"Unsupported language: {config['language']}")
    if config["output_style"] not in _ALLOWED_OUTPUT_STYLES:
        raise ConfigError(f"Unsupported output_style: {config['output_style']}")
    if config["title_color"] not in _ALLOWED_TITLE_COLORS:
        raise ConfigError(f"Unsupported title_color: {config['title_color']}")

    workflow = _expect_mapping(config.get("workflow"), path="workflow")
    _assert_allowed_keys(workflow, _ALLOWED_WORKFLOW, path="workflow")
    if workflow["mode"] not in _ALLOWED_WORKFLOW_MODES:
        raise ConfigError(f"Unsupported workflow.mode: {workflow['mode']}")
    if not isinstance(workflow["require_score"], int) or not (1 <= workflow["require_score"] <= 10):
        raise ConfigError("workflow.require_score must be an integer between 1 and 10")
    if not isinstance(workflow["auto_decide"], bool):
        raise ConfigError("workflow.auto_decide must be boolean")
    learning = _expect_mapping(workflow.get("learning"), path="workflow.learning")
    _assert_allowed_keys(learning, _ALLOWED_LEARNING, path="workflow.learning")
    if learning["auto_capture"] not in _ALLOWED_CAPTURE_MODES:
        raise ConfigError(f"Unsupported workflow.learning.auto_capture: {learning['auto_capture']}")

    plan = _expect_mapping(config.get("plan"), path="plan")
    _assert_allowed_keys(plan, _ALLOWED_PLAN, path="plan")
    if plan["level"] not in _ALLOWED_PLAN_LEVELS:
        raise ConfigError(f"Unsupported plan.level: {plan['level']}")
    if not isinstance(plan["directory"], str) or not plan["directory"].strip():
        raise ConfigError("plan.directory must be a non-empty string")

    multi_model = _expect_mapping(config.get("multi_model"), path="multi_model")
    _assert_allowed_keys(multi_model, _ALLOWED_MULTI_MODEL, path="multi_model")
    if not isinstance(multi_model["enabled"], bool):
        raise ConfigError("multi_model.enabled must be boolean")
    if multi_model["trigger"] not in _ALLOWED_MULTI_MODEL_TRIGGER:
        raise ConfigError(f"Unsupported multi_model.trigger: {multi_model['trigger']}")
    if not isinstance(multi_model["timeout_sec"], int) or multi_model["timeout_sec"] <= 0:
        raise ConfigError("multi_model.timeout_sec must be a positive integer")
    if not isinstance(multi_model["max_parallel"], int) or multi_model["max_parallel"] <= 0:
        raise ConfigError("multi_model.max_parallel must be a positive integer")
    if not isinstance(multi_model["include_default_model"], bool):
        raise ConfigError("multi_model.include_default_model must be boolean")

    advanced = _expect_mapping(config.get("advanced"), path="advanced")
    _assert_allowed_keys(advanced, _ALLOWED_ADVANCED, path="advanced")
    if advanced["ehrb_level"] not in _ALLOWED_EHRB_LEVELS:
        raise ConfigError(f"Unsupported advanced.ehrb_level: {advanced['ehrb_level']}")
    if advanced["kb_init"] not in _ALLOWED_KB_INIT:
        raise ConfigError(f"Unsupported advanced.kb_init: {advanced['kb_init']}")
    if not isinstance(advanced["cache_project"], bool):
        raise ConfigError("advanced.cache_project must be boolean")

    del source_paths  # keep signature explicit for future diagnostics


def _assert_allowed_keys(data: Mapping[str, Any], allowed: set[str], *, path: str) -> None:
    unknown = sorted(set(data.keys()) - allowed)
    if unknown:
        raise ConfigError(f"Unknown config key(s) at {path}: {', '.join(unknown)}")


def _expect_mapping(value: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"Expected mapping at {path}")
    return value


def _resolve_brand(raw_brand: str, workspace_root: Path) -> str:
    if raw_brand != "auto":
        return raw_brand
    project_name = (
        _project_name_from_git_remote(workspace_root)
        or _project_name_from_package_json(workspace_root)
        or workspace_root.name
        or "project"
    )
    return f"{project_name}-ai"


def _project_name_from_git_remote(workspace_root: Path) -> Optional[str]:
    git_config = workspace_root / ".git" / "config"
    if not git_config.exists():
        return None
    content = git_config.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^\s*url\s*=\s*(.+)$", content, re.MULTILINE)
    if not match:
        return None
    remote = match.group(1).strip()
    name = remote.rstrip("/").rsplit("/", 1)[-1]
    if ":" in name and "/" not in remote:
        name = name.rsplit(":", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or None


def _project_name_from_package_json(workspace_root: Path) -> Optional[str]:
    package_json = workspace_root / "package.json"
    if not package_json.exists():
        return None
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    name = payload.get("name")
    return str(name) if isinstance(name, str) and name.strip() else None
