# 技术设计: 状态机 Hotfix（B1 前置门禁）

## 技术方案
- 核心目标: 把“多文件、多作用域、各层各自读状态”的协商态流程，收敛为一次入口内生成、全链路共享的唯一解析快照
- 设计结论:
  - 协商态与执行真相态必须拆开
  - Proposal 不再允许 global fallback
  - Router/Engine/Handoff 必须只消费统一快照，不得自行摸底层状态
  - 冲突必须变成可见、可恢复的 `state_conflict`，不能在构建期直接抛 Fatal

## 目标态总览

### 1. 状态实体分层
| 状态实体 | 语义层级 | 目标作用域 | owner / provenance 字段 | 主要消费阶段 | 跨 Session 规则 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `current_run` | 执行真相 | global execution truth 或 owner-bound review state | `owner_session_id / owner_run_id / resolution_id` | execution confirm / resume / finalize / develop | 允许，需显式 promotion / ownership | 不属于 abortable negotiation state |
| `current_plan` | 执行真相 | 与 `current_run` 同步 | 跟随 active run / plan identity | planning review / execution confirm / finalize | 允许，跟随执行真相 | 不属于 abortable negotiation state |
| `current_plan_proposal` | 协商态 | Session-only | `checkpoint_id / reserved_plan_id / topic_key` | plan package confirm | 不允许 | 废弃 global 视口与 fallback |
| `current_clarification` | 协商态 | 设计态 Session-only；开发态 owner-bound | `phase / owner_session_id / owner_run_id / resume_context` | answer questions / develop resume | 仅开发态允许 | 缺 `phase` 或 provenance 不完整直接 Quarantine |
| `current_decision` | 协商态 | owner-bound | `phase / decision_id / checkpoint_id / owner_session_id / resume_context` | confirm decision / execution gate / develop resume | 允许合法恢复 | 合法的 `unconsumed_decision` 不能被误杀 |
| `current_handoff` | 派生输出 | 跟随 resolved snapshot 写出 | `resolution_id / required_host_action / observability.*` | host handoff / runtime gate / doctor/status 观测 | 不作为协商输入事实 | 必须和 resolved route 唯一一致 |

### 2. 单写真相源
入口先生成不可变 `ContextResolvedSnapshot`，再向下传递：

1. Loader
   - 读取 review scope 与 global scope 的候选状态
   - 在反序列化阶段做 provenance 校验
   - 将 unknown / mismatched 状态放入 Quarantine

2. Resolver
   - 按优先级生成唯一 resolved state 视图
   - 产出 `is_conflict / conflict_reason / allowed_user_intents / allowed_internal_actions / quarantined_items`

3. Router / Engine / Handoff / Output
   - 只消费 snapshot
   - 禁止再次直接 `get_current_*()` 做二次判断

这样可以从接口层禁止“同一毫秒内，上游和下游看到的是两套状态”。

同时需要补一条写侧最小一致性：同一份 resolved snapshot 派生出的 `current_run.json` 与 `current_handoff.json` 必须带同一 `resolution_id`。这不是原子提交机制，也不替代未来的 truth-source 设计；它只负责把“半写入导致的对冲状态”稳定收敛为可恢复的 `state_conflict`。

## H0 | 状态矩阵与不变量冻结
本 Hotfix 的第一优先级不是改代码，而是先冻结状态矩阵和不变量。

### 关键不变量
1. 一次 resolved snapshot 只能有一个有效协商出口
   - `clarification_pending / decision_pending / plan_proposal_pending / execution_confirm_pending` 之间必须互斥
   - 若同一 resolved scope 内同时存在多个合法 pending checkpoint，不走优先级吞并，直接进入 `state_conflict`

2. Session 明确裁决优先于任何旧的 global 协商态
   - `session current_decision`
   - `session current_clarification`
   - `session current_plan_proposal`
   - 以上三者的优先级都高于任何 global 协商态残留

3. Proposal 不得再成为全局输入事实
   - Router 与 Engine 在路由 / 恢复 / handler 入口都不得读取 global proposal

4. `current_plan` 与 `current_run` 是执行真相，不是协商垃圾桶
   - abort / conflict cleanup 都不得清它们

5. Handoff 与 Run Stage 必须单向收敛
   - 若 snapshot 解析结果要求 `confirm_decision`，则 handoff 与 run stage 不能再同时暴露 `confirm_plan_package`

