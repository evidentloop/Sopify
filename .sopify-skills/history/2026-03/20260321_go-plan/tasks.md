---
plan_id: 20260321_go-plan
feature_key: go-plan
level: standard
lifecycle_state: archived
knowledge_sync:
  project: skip
  background: skip
  design: skip
  tasks: skip
archive_ready: true
decision_checkpoint:
  required: true
  decision_id: decision_0b7675d8
  selected_option_id: option_1
  status: confirmed
---

# 任务清单: ~go plan

目录: `.sopify-skills/plan/20260321_go-plan/`

## 1. workspace pilot
- [x] 1.1 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/.sopify-skills/user/preferences.md` 中补充“第一性原理 + 两段式输出”作为当前 workspace 长期偏好试运行版。
- [x] 1.2 校验该偏好只通过 preload 注入，不改变 `project.md`、blueprint 或 runtime machine contract。
- [x] 1.3 把“深度交互只在明显信号命中时触发”写成可执行文案，并与 `preferences.md` 的风格规则解耦。
- [x] 1.4 明确一条回滚规则：若发现对 quick-fix 或 consult 过重，可直接回退 preference 文本而不影响底层能力。

## 2. analyze 提炼通用子集
- [x] 2.1 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/Codex/Skills/CN/skills/sopify/analyze/references/analyze-rules.md` 中加入 4 个稳定能力：目标/路径分离、目标模糊先澄清、次优路径给替代、SMART 成功标准收口。
- [x] 2.2 同步 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/Codex/Skills/EN/skills/sopify/analyze/references/analyze-rules.md`，保证中英文规则语义一致。
- [x] 2.3 运行 `bash scripts/sync-skills.sh` 与 `bash scripts/check-skills-sync.sh`，把改动同步到 `Claude/Skills/{CN,EN}` 镜像并检查无漂移。

## 3. promotion gate
- [x] 3.1 在 plan 与 README 中补充 trigger matrix，明确强信号、弱信号与默认不触发场景。
- [x] 3.2 建立最小样本集：总样本 `>= 45`，其中 analyze 样本 `>= 30`，控制样本 `>= 15`。
- [x] 3.3 覆盖至少 3 类 pilot 环境：业务应用、runtime/infra、quick-fix 高频或等价控制场景。
- [x] 3.4 固定通过阈值：有帮助率 `>= 80%`、误报率 `<= 10%`、漏报率 `<= 20%`、中位额外交互成本 `<= 1` 轮（当前作为 pilot 目标门槛冻结）。
- [x] 3.5 固定回滚条件与版本记录方式，保证后续每轮规则优化都可追溯、可比较、可回退。

## 4. 验证
- [x] 4.1 增补 prompt-layer 或 runtime 相关测试，至少覆盖：目标模糊触发澄清、存在更短路径时给出替代建议、quick-fix 不被强制拉长。
- [x] 4.2 为 promotion gate 设计人工评审 rubric，记录“触发是否有帮助”和“是否明显误伤轻场景”。
- [x] 4.3 用至少 3 类仓库或等价样本跑 pilot，输出一轮可审计评估结果（`45` 样本 / `3` 类环境已完成，聚合结果写入 `external_archive://pilot_round1/round1_aggregation.md`；Batch 2/3 先按 post-v1 校准执行，随后已被吸收进独立 decision pass，不再以半完成状态挂在本轮 plan 上）。

## 5. 文档
- [x] 5.1 更新 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/README.md` 与 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/README_EN.md`，补充“分层矩阵”和“何时提升到底层”的说明。
- [x] 5.2 如最终采纳 analyze 子集，补充 blueprint 或 changelog，记录这是“从 workspace preference 提炼出的稳定默认能力”，而不是一次性风格指令。

