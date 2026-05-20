# 技术设计: P6 Canonical Writer Cutover

## 范围边界

**在范围内**：
- 共享基础层建立（writer-facing 类型 + IO + invariants 从 runtime 迁出）
- StateStore 物理提取为 canonical_writer（在共享基础层之上）
- writer_input 契约定义（P6 内部设计契约，不进 protocol.md）
- runtime 消费者重接线

**不在范围内**：
- Validator 物理提取（P5 已标位置，留后续）
- Copilot 外部 repo 接入（独立证据候选 Copilot Payload-Only Onboarding Proof）
- protocol.md 修改（writer_input 当前是内部设计契约，成熟后再评估协议化）
- 新 CLI 命令或用户面变更

## 架构决策

### DR-1: 共享基础层先行

**决策**：P6 先建顶层共享 state/model/IO 基础层，再在其上放 canonical_writer。不接受"models.py 留在 runtime 里但算共享层"的口径。

**理由**：
- StateStore 依赖 RunState, RuntimeHandoff, DecisionState, PlanArtifact, RouteDecision, RuntimeConfig 等类型。如果这些留在 runtime/models.py，canonical_writer/ import runtime.models = runtime 回指
- runtime/models.py 本质已是 facade（无 engine 耦合），说明"把类型所有权挪出去 + runtime re-export"是低风险路径
- dict/JSON 接口退化类型安全和测试覆盖，不值得

### DR-2: read_runtime_handoff 迁出

**决策**：`read_runtime_handoff()` 是纯 IO + 反序列化（~15 LOC），迁入共享层。`build_runtime_handoff()` 是 builder 逻辑（~230 LOC，engine 耦合），留 runtime。

**理由**：canonical_writer.get_current_handoff() 需要调用 reader。如果 reader 留 runtime = runtime 回指。读写对称性也支持 reader 和 writer 在同一层。

### DR-3: writer_input 不进 protocol

**决策**：writer_input 当前是 P6 内部设计契约。等 canonical_writer 跑实 + 宿主稳定产出合法输入后，再评估是否协议化进 protocol.md。

**理由**：过早协议化 = 过早承诺。P6 先把接口定义清楚、验证可行，才有足够 evidence 升格。

## 技术方案

### 总体策略

"Strangler fig without migration"——无用户，直接切出新栈，runtime 原地退为 legacy。

```
当前:
  runtime/models.py        ← 所有类型定义
  runtime/state.py         ← StateStore (内部类)
  runtime/state_invariants.py ← 不变量校验
  runtime/handoff.py       ← read + build

目标:
  canonical_writer/
    models.py              ← writer-facing 类型（从 runtime/models.py 迁出，过渡命名）
    store.py               ← StateStore 类
    io.py                  ← read_runtime_handoff + _read_json/_write_json
    invariants.py          ← 从 state_invariants.py 迁出
    _time.py               ← iso_now（4 处重复的统一源）
    _resume.py             ← CheckpointRequestError + validate_develop_resume_context

  runtime/
    models.py              ← 临时兼容桥：re-export 已迁出的 writer-facing 类型；engine-only 类型继续原位
    state.py               ← 临时兼容桥：re-export StateStore from canonical_writer
    state_invariants.py    ← 临时兼容桥：re-export from canonical_writer.invariants
    handoff.py             ← build_runtime_handoff 留此处（engine 耦合），read 已迁出

  新宿主 → canonical_writer → state/*.json（无 runtime 依赖）
  engine → canonical_writer → state/*.json（通过新路径或兼容桥）
```

### 提取目标分析

**StateStore 类**（runtime/state.py:40-315, 类整体 ~276 LOC，candidate-kernel ~210 LOC）

核心方法族（7 domain × get/set/clear = 18+ 方法）：

| domain | get | set | clear | invariants |
|--------|-----|-----|-------|-----------|
| current_run | ✅ | ✅ phase_validate | ✅ | resolution_id stamp |
| last_route | ✅ | ✅ | — | json serialization |
| current_plan | ✅ | ✅ | ✅ | — |
| current_clarification | ✅ | ✅ phase_validate+resume | ✅ | provenance stamp |
| current_decision | ✅ | ✅ phase_validate+resume | ✅ | provenance stamp |
| current_handoff | ✅ | ✅ | ✅ | observability meta |
| current_archive_receipt | ✅ | ✅ | ✅ | observability meta |
| host_facing_truth | — | ✅ compound | — | paired write + resolution_id |

**提取规模估算**（candidate-kernel ~210 LOC + 随迁辅助）：

