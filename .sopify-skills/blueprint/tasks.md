# 蓝图路线图与待办

本文定位: 路线图全景 + 未完成长期项与明确延后项。已完成里程碑仅保留一行摘要与归档指引。不替代当前 plan 的执行任务清单。

## 执行优先级（已确认）

以下顺序是硬约束。前一项未稳定前，不进入后一项实现。

> **对齐原则**：Sopify 总方向是 Protocol-first / Validator-centered / Runtime-optional。主航道的每一步都是"先 formalize protocol/validator 层契约，再让 runtime 作为参考实现消费"。不以 runtime 内部治理为驱动。蓝图变更优先做能强化证据与授权层的事，优先做能让外部宿主看懂、接入、被验证的事；AI + 单人维护应串行收敛，不同时开多条线。

> **先行切片例外**：以下两类改动不受上述顺序约束：① 已在后续里程碑描述中显式标注"可先行"的 presentation-only 切片；② 已证明不影响 protocol / validator / runtime machine contract 的纯展示层改动。除此之外，任何涉及契约面的工作必须等前置里程碑稳定。

> **结构重构锚点**：跨 contract 的模块拆分与 legacy control surface 收口应与里程碑同步——P1 后优先 subject resolution / plan lookup 统一入口（✅），P1.5 后优先 authorization policy / gate-receipt 收敛（✅），P2 后优先 action contract adapter 统一（✅），P3a sunset 表最终清理（✅）。engine.py / decision_tables.py 系统拆分属于 P4b（runtime_surface_consolidation），需 P4a 外部消费面冻结后执行。不阻止与上述 contract 无关且不改变 machine truth 的低风险整理。

| 优先级 | 任务 | 前置条件 | 说明 |
|--------|------|---------|------|
| P0 | Blueprint rebaseline | 无 | 已完成。重写 blueprint，实体化 ADR，定义削减目标 |
| P1 | subject_identity_binding | P0 | 已完成。protocol / validator / runtime 三联动定义"操作的是谁" |
| P1.5 | execution_authorization_spine | P1 | 已完成。操作化 ADR-017 ExecutionAuthorizationReceipt，规划授权链路 |
| P2 | local_action_contracts | P1.5 | 已完成。在主体已绑定前提下收敛局部动作 contract |
| P3a | contract_aligned_cleanup | P2 | 已完成。以 protocol/validator 已稳定为前提，清理 runtime 旧 contract 面 |
| P3b | perimeter_cleanup | P3a | 已完成。外围面清理：release gate 修复、CHANGELOG 去文件列表化、tests 分类、旧概念清理 |
| P4a | external_surface_freeze | P3b | 已完成。薄切片：冻结不可删外部消费面 keep-list |
| P4b | runtime_surface_consolidation | P4a | 已完成。prove-kept-or-delete 证明 <20K 不可达，实删 15 LOC |
| P4b.5 | runtime_optionality_audit | P4b | 已完成。设计/审计型：宿主接入层级矩阵 + 消费矩阵 + blast radius + 综合裁定 |
| P4c | host_consumption_governance | P4b.5 | 宿主只消费 contract，不定义 truth |

### P0: Blueprint Rebaseline（已完成）

✅ 已完成。重写 blueprint 三件套、实体化 ADR、定义削减预算表、落地 protocol.md v0。细节见 git history。

### P1: Subject Identity & Existing Plan Binding（已完成）

✅ 已完成（归档：`history/2026-05/20260504_subject_identity_binding/`）。protocol §7 subject identity 升格 normative、Validator admission fail-closed、execute_existing_plan subject binding。P1 语义债（DECISION_REJECT consult 伪装）在 P1.5-A 收口。

### P1.5: Execution Authorization Spine（已完成）

✅ 已完成（4 方案包 + 3 先行切片 + 1 桥接切片）。归档：`history/2026-05/20260505_p15_*` ~ `20260506_p15_*`

### P2: Local Action Contracts on Bound Subjects（已完成）

✅ 已完成。admission contract 闭合（subject binding + delta schema + action-effect pairing）。归档：`history/2026-05/20260506_p2_local_action_contracts/`

### P3a: Contract-Aligned Surface Cleanup（已完成）

✅ 已完成。runtime 旧 contract 面清理 + execution routing 收敛 + knowledge_sync audit trail + dead path cleanup。Runtime 结构性减重（26K→<20K）剥离为 P4b。归档：`history/2026-05/20260507_p3a_contract_aligned_surface_cleanup/`

### P3b: Perimeter Cleanup（已完成）

