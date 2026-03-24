from __future__ import annotations

from tests.runtime_test_support import *


class KnowledgeBaseBootstrapTests(unittest.TestCase):
    def test_progressive_bootstrap_creates_minimal_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-app"}', encoding="utf-8")
            config = load_runtime_config(workspace)

            artifact = bootstrap_kb(config)

            self.assertEqual(
                set(artifact.files),
                {
                    ".sopify-skills/project.md",
                    ".sopify-skills/user/preferences.md",
                    ".sopify-skills/blueprint/README.md",
                },
            )
            self.assertIn("当前暂无已确认的长期偏好", (workspace / ".sopify-skills" / "user" / "preferences.md").read_text(encoding="utf-8"))
            readme = (workspace / ".sopify-skills" / "blueprint" / "README.md").read_text(encoding="utf-8")
            self.assertIn("状态: L0 bootstrap", readme)
            self.assertNotIn("wiki/overview.md", readme)
            self.assertNotIn("./background.md", readme)
            self.assertNotIn("../history/index.md", readme)
            self.assertNotIn("工作目录:", readme)
            self.assertNotIn("项目概览", readme)
            self.assertNotIn("架构地图", readme)
            self.assertNotIn("关键契约", readme)
            self.assertFalse((workspace / ".sopify-skills" / "blueprint" / "background.md").exists())
            self.assertFalse((workspace / ".sopify-skills" / "history").exists())
            self.assertFalse((workspace / ".sopify-skills" / "wiki").exists())

    def test_progressive_bootstrap_materializes_feedback_log_for_explicit_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-app"}', encoding="utf-8")
            preferences_path = workspace / ".sopify-skills" / "user" / "preferences.md"
            preferences_path.parent.mkdir(parents=True, exist_ok=True)
            preferences_path.write_text("# 用户长期偏好\n\n- 保持严格。\n", encoding="utf-8")
            config = load_runtime_config(workspace)

            artifact = bootstrap_kb(config)

            self.assertIn(".sopify-skills/user/feedback.jsonl", artifact.files)
            self.assertTrue((workspace / ".sopify-skills" / "user" / "feedback.jsonl").exists())

    def test_full_bootstrap_creates_extended_kb_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sopify.config.yaml").write_text("advanced:\n  kb_init: full\n", encoding="utf-8")
            config = load_runtime_config(workspace)

            artifact = bootstrap_kb(config)

            self.assertEqual(
                set(artifact.files),
                {
                    ".sopify-skills/project.md",
                    ".sopify-skills/user/preferences.md",
                    ".sopify-skills/user/feedback.jsonl",
                    ".sopify-skills/blueprint/README.md",
                    ".sopify-skills/blueprint/background.md",
                    ".sopify-skills/blueprint/design.md",
                    ".sopify-skills/blueprint/tasks.md",
                },
            )
            self.assertIn(".sopify-skills/user/feedback.jsonl", artifact.files)
            readme = (workspace / ".sopify-skills" / "blueprint" / "README.md").read_text(encoding="utf-8")
            self.assertIn("状态: L1 blueprint-ready", readme)
            self.assertIn("./background.md", readme)
            self.assertNotIn("工作目录:", readme)
            self.assertNotIn("项目概览", readme)
            self.assertNotIn("架构地图", readme)
            self.assertNotIn("关键契约", readme)
            tasks_text = (workspace / ".sopify-skills" / "blueprint" / "tasks.md").read_text(encoding="utf-8")
            self.assertNotIn("[x]", tasks_text)
            self.assertFalse((workspace / ".sopify-skills" / "history").exists())
            self.assertFalse((workspace / ".sopify-skills" / "wiki").exists())

    def test_bootstrap_is_idempotent_and_preserves_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            config = load_runtime_config(workspace)

            first = bootstrap_kb(config)
            self.assertTrue(first.files)

            project_path = workspace / ".sopify-skills" / "project.md"
            project_path.write_text("# custom\n", encoding="utf-8")

            second = bootstrap_kb(config)

            self.assertEqual(second.files, ())
            self.assertEqual(project_path.read_text(encoding="utf-8"), "# custom\n")

    def test_blueprint_index_uses_history_index_for_latest_archive_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-app"}', encoding="utf-8")
            config = load_runtime_config(workspace)

            bootstrap_kb(config)
            blueprint_root = workspace / ".sopify-skills" / "blueprint"
            for filename in ("background.md", "design.md", "tasks.md"):
                (blueprint_root / filename).write_text(f"# {filename}\n", encoding="utf-8")

            history_root = workspace / ".sopify-skills" / "history"
            (history_root / "2026-03" / "20260320_kb_layout_v2").mkdir(parents=True)
            (history_root / "2026-03" / "20260320_prompt_runtime_gate").mkdir(parents=True)
            (history_root / "index.md").write_text(
                (
                    "# 变更历史索引\n\n"
                    "记录已归档的方案，便于后续查询。\n\n"
                    "## 索引\n\n"
                    "- `2026-03-21` [`20260320_kb_layout_v2`](2026-03/20260320_kb_layout_v2/) - standard - Sopify KB Layout V2\n"
                    "- `2026-03-20` [`20260320_prompt_runtime_gate`](2026-03/20260320_prompt_runtime_gate/) - standard - Prompt-Level Runtime Gate\n"
                ),
                encoding="utf-8",
            )

            ensure_blueprint_index(config)

            readme = (blueprint_root / "README.md").read_text(encoding="utf-8")
            self.assertIn("最近归档为 `../history/2026-03/20260320_kb_layout_v2`", readme)
            self.assertIn("最近归档：`../history/2026-03/20260320_kb_layout_v2`", readme)

    def test_blueprint_index_lists_additional_long_lived_blueprint_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-app"}', encoding="utf-8")
            config = load_runtime_config(workspace)

            bootstrap_kb(config)
            blueprint_root = workspace / ".sopify-skills" / "blueprint"
            for filename in ("background.md", "design.md", "tasks.md"):
                (blueprint_root / filename).write_text(f"# {filename}\n", encoding="utf-8")
            (blueprint_root / "skill-standards-refactor.md").write_text(
                "# Skill 标准对齐蓝图\n\n长期专题文档。\n",
                encoding="utf-8",
            )

            ensure_blueprint_index(config)

            readme = (blueprint_root / "README.md").read_text(encoding="utf-8")
            self.assertIn("[Skill 标准对齐蓝图](./skill-standards-refactor.md)", readme)

    def test_real_project_bootstrap_creates_blueprint_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "package.json").write_text('{"name":"sample-app"}', encoding="utf-8")
            config = load_runtime_config(workspace)

            artifact = bootstrap_kb(config)

            self.assertIn(".sopify-skills/blueprint/README.md", artifact.files)
            readme_path = workspace / ".sopify-skills" / "blueprint" / "README.md"
            self.assertTrue(readme_path.exists())
            self.assertIn("sopify:auto:goal:start", readme_path.read_text(encoding="utf-8"))
            self.assertFalse((workspace / ".sopify-skills" / "history" / "index.md").exists())
