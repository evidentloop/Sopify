# Test classification: contract
"""Regression tests for runtime output rendering (P4c surface cleanup)."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime._models.handoff import RecoveredContext, RuntimeHandoff, RuntimeResult
from runtime._models.core import RouteDecision
from runtime.output import render_runtime_output, _execution_gate_line, _GATE_STATUS_DISPLAY
from runtime.gate_output import render_gate_text


def _minimal_route(route_name: str = "plan_only", **kwargs: Any) -> RouteDecision:
    defaults: dict[str, Any] = {
        "route_name": route_name,
        "request_text": "test request",
        "reason": "test reason",
    }
    defaults.update(kwargs)
    return RouteDecision(**defaults)


def _minimal_result(
    route_name: str = "plan_only",
    loaded_files: tuple[str, ...] = (),
    **kwargs: Any,
) -> RuntimeResult:
    route_kwargs = {}
    result_kwargs = {}
    for k, v in kwargs.items():
        if k in {"reason", "request_text", "active_run_action"}:
            route_kwargs[k] = v
        else:
            result_kwargs[k] = v
    return RuntimeResult(
        route=_minimal_route(route_name, **route_kwargs),
        recovered_context=RecoveredContext(loaded_files=loaded_files),
        **result_kwargs,
    )


class TestContextBlockRendering(unittest.TestCase):
    """F6-regression: loaded_files must appear as a Context block, not disappear."""

    def test_loaded_files_render_as_context_section(self) -> None:
        result = _minimal_result(loaded_files=("plan/summary.md", "blueprint/README.md"))
        rendered = render_runtime_output(
            result, brand="test", language="en-US", title_color="none", use_color=False,
        )
        self.assertIn("Context: 2 files", rendered)
        self.assertIn("plan/summary.md", rendered)
        self.assertIn("blueprint/README.md", rendered)

    def test_empty_loaded_files_omits_context_section(self) -> None:
        result = _minimal_result(loaded_files=())
        rendered = render_runtime_output(
            result, brand="test", language="en-US", title_color="none", use_color=False,
        )
        self.assertNotIn("Context:", rendered)

    def test_loaded_files_not_mixed_into_changes(self) -> None:
        result = _minimal_result(loaded_files=("plan/summary.md",))
        rendered = render_runtime_output(
            result, brand="test", language="en-US", title_color="none", use_color=False,
        )
        changes_idx = rendered.index("Changes:")
        context_idx = rendered.index("Context:")
        self.assertLess(context_idx, changes_idx, "Context block should appear before Changes")


def _handoff_with_gate(gate_status: str) -> RuntimeHandoff:
    return RuntimeHandoff(
        schema_version="1",
        route_name="plan_only",
        run_id="test-run",
        artifacts={"execution_gate": {"gate_status": gate_status}},
    )


class TestGateStatusFallback(unittest.TestCase):
    """F6-regression: unknown gate_status must not leak raw internal codes."""

    def test_known_status_renders_display_label(self) -> None:
        for language, expected in (("en-US", "Ready"), ("zh-CN", "就绪")):
            result = _minimal_result(handoff=_handoff_with_gate("ready"))
            line = _execution_gate_line(result, language)
            self.assertIn(expected, line, msg=f"language={language}")

    def test_unknown_gate_status_falls_back_to_blocked_en(self) -> None:
        result = _minimal_result(handoff=_handoff_with_gate("experimental_new_state_xyz"))
        line = _execution_gate_line(result, "en-US")
        self.assertIn("Blocked", line)
        self.assertNotIn("experimental_new_state_xyz", line)

    def test_unknown_gate_status_falls_back_to_blocked_zh(self) -> None:
        result = _minimal_result(handoff=_handoff_with_gate("experimental_new_state_xyz"))
        line = _execution_gate_line(result, "zh-CN")
        self.assertIn("阻断", line)
        self.assertNotIn("experimental_new_state_xyz", line)


class TestGateOutputNoRouteExposure(unittest.TestCase):
    """F6-regression: render_gate_text must not expose internal route names."""

    def test_route_field_not_in_gate_text(self) -> None:
        payload: dict[str, Any] = {
            "status": "ready",
            "allowed_response_mode": "unrestricted",
            "runtime": {
                "route_name": "workflow",
                "reason": "plan matched",
            },
        }
        text = render_gate_text(payload)
        for line in text.splitlines():
            self.assertFalse(
                line.strip().startswith("route:"),
                msg=f"route: field leaked in gate text line: {line!r}",
            )

    def test_reason_still_visible_in_gate_text(self) -> None:
        payload: dict[str, Any] = {
            "status": "ready",
            "runtime": {
                "route_name": "plan_only",
                "reason": "plan matched",
            },
        }
        text = render_gate_text(payload)
        self.assertIn("reason: plan matched", text)

    def test_gate_text_without_runtime_section(self) -> None:
        payload: dict[str, Any] = {"status": "error"}
        text = render_gate_text(payload)
        self.assertNotIn("route:", text)
        self.assertIn("status: error", text)


if __name__ == "__main__":
    unittest.main()
