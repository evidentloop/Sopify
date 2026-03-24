from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.config import load_runtime_config
from runtime.engine import run_runtime
from runtime.gate import enter_runtime_gate
from scripts.model_compare_runtime import make_default_candidate


class BundleSmokeTests(unittest.TestCase):
    def test_import_runtime_entry(self) -> None:
        self.assertTrue(callable(run_runtime))

    def test_route_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = run_runtime(
                "重构数据库层",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(result.route.route_name, "workflow")
            self.assertIsNotNone(result.plan_artifact)
            self.assertIsNotNone(result.handoff)

    def test_gate_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            payload = enter_runtime_gate(
                "重构数据库层",
                workspace_root=workspace,
                user_home=workspace / "home",
            )

            self.assertEqual(payload["status"], "ready")
            self.assertTrue(payload["gate_passed"])
            self.assertEqual(payload["allowed_response_mode"], "normal_runtime_followup")

    def test_config_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sopify.config.yaml").write_text("plan:\n  directory: .runtime\n", encoding="utf-8")

            config = load_runtime_config(workspace)

            self.assertEqual(config.plan_directory, ".runtime")
            self.assertEqual(config.runtime_root, workspace.resolve() / ".runtime")

    def test_helper_available(self) -> None:
        candidate = make_default_candidate(model="gpt-5")

        self.assertEqual(candidate.id, "session_default")
        self.assertEqual(candidate.model, "gpt-5")
