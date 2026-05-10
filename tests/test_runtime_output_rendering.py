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


class TestNextHintMapping(unittest.TestCase):
    """3a.2-regression: Next hint uses handoff_kind, not route_name."""

    def _render_next(self, handoff_kind: str, route_name: str = "plan_only", **handoff_kw: Any) -> str:
        handoff = RuntimeHandoff(
            schema_version="1", route_name=route_name, run_id="test",
            handoff_kind=handoff_kind, **handoff_kw,
        )
        result = _minimal_result(route_name=route_name, handoff=handoff)
        rendered = render_runtime_output(
            result, brand="test", language="en-US", title_color="none", use_color=False,
        )
        for line in rendered.splitlines():
            if line.startswith("Next:"):
                return line
        return ""

    def test_develop_kinds_all_map_to_workflow_hint(self) -> None:
        for route in ("quick_fix", "resume_active", "exec_plan"):
            hint = self._render_next("develop", route_name=route)
            self.assertIn("downstream stages", hint, msg=f"route={route}")

    def test_plan_kind_maps_to_plan_hint(self) -> None:
        hint = self._render_next("plan")
        self.assertIn("plan review", hint)

    def test_clarification_kind_maps_to_answer_hint(self) -> None:
        hint = self._render_next("clarification", route_name="clarification_pending")
        self.assertIn("missing facts", hint)

    def test_decision_kind_maps_to_decision_hint(self) -> None:
        hint = self._render_next("decision", route_name="decision_pending")
        self.assertIn("confirm", hint)

    def test_consult_kind_maps_to_consult_hint(self) -> None:
        hint = self._render_next("consult", route_name="consult")
        self.assertIn("discussion", hint)

    def test_reject_kind_maps_to_reject_hint(self) -> None:
        hint = self._render_next("reject", route_name="proposal_rejected")
        self.assertIn("rejected", hint)

    def test_archive_completed_maps_to_success_hint(self) -> None:
        hint = self._render_next(
            "archive", route_name="archive_lifecycle",
            artifacts={"archive_receipt_status": "completed"},
        )
        self.assertIn("Review", hint)

    def test_archive_incomplete_maps_to_retry_hint(self) -> None:
        hint = self._render_next("archive", route_name="archive_lifecycle")
        self.assertIn("retry", hint)

    def test_state_conflict_active_maps_to_conflict_hint(self) -> None:
        hint = self._render_next(
            "state_conflict", route_name="state_conflict",
            required_host_action="resolve_state_conflict",
        )
        self.assertIn("cancel", hint)

    def test_state_conflict_cleared_maps_to_continue_hint(self) -> None:
        hint = self._render_next(
            "state_conflict", route_name="state_conflict",
            required_host_action="continue_host_develop",
        )
        self.assertIn("downstream stages", hint)


if __name__ == "__main__":
    unittest.main()
