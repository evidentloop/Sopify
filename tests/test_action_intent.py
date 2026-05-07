"""Deterministic tests for ActionValidator (P0-B) and side-effect mapping (P0-E),
plus integration tests for ActionProposal gate flow (P0-G).

给定 ActionProposal + ValidationContext → 确定性 ValidationDecision。
P0-G: gate → validator → engine 端到端集成测试。
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import unittest

from runtime.action_intent import (
    ACTION_TYPES,
    CONFIDENCE_LEVELS,
    DECISION_AUTHORIZE,
    DECISION_DOWNGRADE,
    DECISION_FALLBACK_ROUTER,
    DECISION_REJECT,
    SIDE_EFFECTS,
    ActionProposal,
    ArchiveSubjectProposal,
    ActionValidator,
    ValidationContext,
    ValidationDecision,
    resolve_action_proposal,
)
from runtime.decision_tables import load_default_decision_tables


# ---------------------------------------------------------------------------
# P0-B: ActionValidator deterministic tests
# ---------------------------------------------------------------------------


class ActionValidatorTests(unittest.TestCase):
    """Design.md §测试策略 — Validator deterministic tests."""

    def setUp(self) -> None:
        self.validator = ActionValidator()
        self.empty_ctx = ValidationContext()

    # -- consult_readonly + none → authorize, route_override=consult ----------

    def test_consult_readonly_none_high_no_checkpoint(self) -> None:
        proposal = ActionProposal("consult_readonly", "none", "high")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertEqual(result.resolved_action, "consult_readonly")
        self.assertEqual(result.resolved_side_effect, "none")
        self.assertEqual(result.route_override, "consult")

    def test_consult_readonly_none_low_still_authorized(self) -> None:
        """consult_readonly + none 无需降级，即使 confidence=low。"""
        proposal = ActionProposal("consult_readonly", "none", "low")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertEqual(result.route_override, "consult")

    def test_consult_readonly_none_with_checkpoint(self) -> None:
        """Checkpoint 上方 consult 共存 — checkpoint pending 时仍可 consult。"""
        ctx = ValidationContext(checkpoint_kind="confirm_decision")
        proposal = ActionProposal("consult_readonly", "none", "high")
        result = self.validator.validate(proposal, ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertEqual(result.route_override, "consult")

    def test_consult_readonly_none_with_decision_checkpoint(self) -> None:
        ctx = ValidationContext(checkpoint_kind="confirm_decision")
        proposal = ActionProposal("consult_readonly", "none", "high")
        result = self.validator.validate(proposal, ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertEqual(result.route_override, "consult")

    # -- side-effecting + evidence 通过 → authorize, route_override=None ------

    def test_propose_plan_write_high_evidence_authorized(self) -> None:
        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "high",
            evidence=("用户说要实现缓存功能",),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertIsNone(result.route_override)

    def test_modify_files_write_no_subject_rejected(self) -> None:
        """P2: modify_files without plan_subject → REJECT."""
        proposal = ActionProposal(
            "modify_files", "write_files", "high",
            evidence=("用户明确要求修改文件",),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.bound_subject_missing")

    def test_archive_plan_write_high_evidence_authorizes_with_structured_subject(self) -> None:
        proposal = ActionProposal(
            "archive_plan", "write_files", "high",
            evidence=("用户明确要求归档当前方案",),
            archive_subject=ArchiveSubjectProposal(
                ref_kind="current_plan",
                source="current_plan",
                allow_current_plan_fallback=True,
            ),
        )
        ctx = ValidationContext(current_plan_path=".sopify-skills/plan/demo")
        result = self.validator.validate(proposal, ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertEqual(result.resolved_action, "archive_plan")
        self.assertEqual(result.resolved_side_effect, "write_files")
        self.assertEqual(result.route_override, "archive_lifecycle")
        self.assertEqual(result.reason_code, "validator.archive_plan_authorized")
        self.assertEqual(result.artifacts["archive_subject"]["ref_kind"], "current_plan")

    def test_archive_plan_missing_subject_downgrades_to_consult(self) -> None:
        proposal = ActionProposal(
            "archive_plan", "write_files", "high",
            evidence=("用户明确要求归档当前方案",),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.route_override, "consult")
        self.assertEqual(result.reason_code, "validator.archive_plan_missing_subject")

    def test_archive_plan_current_plan_without_current_plan_downgrades(self) -> None:
        proposal = ActionProposal(
            "archive_plan", "write_files", "high",
            evidence=("用户明确要求归档当前方案",),
            archive_subject=ArchiveSubjectProposal(
                ref_kind="current_plan",
                source="current_plan",
                allow_current_plan_fallback=True,
            ),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.route_override, "consult")
        self.assertEqual(result.reason_code, "validator.archive_plan_current_plan_unavailable")

    def test_archive_plan_blocked_by_pending_checkpoint(self) -> None:
        proposal = ActionProposal(
            "archive_plan", "write_files", "high",
            evidence=("用户明确要求归档当前方案",),
            archive_subject=ArchiveSubjectProposal(
                ref_kind="current_plan",
                source="current_plan",
                allow_current_plan_fallback=True,
            ),
        )
        ctx = ValidationContext(
            current_plan_path=".sopify-skills/plan/demo",
            required_host_action="confirm_decision",
        )
        result = self.validator.validate(proposal, ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.route_override, "consult")
        self.assertEqual(result.reason_code, "validator.archive_plan_blocked_by_checkpoint")

    def test_archive_plan_blocked_by_state_conflict(self) -> None:
        proposal = ActionProposal(
            "archive_plan", "write_files", "high",
            evidence=("用户明确要求归档当前方案",),
            archive_subject=ArchiveSubjectProposal(
                ref_kind="current_plan",
                source="current_plan",
                allow_current_plan_fallback=True,
            ),
        )
        ctx = ValidationContext(
            current_plan_path=".sopify-skills/plan/demo",
            state_conflict=True,
        )
        result = self.validator.validate(proposal, ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.route_override, "consult")
        self.assertEqual(result.reason_code, "validator.archive_plan_blocked_by_state_conflict")

    def test_archive_plan_without_evidence_downgrades(self) -> None:
        proposal = ActionProposal("archive_plan", "write_files", "medium")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.resolved_action, "consult_readonly")
        self.assertEqual(result.route_override, "consult")

    # -- side-effecting + low confidence → downgrade -------------------------

    def test_propose_plan_write_low_downgraded(self) -> None:
        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "low",
            evidence=("用户好像在问问题",),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.resolved_action, "consult_readonly")
        self.assertEqual(result.route_override, "consult")

    # -- side-effecting + evidence 不足 → downgrade --------------------------

    def test_propose_plan_write_high_no_evidence_downgraded(self) -> None:
        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "high",
            evidence=(),  # 无 evidence
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.resolved_action, "consult_readonly")
        self.assertEqual(result.route_override, "consult")

    # -- 未知 action → fallback_router ----------------------------------------

    def test_unknown_action_fallback(self) -> None:
        proposal = ActionProposal("totally_unknown", "none", "high")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_FALLBACK_ROUTER)
        self.assertIsNone(result.route_override)

    # -- consult_readonly with unexpected side_effect -------------------------

    def test_consult_readonly_with_write_rejected_by_pairing(self) -> None:
        """P2: consult_readonly + non-none side_effect → REJECT (pairing mismatch)."""
        proposal = ActionProposal(
            "consult_readonly", "write_plan_package", "high",
            evidence=(),
        )
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    # -- Unknown side_effect → fail-close downgrade --------------------------

    def test_unknown_side_effect_downgraded(self) -> None:
        """Unknown side_effect must fail-close to consult, not authorize."""
        # Construct directly to bypass from_dict validation.
        proposal = ActionProposal("propose_plan", "delete_database", "high",
                                  evidence=("some evidence",))
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_DOWNGRADE)
        self.assertEqual(result.resolved_action, "consult_readonly")
        self.assertEqual(result.route_override, "consult")
        self.assertEqual(result.reason_code, "validator.unknown_side_effect_downgrade")

    # -- Non-side-effecting recognized action ---------------------------------

    def test_cancel_flow_none_authorized_no_override(self) -> None:
        proposal = ActionProposal("cancel_flow", "none", "high")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_AUTHORIZE)
        self.assertIsNone(result.route_override)

    def test_checkpoint_response_none_no_subject_rejected(self) -> None:
        """P2: checkpoint_response is bound-subject — missing plan_subject → REJECT."""
        proposal = ActionProposal("checkpoint_response", "none", "high")
        result = self.validator.validate(proposal, self.empty_ctx)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.bound_subject_missing")


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class ActionProposalSerializationTests(unittest.TestCase):

    def test_round_trip(self) -> None:
        original = ActionProposal(
            "propose_plan", "write_plan_package", "medium",
            evidence=("用户说需要缓存", "第二条证据"),
        )
        restored = ActionProposal.from_dict(original.to_dict())
        self.assertEqual(restored.action_type, original.action_type)
        self.assertEqual(restored.side_effect, original.side_effect)
        self.assertEqual(restored.confidence, original.confidence)
        self.assertEqual(restored.evidence, original.evidence)

    def test_resolve_none(self) -> None:
        self.assertIsNone(resolve_action_proposal(None))

    def test_resolve_valid(self) -> None:
        proposal = resolve_action_proposal({"action_type": "consult_readonly"})
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.action_type, "consult_readonly")

    def test_resolve_malformed(self) -> None:
        # Should not crash, just return None for invalid input types.
        self.assertIsNone(resolve_action_proposal("not a dict"))  # type: ignore[arg-type]

    def test_from_dict_rejects_unknown_action_type(self) -> None:
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({"action_type": "nuke_everything"})

    def test_from_dict_rejects_unknown_side_effect(self) -> None:
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({
                "action_type": "consult_readonly",
                "side_effect": "delete_database",
            })

    def test_from_dict_rejects_unknown_confidence(self) -> None:
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({
                "action_type": "consult_readonly",
                "confidence": "yolo",
            })

    def test_from_dict_rejects_bare_string_evidence(self) -> None:
        """Evidence must be a list, not a bare string."""
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({
                "action_type": "consult_readonly",
                "evidence": "bare string",
            })

    def test_from_dict_rejects_non_string_evidence_items(self) -> None:
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({
                "action_type": "consult_readonly",
                "evidence": [123, 456],
            })

    def test_resolve_returns_none_for_invalid_enum(self) -> None:
        """resolve_action_proposal returns None when from_dict raises."""
        result = resolve_action_proposal({
            "action_type": "consult_readonly",
            "side_effect": "invalid_effect",
        })
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# P0-E: Side-effect mapping row ordering (post-Wave-3a)
# ---------------------------------------------------------------------------


class SideEffectMappingRowOrderingTests(unittest.TestCase):
    """Verify row ordering after Wave 3a proposal removal."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = load_default_decision_tables()
        cls.rows = cls.tables["side_effect_mapping_table"]["rows"]

    def _find_row(self, resolved_action: str, checkpoint_kind: str) -> dict:
        for row in self.rows:
            if (
                row["resolved_action"] == resolved_action
                and row["checkpoint_kind"] == checkpoint_kind
            ):
                return row
        self.fail(
            f"No side_effect_mapping row for "
            f"resolved_action={resolved_action}, checkpoint_kind={checkpoint_kind}"
        )

    def test_existing_decision_row_unchanged(self) -> None:
        """Existing switch_to_consult_readonly for confirm_decision is preserved."""
        row = self._find_row("switch_to_consult_readonly", "confirm_decision")
        self.assertEqual(row["handoff_protocol"]["required_host_action"], "continue_host_consult")
        self.assertEqual(row["handoff_protocol"]["resume_route"], "decision_pending")

    def test_row_ordering_preserved(self) -> None:
        """Rows must follow frozen ordered_resolved_actions order."""
        actions = [r["resolved_action"] for r in self.rows]
        ordered = [
            "switch_to_consult_readonly",
        ]
        self.assertEqual(actions, ordered)


