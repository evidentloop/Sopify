# 变更提案: Blueprint 可插拔增强架构 + Graphify 首个实现

## 需求背景

Sopify 的知识资产按五层组织（L0 index → L1 stable → L2 active → L3 archive → L4 state），其中 blueprint（L1 stable）承载长期项目知识。当前 blueprint 文件完全由人工维护，存在以下痛点：

1. **模块依赖关系不可见**：project 规模增长后，代码模块间的结构关系只存在于开发者脑中，blueprint 缺乏自动化的结构可视化。
2. **plan 间隐式依赖难追溯**：多个并行 plan 可能影响同一组模块，但 blueprint 层没有跨 plan 的依赖全景图。
3. **新人上手成本高**：需要逐文件阅读 blueprint + code 才能理解项目结构。
4. **blueprint 变更影响范围难评估**：修改某模块时，无法快速评估对其他模块的影响半径。

### 架构方向：可插拔增强器

本次引入的不仅是 graphify 集成，而是一套**可插拔的 blueprint 增强器架构**：
- 统一收敛到 `blueprint_enhancers` 配置父键（一次性加入 `_ALLOWED_TOP_LEVEL`，后续增强器零改动扩展）
- 每个增强器通过 auto-section 命名空间隔离（`<!-- {name}:auto:*:start/end -->`）
- 增强器产物目录统一为 `blueprint/{enhancer.name}/`
- 增删增强器互不影响，关闭时零影响
- graphify 作为**首个具体实现**验证架构可行性

### Graphify 简介

[Graphify](https://github.com/user/graphify)（v0.4.16）是一个将文件夹转化为可查询知识图谱的工具：
- 支持 25 种语言的 AST 确定性提取（零 LLM 成本）
- 管线：`collect_files() → extract() → build_from_json() → cluster() → analyze() → generate() → export()`
- 输出：graph.json（NetworkX JSON 格式图谱）、GRAPH_REPORT.md（人类可读摘要）、graph.html（交互可视化）
- 增量更新：`detect_incremental()` 基于 mtime 比对，返回 `new_files` + `deleted_files`
- 分析：`god_nodes()`、`surprising_connections()`、`suggest_questions()`

### 已知局限（适配层需补充）

- `collect_files()` 只收代码后缀（`.py`, `.js` 等），**不收 `.md`**。plan/ 和 history/ 中的 Markdown 方案文件需要适配层额外扫描补充。但本期只保证"文档节点入图可见"，不承诺自动推断文档间依赖关系。
- graph.json 没有 schema version 字段，版本追踪需通过外部 `.meta.json` 实现。

### 集成定位

将 graphify 作为 blueprint 增强器引入，不新增知识层。通过 `blueprint_enhancers.graphify.enabled` 控制。首次运行为显式脚本调用，不挂入 bootstrap 默认流程。

## 本轮目标

1. 设计并实现 `BlueprintEnhancer` 可插拔基类 + 注册表 + auto-section 注入引擎
2. 修改 `runtime/config.py` 新增 `blueprint_enhancers` 稳定父键
3. 实现 `GraphifyEnhancer` 作为首个具体增强器（对齐 graphify 真实 API 签名）
4. 补充 plan/history .md 文档节点扫描（文件级可见性）
5. 扩展 `runtime/kb.py` 的 README 自动发现逻辑（`blueprint/*/report.md`）
6. 图谱增量迭代 + 版本兼容（fail-open + 可回退全量重建）

## 非目标

- 不新增知识层（产物收敛在 blueprint/ 内）
- 不强制依赖 graphify（关闭时零影响；graphify 是 optional enhancer dependency，不改 stdlib_only 基线）
- 不修改 graphify 本体
- 不替代 knowledge_sync 契约（增强器是增值层）
- 不引入 LLM 成本到默认流程（AST-only 模式）
- 不在本期实现其他增强器（仅预留接口）
- 不挂入 bootstrap 默认流程
- 不在本期提供结构化 stale/freshness gate（仅 finalize 可见性提示）
- 不在本期自动推断 .md 文档间依赖关系（仅文件级入图）
