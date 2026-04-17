# 技术设计: Blueprint 可插拔增强架构 + Graphify 首个实现

## 技术方案

- 核心目标：为 blueprint 层引入**可插拔增强器（Enhancer）架构**，graphify 作为首个具体实现
- 本方案定位：本期交付 graphify enhancer；架构层面预留其他 enhancer 的扩展能力

## 设计原则

1. **插拔式增强**
   blueprint 增强器是可选模块，开关关闭时零影响。架构支持后续接入其他增强器，不需改核心流程。

2. **极简用户面**
   用户只需设置 `blueprint_enhancers.graphify.enabled: true`。每个增强器最多暴露一个 `enabled` 开关，全部收敛在 `blueprint_enhancers` 父键下。

3. **auto-section 命名空间隔离**
   每个增强器拥有自己的 auto-section 前缀（`{name}:auto:*`），互不干扰。同一增强器可在同一文件中写入多个 auto-section。

4. **graphify 本体不改**
   所有适配逻辑在 sopify 侧。通过 graphify 的公开 API 做契约面。

5. **降级优于崩溃**
   增强器依赖未安装时跳过，字段缺失时 fallback。

## 配置形态

### 用户面

```yaml
# sopify.config.yaml
blueprint_enhancers:
  graphify:
    enabled: false
```

> **设计选择**：使用 `blueprint_enhancers` 稳定父键。
>
> 原因：当前 `runtime/config.py:53` 的 `_ALLOWED_TOP_LEVEL` 是白名单机制，
> 每加一个增强器就要改白名单，和"可插拔"矛盾。统一到 `blueprint_enhancers`
> 子键后，只需加一次 `"blueprint_enhancers"` 到白名单，后续增强器零改动扩展。

### config.py 改动

```python
# runtime/config.py

_ALLOWED_TOP_LEVEL = {
    "brand", "language", "output_style", "title_color",
    "workflow", "plan", "multi_model", "advanced",
    "blueprint_enhancers",  # 新增
}

_ALLOWED_ENHANCER_KEYS = {"enabled"}

def _validate_blueprint_enhancers(enhancers: dict) -> None:
    """验证 blueprint_enhancers 子配置。不限制增强器名（可插拔）。"""
    if not isinstance(enhancers, dict):
        raise ConfigError("blueprint_enhancers must be a mapping")
    for name, cfg in enhancers.items():
        if not isinstance(cfg, dict):
            raise ConfigError(f"blueprint_enhancers.{name} must be a mapping")
        unknown = set(cfg.keys()) - _ALLOWED_ENHANCER_KEYS
        if unknown:
            raise ConfigError(f"Unknown key(s) in blueprint_enhancers.{name}: {unknown}")
```

增强器名不做白名单限制。未注册的名字被忽略（不报错）。

### RuntimeConfig 取值链路

当前 `load_runtime_config()` (config.py:104) 返回 frozen `RuntimeConfig` dataclass，
所有字段在构造时展开。`blueprint_enhancers` 是新增的嵌套配置，有两种落地方式：

**方案 A（推荐）**：给 RuntimeConfig 加 `blueprint_enhancers` 字段

```python
# runtime/_models/core.py — RuntimeConfig 新增字段
@dataclass(frozen=True)
class RuntimeConfig:
    ...
    blueprint_enhancers: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

# runtime/config.py — load_runtime_config() 构造时传入
return RuntimeConfig(
    ...
    blueprint_enhancers=merged.get("blueprint_enhancers", {}),
)
```

- 优点：编排脚本直接 `config.blueprint_enhancers`，类型安全
- 改动：RuntimeConfig + load_runtime_config 各加一行

**方案 B**：编排脚本独立读 raw config

```python
# scripts/blueprint_enhance.py — 不走 RuntimeConfig
from runtime.config import _load_config_file
raw = _load_config_file(workspace / "sopify.config.yaml")
enhancers_cfg = raw.get("blueprint_enhancers", {})
```

- 优点：零改动 RuntimeConfig
- 缺点：绕过验证链路，未来维护时 config 路径可能分叉

> **本方案选择 A**。`blueprint_enhancers` 是稳定父键，进入 RuntimeConfig 后
> 所有消费者（编排脚本、finalize 提示等）都走同一条链路。