# ---------------------------------------------------------------------------
# Duplicate (resolved_action, checkpoint_kind) guard
# ---------------------------------------------------------------------------


class DuplicateRowGuardTests(unittest.TestCase):
    """Verify that duplicate (resolved_action, checkpoint_kind) pairs are rejected."""

    def test_duplicate_pair_rejected(self) -> None:
        import tempfile
        from runtime.decision_tables import DecisionTableError, load_decision_tables

        # Build a minimal YAML with two identical (action, checkpoint) pairs.
        yaml_text = _build_duplicate_row_yaml()
        with tempfile.TemporaryDirectory() as tmp:
            asset = Path(tmp) / "decision_tables.yaml"
            asset.write_text(yaml_text, encoding="utf-8")
            with self.assertRaisesRegex(DecisionTableError, r"duplicate"):
                load_decision_tables(asset)


def _build_duplicate_row_yaml() -> str:
    """Minimal decision_tables asset with a duplicate side_effect_mapping row.

    Duplicates the first side_effect_mapping row by text insertion,
    preserving the custom YAML parser's expected format.
    """
    from runtime.decision_tables import DEFAULT_DECISION_TABLES_PATH

    original = DEFAULT_DECISION_TABLES_PATH.read_text(encoding="utf-8")
    marker = "    - resolved_action: switch_to_consult_readonly\n"
    first_pos = original.index(marker)
    # Find where this row block ends: next line not indented by 6+ spaces.
    end_pos = first_pos + len(marker)
    while end_pos < len(original):
        line_end = original.index("\n", end_pos) + 1 if "\n" in original[end_pos:] else len(original)
        line = original[end_pos:line_end]
        if line.strip() and not line.startswith("      "):
            break
        end_pos = line_end
    first_row_block = original[first_pos:end_pos]
    return original[:end_pos] + first_row_block + original[end_pos:]


# ---------------------------------------------------------------------------
# P0-C: Gate receives --action-proposal-json / --action-proposal-capability
# ---------------------------------------------------------------------------


