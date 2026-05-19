# 蓝图架构与契约

本文定位: Sopify 的架构分层、核心契约、削减目标与硬约束。这是宿主与 runtime 的共同设计基线。

## 产品定位 (ADR-013)

Sopify 的 durable core 是跨宿主 AI 工作流的 **证据与授权层**。它不负责生成代码或编排 agent，而是把外部生产、验证、知识工具的结果收敛成可恢复、可审计、可授权的机器事实。Sopify 官方在 core 之上提供一个轻量、可插拔、收敛式的 workflow，并以 blueprint 作为默认的长期知识基线。

| 层级 | 表述 |
|------|------|
| 用户层 | 任务可恢复、决策可追踪、产出质量可验证，跨宿主无缝接力 |
| 产品层 | Core: 证据规范 + 授权判定 + 收据 + 接力 + archive truth；Default Workflow: 以 blueprint 为基线的收敛式工作流 |
| 架构层 | Evidence & authorization layer + official workflow anchored on blueprint as long-term knowledge baseline |

## 产品分层

| 产品层 | 职责 | 映射到实现 |
|-------|------|-----------|
| **Core** | 证据规范、授权判定、收据生成、handoff 接力、archive truth | Protocol + Validator |
| **Default Workflow** | 以 blueprint 为基线的分析、标准方案包生成、checkpoint 讨论（含跨宿主审查）、归档回写 | Protocol conventions + Validator policies + 可选 Runtime 编排 |
| **Plugins / Skills** | 外部能力接入，分三类（见下方） | Integration Contract (protocol.md §6) + Validator admission |

**层间规则：**

- **Core promotion rule**：只有影响跨宿主互操作、receipt validity、archive admissibility 的契约才能进 Core
- **Default Workflow 边界**：消费 Core 契约，不自行定义授权语义；是 Core 之上的 opinionated happy path
- **Plugin trust rule**：插件输出进入 receipt/handoff/blueprint 前，必须经过 Validator 或 knowledge_sync admission gate

**Plugin 三分类：**

| 类型 | 职责 | 典型实例 | 输出流向 |
|------|------|---------|---------|
| **Verifier** | 独立验证生产结果，输出 verdict + evidence | cross-review | receipt 风险因子（advisory，不自授权） |
| **Deterministic Checker** | 确定性规则检查（lint / test / schema） | CI gate adapter（未实现） | 证据链 / handoff evidence |
| **Knowledge Provider** | 提供外部知识输入 | graphify | blueprint / plan context |

**对外承诺分层（Now / Emerging / Future）：**

| 层级 | 能力 | 当前状态 |
|------|------|---------|
| **Now** | 跨宿主可恢复状态（Convention + Runtime） | ✅ Codex / Claude deep verified |
| **Now** | fail-closed 授权收据（ExecutionAuthorizationReceipt） | ✅ P1.5 已交付 |
| **Now** | blueprint-driven 知识沉淀 | ✅ 已交付 |
| **Emerging** | 隔离独立审查（cross-review skill） | Advisory only；不自动阻断 |
| **Emerging** | Convention-first 外部宿主接入 | Protocol spec v0 已落地；缺少面向外部宿主的 quickstart |
| **Future** | 硅基↔硅基信任协议（跨 agent 授权） | 概念定义阶段 |
| **Future** | Plugin admission + Verifier evidence 标准化 | 设计阶段 |

**协作模式定位：** 当前主战场是碳基↔硅基（人与 AI）。硅基↔硅基仍属战略预留，现阶段仅有 advisory cross-review 作为早期验证形态。碳基↔碳基主要体现为 blueprint / history 共享带来的兼容收益，不是独立产品面。

**竞品边界：**

| 类别 | 代表产品 | Sopify 的边界 |
|------|---------|-------------|
| 宿主 / IDE（内建工作流状态） | Kiro (AWS)、Claude Code、Codex、Cursor | Sopify 不做模型推理、不做代码执行；宿主原生 spec/checkpoint 是最大吸收风险 |
| Spec / artifact 系统 | OpenSpec (Fission-AI)、Spec Kit (GitHub) | Sopify 不做 spec 方法论、不做 artifact 模板管理；与 spec 系统可互补 |
| Agent runtime / platform | OpenClaw、Hermes Agent | Sopify 不做 agent orchestration、不做 skill routing/gateway；runtime 层有重叠需关注 |
| Skills / methodology 生态 | Superpowers | Sopify 不做技能市场、不做方法论教学；Superpowers 是 agentic skills + methodology |

**Sopify 的不可替代面**：不在于某一项功能，而在于 **可验证的便携式证据与授权语义**——fail-closed 授权回执、跨宿主可恢复状态、可审计项目记忆、独立 validator/compliance 套件。这些能力的组合是单一宿主难以完整替代的。

**竞品吸收应对策略：**

- 宿主吸收执行编排 → Sopify 退守 protocol + validator + compliance
- Spec 工具吸收 checkpoint → Sopify 强调跨宿主连续性 + receipt authority
- Agent 框架吸收 state → Sopify 做 interop 标准层 / 可携带协议

**生存性测试：** 2027 年宿主原生支持 plan/checkpoint/multi-agent 后，Sopify 仍必须保留：项目级资产沉淀、跨宿主连续工作、可审计决策链、独立质量闭环。如果以上任一能力被宿主完全替代且无跨宿主可携带性需求，该能力应 sunset。

## 底层哲学

> 以下 3 条哲学是 ADR-013/016/017 的共同根基。所有设计决策可从中推导。

### 哲学 1: Convergence-first (收敛优先)

**微观（单任务）是收敛链**：produce → verify → authorize → settle。目标是按风险逐步降低不确定性，收敛到"可授权阈值"即停止——不以"更完整/更优雅"为默认继续条件。

- produce: 外部生产器（LLM/宿主）输出候选事实
- verify: 外部验证器（cross-review 等）提供独立证据
- authorize: Sopify Validator 判定是否可执行/可归档
- settle: 沉淀为 receipt / handoff / history

**宏观（跨任务）是知识飞轮**：每次 settle 沉淀的 machine truth 提高下一条收敛链的起点，降低验证成本并缩短授权路径。

**停点原则**：达到可授权阈值后即停止。不是每个任务都需要完整的设计 + 交叉审查 + 知识提炼全套流程；按风险选择验证深度。

**沉淀准入门槛**：只有同时满足以下条件的结论才进入长期知识层（blueprint / history）：
- 跨任务可复用
- 影响未来授权或验证基线
- 已经稳定
- 可 machine-readably 引用

**方案级收敛（Default Workflow 策略）**：收敛链不仅适用于单任务执行，也适用于方案讨论阶段。跨宿主审查遵循收敛链语义：

- 方案状态流转：`draft → under_review → [accept → approved | revise → draft | blocked → escalate]`
- 停点条件：至少一轮审查无阻塞性 finding 且返回 accept；或用户显式 override；或审查轮数达到上限（默认 3 轮）
- 多审查者冲突：有任一 `blocked` 则整体 blocked；`accept` + `revise` 混合时取 revise
- 机器契约：subject identity 见 `protocol.md §7`；verdict shape 见 `protocol.md §6`。策略性规则（轮数上限、severity 判定）归 Default Workflow，不进 Core

### 哲学 2: Wire-composable (线可组合)

独立收敛链通过**线**（机器契约）组合。Sopify 是串联收敛链的证据与授权线——负责证据规范、授权判定和收据生成，不做生产/验证/知识处理节点本身。

线独立于 session / model / host：同一逻辑 session（`session_id`）内，handoff + run state 让中断后精确继续；跨 session 接力需显式 claim/receipt，不允许静默推进旧 session 的 pending checkpoint。

| 显隐 | 实现 | 适用 |
|------|------|------|
| 显式 (Runtime) | gate → handoff → checkpoint JSON | 确定性门控 / 审计 |
| 隐式 (Convention) | SKILL.md + 目录约定 | 轻量任务 / 新宿主 |

外部能力通过 integration contract 接入（见 `protocol.md` Integration Contract 小节）。

### 哲学 3: Surface-shared (面共享)

