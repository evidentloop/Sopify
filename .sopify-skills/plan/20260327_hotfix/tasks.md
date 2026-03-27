---
plan_id: 20260327_hotfix
feature_key: hotfix
level: standard
lifecycle_state: active
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: false
---

# 任务清单: 状态机 Hotfix（B1 前置门禁）

## 0. 立项与边界冻结
说明：先把这个 Hotfix 明确成独立前置方案，而不是继续塞进当前 B1 子 plan。完成标准是边界、依赖、非目标和并行规则全部写死。
- [x] 0.1 冻结本 plan 为独立 pre-B1 Hotfix，实施面不并回 `20260326_5-plan-20260326-phase1-2-3-plan-plan-20260326-ph`
- [x] 0.2 明确本 plan 的唯一目标是修复 runtime 协商态状态机，不顺手改 B1 control-plane 主体
- [x] 0.3 冻结非目标：不交付 `Migration Utility / prune`，不改 `current_plan / current_run` 语义，不恢复 Proposal global fallback
- [x] 0.4 明确 B1 并行硬边界：禁止 `import runtime.state`，禁止读取 `.sopify-skills/state/*.json`
- [x] 0.5 冻结本 Hotfix 不实现隐式物理删除、定时 GC 或批量 Quarantine 清理；后续清理交给专项运维/清理命令
- [x] 0.6 明确 `current_run/current_handoff` 的 primary/secondary truth source 不在本 Hotfix 决策范围内；当前只做 `resolution_id` 批次绑定与冲突检测
  上述边界已回写到 `background.md` / `design.md` 的冻结结论；本阶段只固化 Hotfix 自身边界，不提前扩写到 B1 主体实现。

## 1. H0 | 状态矩阵与不变量
说明：H0 是全链路前提。完成标准是 state matrix、优先级和互斥不变量被明确成实现契约。
- [x] 1.1 列出 `current_run / current_plan / current_plan_proposal / current_clarification / current_decision / current_handoff` 的目标作用域、owner 字段和消费阶段
- [x] 1.2 冻结“协商态 vs 执行真相态”边界：`run/plan` 不属于 abortable negotiation state
- [x] 1.3 冻结优先级：session `decision / clarification` > session `proposal` > stable execution truth；global proposal 不参与
- [x] 1.4 冻结唯一出口不变量：一次 resolved snapshot 只能落到一个 pending checkpoint 或一个 execution truth
- [x] 1.5 冻结 Quarantine 规则：无 provenance 或 provenance 不匹配的协商态进入隔离视图，不得参与路由
- [x] 1.6 将 H0 不变量落成 domain-level invariant checker / validator，并定义专用错误类型；生产路径不得用裸 `assert`
- [x] 1.7 明确同一 resolved scope 内若同时存在多个合法 pending checkpoint，直接进入 `state_conflict`，不做优先级吞并
  H0 矩阵、优先级、abortable 边界与 Quarantine 规则现已在 `design.md` 写成冻结契约，并已由 validator + resolver + 回归用例共同承接。

## 2. H1 | Loader / Resolver / Snapshot
说明：H1 的目标是把状态读取改成一次快照、一次传递。完成标准是 Router/Engine/Handoff 都不再自行散读状态。
- [x] 2.1 设计 `ContextResolvedSnapshot` 的最小字段集与不可变传递方式
- [x] 2.2 将 provenance 校验下沉到 Loader / 反序列化层，不把 owner/session 判定散落到上层
- [x] 2.3 规定 Resolver 只在入口运行一次，输出 resolved state、quarantine、conflict 和 resolution notes
- [x] 2.4 明确冲突时返回 `is_conflict = true` 的 snapshot，而不是直接抛 Fatal
- [x] 2.5 明确 Router / Engine / Output 层禁止再次直接 `get_current_*()` 作为业务判断输入
  主链业务判断已全部改为优先消费 snapshot / recovered context；`engine.py` 中剩余 `get_current_*()` 仅保留在 `_capture_planning_context` 的单次 compatibility capture，以及 abort/conflict cleanup 的清扫分支，不再参与路由、promotion、execution-confirm、handoff 或 output 的业务判定。