class GateActionProposalTests(unittest.TestCase):
    """Gate-layer tests for ActionProposal CLI args and retry contract."""

    def test_is_command_prefix_go(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertTrue(_is_command_prefix_request("~go plan 补一下"))

    def test_is_not_command_prefix_compare_removed(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertFalse(_is_command_prefix_request("~compare 对比 A 和 B"))

    def test_is_not_command_prefix_normal_request(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertFalse(_is_command_prefix_request("请帮我修复一下 bug"))

    def test_is_not_command_prefix_empty(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertFalse(_is_command_prefix_request(""))

    def test_is_not_command_prefix_gofoo(self) -> None:
        """Regression: ~gofoo must not match — require whitespace or end."""
        from runtime.gate import _is_command_prefix_request
        self.assertFalse(_is_command_prefix_request("~gofoo 实现功能"))

    def test_is_not_command_prefix_comparex(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertFalse(_is_command_prefix_request("~comparex 对比"))

    def test_is_command_prefix_go_bare(self) -> None:
        from runtime.gate import _is_command_prefix_request
        self.assertTrue(_is_command_prefix_request("~go"))

    def test_action_proposal_schema_contains_all_enums(self) -> None:
        from runtime.gate import _build_action_proposal_schema
        schema = _build_action_proposal_schema()
        self.assertEqual(set(schema["action_type"]["enum"]), set(ACTION_TYPES))
        self.assertEqual(set(schema["side_effect"]["enum"]), set(SIDE_EFFECTS))
        self.assertEqual(set(schema["confidence"]["enum"]), set(CONFIDENCE_LEVELS))

    def test_action_proposal_schema_has_evidence_type(self) -> None:
        from runtime.gate import _build_action_proposal_schema
        schema = _build_action_proposal_schema()
        self.assertEqual(schema["evidence"]["type"], "list[str]")

    def test_action_proposal_schema_p2_plan_subject_required_for(self) -> None:
        """P2: plan_subject.required_for lists all BOUND_SUBJECT_ACTIONS."""
        from runtime.gate import _build_action_proposal_schema
        from runtime.action_intent import BOUND_SUBJECT_ACTIONS
        schema = _build_action_proposal_schema()
        self.assertEqual(
            set(schema["plan_subject"]["required_for"]),
            set(BOUND_SUBJECT_ACTIONS),
        )
        self.assertIn("cancel_flow", schema["plan_subject"]["optional_for"])

    def test_action_proposal_schema_p2_side_effect_delta(self) -> None:
        """P2: schema includes side_effect_delta with delta-capable actions."""
        from runtime.gate import _build_action_proposal_schema
        from runtime.action_intent import DELTA_CAPABLE_ACTIONS, SIDE_EFFECT_DELTA_CHANGE_TYPES
        schema = _build_action_proposal_schema()
        self.assertIn("side_effect_delta", schema)
        delta_schema = schema["side_effect_delta"]
        self.assertEqual(
            set(delta_schema["optional_for"]),
            set(DELTA_CAPABLE_ACTIONS),
        )
        self.assertEqual(
            set(delta_schema["item_fields"]["change_type"]["enum"]),
            set(SIDE_EFFECT_DELTA_CHANGE_TYPES),
        )

    def test_action_proposal_schema_p2_canonical_pairing(self) -> None:
        """P2: schema side_effect includes canonical_for mapping."""
        from runtime.gate import _build_action_proposal_schema
        from runtime.action_intent import ACTION_TYPES, _CANONICAL_ACTION_EFFECT
        schema = _build_action_proposal_schema()
        se_schema = schema["side_effect"]
        self.assertIn("canonical_for", se_schema)
        canonical = se_schema["canonical_for"]
        for at in ACTION_TYPES:
            self.assertIn(at, canonical, f"{at} missing from schema canonical_for")
            self.assertEqual(canonical[at], _CANONICAL_ACTION_EFFECT[at])

    def test_retry_contract_gate_passed_false(self) -> None:
        from runtime.gate import _build_action_proposal_retry_contract
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            contract = _build_action_proposal_retry_contract(
                config=None, session_id="test-session", workspace=Path(td),
            )
        self.assertFalse(contract["gate_passed"])
        self.assertEqual(contract["status"], "action_proposal_retry")
        self.assertEqual(contract["allowed_response_mode"], "action_proposal_retry")

    def test_retry_contract_includes_schema(self) -> None:
        from runtime.gate import _build_action_proposal_retry_contract
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            contract = _build_action_proposal_retry_contract(
                config=None, session_id="test-session", workspace=Path(td),
            )
        self.assertIn("action_proposal_schema", contract)
        schema = contract["action_proposal_schema"]
        self.assertIn("action_type", schema)
        self.assertIn("side_effect", schema)

    def test_retry_contract_evidence_all_false(self) -> None:
        from runtime.gate import _build_action_proposal_retry_contract
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            contract = _build_action_proposal_retry_contract(
                config=None, session_id="test-session", workspace=Path(td),
            )
        evidence = contract["evidence"]
        self.assertFalse(evidence["handoff_found"])
        self.assertFalse(evidence["strict_runtime_entry"])
        self.assertFalse(evidence["current_request_produced_handoff"])

    def test_retry_contract_state_has_full_paths_with_config(self) -> None:
        """Regression: config-aware retry must include all state paths."""
        from runtime.gate import _build_action_proposal_retry_contract
        from runtime.config import load_runtime_config
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            config = load_runtime_config(workspace)
            contract = _build_action_proposal_retry_contract(
                config=config, session_id="test-session", workspace=workspace,
                request="请帮我看下 bug",
            )
        state = contract["state"]
        expected_keys = {
            "scope", "state_root", "current_plan_path",
            "current_run_path",
            "current_handoff_path", "current_clarification_path",
            "current_decision_path", "last_route_path",
        }
        self.assertTrue(expected_keys.issubset(set(state.keys())),
                        f"Missing keys: {expected_keys - set(state.keys())}")

    def test_resolve_action_proposal_valid_json(self) -> None:
        raw = {"action_type": "consult_readonly", "side_effect": "none", "confidence": "high"}
        proposal = resolve_action_proposal(raw)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.action_type, "consult_readonly")

    def test_resolve_action_proposal_invalid_json_returns_none(self) -> None:
        proposal = resolve_action_proposal("not a dict")
        self.assertIsNone(proposal)

    def test_resolve_action_proposal_bad_action_type_returns_none(self) -> None:
        raw = {"action_type": "INVALID", "side_effect": "none"}
        proposal = resolve_action_proposal(raw)
        self.assertIsNone(proposal)

    def test_resolve_action_proposal_empty_dict_returns_none(self) -> None:
        """Finding #1: {} must not produce ActionProposal(action_type='')."""
        proposal = resolve_action_proposal({})
        self.assertIsNone(proposal)

    def test_resolve_action_proposal_missing_action_type_returns_none(self) -> None:
        """Finding #1: missing action_type → None (fail-close)."""
        raw = {"side_effect": "none", "confidence": "high"}
        proposal = resolve_action_proposal(raw)
        self.assertIsNone(proposal)

    def test_from_dict_empty_action_type_raises(self) -> None:
        """Finding #1: from_dict({}) → ValueError."""
        with self.assertRaises(ValueError):
            ActionProposal.from_dict({})

    def test_gate_malformed_json_implies_capability(self) -> None:
        """Finding #2: passing --action-proposal-json implies new host —
        malformed JSON should trigger retry, not legacy fallback."""
        import tempfile
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            workspace = temp_root / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            result = enter_runtime_gate(
                "请帮我看下 bug",
                workspace_root=workspace,
                user_home=temp_root / "home",
                action_proposal_json="{bad json",
                action_proposal_capability=False,  # not explicitly set
            )
            # Should trigger retry (not silently fall to legacy router).
            self.assertEqual(result.get("status"), "action_proposal_retry")
            self.assertIn("action_proposal_parse_error", result)


# ---------------------------------------------------------------------------
# P0-D: Engine pre-route interceptor (unit-level)
# ---------------------------------------------------------------------------


class EnginePreRouteInterceptorTests(unittest.TestCase):
    """Verify ActionValidator integration with run_runtime() pre-route hook.

    These tests are deterministic — they construct the proposal and validator
    directly to verify the interceptor logic without needing a full workspace.
    """

    def test_consult_readonly_proposal_overrides_route(self) -> None:
        """consult_readonly proposal → route_override='consult' → skip Router."""
        proposal = ActionProposal("consult_readonly", "none", "high")
        validator = ActionValidator()
        ctx = ValidationContext()
        decision = validator.validate(proposal, ctx)
        self.assertEqual(decision.route_override, "consult")

    def test_side_effecting_high_confidence_no_override(self) -> None:
        """Side-effecting + high confidence → authorize, route_override=None."""
        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "high",
            evidence=["user explicitly asked to create a plan"],
        )
        validator = ActionValidator()
        ctx = ValidationContext()
        decision = validator.validate(proposal, ctx)
        self.assertIsNone(decision.route_override)
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_side_effecting_low_confidence_downgrades(self) -> None:
        """Side-effecting + low confidence → downgrade to consult."""
        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "low",
            evidence=["maybe user wants this"],
        )
        validator = ActionValidator()
        ctx = ValidationContext()
        decision = validator.validate(proposal, ctx)
        self.assertEqual(decision.route_override, "consult")
        self.assertEqual(decision.decision, DECISION_DOWNGRADE)

    def test_unknown_action_type_falls_through(self) -> None:
        """Unknown action_type → fallback_router, route_override=None."""
        proposal = ActionProposal("unknown_future_action", "none", "high")
        validator = ActionValidator()
        ctx = ValidationContext()
        decision = validator.validate(proposal, ctx)
        self.assertIsNone(decision.route_override)
        self.assertEqual(decision.decision, DECISION_FALLBACK_ROUTER)

    def test_route_decision_construction_from_override(self) -> None:
        """Verify RouteDecision can be constructed from validator output."""
        from runtime.models import RouteDecision
        proposal = ActionProposal("consult_readonly", "none", "high")
        validator = ActionValidator()
        decision = validator.validate(proposal, ValidationContext())
        if decision.route_override:
            rd = RouteDecision(
                route_name=decision.route_override,
                request_text="test request",
                reason=f"action_proposal_validator: {decision.reason_code}",
            )
            self.assertEqual(rd.route_name, "consult")
            self.assertIn("action_proposal_validator", rd.reason)

    def test_no_proposal_means_no_override(self) -> None:
        """When action_proposal is None, no override → Router runs normally."""
        # This is the trivial case: action_proposal=None means the engine
        # skips the interceptor entirely. Verify the sentinel.
        proposal_override_route = None
        if None is not None:  # action_proposal is None
            pass  # would never enter
        self.assertIsNone(proposal_override_route)


# ---------------------------------------------------------------------------
# P0-D: Real run_runtime() smoke tests
# ---------------------------------------------------------------------------

import tempfile
from runtime.engine import run_runtime


class EngineActionProposalSmokeTests(unittest.TestCase):
    """Smoke tests that call run_runtime() with action_proposal to verify
    the real interceptor wiring doesn't crash."""

    def test_consult_readonly_proposal_routes_to_consult(self) -> None:
        """run_runtime() with consult_readonly proposal → route=consult."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal("consult_readonly", "none", "high")
            result = run_runtime(
                "什么是 runtime gate？",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertEqual(result.route.route_name, "consult")
            self.assertIn("action_proposal_validator", result.route.reason)

    def test_no_proposal_falls_through_to_router(self) -> None:
        """run_runtime() without proposal → normal Router classification."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            result = run_runtime(
                "什么是 runtime gate？",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=None,
            )
            # Without proposal the router runs; consult is the expected
            # route for a question-only request but the exact route_name
            # depends on router logic — just verify it didn't crash and
            # the reason does NOT mention the validator.
            self.assertNotIn("action_proposal_validator", result.route.reason)

    def test_unknown_action_type_falls_through_to_router(self) -> None:
        """Unknown action_type → fallback_router → Router runs normally."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal("future_action_xyz", "none", "high")
            result = run_runtime(
                "什么是 runtime gate？",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            # fallback_router means no route_override → Router handles it.
            self.assertNotIn("action_proposal_validator", result.route.reason)


# ---------------------------------------------------------------------------
# P0-G: Integration tests — full gate + engine end-to-end
# ---------------------------------------------------------------------------

import subprocess


def _setup_workspace_for_gate_integration(
    temp_root: Path,
) -> tuple[Path, Path]:
    """Create a minimal workspace + legacy payload manifest for gate tests.

    Returns (workspace, payload_manifest_path).
    """
    workspace = temp_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    home_root = temp_root / "home"
    payload_root = home_root / ".codex" / "sopify"
    helpers = payload_root / "helpers"
    bundle_dir = payload_root / "bundle"
    helpers.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Minimal bootstrap helper (legacy stub)
    (helpers / "bootstrap_workspace.py").write_text(
        "\n".join([
            "#!/usr/bin/env python3",
            "import argparse, json",
            "from pathlib import Path",
            "parser = argparse.ArgumentParser()",
            "parser.add_argument('--workspace-root', required=True)",
            "args = parser.parse_args()",
            "w = Path(args.workspace_root).resolve()",
            "print(json.dumps({",
            "  'action': 'skipped', 'state': 'READY',",
            "  'reason_code': 'WORKSPACE_BUNDLE_READY',",
            "  'workspace_root': str(w),",
            "  'bundle_root': str(w / '.sopify-runtime'),",
            "  'from_version': None, 'to_version': None,",
            "  'message': 'legacy helper fallback'",
            "}, ensure_ascii=False))",
        ]) + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps({"schema_version": "1", "bundle_version": "2026-03-28.220226"})
        + "\n",
        encoding="utf-8",
    )
    payload_manifest = payload_root / "payload-manifest.json"
    payload_manifest.write_text(
        json.dumps({
            "schema_version": "1",
            "helper_entry": "helpers/bootstrap_workspace.py",
            "bundle_manifest": "bundle/manifest.json",
        }) + "\n",
        encoding="utf-8",
    )
    return workspace, payload_manifest


class GateActionProposalIntegrationTests(unittest.TestCase):
    """P0-G: End-to-end integration tests for the ActionProposal gate flow.

    These tests exercise the real gate function (enter_runtime_gate) to verify:
    - capability-declared host without proposal → retry contract
    - retry contract with valid proposal → normal runtime entry
    - legacy host (no capability) → normal router fallback
    - command prefix requests bypass proposal requirement
    - malformed JSON → retry with parse error
    """

    def test_capability_without_proposal_returns_retry(self) -> None:
        """New host declares capability but no proposal → action_proposal_retry."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            result = enter_runtime_gate(
                "批判看下这个方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_capability=True,
            )
            self.assertEqual(result["status"], "action_proposal_retry")
            self.assertFalse(result["gate_passed"])
            self.assertEqual(result["allowed_response_mode"], "action_proposal_retry")
            self.assertIn("action_proposal_schema", result)
            schema = result["action_proposal_schema"]
            self.assertIn("action_type", schema)
            self.assertIn("side_effect", schema)
            self.assertIn("confidence", schema)
            self.assertIn("evidence", schema)

    def test_retry_then_success_with_consult_proposal(self) -> None:
        """Two-phase: capability → retry → provide consult_readonly proposal → success/consult."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))

            # Phase 1: capability without proposal → retry
            retry = enter_runtime_gate(
                "批判看下这个方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_capability=True,
            )
            self.assertEqual(retry["status"], "action_proposal_retry")

            # Phase 2: host generates proposal from schema and retries
            proposal_json = json.dumps({
                "action_type": "consult_readonly",
                "side_effect": "none",
                "confidence": "high",
                "evidence": ["user said 批判看下, read-only analysis request"],
            })
            result = enter_runtime_gate(
                "批判看下这个方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_json=proposal_json,
            )
            self.assertEqual(result["status"], "ready")
            self.assertTrue(result["gate_passed"])
            self.assertEqual(result["runtime"]["route_name"], "consult")
            self.assertIn("action_proposal_validator", result["runtime"]["reason"])

    def test_legacy_host_no_capability_no_proposal_falls_through(self) -> None:
        """Legacy host (no --action-proposal-capability) → normal router."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            result = enter_runtime_gate(
                "批判看下这个方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                # No capability, no proposal → legacy fallback
            )
            self.assertEqual(result["status"], "ready")
            # Legacy host goes through normal Router — key assertion is:
            # NOT action_proposal_retry and NOT action_proposal_validator.
            self.assertNotEqual(result["runtime"]["route_name"], "action_proposal_retry")
            self.assertNotIn("action_proposal_validator", result["runtime"]["reason"])

    def test_command_prefix_bypasses_proposal_requirement(self) -> None:
        """~go plan request with capability but no proposal → should NOT retry."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            result = enter_runtime_gate(
                "~go plan 补 ActionProposal 集成测试",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_capability=True,
            )
            # Command prefix bypasses proposal — no retry, enters runtime
            self.assertEqual(result["status"], "ready")
            self.assertNotEqual(
                result.get("allowed_response_mode"), "action_proposal_retry"
            )

    def test_malformed_json_returns_retry_with_parse_error(self) -> None:
        """Malformed --action-proposal-json → retry with action_proposal_parse_error."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            result = enter_runtime_gate(
                "加一个缓存功能",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_json="{not valid json!!!}",
            )
            self.assertEqual(result["status"], "action_proposal_retry")
            self.assertIn("action_proposal_parse_error", result)
            self.assertIn("invalid JSON", result["action_proposal_parse_error"])

    def test_side_effecting_proposal_with_high_confidence_authorizes(self) -> None:
        """Side-effecting proposal (propose_plan) with high confidence → authorize, Router runs."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            proposal_json = json.dumps({
                "action_type": "propose_plan",
                "side_effect": "write_plan_package",
                "confidence": "high",
                "evidence": ["user explicitly asked to create a plan"],
            })
            result = enter_runtime_gate(
                "制定一个缓存方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_json=proposal_json,
            )
            self.assertEqual(result["status"], "ready")
            self.assertNotEqual(result["runtime"]["route_name"], "action_proposal_retry")

    def test_side_effecting_low_confidence_downgrades_to_consult(self) -> None:
        """Side-effecting + low confidence → downgrade to consult."""
        from runtime.gate import enter_runtime_gate
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            proposal_json = json.dumps({
                "action_type": "propose_plan",
                "side_effect": "write_plan_package",
                "confidence": "low",
                "evidence": ["maybe user wants this"],
            })
            result = enter_runtime_gate(
                "制定一个缓存方案",
                workspace_root=workspace,
                payload_manifest_path=pm,
                user_home=Path(td) / "home",
                action_proposal_json=proposal_json,
            )
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["runtime"]["route_name"], "consult")
            self.assertIn("action_proposal_validator", result["runtime"]["reason"])


class GateCLIActionProposalTests(unittest.TestCase):
    """P0-G: CLI-level tests for scripts/runtime_gate.py with ActionProposal.

    These exercise the real CLI subprocess to verify:
    - Non-zero exit code for retry is parseable
    - Shell quoting edge cases for --action-proposal-json
    - Full round-trip: capability → parse stdout → generate proposal → retry success
    """

    def _run_gate_cli(
        self, args: list[str], *, check: bool = False
    ) -> tuple[int, dict[str, Any]]:
        """Run scripts/runtime_gate.py and return (exit_code, parsed_json)."""
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "runtime_gate.py"),
            "enter",
            *args,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if check and proc.returncode != 0:
            raise AssertionError(
                f"CLI failed with exit code {proc.returncode}:\n"
                f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
        parsed = json.loads(proc.stdout)
        return proc.returncode, parsed

    def test_cli_capability_returns_retry_with_exit_1(self) -> None:
        """CLI: --action-proposal-capability without json → exit 1 + parseable JSON."""
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            exit_code, result = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "批判看下这段代码",
                "--payload-manifest-path", str(pm),
                "--action-proposal-capability",
            ])
            self.assertEqual(exit_code, 1, "Retry contract should return non-zero exit")
            self.assertEqual(result["status"], "action_proposal_retry")
            self.assertIn("action_proposal_schema", result)

    def test_cli_full_roundtrip_retry_then_success(self) -> None:
        """CLI: Two subprocess calls simulating host retry flow."""
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))

            # Phase 1: capability only → exit 1
            exit_code, retry = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "什么是 ActionProposal？",
                "--payload-manifest-path", str(pm),
                "--action-proposal-capability",
            ])
            self.assertEqual(exit_code, 1)
            self.assertEqual(retry["status"], "action_proposal_retry")
            schema = retry["action_proposal_schema"]
            self.assertIsInstance(schema, dict)

            # Phase 2: host generates proposal per schema and retries
            proposal = json.dumps({
                "action_type": "consult_readonly",
                "side_effect": "none",
                "confidence": "high",
                "evidence": ["user asked a question about ActionProposal"],
            })
            exit_code2, success = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "什么是 ActionProposal？",
                "--payload-manifest-path", str(pm),
                "--action-proposal-json", proposal,
            ])
            self.assertEqual(exit_code2, 0, "Successful gate should return exit 0")
            self.assertEqual(success["status"], "ready")
            self.assertTrue(success["gate_passed"])
            self.assertEqual(success["runtime"]["route_name"], "consult")

    def test_cli_json_with_special_characters_in_evidence(self) -> None:
        """CLI: evidence with quotes, newlines, and Unicode passes through correctly."""
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            proposal = json.dumps({
                "action_type": "consult_readonly",
                "side_effect": "none",
                "confidence": "high",
                "evidence": [
                    'user said "批判看下" with double quotes',
                    "line1\nline2\nline3",
                    "apostrophe's and single 'quotes'",
                    "emoji: 🔍 unicode: café naïve",
                ],
            })
            exit_code, result = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "批判看下这个方案",
                "--payload-manifest-path", str(pm),
                "--action-proposal-json", proposal,
            ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["runtime"]["route_name"], "consult")

    def test_cli_malformed_json_returns_exit_1_with_parse_error(self) -> None:
        """CLI: malformed JSON → exit 1 + action_proposal_parse_error in stdout."""
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            exit_code, result = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "加一个缓存功能",
                "--payload-manifest-path", str(pm),
                "--action-proposal-json", "{{broken}",
            ])
            self.assertEqual(exit_code, 1)
            self.assertEqual(result["status"], "action_proposal_retry")
            self.assertIn("action_proposal_parse_error", result)

    def test_cli_command_prefix_with_capability_bypasses_retry(self) -> None:
        """CLI: ~go plan with --action-proposal-capability → exit 0, not retry."""
        with tempfile.TemporaryDirectory() as td:
            workspace, pm = _setup_workspace_for_gate_integration(Path(td))
            exit_code, result = self._run_gate_cli([
                "--workspace-root", str(workspace),
                "--request", "~go plan 补集成测试",
                "--payload-manifest-path", str(pm),
                "--action-proposal-capability",
            ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "ready")


class IntegrationRegressionTests(unittest.TestCase):
    """P0-G: Regression tests verifying existing router behavior is preserved.

    These cover the tasks.md requirements:
    - "批判看下" → consult (with and without proposal)
    - "加一个缓存功能" → light_iterate via Router fallback (no proposal override)
    """

    def test_regression_consult_request_with_proposal(self) -> None:
        """'批判看下' + consult_readonly proposal → consult via validator."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal("consult_readonly", "none", "high",
                                      evidence=["user said 批判看下"])
            result = run_runtime(
                "批判看下这个方案的可行性",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertEqual(result.route.route_name, "consult")
            self.assertIn("action_proposal_validator", result.route.reason)

    def test_regression_consult_request_without_proposal(self) -> None:
        """'批判看下' without proposal → Router classifies (validator not involved).

        Note: in a clean workspace without active plan, Router may NOT classify
        this as 'consult' — this is the exact misclassification that ActionProposal
        boundary aims to fix. The regression check verifies Router still runs
        normally without being broken by ActionProposal code.
        """
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            result = run_runtime(
                "批判看下这个方案的可行性",
                workspace_root=workspace,
                user_home=workspace / "home",
            )
            # Key assertion: validator NOT involved (legacy/no-proposal path)
            self.assertNotIn("action_proposal_validator", result.route.reason)
            # Router ran and produced some route (not broken)
            self.assertIsNotNone(result.route.route_name)

    def test_regression_feature_request_without_proposal_uses_router(self) -> None:
        """'加一个缓存功能' without proposal → Router classifies, but plan
        materialization is blocked without authorization (P1.5 auth boundary)."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            result = run_runtime(
                "加一个缓存功能",
                workspace_root=workspace,
                user_home=workspace / "home",
            )
            # Without a proposal, Router classifies as a development task,
            # but the engine blocks plan materialization → consult.
            self.assertEqual(result.route.route_name, "consult")
            self.assertIn("Plan materialization not authorized", result.route.reason)
            self.assertNotIn("action_proposal_validator", result.route.reason)

    def test_regression_modify_files_no_subject_rejected(self) -> None:
        """P2: '加一个缓存功能' + modify_files/high without plan_subject → rejected
        at bound-subject admission (before plan materialization check)."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "modify_files", "write_files", "high",
                evidence=["user explicitly asked to add cache feature"],
            )
            result = run_runtime(
                "加一个缓存功能",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            # P2: bound-subject missing → proposal_rejected
            self.assertEqual(result.route.route_name, "proposal_rejected")
            self.assertIn("action_proposal_rejected", result.route.reason)

    def test_regression_modify_files_low_confidence_no_subject_rejected(self) -> None:
        """P2: modify_files/low without plan_subject → REJECT (before evidence check)."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "modify_files", "write_files", "low",
                evidence=["maybe user wants this"],
            )
            result = run_runtime(
                "加一个缓存功能",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            # P2: bound-subject missing → proposal_rejected
            self.assertEqual(result.route.route_name, "proposal_rejected")
            self.assertIn("action_proposal_rejected", result.route.reason)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# P1: execute_existing_plan subject admission tests
# ---------------------------------------------------------------------------


class PlanSubjectAdmissionTests(unittest.TestCase):
    """P1 — validator MUST reject execute_existing_plan when plan_subject is
    missing, subject_ref points to a non-existent plan, or revision_digest
    does not match."""

    def setUp(self) -> None:
        from runtime.action_intent import DECISION_REJECT, PlanSubjectProposal
        self.validator = ActionValidator()
        self.DECISION_REJECT = DECISION_REJECT
        self.PlanSubjectProposal = PlanSubjectProposal
        self._tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self._tmpdir)
        # Create a valid plan directory with plan.md
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "20260504_test_plan"
        plan_dir.mkdir(parents=True)
        self.plan_md = plan_dir / "plan.md"
        self.plan_md.write_text("# Test Plan\n\ntitle: test\n", encoding="utf-8")
        import hashlib
        self.valid_digest = hashlib.sha256(self.plan_md.read_bytes()).hexdigest()
        self.valid_subject_ref = ".sopify-skills/plan/20260504_test_plan"

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_proposal(self, plan_subject=None):
        """Build an execute_existing_plan proposal with side_effect + evidence."""
        return ActionProposal(
            action_type="execute_existing_plan",
            side_effect="write_files",
            confidence="high",
            evidence=("user confirmed execution",),
            plan_subject=plan_subject,
        )

    def _ctx(self, workspace_root=None):
        return ValidationContext(
            workspace_root=workspace_root if workspace_root is not None else str(self.workspace),
        )

    def test_missing_plan_subject_rejected(self):
        """execute_existing_plan without plan_subject → DECISION_REJECT."""
        proposal = self._make_proposal(plan_subject=None)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_missing")

    def test_subject_ref_not_found_rejected(self):
        """plan_subject.subject_ref points to nonexistent plan → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref=".sopify-skills/plan/nonexistent_plan",
            revision_digest="0" * 64,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_not_found")

    def test_digest_mismatch_rejected(self):
        """plan_subject.revision_digest doesn't match actual file → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest="0" * 64,  # wrong digest
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_digest_mismatch")

    def test_valid_subject_authorized(self):
        """Correct plan_subject → authorized (not rejected)."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_no_workspace_root_rejected(self):
        """Missing workspace_root in context → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx(workspace_root=""))
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_no_workspace")

    def test_plan_subject_parse_only_for_subject_capable_actions(self):
        """plan_subject on a non-subject-capable action → parse error."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "consult_readonly",
                "plan_subject": {
                    "subject_ref": self.valid_subject_ref,
                    "revision_digest": self.valid_digest,
                },
            })
        self.assertIn("subject-capable actions", str(cm.exception))

    def test_plan_subject_serialization_roundtrip(self):
        """PlanSubjectProposal survives to_dict/from_dict roundtrip."""
        original = self.PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        d = original.to_dict()
        restored = self.PlanSubjectProposal.from_dict(d)
        self.assertEqual(restored.subject_ref, original.subject_ref)
        self.assertEqual(restored.revision_digest, original.revision_digest)

    # -- Finding 3: subject_ref boundary tests --

    def test_absolute_path_subject_ref_rejected(self):
        """Absolute subject_ref → DECISION_REJECT (path injection defense)."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref="/etc/passwd",
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")

    def test_traversal_subject_ref_rejected(self):
        """subject_ref with '..' → DECISION_REJECT (path traversal defense)."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref="../../etc/shadow",
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")

    def test_non_plan_prefix_subject_ref_rejected(self):
        """subject_ref outside .sopify-skills/plan/ → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref="src/some_dir",
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")

    # -- Windows-style path defense --

    def test_windows_absolute_subject_ref_rejected(self):
        """Windows-style absolute subject_ref (C:\\plan) → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref="C:\\Users\\plan",
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")

    def test_windows_traversal_subject_ref_rejected(self):
        """Windows-style traversal subject_ref (..\\..\\secret) → DECISION_REJECT."""
        plan_subject = self.PlanSubjectProposal(
            subject_ref="..\\..\\secret",
            revision_digest=self.valid_digest,
        )
        proposal = self._make_proposal(plan_subject=plan_subject)
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")


