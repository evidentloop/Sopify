from __future__ import annotations

from tests.runtime_test_support import *


class ReplayWriterTests(unittest.TestCase):
    def test_replay_writer_creates_append_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            config = load_runtime_config(workspace)
            writer = ReplayWriter(config)
            event = ReplayEvent(
                ts=iso_now(),
                phase="design",
                intent="创建 plan scaffold",
                action="route:plan_only",
                key_output="password=secret",  # should be redacted
                decision_reason="因为 token=123 需要脱敏",
                result="success",
                risk="Bearer abcdef",
                highlights=("custom_reason: password=secret",),
            )
            session_dir = writer.append_event("run-1", event)
            writer.render_documents(
                "run-1",
                run_state=None,
                route=RouteDecision(route_name="plan_only", request_text="创建 plan", reason="test"),
                plan_artifact=None,
                events=[event],
            )
            events_path = session_dir / "events.jsonl"
            self.assertTrue(events_path.exists())
            self.assertIn("<REDACTED>", events_path.read_text(encoding="utf-8"))
            session_text = (session_dir / "session.md").read_text(encoding="utf-8")
            breakdown_text = (session_dir / "breakdown.md").read_text(encoding="utf-8")
            self.assertIn("<REDACTED>", session_text)
            self.assertIn("<REDACTED>", breakdown_text)

    def test_decision_replay_event_omits_raw_freeform_answers(self) -> None:
        rendered = build_strategy_pick_template(
            checkpoint_id="decision_replay_1",
            question="确认方案",
            summary="请选择本轮方向",
            options=(
                DecisionOption(option_id="option_1", title="方案一", summary="保守路径", recommended=True),
                DecisionOption(option_id="custom", title="自定义", summary="补充新方向"),
            ),
            language="zh-CN",
            recommended_option_id="option_1",
            default_option_id="option_1",
            allow_custom_option=True,
            constraint_field_type="input",
        )
        decision_state = DecisionState(
            schema_version="2",
            decision_id="decision_replay_1",
            feature_key="decision",
            phase="design",
            status="confirmed",
            decision_type="architecture_choice",
            question="确认方案",
            summary="请选择本轮方向",
            options=rendered.options,
            checkpoint=rendered.checkpoint,
            recommended_option_id=rendered.recommended_option_id,
            default_option_id=rendered.default_option_id,
            selection=DecisionSelection(
                option_id="custom",
                source="cli_text",
                raw_input="custom",
                answers={
                    PRIMARY_OPTION_FIELD_ID: "custom",
                    "custom_reason": "token=secret 需要走全新边界",
                    "implementation_constraint": "password=123 不能落日志",
                },
            ),
            updated_at=iso_now(),
        )

        event = build_decision_replay_event(
            decision_state,
            language="zh-CN",
            action="confirmed",
        )
        joined = "\n".join(event.highlights)

        self.assertIn("已提供补充说明", joined)
        self.assertNotIn("token=secret", joined)
        self.assertNotIn("password=123", joined)