## 6. 独立 Issue: 元评审不应生成新 plan
- [x] 6.1 以 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/.sopify-skills/plan/20260321_go-plan/issue_meta_review_no_new_plan.md` 作为独立 issue 文档，记录现象、根因假设、范围与验收标准。
- [x] 6.2 单独评估 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/router.py` 中 runtime-first guard 与 consultation 判定的顺序和关键词边界。
- [x] 6.3 设计至少 3 个回归样本：plan 评分、plan 追问、plan 风险复核，确保这类元评审不再生成新的 scaffold plan。

## 7. 独立 Issue: 严格单 active plan + topic_key 元数据
- [x] 7.1 以 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/.sopify-skills/plan/20260321_go-plan/issue_single_active_plan_reuse_with_topic_key.md` 作为独立 issue 文档，固定 canonical active plan、复用优先级、topic_key 元数据边界和验收标准。
- [x] 7.2 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/engine.py` 中实现严格单 active plan 规则：默认复用当前 active plan，只有显式新建或显式切换时才允许新 scaffold。
- [x] 7.3 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/plan_scaffold.py` 与 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/models.py` 中补充 `topic_key` 元数据和现有 plan 读取能力；当前版本不启用 no-active-plan 自动匹配。
- [x] 7.4 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/router.py` 中为 active-plan 元评审增加 consultation 旁路，避免 process-semantic review 再次误触发 workflow scaffold。
- [x] 7.5 补充 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/tests/test_runtime.py` 回归样本，覆盖 active plan 复用、显式切换、无 active plan 不自动复用、meta-review 不新建 plan。
- [x] 7.6 将 `.sopify-skills/state/current_plan.json`、`.sopify-skills/state/current_run.json` 与 `.sopify-skills/state/current_handoff.json` 重新绑定到 canonical plan `20260321_go-plan`，并把重复 plan 视为 superseded 待合并目录。
- [x] 7.7 将 `20260321_v1-preferences-md-analyze`、`20260321_task-ba2454`、`20260321_task-a93812` 的有效语义回收进 canonical plan，并在 issue 文档中记录 merged provenance。
- [x] 7.8 删除已完成语义回收的重复 plan 目录，不把它们写入正式 `history/index.md`。

## 8. 独立 Issue: 从 7/10 提升到 8.5+ 的最小补丁
- [x] 8.1 以 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/.sopify-skills/plan/20260321_go-plan/issue_raise_plan_reuse_fix_to_8_5.md` 作为独立 issue 文档，固定残留问题、最小修补边界、验收标准与验证顺序。
- [x] 8.2 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/engine.py` 中为 planning clarification 引入与 decision 分支一致的 active-plan preserve / rebind 逻辑，避免 clarification 期间无条件丢失 `current_plan`。
- [x] 8.3 在 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/runtime/plan_scaffold.py` 中收紧 `explicit new plan` 文案边界，去掉 `其他 plan` 这类高歧义模式，保留真正的新建强信号。
- [x] 8.4 补充 `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills/tests/test_runtime.py` 回归样本，至少覆盖：clarification 后复用 active plan、显式新建仍生效、包含“其他 plan”的评审语句不误触发新 scaffold。
- [x] 8.5 继续使用 `python3 -m unittest` 跑相关子集，覆盖 `PlanReuseRuntimeTests`、`RouterTests`、`EngineIntegrationTests` 的新增样本。
- [x] 8.6 允许安装 `pytest` 并补跑 `python3 -m pytest -q tests/test_runtime.py`，确保测试入口不再只依赖 `unittest`。

## 9. 收口与决策
- [x] 9.1 基于 `45` 样本聚合结果单独完成 `hold / review / propose-promotion` 的 decision pass，不把 Batch 2/3 caution 绑回本轮完成定义。
- [x] 9.2 最终确认 `propose-promotion` 作为本 plan 的正式决策；Batch 2/3 caution 转入后续 wording/examples 优化，不再作为本轮 promotion 决策阻断项。
- [x] 9.3 吸收 `post_v1_batch23_calibration_prep.md` 中仍有价值的上下文到结果性文件，并删除该 prep 中间稿，只保留审计证据、聚合结果与正式结论。