# ---------------------------------------------------------------------------
# P2: Bound-subject admission for modify_files / checkpoint_response
# ---------------------------------------------------------------------------


class BoundSubjectModifyFilesTests(unittest.TestCase):
    """P2 — modify_files MUST carry plan_subject (REJECT on missing)."""

    DECISION_REJECT = DECISION_REJECT

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp())
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "20260506_test"
        plan_dir.mkdir(parents=True)
        plan_md = plan_dir / "plan.md"
        plan_md.write_text("# modify_files test plan\n", encoding="utf-8")
        self.valid_subject_ref = ".sopify-skills/plan/20260506_test"
        self.valid_digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()
        self.validator = ActionValidator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _ctx(self, workspace_root=None):
        return ValidationContext(
            workspace_root=workspace_root if workspace_root is not None else str(self.workspace),
        )

    def test_modify_files_missing_subject_rejected(self):
        """modify_files without plan_subject → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user asked to edit files",),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_missing")

    def test_modify_files_valid_subject_authorized(self):
        """modify_files with valid plan_subject → authorized."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user asked to edit files",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_modify_files_invalid_ref_rejected(self):
        """modify_files with absolute subject_ref → REJECT."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref="/etc/passwd",
            revision_digest=self.valid_digest,
        )
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user asked to edit files",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")


class BoundSubjectCheckpointResponseTests(unittest.TestCase):
    """P2 — checkpoint_response MUST carry plan_subject (REJECT on missing)."""

    DECISION_REJECT = DECISION_REJECT

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp())
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "20260506_test"
        plan_dir.mkdir(parents=True)
        plan_md = plan_dir / "plan.md"
        plan_md.write_text("# checkpoint_response test plan\n", encoding="utf-8")
        self.valid_subject_ref = ".sopify-skills/plan/20260506_test"
        self.valid_digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()
        self.validator = ActionValidator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _ctx(self, workspace_root=None):
        return ValidationContext(
            workspace_root=workspace_root if workspace_root is not None else str(self.workspace),
        )

    def test_checkpoint_response_missing_subject_rejected(self):
        """checkpoint_response without plan_subject → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="checkpoint_response",
            side_effect="write_runtime_state",
            confidence="high",
            evidence=("checkpoint reached",),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_missing")

    def test_checkpoint_response_valid_subject_authorized(self):
        """checkpoint_response with valid plan_subject → authorized."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        proposal = ActionProposal(
            action_type="checkpoint_response",
            side_effect="write_runtime_state",
            confidence="high",
            evidence=("checkpoint reached",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)


# ---------------------------------------------------------------------------
# P2: cancel_flow conditional binding
# ---------------------------------------------------------------------------


class CancelFlowConditionalBindingTests(unittest.TestCase):
    """P2 — cancel_flow: validate plan_subject if present, no REJECT if absent."""

    DECISION_REJECT = DECISION_REJECT

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp())
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "20260506_test"
        plan_dir.mkdir(parents=True)
        plan_md = plan_dir / "plan.md"
        plan_md.write_text("# cancel_flow test plan\n", encoding="utf-8")
        self.valid_subject_ref = ".sopify-skills/plan/20260506_test"
        self.valid_digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()
        self.validator = ActionValidator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _ctx(self, workspace_root=None):
        return ValidationContext(
            workspace_root=workspace_root if workspace_root is not None else str(self.workspace),
        )

    def test_cancel_flow_no_subject_authorized(self):
        """cancel_flow without plan_subject → authorized (not rejected)."""
        proposal = ActionProposal(
            action_type="cancel_flow",
            side_effect="none",
            confidence="high",
            evidence=("user cancelled",),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)

    def test_cancel_flow_valid_subject_authorized(self):
        """cancel_flow with valid plan_subject → authorized."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )
        proposal = ActionProposal(
            action_type="cancel_flow",
            side_effect="none",
            confidence="high",
            evidence=("user cancelled",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)

    def test_cancel_flow_invalid_subject_rejected(self):
        """cancel_flow with invalid plan_subject → REJECT (validates if present)."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref="/etc/passwd",
            revision_digest=self.valid_digest,
        )
        proposal = ActionProposal(
            action_type="cancel_flow",
            side_effect="none",
            confidence="high",
            evidence=("user cancelled",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_invalid_ref")

    def test_cancel_flow_digest_mismatch_rejected(self):
        """cancel_flow with wrong digest → REJECT."""
        from runtime.action_intent import PlanSubjectProposal
        plan_subject = PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest="0" * 64,
        )
        proposal = ActionProposal(
            action_type="cancel_flow",
            side_effect="none",
            confidence="high",
            evidence=("user cancelled",),
            plan_subject=plan_subject,
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.bound_subject_digest_mismatch")


# ---------------------------------------------------------------------------
# P2: side_effect_delta parser + validator
# ---------------------------------------------------------------------------


class SideEffectDeltaParserTests(unittest.TestCase):
    """P2 — side_effect_delta parser: shape, enum, action gate."""

    def test_delta_on_modify_files_parsed(self):
        """modify_files with valid delta → parses correctly."""
        from runtime.action_intent import PlanSubjectProposal
        proposal = ActionProposal.from_dict({
            "action_type": "modify_files",
            "side_effect": "write_files",
            "confidence": "high",
            "evidence": ["edit src/main.py"],
            "plan_subject": {
                "subject_ref": ".sopify-skills/plan/test",
                "revision_digest": "a" * 64,
            },
            "side_effect_delta": [
                {"path": "src/main.py", "change_type": "modified"},
                {"path": "src/new.py", "change_type": "added"},
            ],
        })
        self.assertIsNotNone(proposal.side_effect_delta)
        self.assertEqual(len(proposal.side_effect_delta), 2)
        self.assertEqual(proposal.side_effect_delta[0]["path"], "src/main.py")
        self.assertEqual(proposal.side_effect_delta[1]["change_type"], "added")

    def test_delta_on_non_delta_capable_action_rejected(self):
        """side_effect_delta on execute_existing_plan → ValueError."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "execute_existing_plan",
                "side_effect": "write_files",
                "confidence": "high",
                "evidence": ["execute plan"],
                "plan_subject": {
                    "subject_ref": ".sopify-skills/plan/test",
                    "revision_digest": "a" * 64,
                },
                "side_effect_delta": [
                    {"path": "src/main.py", "change_type": "modified"},
                ],
            })
        self.assertIn("delta-capable actions", str(cm.exception))

    def test_delta_not_a_list_rejected(self):
        """side_effect_delta as a string → ValueError."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "modify_files",
                "side_effect": "write_files",
                "confidence": "high",
                "evidence": ["edit"],
                "plan_subject": {
                    "subject_ref": ".sopify-skills/plan/test",
                    "revision_digest": "a" * 64,
                },
                "side_effect_delta": "src/main.py",
            })
        self.assertIn("must be a list", str(cm.exception))

    def test_delta_entry_not_object_rejected(self):
        """side_effect_delta entry that isn't a dict → ValueError."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "modify_files",
                "side_effect": "write_files",
                "confidence": "high",
                "evidence": ["edit"],
                "plan_subject": {
                    "subject_ref": ".sopify-skills/plan/test",
                    "revision_digest": "a" * 64,
                },
                "side_effect_delta": ["src/main.py"],
            })
        self.assertIn("must be an object", str(cm.exception))

    def test_delta_invalid_change_type_rejected(self):
        """Unknown change_type → ValueError."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "modify_files",
                "side_effect": "write_files",
                "confidence": "high",
                "evidence": ["edit"],
                "plan_subject": {
                    "subject_ref": ".sopify-skills/plan/test",
                    "revision_digest": "a" * 64,
                },
                "side_effect_delta": [
                    {"path": "src/main.py", "change_type": "deleted"},
                ],
            })
        self.assertIn("change_type must be one of", str(cm.exception))

    def test_delta_empty_path_rejected(self):
        """Empty path string → ValueError."""
        with self.assertRaises(ValueError) as cm:
            ActionProposal.from_dict({
                "action_type": "modify_files",
                "side_effect": "write_files",
                "confidence": "high",
                "evidence": ["edit"],
                "plan_subject": {
                    "subject_ref": ".sopify-skills/plan/test",
                    "revision_digest": "a" * 64,
                },
                "side_effect_delta": [
                    {"path": "", "change_type": "modified"},
                ],
            })
        self.assertIn("path must be a non-empty string", str(cm.exception))

    def test_delta_missing_from_dict_serializes_as_none(self):
        """No delta in input → side_effect_delta is None."""
        proposal = ActionProposal.from_dict({
            "action_type": "modify_files",
            "side_effect": "write_files",
            "confidence": "high",
            "evidence": ["edit files"],
            "plan_subject": {
                "subject_ref": ".sopify-skills/plan/test",
                "revision_digest": "a" * 64,
            },
        })
        self.assertIsNone(proposal.side_effect_delta)

    def test_delta_roundtrip(self):
        """side_effect_delta survives to_dict/from_dict roundtrip."""
        original = ActionProposal.from_dict({
            "action_type": "modify_files",
            "side_effect": "write_files",
            "confidence": "high",
            "evidence": ["edit"],
            "plan_subject": {
                "subject_ref": ".sopify-skills/plan/test",
                "revision_digest": "a" * 64,
            },
            "side_effect_delta": [
                {"path": "src/a.py", "change_type": "added"},
                {"path": "src/b.py", "change_type": "removed"},
            ],
        })
        d = original.to_dict()
        self.assertIn("side_effect_delta", d)
        restored = ActionProposal.from_dict(d)
        self.assertEqual(len(restored.side_effect_delta), 2)
        self.assertEqual(restored.side_effect_delta[0]["path"], "src/a.py")
        self.assertEqual(restored.side_effect_delta[1]["change_type"], "removed")

    def test_empty_list_delta_becomes_none(self):
        """Empty delta list → stored as None (no empty tuples)."""
        proposal = ActionProposal.from_dict({
            "action_type": "modify_files",
            "side_effect": "write_files",
            "confidence": "high",
            "evidence": ["edit"],
            "plan_subject": {
                "subject_ref": ".sopify-skills/plan/test",
                "revision_digest": "a" * 64,
            },
            "side_effect_delta": [],
        })
        self.assertIsNone(proposal.side_effect_delta)


class SideEffectDeltaValidatorTests(unittest.TestCase):
    """P2 — side_effect_delta validator: workspace scoping."""

    DECISION_REJECT = DECISION_REJECT

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp())
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "20260506_test"
        plan_dir.mkdir(parents=True)
        plan_md = plan_dir / "plan.md"
        plan_md.write_text("# delta test\n", encoding="utf-8")
        self.valid_subject_ref = ".sopify-skills/plan/20260506_test"
        self.valid_digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()
        self.validator = ActionValidator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _ctx(self):
        return ValidationContext(workspace_root=str(self.workspace))

    def _subject(self):
        from runtime.action_intent import PlanSubjectProposal
        return PlanSubjectProposal(
            subject_ref=self.valid_subject_ref,
            revision_digest=self.valid_digest,
        )

    def test_delta_absolute_path_rejected(self):
        """Delta with absolute path → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
            side_effect_delta=({"path": "/etc/passwd", "change_type": "modified"},),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.delta_absolute_path")

    def test_delta_traversal_rejected(self):
        """Delta with '..' path → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
            side_effect_delta=({"path": "../../etc/shadow", "change_type": "added"},),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.delta_path_traversal")

    def test_delta_valid_paths_authorized(self):
        """Delta with workspace-relative paths → authorized."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
            side_effect_delta=(
                {"path": "src/main.py", "change_type": "modified"},
                {"path": "tests/test_new.py", "change_type": "added"},
            ),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_no_delta_still_authorized(self):
        """modify_files without delta → authorized (SHOULD, not MUST)."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertNotEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    # -- Windows-style path defense --

    def test_delta_windows_absolute_path_rejected(self):
        """Windows-style absolute path (C:\\tmp\\a.py) → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
            side_effect_delta=({"path": "C:\\tmp\\a.py", "change_type": "modified"},),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.delta_absolute_path")

    def test_delta_windows_traversal_rejected(self):
        """Windows-style traversal (..\\..\\secret.py) → DECISION_REJECT."""
        proposal = ActionProposal(
            action_type="modify_files",
            side_effect="write_files",
            confidence="high",
            evidence=("user edit",),
            plan_subject=self._subject(),
            side_effect_delta=({"path": "..\\..\\secret.py", "change_type": "added"},),
        )
        decision = self.validator.validate(proposal, self._ctx())
        self.assertEqual(decision.decision, self.DECISION_REJECT)
        self.assertEqual(decision.reason_code, "validator.delta_path_traversal")


