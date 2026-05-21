# 技术设计: P7 Repo 激活模型迁移（Copilot-first 验收）

## 范围边界

**定性：** P7 不是从 0 到 1 的全局化。全局发动机（`~/<host_dir>/sopify/` 的 payload manifest + versioned bundles + bootstrap helper）已在 P4d 和 installer 主线中就位。P7 的工程目标是：把 repo 内的 legacy 激活物 `.sopify-runtime/manifest.json`（8 字段 thin stub）替换为统一 workspace marker（`.sopify-skills/sopify.json`），repo-local pointer 按宿主需要决定是否追加。

**架构层：** 宿主无关。凡是靠 repo 内发现文件起作用的宿主都适用。
**验收层：** Copilot-first。首个落地和验收样板用 Copilot（Codex），但不排他。

**在范围内**：
- repo 激活物迁移：`.sopify-runtime/manifest.json` → `.sopify-skills/sopify.json`（统一 workspace marker）
- 6 个生产消费者的检测路径迁移（gate, preflight, inspection, bootstrap, validate, smoke）
- workspace detection 锚点切换（祖先扫描标记从 `.sopify-runtime/manifest.json` → `sopify.json`）
- 外部 repo bootstrap 命令 + diagnostics
- 发布链 + examples + smoke test
- 吸收 First-Use Adoption Proof 的 examples/视觉资产部分

**不在范围内**：
- 全局发动机改造（`~/.codex/sopify/` payload/bundle 层已就位，不动）
- Deep runtime 改动（runtime/ 目录本体不动）
- protocol.md 修改
- 大规模 installer 重写（只做消费者检测路径的最小迁移）
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

### DR-1: 版本锚点迁移 — ✅ 方案 A APPROVED

**决策：迁入 `.sopify-skills/sopify.json`**

```json
{
  "schema_version": "1",
  "workspace_kind": "external",
  "bundle_version": "2026-05-21.101226",
  "locator_mode": "global_first",
  "capabilities": ["state_write", "handoff_consume"]
}
```

- 极简 ~5 字段，版本真值在且仅在此文件
- workspace detection 新锚点 = `.sopify-skills/sopify.json`
- 代价：迁移 6 个生产消费者 + N 个测试的检测路径

<details><summary>备选方案（未采纳）</summary>

**方案 B：** `.sopify-version.json`（root 单文件）— 改动最小但 root 多点文件

**方案 C：** 不迁移，双路检测逻辑 — 零破坏但维护成本高

</details>

### DR-2: Repo-local 激活载体 — ✅ 修订方案 APPROVED

**决策：repo-local pointer 不是统一文件模型，而是按宿主发现机制决定的适配策略**

完整 prompt asset 留在全局安装位置，不落入 repo。Repo-local pointer **仅在宿主需要 repo-local discovery 时**，写入宿主原生 instruction 文件。

> 统一的只有 workspace marker（sopify.json）。repo-local pointer 是宿主适配层，不是所有宿主都默认产出。

| 宿主类型 | repo-local 策略 | 原因 |
|---------|----------------|------|
| 全局 prompt 型（Codex/Claude） | 默认不写 repo-local header | 已有 `~/<host_dir>/<header>`，repo 只需 sopify.json |
| 本地 inst 文件型（Copilot 等） | managed block upsert 到宿主原生 repo-local instruction 文件 | 宿主靠 repo 内文件发现 |
| 临时注入型（未来宿主） | 会话态注入，不持久化到 repo 文件 | 以后碰到再定 |

**约束：**
- repo 内 pointer 不含绝对路径
- 版本真值只在 `sopify.json`，pointer 不重复
- pointer 是宿主发现入口，不是操作指南
- **写入策略（仅本地 inst 型宿主）：** managed block upsert（同 `.gitignore` 的 `_write_managed_ignore_block` 模式）
- S1 只定"写入宿主原生 repo-local instruction 文件"策略，具体文件名/路径到实现切片再落

