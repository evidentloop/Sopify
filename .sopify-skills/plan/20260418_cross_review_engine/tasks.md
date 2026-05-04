---
plan_id: 20260418_cross_review_engine
feature_key: cross_review_engine
level: standard
lifecycle_state: deferred
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: false
---

# 任务清单: Cross-Review 独立内核方案

## 当前阶段目标

> **关联参考文档**：`hermes-insights.md`（Hermes Agent 架构对比洞察，持续演进；决策拍板后合并进 design.md）

本方案包关键决策已全部收敛（Q1-Q9 已拍板）：

1. ✅ 名称与定位：CrossReview / cross-review / cross_review config key
2. ✅ 独立内核与 Sopify adapter 边界：见 design.md Ownership Matrix
3. ✅ review 进入 plan 资产层：review.md 单文件，懒加载，finalize 时包含 finding snapshot
4. ✅ artifact / finding / verdict / policy schema：见 design.md 最小 Contract 附录
5. ✅ 首期集成顺序：develop 先行（Phase 1），design 为 Phase 2

> **当前状态**：Phase 1 切片可以开始拆分（config.py + schema 定义为 Slice A）。

## Phase 0 — 现状与定位收敛

- [x] 0.1 明确命名策略（已拍板：CrossReview / cross-review / verification loop / cross_review config key）
  - 已拍板：`CrossReview`（品牌）/ `cross-review`（能力名）/ `verification loop`（内核概念）/ `cross_review`（config key）
    - 产品名称
    - 用户面能力名
    - 内核模块名称
    - 配置键名称
    - 未来命令名称
  - 目标：已完成，命名体系已固化

- [x] 0.1a 整理命名备选清单（已完成：naming-options.md 评审完成，文件已归档删除）
  - 已产出 `naming-options.md`
  - 当前目标：
    - 把方法型 / 对象型 / 品牌型命名拆开
    - 不提前替用户定名
  - 目标：让后续命名评审有统一输入文档

- [x] 0.2 确认产品边界（已拍板：独立内核 + Sopify adapter 两层，见 design.md core/adapter 边界）
  - 明确它是否为：
    - 独立产品内核
    - Sopify 官方内建能力
    - 外部 skill / runtime extension
    - 上述三者的组合
  - 目标：确定仓库落点与生命周期管理策略

- [x] 0.2a 确认仓库形态是否以“未来独立仓库”为目标（已拍板）
  - 已拍板：
    - `CrossReview` 按独立产品设计，宿主中立
    - 先放个人 GitHub 孵化，core schema 稳定后再评估迁移 org
    - 不提前钉死分仓时点
  - 目标：把“独立边界”和“立即分仓”两个问题拆开

- [x] 0.2b 校验产品尺度是否保持“小而集中”（已拍板：Ownership Matrix 明确 core 不承载 gate/history/lifecycle）
  - 校验原则：
    - 不把 `CrossReview` 做成新的 workflow host
    - 不把 plan lifecycle / gate / history 主流程收进 core
    - 保持 `Sopify > CrossReview > sopify-code-review`（Q4 已拍板）
  - 目标：避免产品边界后续膨胀

- [x] 0.3 统一与现有能力的关系（已拍板：见 design.md “为什么不复用 ~compare” + Ownership Matrix）
  - 明确 `cross-review` 与以下能力的分工：
    - `multi_model`
    - `~compare`
    - `develop_quality`
    - `decision facade`
    - `execution gate`
  - 目标：避免职责重叠

- [x] 0.4 确认 `cross-review` 与 `code-review` 的层级关系（已拍板：`CrossReview > sopify-code-review`）
  - `CrossReview` 是通用 review 内核，`sopify-code-review` 是代码工件 vertical
  - Sopify 集成 CrossReview 内核，而不是直接依赖 sopify-code-review 产品壳