所有线共享一个知识面（blueprint / history）。知识面是跨 session/model/host 的共享工作记忆。

在多模型、多云、多宿主逐步解耦的环境下，Surface-shared 的目标是让项目连续性绑定到共享文件协议，而不是绑定到某个模型、云或聊天上下文。任意 host/model 只要正确消费 blueprint/history 与 handoff 暴露的机器事实，就能基于同一项目记忆继续工作；但推进 pending checkpoint 或产生副作用仍必须回到 Wire-composable 的机器接力与 Validator 授权。

**Sopify 的不可替代性 = 线 + 面的组合。** Protocol 定义证据规范，Validator 定义授权判定，Runtime 是可选的"加固线"。

## 三层定位 (ADR-016: Protocol-first / Runtime-optional)

> **迁移现状（2026-05）**：Protocol-first 是已确认的架构方向。`blueprint/protocol.md` v0 已落地，定义了不依赖 runtime 也成立的最小可携带协议。当前 runtime（~29K 行 / 66 模块）仍是最完整的参考实现，protocol.md 是协议层的规范起点。
>
> **Blueprint Truth Cutover 原则**：Blueprint 是产品合法边界和预算的唯一定义源。Runtime 定义 how it currently runs，blueprint 定义 what is valid。当 runtime 与 blueprint 冲突时，以 blueprint 为准——runtime 中超出 canonical 预算的面是待迁移的遗留面，不是产品真相。Runtime 在架构上是参考实现和迁移层，不是 truth source。当前产品尚处于早期阶段，无外部消费者依赖和生产级兼容承诺，处于可激进收敛的窗口期。
>
> **协议规范**：`blueprint/protocol.md` 定义最小可携带协议（目录结构、必备文件/字段、宿主最小义务、生命周期样例）。本节定义三层架构分工，protocol.md 定义最小合规下界。

| 层 | 内容 | 体量目标 | 可替代性 |
|----|------|---------|---------|
| **Protocol** | `.sopify-skills/` 目录约定、schema、SKILL.md 编排 | 纯文档 | 不可替代 |
| **Validator** | ActionProposal 校验、状态迁移校验、archive check/apply | ~2K 行 | 独立交付 |
| **Runtime** | gate / router / engine / handoff 状态机 | 当前 ~26K 行；减重目标 P4b | 可选增强 / 参考实现 |

**Convention 模式 (下界)**: LLM 读 SKILL.md → 自行推进 → Validator 事后校验（protocol acceptance / receipt authority）。
**Runtime 模式 (上界)**: 完整 runtime 控制状态迁移，Validator 是 pre-write authorizer。

"Validator 是唯一授权者"在两种模式下含义不同：Runtime 模式是写前授权；Convention 模式是事后合规校验与 receipt 签发。两者共享同一校验逻辑，但触发时机和阻断语义不同。

模式选择维度是**过程要求**，不是模型强弱。

## 核心管线 (ADR-017: Action/Effect Boundary)

```
用户自然语言
  → Host LLM 映射为 ActionProposal
  → Validator 校验 schema + facts + side effect → ValidationDecision
  → Deterministic action 执行
  → Handoff / Receipt 暴露机器事实
```

**不变量：**

- Host LLM 只是 proposal source，**不是 authorizer**
- Validator 是**唯一授权者**：判断当前 context 下 action/side effect 是否允许
- Validator **不是 executor**：不做 plan materialization、文件迁移、状态推进
- 执行层**不理解人话**：只按结构化字段和文件事实做事
- `fallback_router` 只是临时兼容出口，应单调收缩

### Subject Identity（主体身份）

ActionProposal 管线中，每个 bound-subject side-effecting action 必须携带明确的 subject identity——"操作的是谁"。Subject identity 是 protocol 层契约，validator 和 runtime 都是消费方。Subject-free actions（`consult_readonly`、`propose_plan`）不要求主体。

- `subject_type`：被操作对象类型（`plan` 为 normative；`code` / `architecture` 保留 draft）
- `subject_ref`：对象定位，workspace-relative 路径（如 `.sopify-skills/plan/20260501_dark_mode`）
- `revision_digest`：版本标识（目标对象的 SHA-256 hex digest），保证操作绑定到确定性快照

主体取证优先级：explicit reference → self-reference → new-plan intent → stable handoff evidence → current-plan anchor。

> **规范来源**：`protocol.md` §7 定义 wire contract（P1 升格为 normative；P2 扩展到所有 bound-subject actions）。Bound-subject actions 的 subject binding 通过 `plan_subject` 字段块进入 ActionProposal。Action 与 subject 字段的完整适用关系见 `protocol.md` §7 Action Applicability Matrix。

### ExecutionAuthorizationReceipt（授权脊柱）

执行授权不再是 checkpoint，而是机器授权事实。这是 subject identity 绑定后的直系产物——先确定"操作的是谁"，再回答"这次操作是否被授权"。

**不变量：** 绑定 plan identity + plan revision + execution gate result + action proposal identity + authorization source。使用 canonical JSON + sha256 生成 fingerprint。Plan 变更后 receipt 自动失效。Fail-closed：任一字段不匹配则拒绝执行。

具体字段定义见 ADR-017。操作化路线见 `tasks.md` P1.5。

### side_effect_delta（结构化变更清单）

ActionProposal 的标量 `side_effect` 字段表达粗粒度权限层级（`none|write_runtime_state|write_plan_package|write_files|execute_command`），不描述具体变更内容。`side_effect_delta` 是并行存在的可选字段，提供 file-level 结构化变更清单：

