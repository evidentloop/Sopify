# 背景: P4c Host Consumption Governance

## 前置里程碑

| 里程碑 | 核心产出 | 与本包关系 |
|--------|---------|-----------|
| P4a | Frozen External Surface keep-list（15 条） | contract 文件 schema 不可变的硬约束来源 |
| P4b | prove-kept-or-delete 全量扫描（24,334 LOC 不可大幅瘦身） | 根因：runtime 代码承载 distribution/installer contract |
| P4b.5 | 消费矩阵 + forbidden surface + blast radius + 综合裁定 | 本包的直接前驱，提供 invariant 7 + 实施项 5 + 红线 6 |
| Host Capability Governance bridge | 三级 ladder + checklist + quickstart | 已在 design.md:402-456，本包不改 ladder |

## 问题陈述

P4b.5 完成后，"新宿主该消费什么、不该碰什么"的治理结论已有，但全部停留在审计/文档层面——没有一条是机器可检查的，没有一条在代码里有执行保障：

1. **消费矩阵无机器投影**：FeatureId → 梯度映射规则不存在。系统不知道哪个 feature 属于哪个梯度、哪些是核心、哪些是 opt-in。
2. **增强组合无声明/检测机制**：宿主没有标准方式声明"我启用了接续增强"或"我是全审计宿主"。
3. **可见面仍有 leak**：output.py 渲染仍混合 forbidden surface（F5-F7）；prompt 仍可能定义 route taxonomy；doctor/status 仍可能充当 truth source。
4. **文档入口分散**：接入文档未统一到 protocol.md；builtin skill 能力边界未稳定表达。

## 目标断言

> P4c 应将 P4b.5 审计结论转化为可执行治理：宿主只消费稳定 contract，不再定义 machine truth。每条治理规则要么有机器检查投影，要么有文档/prompt 层面的显式表达。

## 本包定位

**把 P4b.5 的审计结论投影到实现层（代码/prompt/文档），使治理可执行。**

不做的事：
- 不新增/删除梯度，不改 ladder 定义
- 不新增 machine truth / state 文件 / checkpoint 类型
- 不改 P4a keep-list schema
- 不让 payload_capable 依赖 runtime/ 模块
- 不解决 P4d/P5/P6 范围

## 切片策略

P4c 体量大于 P4b.5，按实施性质和依赖关系拆为 6 个子切片（含 3a/3b + 收口项 5），不按来源拆。

| 子切片 | 名称 | 性质 | 核心交付 |
|--------|------|------|---------|
| P4c-1 | 契约投影层 | 机制设计 | FeatureId → 梯度投影矩阵 + deep_verified 最终裁定 |
| P4c-2 | 增强声明/检测层 | 机制设计 | 宿主 opt-in 增强的声明协议和检测逻辑 |
| P4c-3a | 渲染与 truth-source 收敛层 | 代码改动 | output / doctor / handoff 渲染收敛，消除 truth source 越界 |
| P4c-3b | 首接触与 prompt 收敛层 | 代码/prompt 改动 | 首接触感知 + prompt 不定义契约 + F5/F6 防泄露 |
| P4c-4 | 文档与披露层 | 文档 | protocol.md 唯一入口 + 文档递进 + builtin skill 披露 + design.md 结构整理（非阻塞） |
| P4c-5 | Prompt Asset 结构收口 | 文档/结构 | AGENTS.md / CLAUDE.md 零语义漂移的结构瘦身（非阻塞收口项） |

依赖图：P4c-1 → P4c-2 (hard)；P4c-1 → P4c-3a (weak)；P4c-3a → P4c-3b；P4c-3b ‖ P4c-4 (parallel，但 P4c-4 中依赖 AGENTS.md 最终文本的部分需 3b 稳定后收口)；P4c-3b + P4c-4 → P4c-5 (可选收口)

## 跨切片 invariant

- Forbidden surface 执行保障（A5/B5 合并）不是独立切片，而是每个切片必须遵守的 cross-cutting 约束：任何改动不得引入对 F1-F8 的新宿主依赖。

## 预算

| 维度 | 预算 |
|------|------|
| 新增 machine truth | 0（投影矩阵和增强声明是 metadata，不是 state） |
| Schema 变更 | 0（P4a keep-list 保护） |
| 新增代码 | P4c-3a output 收敛涉及实现改动；P4c-1/P4c-2 可能新增 metadata 文件或验证逻辑 |
| 文档变更 | blueprint/design.md 结构整理 + protocol 入口统一 + AGENTS.md/CLAUDE.md 更新 |
| 测试影响 | P4c-3a output 改动可能影响 output 相关测试 |