## graphify 依赖策略

### 定位

graphify 是 **optional enhancer dependency**，不是 sopify runtime hard dependency。
当前 sopify-skills runtime 明确宣称 `stdlib_only=True, runtime_dependencies=[]`
（runtime/manifest.py:139），这个基线不变。

### 分层策略

| 场景 | 安装方式 | 说明 |
|---|---|---|
| 本地开发联调 | `pip install -e /path/to/graphify && pip install graspologic` | editable + Leiden，联调效率最高 |
| 团队/CI/正式环境 | `pip install graphifyy[leiden]==0.4.16` | PyPI pinned + Leiden，可复现。**仅当不依赖本地未发布修复时 CI 跟 PyPI 走** |
| 临时调试 | import path hack | **不作为正式接入路径** |

### 兼容性契约（两层分离）

| 契约 | 适用范围 | 约束 |
|---|---|---|
| **runtime contract** | sopify runtime（IDE 宿主侧） | 不依赖 graphify/leiden，**不受 Python <3.13 限制** |
| **artifact generation contract** | 生成 tracked `report.md` 的执行环境（本地 / CI） | Python 3.11/3.12 + `graphifyy[leiden]==0.4.16` |

> 两层分离原则：optional enhancer 的第三方依赖不反向约束 sopify runtime 基线。

**CI 硬约束**：不满足 Python 3.11/3.12 + Leiden → 编排脚本直接报错退出。
**本地软约束**：允许 fallback Louvain，但输出必须标出 `cluster_backend=louvain`，
防止误提交与 CI 不一致的 report.md。

### leiden extras 注意

graphify 的 `cluster()` 使用 Leiden 算法（`graspologic.partition.leiden`，
定义在 `graphify/cluster.py:31`）。这是 optional extra：

```toml
# graphify pyproject.toml
leiden = ["graspologic; python_version < '3.13'"]
```

**两级可用性**：

| 级别 | 条件 | 聚类行为 | 报告质量 |
|---|---|---|---|
| **base 可用** | graphify 已安装（无 leiden extra） | fallback 到 networkx Louvain | 可用但聚类质量较低 |
| **最佳效果可用** | graphify + `graspologic` 已安装 | Leiden 算法 | 最佳聚类质量 |

> `is_available()` 只检查 base 可用性。leiden extra 缺失不阻塞 enhancer 启用，
> 但编排脚本应在输出中提示聚类质量差异。

> **⚠️ 安装档位一致性**：如果 `report.md` 进入版本管理，所有环境（本地 / CI / 团队成员）
> **必须统一到同一安装档位**（同时有 Leiden 或同时没有）。否则本地走 Leiden、CI 走
> Louvain，图谱和报告的聚类结果会不可复现。编排脚本输出应包含当前聚类后端标识
> （`leiden` / `louvain`），便于 review 时发现环境漂移。

推荐安装：
```bash
pip install graphifyy[leiden]==0.4.16   # PyPI + Leiden
pip install -e /path/to/graphify && pip install graspologic  # editable + Leiden
```

> **注意**：`graspologic` 要求 `python_version < 3.13`。Python 3.13+ 环境
> 会自动 fallback 到 Louvain。

### is_available() 策略链

```python
_DETECT_STRATEGIES = [
    ("pkg", "graphifyy"),    # PyPI 安装
    ("pkg", "graphify"),     # editable install 可能用不同包名
    ("import", "graphify"),  # fallback
]
```

无论哪种安装方式，策略链都能检测到。

## 可插拔增强器架构

### 核心抽象

