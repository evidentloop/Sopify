# 蓝图路线图与待办

本文定位: 路线图全景 + 开放项与延后项。已完成里程碑仅保留一行摘要与归档指引。不替代当前 plan 的执行任务清单。

## 产品方向

> **对齐原则**：Sopify 总方向是 Protocol-first / Validator-centered / Runtime-optional。主航道的每一步都是"先 formalize protocol/validator 层契约，再让 runtime 作为参考实现消费"。不以 runtime 内部治理为驱动。蓝图变更优先做能强化证据与授权层的事，优先做能让外部宿主看懂、接入、被验证的事；AI + 单人维护应串行收敛，不同时开多条线。

## 后 P4c 执行规则

P0→P4c 主航道已全部完成。后续执行遵循以下原则：

1. **串行收敛**：未选定下一主线前，不并行开启多个会扩张 machine truth 的方向。
2. **主线依赖链**：P4d → P5 → P6 仍按依赖链推进；在前项尚未形成足够结论前，不把后项提升为正式主线。
3. **证据驱动升级**：证据型候选服务于主线但不占 P 编号；其产出是主线里程碑的升级证据，不是独立的主航道步骤。（关于硬约束 §8"新增项必须挂回现有 P 主航道"的释义：此约束要求新增开放项服务既有 P 主线，不能另起一条主航道；不等于每个开放项都必须拿一个 P 编号。）

## 已完成主航道（P0→P4c）

| 编号 | 名称 | 一行摘要 | 归档 |
|------|------|---------|------|
| P0 | Blueprint Rebaseline | 蓝图三件套 + ADR 实体化 + 削减预算表 + protocol.md v0 | git history |
| P1 | Subject Identity Binding | protocol §7 normative + Validator fail-closed + execute_existing_plan subject binding | `history/2026-05/20260504_subject_identity_binding/` |
| P1.5 | Execution Authorization Spine | 4 方案包 + 3 先行切片 + 1 桥接切片，操作化 ADR-017 ExecutionAuthorizationReceipt | `history/2026-05/20260505_p15_*` ~ `20260506_p15_*` |
| P2 | Local Action Contracts | admission contract 闭合（subject binding + delta schema + action-effect pairing） | `history/2026-05/20260506_p2_local_action_contracts/` |
| P3a | Contract-Aligned Cleanup | runtime 旧 contract 面清理 + execution routing 收敛 + dead path cleanup | `history/2026-05/20260507_p3a_contract_aligned_surface_cleanup/` |
| P3b | Perimeter Cleanup | release gate 修复 + CHANGELOG 压缩 + tests 分类 + replay 下线 + 旧概念清理 | `history/2026-05/20260508_p3b_perimeter_cleanup/` |
| P4a | External Surface Freeze | 15 条 keep-list + 20 条字段分类（纯文档） | `history/2026-05/20260509_p4a_external_surface_freeze/` |
| P4b | Runtime Surface Consolidation | prove-kept-or-delete 全量扫描，24,334 LOC，15 LOC 实删 | `history/2026-05/20260509_p4b_runtime_surface_consolidation/` |
| P4b.5 | Runtime Optionality Audit | 3 级梯度 + 消费矩阵 + blast radius + 综合裁定（纯审计） | `history/2026-05/20260510_p4b5_runtime_optionality_audit/` |
| P4c | Host Consumption Governance | 契约投影 + 增强声明 + 渲染收敛 + prompt -140 行 + protocol.md §8 唯一入口 | `history/2026-05/20260510_p4c_host_consumption_governance/` |

## 主线里程碑

### P4d: New Host Pilot

选 1 个非 deep 宿主做试点（payload_capable + 接续增强），不接完整 runtime。验证官方最低新宿主画像是否成立、P4b.5/P4c 的分层是否真正降低接入成本。

**Companion: Continuation Entry Convergence**

统一宿主级官方入口语义（Inspect Active Work / Continue Active Work / Start New Work），覆盖同宿主跨 session 与跨宿主接续。只消费现有 frozen contract，不新增 machine truth，不绑定 runtime 正则/路由实现。不规定入口语法或关键词，宿主自行选择暴露形式。有活动工作或 pending checkpoint 时 Start New Work 必须显式仲裁。当前 `~go exec` 是 Continue Active Work 的命令级实现，应被 host-level 入口语义取代。结合 P4d 非 deep 宿主试点 formalize。