- [x] 0.5 确认 review 是否作为 plan 一等资产（已拍板：C 最小化方案）
  - `review.md` 单文件进入 plan（summary + verdict）
  - 不创建 `reviews/` 目录（MVP 阶段）
  - 懒加载，详情留 state/handoff
  - 后续可自然扩展到 B/A 方案

## Phase 1 — 领域模型与 contract 收敛

- [ ] 1.1 确认 artifact taxonomy
  - 候选：
    - `plan_package`
    - `task_result`
    - `code_diff`
    - `design_summary`
    - `consult_answer`
    - `command_result`
  - 目标：锁定 MVP artifact 集

- [ ] 1.2 确认 review pack schema
  - 明确必填字段：
    - task.request
    - acceptance_criteria
    - constraints
    - artifact payload
    - evidence
    - policy_context
  - 目标：后续实现时不再反复改输入 contract

- [ ] 1.3 确认 finding schema
  - 明确：
    - severity
    - category
    - evidence 形式
    - confidence 是否保留
    - reviewer source 标识
  - 目标：与 future replay / handoff / UI 兼容

- [ ] 1.4 确认 verdict schema
  - 明确：
    - `pass / concerns / block / inconclusive`
    - recommended_action
    - 与 develop_quality 的映射方式
  - 目标：形成可执行的最终裁决 contract

- [ ] 1.5 确认 review 资产 schema
  - 明确：
    - `review.md` 总览字段
    - design review 报告结构
    - task review 报告结构
    - final audit 报告结构
  - 目标：把 review 从运行时信号提升为可归档资产

## Phase 2 — 执行模型与 policy 收敛

- [ ] 2.1 确认 reviewer 策略
  - 首期是否支持：
    - 同模型 fresh session
    - 跨模型 reviewer
    - deterministic checker
  - 目标：避免 MVP 一开始做得过宽

- [ ] 2.2 确认 adjudicator 策略
  - 是否坚持确定性裁决
  - 是否允许后续引入 LLM adjudicator
  - 目标：先保稳定，再考虑复杂智能裁决

- [ ] 2.3 确认 policy model
  - 明确 advisory / required / block 的层次
  - 明确按风险标签、改动规模、测试缺失等条件自动升级 review 的规则
  - 目标：让 cross-review 成为工程 policy，而不是偶发动作

- [ ] 2.4 确认 task review 触发策略
  - 选项：
    - 每个 task 完成后默认触发
    - 仅高风险 task 触发
    - 用户手动触发 + policy 升级
  - 目标：在成本与稳定性之间找到可持续策略

## Phase 3 — Sopify 集成路径收敛

- [ ] 3.1 明确 design 集成切入点
  - plan package 完成后是否立即生成设计评审报告
  - 是否在 `confirm_execute` 前阻断
  - 是否要求 `review.md` 在 design 阶段就初始化
  - 目标：把设计评审正式纳入 plan 生命周期

- [ ] 3.2 明确 develop 集成切入点
  - task 完成后 review，还是 develop 整体结束后 review
  - review 结果写入：
    - `handoff.artifacts.cross_review_verdict`（机器事实）
    - `develop_quality.review_result`（verdict 映射）
    - `review.md`（finding snapshot + verdict 历史，懒加载）
  - 目标：先接一条最稳定主链路

- [ ] 3.3 明确 finalize 集成切入点
  - 是否在归档前强制执行 final audit
  - 是否要求 review 资产闭环后才能进 history
  - 目标：让 history 具备审计意义

- [ ] 3.4 暂缓 analyze 集成并定义前置条件
  - 只有在 design / develop 路径稳定后再评估 analyze advisory review
  - 目标：控制噪音

## Phase 4 — 实施前准备

- [ ] 4.1 评估是否需要 `full` 级方案包
  - 若 schema 与集成点稳定，再决定是否补：
    - `adr/`
    - `diagrams/`
  - 目标：在实现前把关键决策沉淀到更强文档结构

