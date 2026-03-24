from __future__ import annotations

from tests.runtime_test_support import *


class SkillRunnerTests(unittest.TestCase):
    def test_runtime_skill_runner_rejects_invalid_permission_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_entry = workspace / "skill_runtime.py"
            runtime_entry.write_text(
                "def run_skill(**kwargs):\n    return {'ok': True}\n",
                encoding="utf-8",
            )
            skill = SkillMeta(
                skill_id="runtime-demo",
                name="runtime-demo",
                description="runtime-demo",
                path=runtime_entry,
                source="project",
                mode="runtime",
                runtime_entry=runtime_entry,
                permission_mode="unsupported_mode",
            )

            with self.assertRaisesRegex(SkillExecutionError, "Unsupported permission mode"):
                run_runtime_skill(skill, payload={})

    def test_runtime_skill_runner_rejects_host_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_entry = workspace / "skill_runtime.py"
            runtime_entry.write_text(
                "def run_skill(**kwargs):\n    return {'ok': True}\n",
                encoding="utf-8",
            )
            skill = SkillMeta(
                skill_id="runtime-demo",
                name="runtime-demo",
                description="runtime-demo",
                path=runtime_entry,
                source="project",
                mode="runtime",
                runtime_entry=runtime_entry,
                host_support=("claude",),
                permission_mode="dual",
            )

            with mock.patch.dict("os.environ", {"SOPIFY_HOST_NAME": "codex"}, clear=False):
                with self.assertRaisesRegex(SkillExecutionError, "not allowed to execute runtime skill"):
                    run_runtime_skill(skill, payload={})

    def test_runtime_skill_runner_allows_supported_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_entry = workspace / "skill_runtime.py"
            runtime_entry.write_text(
                "def run_skill(**kwargs):\n    return {'ok': True, 'value': kwargs.get('value')}\n",
                encoding="utf-8",
            )
            skill = SkillMeta(
                skill_id="runtime-demo",
                name="runtime-demo",
                description="runtime-demo",
                path=runtime_entry,
                source="project",
                mode="runtime",
                runtime_entry=runtime_entry,
                host_support=("codex",),
                permission_mode="dual",
            )

            with mock.patch.dict("os.environ", {"SOPIFY_HOST_NAME": "codex"}, clear=False):
                result = run_runtime_skill(skill, payload={"value": 7})
            self.assertEqual(result["ok"], True)
            self.assertEqual(result["value"], 7)