| 组件 | 来源 | LOC (估) | 目标 |
|------|------|----------|------|
| StateStore 类 | state.py | ~276 | canonical_writer/store.py |
| state_invariants | state_invariants.py | ~100 | canonical_writer/invariants.py |
| IO helpers | state.py 内 | ~15 | canonical_writer/io.py |
| read_runtime_handoff | handoff.py | ~15 | canonical_writer/io.py |
| iso_now | state.py 内 | ~3 | canonical_writer/_time.py |
| normalize_session_id | state.py 内 | ~12 | canonical_writer/store.py |
| _stamp_provenance | state.py 内 | ~20 | canonical_writer/store.py |
| _validate_resume | state.py 内 | ~20 | canonical_writer/_resume.py |
| checkpoint_request 片段 | checkpoint_request.py | ~60 | canonical_writer/_resume.py |
| writer-facing 类型 | models.py (部分) | TBD | canonical_writer/models.py |
| **canonical_writer 总计** | | **~520+ LOC** | |

> 注：P5 口径"~210 LOC candidate-kernel"是 get/set/clear 方法族规模。实际提取含随迁辅助 + 类型迁出，总量 ~520+ LOC。类型迁出规模取决于 S1 分析（哪些类型是 writer-facing vs engine-only）。

**不随迁（留 runtime）**：
- build_runtime_handoff (~230 LOC) — engine 耦合 builder
- checkpoint_request.py 主体 (~330 LOC) — 依赖 runtime.clarification
- engine-only 类型（如果有）— S1 分析后确定

### S1: writer_input 契约规格 + models 分割分析

定义 canonical writer 的对外接口，同时确定 models.py 的分割边界：

1. **WriterInput 类型族**：每个 set 方法的入参即一个 writer_input。不引入新的通用容器——保持现有强类型签名
2. **models.py 分割**：哪些类型是 writer-facing（必须迁出）vs engine-only（留 runtime）
3. **Invariant 契约**：哪些校验是 writer 自己做的 vs caller 负责的
4. **IO 契约**：文件路径 convention、atomic write 语义、JSON 编码约定
5. **Observability 契约**：writer stamp（writer="canonical_writer"）、timestamp、provenance

输出：`writer_input_contract.md`

### S2: 物理提取

创建 `canonical_writer/` 顶层模块（方案 A，已拍板）：

```
canonical_writer/
  __init__.py           # re-export StateStore
  store.py              # StateStore 类 + normalize_session_id + _stamp_provenance
  models.py             # writer-facing 类型（从 runtime/models.py 迁出）
  io.py                 # read_runtime_handoff + _read_json + _write_json
  invariants.py         # 从 state_invariants.py 迁移
  _time.py              # iso_now (4 处重复的统一源)
  _resume.py            # CheckpointRequestError + validate_develop_resume_context + 常量
```

### S3: 消费者重接线

runtime 内 ~15 个文件导入 StateStore / models / invariants，需逐个改为从新模块导入。

| 消费者分类 | 文件数 | 策略 |
|-----------|--------|------|
| runtime 核心（engine, gate, bridges） | ~10 | import 路径切换，行为不变 |
| installer（inspection.py） | 1 | import 路径切换 |
| scripts（sopify_runtime.py, skill-eval） | 2 | import 路径切换 |
| tests | ~5 | import 路径切换 + fixture 不变 |

**临时兼容桥（仅过渡用，非长期设计）**：
- `runtime/state.py` → `from canonical_writer import StateStore`（deprecated）
- `runtime/models.py` → `from canonical_writer.models import *`（deprecated，仅 re-export 已迁出的 writer-facing 类型；engine-only 类型继续原位）
- `runtime/state_invariants.py` → `from canonical_writer.invariants import *`（deprecated）

目标：S4 阶段所有消费者切换到新路径后，移除全部兼容桥。

### S4: 验证 + 清理

1. 721+ tests 全过（零行为变更）
2. iso_now 重复清理：4 处定义 → 统一从 `canonical_writer/_time.py` 导入
3. 移除临时兼容桥（确认无旧路径引用后删除 re-export）
4. canonical_writer/ import 审计：无 runtime.* 依赖
5. state.py / models.py / state_invariants.py 瘦身确认

## 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| models.py 分割边界不清 | 中-高 | S1 先做完整类型依赖图，确定 writer-facing vs engine-only 边界 |
| 提取后循环导入 | 中 | S2 先画完整 import graph，确认新模块无回指 runtime |
| 兼容桥残留变双归属 | 中 | S4 显式移除桥 + grep 审计，tasks 有独立 checklist 项 |
| invariant 遗漏 | 中 | S1 逐方法列 invariant，S4 用现有测试覆盖验证 |
| 消费者遗漏 | 低 | grep 全量扫描，CI 兜底 |
| 新宿主适配性 | 低-中 | writer_input contract 由 S1 文档化，但真实适配需后续宿主试点验证 |