**managed block upsert 规则（仅本地 inst 型宿主适用）：**

| 场景 | 行为 |
|------|------|
| 宿主原生 inst 文件不存在 | 创建新文件，仅含 pointer block |
| 已存在，无 SOPIFY 标记 | 在文件末尾追加 pointer block |
| 已存在，有 SOPIFY 标记 | 原地替换 BEGIN/END 之间的内容 |
| 卸载 / 清理 | 删除 BEGIN/END block，保留用户其他内容 |

实现参考：`installer/bootstrap_workspace.py:1117-1132`（`_write_managed_ignore_block`）

<details><summary>原始方案（已修订）</summary>

原方案 A（`.sopify-skills/prompts/`）把 prompt asset 落入 repo — 否决：prompt 是发动机的一部分，应随全局安装走。

原方案 B（root AGENTS.md 完整版）— 否决：不应把全量 prompt 放 repo root。

</details>

**Copilot 具体分发方案（S3 落地）：**

Copilot 属于"本地 inst 文件型"宿主，使用 GitHub 官方支持的 instruction 文件：
- 轻入口：`.github/copilot-instructions.md`（managed block upsert）
- 重说明：`.github/instructions/sopify.instructions.md`（官方 path-specific instructions）
- 内容来源：从 `Copilot/Skills/CN/COPILOT.md`（P4d seed）提炼，bootstrap 托管写入
- 待验证：目标 Copilot 运行面是否支持 path-specific instructions；如不支持，重说明内联到轻入口

### DR-3: Bootstrap 入口 — ✅ 方案 APPROVED

**决策：** `python3 -m sopify_bootstrap` 为 canonical 入口，`curl|bash` 为 convenience wrapper。

```bash
# Canonical 入口
python3 -m sopify_bootstrap init --workspace .

# Convenience wrapper（下载并执行）
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/bootstrap.sh | bash -s -- init .
```

产出（最小必需）：
```
workspace/
├── .sopify-skills/
│   └── sopify.json          ← 版本锚点 + 能力声明（~5 字段）
└── .gitignore                ← managed ignore block 追加（.sopify-skills/state/ 等）
```

> `state/` 目录由 canonical_writer 在首次写入时懒创建，init 不落盘。
> `project.md`、`blueprint/` 等 protocol 骨架不在 init 范围 — 那是使用者按需创建的，不是激活物。
> repo-local pointer（宿主原生 inst 文件）**不是默认产物**，仅在宿主需要 repo-local discovery 时按需追加。

---

## 目标态总结

### 现在 vs P7 后

| 层 | 现在 | P7 后 |
|---|---|---|
| **全局** `~/<host_dir>/sopify/` | payload-manifest.json + bundles/ + helpers/ | **不动** |
| **全局** `~/<host_dir>/<header>` | 完整 prompt asset | **不动** |
| **repo** 激活物 | `.sopify-runtime/manifest.json`（8 字段 thin stub） | → `.sopify-skills/sopify.json`（~5 字段，统一 marker）；repo-local pointer 按宿主需要决定 |

### Repo 目标结构（init 最小产出）

```
workspace/                        （任意外部 repo）
├── .sopify-skills/
│   └── sopify.json               ← 新门牌：版本锚点 + 能力声明
├── .gitignore                     ← managed ignore block
└── (NO .sopify-runtime/)
```

> `state/`、`project.md`、`blueprint/`、`plan/`、`history/` 由使用者按需创建，不在 init 产出范围。
> repo-local pointer（宿主原生 inst 文件）不在默认产出范围，仅在宿主需要 repo-local discovery 时按需追加。

### 依赖链

workspace `sopify.json` → 全局 `payload-manifest.json` → 选中 bundle → canonical_writer + sopify_contracts

**一句话：** 全局发动机不动，只把 repo 里的旧门牌换成新门牌。
