# P5 Receipt: Contract Surface Shrinkage

## 基本信息

| 字段 | 值 |
|------|------|
| Plan ID | 20260520_p5_contract_surface_shrinkage |
| 状态 | **完成**（可归档；Onboarding Proof 3 面留 pending，不挡结论） |
| 分支 | plan/p5-contract-surface-shrinkage |
| 证据基础 | P4d Copilot CLI pilot + S2.1 Shadow Writer Gap Analysis |

---

## 核心结论（一句话）

payload_capable 只消费；candidate-kernel 收缩为 StateStore ~210 LOC；P6 直接切到 lightweight canonical writer 新栈（builder 留 engine 侧，writer_input 契约独立定义），新宿主直接适配此层。无线上用户，零迁移负担，可直接面向目标态。

---

## 裁定结果

### 最终分类

| disposition | surface 数 | LOC | 占比 |
|-------------|-----------|-----|------|
| keep-cross-tier | 10 | ~2,500 | ~10% |
| keep-candidate-kernel | 1 | ~210 | ~0.8% |
| keep-deep-only | 46 | ~21,400 | ~84.5% |
| deleted | 1 | ~8 | <0.1% |

> 58 个 sub-surface 逐项裁定。validator-bearing ~1K-1.2K LOC 作为分析标注已包含在 keep-deep-only 中。

### 代码变更

| 变更 | 文件 | LOC |
|------|------|-----|
| 删除死代码 | `runtime/handoff.py` — `write_runtime_handoff` | -8 |
| 清理 unused import | `runtime/handoff.py` — `NamedTemporaryFile` | -1 |
| 测试回归 | 721 passed, 49 subtests passed | — |

---

## 核心发现

### 1. Candidate-Kernel = StateStore ~210 LOC

P5 最重要的结论：真正的 candidate-kernel **只有 StateStore 的 get/set/clear 方法族**。

Shadow Writer Gap Analysis（结论 B）证明：
- 4 个 builder 面 (~470 LOC) 深度耦合 engine → 降级 keep-deep-only
- StateStore IO (~210 LOC) 部分可行 → 保持 keep-candidate-kernel
- candidate-kernel 从 provisional 的 ~680 LOC 缩减至 ~210 LOC

### 2. Canonical Writer Authority 不需要独立建模

非 deep host 核心需求是读取（P4d 已验证），不是写入。Writer authority 本质是"哪个 engine"的问题，不是"谁被授权写"的问题。当前 "deep = read+write, 其他 = read-only" 隐式规则足够。

### 3. Validator 物理分层形状已识别

~1K-1.2K LOC 验证逻辑可提取（action_intent ~450, deterministic_guard ~200, workspace_preflight ~250-350, installer/validate ~100-150）。但 Validator 物理提取是 P6+ 决策，P5 仅识别位置。

### 4. S1 Delete 估算修正

S1 估计 ~137 LOC 可删除 → S4 验证后实际可安全删除 ~8 LOC。差异原因：
- `iso_now` 等工具函数重复是故意的（避免循环导入 state.py↔handoff.py）
- `_models/` 工具函数有外部调用方
- 重构到共享 `_utils.py` 属 P6 清理范围

### 5. Cross-Tier 文档覆盖完整

10/10 cross-tier 面均有 docstring + blueprint/design.md 覆盖。`protocol.md` 作为独立文件不存在是既有状态。

---

## 决策记录

| ID | 决策 | 理由 |
|----|------|------|
| DR-1 | Shadow Writer 结论 B（部分可行） | Builder 不可行，StateStore 部分可行。candidate-kernel 680→210 LOC |
| DR-2 | Canonical writer authority 不独立建模 | 读写分离已充分，protocol + Validator 可覆盖 |
| DR-3 | Runtime 退场路线写入蓝图 | 三层分离：payload_capable(消费) / canonical writer(生产) / runtime(legacy)。无用户=可激进，P6 直接提取 writer + 适配新宿主 |

---

## 蓝图变更

| 文件 | 变更 |
|------|------|
| `blueprint/design.md` | 新增 "Runtime 退场路线" 小节：三层分离定位 + 退场节奏 + 4 条约束 |
| `blueprint/tasks.md` | P4d 标完成，P5 标 completed + archive_ready |
| `blueprint/README.md` | focus→P5，latest archive→P4d |

---

## P6 输入

### 最小必留面清单（Candidate-Kernel）

| 面 | LOC | 位置 | P6 动作 |
|----|-----|------|--------|
| StateStore get/set/clear | ~210 | runtime/state.py | 直接切出为 lightweight canonical writer + 定义 writer_input 契约 |

### Validator 提取候选

| 面 | LOC | 位置 | P6 动作 |
|----|-----|------|--------|
| action_intent 验证逻辑 | ~450 | runtime/action_intent.py | 物理提取为独立 Validator 模块 |
| deterministic_guard | ~200 | runtime/deterministic_guard.py | 同上 |
| workspace_preflight 验证部分 | ~250-350 | runtime/workspace_preflight.py | 部分提取（依赖 installer 类型） |
| installer/validate | ~100-150 | installer/validate.py | 部分提取 |

### 待 Onboarding Proof 的 3 面

| 面 | LOC | 位置 |
|----|-----|------|
| installer/hosts/base.py | ~122 | HostAdapter 接口 |
| installer/bootstrap_workspace.py | ~1,358 | Workspace bootstrap |
| installer/models.py cross-tier 类型 | — | 独立化时机待定 |

### iso_now 重复清理

5 处 `iso_now` 重复（state.py, handoff.py, decision.py, clarification.py, state.py:local_iso_now）。因循环导入不可直接合并。建议 P6 提取到共享 `runtime/_time_utils.py`。

---

## 产出文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `surface_inventory.md` | S1 产出 | 两轮清点（模块级 + 行级 sub-surface） |
| `provisional_adjudication.md` | S3 产出 | Final 裁定表（Shadow Writer applied） |
| `shadow_writer_analysis.md` | S2.1 产出 | 5 面逐项分析 + A/B/C 结论 |
| `background.md` | 方案背景 | P5 proposal |
| `design.md` | 技术设计 | 5 slices + 4-way classification |
| `tasks.md` | 任务清单 | S1-S4 完成，S5 完成 |
| `receipt.md` | 本文件 | P5 结论报告 |
