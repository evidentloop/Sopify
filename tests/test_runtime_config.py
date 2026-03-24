from __future__ import annotations

from tests.runtime_test_support import *


class RuntimeConfigTests(unittest.TestCase):
    def test_zero_config_uses_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_runtime_config(temp_dir, global_config_path=Path(temp_dir) / "missing.yaml")
            self.assertEqual(config.language, "zh-CN")
            self.assertEqual(config.workflow_mode, "adaptive")
            self.assertEqual(config.plan_directory, ".sopify-skills")
            self.assertFalse(config.multi_model_enabled)
            self.assertTrue(config.brand.endswith("-ai"))

    def test_project_config_overrides_global(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            global_path = workspace / "global.yaml"
            project_path = workspace / "sopify.config.yaml"
            global_path.write_text(
                "language: en-US\nworkflow:\n  require_score: 5\nplan:\n  level: light\n",
                encoding="utf-8",
            )
            project_path.write_text(
                "workflow:\n  require_score: 9\nplan:\n  directory: .runtime\n",
                encoding="utf-8",
            )
            config = load_runtime_config(workspace, global_config_path=global_path)
            self.assertEqual(config.language, "en-US")
            self.assertEqual(config.require_score, 9)
            self.assertEqual(config.plan_level, "light")
            self.assertEqual(config.plan_directory, ".runtime")

    def test_invalid_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sopify.config.yaml").write_text("workflow:\n  mode: unsupported\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_runtime_config(workspace)

    def test_brand_auto_prefers_package_name_over_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-workspace"}', encoding="utf-8")
            config = load_runtime_config(workspace, global_config_path=workspace / "missing.yaml")
            self.assertEqual(config.brand, "sample-workspace-ai")


class YamlLoaderTests(unittest.TestCase):
    def test_quoted_list_item_with_colon_is_parsed_as_string(self) -> None:
        payload = load_yaml('triggers:\n  - "~compare"\n  - "compare:"\n')
        self.assertEqual(payload["triggers"], ["~compare", "compare:"])
