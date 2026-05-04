# 技术设计: UX 感知层调优

## 技术方案

- 核心目标：在不改动引擎执行路径和机器契约的前提下，让用户感知到 Sopify 的知识沉淀价值，并减少路由误判和输出冗余
- 改动范围限定在：`runtime/handoff.py`（artifacts 层）、`runtime/output.py`（展示层）、`runtime/router.py`（分类精度）

## 设计原则

1. **artifacts 层暴露信息，output 层格式化展示**
   blueprint 贡献信息通过 handoff artifacts 传递给宿主，output 负责渲染为用户可见的摘要。两层各自职责清晰。

2. **调优 precedence，不新增分类函数**
   router 的问题是现有分类函数的判断边界不够精确，不是缺少新的分类器。修改现有函数的内部逻辑。

3. **减少面向开发者的输出，增加面向用户的输出**
   当前 output 中有大量 "repo-local runtime 未执行…" 的调试说明，这些对用户没有价值。替换为用户关心的信息。

## A. Blueprint 贡献可见化

### A.1 handoff artifacts 增加 blueprint 摘要

在 `handoff.py:build_runtime_handoff()` (L86) 中，该函数已有 `config: RuntimeConfig`（包含 `runtime_root`，可推导 blueprint 目录路径）和 `resolved_context`。在调用 `_collect_handoff_artifacts()` 之后、构建 `RuntimeHandoff` 之前，注入 blueprint 摘要：

```python
# handoff.py — build_runtime_handoff() 中，_collect_handoff_artifacts() 之后
blueprint_summary = _extract_blueprint_summary(config)
if blueprint_summary:
    artifacts["blueprint_summary"] = blueprint_summary
```

注意：`_collect_handoff_artifacts()` (L267) 的签名不含 `resolved_context`，只接收从中拆出的各组件。因此 blueprint 提取在上层 `build_runtime_handoff()` 中进行，通过 `config.runtime_root` 定位 blueprint 目录。

`_extract_blueprint_summary()` 从 `config` 中提取：
- blueprint 目录是否存在且非空
- 直接调用 `_detect_manifests(config.workspace_root)` 获取 manifest 文件名列表（仅 7 次 `exists()` 调用，无 I/O 成本）
- 是否存在 design.md / background.md（表示已有架构决策沉淀）
- 当前活跃 plan 数量

**返回结构**：
```python
{
    "has_blueprint": True,
    "detected_manifests": ["package.json", "tsconfig.json"],
    "has_design_decisions": True,
    "active_plan_count": 2,
}
```

**改动文件**：`runtime/handoff.py` — 新增 `_extract_blueprint_summary(config)` + 在 `build_runtime_handoff()` 中调用（artifacts 注入点在 `_collect_handoff_artifacts()` 返回后）

### Graphify 兼容性约束

Graphify 方案包（`20260416_blueprint_graphify_integration`）将在后续引入：

1. **`blueprint/graphify/` 目录**：含 report.md、graph.json、graph.html
2. **auto-section 注入**：blueprint 文件中会出现 `<!-- graphify:auto:*:start/end -->` 标记
3. **`blueprint_enhancers` 配置键**：RuntimeConfig 将新增 `blueprint_enhancers: Mapping[str, Mapping[str, Any]]` 字段
4. **handoff stale/refresh 信号**：增强器可通过 handoff artifact 暴露 stale/recommended-refresh 信号

`_extract_blueprint_summary()` 的设计需要满足以下兼容性：

- **返回结构可扩展**：使用 dict 而非 frozen dataclass，方便后续增加 `enhancers` 字段
  ```python
  # 当前（无 Graphify）
  {"has_blueprint": True, "detected_manifests": [...], ...}
  # 未来（有 Graphify）
  {"has_blueprint": True, ..., "enhancers": {"graphify": {"enabled": True, "stale": False}}}
  ```
- **不假设 blueprint 目录结构**：只检查已知文件（project.md, design.md, background.md），不排斥增强器创建的子目录
- **与 `blueprint_enhancers` config 协同**：当 Graphify 启用后，`_extract_blueprint_summary()` 可从 `config.blueprint_enhancers` 读取增强器状态，在摘要中展示"知识图谱: 已启用"
- **不侵入 auto-section 命名空间**：`_extract_blueprint_summary()` 只读取文件存在性和元数据，不解析文件内容中的 auto-section 标记

### A.2 output 层展示 blueprint 摘要

在 `output.py` 的输出渲染中，当 handoff artifacts 包含 `blueprint_summary` 时，在路由/阶段信息后追加 1-3 行摘要：

```
📚 blueprint 已加载: 2 个架构决策 · package.json, tsconfig.json
💡 当前有 1 个活跃计划
```

渲染逻辑应使用 `blueprint_summary` dict 的 key 做条件判断，不硬编码字段列表——这样后续 Graphify 增加 `enhancers` 字段时，只需在渲染层追加一行（如 "🔗 知识图谱: 已启用"），不需改 handoff 层。