- 前置：P4c ✅
- 状态：✅ 已完成 — 归档于 `history/2026-05/20260519_p4d_copilot_cli_pilot/`
- 升级判断：试点宿主走通 payload_capable + 接续增强的最小接续链路（至少 handoff 消费，常见配套为 plan binding + run state），且接续入口语义验证可行，即可声明 P4d 结论足够，评估 P5 启动

### P5: Contract Surface Shrinkage

在 P4d 验证后，按 evidence 逐项删除或降级 deep runtime 专属的 contract surface（bridge capability / manifest entry / installer bundle 项）。此时已知哪些 contract 是新宿主需要 vs 历史包袱。

- 前置：P4d ✅
- 状态：活跃 — 方案包 `plan/20260520_p5_contract_surface_shrinkage/`
- 升级判断：P4d 试点产出 keep / delete / downgrade 裁定表，覆盖所有 deep-only contract 面

### P6: Runtime Sunset / Reference Runtime

将 runtime 明确降级为 reference implementation 或 deep host hardening layer。新宿主默认走 Protocol/Convention 模式，runtime 不再承载新增产品能力。可能与 P5 合并。

- 前置：P5
- 状态：待 P5 结论
- 升级判断：P5 裁定表执行完毕，deep-only surface 削减到可维护水位

## 证据型候选（为下一主线提供升级证据，不占 P 编号）

> 以下项目服务于主线里程碑的推进判断，不是独立的主航道步骤。其产出（验证报告、试点数据、compliance 结论）是主线决策的输入。

### First-Use Adoption Proof

验证非作者用户/宿主能安装、触发、理解、走通 Sopify 首次使用链路。覆盖 install/bootstrap 文案压缩、status/doctor 用户语言化验收、scripts 用户面与维护面分离、至少一个非作者首次采用 walkthrough。前提：P4c 已确保默认路径不暴露内部 taxonomy。边界：只做首次采用证明与用户面收口，不重开 protocol/runtime 产品定位，不回头扩 machine contract。

- 前置：P4c ✅
- 服务主线：P4d（提供首次采用基线数据）
- 前置条件：GitHub Release 可用——install 脚本 `curl` / `iwr` 命令实际可执行（安装链路的物理前提）
- 最小交付证据：
  1. 至少 1 个非作者用户完成首次安装→触发→理解→走通链路的记录（含卡点与解决方式）
  2. `examples/` 包含至少 1 个可独立跟随的端到端 demo（含配置、操作步骤、预期输出）
  3. README 包含至少 1 个视觉资产（截图或 GIF），展示核心工作流的用户可感知效果（架构图不计入此项）

### Protocol Compliance Phase 2

在 Phase 1 文件断言之上，参考 Superpowers headless behavioral test 做端到端行为验证；扩展 Convention smoke 到完整最小生命周期（含 knowledge_sync / blueprint writeback）。

- 前置：P4c ✅
- 服务主线：P4d / P5（提供合规性证据）
- 最小交付证据：Convention smoke 覆盖 Convention 模式最小生命周期，全部 PASS（具体步骤在 Phase 2 开包时定义）

### 第三方宿主自助接入 Convention 证明

不指定下一个官方深适配目标，先把 Convention quickstart + compliance check 做出来，再由外部宿主自行验证接入。

- 前置：P4c ✅
- 服务主线：P4d（提供外部接入可行性证据）
- 最小交付证据：Convention quickstart 文档 + compliance check 脚本可独立运行，至少 1 个非 deep 宿主跑通

### Copilot Payload-Only Onboarding Proof

验证任意外部 repo 的 Copilot + Sopify 接入路径：(1) prompt asset 分发机制（不碰 `.github/copilot-instructions.md`）(2) 任意 repo 的 `.sopify-skills/` workspace bootstrap (3) 不涉及 `.sopify-runtime`、不进 installer mainline。P4d 验证了 repo-local 手工接入可行，本项验证面向外部项目的低摩擦 onboarding。

- 前置：P4d ✅
- 服务主线：P5（提供 payload_capable onboarding 可行性证据）
- 最小交付证据：至少 1 个非 Sopify repo 完成 Copilot + Sopify workspace 初始化并走通接续消费

### Shadow Writer Gap Analysis