```python
# installer/blueprint_enhancer.py（新增）

from pathlib import Path
from abc import ABC, abstractmethod

class BlueprintEnhancer(ABC):
    """可插拔的 blueprint 增强器基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """增强器标识符。
        用于：config key (`blueprint_enhancers.{name}.enabled`)
              auto-section 前缀 (`<!-- {name}:auto:{section_id}:start/end -->`)
              产物子目录 (`blueprint/{name}/`)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查依赖是否已安装且版本兼容。"""
        ...

    @abstractmethod
    def generate(self, repo_root: Path, output_dir: Path) -> dict:
        """全量生成。返回结构化结果供 render_auto_sections 使用。"""
        ...

    @abstractmethod
    def update(self, repo_root: Path, output_dir: Path) -> dict:
        """增量更新。无法增量时内部自动 fallback 到 generate。"""
        ...

    @abstractmethod
    def render_auto_sections(self, result: dict) -> dict[str, dict[str, str]]:
        """返回 {filename: {section_id: markdown_content}}。

        同一增强器可在同一文件中写入多个 auto-section。
        例如：
        {
            "background.md": {
                "codebase-overview": "...",
            },
            "design.md": {
                "architecture": "...",
                "module-stats": "...",
            },
        }
        """
        ...

    def ensure_output_excluded(self, repo_root: Path, output_dir: Path):
        """确保增强器自产物不被自身的增量检测扫描到。

        增强器通用约定——每个增强器在 generate()/update() 前应调用此方法
        （或自行实现等效逻辑），避免"自产物触发自身再次更新"的反馈循环。

        默认实现为 no-op；具体增强器按自身检测工具的约定 override。
        例如 GraphifyEnhancer 通过 .graphifyignore 实现。
        """
        pass
```

### 增强器注册表

```python
ENHANCER_REGISTRY: dict[str, type[BlueprintEnhancer]] = {}

def register_enhancer(cls: type[BlueprintEnhancer]):
    instance = cls()
    ENHANCER_REGISTRY[instance.name] = cls
    return cls

def get_enabled_enhancers(config: RuntimeConfig) -> list[BlueprintEnhancer]:
    enhancers_cfg = config.blueprint_enhancers
    result = []
    for name, cls in ENHANCER_REGISTRY.items():
        if enhancers_cfg.get(name, {}).get("enabled", False):
            instance = cls()
            if instance.is_available():
                result.append(instance)
            else:
                import warnings
                warnings.warn(f"Enhancer '{name}' enabled but dependencies not available")
    return result
```

### auto-section 注入引擎

```python
import re

def inject_auto_sections(
    blueprint_dir: Path,
    enhancer: BlueprintEnhancer,
    sections: dict[str, dict[str, str]],
) -> list[str]:
    """将渲染结果注入 blueprint 文件的 auto-section。

    sections 结构：{filename: {section_id: content}}
    匹配标记：<!-- {enhancer.name}:auto:{section_id}:start/end -->
    手写区域永远不碰。
    """
    modified = []
    prefix = re.escape(enhancer.name)
    for filename, section_map in sections.items():
        filepath = blueprint_dir / filename
        if not filepath.exists():
            continue
        text = filepath.read_text(encoding="utf-8")
        changed = False
        for section_id, content in section_map.items():
            escaped_id = re.escape(section_id)
            pattern = re.compile(
                rf"(<!-- {prefix}:auto:{escaped_id}:start -->)\n.*?\n(<!-- {prefix}:auto:{escaped_id}:end -->)",
                re.DOTALL,
            )
            new_text = pattern.sub(rf"\1\n{content}\n\2", text)
            if new_text != text:
                text = new_text
                changed = True
        if changed:
            filepath.write_text(text, encoding="utf-8")
            modified.append(str(filepath))
    return modified
```

> **与上版差异**：
> - `sections` 从 `dict[str, str]` 改为 `dict[str, dict[str, str]]`
> - 按 `(filename, section_id)` 精确匹配，同一文件可有多个 auto-section
> - section_id 也做 `re.escape()` 确保特殊字符安全

## Graphify 增强器具体实现

### 引用 graphify 公开 API（对齐真实签名）

基于 graphify 仓库当前 v0.4.16 的实际实现：