6. H0 必须落成可执行契约
   - 不变量不能只保留在 Markdown 中，必须通过 domain validator / invariant checker 进入 Loader、Resolver 或测试主链
   - 生产路径禁止使用裸 `assert` 作为契约执行手段，应使用显式 validator 与 domain error

### 已冻结的协商态边界
1. abortable negotiation state 只包含
   - `current_plan_proposal`
   - abortable `current_clarification`
   - abortable `current_decision`
   - 派生的 checkpoint handoff carrier
2. `current_run / current_plan` 始终属于 stable execution truth
   - 可以在 abort 后被 stage normalize
   - 不能被当成 negotiation garbage 一并清空
3. `current_run / current_handoff` 的 primary/secondary truth source 不是本 Hotfix 决策范围
   - 当前只做 `resolution_id` 批次绑定与 mismatch/conflict 检测
   - 更大范围的 truth-source 设计留给后续 control-plane 演进

## H1 | Loader + Resolver + Immutable Snapshot

### 设计要求
1. provenance 校验下沉到 Loader
   - JSON 一旦声明了 `session_id / owner_session_id / owner_run_id / run_id`，就在对象重建时校验
   - 若与当前上下文不匹配，直接返回 `None` 或 `QuarantinedState`
   - 不允许把这种 if/else 分散在 Router / Engine / API 层重复实现

2. Resolver 只在入口运行一次
   - 输入是 review scope + global scope 的候选状态
   - 输出是不可变 `ContextResolvedSnapshot`
   - snapshot 作为 Router / Engine / Handoff 的唯一输入
   - `ContextResolvedSnapshot` 的建议实现为 `@dataclass(frozen=True)`，内部集合统一使用 `tuple` / `MappingProxyType`，避免下游拿到快照后继续 mutate

3. Resolver 不允许“失败即崩”
   - 冲突场景返回 `is_conflict = true`
   - 同时附带 `conflict_reason`、`allowed_user_intents = ["cancel", "force_cancel"]` 与 `allowed_internal_actions = ["abort_negotiation"]`
   - 这样冷启动死锁时，用户仍可通过取消语义脱困，宿主 / Bridge 也不依赖完整语义解析就能触发 cleanup

4. Loader 要承担 legacy 兼容与写侧批次校验
   - `phase` 是 clarification / decision 反序列化分支的必需字段
   - legacy 状态若缺 `phase`、关键 provenance，或无法判断所属分支，不猜测归类，直接进入 Quarantine
   - `current_run.json` 与 `current_handoff.json` 若 `resolution_id` 不一致，则直接产出 `is_conflict = true` 的 snapshot
   - legacy `current_run/current_handoff` 若同时缺少 `resolution_id`，按兼容路径处理；新旧混杂或新写后 mismatch 则进入 `state_conflict`

### Snapshot 最小字段建议
- `resolution_id`
- `resolved_current_run`
- `resolved_current_plan`
- `resolved_current_plan_proposal`
- `resolved_current_clarification`
- `resolved_current_decision`
- `resolved_last_route`
- `quarantined_items`
- `is_conflict`
- `conflict_reason`
- `allowed_user_intents`
- `allowed_internal_actions`
- `resolution_notes`

## H2 | 作用域与 Provenance 收口

### Proposal
1. `current_plan_proposal` 定义为严格 Session-only
2. global proposal 不再参与当前路由
3. legacy proposal 即使物理存在，也只能进入 Quarantine 视图

### Clarification
1. 设计态 clarification
   - Session-only
   - 会话结束即失效

2. 开发态 clarification
   - 必须绑定 `owner_run_id / session_id`
   - 允许跨 Session 恢复，但只能被同一执行链路认领

### Decision
1. Decision 允许跨 Session 恢复
   - 但必须满足 owner 绑定
   - 不能因为“当前没有对应 Proposal”就自动归入幽灵状态

2. 对 `unconsumed_decision` 的保护
   - 默认保留 owner-bound 且仍可恢复的 confirmed decision
   - 只有用户显式 abort 时才允许清理 abortable decision

3. Decision liveness 必须按 kind / phase 分层
   - design-phase decision
     - 校验 `decision_id / checkpoint_id / owner_session_id / resume_context`
     - 不要求 execution gate 拓扑连通
   - execution-gate decision
     - 在上述校验基础上，额外要求与当前 `execution_gate / pause_reason` 拓扑连通
   - `run_id` 不是唯一存活条件，不能单独决定 decision 是否进入 Quarantine
   - 写入时必须带 `phase`；legacy decision 若缺 `phase`，按 provenance 不完整处理并进入 Quarantine

