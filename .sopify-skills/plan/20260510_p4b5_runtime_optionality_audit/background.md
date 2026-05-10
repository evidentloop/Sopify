# 背景: P4b.5 Runtime Optionality & Host Onboarding Audit

## 前置里程碑

| 里程碑 | 核心产出 | 与本包关系 |
|--------|---------|-----------|
| P4a | Frozen External Surface keep-list（15 条） | 本包的 forbidden surface 从 keep-list 排除面正面化 |
| P4b | prove-kept-or-delete 全量扫描，结论：24,334 LOC 不可大幅瘦身 | 根因是大量 runtime 代码承载 distribution/installer contract，引出"runtime 何时可选"的问题 |
| Host Capability Governance bridge | 三级 ladder + checklist + quickstart 定义 + prompt 治理原则 | 已落地 `blueprint/design.md:402-456`；本包不重定义梯度，只在其上补审计 |

## 问题陈述

P4b 证明了 runtime 删不动的根因，bridge 定义了三级宿主梯度——但两者之间缺少一层可操作的 **消费矩阵**：

1. 每一级宿主**到底能消费哪些 state 文件和 contract 面**，至今只有 handoff 被显式提到（`design.md:414` "可选增强"），其余主链真相文件（clarification / decision）和可审计凭证（gate_receipt / ExecutionAuthorizationReceipt）的层级位置是空白
2. **Forbidden surface 只有隐式表述**（`design.md:366` "未列入面默认可删"），新宿主无法从正面清单推导出"禁止触碰什么"
3. **接续锚点与授权凭证混在一起讲**——handoff 只回答"接下来做什么"，gate_receipt 回答"为什么被授权"，ExecutionAuthorizationReceipt 是协议级授权语义。三者消费层级不同，但现有文档没有分开归位
4. P4c 多项验收条件（`tasks.md:76-80`）的执行边界取决于本包的审计结论

## 目标断言（待审计证明）

> P4b.5 应证明：在 runtime-optional / runtime sunset 路线下，新宿主不接完整 runtime 也应能基于显式知识资产与冻结 session contract 继续知道该做什么并安全接班；但该能力不是 payload_capable 的默认最低准入，而是 payload_capable 内部若干 opt-in 增强组合的结果。具体增强档位、依赖链、必选项与禁止项，由 P4b.5 审计裁定。

背景要点：
- 蓝图大方向已明确往 runtime sunset 走（P4d 验证不接 runtime 的新宿主，P6 将 runtime 降为 reference implementation）
- 但 payload_capable 的现有 ladder 下限只到"payload 安装 + prompt asset 消费"，handoff 仍是 opt-in 增强（design.md:414, 417）
- 因此"新宿主能安全接续"不能直接等于"payload_capable 的最低准入能力"——它是同层内的可选能力组合
- P4b.5 不预设哪些增强是必选，而是通过审计裁定

## 本包定位

**审计现有 bridge 的消费面归位，为 P4c 划定可执行边界。**

- 不重定义三级梯度（已有）
- 不改代码 / schema / FeatureId 投影（属 P4c）
- 不新增 machine truth
- 产出物：consumption matrix + forbidden surface + blast radius 审计 + P4c boundary statement

## 预算

| 维度 | 预算 |
|------|------|
| 新增代码 | 0 LOC |
| 新增 machine truth | 0 |
| 文档变更 | blueprint/design.md 补充审计结论；方案包 3 件套 |
| 测试影响 | 无（不改代码） |
