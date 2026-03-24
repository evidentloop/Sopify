from __future__ import annotations

from tests.runtime_test_support import *


class PreferencesPreloadTests(unittest.TestCase):
    def test_preload_preferences_loads_default_workspace_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            config = load_runtime_config(workspace)
            preferences_path = workspace / ".sopify-skills" / "user" / "preferences.md"
            preferences_path.parent.mkdir(parents=True, exist_ok=True)
            preferences_path.write_text("# 用户长期偏好\n\n- 保持严格。\n", encoding="utf-8")

            result = preload_preferences(config)

            self.assertEqual(result.status, "loaded")
            self.assertTrue(result.injected)
            self.assertEqual(result.plan_directory, ".sopify-skills")
            self.assertEqual(Path(result.preferences_path), preferences_path.resolve())
            self.assertEqual(Path(result.feedback_path), (workspace / ".sopify-skills" / "user" / "feedback.jsonl").resolve())
            self.assertFalse(result.feedback_present)
            self.assertIn("[Long-Term User Preferences]", result.injection_text)
            self.assertIn("保持严格。", result.injection_text)

    def test_preload_preferences_respects_custom_plan_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sopify.config.yaml").write_text("plan:\n  directory: .runtime\n", encoding="utf-8")
            preferences_path = workspace / ".runtime" / "user" / "preferences.md"
            preferences_path.parent.mkdir(parents=True, exist_ok=True)
            preferences_path.write_text("# Long-Term User Preferences\n\n- Be concise.\n", encoding="utf-8")

            result = preload_preferences_for_workspace(workspace)

            self.assertEqual(result.status, "loaded")
            self.assertEqual(result.plan_directory, ".runtime")
            self.assertEqual(Path(result.preferences_path), preferences_path.resolve())
            self.assertEqual(Path(result.feedback_path), (workspace / ".runtime" / "user" / "feedback.jsonl").resolve())
            self.assertFalse(result.feedback_present)
            self.assertIn("Be concise.", result.injection_text)

    def test_preload_preferences_reports_missing_without_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = preload_preferences_for_workspace(workspace)

            self.assertEqual(result.status, "missing")
            self.assertFalse(result.injected)
            self.assertEqual(result.injection_text, "")
            self.assertIsNone(result.error_code)
            self.assertFalse(result.feedback_present)

    def test_preload_preferences_reports_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            preferences_path = workspace / ".sopify-skills" / "user" / "preferences.md"
            preferences_path.parent.mkdir(parents=True, exist_ok=True)
            preferences_path.write_bytes(b"\xff\xfe\x00\x00")

            result = preload_preferences_for_workspace(workspace)

            self.assertEqual(result.status, "invalid")
            self.assertEqual(result.error_code, "invalid_utf8")
            self.assertFalse(result.injected)
            self.assertEqual(result.injection_text, "")