| graphify API | 真实签名 | 适配层用途 |
|---|---|---|
| `collect_files(target)` | `(Path, *, follow_symlinks=False, root=None) -> list[Path]` | 目录扫描，返回代码文件路径列表 |
| `extract(paths)` | `(list[Path], cache_root=None) -> dict{nodes, edges, input_tokens, output_tokens}` | 批量 AST 提取 |
| `build_from_json(data)` | `(dict, *, directed=False) -> nx.Graph` | 提取结果 → NetworkX 图 |
| `cluster(G)` | `(nx.Graph) -> dict[int, list[str]]` | Leiden 社区检测 |
| `score_all(G, communities)` | `(G, dict) -> dict[int, float]` | 社区内聚度评分 |
| `god_nodes(G, top_n=10)` | `(G, int) -> list[dict]` | 核心节点 |
| `surprising_connections(G, communities)` | `(G, dict) -> list[dict]` | 跨社区异常连接 |
| `suggest_questions(G, communities, labels)` | `(G, dict, dict) -> list[dict]` | 建议问题 |
| `generate(G, ...)` | `(G, communities, cohesion, labels, gods, surprises, detection, token_cost, root, *, suggested_questions) -> str` | 生成 report.md |
| `to_json(G, communities, path)` | `(G, dict, str) -> None` | 持久化 graph.json |
| `to_html(G, communities, path)` | `(G, dict, str) -> None` | 交互可视化 |
| `detect_incremental(root)` | `(Path, manifest_path=...) -> dict` | 增量检测，返回 `new_files` + `deleted_files` + `new_total` |

### collect_files 局限：不收 .md

```python
# graphify/extract.py:3183
_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ...}  # 无 .md
```

plan/ 和 history/ 的 Markdown 方案文件不会被收集。适配层额外扫描补充。

> **本期能力边界**：只保证"文档节点入图可见"，不承诺自动推断文档间依赖。

### _collect_plan_docs — 文档节点补充扫描

```python
def _collect_plan_docs(self, repo_root: Path) -> list[dict]:
    """扫描 plan/ 和 history/ 中的 .md 文件，生成文件级文档节点。

    source_location 按 sopify 知识层级映射：
    - plan/  → L2 (active plan)
    - history/ → L3 (archived plan)
    不写死为 L1，避免与 blueprint stable 层混淆。
    """
    LAYER_MAP = {
        "plan": "L2",       # active plan
        "history": "L3",    # archived plan
    }
    md_nodes = []
    for subdir, layer in LAYER_MAP.items():
        md_dir = repo_root / ".sopify-skills" / subdir
        if not md_dir.exists():
            continue
        for md_file in md_dir.rglob("*.md"):
            md_nodes.append({
                "id": str(md_file.relative_to(repo_root)),
                "label": md_file.stem,
                "file_type": "markdown",
                "source_file": str(md_file),
                "source_location": layer,
            })
    return md_nodes
```

### 依赖可用性检测

`is_available()` 使用策略链检测（见上方"graphify 依赖策略"节），不硬绑分发名：

```python
class GraphifyEnhancer(BlueprintEnhancer):
    MIN_VERSION = "0.4.16"

    _DETECT_STRATEGIES = [
        ("pkg", "graphifyy"),
        ("pkg", "graphify"),
        ("import", "graphify"),
    ]

    def is_available(self) -> bool:
        for strategy, target in self._DETECT_STRATEGIES:
            if strategy == "pkg":
                try:
                    from importlib.metadata import version
                    ver = version(target)
                    if self._version_compat(ver):
                        return True
                except Exception:
                    continue
            elif strategy == "import":
                try:
                    import importlib
                    mod = importlib.import_module(target)
                    ver = getattr(mod, "__version__", None)
                    if ver and self._version_compat(ver):
                        return True
                except Exception:
                    continue
        return False
```

### 社区标签策略

```python
def _label_communities(self, G: nx.Graph, communities: dict) -> dict[int, str]:
    """基于社区内核心节点生成可读标签。"""
    labels = {}
    for cid, members in communities.items():
        if not members:
            labels[cid] = f"Community {cid}"
            continue
        # 取社区内 degree 最高的节点
        real_members = [n for n in members if n in G]
        if not real_members:
            labels[cid] = f"Community {cid}"
            continue
        sorted_by_degree = sorted(real_members, key=lambda n: G.degree(n), reverse=True)
        top = sorted_by_degree[0]
        top_label = G.nodes[top].get("label", top)
        # 空社区或弱标签时，用前两个代表节点
        if len(sorted_by_degree) >= 2 and G.degree(sorted_by_degree[0]) <= 2:
            second_label = G.nodes[sorted_by_degree[1]].get("label", sorted_by_degree[1])
            labels[cid] = f"{top_label} & {second_label}"
        else:
            labels[cid] = f"{top_label} cluster"
    return labels
```

