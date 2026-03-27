# 变更提案: 状态机 Hotfix（B1 前置门禁）

## 需求背景
当前 runtime 的问题不是“规划任务天然复杂”，而是协商态状态文件在多作用域、多入口下缺乏统一解析与优先级收敛，导致最简单的“确认一个结论并写回文档”也可能失真。已明确的故障链路如下：

1. 全局残留了过期的 `current_plan_proposal.json`
   - Proposal 本应是协商态临时产物，但旧文件没有被垃圾回收清掉，形成“幽灵 Proposal”。

2. `router.py` 的 pending 分类优先级错误
   - 当前 Session 已经写下新的 `current_decision`，但 Router 先看到了全局 Proposal，再看 Decision，导致真实用户裁决被旧 Proposal 抢占。

3. `plan_proposal_pending` 的处理器只看当前 Session
   - Router 把路由导向 Proposal，但当前 Session 内并没有对应 Proposal 文件，Handler 进入后只能抛错。

4. 运行态机器事实发生分裂
   - `current_handoff.json` 指向 `confirm_plan_package`，底层 gate / run stage 却仍然指向 `confirm_decision`，宿主只能看到相互打架的出口。

5. 写侧缺少同批次绑定
   - `current_run.json` 与 `current_handoff.json` 由不同路径顺序写出，中间没有任何批次绑定；即使读侧统一成 snapshot，只要写侧仍然允许半写入，冷启动后仍会天然落入冲突态。

这个问题必须作为独立 Hotfix 单独立项，而不能直接并回当前 B1 子 plan，原因有三点：

1. 变更面超出当前 B1 冻结边界
   - 预计直接触达 `runtime/state.py`、`runtime/context_recovery.py`、`runtime/router.py`、`runtime/engine.py`、`runtime/handoff.py`、`runtime/_models/proposal.py` 以及对应测试。

2. 它是 B1 的前置门禁，而不是 B1 的顺手优化
   - B1 正在做 control-plane decoupling、global bundle、thin stub、diagnostics。如果带着当前状态机缺陷推进，只会把“幽灵状态”从单仓问题放大成多仓共享 runtime 的系统性问题。

3. 它决定后续测试是否可验收
   - B1 的 `doctor / status / smoke / runtime_gate` 都依赖稳定、唯一、可重复的机器事实；如果 handoff 与 run stage 继续允许对冲，B1 的验收会持续出现历史状态相关的 flaky failure。

## 核心目标
1. 收敛 checkpoint 解析入口
   - 在一次 runtime 入口里先生成唯一的 `ContextResolvedSnapshot`，Router、Engine、Handoff 只消费这一个快照，不再各自直接读状态文件。

2. 修正协商态的作用域模型
   - `current_plan_proposal` 改为严格 Session-only。
   - `current_clarification` 按生命周期分治：设计态 Session-only；开发态绑定 `owner_run_id / session_id`。
   - `current_decision` 允许合法跨 Session 恢复，但必须满足 owner/provenance 约束。

3. 修正优先级与防幽灵规则
   - 当前 Session 的 `decision / clarification` 必须高于任何全局遗留协商态。
   - 无 provenance 或 provenance 不匹配的 legacy 协商态不得参与当前路由，只能进入 Quarantine。

4. 让冲突变成可恢复状态，而不是致命异常
   - 即使进入 `state_conflict`，也必须允许用户侧“取消 / 强制取消”意图，或宿主 / Bridge 的内部 `abort_negotiation` 原语穿透进入“放弃当前协商、回到主线稳态”的逃生口。

5. 为 B1 解锁稳定前提
   - 给出明确的阻塞/并行边界，并补齐回归测试，确保 B1 后续任务不再建立在不可信的状态机之上。

6. 把不变量变成可执行门禁
   - H0 的状态矩阵、互斥规则与作用域约束不能只停留在文档里，必须落成可执行的 invariant checker / validator，并进入测试与 Loader 主链。

## 变更内容
本 plan 只处理 runtime 的“协商态与状态机一致性”，不处理 B1 的 control-plane decoupling 主体功能。范围如下：

1. 状态解析层
   - `runtime/state.py`
   - 新增或改造统一的 checkpoint resolver / loader 逻辑
   - provenance 校验、scope 判定、Quarantine 视图