### Legacy Unknown State
1. 没有 provenance 的旧文件不直接报错
2. 也不允许被 adopt 成当前真实状态
3. 统一标注为 `provenance = unknown` 并进入 Quarantine

## H3 | Router / Engine / Handoff 单向收敛

### Router
1. Router 只看 snapshot，不再自己做 `review or global` 拼接
2. pending 判断顺序改为：
   - resolved clarification
   - resolved decision
   - resolved plan proposal
   - execution confirm / resume
3. 只有 snapshot 中存在同 scope、同 provenance 的 Proposal，才允许路由到 `plan_proposal_pending`

### Engine
1. Handler 只消费 resolved checkpoint
2. `plan_proposal_pending` handler 不再“二次读取当前 Session 文件赌它存在”
3. 若路由与 snapshot 事实不一致，返回结构化 `state_conflict`，而不是抛原始异常
4. `state_conflict` 与 `InvariantViolation` 必须分开
   - `state_conflict`：用户可恢复的状态冲突、作用域冲突、批次不一致
   - `InvariantViolation`：程序员错误、写侧契约被破坏或实现遗漏
   - 两者不得混用，更不能把程序员 bug 包装成“用户自己 abort 就好”

### Handoff
1. Handoff 必须从同一个 snapshot 构造
2. Handoff 只暴露一个明确的 `required_host_action`
3. 若 route 与 handoff 试图输出不同 checkpoint，直接进入 `state_conflict`
4. `current_run.json` 与 `current_handoff.json` 作为同一轮派生写出，必须携带同一 `resolution_id`

### Context Recovery
1. `context_recovery.py` 不再自行散读 `current_*`
2. 它只从 snapshot 中挑需要的计划摘要和 active state
3. 这样恢复上下文不会再次把已 Quarantine 的幽灵状态混回来

### Quarantine 结构
Quarantine 不能只是 `list[str]`，否则后续 `status / doctor` 难以给出行动建议。最小结构建议为：

- `state_kind`
- `path`
- `reason`
- `provenance_status`

## H4 | Conflict Handling 与内部 Abort 原语

### 冲突输出原则
1. `state_conflict` 是可见错误，不是隐藏内部异常
2. 它至少要暴露：
   - conflict kind
   - conflicting state kinds
   - owner / session mismatch 摘要
   - 当前唯一允许的用户意图与内部动作
3. fallback 提示只描述用户意图
   - 可以提示“取消当前协商”或“强制取消”
   - 不暴露内部动作名，也不把内部控制原语包装成顶级 CLI 命令

### 公开面与内部面
1. `abort_negotiation` 是内部控制原语，不是常规面向用户的顶级命令
2. 用户公开入口统一收敛为自然语言“取消 / 强制取消”或交互式 cancel
3. 宿主 / Gate / Bridge 必须保留无需完整上下文校验的廉价机器入口，用于极端冲突态或冷启动死锁时直接下发 `abort_negotiation`
4. Router 负责把取消语义映射到同一内部 cleanup 原语，但这层映射不改变对外公开面

### abort 原语可清理范围
1. `current_plan_proposal`
2. `current_clarification`
   - 仅限 design-phase 或已判定为 abortable 的 develop-phase clarification
3. `current_decision`
   - 仅限用户显式放弃当前协商，或宿主 / Bridge 显式调用内部 `abort_negotiation` 时
   - 且只清理 abortable / unresolved / cancelled-like 状态

### abort 原语禁止清理范围
1. `current_plan`
2. `current_run`
3. 合法 owner-bound、可恢复的 confirmed `unconsumed_decision`

### 自愈策略
1. 优先逻辑隔离，不优先物理删除
2. Quarantine 状态可以被 Tombstone，但只限明确 stale 且不可恢复的协商态
3. 不允许因为一次冲突就把所有旧状态一锅端
4. Quarantine 默认通过 `status / doctor` 与 handoff notes 暴露，不在每轮成功链路强提示刷屏
5. 本 Hotfix 不实现隐式物理删除、定时 GC 或批量清理；清理能力留给未来专项命令

## H5 | 回归测试与解除门禁

### 先补纯函数单测
1. Loader provenance / phase 校验单测
2. Resolver 优先级、互斥不变量与多 pending 并存单测
3. `resolution_id` mismatch 单测
4. Quarantine 结构与可见性单测
5. `InvariantViolation` 与 `state_conflict` 分类单测

### 必补回归
1. ghost global proposal + fresh session decision
   - 结果必须是 decision 胜出

2. ghost global proposal + missing session proposal
   - 不能再进入 `plan_proposal_pending -> missing proposal` 崩溃链路

