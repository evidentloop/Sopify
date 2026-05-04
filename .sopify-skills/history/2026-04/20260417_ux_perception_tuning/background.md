# 变更提案: UX 感知层调优

## 需求背景

通过四项目对比分析（Sopify / Superpowers / Spec Kit / HelloAGENTS），识别出 Sopify 用户体验层的三个真实问题。这些问题不涉及引擎架构或机器契约变更，仅聚焦于**用户可感知的输出和路由精度**。

### 问题 1: 知识沉淀不可见

Sopify 的核心优势是 blueprint 知识沉淀——使用越久，AI 越懂项目。blueprint 目录（project.md / design.md 等）已有完善的存储与索引机制（`kb.py` 负责 bootstrap，engine.py 的 prompt 构建负责注入），但当前 handoff 和 output 层没有显式暴露其价值——用户在交互输出中看不到"AI 记住了什么"。这导致：

- 用户不知道 Sopify 与普通 AI 编程助手的区别
- 第一个 wow moment 推迟到第二次会话（恢复时）
- 沉淀价值的复利效应无法被感知

**对比**：Superpowers 的 brainstorming 技能在首次交互就展示结构化输出（`.brainstorm/` 目录、交互式画布），wow moment 在第一分钟。Spec Kit 的 constitution 在每次交互中可见（9 条宪法始终展示在上下文中）。

### 问题 2: 路由优先级偶发误判

`router.py:classify()` 已有完整的无前缀分流链（meta_review → analyze_challenge → explain_only_override → runtime_first_guard → _is_consultation → _estimate_complexity），但存在偶发误判：

- `_is_consultation()` (L1073) 用 `_ACTION_KEYWORDS` 排除法判断——如果请求包含动作词但实际只是在问问题（如"删除操作会影响哪些表？"），可能被误分到 quick_fix 而非 consult
- `_estimate_complexity()` (L956) 中 `file_refs == 0 && has_action` 一律返回 complex (L969-970)，导致没有指定文件路径的修改请求被强制拉入 workflow 全链路
- `_should_bypass_consult_for_active_plan_followup_edit()` (L1153) 是已有的误判修补，说明 precedence 问题已经出现过

**注意**：这不是"新增自动路由"，而是调优现有优先级链的精度。

### 问题 3: 简单路由的 host-facing 输出冗余

consult/quick_fix 路由的 host-facing 输出（`output.py` L95-96, L178-179）包含大量 runtime 内部状态说明（"repo-local runtime 未执行代码修改"、"当前 runtime 不生成正文回答"），这些是面向开发者的调试信息，不是面向用户的。bootstrap 时 `kb.py:143` 的 `_project_stub()` 已经扫描 manifest 并写入 `project.md`，但首次扫描结果在 output 层没有被主动展示。

### 设计约束

1. **不改 context_recovery.py 的加载逻辑** — 它的职责是恢复状态，不是展示
2. **不新增路由分类函数** — 调优现有 `_is_consultation` / `_estimate_complexity` 的判断逻辑
3. **不改 engine.py 的执行路径** — 所有改动限制在 output/handoff/router 展示和分类层
4. **不改机器契约** — deterministic_guard / execution_gate 完全不动
5. **Graphify 前向兼容** — blueprint 摘要的数据结构和渲染逻辑需为后续 Graphify 增强器（`20260416_blueprint_graphify_integration`）预留扩展空间，不硬编码 blueprint 目录结构

## 本轮目标

三项独立可交付的 UX 改进：
1. 在 handoff artifacts + output 展示层暴露 blueprint 贡献摘要
2. 修正 router precedence 中已识别的误判场景
3. 瘦身 consult/quick_fix 的 host-facing 输出，增加首次扫描结果的展示
