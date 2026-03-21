"""Host-side long-term preference preload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .config import load_runtime_config
from .models import RuntimeConfig

PreferencesPreloadStatus = Literal["loaded", "missing", "invalid", "read_error"]
PREFERENCES_PRELOAD_STATUSES: tuple[PreferencesPreloadStatus, ...] = (
    "loaded",
    "missing",
    "invalid",
    "read_error",
)

_PREFERENCES_PROMPT_PREFIX = (
    "[Long-Term User Preferences]\n"
    "Scope: current workspace\n"
    "Priority: current task explicit request > this preferences file > default rules\n\n"
    "Apply these as durable collaboration rules for this Sopify run.\n"
    "If a rule conflicts with the current explicit task, follow the current task."
)
_PREFERENCES_PLACEHOLDER_LINES = (
    "当前暂无已确认的长期偏好。",
    "No confirmed long-term preferences yet.",
)


@dataclass(frozen=True)
class PreferencesPreloadResult:
    """Deterministic host-facing result for workspace preference preload."""

    status: PreferencesPreloadStatus
    workspace_root: str
    plan_directory: str
    preferences_path: str
    feedback_path: str
    feedback_present: bool
    injected: bool
    error_code: str | None = None
    injection_text: str = ""
    raw_content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "workspace_root": self.workspace_root,
            "plan_directory": self.plan_directory,
            "preferences_path": self.preferences_path,
            "feedback_path": self.feedback_path,
            "feedback_present": self.feedback_present,
            "injected": self.injected,
            "error_code": self.error_code,
            "injection_text": self.injection_text,
            "raw_content": self.raw_content,
        }


def resolve_preferences_path(config: RuntimeConfig) -> Path:
    """Resolve the workspace-scoped preferences path from normalized config."""
    return config.runtime_root / "user" / "preferences.md"


def resolve_feedback_path(config: RuntimeConfig) -> Path:
    """Resolve the workspace-scoped raw feedback log path from normalized config."""
    return config.runtime_root / "user" / "feedback.jsonl"


def preload_preferences(config: RuntimeConfig) -> PreferencesPreloadResult:
    """Load workspace preferences and build the host injection block when possible."""
    preferences_path = resolve_preferences_path(config)
    feedback_path = resolve_feedback_path(config)
    base_payload = {
        "workspace_root": str(config.workspace_root),
        "plan_directory": config.plan_directory,
        "preferences_path": str(preferences_path),
        "feedback_path": str(feedback_path),
        "feedback_present": feedback_path.exists(),
    }

    if not preferences_path.exists():
        return PreferencesPreloadResult(status="missing", injected=False, **base_payload)

    if not preferences_path.is_file():
        return PreferencesPreloadResult(
            status="invalid",
            injected=False,
            error_code="not_a_file",
            **base_payload,
        )

    try:
        raw_bytes = preferences_path.read_bytes()
    except OSError as exc:
        return PreferencesPreloadResult(
            status="read_error",
            injected=False,
            error_code=_read_error_code(exc),
            **base_payload,
        )

    # Invalid means the file exists but cannot be treated as the plain UTF-8
    # markdown contract the host is expected to inject.
    try:
        raw_content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return PreferencesPreloadResult(
            status="invalid",
            injected=False,
            error_code="invalid_utf8",
            **base_payload,
        )

    if "\x00" in raw_content:
        return PreferencesPreloadResult(
            status="invalid",
            injected=False,
            error_code="non_text_content",
            **base_payload,
        )

    injection_text = build_preferences_injection(raw_content)
    return PreferencesPreloadResult(
        status="loaded",
        injected=True,
        raw_content=raw_content,
        injection_text=injection_text,
        **base_payload,
    )


def preload_preferences_for_workspace(
    workspace_root: str | Path,
    *,
    global_config_path: str | Path | None = None,
) -> PreferencesPreloadResult:
    """Resolve config and preload preferences for a workspace in one step."""
    config = load_runtime_config(workspace_root, global_config_path=global_config_path)
    return preload_preferences(config)


def build_preferences_injection(raw_content: str) -> str:
    """Wrap raw preference text in the stable host injection prefix."""
    trimmed = raw_content.strip()
    if not trimmed:
        return _PREFERENCES_PROMPT_PREFIX
    return f"{_PREFERENCES_PROMPT_PREFIX}\n\n{trimmed}"


def preferences_have_confirmed_entries(raw_content: str) -> bool:
    """Return whether a preferences file contains explicit durable preferences."""
    trimmed = raw_content.strip()
    if not trimmed:
        return False
    normalized = trimmed.casefold()
    for placeholder in _PREFERENCES_PLACEHOLDER_LINES:
        if placeholder.casefold() in normalized:
            return False
    return True


def _read_error_code(exc: OSError) -> str:
    if getattr(exc, "errno", None) is None:
        return "os_read_error"
    return f"os_error_{exc.errno}"


__all__ = [
    "PREFERENCES_PRELOAD_STATUSES",
    "PreferencesPreloadResult",
    "PreferencesPreloadStatus",
    "build_preferences_injection",
    "preferences_have_confirmed_entries",
    "preload_preferences",
    "preload_preferences_for_workspace",
    "resolve_feedback_path",
    "resolve_preferences_path",
]
