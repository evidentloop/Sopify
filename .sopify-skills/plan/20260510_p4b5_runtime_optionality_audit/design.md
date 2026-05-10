# 技术设计: P4b.5 Runtime Optionality & Host Onboarding Audit

## 方案概述

1 个方案包，纯文档/审计变更。在 bridge 已定义的三级 ladder 之上，补充 **消费矩阵**（每级能碰什么）、**禁止面清单**（每级不能碰什么）、**blast radius 审计**（runtime 哪些模块在哪级可选），为 P4c 划定可执行边界。

## Scope 边界

### 在 scope 内

1. **Forbidden surface 正面化** — 将 `design.md:366` 的排除法隐式禁止转为每级宿主的显式禁止清单
2. **Consumption matrix** — 对每个主链真相文件和可审计凭证，裁定在每级梯度的消费定位（required / optional / forbidden）
3. **接续锚点 vs 授权凭证拆面** — 将 handoff（接续）、gate_receipt（运行凭证）、ExecutionAuthorizationReceipt（协议授权）分开归位
4. **Pending checkpoint 层级裁定** — 裁定 current_clarification / current_decision 在 payload_capable 是 required / optional / forbidden
5. **Blast radius 审计** — 评估 runtime 各主要模块（engine/router/gate/output/installer）在每级梯度的必需性
6. **P4c boundary statement** — 基于审计结论，明确 P4c 的可执行范围和验收前提

### 不在 scope 内

- 不重定义三级梯度（design.md:409-415 已冻结）
- 不改代码 / schema / Python API
- 不做 FeatureId → 梯度的可执行投影矩阵（design.md:419 明确属 P4c）
- 不改 installer / adapter / output
- 不新增 machine truth / route / state file

## 设计要点

### S1: Forbidden Surface 正面化

> 来源：design.md:340（运行态附属/可删派生）、design.md:366（未列入面默认可删）

将隐式 forbidden 面转为显式三列表：

| forbidden surface | 为什么禁止 | 来源 |
|-------------------|-----------|------|
| `state/sessions/*` | runtime 内部会话管理，非 contract 面 | design.md:340 |
| `state/last_route.json` | 可从 handoff/run 派生，derived surface | design.md:340, 328 |
| Route name 全集 / route taxonomy | runtime 内部路由枚举，不是宿主消费的 contract | design.md:366 |
| Output 渲染文案措辞（Next: / Status: 等 human hint） | derived 人类提示，不是 machine truth | design.md:374, 380, 393 |
| Runtime 内部模块边界（Python API 签名、class 结构） | 实现细节，不在 keep-list | design.md:366 |
| Gate 三元组直渲（gate_status / blocking_reason / plan_completion） | 内部 gate 状态机 leak | design.md:378 |
| Entry Guard Reason 内部守卫码 | runtime 内部守卫码 | design.md:388 |

**适用范围**：所有三级梯度。此表是绝对禁止面，无论 convention_only / payload_capable / deep_verified 均不得将上述面作为稳定消费 contract。

> deep_verified 宿主的 runtime 内部可能事实上读取这些值（如 route_name 用于渲染），但这属于 runtime 实现细节，不是宿主的 contract 承诺。P4c 收敛 output 时需消除此类 leak。

### S2: Consumption Matrix

> 来源：design.md:338（主链机器真相）、design.md:339（可审计凭证）、design.md:344-365（P4a keep-list）

将接续锚点、运行凭证、协议授权三类面分开归位：

**接续锚点（告诉下一步做什么）**

| surface | 文件 | convention_only | payload_capable | deep_verified | 来源 |
|---------|------|-----------------|-----------------|---------------|------|
| Handoff contract | `state/current_handoff.json` | forbidden | **待裁定** | required | design.md:355, 414 |
| Run state | `state/current_run.json` | forbidden | **待裁定** | required | design.md:338 |
| Plan binding | `state/current_plan.json` | forbidden | **待裁定** | required | design.md:338 |

> **注意**：handoff 在现有 ladder（design.md:414, 417）中是 payload_capable 的 opt-in 增强，不是准入条件。current_run 虽在 P4c 允许宿主消费的主链真相中（tasks.md:76），但现有 ladder 未将其列为中间层增强项。三者均作为待裁定对象，不预设并入"接续增强"。

**授权凭证（证明为什么被授权）**

| surface | 文件/规范 | convention_only | payload_capable | deep_verified | 来源 |
|---------|----------|-----------------|-----------------|---------------|------|
| Gate receipt（运行级） | `state/current_gate_receipt.json` | forbidden | **待裁定** | **待裁定**¹ | design.md:354, 364 |
| ExecutionAuthorizationReceipt（协议级） | protocol.md §6 | **待裁定** | **待裁定** | **待裁定**¹ | design.md:351 |
| Archive receipt | `state/current_archive_receipt.json` | forbidden | **待裁定** | optional | design.md:364 |

> ¹ deep_verified 按现状预期为 required，但不替代 S2 裁定。

> **EAR 层级说明**：ExecutionAuthorizationReceipt 是 protocol/doc contract（design.md:351），不是 runtime 专属产物。即便某梯度最终裁为 forbidden，理由应是"该梯度不承诺消费此协议面"，而非"无 runtime"。当前 gate_receipt 是一种常见运行态承载，不自动等同于 ExecutionAuthorizationReceipt 的唯一消费路径。避免把 runtime 耦合重新写回 contract 审计。

