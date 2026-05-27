---
plan_id: "20260526_pre_launch_host_and_bundle_unification"
title: "推广前宿主分发与 Bundle 统一"
level: standard
topic_key: pre_launch_host_and_bundle_unification
lifecycle_state: completed
created_at: "2026-05-26T14:30:00+08:00"
---

# 任务清单

## T0 | 治理对齐与 blast-radius 确认（新增）

**动作**：

1. **对齐 README ↔ registry 状态**：
   - `blueprint/README.md:16` 写"当前活动 plan：暂无"，但 `_registry.yaml` 已有 p0 active plan → 更新 README 指向本 plan
   - `cross_review_engine` 的 `lifecycle_state` 从 `active` 改为 `deferred`（不应占 active 位；`deferred` 是 `project.md:19` 定义的合法非归档例外）
   - `skill_writing_and_plugin_system` 的 `lifecycle_state` 从 `active` 改为 `deferred`（draft 阶段，不与 p0 plan 竞争 active 语义）

2. **定义唯一 source-of-truth**：
   - 依据：`CONTRIBUTING.md:14-17` 治理定义——**Codex 是 prompt-layer 真源**，Claude 是镜像
   - 本 plan T1 原文"从 Claude 移入"→ 修正为"从 Codex 移入"
   - 文件实态：Codex/Skills/EN 与 Claude/Skills/EN 各 23 个文件（排除 .DS_Store），内容等价，差异仅在 header 文件名（AGENTS.md vs CLAUDE.md）。source-of-truth 认定基于治理约定，不基于文件计数

3. **blast-radius 完整清单**：

   | 类别 | 受影响文件 | 触点数 |
   |------|----------|--------|
   | 旧宿主目录引用 | README.md, README.zh-CN.md, CONTRIBUTING.md, CONTRIBUTING_CN.md, 2 test 文件, 2 plan/history 文件 | 8 |
   | Copilot special-case（installer） | distribution.py, models.py, bootstrap_workspace.py, payload.py | 4 |
   | Copilot special-case（tests） | test_installer.py, test_distribution.py, test_sopify_init_smoke.py, test_runtime_gate.py | 4 |
   | runtime_bundle 引用 | CONTRIBUTING.md†, test_runtime_engine.py, test_installer.py†, test_installer_validate.py | 4 |
   | 旧同步脚本 + 消费者 | sync-skills.sh, check-skills-sync.sh, release-sync.sh, release-preflight.sh, ci.yml, pre-commit hook, CONTRIBUTING*.md†, test_release_hooks.py | 8 |
   | **合计（含跨类重复）** | | **28 触点** |

   > † 标注文件跨类重复：CONTRIBUTING.md 出现在 3 个类别，test_installer.py 出现在 2 个类别。去重后唯一文件约 22 个。

4. **设计 render golden snapshot 保护**：
   - 在删除旧目录前，必须从**当前旧宿主产物**生成 golden snapshot（不是从目标目录 `skills/{lang}/`）
   - T1 之后，新渲染管线产物与旧产物 hash 对比，验证内容等价

   **Golden Snapshot 协议**：

   | 维度 | 约定 |
   |------|------|
   | 基线来源（T0 生成） | 旧宿主安装产物——即 `Codex/Skills/{EN,CN}/`、`Claude/Skills/{EN,CN}/`、`Copilot/` 下的最终内容，按当前 installer 逻辑渲染后的产物 |
   | 换行归一化 | 统一为 LF（`\n`），去除每行尾部空白 |
   | 拼接顺序 | 按相对路径（相对各宿主安装根）**字典序升序**排列 |
   | 单文件格式 | `{relative_path}\0{file_content}\n`（路径与内容用 NUL 分隔，内容末尾保证换行） |
   | hash 算法 | sha256，输入 = 全部单文件格式按顺序拼接的字节流 |
   | hash key 定义 | 每条 key 是一个 host:lang 的**最终安装产物** hash（如 `claude:en-US` = Claude EN 渲染后的完整内容 hash），不是共享源 hash。claude/codex header 变量不同，各自独立取 hash |
   | 输出物 | `golden-snapshots.json`：`{ "claude:en-US": "sha256:...", "claude:zh-CN": "...", "codex:en-US": "...", "codex:zh-CN": "...", "copilot:en-US": "...", "copilot:zh-CN": "..." }` |
   | 等价判定 | T1+ 新管线渲染产物，用同一拼接+hash 规则取 sha256，与旧产物 golden hash 对比。hash 相同 = 等价；hash 不同时输出 diff 辅助定位 |
   | binary assets | 不参与 hash（图片等）；仅文本文件参与 |