2. 路由与执行层
   - `runtime/context_recovery.py`
   - `runtime/router.py`
   - `runtime/engine.py`
   - `runtime/handoff.py`
   - 消除“不同层各自读 JSON、各自合并”的分裂实现

3. 模型与 checkpoint 契约
   - `runtime/_models/proposal.py`
   - 相关 clarification / decision / handoff 模型
   - `state_conflict` 输出与内部 `abort_negotiation` 恢复契约

4. 回归测试
   - Resolver / Loader 纯函数单测
   - ghost proposal 抢路由
   - conflicting handoff / run stage
   - `resolution_id` 批次不一致
   - cold-boot 冲突脱困
   - cross-session recoverable decision
   - legacy unknown state quarantine

## 影响范围
- 核心实现面
  - `runtime/state.py`
  - `runtime/context_recovery.py`
  - `runtime/router.py`
  - `runtime/engine.py`
  - `runtime/handoff.py`
  - `runtime/_models/proposal.py`
  - `runtime/plan_proposal.py`
  - `runtime/clarification.py`
  - `runtime/decision.py`
- 预期测试面
  - `tests/test_runtime_engine.py`
  - `tests/test_runtime_decision.py`
  - `tests/test_runtime_execution_gate.py`
  - 新增或拆分 state-machine 专项测试

对当前 B1 子 plan 的影响分为两类：

1. 必须阻塞
   - 一切依赖稳定 runtime 状态语义的实现与验收：
   - `runtime gate` 的协商态恢复
   - `router / engine / handoff` 相关行为
   - `doctor / status` 若要读取或解释协商态
   - 所有基于 handoff / run stage 唯一出口的 smoke 与 regression tests

2. 允许并行
   - 纯文件系统 / manifest / payload index / thin stub 方向的 B1 结构工作，只要满足两条约束：
   - 不得 `import runtime.state`
   - 不得直接读取 `.sopify-skills/state/*.json` 参与逻辑判断

## 非目标
1. 不把本 Hotfix 并回当前 B1 子 plan 的实现面
2. 不顺手改写 `ExecutionGate`、bundle 架构、thin stub contract 或 bootstrap 逻辑
3. 不提供 `Migration Utility` 或 `prune`
4. 不把 `current_plan`、`current_run` 纳入 `abort` 清理范围
5. 不采用“发现冲突就物理删除所有旧状态”的激进自愈策略
6. 不恢复或保留 Proposal 的 global fallback 视口
7. 不在本 Hotfix 中定义 `current_run / current_handoff` 的 primary/secondary truth source
8. 不实现任何隐式物理删除、定时 GC 或批量清理 Quarantine 文件的逻辑；后续如需清理，交给专项运维/清理命令统一处理

## 当前冻结结论
截至当前实现轮次，本 Hotfix 的立项边界与状态机前提已经冻结为以下事实：

1. 本方案是独立的 pre-B1 Hotfix
   - 实施面不并回 `20260326_5-plan-20260326-phase1-2-3-plan-plan-20260326-ph`
   - 当前只处理 runtime 协商态状态机，不扩展到 B1 control-plane 主体

2. 协商态与执行真相态边界已经写死
   - `current_plan / current_run` 继续作为 stable execution truth
   - `proposal / clarification / decision` 才属于 negotiation state
   - abort / conflict cleanup 只允许处理协商态及其派生 carrier

3. 非目标已经冻结为实现约束
   - 不交付 `Migration Utility / prune`
   - 不恢复 Proposal global fallback
   - 不引入隐式物理删除、定时 GC 或批量 Quarantine 清理
   - 不在本 Hotfix 内决定 `current_run / current_handoff` 的 primary/secondary truth source

4. B1 协同规则已经冻结并反写到 B1 / program plan
   - `blocked by 20260327_hotfix` 与 `parallel-allowed` 已同步到 B1 / 总纲任务清单
   - 真实 `runtime_gate` smoke 已通过；此前被 Hotfix 门禁压住的 `runtime gate / doctor / status / smoke` 相关 B1 切片可以按依赖顺序恢复
   - 在恢复这些切片时，仍需继续遵守已冻结的 blocked/parallel-allowed 边界，不把本 Hotfix 的 scope 扩散回 B1