**改动文件**：`runtime/output.py` — 新增 blueprint 摘要渲染逻辑

### A.3 首次 bootstrap 扫描结果展示

`kb.py:bootstrap_kb()` → `_project_stub()` → `_detect_manifests()` 已经在首次创建 project.md 时扫描了 7 种 manifest。但扫描结果没有在 output 中展示。

注意：`KbArtifact` 只有 `files`（文件路径列表）、`mode`、`created_at`，不携带 manifest 列表。因此不能直接从 KbArtifact 提取扫描结果。

两个可选实现路径：
- **稳妥方案**：output 层仅展示"已初始化 project.md / blueprint index"的事实，不重复检测 manifest
- **增强方案**：在 output 层轻量调用 `_detect_manifests(config.workspace_root)` 重新扫描，渲染具体的 manifest 列表

推荐稳妥方案，因为 manifest 信息已经写入 project.md 内容中，用户可以直接查看。

```
📝 已初始化: blueprint/project.md, blueprint/preferences.md
```

**改动文件**：`runtime/output.py` — 在 kb artifact 输出区域增加首次创建文件的展示

## B. Router 精度修正

### B.1 `_is_consultation` 误判修正

**当前问题**：`_is_consultation()` (L1073-1081) 用 `_ACTION_KEYWORDS` 做排除法——只要包含动作词就返回 False。但有些请求虽然包含动作词却确实是咨询（如 "删除操作会影响哪些表？"、"如果重构这个模块需要考虑什么？"）。

**修正方向**：当句子同时满足问句特征（? / ？/ 问句前缀）和动作词时，问句特征应优先。因为用户在"问关于动作的问题"而不是"要求执行动作"。

```python
def _is_consultation(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    is_question_form = text.endswith("?") or text.endswith("？") or normalized.startswith(_QUESTION_PREFIXES)
    has_action = any(keyword.lower() in normalized for keyword in _ACTION_KEYWORDS)
    # 问句形式 + 动作词 = 咨询（问关于动作的问题）
    if is_question_form and has_action:
        return True
    if has_action:
        return False
    return is_question_form
```

**风险评估**：这会让部分以问号结尾的修改请求被分到 consult（如 "能帮我把这个函数改一下吗？"）。需要通过测试覆盖边界 case 来验证。如果边界太模糊，可以收窄条件为"问句前缀 + 动作词"而非"问号结尾 + 动作词"。

**改动文件**：`runtime/router.py` — 修改 `_is_consultation()` 内部逻辑

### B.2 `_estimate_complexity` 的 complex 默认降级

**当前问题**：`_estimate_complexity()` (L969-970) 对 `has_action && file_refs == 0` 一律返回 complex + standard plan_level。这意味着"帮我加个日志"这样的请求（有动作词、没指定文件）会被拉入 workflow 全链路。

**修正方向**：当 `file_refs == 0` 且文本长度较短（低于某个阈值）时，应该 fallback 到 medium 而非 complex。长文本+动作词+无文件引用才应该是 complex。

```python
if has_action and file_refs == 0:
    if len(text) < _SHORT_REQUEST_THRESHOLD:
        return _ComplexitySignal("medium", "Short action request without file scope", "light")
    return _ComplexitySignal("complex", "Detected change intent without bounded file scope", "standard")
```

`_SHORT_REQUEST_THRESHOLD` 需要通过现有测试回归来确定合理值（建议 80-120 字符）。

**改动文件**：`runtime/router.py` — 修改 `_estimate_complexity()` 内部逻辑

## C. Host-facing 输出瘦身

### C.1 consult/quick_fix 输出精简

**当前问题**：`output.py` L95-96 / L178-179 的 handoff 描述（如 "已识别 quick_fix 路由，当前 repo-local runtime 未执行代码修改"）是面向开发者的调试信息。

**修正方向**：将技术性描述替换为用户导向的下一步提示。保留 `_LABELS` dict 结构不变，只调整文案内容。

**改动文件**：`runtime/output.py` — 修改 `_LABELS` 中 quick_fix_handoff / consult_handoff 的文案

## 改动范围汇总

| 文件 | 改动类型 | 预估行数 |
|------|---------|---------|
| `runtime/handoff.py` | 新增 `_extract_blueprint_summary()` + 调用 | ~25 行 |
| `runtime/output.py` | blueprint 摘要渲染 + 首次扫描展示 + 文案精简 | ~40 行 |
| `runtime/router.py` | `_is_consultation()` + `_estimate_complexity()` 逻辑修正 | ~15 行 |
| `tests/` | 新增/修改测试用例 | ~60 行 |
| **总计** | | ~140 行 |

## 不改动的文件

- `runtime/engine.py` — 执行路径不变
- `runtime/context_recovery.py` — 加载逻辑不变
- `runtime/deterministic_guard.py` — 机器契约不变
- `runtime/execution_gate.py` — 执行门禁不变
- `runtime/kb.py` — bootstrap 逻辑不变（已有的扫描能力够用）