**验收**：
- README 的"当前活动 plan"指向本 plan
- `_registry.yaml` 中只有本 plan 为 `lifecycle_state: active`
- blast-radius 分类表覆盖全部 28 个触点（去重后 ~22 个唯一文件）
- golden snapshot 基线已生成：`golden-snapshots.json` 含 6 条 host:lang 记录，其中 5 条 sha256，copilot:en-US 为无旧基线 null

**状态**：done

---

## T1 | 单一事实源建立 + installer source cutover（合并原 T1+T2）


**动作**：

1. ~~从 **Codex** 树移入 `skills/en/` 和 `skills/zh/`~~ — ✅ 已存在，白名单校验通过（6 个 SKILL.md 仅脚本路径替换，其余与 Codex 等价）
2. 创建 `skills/hosts.yaml`（claude / codex / copilot 三个 host 元数据）
3. 编写渲染脚本 `scripts/render-host-skills.py`：读取 `skills/{lang}/header.md.template` + `skills/hosts.yaml` → 输出最终 header
4. **切 installer source**：修改 `installer/hosts/base.py` 的 `source_root()` 从 `{Host}/Skills/{Lang}/` → `skills/{lang}/`
5. 更新 Claude/Codex adapter 的 `source_root()` 指向新路径
6. skill 文件内部清理：所有 `Claude/Skills/` / `Codex/Skills/` 旧路径引用替换为 `skills/{lang}/` — ✅ 已在 skills/ 半成品中完成

**为什么合并**：T1 和 T2 分开执行会制造"两套并存"中间态——新旧文件同时存在，改一处需同步两边，比方案包开始前更差。合并后一刀切换，无中间态。

**验收**：
- `skills/en/` 和 `skills/zh/` 包含完整 skill tree（与 Codex 源内容一致）
- `installer/hosts/base.py` 的 `source_root()` 指向 `skills/{lang}/`
- 渲染脚本 `render-host-skills.py` 输出的 claude/codex header 与 golden snapshot 内容等价
- skill 文件内部不再引用旧宿主目录路径

**状态**：done

---

## T2 | Copilot 进入 host registry + 单文件渲染（原 T3）

**动作**：新建 `installer/hosts/copilot.py`，注册到 `installer/hosts/__init__.py`。Copilot adapter 从 `skills/{lang}/` 读取源，渲染到单文件 `.github/copilot-instructions.md`。

**单文件渲染 contract**：
- **输入**：`skills/{lang}/header.md.template` + `skills/{lang}/skills/sopify/` 下所有 `SKILL.md`
- **展平顺序**：header → skill 按目录名字母序（analyze → design → develop → kb → templates）
- **分隔格式**：每个 skill 之间用 `---` + 空行分隔，skill 标题保留为二级标题
- **references / assets**：纯文本内容内联展平；二进制资源不进单文件
- **输出**：`.github/copilot-instructions.md`，UTF-8

**验收**：
- `installer/hosts/__init__.py` 包含 claude、codex、copilot 三个注册项
- `install.sh --target copilot` 走统一主链路
- 渲染产物与 golden snapshot 中 copilot:zh-CN 基线内容等价；copilot:en-US 无旧基线（hash == null），只验证新产物存在、可安装、由 `skills/en/` 渲染且通过 smoke

**状态**：done

---

## T3 | 砍 Copilot 主链 special-case（原 T4）

**动作**：删除 installer + scripts 中所有 copilot 硬编码分支。

**前置**：T2

**完整 blast-radius（28 处中的 copilot 相关）**：

| 文件 | 行号/模式 | 改动 |
|------|----------|------|
| `installer/distribution.py` | `if target.host == "copilot":` | 删除条件分支 |
| `installer/models.py` | `if value == "copilot":`, `startswith("copilot:")` | 走统一 registry |
| `installer/bootstrap_workspace.py` | `_COPILOT_*` 常量, `_sync_copilot_*` | 删除 |
| `installer/payload.py` | `resources/copilot/`, `_install_copilot_*`, `_ensure_copilot_*` | 删除 |
| `scripts/sopify_init.py:190` | copilot 特殊路径 | 走统一 registry |
| `scripts/check-readme-links.py:20` | 旧路径结构依赖 | 更新路径 |
| `installer/validate.py:54` | 旧路径校验逻辑 | 走统一 registry |
| `installer/resources/copilot/` | 整个目录 | 删除 |
| `tests/test_installer.py` | copilot instruction 测试 | 更新为走 registry |
| `tests/test_distribution.py` | copilot target/install paths | 更新路径 |
| `tests/test_sopify_init_smoke.py` | copilot init behavior | 更新 |
| `tests/test_runtime_gate.py` | copilot 引用 | 更新 |
| `tests/test_release_hooks.py:141` | 旧结构引用 | 更新路径 |