3. conflict snapshot cold boot
   - 在冲突态下，用户取消意图与宿主 / Bridge 内部 `abort_negotiation` 都仍可进入 cleanup

4. legal cross-session decision recovery
   - owner-bound confirmed decision 不因新 Session 打开而被误删

5. legacy unknown proposal / clarification
   - 被 Quarantine，但不阻断无关主线

6. unique exit invariant
   - `current_handoff.required_host_action` 与 `current_run.stage` 不再产生互相对冲的 checkpoint 出口

7. write-side batch mismatch
   - `current_run.json` 与 `current_handoff.json` 的 `resolution_id` 不一致时，必须稳定进入 `state_conflict`

8. legacy compatibility
   - legacy `current_run/current_handoff` 双缺失 `resolution_id` 时可按兼容路径读取；新旧混杂时不得静默继续

### 解除门禁条件
满足以下条件后，才允许解除本 Hotfix 对 B1 状态链路的阻塞：

1. Router / Engine / Handoff 全部改为 snapshot-only 消费
2. Proposal global fallback 被彻底移除
3. `state_conflict` 与“取消脱困 + 内部 abort 原语”闭环通过回归测试
4. cross-session decision recovery 测试通过
5. legacy quarantine 行为可见且不误伤主线
6. 真实 `runtime_gate` 入口 smoke 通过，至少覆盖：
   - `state_conflict inspect -> 取消`
   - global-scope `abort_conflict`
   - develop-bound checkpoint

## 与 B1 的依赖与并行边界

说明：本节最初是 B1 反写前的唯一冻结输入；当前轮次已完成回写，下面保留为后续验收与解锁依据。

### Hotfix 内部优先级
1. H0
2. H1
3. H2
4. H3
5. H4
6. H5

说明：
- H0-H1 是一切实现前提，没有统一矩阵和 snapshot contract，后面的 Router / Engine 修复只会继续散。
- H3-H4 是真正解除死锁与矛盾 handoff 的主链。
- H5 是 B1 解锁门，而不是补充项。

### B1 必须阻塞的部分
1. 所有触碰 `runtime/router.py`、`runtime/engine.py`、`runtime/handoff.py`、runtime gate 协商恢复的任务
2. 所有要读取或解释 negotiation state 的 `doctor / status / smoke / regression`
3. 所有基于“唯一 handoff 出口”验收的测试

补充冻结：
- 这类任务在 B1 / program plan 中统一按 `blocked by 20260327_hotfix` 处理
- 解除条件不是“代码大体可跑”，而是本 Hotfix 的 H5 回归门全部通过

### B1 允许并行的部分
1. `Bootstrap / Thin Stub / Payload Index / Manifest` 的纯文件系统脚手架
2. `ignore` 写入与 bootstrap 结构整理
3. Host-aware preflight 的 ingress / manifest contract 定义

补充冻结：
- 这类任务统一按 `parallel-allowed` 处理
- 并行工作的输入事实只允许来自文件系统、manifest、payload index，不允许来自 runtime checkpoint

### B1 并行的硬边界
1. 不得 `import runtime.state`
2. 不得读取 `.sopify-skills/state/*.json`
3. 不得根据 `current_handoff.json / current_run.json` 推导业务逻辑
4. 只允许基于 OS 文件系统、manifest、payload index 做判断

### 当前解除门禁结论
1. 在 H5 全绿且真实 `runtime_gate` smoke 通过前，B1 中凡是触碰 runtime 状态链路判断的实现与验收，都继续阻塞
2. B1 中纯 control-plane 脚手架仍可并行
3. 满足上述双门后，优先解锁 `runtime gate / doctor / status / smoke` 相关 B1 切片

## 已冻结结论
1. 本 Hotfix 是独立前置方案，不并回当前 B1 子 plan
2. Proposal global 视口废弃，不保留 fallback read
3. Clarification 按设计态 / 开发态分治
4. 内部 `abort_negotiation` 原语保留，但用户面只暴露“取消 / 强制取消”语义，不暴露顶级 CLI 命令
5. B1 只有纯 control-plane 文件系统工作可并行，所有 runtime 状态链路任务等待本 Hotfix 解除门禁
6. 不实现 `Migration Utility / prune`
7. 不实现隐式物理删除、定时 GC 或批量 Quarantine 清理
8. 不改变 `current_plan / current_run` 语义
9. 不在本 Hotfix 内定义 `current_run / current_handoff` 的 primary/secondary truth source