## 当前验收结论
本 Hotfix 当前轮次已经满足以下验收事实，可作为 `8.x` 的直接证据来源：

1. stale global proposal 不再抢占当前 Session 的明确 decision / clarification
   - Resolver 优先级已收敛为 session decision / clarification > session proposal > stable execution truth
   - global proposal 只会进入 Quarantine，不再参与当前会话 pending 路由

2. 唯一出口与冲突恢复已闭环
   - `current_handoff` 与 `current_run.stage` 的不一致会稳定进入 `state_conflict`
   - 冲突态下允许自然语言取消与内部 `abort_negotiation` 脱困
   - 用户可见文案不暴露公开 `~go abort`

3. 合法跨 Session decision 恢复已受保护
   - design / develop / execution_gate 三类 decision 的 liveness 已按 phase 分层
   - owner-bound confirmed decision 不会被误 quarantine 或误清理

4. legacy unknown state 只进入 Quarantine
   - 缺 `phase`、provenance 不完整、proposal contract 残缺或 unsupported phase 的旧文件都会被隔离
   - 它们不 adopt、不炸主流程，并已通过 `status / doctor` 暴露可见性

5. 最后两轮实现补丁已并入主链
   - `runtime_gate` 已按实际 handoff 落盘 scope 读取 global-scope `abort_conflict` 与 develop-bound checkpoint，不再误报 `current_request_not_persisted`
   - `state_conflict` 的 inspect 路径已收紧为绝对零写入，不再偷偷改写 `current_handoff/current_run/last_route`

6. 当前验证结果
   - `python3 -m compileall runtime installer tests scripts` 通过
   - `python3 -m unittest` 全量通过，结果为 `Ran 321 tests in 94.052s, OK`
   - 真实 `runtime_gate` smoke 已通过，覆盖 `state_conflict inspect -> 取消`、global-scope `abort_conflict` 与 develop-bound checkpoint

## 风险评估
- 风险: Resolver 仍然在构建快照前直接抛 Fatal，导致用户侧取消意图与宿主 / Bridge 的内部脱困原语都进不来
  - 缓解: 冲突必须产出 `is_conflict = true` 的快照，而不是直接中止进程；Router 只允许放行取消意图，宿主 / Bridge 仍可直接调用内部 `abort_negotiation`

- 风险: `abort` 误杀合法的跨 Session `unconsumed_decision`
  - 缓解: Decision 只在用户显式放弃当前协商，或宿主 / Bridge 显式调用内部 `abort_negotiation` 时、且满足 abortable 条件时才清理；合法 owner-bound 决策默认保留

- 风险: provenance 缺失的 legacy 文件被直接 adopt
- 缓解: Loader 对无 provenance / provenance 不匹配状态统一标记为 Quarantine，不参与路由

- 风险: Quarantine 或自愈策略过重，误删本可恢复的状态
- 缓解: 默认“逻辑隔离优先、物理删除最小化”；只有明确 stale 且不再可恢复的协商态才允许 tombstone

- 风险: `current_run.json` 与 `current_handoff.json` 没有同批次绑定，写侧半完成就会制造天然 split-brain
- 缓解: 由 Resolver 为每次已解析快照生成 `resolution_id`，所有派生写出必须携带同一 ID；Loader 发现 mismatch 直接进入 `state_conflict`

- 风险: Quarantine 只在磁盘里静默存在，后续 ghost 文件越积越多却没人看见
- 缓解: Quarantine 默认通过 `status / doctor` 与 handoff notes 暴露，不在每轮成功链路刷屏；同时明确本 Hotfix 不做静默清理

- 风险: B1 并行工作重新触碰旧状态读取，形成新的耦合
  - 缓解: 在本 Hotfix 中明确并行边界，B1 的并行代码只能基于文件系统与 manifest，不得依赖 runtime checkpoint

## 评分
- 方案质量: 9/10
- 落地就绪: 8/10
- 评分理由: 问题链路、边界和优先级已经清楚，H0-H5 可直接拆任务；主要复杂度在于既要修复优先级和作用域，又要保证“用户侧取消脱困 + 内部 abort 原语”、cross-session recovery 与 legacy quarantine 同时成立。