**验收**：
- `copilot` 不再作为 `if/elif` 条件控制安装主链路
- Copilot 差异只存在于 `skills/hosts.yaml` + `hosts/copilot.py` + surface renderer
- `installer/resources/copilot/` 目录已删除
- 全量测试通过

**状态**：done

---

## T4 | bundle / smoke 对外命名收口（原 T5）

**动作**：
- `installer/runtime_bundle.py` → `installer/sopify_bundle.py`（文件名 + 内部函数名）
- `scripts/check-runtime-smoke.sh` → `scripts/check-bundle-smoke.sh`
- 更新所有引用方

**完整引用方**：

| 文件 | 引用 | 改动 |
|------|------|------|
| `CONTRIBUTING.md:32,40` | `installer.runtime_bundle`, `check-runtime-smoke.sh` | 更新名称 |
| `tests/test_runtime_engine.py:8,1848,1863,1868,2042,2050` | `sync_runtime_bundle`, `check-runtime-smoke.sh` | 更新 |
| `tests/test_installer.py` | `_install_versioned_runtime_bundle`, `sync_runtime_bundle` | 更新 |
| `tests/test_installer_validate.py:24,48,73` | `check-runtime-smoke.sh` | 更新 |

**验收**：
- `runtime_bundle` / `runtime-smoke` 作为文件名和对外接口名不再存在
- CI + 全量测试通过

**状态**：done

---

## T5 | 贡献指南 + 文档更新（原 T5.5）

**动作**：
- `CONTRIBUTING.md` + `CONTRIBUTING_CN.md`：新增 "Adding a New Host" 章节，删除旧 source-of-truth 描述（Codex/Claude 分源），改为指向 `skills/{lang}/`
- `README.md` + `README.zh-CN.md`：更新目录结构描述，删除旧宿主目录引用
- 更新 blueprint 相关文档中引用旧路径的描述

**验收**：
- 社区用户按指南可独立完成新宿主接入
- 文档中不再引用 `Claude/`、`Codex/`、`Copilot/` 目录

**状态**：done

---

## T6 | 三宿主双语言端到端验证 + golden snapshot 对比（原 T6）

**前置**：T1-T5

**验证命令**：
1. `install.sh --target claude:en-US`
2. `install.sh --target claude:zh-CN`
3. `install.sh --target codex:en-US`
4. `install.sh --target codex:zh-CN`
5. `install.sh --target copilot:en-US`
6. `install.sh --target copilot:zh-CN`

**验收**：
- 6 条路径全部安装成功
- 有旧基线的 5 条路径（hash ≠ null），新管线渲染产物按 Golden Snapshot 协议取 hash 与 T0 旧产物对比等价
- copilot:en-US 无旧基线（hash == null）：只验证新产物存在、可安装、由 `skills/en/` 渲染且通过 smoke，不做旧产物等价比较
- smoke 脚本全通过
- 全量测试通过

**状态**：done

---

## T7 | 删除旧宿主目录与旧同步脚本（原 T7）

**前置**：T6 验证通过

**删除清单**：

| 目标 | 类型 |
|------|------|
| `Claude/` | 目录 |
| `Codex/` | 目录 |
| `Copilot/` | 目录 |
| `scripts/sync-skills.sh` | 文件 |
| `scripts/check-skills-sync.sh` | 文件 |

**消费者更新**：

| 文件 | 改动 |
|------|------|
| `scripts/release-sync.sh` | 删除或改为消费 `skills/{lang}/` |
| `scripts/release-preflight.sh` | 更新路径 |
| `.github/workflows/ci.yml` | 更新 sync 步骤 |
| `.githooks/pre-commit` | 更新 sync 引用 |
| `tests/test_check_readme_links.py:93-96,125-133,194,203` | 更新路径断言 |
| `tests/test_release_hooks.py:127-150,334-335,441,455` | 更新路径断言 |

**验收**：
- `Claude/`、`Codex/`、`Copilot/` 目录不存在
- 旧同步脚本不再引用已删目录
- CI + 全量测试通过

**状态**：done

---

## 执行顺序

```
T0（治理对齐）→ T1（源切换，原 T1+T2 合并）→ T2（Copilot 注册，原 T3）→ T3（砍 special-case，原 T4）→ T4（命名收口，原 T5）→ T5（文档，原 T5.5）→ T6（验证，原 T6）→ T7（删旧，原 T7）
```

T4 与 T2/T3 无硬依赖，可在 T1 之后任意位置插入。

## 不在本包范围

- runtime/ 模块外迁或删除（属于 runtime_retirement_phase2）
- installer → runtime import 解耦（同上）
- Copilot skill subtree 物理展平（先统一源和安装链，后续迭代）
- sopify_contracts + canonical_writer 合并（独立评估）
- 仓库级 `runtime` 更名（Phase 2 范畴）
