---
plan_id: 20260519_p4d_copilot_cli_pilot
feature_key: p4d_copilot_cli_pilot
level: standard
lifecycle_state: active
---

# 任务清单

## S1: Prompt 资产创建

- [ ] 从 Codex/Skills/CN/AGENTS.md 派生 Copilot 中文版本，裁剪 runtime 依赖
- [ ] 创建 `Copilot/Skills/CN/COPILOT.md`
- [ ] 新增接续增强消费指令 + 交互/审计增强消费指令
- [ ] EN 版本暂不创建（后续按社区需求快速扩展）
- [ ] Shadow writer 指令不进默认 prompt；作为独立 optional experiment 段落，需显式启用

## S2: Installer Adapter

- [ ] 创建 `installer/hosts/copilot.py`
- [ ] 注册到 `installer/hosts/__init__.py`
- [ ] 声明 SupportTier.payload_capable + declared_enhancements: [CONTINUATION]
- [ ] INTERACTION / AUDIT 不预先声明，待 S3 验证通过后按结果追加

## S3: Continuation Smoke 验证

- [ ] 场景 1：消费 `current_handoff.json` 的 `required_host_action` + `artifacts`，结合 `plan/` 目录和 `current_run.json`，正确复述当前上下文（活跃 plan、最后步骤、下一步预期）
- [ ] 场景 2：读 pending checkpoint（clarification/decision）→ 识别类型并呈现给用户
- [ ] 场景 3：读 gate_receipt 查看上一轮执行的审计历史记录（不作为当前轮次的授权依据）
- [ ] 验证报告输出

## S3.5: 轻量 Handoff Writer Shadow Experiment

- [ ] 设计 shadow handoff schema（canonical handoff 的字段子集 + experimental 标记）
- [ ] 创建独立 experiment 配置（不进默认 prompt，需显式启用）
- [ ] 验证 shadow 产出的 `required_host_action` 使用 canonical 值域
- [ ] Lab-only harness：手动将 shadow 拷贝为 canonical → 在 Codex 中执行 schema replay / consumption check
- [ ] 产出：字段覆盖率 / 缺口 / 是否影响接续的 gap analysis 表（不是"兼容/不兼容"二元结论）

> 注意：Shadow experiment 独立于正式产品面。不直接写 `current_handoff.json`，不声称"Copilot→Codex 双向接续已成立"。产出为 P5/P6 working hypothesis 的输入证据。

## S4: 入口语义验证 (Continuation Entry Convergence)

- [ ] Inspect Active Work 路径验证
- [ ] Continue Active Work 路径验证
- [ ] Start New Work + 活跃工作仲裁验证
- [ ] 确认不依赖 `~go exec` 语法

## S5: 结论文档

- [ ] 试点报告：接入成本、验证结果、发现问题
- [ ] 更新 design.md 宿主能力矩阵
- [ ] 产出 P5 输入：keep/delete/downgrade 裁定建议
- [ ] 归档到 history/2026-05/

## 待决策

### D1: Handoff Writer 定位

**问题**：Copilot 纯消费者不写 canonical state → Copilot→Deep 方向无接续信息。

- A) P4d 不涉及 writer
- B) P4d 包含 shadow experiment（不写 canonical state，产出 gap analysis 作为 P5/P6 working hypothesis）

**决策**：B。Shadow experiment 是隔离试验，不进默认产品面。

### D2: Runtime 渐进替代路径（Working Hypothesis）

基于 shadow experiment 结果，P5/P6 可评估：
- P5：shadow gap analysis 是否支持"handoff 生产层可从 runtime 拆出"假设 → 判定哪些 runtime surface 可削减
- P6：若 P5 裁定成立 → 评估 Codex/Claude 从重 runtime 迁移到"轻 writer + 保留 Validator/receipt/checkpoint authority"组合的可行性

此路径为 working hypothesis，不是已确认决策。P4d 只提供证据，不执行迁移。