> **与上版差异**：
> - 空社区或弱标签（degree ≤ 2）时回退到前两个代表节点名
> - 防御 real_members 为空的边界情况

### GraphifyEnhancer 实现

```python
@register_enhancer
class GraphifyEnhancer(BlueprintEnhancer):
    MIN_VERSION = "0.4.16"

    @property
    def name(self) -> str:
        return "graphify"

    def generate(self, repo_root, output_dir):
        import graphify

        # 0. 通过基类 hook 排除自产物
        self.ensure_output_excluded(repo_root, output_dir)

        # 1. 扫描代码文件 → list[Path]
        code_files = graphify.collect_files(repo_root)

        # 2. 批量 AST 提取 → dict{nodes, edges}
        extraction = graphify.extract(code_files)

        # 3. 构图
        G = graphify.build_from_json(extraction)

        # 4. 补充 plan/history .md 文档节点（L2/L3 层级标记）
        for node in self._collect_plan_docs(repo_root):
            G.add_node(node["id"], **node)

        # 5. 聚类 + 分析
        communities = graphify.cluster(G)
        cohesion = graphify.score_all(G, communities)
        gods = graphify.god_nodes(G, top_n=5)
        surprises = graphify.surprising_connections(G, communities)
        labels = self._label_communities(G, communities)
        questions = graphify.suggest_questions(G, communities, labels)

        # 6. 持久化到 blueprint/graphify/ 目录
        output_dir.mkdir(parents=True, exist_ok=True)
        detection_stub = {"files": {}, "total_files": len(code_files)}
        report_md = graphify.generate(
            G, communities, cohesion, labels, gods, surprises,
            detection_stub, {"input": 0, "output": 0}, str(repo_root),
            suggested_questions=questions,
        )
        (output_dir / "report.md").write_text(report_md, encoding="utf-8")
        graphify.to_json(G, communities, str(output_dir / "graph.json"))
        graphify.to_html(G, communities, str(output_dir / "graph.html"))
        self._write_meta(output_dir, G, communities)

        return {
            "gods": gods, "communities": communities,
            "surprises": surprises, "questions": questions,
            "labels": labels,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "community_count": len(communities),
        }

    def update(self, repo_root, output_dir):
        # 通过基类 hook 排除自产物（增量检测前必须生效）
        self.ensure_output_excluded(repo_root, output_dir)

        graph_json = output_dir / "graph.json"
        if not graph_json.exists():
            return self.generate(repo_root, output_dir)

        meta = self._read_meta(output_dir)
        if self._needs_full_rebuild(meta):
            return self.generate(repo_root, output_dir)

        from graphify.detect import detect_incremental
        detection = detect_incremental(repo_root)

        if detection.get("new_total", 0) == 0 and not detection.get("deleted_files"):
            return self._load_existing_result(output_dir)

        return self._incremental_rebuild(detection, output_dir, repo_root)

    def render_auto_sections(self, result):
        """返回 {filename: {section_id: content}}。"""
        return {
            "background.md": {
                "codebase-overview": self._render_codebase_overview(result),
            },
            "design.md": {
                "architecture": self._render_architecture(result),
            },
        }
```

## 增量检测自产物排除

### 通用约定

`BlueprintEnhancer` 基类定义了 `ensure_output_excluded(repo_root, output_dir)` 方法。
每个增强器在 `generate()`/`update()` 开始前应调用此方法（或等效实现），
确保自产物不被自身的增量检测扫描到。后续接入第二个 enhancer 时复用同一约定。

### GraphifyEnhancer 实现

`detect_incremental(repo_root)` 扫描整个仓库（detect.py:337-360），
包括 `blueprint/graphify/report.md` 等增强器自产物。如果不排除，
上次生成的 report.md 会在下次检测中被识别为"新变化文件"，
导致"自己生成的报告触发自己再次更新"的噪音循环。

### 方案

GraphifyEnhancer override `ensure_output_excluded()` 为 `_ensure_graphifyignore()`，
利用 graphify 自带的 `.graphifyignore` 文件过滤（detect.py:337-348）：

