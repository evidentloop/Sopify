---
plan_id: 20260519_p4d_copilot_cli_pilot
feature_key: p4d_copilot_cli_pilot
level: standard
lifecycle_state: completed
---

# 任务清单

## S1: Prompt 资产创建

- [x] 从 Codex/Skills/CN/AGENTS.md 派生 Copilot 中文版本，裁剪 runtime 依赖
- [x] 创建 `Copilot/Skills/CN/COPILOT.md`
- [x] 新增接续增强消费指令 + 交互/审计增强消费指令
- [x] EN 版本暂不创建（后续按社区需求快速扩展）
- [x] Shadow writer 指令不进默认 prompt；作为独立 optional experiment 段落，需显式启用
- [x] 不创建 `.github/copilot-instructions.md`（通用 repo 配置文件不由 Sopify 占有，与 AGENTS.md/CLAUDE.md 宿主专属文件不同）

## S2: Installer Adapter ⏸️ DEFERRED → 见 D3

> P4d 不创建 installer adapter。Copilot 用 repo-local 资产 + 手工接入完成验证。
> 原因见 D3 决策记录。

## S3: Continuation Smoke 验证

- [x] 场景 1：消费 `current_handoff.json` 的 `required_host_action` + `artifacts`，结合 `plan/` 目录和 `current_run.json`，正确复述当前上下文（活跃 plan、最后步骤、下一步预期）
- [x] 场景 2：读 pending checkpoint（clarification/decision）→ 识别类型并呈现给用户
- [x] 场景 3：读 gate_receipt 查看上一轮执行的审计历史记录（不作为当前轮次的授权依据）
- [x] 验证报告输出

> S3 验证通过。在独立 Copilot CLI 会话中完成：
> - 场景 1：正确复述活跃 plan / design 阶段 / S1 完成 + S2 deferred / confirm_decision 3 选项
> - 场景 2：展示 decision question + options + recommended 标记 + tasks.md 预填信息
> - 场景 3：结构化表格展示 gate_receipt + "仅供参考，不作当前轮授权依据" + 正确解释 checkpoint_only

## S3.5: 轻量 Handoff Writer Shadow Experiment ⏸️ MOVED TO P5

> P4d 不执行 shadow writer experiment。S3.5 的工作项已移交 P5 scope。
> P5 工作项名称：Shadow writer gap analysis / handoff production detachment。
> 不影响 P4d 主结论（S3 通过 = P4d 通过）。

## S4: 入口语义验证 (Continuation Entry Convergence)

- [x] Inspect Active Work 路径验证
- [x] Continue Active Work 路径验证
- [x] Start New Work + 活跃工作仲裁验证
- [x] 确认不依赖 `~go exec` 语法

> S4 验证通过。在独立 Copilot CLI 会话中完成：
> - Inspect：结构化表格展示活跃 plan / 阶段 / 任务状态 / 等待项
> - Continue：按 confirm_decision 展示 3 选项 + 推荐标记，等待用户确认不自行推进
> - Start New：提示"当前有进行中的工作"+ 确认提问
> - ~go exec：正确拒绝，识别为 runtime 专属指令

## S5: 结论文档

- [x] 试点报告：接入成本、验证结果、发现问题
- [x] 更新 design.md 宿主能力矩阵
- [x] 产出 P5 输入：runtime surface 证据汇总 + keep/defer 裁定
- [x] 归档到 history/2026-05/

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

### D3: Installer Adapter 延迟

**问题**：S2 是否创建 `installer/hosts/copilot.py` 正式接入 installer mainline？

**现状**：
- `HostAdapter` 抽象假设 `header_filename` + `destination_root` + `skills/sopify` 三层结构（`base.py:17,65`）
- Copilot 无宿主私有 header 文件，资产在 repo-local `Copilot/Skills/CN/`，不走 `home_root` 部署
- `SupportTier` 枚举（`models.py:19`）无 `payload_capable` 值，该术语是蓝图概念不是代码枚举
- `.sopify-runtime` 是 deep_verified runtime bundle 目录，Copilot 不需要

**选项**：
- A) 硬塞现有 HostAdapter → 语义不干净的假 adapter
- B) 改 installer 抽象 → scope 膨胀，不属于 P4d
- C) 跳过，repo-local 资产 + 手工验证

**决策**：C。P4d 是 pilot 验证，不改 installer 抽象。S3 用 repo-local `Copilot/Skills/CN/COPILOT.md` 直接验证。

**P5 条件**：若 P4d 验证通过且社区有 installer 集成需求，P5 可评估 HostAdapter 抽象扩展（payload-only adapter 模式）。