- [x] 2.6 将 `ContextResolvedSnapshot` 明确实现为 `@dataclass(frozen=True)`；内部集合统一使用 `tuple` / `MappingProxyType`
- [x] 2.7 为每次 resolved snapshot 生成 `resolution_id`，并定义其在派生写出链路中的传播规则
  现已将 resolver 生成的 `resolution_id` 贯通到 engine 最终 handoff、review→global promotion、develop checkpoint callback；仅 `state_conflict` 非 abort 的 legacy 兼容路径保留“不强补 resolution_id”以避免制造 mixed-presence 假冲突。
- [x] 2.8 在 Loader 中补 `phase / provenance / resolution_id` 校验与 legacy 兼容规则：缺关键字段不猜测归类，双缺失 `resolution_id` 走兼容路径，新旧混杂或 mismatch 进入 `state_conflict`

## 3. H2 | 作用域与 Provenance 收口
说明：H2 解决“谁该是 Session-only，谁允许跨 Session 恢复”。完成标准是三类协商态的 scope 被分别写清。
- [x] 3.1 将 `current_plan_proposal` 定义为严格 Session-only，并废弃 global fallback read
- [x] 3.2 将 design-phase `current_clarification` 定义为 Session-only
- [x] 3.3 将 develop-phase `current_clarification` 改为 `owner_run_id / session_id` 强绑定恢复
- [x] 3.4 为 `current_decision` 定义合法的 cross-session recovery 条件与 owner 约束
- [x] 3.5 明确 legacy unknown proposal / clarification / decision 的 Quarantine 行为与可见性
- [x] 3.6 将 decision liveness 改为按 kind / phase 分层：design-phase 看 `decision_id / checkpoint_id / owner_session_id / resume_context`，execution-gate phase 在此基础上再校验 gate 拓扑连通
- [x] 3.7 明确 `run_id` 不能单独决定 decision 存活；decision 写入必须带 `phase`，legacy decision 缺 `phase` 直接进入 Quarantine
  现已将 writer-side `phase` 校验收紧为模型内合法值集；loader 对缺失或不支持的 `phase` 统一 Quarantine，不再静默 adopt。

## 4. H3 | Router / Engine / Handoff 收敛
说明：H3 是主链修复。完成标准是不会再出现“Router 看 proposal，Handler 看不到 proposal”的链路裂缝。
- [x] 4.1 将 Router 改为只基于 snapshot 做 pending 分类，不再自行 `review or global` 拼接
- [x] 4.2 调整 pending 判断顺序，确保 `decision / clarification` 高于 `proposal`
- [x] 4.3 将 `plan_proposal_pending` handler 改为只消费 resolved proposal，不再二次散读状态文件
- [x] 4.4 将 `context_recovery.py` 改为从 snapshot 读取 active state，不再重新拉取已隔离状态
- [x] 4.5 将 Handoff 构造改为只消费 snapshot 与 effective route，保证 `required_host_action` 唯一
- [x] 4.6 增加 route/handoff/run-stage 一致性断言，命中时统一进入 `state_conflict`
- [x] 4.7 将 `current_run.json` 与 `current_handoff.json` 的派生写出绑定到同一 `resolution_id`，不再允许无批次关联的写侧结果共存
  已对 engine 最终 handoff、review→global promotion、develop checkpoint callback 全部落地 paired-write；loader 继续对 mixed-presence / mismatch 稳定收敛为 `state_conflict`。
- [x] 4.8 明确 `state_conflict` 与 `InvariantViolation` 的边界：前者用于可恢复状态冲突，后者用于实现错误或契约破坏
- [x] 4.9 将 `quarantined_items` 升级为结构化项，至少包含 `state_kind / path / reason / provenance_status`

## 5. H4 | `state_conflict` 与取消脱困原语
说明：H4 的目标是把“死锁”改成“可恢复错误”。完成标准是冲突态下仍能走通用户侧 cancel/强制取消与宿主内部 abort 原语。
- [x] 5.1 设计 `state_conflict` 的结构化输出：冲突类型、涉及状态、owner/session 摘要、允许的用户意图与内部动作
- [x] 5.2 让 Router 在 `snapshot.is_conflict = true` 时只放行取消语义，并允许宿主 / Bridge 直达内部 `abort_negotiation`；其他执行命令统一阻断
- [x] 5.3 定义内部 `abort_negotiation` 的 cleanup 范围：`proposal`、abortable `clarification`、显式放弃协商时的 abortable `decision`
- [x] 5.4 明确内部 `abort_negotiation` 禁止清理 `current_plan / current_run` 与合法 owner-bound confirmed decision
- [x] 5.5 明确 Quarantine / Tombstone 的最小化自愈规则，禁止“一次冲突清空所有 JSON”
- [x] 5.6 明确 Quarantine 默认通过 `status / doctor` 与 handoff notes 暴露，而不是每轮成功链路强提示
- [x] 5.7 写死 fallback 文案规则：用户提示只描述“取消 / 强制取消”意图，不暴露内部动作名或顶级 CLI 命令

