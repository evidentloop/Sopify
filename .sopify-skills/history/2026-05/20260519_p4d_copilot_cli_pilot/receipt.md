# Receipt: P4d Copilot CLI 新宿主试点

outcome: passed
date: 2026-05-19

## Summary

GitHub Copilot CLI 作为首个 `payload_capable + CONTINUATION` 宿主试点通过。Copilot 不接 runtime、不接 installer mainline，仅通过 repo-local prompt 资产 (`Copilot/Skills/CN/COPILOT.md`) 消费冻结 contract 文件，验证了跨宿主接续消费链路的可行性。实证支撑蓝图 design.md:573 "官方最低新宿主画像 = payload_capable + CONTINUATION"。

## 核心结论

### 1. P4d 通过条件已满足

| 条件 | 状态 | 证据 |
|------|------|------|
| Copilot/Skills/CN/ 资产存在 | ✅ | 252 行，从 AGENTS.md 裁剪 runtime 依赖 |
| S3 场景 1：消费 `required_host_action` + `artifacts` + plan/run 接续复述 | ✅ | 独立会话验证，正确复述活跃 plan / design 阶段 / S1 完成 / confirm_decision 3 选项 |

### 2. Copilot 实际画像

**声明梯度**：`payload_capable + CONTINUATION`

**实证能力**：

| 能力 | 验证状态 | 说明 |
|------|---------|------|
| CONTINUATION 消费 | ✅ 已验证 | 读 handoff → 正确按 required_host_action 接续 |
| INTERACTION 倾向 | ✅ 有正面信号 | S3 场景 2 识别 pending decision + 展示 question/options/recommended |
| AUDIT 倾向 | ✅ 有正面信号 | S3 场景 3 读 gate_receipt 作审计历史 + 正确标注"非当前授权" |
| 入口语义 | ✅ 已验证 | Inspect / Continue / Start New 三路径 + ~go exec 正确拒绝 |
| runtime-only 边界 | ✅ 有效 | `~go exec design` 被识别为 runtime 专属指令并拒绝 |

> INTERACTION/AUDIT 目前为"有正面信号"而非"已声明增强"。若需正式声明，应在 adapter metadata 中追加（P5 scope）。

### 3. `~go exec` 被正确拒绝

Copilot 在收到 `~go exec design` 时明确回复："runtime 专属指令，payload_capable + CONTINUATION 宿主不处理此语法"。证明 prompt 资产中 runtime-only 边界的裁剪是有效的，不会导致宿主误入 runtime 路径。

### 4. 接入成本

| 项目 | 成本 |
|------|------|
| Prompt 资产 | 1 文件 252 行（从 373 行 AGENTS.md 裁剪） |
| Installer adapter | 不需要（repo-local 资产直接可用） |
| Runtime 依赖 | 零 |
| State 文件 | 只读消费，不写入 |
| 新代码 | 无 runtime/product code 变更（纯 prompt 工程 + plan/blueprint 文档同步） |

> **产品口径**：Copilot 已验证接续消费能力（verified pilot），不等于已完成对外安装支持（production onboarding）。当前为 repo-local 手工接入，非正式安装路径。

## Key Decisions

### D1: Handoff Writer 定位

Shadow experiment（S3.5）作为隔离试验，不进默认产品面。不写 canonical `current_handoff.json`。S3.5 暂未执行，不影响 P4d 主结论。

### D2: Runtime 渐进替代路径

Working hypothesis。P4d 只提供证据，不执行迁移。P5 基于 S3.5 gap analysis（若完成）评估。

### D3: Installer Adapter 延迟

P4d 不创建 `installer/hosts/copilot.py`。原因：
- `HostAdapter` 抽象（header + destination_root + skills/sopify）与 Copilot repo-local payload-only 模型不匹配
- `SupportTier` 枚举无 `payload_capable` 值
- 强行适配 = 假 adapter 或 scope 膨胀
- P5 条件：验证通过 + 社区需求 → 评估 HostAdapter 抽象扩展

## Verification Evidence

| 场景 | 验证环境 | 结果 |
|------|---------|------|
| S3-1: Handoff 消费 + 接续复述 | Copilot CLI 独立会话 | ✅ 通过 |
| S3-2: Pending decision 识别与呈现 | Copilot CLI 独立会话 | ✅ 通过 |
| S3-3: Gate receipt 审计历史读取 | Copilot CLI 独立会话 | ✅ 通过 |
| S4-1: Inspect Active Work 路径 | Copilot CLI 独立会话 | ✅ 通过 |
| S4-2: Continue Active Work 路径 | Copilot CLI 独立会话 | ✅ 通过 |
| S4-3: Start New Work 仲裁 | Copilot CLI 独立会话 | ✅ 通过 |
| S4-4: ~go exec 不依赖 | Copilot CLI 独立会话 | ✅ 通过 |

