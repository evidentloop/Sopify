# 技术设计: P4a External Surface Freeze

## 方案概述

1 个方案包，2 个切片，纯文档变更，不写运行代码。

产出物：design.md 新增 "Frozen External Surface" 表 + output.py 字段审计表。

## Scope 边界

### 在 scope 内

- 枚举外部消费面 keep-list，写入 design.md "Frozen External Surface" 表
- 冻结 persistence surface 分类到目录级别（补充 design.md 已有分层表）
- output.py 渲染字段逐字段审计分类（machine truth projection / human hint / internal taxonomy leak）

### 不在 scope 内

- 不写运行代码、不改测试
- 不冻结 runtime 内部模块边界（engine.py / decision_tables.py 内部拆分属 P4b）
- 不冻结 Python 内部 API（函数签名、类方法名属实现，不是外部契约）
- 不冻结当前 route 名全集（route 枚举是实现细节，不是外部契约）
- 不冻结当前输出文案措辞（符号语义、Next 措辞、Changes 重命名属 P4c）
- 不冻结 skill_eval 具体维度 taxonomy 或分数阈值
- 不替 P4c 做动作决策（output audit 只分类，不定 keep/simplify/remove）
- 不设计新命名、新层次、新流程

## 表结构定义

### Frozen External Surface 表

| 列 | 含义 |
|---|---|
| `surface` | 被冻结的面（持久化文件路径、JSON schema 名、文档 normative section） |
| `kind` | 分类：`doc_contract` / `machine_truth` / `persistence_red_line` / `gate_contract` / `install_contract` |
| `consumer` | 谁消费：host / user / external_tool（不含 runtime_internal——内部面留在 design.md Persistence Surface 分层表） |
| `freeze_level` | `schema`（字段结构冻结）/ `existence`（存在性冻结，内容可变）/ `semantics`（语义冻结） |
| `why_kept` | 一句话说明为什么不可删 |
| `non-goals / not frozen` | 明确不冻结的方面（防过度冻结） |

### output.py 字段审计表

| 列 | 含义 |
|---|---|
| `field / section` | output.py 中渲染的字段或区块 |
| `source` | 数据来源（handoff / gate / state / derived） |
| `classification` | `machine_truth_projection` / `human_hint` / `internal_taxonomy_leak` |
| `note` | 补充说明（可选）。不做动作决策——动作选择留给 P4c |

## 切片设计

### S1: Frozen External Surface 表

基于已有 design.md Persistence Surface 分层表，补充冻结维度。逐条审计以下消费面：

1. **protocol.md normative sections** — §6 Verifier/ExecutionAuthorizationReceipt 字段、§7 Subject Identity 字段
2. **gate_receipt schema** — current_gate_receipt.json 的宿主可消费字段
3. **handoff machine truth** — current_handoff.json 的宿主可消费字段子集（冻结 artifact/schema 形态，不冻结 Python 内部组装方式）
4. **archive truth** — ArchiveCheckResult / ArchiveApplyResult 的持久化/导出字段
5. **install contract** — SOURCE_CHANNEL / SOURCE_REF / --ref 参数
6. **builtin_catalog contract** — builtin_catalog.generated.json 的 schema / metadata contract（不冻结具体 skill 枚举，不冻结 Python API 签名）
7. **skill_eval gate** — 门禁存在性 + baseline/SLO artifact contract（不冻结当前具体维度 taxonomy 或分数阈值）

### S2: output.py 字段审计

逐字段分类 output.py 渲染内容，产出审计表。此表只做分类，不做 P4c 级别的改造决策。

已知热点（从审计预研）：
- `gate_status` / `blocking_reason` / `plan_completion` 三元组：internal taxonomy leak
- `Changes:` 混合 loaded_files + generated files：分类模糊
- `Next:` 由 required_host_action + route_name 推导：human hint 但混合了内部路由名
- phase label / status symbol：human hint

## 风险

- **过度冻结风险**：把实现细节误冻成外部契约。缓解：`non-goals / not frozen` 列显式标注
- **遗漏风险**：某个外部面未被枚举。缓解：P4b 执行前 re-check，未冻结面默认可删