评估 handoff 生产层拆分假设：Convention 模式下宿主是否需要/能够写出 canonical handoff state，还是只能消费 runtime 产出的 frozen contract。P4d S3.5 移交项。

- 前置：P4d ✅
- 服务主线：P5（决定哪些 handoff 生产面是 deep-only vs 可降级为 convention 自驱）
- 最小交付证据：Gap 分析报告，覆盖 RuntimeHandoff / RunState / DecisionState 的生产 vs 消费拆分判定

## 独立产品线

### CrossReview

独立审查内核，宿主中立。Phase 0 决策全部锁定（命名/边界/仓库形态/资产层/MVP artifact/集成顺序），Phase 1-4 待推进。与主航道无硬依赖，可独立推进。

- Registry 状态：active + governance deferred
- 详见：`plan/20260418_cross_review_engine/`
- 相关蓝图项：CrossReview Phase 4a（advisory skill 接入 develop 后审查）

## 流程与工具项

- [ ] Plan intake checklist（后续新 plan 开包时手工回答以下问题）：
  1. 主命中哪个蓝图活跃分层？主线里程碑（P4d / P5 / P6）、证据型候选（Adoption Proof / Compliance Phase 2 / Convention 证明）、独立产品线（CrossReview）？若不命中以上任一，须显式标记为"流程工具项"或"延后项"，不强行归类
  2. 这次改动定义的是 contract acceptance boundary，还是 execution strategy / implementation wave？（前者进 blueprint，后者留方案包）
  3. 是否新增、删除、替代 action / route / state / checkpoint / receipt 中的任一 machine truth？若是，对照 `design.md` 削减预算表
  4. 若涉及 legacy surface，替代 contract 是否已在 `design.md` sunset 表中对应里程碑稳定？
  5. 若影响 Core promotion rule / hard max / ownership / validator authority，须补充 ADR impact
- [ ] 补宿主级 first-hop ingress proof / diagnostics
- [ ] `~compare` shortlist facade 收敛进默认主链路
- [ ] blueprint 索引摘要更细粒度自动刷新
- [ ] history feature_key 聚合视图
- [ ] Multi-host review contract 正式化（protocol.md §7 从 informative/draft 升级为 normative）
- [ ] 方案级收敛语义操作化（risk ladder + 验证深度规则 + 多审查者冲突解决）
- [ ] 轻量化产品指标与 acceptance gate（首次上手步骤数、必需文件数、默认 workflow 必需 contract 数）
- [ ] 产品层 ↔ 实现层 contract matrix 正式化（ownership / admission / lifecycle responsibilities）
- [ ] GitHub Release pipeline 建立（首次 release 创建 + tag 规范 + install 脚本端到端验证）
- [ ] 测试套件健康基线（pass rate ≥ 99%；当前基线 717 tests / 695 passed / 22 failed = 97%）

## 已关闭 / 已吸收项

| 原项 | 处置状态 | 归因 |
|------|---------|------|
| workflow-learning 独立 helper | 终止 | P3b replay 能力下线，未来如需重设计另行评估 |
| Convention 入口兑现差距 | 已并入 | 已转入 P1.5 先行切片 |
| ~replay 更多入口 | 终止 | P3b replay 能力已下线 |
| 第三方 CLI 宿主能力边界治理（P4a→P4c bridge） | 已消费 | P4c 已消费，Host Capability Governance 已落地 design.md |

## 明确延后项

| 项目 | 复审触发 |
|------|---------|
| runtime 全接管 develop orchestrator | Runtime-optional 方向明确转向时 |
| 非 CLI 宿主图形化表单 | 有非 CLI 宿主试点需求时 |
| history 正文纳入默认长期上下文 | 上下文窗口或 KB 机制显著变化时 |
| daily index | 用户数增长到需要每日索引时 |
| runtime 独立 preferences_artifact | 偏好管理成为产品瓶颈时 |
| 偏好自动归纳/提炼 | 与 runtime 全接管/知识自动提炼方向收敛时 |
| `sopify init --minimal` 等新增 CLI 面 | Convention 入口优先通过文档/模板兑现；P4d 试点后评估 |
| 知识自动提炼（Hermes Agent 方向） | 与 Runtime-optional 张力解决后 |
| 声明式工作流引擎（Spec-Kit 方向） | 与 Runtime-optional 张力解决后 |

## 遴选决策记录

（待填写）
