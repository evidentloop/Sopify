# 技术设计: P7 Copilot Payload-Only Onboarding Mainline

## 范围边界

**在范围内**：
- 外部 repo 接入路径产品化（Copilot + payload-only）
- 版本锚点从 `.sopify-runtime/manifest.json` 迁入 `.sopify-skills/` 结构
- prompt asset 分发机制（不碰 `.github/copilot-instructions.md`）
- 外部 repo bootstrap 命令 + diagnostics
- 发布链 + examples + smoke test
- 吸收 First-Use Adoption Proof 的 examples/视觉资产部分

**不在范围内**：
- Deep runtime 改动（runtime/ 目录本体不动）
- 多宿主适配（只押 Copilot 一条路）
- protocol.md 修改
- 大规模 installer 重写
- 人工试点验证（用机器 smoke 替代）

## S1 分析结果

### 1. `.sopify-runtime/manifest.json` 消费者全景

| 消费者 | 读取字段 | 用途 | 可迁移性 |
|--------|---------|------|---------|
| installer/bootstrap_workspace.py L578-586 | 文件存在性 | workspace detection（ancestor marker） | 需要新锚点 |
| installer/bootstrap_workspace.py L614-679 | schema_version, stub_version, bundle_version, required_capabilities, locator_mode, legacy_fallback, ignore_mode, written_by_host | 分类状态（MISSING/INCOMPATIBLE/READY） | 字段可迁移 |
| installer/inspection.py L837-951, L989-1024 | 同上全量 | 健康检查 + 能力验证 | 字段可迁移 |
| installer/validate.py L222-244 | stub 全量字段 | schema 校验 | 字段可迁移 |
| runtime/gate.py L141/241/322 | 文件存在性 only | workspace 存在证据 | 最简单：改检测路径 |
| scripts/check-runtime-smoke.sh L190-207 | stub_version | 烟雾测试 | 需同步改 |
| tests/* | 同上 | 测试消费者 | 跟随主实现 |

**关键发现：** 6 个生产消费者，全部硬编码 `.sopify-runtime/manifest.json`。但其中 3 个只做存在性检查，另 3 个读全量字段。

### 2. Workspace Detection 机制

当前检测链：
```
_resolve_activation_root():
  1. for ancestor in workspace_root.parents:
  2.   check ancestor/.sopify-runtime/manifest.json
  3.   if valid → use ancestor as workspace root
  4. fallback → use cwd
```

**检测锚点 = `.sopify-runtime/manifest.json` 的存在性。** 如果迁移，需要一个新的锚点文件。

### 3. 全局 Payload Manifest vs Workspace Stub

| 层 | 位置 | 字段 | 职责 |
|----|------|------|------|
| 全局 payload | `~/.sopify/payload-manifest.json` | schema_version, payload_version, bundle_version, active_version, bundles_dir, default_bundle_dir, capabilities, minimum_workspace_manifest | 宿主安装时生成，描述可用的全部 bundle |
| 全局 bundle | `~/.sopify/bundles/<version>/manifest.json` | bundle_version, helper_entry, scripts, tests | 每个 bundle 的内容清单 |
| 工作区 stub | `workspace/.sopify-runtime/manifest.json` | schema_version, stub_version, bundle_version, required_capabilities, locator_mode, ignore_mode, written_by_host | 工作区的版本 pin + 能力声明 |

**解析链：** workspace stub → 全局 payload manifest → 选中 bundle manifest → 加载

### 4. Prompt Asset 现状

| 宿主 | 路径 | 说明 |
|------|------|------|
| Codex | `Codex/Skills/{CN,EN}/AGENTS.md` | 含 SOPIFY_VERSION 注释 |
| Claude | `Claude/Skills/{CN,EN}/CLAUDE.md` | 同上 |

**发现机制：** 目前是 Sopify 自身 repo 的内部结构，通过 pre-commit hook 同步。外部 repo 需要不同的方案 — 没有现成的"外部 repo prompt asset 分发"机制。

### 5. `.sopify-skills/` 现有结构 + 最小可行

**protocol.md 定义的最小下界（Convention 模式）：**
`project.md` + `blueprint/` + `plan/` + `history/`

**canonical_writer 需要：**
`.sopify-skills/state/` 目录（current_run.json, current_handoff.json 等）

### 6. `sopify.config.yaml`

存在于 `examples/sopify.config.yaml`（示例）。
字段：brand, language, output_style, title_color 等用户面配置。
**与版本治理无关。**

---

## 决策方案

### DR-1: 版本锚点迁移

**方案 A（推荐）：迁入 `.sopify-skills/sopify.json`**

```json
{
  "schema_version": "1",
  "stub_version": "2",
  "bundle_version": "2026-05-21.101226",
  "required_capabilities": ["state_write", "handoff_consume"],
  "locator_mode": "global_first",
  "ignore_mode": "gitignore"
}
```

- 优点：一个目录、直觉、与 protocol.md 定义的 `.sopify-skills/` 结构对齐
- 代价：改 6 个生产消费者 + N 个测试的检测路径
- workspace detection 新锚点 = `.sopify-skills/sopify.json`

**方案 B：保留 `.sopify-runtime/manifest.json` 但重命名为 `.sopify-version.json`（root 单文件）**

- 优点：改动最小（只是路径字符串替换）
- 缺点：root 多一个点文件，还是两层

**方案 C：不迁移，只在外部 repo 路径中不要求 `.sopify-runtime/`**

- 优点：零破坏性
- 缺点：两套检测逻辑（deep repo 有 `.sopify-runtime/`，外部 repo 用别的）

### DR-2: Prompt Asset 外部 repo 分发

**方案 A（推荐）：`.sopify-skills/prompts/{AGENTS.md,CLAUDE.md}`**

- bootstrap 时从 release asset 复制到外部 repo
- 宿主自行配置 copilot-instructions 指向此路径
- 不碰 `.github/copilot-instructions.md`

**方案 B：root 级 `AGENTS.md`**

- 简单但污染 repo root
- Copilot 的 custom instructions 发现机制不保证自动加载任意位置

### DR-3: 外部 repo Bootstrap 入口

**方案 A（推荐）：单命令 bootstrap**

```bash
# 从 release asset 初始化
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/bootstrap.sh | bash -s -- --workspace .
```

或 Python 入口：
```bash
python3 -m sopify_bootstrap --workspace .
```

产出：
```
workspace/
├── .sopify-skills/
│   ├── sopify.json          ← 版本锚点
│   ├── project.md           ← 骨架
│   ├── blueprint/           ← 骨架
│   ├── prompts/
│   │   ├── AGENTS.md        ← Codex prompt asset
│   │   └── CLAUDE.md        ← Claude prompt asset
│   └── state/               ← canonical_writer 目标目录（空）
└── .gitignore update        ← 追加 .sopify-skills/state/
```

---

## 目标态总结

```
外部 repo 接入后（无 .sopify-runtime/）：

workspace/
├── .sopify-skills/
│   ├── sopify.json          ← 版本锚点 + 能力声明（替代 .sopify-runtime/manifest.json）
│   ├── project.md           ← 项目技术约定
│   ├── blueprint/           ← 蓝图骨架
│   │   ├── background.md
│   │   └── tasks.md
│   ├── prompts/             ← prompt asset
│   │   ├── AGENTS.md
│   │   └── CLAUDE.md
│   ├── plan/                ← 方案包（使用时创建）
│   ├── history/             ← 归档（使用时创建）
│   └── state/               ← canonical_writer 状态目录
│       ├── current_run.json
│       ├── current_handoff.json
│       └── ...
├── sopify.config.yaml       ← 用户面配置（可选）
└── (NO .sopify-runtime/)
```

依赖链：workspace sopify.json → 全局 payload manifest → bundle → canonical_writer + sopify_contracts