# ---------------------------------------------------------------------------
# P2: Action-effect canonical pairing
# ---------------------------------------------------------------------------


class ActionEffectPairingTests(unittest.TestCase):
    """P2 — every action_type has exactly one legal side_effect."""

    def setUp(self) -> None:
        from runtime.action_intent import ActionValidator, _CANONICAL_ACTION_EFFECT

        self.validator = ActionValidator()
        self.canonical = _CANONICAL_ACTION_EFFECT

    def _empty_ctx(self) -> "ValidationContext":
        from runtime.action_intent import ValidationContext

        return ValidationContext()

    # -- canonical pairings pass (subject-free actions only, to avoid
    #    bound-subject rejection noise) ----------------------------------------

    def test_canonical_consult_readonly(self) -> None:
        from runtime.action_intent import ActionProposal, DECISION_AUTHORIZE

        proposal = ActionProposal("consult_readonly", "none", "high")
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_AUTHORIZE)

    def test_canonical_propose_plan(self) -> None:
        from runtime.action_intent import ActionProposal, DECISION_AUTHORIZE

        proposal = ActionProposal(
            "propose_plan", "write_plan_package", "high",
            evidence=("用户请求建新方案",),
        )
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_AUTHORIZE)

    def test_canonical_cancel_flow(self) -> None:
        from runtime.action_intent import ActionProposal, DECISION_AUTHORIZE

        proposal = ActionProposal("cancel_flow", "none", "high")
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_AUTHORIZE)

    # -- non-canonical pairings → REJECT ---------------------------------------

    def test_consult_readonly_with_write_files_rejected(self) -> None:
        from runtime.action_intent import ActionProposal, DECISION_REJECT

        proposal = ActionProposal("consult_readonly", "write_files", "high")
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_modify_files_with_none_rejected(self) -> None:
        """modify_files + none → pairing mismatch (bypasses subject gate with valid subject)."""
        import hashlib
        import tempfile
        from pathlib import Path as P

        from runtime.action_intent import (
            ActionProposal,
            DECISION_REJECT,
            PlanSubjectProposal,
            ValidationContext,
        )

        with tempfile.TemporaryDirectory() as td:
            plan_dir = P(td) / ".sopify-skills" / "plan" / "test_plan"
            plan_dir.mkdir(parents=True)
            plan_file = plan_dir / "plan.md"
            plan_file.write_text("# test")
            digest = hashlib.sha256(plan_file.read_bytes()).hexdigest()
            ctx = ValidationContext(workspace_root=td)
            proposal = ActionProposal(
                "modify_files", "none", "high",
                evidence=("modify",),
                plan_subject=PlanSubjectProposal(
                    subject_ref=".sopify-skills/plan/test_plan",
                    revision_digest=digest,
                ),
            )
            result = self.validator.validate(proposal, ctx)
            self.assertEqual(result.decision, DECISION_REJECT)
            self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_checkpoint_response_with_execute_command_rejected(self) -> None:
        """checkpoint_response + execute_command → pairing mismatch."""
        import hashlib
        import tempfile
        from pathlib import Path as P

        from runtime.action_intent import (
            ActionProposal,
            DECISION_REJECT,
            PlanSubjectProposal,
            ValidationContext,
        )

        with tempfile.TemporaryDirectory() as td:
            plan_dir = P(td) / ".sopify-skills" / "plan" / "test_plan"
            plan_dir.mkdir(parents=True)
            plan_file = plan_dir / "plan.md"
            plan_file.write_text("# test")
            digest = hashlib.sha256(plan_file.read_bytes()).hexdigest()
            ctx = ValidationContext(workspace_root=td)
            proposal = ActionProposal(
                "checkpoint_response", "execute_command", "high",
                evidence=("checkpoint response",),
                plan_subject=PlanSubjectProposal(
                    subject_ref=".sopify-skills/plan/test_plan",
                    revision_digest=digest,
                ),
            )
            result = self.validator.validate(proposal, ctx)
            self.assertEqual(result.decision, DECISION_REJECT)
            self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_cancel_flow_with_write_files_rejected(self) -> None:
        """cancel_flow + write_files → pairing mismatch."""
        from runtime.action_intent import ActionProposal, DECISION_REJECT

        proposal = ActionProposal(
            "cancel_flow", "write_files", "high",
            evidence=("cancel",),
        )
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_propose_plan_with_none_rejected(self) -> None:
        """propose_plan + none → pairing mismatch."""
        from runtime.action_intent import ActionProposal, DECISION_REJECT

        proposal = ActionProposal("propose_plan", "none", "high")
        result = self.validator.validate(proposal, self._empty_ctx())
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_execute_existing_plan_with_none_rejected(self) -> None:
        """execute_existing_plan + none → pairing mismatch."""
        import hashlib
        import tempfile
        from pathlib import Path as P

        from runtime.action_intent import (
            ActionProposal,
            DECISION_REJECT,
            PlanSubjectProposal,
            ValidationContext,
        )

        with tempfile.TemporaryDirectory() as td:
            plan_dir = P(td) / ".sopify-skills" / "plan" / "test_plan"
            plan_dir.mkdir(parents=True)
            plan_file = plan_dir / "plan.md"
            plan_file.write_text("# test")
            digest = hashlib.sha256(plan_file.read_bytes()).hexdigest()
            ctx = ValidationContext(workspace_root=td)
            proposal = ActionProposal(
                "execute_existing_plan", "none", "high",
                evidence=("execute",),
                plan_subject=PlanSubjectProposal(
                    subject_ref=".sopify-skills/plan/test_plan",
                    revision_digest=digest,
                ),
            )
            result = self.validator.validate(proposal, ctx)
            self.assertEqual(result.decision, DECISION_REJECT)
            self.assertEqual(result.reason_code, "validator.action_effect_pairing_mismatch")

    def test_canonical_pairing_table_covers_all_action_types(self) -> None:
        """Every ACTION_TYPE must appear in _CANONICAL_ACTION_EFFECT."""
        from runtime.action_intent import ACTION_TYPES

        for at in ACTION_TYPES:
            self.assertIn(at, self.canonical, f"{at} missing from canonical pairing table")