✅ 已完成。Release gate 修复、CHANGELOG 压缩、tests 分类标注、replay/workflow-learning 下线、README 首屏降噪、旧概念清理。归档：`history/2026-05/20260508_p3b_perimeter_cleanup/`

### P4a: External Surface Freeze（已完成）

✅ 已完成。Frozen External Surface keep-list（15 条）+ Output Rendering Audit（20 条字段分类 + 5 个已知热点）。纯文档变更，不写运行代码。归档：`history/2026-05/20260509_p4a_external_surface_freeze/`

### P4b: Runtime Surface Consolidation（已完成）

✅ 已完成。prove-kept-or-delete 全量扫描证明 runtime 在当前 contract 约束下已接近最小可行体积（24,334 LOC）。<20K 目标在不改 distribution/installer contract 的约束下不可达。交付物：Phase 0 test re-audit（653 hard / 31 soft gate）、Phase 1 CI/preflight 真实降载、Phase 2 全量死代码扫描（15 LOC 删除）。归档：`history/2026-05/20260509_p4b_runtime_surface_consolidation/`

### P4b.5: Runtime Optionality & Host Onboarding Audit（已完成）

✅ 已完成。设计/审计型，不改代码。交付物：S1 Forbidden Surface（F1-F8）、S2 消费矩阵 + opt-in 增强组合 + 官方接入画像、S3 Blast Radius 审计（15 功能区 + 语义来源→落盘→contract 映射）、S4 综合裁定 + P4c 前提声明。归档：`history/2026-05/20260510_p4b5_runtime_optionality_audit/`

### P4c: Host Consumption Governance

宿主只消费稳定 contract，不再定义 machine truth。P4b.5 宿主接入层级矩阵就绪后执行。

