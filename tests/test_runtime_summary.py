from __future__ import annotations

from tests.runtime_test_support import *


class SummaryContractTests(unittest.TestCase):
    def test_daily_summary_artifact_roundtrip_preserves_nested_contract(self) -> None:
        artifact = DailySummaryArtifact(
            summary_key="2026-03-19::/Users/weixin.li/Desktop/vs-code-extension/sopify-skills",
            scope=SummaryScope(
                local_day="2026-03-19",
                workspace_root="/Users/weixin.li/Desktop/vs-code-extension/sopify-skills",
                workspace_label="当前工作区",
                timezone="Asia/Shanghai",
            ),
            revision=2,
            generated_at="2026-03-19T21:21:41+08:00",
            source_window=SummarySourceWindow(
                from_ts="2026-03-19T00:00:00+08:00",
                to_ts="2026-03-19T21:21:41+08:00",
            ),
            source_refs=SummarySourceRefs(
                plan_files=(
                    SummarySourceRefFile(
                        path=".sopify-skills/plan/20260319_task-168cb6/design.md",
                        kind="plan",
                        updated_at="2026-03-19T20:58:00+08:00",
                    ),
                ),
                state_files=(
                    SummarySourceRefFile(
                        path=".sopify-skills/state/current_plan.json",
                        kind="state",
                        updated_at="2026-03-19T21:10:00+08:00",
                    ),
                ),
                handoff_files=(
                    SummarySourceRefFile(
                        path=".sopify-skills/state/current_handoff.json",
                        kind="handoff",
                        updated_at="2026-03-19T21:10:00+08:00",
                    ),
                ),
                git_refs=SummaryGitRefs(
                    base_ref="HEAD",
                    changed_files=(".sopify-skills/plan/20260319_task-168cb6/design.md",),
                    commits=(
                        SummaryGitCommitRef(
                            sha="abc1234",
                            title="Refine summary contract",
                            authored_at="2026-03-19T20:45:00+08:00",
                        ),
                    ),
                ),
                replay_sessions=(
                    SummaryReplaySessionRef(
                        run_id="20260319T132141_14a099",
                        path=".sopify-skills/replay/sessions/20260319T132141_14a099",
                        used_for="timeline",
                    ),
                ),
            ),
            facts=SummaryFacts(
                headline="今天完成了当前时间显示与 ~summary 主线收敛。",
                goals=(
                    SummaryGoalFact(
                        fact_id="goal-1",
                        summary="收窄当前切片，优先满足可复盘摘要需求。",
                        evidence_refs=("plan_files[0]",),
                    ),
                ),
                decisions=(
                    SummaryDecisionFact(
                        fact_id="decision-1",
                        summary="本期不先做 daily index。",
                        reason="~summary 一天通常只运行 1-2 次，现算现出更轻。",
                        status="confirmed",
                        evidence_refs=("plan_files[0]", "handoff_files[0]"),
                    ),
                ),
                code_changes=(
                    SummaryCodeChangeFact(
                        path=".sopify-skills/plan/20260319_task-168cb6/design.md",
                        change_type="modified",
                        summary="把 ~summary 数据契约收敛到可编码 schema。",
                        reason="让后续实现不依赖聊天回忆。",
                        verification="not_run",
                        evidence_refs=("git_refs.changed_files[0]",),
                    ),
                ),
                issues=(
                    SummaryIssueFact(
                        fact_id="issue-1",
                        summary="replay events 当前使用率不高。",
                        status="open",
                        resolution="",
                        evidence_refs=("replay_sessions[0]",),
                    ),
                ),
                lessons=(
                    SummaryLessonFact(
                        fact_id="lesson-1",
                        summary="摘要应优先绑定机器事实源，而不是自由聊天文本。",
                        reusable_pattern="先确定性收集，再模板渲染。",
                        evidence_refs=("state_files[0]", "handoff_files[0]"),
                    ),
                ),
                next_steps=(
                    SummaryNextStepFact(
                        fact_id="next-1",
                        summary="把 summary schema 映射到实际运行时实现。",
                        priority="medium",
                        evidence_refs=("plan_files[0]",),
                    ),
                ),
            ),
            quality_checks=SummaryQualityChecks(
                replay_optional=True,
                summary_runs_per_day="1-2",
                required_sections_present=True,
                missing_inputs=(),
                fallback_used=(),
            ),
        )

        payload = artifact.to_dict()
        restored = DailySummaryArtifact.from_dict(payload)

        self.assertEqual(payload["source_window"]["from"], "2026-03-19T00:00:00+08:00")
        self.assertEqual(restored.summary_key, artifact.summary_key)
        self.assertEqual(restored.scope.workspace_root, artifact.scope.workspace_root)
        self.assertEqual(restored.revision, 2)
        self.assertEqual(restored.source_refs.git_refs.commits[0].sha, "abc1234")
        self.assertEqual(restored.facts.decisions[0].status, "confirmed")
        self.assertTrue(restored.quality_checks.replay_optional)
        self.assertEqual(restored.to_dict(), payload)

    def test_daily_summary_markdown_preserves_iso_timestamp_for_internal_artifact(self) -> None:
        artifact = DailySummaryArtifact(
            summary_key="2026-03-19::/tmp/demo",
            scope=SummaryScope(
                local_day="2026-03-19",
                workspace_root="/tmp/demo",
                workspace_label="当前工作区",
                timezone="Asia/Shanghai",
            ),
            revision=1,
            generated_at="2026-03-19T21:21:41+08:00",
            source_window=SummarySourceWindow(
                from_ts="2026-03-19T00:00:00+08:00",
                to_ts="2026-03-19T21:21:41+08:00",
            ),
            source_refs=SummarySourceRefs(),
            facts=SummaryFacts(
                headline="今天围绕当前方案推进了关键实现。",
                goals=(),
                decisions=(),
                code_changes=(),
                issues=(),
                lessons=(),
                next_steps=(),
            ),
            quality_checks=SummaryQualityChecks(
                replay_optional=True,
                summary_runs_per_day="1-2",
                required_sections_present=True,
                missing_inputs=(),
                fallback_used=(),
            ),
        )

        markdown = render_daily_summary_markdown(artifact=artifact, language="zh-CN")

        self.assertIn("生成于: 2026-03-19T21:21:41+08:00", markdown)
        self.assertNotIn("生成于: 2026-03-19 21:21:41", markdown)