## 6. H5 | 回归测试与验收门
说明：H5 不是收尾点缀，而是 B1 解锁门。完成标准是故障链路被稳定复现并被回归用例覆盖。
- [x] 6.1 补 Loader provenance / phase 校验纯函数单测
- [x] 6.2 补 Resolver 优先级、互斥不变量与多 pending 并存纯函数单测
- [x] 6.3 补 `resolution_id` mismatch 与 legacy 兼容纯函数单测
- [x] 6.4 补 Quarantine 结构与可见性单测
- [x] 6.5 补 `state_conflict` 与 `InvariantViolation` 分类单测
- [x] 6.6 补 `ghost global proposal + fresh session decision` 回归，断言 decision 胜出
- [x] 6.7 补 `plan_proposal_pending` 缺失 proposal 的防回归，断言不再抛裸异常
- [x] 6.8 补 cold-boot `state_conflict + 取消脱困` 回归，断言用户取消意图与宿主内部 abort 原语都可进入 cleanup
- [x] 6.9 补合法 cross-session recoverable decision 回归，断言不会被误删
- [x] 6.10 补 legacy unknown state quarantine 回归，断言不 adopt、不阻断无关主线
- [x] 6.11 补 handoff / run-stage 唯一出口回归，断言不再出现对冲 checkpoint
- [x] 6.12 补 write-side batch mismatch 回归，断言 `current_run/current_handoff` 的 `resolution_id` 不一致时稳定进入 `state_conflict`

## 7. 与 B1 的协同顺序
说明：本节不是补充说明，而是排期门禁。完成标准是哪些任务 blocked、哪些可 parallel 被写成明确执行约束。
- [x] 7.1 将当前 B1 中所有触碰 `runtime/router.py / runtime/engine.py / runtime/handoff.py / runtime gate` 的任务标记为 `blocked by 20260327_hotfix`
- [x] 7.2 将当前 B1 中所有依赖协商态唯一出口的 `doctor / status / smoke / regression` 标记为 `blocked by 20260327_hotfix`
- [x] 7.3 将 B1 中纯文件系统 / manifest / thin stub / payload index / ignore 脚手架任务标记为 `parallel-allowed`
- [x] 7.4 为并行 B1 任务增加硬约束说明：不得 `import runtime.state`，不得读取 checkpoint JSON，判断仅基于文件系统与 manifest
- [x] 7.5 约定以 H5 通过作为解除 B1 状态链路阻塞的唯一门
  当前阶段先在 Hotfix 方案包内冻结 blocked / parallel-allowed / hard-boundary 结论，作为下一步反写 B1 与 program plan 的唯一输入；不在本步骤直接改 B1 文档。

## 8. 总验收门
说明：只有全部满足，才说明本 Hotfix 可以关闭并解除 B1 主链阻塞。
- [x] 8.1 stale global proposal 不再抢占当前 Session 的明确 decision / clarification
- [x] 8.2 Proposal 不再作为 global 路由输入事实参与当前会话
- [x] 8.3 冲突态下依然可以通过自然语言取消 / 交互式 cancel 或宿主内部 abort 原语脱困，且用户文案不暴露公开 `~go abort` 命令
- [x] 8.4 `current_handoff` 与 `current_run.stage` 始终只暴露一个明确出口
- [x] 8.5 合法跨 Session recoverable decision 不会被误 quarantine 或误清理
- [x] 8.6 legacy unknown state 只进入 Quarantine，不 adopt、不炸主流程
- [x] 8.7 补一轮真实 `runtime_gate` 入口 smoke，至少覆盖 `state_conflict inspect -> 取消`、global-scope `abort_conflict`、develop-bound checkpoint
  对应实现与验证已在 `background.md` 的“当前验收结论”中汇总；当前静态/回归证据为 `python3 -m compileall runtime installer tests scripts` 通过，以及 `python3 -m unittest` 全量 `Ran 321 tests in 94.052s, OK`；真实 `runtime_gate` smoke 也已完成并收口。