- prompt 不定义机器契约、不维护路由表
- doctor/status 输出只渲染 machine truth，不作为 truth source
- handoff rendering 只消费结构化字段，不做语义推断
- 接入文档以 protocol.md 为唯一合规入口
- **宿主消费边界**：宿主只允许消费"主链机器真相"层（current_run/current_plan/current_handoff/current_clarification/current_decision）和"可审计凭证"层（gate_receipt/archive_receipt）；不得消费 state/sessions/* 内部细节、last_route 等 runtime-only/derived 面（参照 design.md "Persistence Surface 分层"表）
- **验收 (a) 文档递进顺序**：渐进式披露 Layer 0 Protocol ≤120 行 → Layer 1 Gate → Layer 2 Phase → Layer 3 Reference（不进 prompt）
- **验收 (b) 运行时首接触感知**：新用户首次使用时，只感知到"中断可恢复"和"需要拍板时会停"两个语义；blueprint / checkpoint taxonomy / runtime state 等内部概念不在默认运行时路径中主动暴露。doctor/status 不主动呈现 checkpoint 分类体系，~go 入口不前置 blueprint 概念
- **Output contract convergence**：基于 P4a 审计分类，收敛 `runtime/output.py` 渲染层——① 状态符语义：定义 canonical route family → 符号映射（当前 consult=`!` 无明确约束）；② Next 降级：明确为 human hint，不再混合 `required_host_action` + `route_name` 推导，宿主消费 handoff 不依赖 Next；③ Changes 重定义：`loaded_files`（恢复上下文）从 Changed（实际写入）中拆出，或重命名为 Touched/Files；④ Gate 行简化：默认输出不暴露 `gate_status`/`blocking_reason`/`plan_completion` 三元组，详细诊断留给 doctor/status
- **Builtin skill capability disclosure**：宿主文案稳定表达 builtin skill 的当前能力边界与可消费方式；AGENTS.md 只做消费投影，builtin_catalog 为唯一 truth source。当前 analyze/design/develop 是 phase-bound workflow skill（entry_kind=null, triggers=[]），不宣称 standalone invocation。若后续要支持 builtin skill 显式单独调用，必须先 formalize 独立的 invocation metadata contract / invocation syntax；在该 contract 明确前，本项只做披露，不预设其进入 P2 或单列里程碑。边界：只覆盖 builtin skill，不扩展到外部 skill discovery/routing/distribution（background.md 明确排除）

**P4c 前提声明（来自 P4b.5 S4 审计）**

> 以下三部分基于 P4b.5 S1-S3 审计结论提取。P4c 开包时消费此声明，不重新证明已审计项。

**P4c 可以假设的 invariant**

1. **Forbidden surface 已定义**（design.md F1-F8）：state/sessions/\*、last\_route、route taxonomy、Next:/输出文案、渲染层实现、runtime 内部模块边界均为 forbidden surface，适用所有三级梯度。P4c 的任何实施项不得引入对这些面的新宿主依赖。
2. **消费矩阵已裁定**（design.md S2 四子表）：convention\_only 和 payload\_capable 的每项 contract 文件归位（required/optional/forbidden）已确定。deep\_verified 列部分项标为"预期 required†"，待 P4c 最终裁定。P4c 直接消费此矩阵，不重新审计层级归位。
3. **三级 ladder 不变**（design.md L409-419）：convention\_only / payload\_capable / deep\_verified 的准入定义不因 P4c 改变。payload\_capable 准入仍为"payload 安装 + prompt asset 消费"。
4. **payload\_capable 对 runtime/ 的 blast radius 为零**（design.md S3 结论 2）：payload\_capable 不需要运行任何 runtime/ 模块。消费冻结 contract 文件不等于依赖生产者模块。
5. **生产者 vs 消费者边界明确**（design.md S3 语义来源表）：7 个 contract 文件的语义来源已映射，全部经 state.py 统一落盘。P4c 可以改变生产者实现，不能改变 contract 文件 schema（P4a keep-list 保护）。
6. **官方接入画像已定义**（design.md S2）：官方最低接入 = payload\_capable + 接续增强全组；对话式/全审计宿主在此基础上叠加。此画像是独立于 ladder 的接入策略层。
7. **EAR @ convention\_only = forbidden 已闭合**（design.md S2 消费矩阵）：convention\_only 不承诺消费协议级 receipt 实例语义。此裁定不在 P4c 重新开放。

**P4c 需做的实施项（由 P4b.5 推导）**

1. **机器可检查投影矩阵**：将消费矩阵中的层级归位翻译为可执行的 FeatureId → 梯度映射规则（design.md L419 已预告此项属 P4c）。
2. **增强检测机制**：P4c 需定义宿主如何声明/检测已激活的 opt-in 增强组合（接续/交互/审计）。当前无此机制，ladder 只定义准入面。
3. **Output 渲染层收敛**：消除 forbidden surface F5（Next: 输出文案推导逻辑）和 F6（渲染层实现细节）中被新宿主事实上依赖的泄露。对应 P4c 已有的 Output contract convergence 项。
4. **deep\_verified "预期 required†" 最终裁定**：消费矩阵中 deep\_verified 列的"预期 required†"项需在 P4c 做最终 required/optional 裁定。P4b.5 只做审计判断，不替代最终裁定。
5. **Forbidden surface 执行保障**：P4c 需确保 F1-F8 中的每一项在实现层有对应的防泄露措施（如移除 prompt 中的 route\_name 直接暴露、收敛 Next: 推导逻辑等）。

**P4c 不能做的事（红线）**

1. **不改 ladder 定义**：不修改三级梯度的准入条件，不新增/删除梯度。
2. **不新增 machine truth**：不新增 state 文件、不新增 checkpoint 类型、不新增 contract 文件。若确需新增，须走 ADR 路径并对照削减预算表。
3. **不改 P4a keep-list schema**：contract 文件的 schema 由 P4a 冻结面保护。P4c 可以改变生产者实现，不能改变 contract 文件结构。
4. **不让 payload\_capable 依赖 runtime/ 模块**：这是 S3 的核心审计结论。任何 P4c 实施项如果引入 payload\_capable 对 runtime 模块的运行依赖，视为违反 P4b.5 审计边界。
5. **不消费 forbidden surface**：P4c 实施项不得引入对 F1-F8 中任何面的新宿主依赖。消除已有泄露是 P4c 的目标，不是引入新泄露。
6. **不解决 P4d/P5/P6 范围**：P4c 不预设新宿主试点（P4d）、不预执行 contract surface 删减（P5）、不预判 runtime 降级路径（P6）。

**P4c 收口附带：design.md 结构整理**

> P4c 收口时，将 design.md Host Capability Governance 节中 P4b.5 的增量段（S1-S4）内化为稳定章节结构（Forbidden Surface / Consumption Matrix / Official Onboarding Profile / Blast Radius / Comprehensive Verdict）。此整理不改变观点，只优化文档结构，避免后续里程碑继续无限追加 S 段。

## 未完成长期项

### P4b 后续路线（P4c 后视评估）

- [ ] P4d New Host Pilot：选 1 个非 deep 宿主做试点（convention_only 或 payload_capable），不接完整 runtime。验证 P4b.5/P4c 的分层是否真正降低接入成本。可与 P4c 后期并行启动。
- [ ] P5 Contract Surface Shrinkage：在 P4d 验证后，按 evidence 逐项删除或降级 deep runtime 专属的 contract surface（bridge capability / manifest entry / installer bundle 项）。此时已知哪些 contract 是新宿主需要 vs 历史包袱。
- [ ] P6 Runtime Sunset / Reference Runtime：将 runtime 明确降级为 reference implementation 或 deep host hardening layer。新宿主默认走 Protocol/Convention 模式，runtime 不再承载新增产品能力。可能与 P5 合并。

### 其他长期项

- [ ] 补宿主级 first-hop ingress proof / diagnostics
- [ ] `~compare` shortlist facade 收敛进默认主链路
- [-] `workflow-learning` 独立 helper 与更稳定 replay retrieval → P3b replay 能力下线后，未来如需重设计另行评估
- [ ] blueprint 索引摘要更细粒度自动刷新
- [ ] history feature_key 聚合视图

- [ ] CrossReview Phase 4a：advisory skill 接入 develop 后审查
- [ ] Plan intake checklist（在 intake 模板/脚本落地前，后续新 plan 开包时手工回答以下问题）：
  1. 主命中哪个蓝图里程碑（P4b.5 / P4c / P4d / P5 / P6）？若不命中主线，须显式标记为"长期项"或"延后项"，不强行归类
  2. 这次改动定义的是 contract acceptance boundary，还是 execution strategy / implementation wave？（前者进 blueprint，后者留方案包）
  3. 是否新增、删除、替代 action / route / state / checkpoint / receipt 中的任一 machine truth？若是，对照 `design.md` 削减预算表
  4. 若涉及 legacy surface，替代 contract 是否已在 `design.md` sunset 表中对应里程碑稳定？
  5. 若影响 Core promotion rule / hard max / ownership / validator authority，须补充 ADR impact
- [ ] Multi-host review contract 正式化（protocol.md §7 从 informative/draft 升级为 normative）— 部分由 P1 subject identity 升格推进
- [ ] 方案级收敛语义操作化（risk ladder + 验证深度规则 + 多审查者冲突解决）
- [ ] 轻量化产品指标与 acceptance gate（首次上手步骤数、必需文件数、默认 workflow 必需 contract 数）
- [-] Convention 入口兑现差距 → 已转入 P1.5 可先行切片，非落地完成
- [ ] 产品层 ↔ 实现层 contract matrix 正式化（ownership / admission / lifecycle responsibilities）
- [ ] Protocol Compliance Phase 2：在 Phase 1 文件断言之上，参考 Superpowers headless behavioral test 做端到端行为验证；扩展 Convention smoke 到完整最小生命周期（含 knowledge_sync / blueprint writeback）。外部启发：Superpowers headless Claude 测试，准入 T1 Adoption。_触发条件：P4c 验收通过后评估是否提升为里程碑_
- [ ] 第三方宿主自助接入 Convention 证明：不指定下一个官方深适配目标，先把 Convention quickstart + compliance check 做出来，再由外部宿主自行验证接入。_触发条件：P4c 验收通过后评估是否提升为里程碑_
- [-] 第三方 CLI 宿主能力边界治理（P4a→P4c bridge）：已设计，待 P4c 消费。Host Capability Ladder（3 级 canonical 梯度）、接入判定 Checklist、Convention Quickstart 最小交付面、Prompt 镜像治理原则已落地 → `blueprint/design.md` Host Capability Governance 节。_P4c 消费该结论。_
- [ ] First-Use Adoption Proof：验证非作者用户/宿主能安装、触发、理解、走通 Sopify 首次使用链路。覆盖 install/bootstrap 文案压缩、status/doctor 用户语言化验收、scripts 用户面与维护面分离、至少一个非作者首次采用 walkthrough。前提：P4c 已确保默认路径不暴露内部 taxonomy。边界：只做首次采用证明与用户面收口，不重开 protocol/runtime 产品定位，不回头扩 machine contract，不把维护者脚本整理泛化成大规模重构。语义方向待收窄（External Adoption Proof 或 User-Facing Onboarding Convergence），编号待定。_触发条件：P4c 验收通过后评估是否提升为里程碑_

## 明确延后项

- [-] runtime 全接管 develop orchestrator
- [-] 非 CLI 宿主图形化表单
- [-] history 正文纳入默认长期上下文
- [-] daily index
- [-] ~replay 更多入口 → P3b replay 能力已下线
- [-] runtime 独立 preferences_artifact
- [-] 偏好自动归纳/提炼
- [-] `sopify init --minimal` 等新增 CLI 面（Convention 入口优先通过文档/模板兑现）
- [-] 知识自动提炼（Hermes Agent persistent memory + curator 方向，T0 Reference；与 runtime 全接管、偏好自动归纳有直接张力）
- [-] 声明式工作流引擎（Spec-Kit YAML workflow engine 方向，T0 Reference；与 Runtime-optional 有张力）