> **gate_receipt 消费者投影差异**：keep-list 表（design.md:354）将 gate_receipt 的 consumer 写为 `host / external_tool`，但 persistence red-line 表（design.md:364）写为 `external_tool`。此差异属本次审计范围——P4b.5 需裁定 payload_capable 宿主是否有合法消费 gate_receipt 的场景。

**Pending checkpoint（交互式等待）**

| surface | 文件 | convention_only | payload_capable | deep_verified | 来源 |
|---------|------|-----------------|-----------------|---------------|------|
| Clarification | `state/current_clarification.json` | forbidden | **待裁定** | required | design.md:338 |
| Decision | `state/current_decision.json` | forbidden | **待裁定** | required | design.md:338 |

> **裁定框架**：P4b.5 需在以下三档中为每个"待裁定"项选定位置：
> - **required**：进入该梯度的准入条件
> - **optional**：可选增强，不阻断准入（与 handoff 在 payload_capable 的现有定位一致）
> - **forbidden**：该梯度不得消费
>
> 裁定依据应基于真实接入场景分析（如"大模型规划 + 小模型编码 + 断点接续"），不做纯理论推导。
>
> **payload_capable 内部分档预期**：payload_capable 是能力带宽，不是单点能力。审计可能产出若干 opt-in 增强组合（如接续增强、交互增强、审计增强），每个组合消费不同的冻结 contract 面、支持不同的用户场景。P4b.5 需审计这些组合的依赖链和互斥关系，但不预设哪些是必选。

**长期知识（所有梯度均可消费）**

| surface | 物理对应 | 所有梯度 | 来源 |
|---------|---------|---------|------|
| Blueprint / Plan / History | `.sopify-skills/blueprint/`, `plan/`, `history/` | readable | design.md:336, 361 |
| Protocol | `blueprint/protocol.md` | readable | design.md:350-353 |
| Preferences / Feedback | `user/preferences.md`, `user/feedback.jsonl` | readable | design.md:337, 362 |

### S3: Blast Radius 审计

评估 runtime 各主要模块在每级梯度的必需性：

| runtime 模块 | convention_only | payload_capable | deep_verified | 备注 |
|-------------|-----------------|-----------------|---------------|------|
| `runtime/engine.py` | 不需要 | 不需要 | 需要 | 路由引擎，deep-only |
| `runtime/router.py` | 不需要 | 不需要 | 需要 | 路由决策 |
| `runtime/gate.py` | 不需要 | 不需要 | 需要 | gate 入口判定，deep-only 生产者 |
| `runtime/output.py` | 不需要 | 不需要 | 需要 | 渲染层 |
| `installer/` | 不需要 | 部分需要 | 需要 | payload 安装 |
| `runtime/context_snapshot.py` | 不需要 | 不需要 | 需要 | 会话上下文快照 |
| `runtime/failure_recovery.py` | 不需要 | 不需要 | 需要 | 容错恢复 |
| `runtime/message_templates.py` | 不需要 | 不需要 | 需要 | 消息模板 |
| `runtime/workspace_preflight.py` | 不需要 | 不需要 | 需要 | workspace 初始化 |

> **生产者 vs 消费者区分**：上表评估的是"新宿主是否需要运行该 runtime 模块"，不是"新宿主是否消费该模块的持久化产物"。新宿主读 `current_gate_receipt.json`（消费冻结 contract 文件）不等于它在接入契约上依赖 `runtime/gate.py`（当前生产者恰好是 deep runtime）。持久化 contract 消费面的评估在 S2，不在 S3。

### S4: P4c Boundary Statement

基于 S1-S3 审计结论，产出 P4c 的可执行前提声明：

1. P4c 可以假设的 invariant（来自 P4b.5 审计结论）
2. P4c 需要做的实施项（来自消费矩阵的"待裁定"已裁定结果）
3. P4c 不能做的事（来自 forbidden surface 和 scope 红线）

> 此声明落入 blueprint/tasks.md P4c 段或 blueprint/design.md 的 P4c 相关节。

## 产出物落点

| 产出 | 落入位置 | 说明 |
|------|---------|------|
| Forbidden surface 正面清单 | `blueprint/design.md` Host Capability Governance 节下新增 | 与现有 ladder 表同级 |
| Consumption matrix | `blueprint/design.md` Host Capability Governance 节下新增 | 含接续/授权/checkpoint 三个子表 |
| Blast radius 审计结论 | `blueprint/design.md` 新增审计节 或 方案包 design.md | 视篇幅决定 |
| P4c boundary statement | `blueprint/tasks.md` P4c 段更新 | 补充验收前提 |

## 风险

| 风险 | 缓解 |
|------|------|
| "待裁定"项过多导致审计变成设计 | 严守裁定三档框架（required/optional/forbidden），基于场景分析，不做过度架构推导 |
| 审计结论和 P4c 验收条件冲突 | 审计先行，P4c 验收条件如有冲突则在 P4c 开包时修正 |
| gate_receipt 消费者投影差异导致讨论发散 | 限定为"payload_capable 是否有合法消费场景"的二元裁定，不重新定义 gate_receipt 的 keep-list 角色 |
| blast radius 审计面太广 | 只审计 runtime/ 顶层模块，不递归子函数级别 |