## Fixture 说明

S3 验证使用 schema-aligned fixture（参照 `RuntimeHandoff` / `RunState` / `DecisionState` 模型字段构造，非 runtime 真实产出）：
- `current_handoff.json`：`confirm_decision` + decision_checkpoint 含 question/options/recommended_option_id
- `current_run.json`：active run → P4d plan, stage=design
- `current_decision.json`：pending decision（shadow writer scope）
- `current_gate_receipt.json`：gate_passed=true, `checkpoint_only`

fixture 口径：schema-aligned consumption smoke，非 strict bridge conformance proof。fixture 字段结构参照 runtime 模型，但由构造生成而非 runtime 真实写入。

## Limitations

- S3.5 Shadow Writer Experiment 未执行——不影响 P4d 主结论，但 P5 若需评估"handoff 生产层可拆"假设仍需补充
- Fixture 为构造数据（非真实 runtime 产出），验证的是"Copilot 能否正确消费 canonical schema"，非"端到端 runtime→Copilot 管道"
- INTERACTION/AUDIT 为正面信号，未升级为正式声明增强
- 未验证 Copilot 自动加载 `Copilot/Skills/CN/COPILOT.md` 的机制——当前验证需用户手动指引"先读 COPILOT.md"

## P5 输入

### 已证明不必依赖 runtime 的面

| 面 | 证据 |
|----|------|
| CONTINUATION 消费（handoff reading） | S3 三场景通过，纯文件消费 |
| INTERACTION 消费（decision/clarification reading） | S3 场景 2 通过 |
| AUDIT 消费（gate_receipt reading） | S3 场景 3 通过 |
| 入口语义（Inspect/Continue/Start New） | S4 四路径通过，基于 required_host_action 而非 route taxonomy |
| runtime-only 边界（~go exec 拒绝） | S4-4 通过 |

### P5 待评估项

| 项 | 说明 |
|----|------|
| Installer adapter 扩展 | HostAdapter 需支持 payload-only 模式（无 header、无 home_root） |
| SupportTier 枚举补齐 | 代码中无 `payload_capable` 值，需与蓝图术语对齐 |
| INTERACTION/AUDIT 正式声明 | 有正面信号但未在 adapter metadata 中声明 |
| Shadow writer gap analysis | S3.5 未执行，需评估 handoff 生产层拆分假设 |
| Copilot payload-only onboarding | P4d 用 repo-local pilot 验证，未解决任意外部项目的分发/初始化：(1) prompt asset 分发路径（不碰 .github/copilot-instructions.md）(2) 任意 repo 的 .sopify-skills/ workspace bootstrap (3) 不涉及 .sopify-runtime |

### Keep / Defer 裁定

| 产出物 | 建议 | 理由 |
|--------|------|------|
| `Copilot/Skills/CN/COPILOT.md` | **Keep** | 核心资产，S3/S4 验证通过 |
| S3 state fixtures | **Keep as test data** | 可复用于后续 smoke / regression |

> S2 installer adapter 和 S3.5 shadow writer 的延迟决策已记录在 tasks.md D3 和正文中，不重复列入 surface 裁定。

### Runtime Surface 证据汇总（P5 消费用）

| Runtime Surface | 是否已证明可脱 runtime | 证据来源 |
|----------------|----------------------|---------|
| Handoff 消费（reading frozen contract） | ✅ 已证明 | S3 三场景 |
| Decision/Clarification 消费 | ✅ 已证明 | S3 场景 2 |
| Gate receipt 消费（审计历史） | ✅ 已证明 | S3 场景 3 |
| 入口语义（Inspect/Continue/Start New） | ✅ 已证明 | S4 |
| Handoff 生产（writing canonical state） | ❓ 未验证 | S3.5 未执行 |
| Gate 授权（runtime gate enter） | ❌ 仍需 runtime | payload_capable 不走 gate |
| Route 路由（~go exec / route taxonomy） | ❌ 仍需 runtime | S4-4 正确拒绝 |
| Workspace bootstrap | ❓ 未验证 | P4d 不涉及 |

## Impact on Blueprint

- design.md:432 `payload_capable` 行 Copilot 列可标记为 "P4d verified"
- design.md:435 "qoder/copilot 等宿主合法停在中间层" 注释现在有实证支撑
- ADR-016 "Protocol-first / Runtime-optional" 获得第一个 payload_capable 宿主的实证
