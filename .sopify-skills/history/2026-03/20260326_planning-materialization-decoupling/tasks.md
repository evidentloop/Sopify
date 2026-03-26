---
plan_id: 20260326_planning-materialization-decoupling
feature_key: planning-materialization-decoupling
level: standard
lifecycle_state: archived
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: true
plan_status: completed
---

# 任务清单: 规划流程与方案包物化解耦

## Group 1 — 锁定 contract 边界

说明：本组先锁定 contract / schema / 语义边界，属于 design freeze；不要求在本组直接完成全部代码接线。

- [x] 1.1 在 `RouteDecision` 中引入 `plan_package_policy = none | confirm | immediate`
- [x] 1.2 明确 `should_create_plan` 仅作为 `immediate` 的兼容派生值
- [x] 1.3 定义 proposal pending 的三层停点语义边界：
  `confirm_plan_package / review_or_execute_plan / confirm_execute`
- [x] 1.4 明确 `~go plan` 只跳过建包确认，不跳过 clarification / decision

**Gate — Group 1 完成后：**
- [x] 1.G planning intent 与 plan package materialization 的 contract 已拆开，且不污染现有 execution-confirm contract

## Group 2 — Proposal 状态与 checkpoint 设计

- [x] 2.1 定义 `current_plan_proposal.json` 的 v1 schema
- [x] 2.2 明确使用 `checkpoint_id + reserved_plan_id`，v1 不引入 `proposal_id`
- [x] 2.3 明确 `proposed_path` confirm 前后必须一致
- [x] 2.4 定义 `checkpoint_kind = plan_proposal`
- [x] 2.5 定义 `required_host_action = confirm_plan_package`

**Gate — Group 2 完成后：**
- [x] 2.G proposal 有结构化状态文件与 checkpoint contract，宿主在确认前有足够信息展示

## Group 3 — Router / flow 设计

- [x] 3.1 明确显式建包请求与非显式规划请求的分类规则
- [x] 3.2 定义 consult/meta-debug bypass，覆盖“为什么生成了 plan / 不要再生成 plan”等善后请求
- [x] 3.3 设计 `_classify_pending_plan_proposal()`
- [x] 3.4 明确 `continue / next / status / revise / cancel / ~go exec` 在 proposal pending 下的行为
- [x] 3.5 明确 proposal pending 不复用 `resume_active`

**Gate — Group 3 完成后：**
- [x] 3.G proposal pending 没有 dead end，且 `~go exec` 无法绕过 proposal checkpoint

## Group 4 — Engine / handoff / gate / output 接线

- [x] 4.1 定义 engine 在 `confirm` 模式下“先 proposal、后 materialize”的状态变化
- [x] 4.2 定义 `revise_plan_proposal` 的 engine 行为：
  允许刷新 proposal 内容字段并回到 `confirm_plan_package`，但不得漂移 `topic_key / reserved_plan_id / proposed_path`
  若 revise 需要改变 `topic_key / proposed_path`，则立即清理旧 proposal，并在同一次 engine 调用内转入新的 planning 稳定停点，而不是原地漂移
- [x] 4.3 定义 confirm 后如何复用 `reserved_plan_id` 创建真实 scaffold
- [x] 4.4 定义 `confirm_plan_package -> CHECKPOINT_ONLY`
- [x] 4.5 定义 output 中 proposal pending 的摘要与 next hint
- [x] 4.6 定义宿主文档中对 `confirm_plan_package` 的消费规则
- [x] 4.7 更新 repo 内宿主源文档：
  `Codex/Skills/CN/AGENTS.md`、`Codex/Skills/EN/AGENTS.md`、`Claude/Skills/CN/CLAUDE.md`、`Claude/Skills/EN/CLAUDE.md`
  使其显式反映 `confirm_plan_package` 的消费规则
  注：本 plan 不要求直接修改 vendored 副本或全局安装产物

**Gate — Group 4 完成后：**
- [x] 4.G handoff / gate / output / host docs 对 proposal checkpoint 的机器契约一致

## Group 5 — 验证与回归

- [x] 5.1 router 测试覆盖：
  - 善后 / 元问题走 consult
  - 非显式复杂请求走 `confirm`
  - `~go plan` 走 `immediate`
- [x] 5.2 engine 测试覆盖：
  - proposal 先生成，不直接建包
  - revise 后仅刷新 proposal 内容字段，不漂移 identity/path
  - revise 若要求变更 topic/path，则立即清理旧 proposal，并在同一次 engine 调用内进入新的 planning 结果
  - `status` 只读取当前 proposal 并返回摘要，不修改 proposal/state
  - confirm 后 path 不漂移
  - 建包后停在 `review_or_execute_plan`
- [x] 5.3 gate 测试覆盖：
  - `confirm_plan_package -> CHECKPOINT_ONLY`
- [x] 5.4 regression 覆盖：
  - 同意建包不等于同意执行
  - `review_or_execute_plan` 与 `confirm_execute` 语义不变
- [x] 5.5 regression 覆盖历史误触发样例：
  - 输入 `那你执行吧 逻辑严谨`
  - 预期进入 proposal-first flow，不得在未确认时直接创建 `.sopify-skills/plan/...`

**Gate — Group 5 完成后：**
- [x] 5.G proposal-first flow 可验证，且不破坏既有 planning / execution 主链