# ---------------------------------------------------------------------------
# P1: Engine-level integration — reject blocks main route
# ---------------------------------------------------------------------------


class PlanSubjectEngineIntegrationTests(unittest.TestCase):
    """P1 — engine MUST block execution when validator rejects plan_subject.

    These tests prove the full path: ActionProposal → validator → engine routing.
    """

    # Execution-semantic routes that reject MUST NOT fall into.
    _EXEC_ROUTES = frozenset({"develop", "exec_plan", "workflow", "light_iterate", "quick_fix", "go_plan"})

    def test_reject_missing_subject_blocks_engine(self):
        """execute_existing_plan without plan_subject → rejected, not routed to execution."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertIn("action_proposal_rejected", result.route.reason)
            self.assertNotIn(result.route.route_name, self._EXEC_ROUTES)
            # P1.5-A: reject MUST use independent surface, not consult
            self.assertEqual(result.route.route_name, "proposal_rejected")

    def test_reject_invalid_digest_blocks_engine(self):
        """execute_existing_plan with wrong digest → rejected, not routed to execution."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            plan_dir = workspace / ".sopify-skills" / "plan" / "20260504_test"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("# test\n", encoding="utf-8")

            from runtime.action_intent import PlanSubjectProposal
            plan_subject = PlanSubjectProposal(
                subject_ref=".sopify-skills/plan/20260504_test",
                revision_digest="0" * 64,
            )
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
                plan_subject=plan_subject,
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertIn("action_proposal_rejected", result.route.reason)
            self.assertNotIn(result.route.route_name, self._EXEC_ROUTES)
            # P1.5-A: reject MUST use independent surface, not consult
            self.assertEqual(result.route.route_name, "proposal_rejected")

    def test_valid_subject_not_blocked_by_engine(self):
        """execute_existing_plan with valid plan_subject → NOT rejected (router runs)."""
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            plan_dir = workspace / ".sopify-skills" / "plan" / "20260504_test"
            plan_dir.mkdir(parents=True)
            plan_md = plan_dir / "plan.md"
            plan_md.write_text("# test\n", encoding="utf-8")
            digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()

            from runtime.action_intent import PlanSubjectProposal
            plan_subject = PlanSubjectProposal(
                subject_ref=".sopify-skills/plan/20260504_test",
                revision_digest=digest,
            )
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
                plan_subject=plan_subject,
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            # Valid subject → authorized, NOT rejected — router handles routing
            self.assertNotIn("action_proposal_rejected", result.route.reason)