```python
def ensure_output_excluded(self, repo_root: Path, output_dir: Path):
    """Override 基类通用 hook，委托到 .graphifyignore 机制。"""
    self._ensure_graphifyignore(repo_root, output_dir)

def _ensure_graphifyignore(self, repo_root: Path, output_dir: Path):
    """确保 .graphifyignore 排除增强器自产物目录。"""
    ignore_file = repo_root / ".graphifyignore"
    rel_output = output_dir.relative_to(repo_root)
    exclude_pattern = f"{rel_output}/"

    if ignore_file.exists():
        content = ignore_file.read_text(encoding="utf-8")
        if exclude_pattern not in content:
            with ignore_file.open("a", encoding="utf-8") as f:
                f.write(f"\n# sopify blueprint enhancer output\n{exclude_pattern}\n")
    else:
        ignore_file.write_text(
            f"# sopify blueprint enhancer output\n{exclude_pattern}\n",
            encoding="utf-8",
        )
```

- generate()/update() 调用 `self.ensure_output_excluded()` → 走基类 hook
- GraphifyEnhancer override → `_ensure_graphifyignore()` → `.graphifyignore` 机制
- 排除的是整个 `blueprint/graphify/` 目录
- `.graphifyignore` 应 git tracked（和 `.gitignore` 同级），这样团队共享
- 如果仓库已有 `.graphifyignore`，只追加不覆盖

## README.md 入口链接

### 问题

`runtime/kb.py` 的 read-next 区块是 runtime 完全重渲染的（L298-301, L351-354），
手工注入会被覆盖。`_additional_blueprint_entries()` (L359-364) 只扫顶层文件。

### 方案

扩展 `_additional_blueprint_entries()` 自动发现子目录产物：

```python
def _additional_blueprint_entries(config: RuntimeConfig) -> list[str]:
    blueprint_root = config.runtime_root / "blueprint"
    if not blueprint_root.exists():
        return []
    entries: list[str] = []
    for path in sorted(blueprint_root.glob("*.md")):
        if path.name in _STANDARD_BLUEPRINT_FILENAMES:
            continue
        entries.append(f"- [{path.stem}](./{path.name})")
    # 新增：扫描增强器产物目录中的 report.md
    for subdir in sorted(blueprint_root.iterdir()):
        if subdir.is_dir() and (subdir / "report.md").exists():
            entries.append(f"- [{subdir.name} 增强报告](./{subdir.name}/report.md)")
    return entries
```

不绑定 graphify 名字——任何增强器在 `blueprint/{name}/report.md` 放产物都被发现。

## 首次运行时机

增强器**不挂入 bootstrap 默认流程**。首次运行为显式脚本调用：

```bash
python3 scripts/blueprint_enhance.py
```

脚本内部检查 blueprint scaffold 是否存在，不存在则报提示退出。

## 目录结构

```
.sopify-skills/
├── blueprint/
│   ├── README.md                    # 索引（runtime 自动渲染 read-next）
│   ├── background.md                # 手写 + <!-- graphify:auto:codebase-overview:start/end -->
│   ├── design.md                    # 手写 + <!-- graphify:auto:architecture:start/end -->
│   ├── tasks.md                     # 不变
│   └── graphify/                    # = blueprint/{enhancer.name}/
│       ├── report.md                # git tracked
│       ├── graph.json               # git ignored
│       ├── graph.html               # git ignored
│       └── .meta.json               # git ignored
```

.gitignore 追加：
```
.sopify-skills/blueprint/graphify/graph.json
.sopify-skills/blueprint/graphify/graph.html
.sopify-skills/blueprint/graphify/.meta.json
.sopify-skills/blueprint/graphify/.cache/
```

## 迭代机制

```
代码/文档变更
  → python3 scripts/blueprint_enhance.py
  → get_enabled_enhancers(config)
  → 每个增强器 update()
      - graph.json 不存在 → fallback generate()
      - .meta.json 缺失/损坏/版本变化 → fallback generate()
      - graph.json 格式异常 → fallback generate()
      - 正常 → detect_incremental() → new_files + deleted_files
  → render_auto_sections() → {filename: {section_id: content}}
  → inject_auto_sections() 精确匹配 (filename, section_id) 注入
  → 人工 review
```