```json
{
  "side_effect_delta": [
    {"path": "src/auth.py", "change_type": "modified"},
    {"path": "src/new_module.py", "change_type": "added"},
    {"path": "tests/old_test.py", "change_type": "removed"}
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `path` | string | workspace-relative 文件路径 |
| `change_type` | enum | `added` \| `modified` \| `removed` |

**与标量 side_effect 的关系**：标量不替换、不废弃。两者并行——标量回答"我可以写什么类别？"，delta 回答"我具体要改哪些文件？"。

**P2 scope**：第一版仅 `modify_files` 消费 `side_effect_delta`。其他 action_type（含 `execute_existing_plan`）的 delta 支持为 future hook，蓝图留口但不进 P2 runtime acceptance。缺失 delta 等同 legacy 行为，validator 不 REJECT。

**Validator 消费**：Workspace scoping — delta 路径 MUST 为 workspace-relative（无绝对路径、无 `..` 穿越）。不做 plan-scope 判定（无稳定的 plan scope 机器定义）。

**设计影响来源**：OpenSpec ADDED/MODIFIED/REMOVED delta 语义（T1 Adoption，准入 delta 枚举，不准入 specs/changes 工作区模型）。

### Action-Effect Canonical Pairing（admission 闭合）

每个 action_type 有且仅有一个合法的 side_effect。Validator 在 subject/delta check 之后、evidence check 之前做 pairing 校验，不匹配 → DECISION_REJECT（fail-close，不 downgrade consult）。完整 pairing 表见 `protocol.md` §7 Action Applicability Matrix 的 `canonical side_effect` 列。

**设计理据**：action_type 表达意图语义，side_effect 表达权限层级。1:1 pairing 防止 action_type 退化成标签而真正权限语义漂在 side_effect 上。不引入新常量类型或 schema 字段——只是一个 dict 常量 + validator 函数。

**P2 scope 边界**：P2 做的是 admission contract 闭合（哪些 action+effect 组合合法）。Execution routing 收敛（Validator 授权后直接走确定性执行，不再经 Router）属于 P3a。

## Runtime 五层架构（参考实现）

> 以下五层是当前 Python runtime 的参考实现架构。Protocol 本体（目录约定、schema、Validator 契约）不依赖此五层也成立。宿主可通过 Convention 模式直接消费 Protocol + Validator，不必实现完整 runtime。

### 1. Ingress Layer | 入口守卫层

回答：当前请求能不能进入 runtime、带什么最小上下文进入。不负责路由或意图解释。

### 2. State Resolution Layer | 状态真相层

收敛"现在该信哪份状态"。Loader + Resolver 生成唯一 `ContextResolvedSnapshot`，下游只消费 snapshot，不散读 JSON。

### 3. Routing & Checkpoint Layer | 路由与停点层

基于 snapshot 决定：直接执行还是进入 checkpoint。只有两种 checkpoint 是真正的协作分叉：

- **clarification**：补事实
- **decision**：拍板选路

### 4. Execution & Handoff Layer | 执行交接层

执行当前动作，结果写入 `current_handoff.json`。宿主后续该做什么以 handoff 为准。

### 5. Knowledge Lifecycle Layer | 知识生命周期层

渐进式物化：bootstrap 建最小骨架 → 方案流补齐 blueprint → archive 后归档到 history。

## 削减目标

### 目标词汇表

以下是 canonical 目标。当前存在的非 canonical 词汇标为 legacy/compat，需带 sunset 条件，不得被 blueprint 重新合法化。

#### Checkpoint Types (target: 2)

| Canonical | 语义 |
|-----------|------|
| `clarification` | 补事实（真协作分叉） |
| `decision` | 拍板选路（真协作分叉） |

**已重分类（不再是 checkpoint type）：**

| 旧类型 | 新定位 | 说明 |
|--------|--------|------|
| `plan_proposal` | ~~propose_plan 的 pending artifact~~ | **Wave 3a 已 hard-cut 删除** |
| `execution_confirm` | ExecutionAuthorizationReceipt | 机器授权事实，不是协作分叉 |
| `develop_checkpoint` | develop callback source | 可触发 clarification 或 decision，不是独立 checkpoint type |

#### required_host_action (target: 5)

| Canonical | 语义 |
|-----------|------|
| `answer_questions` | 宿主展示缺失事实，等待用户补充 |
| `confirm_decision` | 宿主展示设计分叉，等待用户选择 |
| `continue_host_consult` | 宿主继续问答 |
| `continue_host_develop` | 宿主继续代码修改（develop_mode 为 hint：quick_fix/standard） |
| `resolve_state_conflict` | 状态冲突，需宿主介入 |

**Sunset（不计入 canonical budget）：**

| Legacy action | 目标归宿 | Sunset 条件 | 替代 contract | 清理里程碑 |
|---------------|----------|------------|-------------|-----------|
| `confirm_plan_package` | — | — | — | ✅ 已完成（Wave 3a） |
| `confirm_execute` | ExecutionAuthorizationReceipt | receipt 替代 checkpoint | P1.5 authorization contract spec | P3a 复核（runtime 已清，tests/contracts 残留待确认） |
| `review_or_execute_plan` | ActionProposal routing | Validator 接管 plan review/execute 语义；plan review 状态改由 `continue_host_develop` + `plan_generated` stage 表达 | P2 local action contracts | ✅ 已完成（P3a） |
| `continue_host_quick_fix` | `continue_host_develop(mode=quick_fix)` | 合并为 hint | P2 local action contracts | P3a 复核（runtime 已清） |
| `continue_host_workflow` | `continue_host_develop(mode=standard)` | 合并 | P2 local action contracts | P3a 复核（runtime 已清） |
| `archive_completed` | — | — | — | ✅ 已完成（archive lifecycle cutover） |
| `archive_review` | — | — | — | ✅ 已完成（archive lifecycle cutover） |
| `host_replay_bridge_required` | — | — | — | ✅ 已完成（runtime 无活跃引用） |

> **P2 → P3a 衔接说明（P2 追记）**：P2 已落地替代 contract——bound-subject local actions 的 plan_subject binding + Action Applicability Matrix + side_effect_delta schema（见 `protocol.md` §7、本文 side_effect_delta 段落）。上述 3 项 legacy action 的替代 contract 条件已满足。P3a 执行实际清理时，以 P2 定义的 Action Applicability Matrix 为准入基线，删除对应 legacy surface。

#### Route Families (target: 6)

| Canonical | 覆盖 route_name（runtime 实际值） |
|-----------|-------------------------------|
| `plan` | `plan_only`, `workflow`, `light_iterate` |
| `develop` | `exec_plan`, `resume_active`, `quick_fix` |
| `consult` | `consult` |
| `archive` | `archive_lifecycle` |
| `clarification` | `clarification_pending`, `clarification_resume` |
| `decision` | `decision_pending`, `decision_resume` |

#### Non-family Surfaces

以下 route 不计入 6 family 预算。总条件：它不是 resumable 的 host-facing workflow continuation。然后必须属于以下之一：

1. **跨路由错误面** — 任何 route 内均可触发的横切 error handling
2. **显式 control/teardown 命令** — 不产出 handoff、不参与工作流推进
3. **显式 read-only utility 命令** — 不影响工作流状态的只读渲染

| route_name | 分类 | 说明 |
|------------|------|------|
| `state_conflict` | 跨路由错误面 | state-resolution error surface |
| `proposal_rejected` | 跨路由错误面 | Validator DECISION_REJECT 独立 surface |
| `cancel_active` | control/teardown | 清空 active flow，不产出 handoff |

新增 non-family surface 必须显式修改本段落，默认不允许扩口。non-family surface 如果不再被 runtime 主链路引用，应直接删除而非保留为 legacy。

#### Core State Files (target: 6, authoritative)

| File | 职责 |
|------|------|
| `current_run.json` | 当前运行态 |
| `current_plan.json` | 活动 plan 绑定 |
| `current_handoff.json` | 执行交接 |
| `current_clarification.json` | clarification checkpoint |
| `current_decision.json` | decision checkpoint |
| `current_archive_receipt.json` | archive 可审计 receipt（不是 host action） |

**Fold/remove：** ~~`current_plan_proposal.json`~~ — **Wave 3a 已删除，未新建替代文件。`context_snapshot.current_plan_proposal` 字段保留为 `None`（反序列化兼容）。**

**Derived/compat（不计入 core budget）：** `last_route.json` — 后续证明可从 handoff/run 派生后移除。

**Ingress scope（不算 review state）：** `current_gate_receipt.json`

### 削减预算表

| 维度 | 当前 | Target | Hard Max | 计算口径 |
|------|-----:|-------:|---------:|---------|
| Checkpoint types | 5 | 2 | 2 | canonical only |
| required_host_action | 13 | 5 | 6 | canonical; compat/derived 不计 |
| Route families | 18 | 6 | 8 | canonical; migration alias 不计 |
| Core state files | 8 | 6 | 7 | authoritative only; derived/compat 不计 |

**Hard max 例外路径：** 只能通过 ADR 更新。必须说明替代了什么旧概念、为什么不能放到 artifacts/status/hint 里。

> **削减前提**：Runtime 减重目标 P4b，但 P4b 执行以 P4a 外部消费面 keep-list 冻结为硬前提。P4b 执行顺序固定为：release gate 收口 → runtime 旧面删除 → implementation-mirror tests 收口（详见 `tasks.md` P4b）。先 formalize contract，再清 runtime 旧面。不以 runtime 内部治理为驱动独立清理。


## Persistence Surface 分层

| 层级 | 物理对应 | Git 状态 | 消费者 | 可删性 |
|------|---------|---------|--------|--------|
| **长期知识** | blueprint/ plan/ history/ project.md | tracked | 人 + 宿主 + runtime | 不可删 |
| **长期知识 / 偏好审计** | user/preferences.md · user/feedback.jsonl | tracked | 人 + runtime | 不可删 |
| **主链机器真相** | state/current_run · current_plan · current_handoff · current_clarification · current_decision | gitignored | runtime gate/router + 宿主 handoff | 运行期不可删 |
| **可审计凭证** | state/current_gate_receipt · current_archive_receipt | gitignored | 诊断 / 审计 | 运行期不可删，非主链依赖 |
| **运行态附属 / 可删派生** | state/sessions/* · last_route | gitignored | runtime 内部 | 无活动 session / 超租约后可清理 |

> replay/ 已在 P3b 列为能力下线（tasks.md P3b），不再列入 persistence surface。


## 外部消费面 Keep-list

P4b 减重和 P4c 宿主消费治理的红线边界。只冻结 artifact / schema / host-visible contract，不冻结 Python 内部 API、route 枚举、输出文案措辞。未列入本表的面默认为 runtime 内部实现，P4b 可删。

| surface | kind | consumer | freeze_level | why_kept | non-goals / not frozen |
|---------|------|----------|-------------|----------|----------------------|
| protocol.md §6 Verifier: `verdict`, `evidence`, `source` | doc_contract | host / external_tool | semantics | 跨宿主验证结果的标准格式；宿主消费 verdict 做风险判断 | `scope`（SHOULD，非 MUST）；verifier 内部实现方式 |
| protocol.md §6 ExecutionAuthorizationReceipt: `plan_id`, `plan_path`, `plan_revision_digest`, `gate_status`, `action_proposal_id`, `authorization_source`, `fingerprint`, `authorized_at` | doc_contract | host / external_tool | semantics | fail-closed 授权回执；跨宿主可恢复的授权证明 | receipt 内部生成方式；fingerprint 算法（可演进） |
| protocol.md §7 Subject Identity: `subject_type`, `subject_ref`, `revision_digest` | doc_contract | host / external_tool | semantics | 操作主体绑定；admission fail-closed 的前提 | subject resolution 的 runtime 实现方式 |
| protocol.md §7 plan_subject block: `subject_ref`, `revision_digest` | doc_contract | host | semantics | bound-subject 操作的必要条件 | action applicability matrix 的具体枚举值（实现细节） |
| `current_gate_receipt.json` top-level: `schema_version`, `status`, `gate_passed`, `workspace_root`, `session_id`, `preflight`, `preferences`, `runtime`, `handoff`, `state`, `trigger_evidence`, `observability`, `allowed_response_mode`, `evidence`, `action_proposal_schema` | gate_contract | host / external_tool | schema | gate 入口判定的完整凭证；诊断/审计依赖；`action_proposal_schema` 在 action_proposal_retry 模式下为当前回合必须消费的 gate contract | receipt 内部子字段结构（observability payload 可演进）；`receipt_path`/`receipt_write_error` 为条件性写入，不冻 |
| `current_handoff.json` top-level: `schema_version`, `route_name`, `run_id`, `plan_id`, `plan_path`, `handoff_kind`, `required_host_action`, `recommended_skill_ids`, `artifacts`, `notes`, `observability`, `resolution_id` | machine_truth | host | schema | 宿主消费 handoff 做执行交接；跨宿主恢复的核心数据 | 内部组装方式（Python to_dict/from_dict）；observability 子字段可演进 |
| Archive truth — ArchiveCheckResult: `status`, `subject`, `notes`, `knowledge_sync_result` | machine_truth | host | schema | archive 前检查结果；宿主据此决定是否归档 | Python dataclass 名称和内部方法 |
| Archive truth — ArchiveApplyResult: `status`, `subject`, `archived_plan`, `kb_artifact`, `notes`, `registry_updated`, `state_cleared`, `knowledge_sync_result` | machine_truth | host | schema | archive 执行结果的完整凭证 | Python dataclass 名称和内部方法 |
| `install.sh` / `install.ps1` user params: `--target`, `--ref`, `--workspace`, `-h` | install_contract | user | existence | 用户安装入口的稳定参数 | 内部转发参数（`--source-channel`, `--source-resolved-ref`, `--source-asset-name`）；`SOURCE_CHANNEL`/`SOURCE_REF` 为 distribution metadata，非用户面稳定接口，默认值可变；freeze 口径以用户入口 contract 为主 |
| `builtin_catalog.generated.json` file-level: `schema_version`, `generated_at`, `source`, `skills`; per-skill: `id`, `names`, `descriptions`, `mode`, `entry_kind`, `handoff_kind`, `contract_version`, `supports_routes`, `triggers`, `metadata`, `tools`, `disallowed_tools`, `allowed_paths`, `requires_network`, `host_support`, `permission_mode`, `runtime_entry` | machine_truth | host | schema | 宿主消费 skill 清单做能力发现和 prompt 注入 | 具体 skill 枚举（能力上下线属内容变更，不违反 freeze）；Python API 签名（`load_builtin_skills()`） |
| `evals/skill_eval_slo.json` + `evals/skill_eval_baseline.json` | gate_contract | external_tool | existence | 发布门禁的存在性和最小语义（SLO 定义 pass/fail） | 具体维度 taxonomy（selection/discovery/navigation 可演进）；具体分数阈值（可调） |
| Persistence: `blueprint/` `plan/` `history/` `project.md` | persistence_red_line | user / host | existence | 长期知识；人 + 宿主 + runtime 共同消费 | 目录内部文件结构（可增删文件） |
| Persistence: `user/preferences.md` · `user/feedback.jsonl` | persistence_red_line | user / host | existence | 偏好审计；tracked 不可删 | 文件内部格式可演进 |
| Persistence: `state/current_run` · `current_plan` · `current_handoff` · `current_clarification` · `current_decision` | persistence_red_line | host | existence | 主链机器真相；运行期不可删 | 具体 JSON 内部子字段结构（由上方 schema freeze 覆盖） |
| Persistence: `state/current_gate_receipt` · `current_archive_receipt` | persistence_red_line | external_tool | existence | 可审计凭证；运行期不可删 | 非主链依赖；诊断用途 |

> **未列入面默认可删**：`state/sessions/*`、`state/last_route.json`、runtime 内部模块边界、route name 全集、output 渲染文案措辞均为 runtime 内部实现，不在 keep-list 内。P4b 减重时可自由处置。


## Output Rendering Audit

output.py 渲染层逐字段分类。只做分类，不做改造决策（改造属 P4c）。

| field / section | source | classification | note |
|----------------|--------|---------------|------|
| Title: `[brand] phase status_symbol` | derived（route_name → phase label 映射） | human_hint | phase label 和 ✓/?/! 均为人类可读提示，不是 machine truth |
| `Plan: <path>` / `Current Plan: <path>` | plan_artifact.path / current_plan.path | machine_truth_projection | resume_active/exec_plan 路径渲染 Current Plan，其余路径渲染 Plan |
| `Summary: <summary>` | plan_artifact.summary / clarification.summary | machine_truth_projection | |
| `Stage: <stage>` | current_run.stage | machine_truth_projection | |
| `Gate: gate_status / blocking_reason / plan_completion` | current_run.execution_gate 或 handoff.artifacts | internal_taxonomy_leak | 三元组直接暴露 runtime 内部 gate 状态机；默认输出中不应前置 |
| `Handoff: <path>` | handoff 文件路径 | machine_truth_projection | |
| `Status: <message>` | derived（route_name + gate_status + handoff） | human_hint | 消息模板由 route_name 和 required_host_action 推导 |
| `Priority note` | result.notes（plan_registry 事件） | human_hint | |
| `Missing Facts: <facts>` | current_clarification.missing_facts | machine_truth_projection | |
| `Questions: <questions>` | current_clarification.questions | machine_truth_projection | |
| `Question: <question>` + `Options: <options>` | current_decision | machine_truth_projection | |
| `Decision Status: awaiting confirmation` | derived（recommended_option_id） | human_hint | |
| `Conflict Code: <code>` + `Reason: <message>` | state_conflict payload | machine_truth_projection | |
| `Quarantined: <count>` | quarantined_items | machine_truth_projection | |
| `Entry Guard Reason: <code>` | handoff.artifacts.entry_guard_reason_code | internal_taxonomy_leak | runtime 内部守卫码，非宿主需消费的 contract |
| `Archive: <path>` + archive status | plan_artifact / archive result | machine_truth_projection | |
| `Route: <route_name>` | result.route.route_name | internal_taxonomy_leak | 仅在 cancel_active 和 fallback 路径直接暴露内部 route 名 |
| `Reason: <reason>` | result.notes / route.reason / route_name（fallback） | mixed（machine_truth_projection + internal） | fallback 到 route_name 时属于 internal taxonomy leak |
| `Changes: N files` + file list | kb_artifact.files + plan_artifact.files + loaded_files + generated_files + state paths | mixed（machine_truth_projection + internal） | 混合了实际写入文件和恢复上下文加载文件（loaded_files）；loaded 不是 Changed |
| `Next: <hint>` | derived（required_host_action + route_name + handoff_kind） | human_hint | 推导逻辑混合了内部 route_name 和 handoff contract 字段 |

**已知热点汇总**：
- **Gate 三元组 leak**：`gate_status / blocking_reason / plan_completion` 直接渲染 runtime 内部 gate 状态机到默认输出
- **Changes 混层**：`loaded_files`（恢复上下文）与实际写入文件混在同一个 Changes 区块
- **Next 推导**：human hint 但内部依赖 route_name + required_host_action 交叉推导，逻辑复杂
- **Route 名泄露**：cancel_active 和 fallback 路径直接渲染 route_name
- **Entry Guard Reason**：内部守卫码不应在默认输出中暴露


## 宿主能力治理

定义 canonical 能力梯度（产品真相），将现有 SupportTier 降为 legacy projection。

> 蓝图总纲：Protocol-first / Validator-centered / Runtime-optional。
> 能力梯度的判定标准是"能消费哪些 contract"，不是"有没有某个安装动作"。

### 能力梯度


| 梯度 | 含义 | 进入条件（contract 准入） | SupportTier 映射（legacy） |
|------|------|--------------------------|--------------------------|
| `convention_only` | 只支持 Convention 协议；无 payload、无 runtime | 能消费 protocol.md §1–§5；有 .sopify-skills/ 目录结构；遵守 repo-local 优先级；能消费宿主侧 skill/prompt disclosure surface（不把未冻结 workspace 路径当作协议前提） | 无直接对应；当前 DOCUMENTED_ONLY 或 EXPERIMENTAL 可作为临时映射 |
| `payload_capable` | 支持 payload 安装；能消费 prompt asset | convention_only 全部条件 + payload 落点 + prompt asset 消费。workspace bootstrap 和 handoff contract 消费为可选增强项，不阻断进入此级别 | BASELINE_SUPPORTED 可作为临时映射 |
| `deep_verified` | 完整深适配；installer + runtime + smoke | payload_capable 全部条件 + workspace bootstrap + handoff contract 消费 + host adapter + smoke 验证 | DEEP_VERIFIED（codex, claude） |

> **payload_capable 关于 workspace bootstrap 和 handoff 的定位**：这两项是可选增强项（opt-in），不是准入门槛。这允许 qoder/copilot 等宿主合法停在中间层——支持 payload 安装但不要求完整 runtime 深适配——而不是被迫二选一（纯文档 or deep adapter）。

> **宿主验证状态**：
> | 宿主 | 梯度 | 增强 | runtime | installer | 验证 |
> |------|------|------|---------|-----------|------|
> | Codex | `deep_verified` | CONTINUATION + INTERACTION + AUDIT | ✅ | ✅ | 已验证 |
> | Claude | `deep_verified` | CONTINUATION + INTERACTION + AUDIT | ✅ | ✅ | 已验证 |
> | Copilot CLI | `payload_capable` | CONTINUATION: verified; INTERACTION/AUDIT: positive signal | ❌ 不需要 | ❌ 不接入 mainline | P4d verified pilot（repo-local 手工接入，非正式安装支持） |

> **SupportTier 映射说明**：上表第 4 列为 prose-level 映射。具体 FeatureId 组合到梯度的可执行投影规则属 P4c 实施范围，本 bridge 不预定义。P4c 消费本表时需补充机器可检查的投影矩阵。


### 接入判定

新宿主接入时需回答：

Convention 层（convention_only 准入）：
- 是否支持 Convention 协议（.sopify-skills/ 目录结构 + plan lifecycle）
- 是否遵守 repo-local 优先级（workspace 配置优先于全局配置）
- 是否能消费宿主侧 skill/prompt disclosure surface（不把未冻结 workspace 路径当作协议前提）

Payload 层（payload_capable 准入）：
- 是否支持 payload 安装（prompt asset 落点 + payload bundle）
- 是否支持 workspace bootstrap（KB init）— 可选增强
- 是否能消费 handoff contract（gate receipt 中 state.current_handoff_path 指向的 handoff 文件）— 可选增强

Deep 层（deep_verified 准入）：
- 是否需要官方 installer/hosts/* 适配
- 是否值得进 --target 参数和 README 安装矩阵
- 是否有 smoke 验证覆盖

> 只有 payload_capable 以上才进 installer；convention_only 宿主只做文档支持。

### 禁止消费面

所有三级梯度（convention_only / payload_capable / deep_verified）均不得将以下面作为稳定消费 contract。违反此表意味着宿主与 runtime 实现细节产生耦合，此类消费将被视为 leak。

| # | forbidden surface | 类型 | 为什么禁止 | 来源 |
|---|-------------------|------|-----------|------|
| F1 | `state/sessions/*` | 运行态附属 | runtime 内部会话管理，非 contract 面；超租约后可清理 | Persistence Surface 分层 |
| F2 | `state/last_route.json` | 可删派生 | 可从 handoff/run 派生，derived surface | Persistence Surface 分层 |
| F3 | Route name 全集 / route taxonomy | 实现细节 | runtime 内部路由枚举，不是宿主消费的 contract；keep-list 不冻结 route 枚举 | 外部消费面 Keep-list |
| F4 | Gate 三元组直渲（`gate_status` / `blocking_reason` / `plan_completion`） | internal_taxonomy_leak | runtime 内部 gate 状态机，默认输出中不应前置 | Output Rendering Audit |
| F5 | `Entry Guard Reason` 内部守卫码 | internal_taxonomy_leak | runtime 内部守卫码，非宿主需消费的 contract | Output Rendering Audit |
| F6 | `Route: <route_name>` 直接暴露 | internal_taxonomy_leak | cancel_active / fallback 路径直接渲染 route_name | Output Rendering Audit |
| F7 | Output 渲染文案措辞（`Next:` / `Status:` / `Decision Status:` 等 human hint） | derived 人类提示 | 由 route_name + gate_status + handoff 推导，不是 machine truth；宿主消费 handoff contract 而非 Next 文案 | Output Rendering Audit; 外部消费面 Keep-list |
| F8 | Runtime 内部模块边界（Python API 签名、class 结构、dataclass 名称） | 实现细节 | keep-list 不冻结 Python 内部 API；宿主消费的是持久化 contract 文件而非 Python 调用面 | 外部消费面 Keep-list |

> deep_verified 宿主的 runtime 内部可能事实上读取 F3-F7 中的值（如 route_name 用于渲染），但这属于 runtime 实现细节，不是宿主的 contract 承诺。P4c 收敛 output 时需消除此类 leak。


### 契约消费矩阵

每个主链真相文件和可审计凭证在每级梯度的消费定位。接续锚点、授权凭证、交互 checkpoint 三类面分开归位。deep_verified 列已完成最终裁定（原"预期 required†"全部确认为 required，来源：P4c-1）。

_接续锚点（告诉下一步做什么）_

| surface | 文件 | convention_only | payload_capable | deep_verified | 来源 |
|---------|------|-----------------|-----------------|---------------|------|
| Handoff contract | `state/current_handoff.json` | forbidden | optional | required | Keep-list, 能力梯度 |
| Plan binding | `state/current_plan.json` | forbidden | optional | required | Persistence Surface |
| Run state | `state/current_run.json` | forbidden | optional | required | Persistence Surface |

_授权凭证（证明为什么被授权）_

| surface | 文件/规范 | convention_only | payload_capable | deep_verified | 来源 |
|---------|----------|-----------------|-----------------|---------------|------|
| Gate receipt（运行级） | `state/current_gate_receipt.json` | forbidden | optional | required | Keep-list, Persistence Surface |
| ExecutionAuthorizationReceipt（协议级） | protocol.md §6 | forbidden | optional | required | Keep-list |
| Archive receipt | `state/current_archive_receipt.json` | forbidden | optional | optional | Persistence Surface |

_交互 checkpoint（AI 暂停等待）_

| surface | 文件 | convention_only | payload_capable | deep_verified | 来源 |
|---------|------|-----------------|-----------------|---------------|------|
| Clarification | `state/current_clarification.json` | forbidden | optional | required | Persistence Surface |
| Decision | `state/current_decision.json` | forbidden | optional | required | Persistence Surface |

_长期知识（所有梯度均可消费）_

| surface | 物理对应 | 所有梯度 | 来源 |
|---------|---------|---------|------|
| Blueprint / Plan / History | `.sopify-skills/blueprint/`, `plan/`, `history/` | readable | Persistence Surface, Keep-list |
| Protocol | `blueprint/protocol.md` | readable | Keep-list |
| Preferences / Feedback | `user/preferences.md`, `user/feedback.jsonl` | readable | Persistence Surface, Keep-list |

> **P4c-1 裁定依据**：deep_verified 必须稳定消费这些 canonical contract surface——runtime 完整路径会产出并使用它们。把任何一项降为 optional 会制造"运行了 runtime 但不承诺消费其 contract 产物"的矛盾。

> **convention_only forbidden 理由**：该梯度只承诺消费 protocol + 文件约定，不承诺消费运行态 state 文件或 receipt 实例面。

> **EAR 与 gate_receipt 的关系**：EAR 是 protocol/doc contract（Keep-list），gate_receipt 是一种常见运行态承载（Keep-list），两者不等同。EAR @ convention_only = forbidden 的理由是"该梯度不承诺消费协议级 receipt 实例语义"，不是"无 runtime"。

> **gate_receipt 消费者投影差异**：Keep-list 表将 consumer 写为 `host / external_tool`，Persistence Surface 表写为诊断/审计消费者。两者不矛盾：Keep-list 说明有合法宿主消费场景（如 action_proposal_retry），Persistence Surface 反映常态下的主要消费者。payload_capable 消费 gate_receipt 属于审计增强。


**消费面投影 summary（derived / non-normative）**

> 此表从上方消费矩阵机械派生，不是独立权威源。如有冲突，以上方消费矩阵为准。

| 消费面 ID | convention_only | payload_capable | deep_verified |
|-----------|:-:|:-:|:-:|
| handoff_contract | ✗ | ○ | ● |
| plan_binding | ✗ | ○ | ● |
| run_state | ✗ | ○ | ● |
| gate_receipt | ✗ | ○ | ● |
| ear | ✗ | ○ | ● |
| archive_receipt | ✗ | ○ | ○ |
| clarification | ✗ | ○ | ● |
| decision | ✗ | ○ | ● |

> ✗ = forbidden　○ = optional　● = required


### 增强组合与声明

payload_capable 是能力带宽，不是单点能力。以下是 canonical 的三组 opt-in 增强：

| 增强组合 | 消费的 contract 面 | 回答的问题 | 依赖 |
|---------|-------------------|-----------|------|
| **接续增强** | handoff + plan binding + run state | 上次停哪了？现在该干嘛？handoff 是核心前提，plan binding / run state 是补强接续上下文的常见配套面 | 无硬性前置依赖 |
| **交互增强** | clarification + decision | 当前是否卡在 clarification / decision checkpoint？即 AI 在等用户补事实或拍板 | 建议先有接续增强（否则缺执行上下文） |
| **审计增强** | gate_receipt + EAR + archive_receipt | 这次接续有没有授权？有没有证据链？gate_receipt + EAR 是核心授权证据；archive_receipt 是历史归档补强 | 无硬性前置依赖（可独立审计） |

> 三组之间无互斥。交互增强对接续增强有弱依赖（建议而非必须）。


宿主通过 `HostCapability.declared_enhancements` 声明自己启用的增强组。声明轴为 `EnhancementGroup` enum（`installer/models.py`），与 `FeatureId`（安装能力轴）正交，不互相扩展。

_治理期望表_

| SupportTier | 期望的 declared_enhancements | 说明 |
|-------------|----------------------------|------|
| deep_verified | CONTINUATION + INTERACTION + AUDIT | 完整路径，消费全部 contract 面 |
| payload_capable | 至少 CONTINUATION（官方接入）；最小准入可为空 | 官方新宿主底线为接续增强；tier 本身不强制。此区分是 policy，不是机器可检查轴 |
| convention_only | 空 | 不消费 state 文件，无增强声明 |

> 此表是 policy expectation，不是 hard constraint。校验脚本检查声明与期望的一致性，结果为 advisory（警告而非阻断）。


### 官方接入画像

> 能力分层（ladder）定义"你属于哪级"，接入画像定义"官方新宿主至少该做到什么程度"。两者是不同的层，ladder 不因画像而改。

| 画像 | 能力层 | 增强要求 | 适用场景 |
|------|--------|---------|---------|
| **官方最低接入** | payload_capable + 接续增强 | 接续增强全组（核心：handoff；配套：plan binding + run state） | 所有官方新宿主的底线 |
| **对话式宿主** | payload_capable + 接续增强 + 交互增强 | 额外消费 clarification/decision checkpoint | 需要处理挂起的"AI 等人回答/拍板"状态的宿主 |
| **全审计宿主** | payload_capable + 接续增强 + 交互增强 + 审计增强 | 额外消费 gate_receipt/EAR/archive_receipt | 需要证明接续合法性和证据链的宿主 |

> 此画像基于能力治理审计建议（来源：P4b.5），不改 ladder 定义。ladder 上 payload_capable 的准入仍为"payload 安装 + prompt asset 消费"，但官方新宿主在此基础上应至少叠加接续增强。


**接入路径**

```
步骤 1: 读 protocol + 遵守文件约定
         ↓
    convention_only ✅ "算接入了"
    能读 plan、blueprint、protocol
    但不知道上次做到哪了
         ↓
步骤 2: 装 prompt asset / payload
         ↓
    payload_capable ✅ "拿到入场券"
    能装 prompt，消费 prompt asset
    但仍然不知道上次做到哪了
         ↓
步骤 3: 叠加 opt-in 增强（官方新宿主至少到接续增强）
         ↓
    + 接续增强：读 current_handoff（核心）+ plan binding + run state（配套）→ 知道上次停哪了、接下来该干嘛
    + 交互增强：读 clarification/decision → 知道是否卡在等人回答/拍板
    + 审计增强：读 gate_receipt/EAR（+ archive_receipt）→ 证明这次接续有授权、有证据链
         ↓
    新宿主拿到 plan + handoff + 凭证 → 直接接着编码 ✅
```

> 步骤 3 的每一项增强都是读冻结的 contract 文件（schema 被 P4a keep-list 保护），不是调 runtime API。不需要跑完整 runtime 也能接班。


**接入判定 summary**

- **官方新宿主最低接入**：payload\_capable + 接续增强（handoff 为核心；plan binding + run state 为配套）。
- **需要处理用户补事实/拍板**：再加交互增强（消费 clarification / decision checkpoint）。
- **需要证明授权链**：再加审计增强（gate\_receipt + EAR 为核心授权证据；archive\_receipt 为历史归档补强）。
- **deep\_verified**：仍保留为完整 runtime / installer / smoke 的高保证层，不作为新宿主默认前提。


### Convention Quickstart 最小交付面

定位：adoption guide / reading order。**不是**第二规范源。本节只定义 quickstart 的交付面边界，不等于 quickstart 本身已实现（实现见 tasks.md 长期项）。

- 提供 protocol.md 面向外部宿主的阅读顺序指引（按文档披露梯度）
- 提供 compliance check 的运行入口（指向 Protocol Compliance Suite Phase 1 已有基础）
- **不新增 normative 内容**：protocol.md 是唯一合规入口
- **不复述 schema**：只引用、不重新定义


### Prompt 镜像治理原则

- prompt asset 属于 payload/install surface（P4a keep-list 已冻结此消费面）
- 现有 Claude/Skills/ 和 Codex/Skills/ 目录树是 legacy exception，只维护现有内容，不再扩张
- 新宿主不进现有目录树结构；新宿主如需 prompt asset，走 payload 机制
- 讨论框架不是"要不要再开目录树"，而是"payload 机制是否满足需求"


### 模块运行必需性

> 审计目标：评估 runtime/ 和 installer/ 各功能区在每级梯度的**模块运行必需性**。判定标准是"新宿主是否需要**运行**该模块"，不是"是否消费该模块的持久化产物"。持久化 contract 消费面的评估在契约消费矩阵，不在本节。（来源：P4b.5 审计）

> **模块计数口径**：runtime/ 59 个非 `__init__.py` 的 Python 模块（含 `_models/` 下 5 个），另有 `contracts/`、`builtin_skill_packages/` 两个资源目录（不计入模块数）。installer/ 11 个非 `__init__.py` 的 Python 模块（含 `hosts/` 下 3 个宿主适配器）。


| 功能区 | 包含模块 | conv | payload | deep | 备注 |
|--------|---------|:----:|:-------:|:----:|------|
| **核心管线** | engine, router, gate, execution\_gate, entry\_guard, gate\_output | ✗ | ✗ | ✓ | 路由/gate 决策循环，deep runtime 核心 |
| **状态持久化** | state, state\_invariants | ✗ | ✗ | ✓ | 所有 state/ contract 文件的统一落盘层（set\_current\_\* 方法族） |
| **上下文构建** | context\_snapshot, context\_recovery, context\_builder, context\_v1\_scope | ✗ | ✗ | ✓ | 会话上下文快照与恢复，deep runtime 的执行上下文供应链 |
| **Plan 编排** | plan\_orchestrator, plan\_registry, plan\_scaffold | ✗ | ✗ | ✓ | plan 生命周期由 runtime 驱动；payload\_capable 读 plan/ 目录（协议层面） |
| **Handoff / Checkpoint** | handoff, checkpoint\_materializer, checkpoint\_request, checkpoint\_cancel | ✗ | ✗ | ✓ | handoff.py 提供 handoff 语义；实际写盘经 state.py；接续增强消费 JSON 文件 |
| **Clarification / Decision** | clarification, clarification\_bridge, decision, decision\_bridge, decision\_policy, decision\_tables, decision\_templates | ✗ | ✗ | ✓ | 交互 checkpoint 语义来源；实际写盘经 state.py；交互增强消费 JSON |
| **Output / Templates** | output, message\_templates | ✗ | ✗ | ✓ | 渲染层，属 forbidden surface F5/F6 |
| **Skill 系统** | skill\_registry, skill\_resolver, skill\_runner, skill\_schema, builtin\_catalog | ✗ | ✗ | ✓ | deep runtime 技能调度 |
| **知识层** | kb, knowledge\_layout, knowledge\_sync | ✗ | ✗ | ✓ | KB 管理是 runtime feature |
| **校验 / Guard** | deterministic\_guard, action\_intent, action\_projection, develop\_callback, develop\_quality | ✗ | ✗ | ✓ | Validator 逻辑在 deep runtime 进程内运行 |
| **Archive** | archive\_lifecycle | ✗ | ✗ | ✓ | 归档语义来源；实际写盘经 state.py |
| **基础设施** | config, preferences, manifest, models, \_models/, \_yaml, contracts/, cli, cli\_interactive, resolution\_planner, sidecar\_classifier\_boundary, vnext\_phase\_boundary, failure\_recovery, workspace\_preflight | ✗ | ✗ | ✓ | runtime 内部基础设施；workspace\_preflight 是 deep 的启动检查 |
| **Installer: payload 安装** | installer/payload, hosts/, distribution, validate, models, outcome\_contract, inspection | ✗ | 工具† | ✓ | payload\_capable 通过 install.sh 调用，不直接依赖 Python API |
| **Installer: workspace 初始化** | installer/bootstrap\_workspace | ✗ | opt-in‡ | ✓ | workspace bootstrap 是 payload\_capable 的可选增强 |
| **Installer: runtime 打包** | installer/runtime\_bundle | ✗ | ✗ | ✓ | 只有 deep\_verified 需要完整 runtime bundle |

> ✗ = 不需要运行；✓ = 需要运行；工具† = 通过 CLI 脚本间接调用（install.sh/install.ps1），不是 contract 级依赖；opt-in‡ = payload\_capable 可选增强，不是准入。


**语义来源 → 落盘路径 → contract 文件**

> 所有 state/ contract 文件的磁盘写入都经过 `state.py` 的 `set_current_*` 方法族统一落盘。下表的"语义来源"指提供业务语义和触发写入的模块，不是唯一写入者。

| 语义来源 | 落盘路径 | contract 文件 | 对应增强组 |
|---------|---------|--------------|--------------|
| handoff.py（+ engine.py 触发） | state.set\_current\_handoff | current\_handoff.json | 接续增强核心 |
| engine.py / state.py | state.set\_current\_run | current\_run.json | 接续增强配套（run state） |
| plan\_registry.py / plan\_orchestrator.py | state.set\_current\_plan | current\_plan.json | 接续增强配套（plan binding） |
| clarification.py（+ clarification\_bridge 触发） | state.set\_current\_clarification | current\_clarification.json | 交互增强 |
| decision.py（+ decision\_bridge 触发） | state.set\_current\_decision | current\_decision.json | 交互增强 |
| gate.py | state 直写 | current\_gate\_receipt.json | 审计增强 |
| archive\_lifecycle.py / engine.py | state.set\_current\_archive\_receipt | current\_archive\_receipt.json | 审计增强 |

> 此映射是"当前事实"，不是"永久绑定"。P4c 及后续里程碑可以改变生产者实现，只要 contract 文件 schema 不变（P4a keep-list 保护）。


**审计结论**

1. **convention\_only 不需要任何 runtime/ 或 installer/ 模块**。全部能力来自读协议文档和遵守文件约定。
2. **payload\_capable 不需要任何 runtime/ 模块**。其消费的机器真相文件都是冻结 JSON contract，由 P4a keep-list 保护 schema。消费文件 ≠ 依赖生产者模块。
3. **payload\_capable 对 installer/ 的依赖是工具性的**，不是 contract 性的。宿主通过 install.sh 安装 payload，或按 protocol 手动放置文件。installer 的 Python 内部 API 不在接入契约范围内。
4. **deep\_verified 对 runtime/ + installer/ 有完整能力覆盖依赖**。不是"每轮运行全部模块"——单次执行路径取决于具体 action/route，但能力层面需要完整 runtime 可用。这是设计预期，不是缺陷。
5. **生产者 vs 消费者边界明确**：7 个 contract 文件的语义分别来自 ~7 个 runtime 模块，全部经 state.py 统一落盘。payload\_capable 消费产物（文件），不消费生产者（模块）。此边界由 forbidden surface F8 保护。


审计结论不是"runtime 已可删除"，而是"新宿主接班所需能力已可用 contract 显式表达，并与 runtime 内部实现解耦"。新宿主要实现安全接班，不需要接入完整 runtime，但不能绕过显式 contract。官方最低接入画像应为 payload\_capable + 接续增强；runtime 在该路径中是 contract 生产者与 deep hardening 层，不是新宿主的接入前提。


### 长期边界与后续交接

**已证明结论**


1. convention\_only 仍保留为定义层最低边界，负责界定"什么算进入 Sopify 生态"，但不是官方新宿主的真实落点。
2. payload\_capable 是能力带宽，不等于完整接续；官方新宿主至少还应叠加接续增强。
3. 新宿主接续依赖的是冻结的 state/ contract 文件与长期知识资产，不是 runtime 内部模块或 API。
4. Forbidden surface 已显式列出（F1-F8），宿主不得依赖 sessions/\*、last\_route、输出文案、runtime 模块边界等未冻结面。
5. payload\_capable 对 runtime/ 的 blast radius 为零；对 installer/ 仅有工具性依赖。

**未裁定的边界**

1. ~~原未裁定 deep\_verified 的每个面是否全部 required。~~ **P4c-1 已裁定：7 项全部 required，† 已消除。**
2. 不在能力治理审计中重写 ladder 定义，只审计消费边界与 blast radius。
3. 不在能力治理审计中变更 schema、代码实现或 installer/runtime 结构。
4. 审计增强内部的长期最小组合（gate\_receipt / EAR / archive\_receipt 哪些是核心、哪些是补强）仍以后续试点 evidence 为准。官方最低接入不含审计增强这一点已在契约消费矩阵和官方接入画像中定下，此条不开放该结论。
5. 若未来长期验证 convention\_only 只承担只读参与者角色，可在后续里程碑考虑降格或改名，但不在本次处理。


**后续里程碑交接**

- **P4c**：负责把本次审计结论投影到实现层和 host adapter / installer / validator 消费面。详见 tasks.md P4c 段"P4c 前提声明"。
- **P4d**：负责选非 deep 宿主做试点，验证 payload\_capable + 接续增强是否足以支撑真实接班。
- **P5/P6**：再依据试点 evidence 逐步收缩 deep-runtime-only surface，并推动 runtime 向 reference implementation 退位。


## 轻量化产品指标

Sopify 的设计目标不仅是工程轻量（削减 runtime），更是产品轻量（少概念、少前置、默认能用、可逐步增强）。

| 指标 | 目标 |
|------|------|
| Convention 首次上手步骤数 | ≤3（读 blueprint → 写 light plan → finalize） |
| 首次上手必需持久化文件 | ≤4（project.md + blueprint/ 三件套） |
| 默认 workflow 必需 contract 数 | ≤5（plan package + archive + receipt + knowledge_sync + blueprint read） |
| 增强路径额外概念 | 逐步引入：review loop → checkpoint → runtime state → plugin |

## 硬约束

1. **能删则删**：新概念必须替换旧概念或证明不增加概念预算
2. **Validator 只授权不执行**：不做 plan materialization、文件迁移、自动修复、状态推进
3. **Deterministic core 只按结构化事实执行**：不理解人话、不做语义推断
4. **Host prompt 不定义机器真相**：prompt 只渲染 machine truth，不作为 runtime truth source
5. **develop_mode 是 hint**：不参与权限裁决；权限裁决看 ActionProposal side_effect + state + risk policy
6. **archive 终态不是 host action**：`archive_receipt.status` 是结果状态，不进 `required_host_action`
7. **不用 router phrasing patch 或 prompt workaround 充当长期解法**：machine truth 未收敛时，回到 protocol/validator/deterministic guard 修复
8. **新增判断挂旧语法**：蓝图变更优先强化证据与授权层，不优先做"更多能力"；新增项必须挂回现有 P 主航道，不得新造编号/章节体系
9. **外部接入优先于官方适配**：优先做能让外部宿主看懂、接入、被验证的事，不优先增加官方深适配负担

## 核心契约

### Archive lifecycle

- `ActionProposal(action_type="archive_plan")` 是协议入口；`~go finalize` 只是 alias
- 主体是结构化 `archive_subject`，不通过正则或词表猜
- 两层分离：Validator 负责 validate + authorize + emit artifacts；deterministic core 负责 check + apply
- Legacy/metadata 不完整主体返回 `migration_required`，不自动修复
- 归档只在主体等于当前 global `current_plan` 时清理执行状态

### Checkpoint 契约

只有两种 canonical checkpoint：

**Clarification：** 补齐最小事实。Runtime 写入 `current_clarification.json`，handoff 暴露 `checkpoint_request`。宿主展示问题列表，等待用户补充后恢复 runtime。Pending 期间不生成正式 plan。

**Decision：** 多方案拍板。Runtime 写入 `current_decision.json`，handoff 暴露推荐项与提交状态。宿主展示选项，等待确认后恢复 runtime。Pending 期间不物化 plan。

**Develop callback：** `continue_host_develop` 期间命中用户拍板分叉时，通过 `develop_callback_runtime.py` 回调 runtime，触发 clarification 或 decision。不是独立 checkpoint type。

### knowledge_sync

`knowledge_sync` 是唯一正式同步契约。旧 `blueprint_obligation` 概念只保留 legacy reject 语义，不重新合法化。

```yaml
knowledge_sync:
  project: skip|review|required
  background: skip|review|required
  design: skip|review|required
  tasks: skip|review|required
```

- `skip`: 本轮无需同步
- `review`: 可能受影响，finalize 时复核
- `required`: 必须更新，否则 finalize 阻断

### Runtime gate ingress

- `persisted_handoff` 是 gate 唯一正向机器证据
- gate 判定优先级：`strict_runtime_entry_missing` > `handoff_missing/normalize_failed` > `handoff_source_kind`
- `reused_prior_state` 保持允许态（只读恢复路径）

### Runtime state scope

- Review state 默认落在 `state/sessions/<session_id>/`，覆盖 `current_plan/current_run/current_handoff/current_clarification/current_decision/last_route`
- 根级 `state/` 只承载 global execution truth（当前仍包含 `resume_active / exec_plan` 等 transitional 语义，将随 route 收敛逐步清理；`execution_confirm_pending` 已在 Wave 3b 删除）
- Archive lifecycle 只在归档主体等于当前 global `current_plan` 时清理对应执行状态
- `session_id` 由宿主透传或 gate 自动生成；同一条 review 续轮必须复用同一个 `session_id`
- 并发 review 使用不同 `session_id`；global truth 只补 soft ownership 观测字段
- Clarification / decision bridge 先读 session review state，再回退到 global execution truth

### 消费契约

| Context | 读取集 | Fail-open |
|---------|--------|-----------|
| `bootstrap` | project.md, preferences.md, blueprint/README.md | 缺深层 blueprint 不报错 |
| `consult` | project.md, preferences.md, blueprint/README.md | 不要求 background/design/tasks |
| `plan` | 上述 + blueprint 全集 + active_plan | 深层 blueprint 缺失先补齐 |
| `develop` | plan 读取集 + state/*.json | history 缺失不阻断 |
| `archive` | archive_subject, knowledge_sync, blueprint 全集, history/index.md | history/index.md 缺失现场创建 |

## Design Influence Intake Gate

外部设计影响分三级准入：

| 级别 | 含义 | 准入条件 |
|------|------|---------|
| T0 Reference | 启发方向 | plan 包内标注 |
| T1 Adoption | 采纳待验证 | 映射到哲学 + 有实现路径 + 有验证方案 + 不与 ADR 冲突 |
| T2 Principle | 沉淀原则 | 已实现 + dogfood 未回退 + 通过删除测试 |

### 已登记的外部设计影响（2026-05）

| 来源 | 吸收方向 | 准入 | 落点 | 映射哲学 |
|------|---------|------|------|---------|
| HelloAGENTS | 验证证据结构化挂载（contract.json / review.json 启发 Verifier evidence 标准化） | T1 | P1.5→P2 桥接 Verifier slice | Convergence-first |
| OpenSpec | side_effect delta 语义（ADDED / MODIFIED / REMOVED，file-level 第一版） | T1 | P2 子项 | Wire-composable |
| Superpowers | 行为级协议合规验证（headless behavioral test 启发 Protocol Compliance Suite） | T1 | P1.5 先行 Phase 1 + 长期 Phase 2 | Convergence-first |
| Hermes Agent | 知识自动提炼方向（persistent memory + skill curator） | T0 | 明确延后 | Surface-shared |
| Spec-Kit | 声明式工作流定义 / 离线分发 | T0 | 明确延后 / installer 层 | Wire-composable |

## ADR 索引

| ADR | 标题 | 状态 |
|-----|------|------|
| ADR-013 | Product Positioning: Evidence & Authorization Layer | 已确认 |
| ADR-016 | Protocol-first / Runtime-optional | 已确认 |
| ADR-017 | Action/Effect Boundary | P0 完成，持续扩展 |

详见 `architecture-decision-records/`。

## KB 职责矩阵

| Path | Layer | Created When | Git Default |
|------|-------|-------------|-------------|
| `blueprint/README.md` | L0 index | 首次项目触发 | tracked |
| `project.md` | L1 stable | 首次 bootstrap | tracked |
| `blueprint/{background,design,tasks}.md` | L1 stable | 首次进入 plan 流 | tracked |
| `plan/YYYYMMDD_feature/` | L2 active | 每次正式方案流 | tracked |
| `history/YYYY-MM/...` | L3 archive | archive_plan apply 成功 | tracked |
| `state/*.json` | runtime | runtime 执行期间 | ignored |
| `replay/` | ~~optional~~ P3b 下线 | 命中主动记录策略（P3b 后移除） | ignored |
