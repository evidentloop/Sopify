# 设计方案

## 概述

消灭宿主级内容副本，统一安装链路。4 套宿主语言内容 → 2 套语言源 + 安装时 host 渲染。

---

## 设计原则

1. **committed source 只有 `skills/en/` 和 `skills/zh/`**——宿主差异不体现在内容文件中
2. **host-specific 差异只允许存在于 header template + host metadata**——不允许为每个宿主维护独立内容副本
3. **Copilot 纳入统一 registry**——installer 可以先把同一 skill 源渲染到单文件 surface（`.github/copilot-instructions.md`），不强求 subtree 物理同形
4. **每一步必须是减法**——如果一个改动增加了文件数或概念数，重新审视

---

## D1 | Skill 源单一化：4 → 2

### 当前结构

```
Codex/Skills/EN/  (header + 22 skill files, 共 23) ← CONTRIBUTING:14 定义的 prompt-layer 真源
Codex/Skills/CN/  (header + 22 skill files, 共 23) ← 同上
Claude/Skills/EN/ (header + 22 skill files, 共 23, 与 Codex EN 内容等价，header 文件名不同)
Claude/Skills/CN/ (header + 22 skill files, 共 23, 与 Codex CN 内容等价)
Copilot/Skills/CN/ (1 file: COPILOT.md)
```

Codex 是唯一事实源（依据 `CONTRIBUTING.md:14-17` 治理定义）。Claude 是镜像，内容等价。

### 目标结构

```
skills/
  en/
    header.md.template     ← 含 {{config_dir}} 等变量
    skills/sopify/
      analyze/SKILL.md     ← 从 Codex/Skills/EN 移入（唯一真源）
      design/SKILL.md
      develop/SKILL.md
      kb/SKILL.md
      templates/SKILL.md
      (assets/ references/ 同移)
  zh/
    header.md.template
    skills/sopify/
      (同上，从 Codex/Skills/CN 移入)
```

### skills/hosts.yaml

```yaml
hosts:
  claude:
    host_id: claude
    config_dir: "~/.claude"
    header_filename: CLAUDE.md
    destination_dir: ".claude"
    instruction_surface: header_embedded
    install_enabled: true
  codex:
    host_id: codex
    config_dir: "~/.codex"
    header_filename: AGENTS.md
    destination_dir: ".codex"
    instruction_surface: header_embedded
    install_enabled: true
  copilot:
    host_id: copilot
    config_dir: null
    header_filename: COPILOT.md
    destination_dir: ".github"
    instruction_surface: copilot_instructions_md
    install_enabled: true
```

### 旧目录处理

**删除 Claude/、Codex/、Copilot/ 目录**（选项 A：当前无线上用户，可以激进）。`scripts/sync-skills.sh` 相应删除或改为从 `skills/{lang}/` 读取。

### 后续宿主适配

新增宿主只需：
- 在 `skills/hosts.yaml` 加一条 host 元数据
- 在 `installer/hosts/` 加一个 adapter（消费 host metadata）
- 不需要复制任何 skill 内容

---

## D2 | Copilot 进入统一 Host Registry

### 当前问题

- `installer/hosts/__init__.py:14`：registry 只有 codex、claude
- `installer/payload.py:23,151`：Copilot 走 `resources/copilot/*.md` 特殊路径
- `installer/bootstrap_workspace.py:123-126`：硬编码 `_COPILOT_*` 常量
- `installer/distribution.py:461`：`if target.host == "copilot":` 特殊分支
- `installer/models.py:163-169`：`parse_install_target` 硬编码 copilot

### 设计决策

1. 新增 `installer/hosts/copilot.py`，注册进 `_REGISTRATIONS`
2. Copilot adapter 消费 `skills/{lang}/` 同一源，但渲染输出走 `instruction_surface: copilot_instructions_md`（单文件展平）
3. 逐步删除 payload.py / bootstrap_workspace.py / distribution.py 中的 copilot special-case
4. `installer/resources/copilot/` 目录删除（被 `skills/{lang}/` + 模板渲染取代）

### Copilot surface 形态

**本包默认实现**：Copilot 渲染为单文件 `.github/copilot-instructions.md`（header + skill 内容展平拼接）。不为 Copilot 建立 subtree 物理目录。

后续如需 subtree 支持，通过 `instruction_surface` 字段扩展，不影响本包设计。

---

## D3 | Bundle / Manifest 概念收口

### 当前问题

`installer/runtime_bundle.py:14`：
```python
_DIRECTORY_ASSETS = ("runtime", "sopify_contracts", "canonical_writer")
```
名字叫 `runtime_bundle`，但打包的不只是 runtime。对外传达"runtime 是核心"的错误信号。

### 设计决策

1. `runtime_bundle.py` → `sopify_bundle.py`（文件名和函数名）
2. smoke 检查脚本命名同步调整（`check-runtime-smoke.sh` → `check-bundle-smoke.sh`）
3. 文档和 CI 中的对外描述从 "runtime bundle" 统一为 "sopify bundle"

### 边界限制

本包 **只做命名和对外描述收口**。不做 installer → runtime 的 import 解耦，不改 manifest 生成逻辑——那属于 runtime_retirement_phase2。

---

## 修改范围汇总

| 区域 | 变更 | 增/减 |
|------|------|-------|
| `skills/en/` | 新建，从 Codex EN 移入 | +23 files |
| `skills/zh/` | 新建，从 Codex CN 移入 | +23 files |
| `skills/hosts.yaml` | 新建 | +1 file |
| `Claude/` | 删除 | −46 files |
| `Codex/` | 删除 | −46 files |
| `Copilot/` | 删除 | −1 file |
| `installer/resources/copilot/` | 删除 | −2 files |
| `installer/hosts/copilot.py` | 新建 | +1 file |
| `installer/hosts/__init__.py` | 注册 copilot | 修改 |
| `installer/runtime_bundle.py` | 改名 → `sopify_bundle.py` | 修改 |
| `scripts/sync-skills.sh` | 改为消费 `skills/{lang}/` 或删除 | 修改/删除 |
| bootstrap_workspace / payload / distribution | 砍 copilot special-case | 修改 |

**净效果**：文件数减少 ~47（46+46+1 旧 − 23+23 新 − 其他），维护面从 4 套 → 2 套，概念从"runtime bundle" → "sopify bundle"。