编排脚本接口：
```bash
python3 scripts/blueprint_enhance.py                    # 全部已启用增强器
python3 scripts/blueprint_enhance.py --only graphify     # 仅 graphify
python3 scripts/blueprint_enhance.py --list              # 列出注册表
python3 scripts/blueprint_enhance.py --strict            # CI 模式：不满足 Leiden → exit 1
```

**CI / 本地模式切换**：

| 模式 | 触发条件 | Louvain fallback 行为 |
|---|---|---|
| strict（CI） | `--strict` flag 或 `CI=true` 环境变量 | **报错退出**（exit 1），不生成 report.md |
| normal（本地） | 默认 | warning + 标出 `cluster_backend=louvain`，允许生成但提示勿提交 |

脚本伪逻辑：
```python
strict_mode = args.strict or os.environ.get("CI", "").lower() in ("true", "1")
if cluster_backend == "louvain" and strict_mode:
    sys.exit("[FAIL] Leiden required in strict mode. Install: pip install graspologic")
```

编排脚本输出必须包含**聚类后端标识**，便于 review 和排障：

```
[graphify] cluster_backend=leiden    node_count=142  edge_count=287  community_count=5
[graphify] report.md updated: blueprint/graphify/report.md
```

或 fallback 时：

```
[graphify] ⚠ cluster_backend=louvain (graspologic not installed)
[graphify] ⚠ Report generated with Louvain fallback. Do NOT commit if CI requires Leiden.
```

## Plan 同步机制

### 能力边界

> 本期：plan/history 文档"入图可见"（文件节点，L2/L3 层级标记）。
> 不承诺：自动推断文档间依赖（Phase 4.1）。

### Plan 生命周期映射

| Plan 事件 | 图谱反应 | 触发方式 |
|---|---|---|
| Plan Created | plan/ .md → L2 节点 | 下次手动 run |
| Plan Modified | mtime 变化 → 重提取 | 下次手动 run |
| Plan Finalized | plan/ → history/ → L2 节点消失、L3 节点出现 | finalize 后提示 |

### Finalize 提示

```
Plan finalized. Run 'python3 scripts/blueprint_enhance.py' to update the blueprint.
```
仅存在已启用增强器时显示。不自动触发。

> 本期仅可见性提示，不提供结构化 stale/freshness gate。
> 后续可在 state/ 或 .meta.json 中记录 enhancer freshness。

## 版本兼容策略

### .meta.json（自动管理，git ignored）

```json
{
  "generated_with": "0.4.16",
  "generated_at": "2026-04-16T06:45:00Z",
  "node_count": 142,
  "edge_count": 287,
  "community_count": 5
}
```

### 兼容矩阵

| 场景 | 适配层行为 |
|---|---|
| graphify 未安装 | 策略链检测失败 → warn + skip |
| graphify < MIN_VERSION | 同上 |
| patch 升级 | 默认增量；.meta.json/graph.json 异常 → 回退全量 |
| minor/major 升级 | `_needs_full_rebuild()` → 全量重建 |
| .meta.json 缺失/损坏 | 回退全量重建（fail-open） |
| graph.json 字段缺失 | `.get()` 防御 → placeholder |

> 原则：fail-open + 可回退。任何异常状态统一回退全量重建。

## 实现分层

| 层 | 文件 | 职责 | 状态 |
|---|---|---|---|
| 配置验证 | `runtime/config.py` | `blueprint_enhancers` 父键 | 改动 |
| 增强器抽象 | `installer/blueprint_enhancer.py` | 基类 + 注册表 + 注入引擎 | **新增** |
| Graphify 实现 | `installer/enhancers/graphify_enhancer.py` | 增强器 + plan 补充 + 标签 + 检测策略链 | **新增** |
| 编排脚本 | `scripts/blueprint_enhance.py` | 协调流程 | **新增** |
| README 发现 | `runtime/kb.py` | 子目录产物发现 | 改动 |
| .gitignore | `.gitignore` | 排除 graphify 重文件 | 追加 |
| blueprint 文件 | `blueprint/{background,design}.md` | auto-section 占位 | 追加 |
| graphify 核心 | （外部仓库） | 不改 | — |
