from __future__ import annotations

from tests.runtime_test_support import *


class SkillRegistryTests(unittest.TestCase):
    def _write_skill(self, root: Path, *, skill_id: str, description: str, mode: str = "advisory") -> None:
        skill_dir = root / skill_id
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_id}\ndescription: {description}\n---\n\n# {skill_id}\n",
            encoding="utf-8",
        )
        (skill_dir / "skill.yaml").write_text(
            f"id: {skill_id}\nmode: {mode}\n",
            encoding="utf-8",
        )

    def test_skill_registry_discovers_builtin_and_project_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "local-demo"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: local-demo\ndescription: local skill\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: local-demo\nmode: advisory\ntriggers:\n  - local\n",
                encoding="utf-8",
            )
            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home").discover()
            skill_ids = {skill.skill_id for skill in skills}
            self.assertIn("analyze", skill_ids)
            self.assertIn("model-compare", skill_ids)
            self.assertIn("local-demo", skill_ids)
            model_compare = next(skill for skill in skills if skill.skill_id == "model-compare")
            self.assertEqual(model_compare.mode, "runtime")
            self.assertIsNotNone(model_compare.runtime_entry)
            self.assertEqual(model_compare.entry_kind, "python")
            self.assertEqual(model_compare.handoff_kind, "compare")
            self.assertEqual(model_compare.supports_routes, ("compare",))
            self.assertEqual(model_compare.permission_mode, "dual")
            self.assertTrue(model_compare.requires_network)
            self.assertIn("codex", model_compare.host_support)
            self.assertIn("read", model_compare.tools)
            self.assertIn("network", model_compare.tools)

    def test_skill_registry_builtin_catalog_does_not_require_builtin_skill_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace = temp_root / "workspace"
            target_root = temp_root / "target"
            workspace.mkdir()
            target_root.mkdir()

            sync_script = REPO_ROOT / "scripts" / "sync-runtime-assets.sh"
            completed = subprocess.run(
                ["bash", str(sync_script), str(target_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)

            bundle_root = target_root / ".sopify-runtime"
            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, repo_root=bundle_root, user_home=workspace / "home").discover()
            skill_ids = {skill.skill_id for skill in skills}

            self.assertIn("analyze", skill_ids)
            self.assertIn("workflow-learning", skill_ids)
            self.assertIn("model-compare", skill_ids)

            model_compare = next(skill for skill in skills if skill.skill_id == "model-compare")
            self.assertEqual(model_compare.source, "builtin")
            self.assertEqual(model_compare.runtime_entry, (bundle_root / "scripts" / "model_compare_runtime.py").resolve())
            self.assertEqual(model_compare.path, (bundle_root / "runtime" / "builtin_catalog.py").resolve())

    def test_skill_registry_prefers_generated_builtin_catalog_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace = temp_root / "workspace"
            repo_root = temp_root / "repo"
            workspace.mkdir()
            (repo_root / "runtime").mkdir(parents=True)
            (repo_root / "runtime" / "builtin_catalog.py").write_text("# placeholder\n", encoding="utf-8")
            (repo_root / "runtime" / "builtin_catalog.generated.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "generated_at": "2026-03-19T00:00:00+00:00",
                        "skills": [
                            {
                                "id": "generated-only",
                                "names": {"en-US": "generated-only", "zh-CN": "generated-only"},
                                "descriptions": {"en-US": "generated", "zh-CN": "generated"},
                                "mode": "advisory",
                                "supports_routes": ["workflow"],
                                "permission_mode": "default",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, repo_root=repo_root, user_home=workspace / "home").discover()
            skill_ids = {skill.skill_id for skill in skills}
            self.assertIn("generated-only", skill_ids)
            generated = next(skill for skill in skills if skill.skill_id == "generated-only")
            self.assertEqual(generated.description, "generated")
            self.assertEqual(generated.supports_routes, ("workflow",))
            self.assertEqual(generated.permission_mode, "default")

    def test_skill_registry_does_not_override_builtin_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "analyze"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: analyze\ndescription: local override attempt\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: analyze\nmode: advisory\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home").discover()
            analyze = next(skill for skill in skills if skill.skill_id == "analyze")

            self.assertEqual(analyze.source, "builtin")
            self.assertNotEqual(analyze.description, "local override attempt")

    def test_skill_registry_allows_explicit_builtin_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "analyze"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: analyze\ndescription: local override\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: analyze\noverride_builtin: true\nmode: advisory\nsupports_routes:\n  - workflow\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home").discover()
            analyze = next(skill for skill in skills if skill.skill_id == "analyze")

            self.assertEqual(analyze.source, "project")
            self.assertEqual(analyze.description, "local override")
            self.assertTrue(analyze.metadata.get("override_builtin"))
            self.assertEqual(analyze.supports_routes, ("workflow",))

    def test_skill_registry_parses_permission_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "permission-demo"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: permission-demo\ndescription: local permission skill\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: permission-demo\n"
                "mode: runtime\n"
                "runtime_entry: local_runtime.py\n"
                "tools:\n"
                "  - read\n"
                "  - exec\n"
                "disallowed_tools:\n"
                "  - write\n"
                "allowed_paths:\n"
                "  - .\n"
                "requires_network: true\n"
                "host_support:\n"
                "  - codex\n"
                "permission_mode: dual\n",
                encoding="utf-8",
            )
            (project_skill / "local_runtime.py").write_text(
                "def run_skill(**kwargs):\n    return {'ok': True}\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home", host_name="codex").discover()
            permission_skill = next(skill for skill in skills if skill.skill_id == "permission-demo")

            self.assertEqual(permission_skill.tools, ("read", "exec"))
            self.assertEqual(permission_skill.disallowed_tools, ("write",))
            self.assertEqual(permission_skill.allowed_paths, (".",))
            self.assertTrue(permission_skill.requires_network)
            self.assertEqual(permission_skill.host_support, ("codex",))
            self.assertEqual(permission_skill.permission_mode, "dual")

    def test_skill_registry_host_support_fail_closed_when_host_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "host-locked"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: host-locked\ndescription: host locked skill\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: host-locked\n"
                "mode: advisory\n"
                "host_support:\n"
                "  - claude\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home", host_name="codex").discover()
            skill_ids = {skill.skill_id for skill in skills}
            self.assertNotIn("host-locked", skill_ids)

    def test_skill_registry_invalid_permission_mode_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_skill = workspace / "skills" / "invalid-permission"
            project_skill.mkdir(parents=True)
            (project_skill / "SKILL.md").write_text(
                "---\nname: invalid-permission\ndescription: invalid permission mode\n---\n\n# local\n",
                encoding="utf-8",
            )
            (project_skill / "skill.yaml").write_text(
                "id: invalid-permission\n"
                "mode: advisory\n"
                "permission_mode: unsupported_mode\n",
                encoding="utf-8",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=workspace / "home", host_name="codex").discover()
            skill_ids = {skill.skill_id for skill in skills}
            self.assertNotIn("invalid-permission", skill_ids)

    def test_skill_registry_workspace_precedence_over_user_for_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            user_home = workspace / "home"
            self._write_skill(
                workspace / ".agents" / "skills",
                skill_id="shared-skill",
                description="workspace-agents",
            )
            self._write_skill(
                user_home / ".agents" / "skills",
                skill_id="shared-skill",
                description="user-agents",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=user_home).discover()
            shared = next(skill for skill in skills if skill.skill_id == "shared-skill")

            self.assertEqual(shared.description, "workspace-agents")
            self.assertEqual(shared.source, "workspace")

    def test_skill_registry_workspace_alias_precedence_prefers_public_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            user_home = workspace / "home"
            self._write_skill(
                workspace / ".agents" / "skills",
                skill_id="alias-priority",
                description="from-agents",
            )
            self._write_skill(
                workspace / ".gemini" / "skills",
                skill_id="alias-priority",
                description="from-gemini",
            )
            self._write_skill(
                workspace / "skills",
                skill_id="alias-priority",
                description="from-project",
            )
            self._write_skill(
                workspace / ".sopify-skills" / "skills",
                skill_id="alias-priority",
                description="from-legacy-workspace",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=user_home).discover()
            alias_skill = next(skill for skill in skills if skill.skill_id == "alias-priority")

            self.assertEqual(alias_skill.description, "from-agents")
            self.assertEqual(alias_skill.source, "workspace")

    def test_skill_registry_user_alias_precedence_prefers_public_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            user_home = workspace / "home"
            self._write_skill(
                user_home / ".agents" / "skills",
                skill_id="user-priority",
                description="user-agents",
            )
            self._write_skill(
                user_home / ".gemini" / "skills",
                skill_id="user-priority",
                description="user-gemini",
            )
            self._write_skill(
                user_home / ".codex" / "skills",
                skill_id="user-priority",
                description="user-codex",
            )
            self._write_skill(
                user_home / ".claude" / "skills",
                skill_id="user-priority",
                description="user-claude",
            )
            self._write_skill(
                user_home / ".claude" / "skills",
                skill_id="claude-only",
                description="claude-only",
            )

            config = load_runtime_config(workspace)
            skills = SkillRegistry(config, user_home=user_home).discover()
            user_skill = next(skill for skill in skills if skill.skill_id == "user-priority")
            claude_skill = next(skill for skill in skills if skill.skill_id == "claude-only")

            self.assertEqual(user_skill.description, "user-agents")
            self.assertEqual(user_skill.source, "user")
            self.assertEqual(claude_skill.description, "claude-only")
            self.assertEqual(claude_skill.source, "user")