- [ ] 4.2 拆分第一版实现切片
  - 候选切片：
    - 切片 A: config + schema
    - 切片 B: core engine + CLI
    - 切片 C: repo/package split preparation
    - 切片 D: Sopify runtime adapter
    - 切片 E: develop integration
  - 目标：确认后再进入开发实施

- [ ] 4.3 确认测试策略
  - 至少覆盖：
    - config validation
    - review pack normalization
    - finding / verdict contract
    - policy decision
    - develop integration handoff
  - 目标：避免产品一开始就停留在 prompt 级实验

## 当前待讨论问题

### 已拍板

- [x] Q1: **产品品牌名确定为 `CrossReview`**，不使用 `sopify-cross-review`
  - repo slug: `cross-review`（kebab-case）
  - 品牌显示名: `CrossReview`（PascalCase）
  - 宿主中立，不绑定 Sopify 前缀

- [x] Q2: **`cross-review` 固定为用户面能力名**，`verification loop` 固定为架构内核概念名
  - `cross-review`：用户能力名 / 命令名 / README 主标题
  - `verification loop`：设计文档中描述内核运作方式的架构术语，不作为用户面命令名（类比 Claude 的 query loop）

- [x] Q3: **`cross_review` 作为新的顶层配置键**，与 `multi_model` 并列，保持 snake_case 惯例

- [x] Q9: **主品牌不保留 `sopify-` 前缀**，采用 `CrossReview` 作为独立宿主中立品牌

- [x] 仓库落点（补充决策）: **先放个人 GitHub 账号孵化**，待 core schema 稳定 / MVP 第一个集成阶段验证后，再评估迁移至 `sopify-ai` org 或独立 `crossreview` org
- [x] Q4: **`CrossReview > sopify-code-review` 确认（已拍板）**
  - `CrossReview` 是通用 review/verification 内核（总产品）
  - `sopify-code-review` 是代码工件 vertical（基于 CrossReview 的垂直产品）
  - Sopify 集成 `CrossReview` 内核，而不是直接依赖 `sopify-code-review`

- [x] Q5: **plan 资产层 = `review.md` 单文件，C 最小化方案（已拍板）**
  - 懒加载，只在第一次 review 运行后创建，不在 plan 初始化时生成
  - `review.md` 在 finalize 时必须包含 **finding snapshot**（category/severity/reason_code/description）
  - findings 在运行态留 state/handoff；finalize 时同步快照进 `review.md`；state 清理后 `review.md` 是唯一审计证据
  - 不引入 `reviews/` 子目录（Phase 1 不做）

- [x] Q6: **MVP artifact 范围 = `code_diff` only（已拍板，最小化）**
  - 首版 MVP 只支持 `code_diff` artifact
  - `plan_package` Phase 1.5，`task_result` Phase 2

- [x] Q7: **首批 Sopify 集成阶段 = develop 先行（已拍板）**
  - Phase 1: develop 集成（task 完成后触发 code_diff review → `review.md`）
  - Phase 2: design 集成（plan package 完成后触发 plan_package review → `review.md`）

### 待拍板

## 决策约束

所有核心决策（Q1-Q9）已拍板。以下约束继续有效：

- 可以继续补充背景、设计、利弊比较与 contract 草案
- 不把推荐方向写成"已确定规则"
- 不进入实现阶段
- 不把资产层结构、MVP 边界视为冻结契约

**已拍板决策约束（立即生效）**：

- 所有文档与代码注释中统一使用 `CrossReview`（品牌名）和 `cross-review`（能力名）
- Sopify `config.py` 扩展时使用 `cross_review` 作为顶层键（snake_case，不接受 `cross-review`）
- handoff artifact 字段命名使用 `cross_review_*` 前缀
- 不再使用 `sopify-cross-review` 作为产品名或 repo 名

对 `Q8` 的特别约束：

- 触发迁移条件：core schema（finding / verdict / review pack）稳定且通过第一个集成阶段验证
- 不把"立即分仓"视为当前阶段前置条件
