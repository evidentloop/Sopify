# Test classification: contract
#
# 4.11 — Direct tests for execute_kernel_turn() through the orchestration module.
# Proves the kernel orchestration seam works independently of the
# run_runtime() wrapper in engine.py.
from __future__ import annotations

from tests.runtime_test_support import *

from runtime._orchestration import execute_kernel_turn


class TestKernelTurnDirect(unittest.TestCase):
    """Minimum verification set for the kernel seam (5 cases)."""

    # ------------------------------------------------------------------
    # 1. Planning main chain: plan_only → handoff
    # ------------------------------------------------------------------
    def test_kernel_plan_only_produces_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()

            result = execute_kernel_turn(
                "~go plan 补 kernel 直测骨架",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(result.route.route_name, "plan_only")
            self.assertIsNotNone(result.plan_artifact)
            self.assertIsNotNone(result.handoff)
            self.assertEqual(result.handoff.handoff_kind, "plan")

    # ------------------------------------------------------------------
    # 2. Active develop state → planning path reuses existing plan
    # ------------------------------------------------------------------
    def test_kernel_active_develop_planning_reuses_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            _enter_active_develop_context(workspace)

            config = load_runtime_config(workspace)
            store = StateStore(config)
            existing_plan = store.get_current_plan()

            # Natural text (not bare ~go) so the router routes to workflow
            # through the standard planning path and emits a handoff.
            # (bare ~go with active plan maps to exec_plan which intentionally
            # suppresses handoff — see handoff.py _should_emit_handoff.)
            result = execute_kernel_turn(
                "帮我继续实现",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(
                result.recovered_context.current_plan.plan_id,
                existing_plan.plan_id,
            )
            self.assertIsNotNone(result.handoff)
            self.assertEqual(
                result.handoff.plan_id,
                existing_plan.plan_id,
            )
            self.assertEqual(
                result.handoff.required_host_action,
                "continue_host_develop",
            )

    # ------------------------------------------------------------------
    # 3. Decision resume dispatches through kernel seam
    # ------------------------------------------------------------------
    def test_kernel_decision_resume_dispatches_through_seam(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()

            # Step 1: trigger decision_pending via text classification.
            pending = execute_kernel_turn(
                "~go plan payload 放 host root 还是 workspace/.sopify-skills",
                workspace_root=workspace,
                user_home=workspace / "home",
            )
            self.assertEqual(pending.route.route_name, "decision_pending")
            self.assertIsNotNone(pending.recovered_context.current_decision)

            # Step 2: confirm decision through kernel seam.
            resumed = execute_kernel_turn(
                "1",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(resumed.route.route_name, "plan_only")
            self.assertIsNotNone(resumed.plan_artifact)
            decision_file = (
                workspace / ".sopify-skills" / "state" / "current_decision.json"
            )
            self.assertFalse(decision_file.exists())

    # ------------------------------------------------------------------
    # 4. State conflict — inspect is strictly read-only
    # ------------------------------------------------------------------
    def test_kernel_state_conflict_inspect_is_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            config = load_runtime_config(workspace)
            store = StateStore(config)
            store.ensure()

            plan_artifact = create_plan_scaffold(
                "补 runtime 状态机 hotfix", config=config, level="standard",
            )
            store.set_current_plan(plan_artifact)
            store.set_current_run(
                RunState(
                    run_id="run-1",
                    status="active",
                    stage="plan_generated",
                    route_name="plan_only",
                    title=plan_artifact.title,
                    created_at=iso_now(),
                    updated_at=iso_now(),
                    plan_id=plan_artifact.plan_id,
                    plan_path=plan_artifact.path,
                    resolution_id="run-resolution",
                )
            )
            store.set_current_handoff(
                RuntimeHandoff(
                    schema_version="1",
                    route_name="plan_only",
                    run_id="run-1",
                    plan_id=plan_artifact.plan_id,
                    plan_path=plan_artifact.path,
                    handoff_kind="plan_only",
                    required_host_action="continue_host_develop",
                    resolution_id="handoff-resolution",
                )
            )

            result = execute_kernel_turn(
                "看看状态",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(result.route.route_name, "state_conflict")
            self.assertEqual(
                result.route.active_run_action, "inspect_conflict",
            )
            # Store unchanged — strictly read-only.
            inspected_store = StateStore(load_runtime_config(workspace))
            self.assertEqual(
                inspected_store.get_current_handoff().resolution_id,
                "handoff-resolution",
            )
            self.assertEqual(
                inspected_store.get_current_run().resolution_id,
                "run-resolution",
            )
            # last_route must NOT be written for inspect.
            self.assertIsNone(inspected_store.get_last_route())

    # ------------------------------------------------------------------
    # 5. State conflict — abort persists stable host-facing truth
    # ------------------------------------------------------------------
    def test_kernel_state_conflict_abort_persists_stable_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            config = load_runtime_config(workspace)
            store = StateStore(config)
            store.ensure()

            plan_artifact = create_plan_scaffold(
                "补 runtime 状态机 hotfix", config=config, level="standard",
            )
            store.set_current_plan(plan_artifact)
            store.set_current_run(
                RunState(
                    run_id="run-1",
                    status="active",
                    stage="plan_generated",
                    route_name="plan_only",
                    title=plan_artifact.title,
                    created_at=iso_now(),
                    updated_at=iso_now(),
                    plan_id=plan_artifact.plan_id,
                    plan_path=plan_artifact.path,
                    resolution_id="run-resolution",
                )
            )
            store.set_current_handoff(
                RuntimeHandoff(
                    schema_version="1",
                    route_name="plan_only",
                    run_id="run-1",
                    plan_id=plan_artifact.plan_id,
                    plan_path=plan_artifact.path,
                    handoff_kind="plan_only",
                    required_host_action="continue_host_develop",
                    resolution_id="handoff-resolution",
                )
            )

            # Step 1: inspect (confirm conflict exists).
            inspected = execute_kernel_turn(
                "看看状态",
                workspace_root=workspace,
                user_home=workspace / "home",
            )
            self.assertEqual(inspected.route.route_name, "state_conflict")

            # Step 2: abort — persists stable truth.
            cleared = execute_kernel_turn(
                "强制取消",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(cleared.route.route_name, "state_conflict")
            self.assertEqual(
                cleared.route.active_run_action, "abort_conflict",
            )
            self.assertFalse(cleared.recovered_context.state_conflict)

            # Plan and run survive (tombstone semantics, not full clear).
            after_store = StateStore(load_runtime_config(workspace))
            self.assertIsNotNone(after_store.get_current_plan())
            surviving_run = after_store.get_current_run()
            self.assertIsNotNone(surviving_run)
            self.assertEqual(surviving_run.stage, "plan_generated")


if __name__ == "__main__":
    unittest.main()