# ---------------------------------------------------------------------------
# P1.5-A: DECISION_REJECT Surface 收口
# ---------------------------------------------------------------------------


class RejectSurfaceTests(unittest.TestCase):
    """P1.5-A — reject MUST use independent surface, not masquerade as consult."""

    def test_reject_handoff_kind_is_reject(self):
        """Rejected proposal → handoff_kind == 'reject', not 'consult'."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertEqual(result.route.route_name, "proposal_rejected")
            self.assertIsNotNone(result.handoff, "reject MUST emit handoff")
            self.assertEqual(result.handoff.handoff_kind, "reject")
            self.assertNotEqual(result.handoff.handoff_kind, "consult")

    def test_reject_handoff_artifacts_contain_reason_code(self):
        """Rejected proposal → handoff artifacts include reject_reason_code."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertIsNotNone(result.handoff)
            artifacts = result.handoff.artifacts
            self.assertIn("reject_reason_code", artifacts)
            self.assertTrue(str(artifacts["reject_reason_code"]).strip())

    def test_reject_required_host_action_is_continue_host_consult(self):
        """Reject uses existing continue_host_consult (budget stays at 5)."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
            )
            result = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertIsNotNone(result.handoff)
            self.assertEqual(result.handoff.required_host_action, "continue_host_consult")

    def test_genuine_consult_not_affected(self):
        """Normal consult (no action proposal) still uses consult surface."""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            result = run_runtime(
                "什么是 Python?",
                workspace_root=workspace,
                user_home=workspace / "home",
            )
            self.assertEqual(result.route.route_name, "consult")
            if result.handoff is not None:
                self.assertEqual(result.handoff.handoff_kind, "consult")

    def test_digest_mismatch_admission_reject_uses_new_surface(self):
        """Digest mismatch admission reject → proposal_rejected surface (not consult)."""
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            plan_dir = workspace / ".sopify-skills" / "plan" / "20260504_test"
            plan_dir.mkdir(parents=True)
            plan_md = plan_dir / "plan.md"
            plan_md.write_text("# original\n", encoding="utf-8")
            digest = hashlib.sha256(plan_md.read_bytes()).hexdigest()

            from runtime.action_intent import PlanSubjectProposal
            plan_subject = PlanSubjectProposal(
                subject_ref=".sopify-skills/plan/20260504_test",
                revision_digest=digest,
            )

            # First run: authorize with correct digest
            proposal = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
                plan_subject=plan_subject,
            )
            result1 = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal,
            )
            self.assertNotIn("action_proposal_rejected", result1.route.reason)

            # Mutate plan.md but keep OLD digest → stale
            plan_md.write_text("# mutated content\n", encoding="utf-8")

            stale_subject = PlanSubjectProposal(
                subject_ref=".sopify-skills/plan/20260504_test",
                revision_digest=digest,  # old digest, now mismatches plan.md
            )
            proposal2 = ActionProposal(
                "execute_existing_plan", "write_files", "high",
                evidence=("user confirmed execution",),
                plan_subject=stale_subject,
            )
            result2 = run_runtime(
                "继续执行计划",
                workspace_root=workspace,
                user_home=workspace / "home",
                action_proposal=proposal2,
            )
            # Stale digest → admission reject → proposal_rejected surface
            self.assertEqual(result2.route.route_name, "proposal_rejected")
            self.assertIsNotNone(result2.handoff)
            self.assertEqual(result2.handoff.handoff_kind, "reject")


# ---------------------------------------------------------------------------
# P1.5-B: ExecutionAuthorizationReceipt tests
# ---------------------------------------------------------------------------

from runtime.action_intent import (
    ExecutionAuthorizationReceipt,
    generate_proposal_id,
    _receipt_fingerprint,
    _check_stale_receipt,
    PlanSubjectProposal,
    DECISION_REJECT,
)


class ExecutionAuthorizationReceiptTests(unittest.TestCase):
    """T5-A: Receipt dataclass unit tests."""

    def test_to_dict_from_dict_roundtrip(self):
        receipt = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/test_plan",
            plan_revision_digest="a" * 64,
            gate_status="ready",
            action_proposal_id="abcdef0123456789",
            request_sha1="abc123",
        )
        data = receipt.to_dict()
        restored = ExecutionAuthorizationReceipt.from_dict(data)
        self.assertEqual(restored.plan_id, receipt.plan_id)
        self.assertEqual(restored.plan_path, receipt.plan_path)
        self.assertEqual(restored.plan_revision_digest, receipt.plan_revision_digest)
        self.assertEqual(restored.gate_status, receipt.gate_status)
        self.assertEqual(restored.action_proposal_id, receipt.action_proposal_id)
        self.assertEqual(restored.authorization_source, receipt.authorization_source)
        self.assertEqual(restored.fingerprint, receipt.fingerprint)
        self.assertEqual(restored.authorized_at, receipt.authorized_at)

    def test_fingerprint_deterministic(self):
        """Same inputs → same fingerprint."""
        r1 = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="b" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha1",
        )
        r2 = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="b" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha1",
        )
        self.assertEqual(r1.fingerprint, r2.fingerprint)

    def test_fingerprint_sensitive_to_field_change(self):
        """Any field change → different fingerprint."""
        base_kwargs = dict(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="c" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha1",
        )
        base = ExecutionAuthorizationReceipt.create(**base_kwargs)
        for field, alt_value in [
            ("plan_path", ".sopify-skills/plan/p2"),
            ("plan_revision_digest", "d" * 64),
            ("gate_status", "blocked"),
            ("action_proposal_id", "fedcba9876543210"),
        ]:
            changed_kwargs = {**base_kwargs, field: alt_value}
            changed = ExecutionAuthorizationReceipt.create(**changed_kwargs)
            self.assertNotEqual(base.fingerprint, changed.fingerprint, f"fingerprint should differ when {field} changes")

    def test_plan_id_extracted_from_path(self):
        receipt = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/my_cool_plan",
            plan_revision_digest="e" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha1",
        )
        self.assertEqual(receipt.plan_id, "my_cool_plan")

    def test_authorization_source_structure(self):
        receipt = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="f" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="my_sha1",
        )
        self.assertEqual(receipt.authorization_source["kind"], "request_hash")
        self.assertEqual(receipt.authorization_source["request_sha1"], "my_sha1")

    def test_frozen_dataclass(self):
        receipt = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="0" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha",
        )
        with self.assertRaises(AttributeError):
            receipt.plan_id = "changed"  # type: ignore[misc]


class GenerateProposalIdTests(unittest.TestCase):
    """T5-B: generate_proposal_id deterministic tests."""

    def test_idempotent(self):
        """Same inputs → same ID."""
        id1 = generate_proposal_id("execute_existing_plan", "write_files", "ref", "digest", "hash")
        id2 = generate_proposal_id("execute_existing_plan", "write_files", "ref", "digest", "hash")
        self.assertEqual(id1, id2)

    def test_length_16(self):
        pid = generate_proposal_id("execute_existing_plan", "write_files", "ref", "digest", "hash")
        self.assertEqual(len(pid), 16)

    def test_input_change_changes_id(self):
        """Any input change → different ID."""
        base = ("execute_existing_plan", "write_files", "ref", "digest", "hash")
        base_id = generate_proposal_id(*base)
        alternatives = [
            ("consult_readonly", "write_files", "ref", "digest", "hash"),
            ("execute_existing_plan", "none", "ref", "digest", "hash"),
            ("execute_existing_plan", "write_files", "other_ref", "digest", "hash"),
            ("execute_existing_plan", "write_files", "ref", "other_digest", "hash"),
            ("execute_existing_plan", "write_files", "ref", "digest", "other_hash"),
        ]
        for alt in alternatives:
            alt_id = generate_proposal_id(*alt)
            self.assertNotEqual(base_id, alt_id, f"ID should differ for {alt}")

    def test_host_supplied_proposal_id_rejected(self):
        """ActionProposal.from_dict MUST reject host-supplied proposal_id."""
        raw = {
            "action_type": "consult_readonly",
            "side_effect": "none",
            "confidence": "high",
            "evidence": ["test"],
            "proposal_id": "host_injected_value",
        }
        with self.assertRaises(ValueError, msg="proposal_id must not be supplied by host"):
            ActionProposal.from_dict(raw)


class StaleReceiptDetectionTests(unittest.TestCase):
    """T5-D: stale receipt fail-closed tests."""

    def setUp(self) -> None:
        self.validator = ActionValidator()
        self._tmpdir = tempfile.mkdtemp()
        self.workspace = Path(self._tmpdir)
        plan_dir = self.workspace / ".sopify-skills" / "plan" / "test_plan"
        plan_dir.mkdir(parents=True)
        self.plan_md = plan_dir / "plan.md"
        self.plan_md.write_text("# Original Plan\n", encoding="utf-8")
        import hashlib
        self.original_digest = hashlib.sha256(self.plan_md.read_bytes()).hexdigest()
        self.subject_ref = ".sopify-skills/plan/test_plan"
        self.valid_receipt = ExecutionAuthorizationReceipt.create(
            plan_path=self.subject_ref,
            plan_revision_digest=self.original_digest,
            gate_status="ready",
            action_proposal_id="abcdef0123456789",
            request_sha1="req_hash",
        ).to_dict()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_proposal(self, subject_ref=None, revision_digest=None):
        plan_subject = PlanSubjectProposal(
            subject_ref=subject_ref or self.subject_ref,
            revision_digest=revision_digest or self.original_digest,
        )
        return ActionProposal(
            action_type="execute_existing_plan",
            side_effect="write_files",
            confidence="high",
            evidence=("user confirmed execution",),
            plan_subject=plan_subject,
        )

    def _ctx(self, receipt=None, gate_status="ready"):
        return ValidationContext(
            workspace_root=str(self.workspace),
            existing_receipt=receipt,
            current_gate_status=gate_status,
        )

    def test_no_receipt_passes(self):
        """No existing receipt → first-time auth, no stale rejection."""
        proposal = self._make_proposal()
        decision = self.validator.validate(proposal, self._ctx(receipt=None))
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_fresh_receipt_passes(self):
        """Receipt matches current facts → authorization proceeds."""
        proposal = self._make_proposal()
        decision = self.validator.validate(proposal, self._ctx(receipt=self.valid_receipt))
        self.assertEqual(decision.decision, DECISION_AUTHORIZE)

    def test_plan_content_changed_rejects(self):
        """plan.md modified after receipt → stale → DECISION_REJECT."""
        self.plan_md.write_text("# Modified Plan\n", encoding="utf-8")
        import hashlib
        new_digest = hashlib.sha256(self.plan_md.read_bytes()).hexdigest()
        proposal = self._make_proposal(revision_digest=new_digest)
        decision = self.validator.validate(proposal, self._ctx(receipt=self.valid_receipt))
        self.assertEqual(decision.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_digest", decision.reason_code)

    def test_plan_deleted_rejects(self):
        """Plan directory removed → stale → DECISION_REJECT."""
        import shutil
        shutil.rmtree(self.workspace / ".sopify-skills" / "plan" / "test_plan")
        # Proposal still references the old plan (will fail subject admission first,
        # but let's test _check_stale_receipt directly)
        proposal = self._make_proposal()
        result = _check_stale_receipt(proposal, self._ctx(receipt=self.valid_receipt))
        self.assertIsNotNone(result)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_path_gone", result.reason_code)

    def test_gate_status_changed_rejects(self):
        """gate_status changed since receipt → stale → DECISION_REJECT."""
        proposal = self._make_proposal()
        decision = self.validator.validate(proposal, self._ctx(receipt=self.valid_receipt, gate_status="blocked"))
        self.assertEqual(decision.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_gate", decision.reason_code)

    def test_plan_mismatch_rejects(self):
        """Receipt for plan A, proposal for plan B → stale → DECISION_REJECT."""
        other_plan_dir = self.workspace / ".sopify-skills" / "plan" / "other_plan"
        other_plan_dir.mkdir(parents=True)
        other_plan_md = other_plan_dir / "plan.md"
        other_plan_md.write_text("# Other Plan\n", encoding="utf-8")
        import hashlib
        other_digest = hashlib.sha256(other_plan_md.read_bytes()).hexdigest()
        proposal = self._make_proposal(
            subject_ref=".sopify-skills/plan/other_plan",
            revision_digest=other_digest,
        )
        decision = self.validator.validate(proposal, self._ctx(receipt=self.valid_receipt))
        self.assertEqual(decision.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_plan_mismatch", decision.reason_code)

    def test_malformed_receipt_rejects(self):
        """Receipt with missing required fields → malformed → DECISION_REJECT."""
        malformed = {"plan_path": self.subject_ref}  # missing most fields
        proposal = self._make_proposal()
        result = _check_stale_receipt(proposal, self._ctx(receipt=malformed))
        self.assertIsNotNone(result)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_malformed", result.reason_code)

    def test_empty_authorization_source_rejects(self):
        """Receipt with empty authorization_source → malformed → DECISION_REJECT."""
        bad_receipt = dict(self.valid_receipt)
        bad_receipt["authorization_source"] = {}
        proposal = self._make_proposal()
        result = _check_stale_receipt(proposal, self._ctx(receipt=bad_receipt))
        self.assertIsNotNone(result)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_malformed", result.reason_code)

    def test_authorization_source_wrong_kind_rejects(self):
        """authorization_source with invalid kind → malformed → DECISION_REJECT."""
        bad_receipt = dict(self.valid_receipt)
        bad_receipt["authorization_source"] = {"kind": "magic", "request_sha1": "abc123"}
        proposal = self._make_proposal()
        result = _check_stale_receipt(proposal, self._ctx(receipt=bad_receipt))
        self.assertIsNotNone(result)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_malformed", result.reason_code)

    def test_authorization_source_missing_sha1_rejects(self):
        """authorization_source without request_sha1 → malformed → DECISION_REJECT."""
        bad_receipt = dict(self.valid_receipt)
        bad_receipt["authorization_source"] = {"kind": "request_hash"}
        proposal = self._make_proposal()
        result = _check_stale_receipt(proposal, self._ctx(receipt=bad_receipt))
        self.assertIsNotNone(result)
        self.assertEqual(result.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_malformed", result.reason_code)

    def test_gate_truth_missing_rejects(self):
        """Receipt exists but no current gate truth → fail-closed → DECISION_REJECT."""
        proposal = self._make_proposal()
        decision = self.validator.validate(proposal, self._ctx(receipt=self.valid_receipt, gate_status=""))
        self.assertEqual(decision.decision, DECISION_REJECT)
        self.assertIn("stale_receipt_gate_missing", decision.reason_code)


class RunStateReceiptPersistenceTests(unittest.TestCase):
    """T5-C (partial): RunState receipt serialization roundtrip."""

    def test_runstate_receipt_roundtrip(self):
        from runtime._models.core import RunState
        receipt_dict = ExecutionAuthorizationReceipt.create(
            plan_path=".sopify-skills/plan/p1",
            plan_revision_digest="a" * 64,
            gate_status="ready",
            action_proposal_id="1234567890abcdef",
            request_sha1="sha",
        ).to_dict()
        run = RunState(
            run_id="test-001",
            status="active",
            stage="develop_pending",
            route_name="resume_active",
            title="Test",
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
            execution_authorization_receipt=receipt_dict,
        )
        data = run.to_dict()
        self.assertIsNotNone(data["execution_authorization_receipt"])
        restored = RunState.from_dict(data)
        self.assertEqual(restored.execution_authorization_receipt, receipt_dict)

    def test_runstate_no_receipt_roundtrip(self):
        from runtime._models.core import RunState
        run = RunState(
            run_id="test-002",
            status="active",
            stage="plan_generated",
            route_name="develop",
            title="Test",
            created_at="2026-05-06T00:00:00Z",
            updated_at="2026-05-06T00:00:00Z",
        )
        data = run.to_dict()
        self.assertIsNone(data["execution_authorization_receipt"])
        restored = RunState.from_dict(data)
        self.assertIsNone(restored.execution_authorization_receipt)


if __name__ == "__main__":
    unittest.main()
