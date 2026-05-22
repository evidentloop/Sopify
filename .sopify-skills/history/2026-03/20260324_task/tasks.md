---
plan_id: 20260324_task
feature_key: learning-path-steering
level: standard
lifecycle_state: archived
plan_kind: steering
execution_gate_hint:
  status: blocked
  blocking_reason: steering_plan_requires_followup_implementation_plans
  next_required_action: create_followup_plans_then_execute_narrow_scope_plan
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: false
plan_status: on_hold
---

# 任务清单: 从 HelloAGENTS / Superpowers 对比收口 Sopify 的学习路径与实施顺序

## 当前状态

- `2026-03-24` 基线清理：本 steering plan 保留为路线参考，但暂标记为 `on_hold`，不直接进入执行。
- 恢复条件：仅在需要重新做路线收口时恢复；实际实施优先进入更窄的 follow-up implementation plan。

## A. 已确认结论

- [x] A.1 Sopify 的护城河是 runtime 机器契约与 plan 生命周期，不应为借鉴而削弱
- [x] A.2 当前 visible active plan 更偏 control plane，存在“复杂度向内生长”的风险
- [x] A.3 从 Superpowers 最值得学的是两阶段复审纪律，而不是先做完整子智能体平台
- [x] A.4 从 HelloAGENTS 最值得学的是验证循环、`status/doctor`、渐进式降级与分发产品化
- [x] A.5 “更好的帮用户写代码的工具”当前优先级应高于“更强的 Sopify 元系统”
- [x] A.6 本 plan 是 steering plan，不适合直接进入大范围开发实施

## B. 待推进路线

依赖关系：
- Group 2 依赖 Group 1 的优先级确认；
- Group 3 建议在 Group 2 之后；
- Group 4 建议在 Group 2 或 Group 3 之后；
- Group 5 最后执行。

## Group 1 — 收口当前优先级

- [x] 1.1 在 `20260320_helloagents_integration_enhancements` 的 plan 文件中找到超出当前范围的事项，标记为 `[-]` 并注明延后原因
- [x] 1.2 在 `20260320_helloagents_integration_enhancements` 的背景或设计文件中重申当前实现边界：仅保留 `registry + status/doctor + README matrix`
- [x] 1.3 在本 steering plan 中固化两层顺序说明：先规划 `develop-quality-loop`，但先实施收窄后的 `helloagents-integration-enhancements`
- [x] 1.4 在本 steering plan 中固化产品级判断口径，用于后续评估 Sopify 是否更像“帮用户写代码的工具”

**Gate — Group 1 完成后：**
- [x] 1.G `20260320_helloagents_integration_enhancements` 已完成范围收窄且延后项已落盘；本 steering plan 已明确 planning order 与 implementation order

验收标准:

- 当前路线不再同时追多个方向
- “该学什么”和“先做什么”被清楚区分
- 明确哪些方向延后，不再默认都要做

## Group 2 — 产出 `develop-quality-loop` 实现 plan（推荐下一步）

- [x] 2.1 创建独立 plan 包：`.sopify-skills/plan/20260324_develop-quality-loop/`
- [x] 2.2 在 `background.md` 中写清问题定义、范围边界、非目标与成功标准
- [x] 2.3 在 `design.md` 中写清四类核心内容：验证命令发现顺序、失败重试与根因分类、两阶段复审、handoff/replay/state 记录方式
- [x] 2.4 在 `tasks.md` 中拆出可执行任务与 gate，保证每项任务有明确验证方式
- [x] 2.5 评审该 plan 包，确认其不依赖原生子智能体平台即可先落地

**Gate — Group 2 完成后：**
- [x] 2.G `develop-quality-loop` plan 包已存在，且 `background/design/tasks` 三个文件都显式覆盖验证发现、重试/根因、两阶段复审、handoff/replay 结果记录

验收标准:

- 路线直接面向 develop 体验，而不是继续抽象 runtime 元结构
- 每个子任务都有明确可验证结果
- 可以在不引入复杂编排的前提下先落地

## Group 3 — 完成收窄后的 `helloagents-integration-enhancements`

- [ ] 3.1 落地 host capability registry 的单一事实源
- [ ] 3.2 落地 `sopify status`
- [ ] 3.3 落地 `sopify doctor`
- [ ] 3.4 补齐 README / README_EN 宿主矩阵与状态说明
- [ ] 3.5 补齐 registry / status / doctor 的稳定 contract 测试

**Gate — Group 3 完成后：**
- [ ] 3.G 用户可以通过只读命令看到支持矩阵、workspace 健康度与修复建议

验收标准:

- 支持现状和失败原因对用户可见
- 不新增多宿主 scaffold
- 不引入 runtime 深重构

## Group 4 — 产出 `runtime-gate-degradation-mode` 实现 plan

- [ ] 4.1 枚举 hard-fail evidence 与 degradable evidence
- [ ] 4.2 定义 `gate_passed=degraded` 的 contract 及宿主响应规则
- [ ] 4.3 定义 degraded 模式允许的 `allowed_response_mode`
- [ ] 4.4 生成独立 plan 包，并明确需要补的测试断言

**Gate — Group 4 完成后：**
- [ ] 4.G 已有受限降级方案，但不破坏 `manifest-first + handoff-first` 主链

验收标准:

- 降级是显式、受限、可测试的
- 不把关键 evidence 缺失偷偷放行

## Group 5 — 产出 `one-liner-distribution` 实现 plan

- [ ] 5.1 定义打包入口与最小渠道范围
- [ ] 5.2 定义 `install.sh / install.ps1` 的行为边界
- [ ] 5.3 定义安装后如何复用 bootstrap 与 doctor
- [ ] 5.4 明确分发依赖于 Group 3 的 registry / doctor 底座

**Gate — Group 5 完成后：**
- [ ] 5.G 已形成独立分发 plan，且没有绕开现有 bundle / bootstrap / doctor 主链

验收标准:

- 分发方案建立在稳定产品内核之上
- 不把“一键安装”建立在不可诊断状态之上

## C. 明确延后项

- [-] C.1 多宿主 scaffold 扩张（`opencode / gemini / qwen / grok`）
- [-] C.2 原生子智能体编排平台
- [-] C.3 低门槛 skill 注册
- [-] C.4 继续扩 plan lifecycle / history / index 元系统

## D. 推荐顺序

### Planning Order

1. Group 1：先确认优先级与延后项
2. Group 2：先开 `develop-quality-loop` 的独立实现 plan
3. Group 4：按需产出 `runtime-gate-degradation-mode` 实现 plan
4. Group 5：按需产出 `one-liner-distribution` 实现 plan

### Implementation Order

1. Group 3：先完成收窄后的 `helloagents-integration-enhancements`
2. 执行 `develop-quality-loop`
3. 再执行 `runtime-gate-degradation-mode`
4. 最后执行 `one-liner-distribution`

## E. Steering Plan 完成条件

- [x] E.1 `20260320_helloagents_integration_enhancements` 已完成范围收窄，超范围项已标 `[-]`
- [x] E.2 独立的 `develop-quality-loop` plan 包已生成并通过评审
- [x] E.3 本 plan 已明确 planning order 与 implementation order，且后续实现入口无歧义

当 E.1-E.3 满足时，本 steering plan 可评估为 `archive_ready: true`。
