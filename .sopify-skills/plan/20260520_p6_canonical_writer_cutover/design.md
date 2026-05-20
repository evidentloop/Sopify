# 技术设计: P6 Canonical Writer Cutover

## 范围边界

**在范围内**：
- 共享契约层建立（`runtime/_models/` 整包迁出为独立顶层 `sopify_contracts/`）
- StateStore 物理提取为 `canonical_writer/`（在共享契约层之上）
- writer_input 契约定义（P6 内部设计契约，不进 protocol.md）
- runtime 消费者重接线
- 不变量 + IO 辅助迁入 canonical_writer/

**不在范围内**：
- Validator 物理提取（P5 已标位置，留后续）
- Copilot 外部 repo 接入（独立证据候选 Copilot Payload-Only Onboarding Proof）
- protocol.md 修改（writer_input 当前是内部设计契约，成熟后再评估协议化）
- 新 CLI 命令或用户面变更

## 架构决策

### DR-1: 共享契约层先行（整包迁出）

**决策**：`runtime/_models/`（1,179 LOC，零 engine 依赖）整包迁出为顶层 `sopify_contracts/`。不接受"留在 runtime 里但算共享层"的口径，也不接受"canonical_writer → runtime._models"的依赖路径。

**理由**：
- S1 发现 `_models/` 已是自洽包：5 文件仅互相引用 + 标准库，无 runtime engine 依赖
- 按 writer-facing / engine-only 拆分单个文件（如 decision.py 547 LOC）= 打断链式引用结构，成本高且脆
- runtime/models.py 本质已是纯 facade（47 LOC re-export），真正的所有权已在 _models/
- 命名 `sopify_contracts/` 而非 `state_contracts/`：包内含 RuntimeResult、SkillMeta、PlanProposalState 等超出 state 范畴的类型

**S1 关键发现**（推翻原假设）：
- 原假设："按 writer-facing / engine-only 边界拆分 models.py"
- 实际："_models/ 整体是共享类型层，不可按消费者拆"
- Writer-facing 有 16 个类型（9 直接 + 7 结构依赖），engine-only 有 7 个，但两组在 decision.py 内链式引用
- 详见 `writer_input_contract.md` §2

### DR-2: read_runtime_handoff 迁出

**决策**：`read_runtime_handoff()` 是纯 IO + 反序列化（~15 LOC），迁入 canonical_writer。`build_runtime_handoff()` 是 builder 逻辑（~230 LOC，engine 耦合），留 runtime。

**理由**：canonical_writer.get_current_handoff() 需要调用 reader。如果 reader 留 runtime = runtime 回指。读写对称性也支持 reader 和 writer 在同一层。

### DR-3: writer_input 不进 protocol

**决策**：writer_input 当前是 P6 内部设计契约。等 canonical_writer 跑实 + 宿主稳定产出合法输入后，再评估是否协议化进 protocol.md。

**理由**：过早协议化 = 过早承诺。P6 先把接口定义清楚、验证可行，才有足够 evidence 升格。

## 技术方案

### 总体策略

"Strangler fig without migration"——无用户，直接切出新栈，runtime 原地退为 legacy。

```
当前（三层混在 runtime/ 里）:
  runtime/_models/         ← 共享类型定义（1,179 LOC，零 engine 依赖）
  runtime/models.py        ← 纯 facade re-export（47 LOC）
  runtime/state.py         ← StateStore (内部类)
  runtime/state_invariants.py ← 不变量校验
  runtime/handoff.py       ← read + build

目标（三层物理分离）:
  sopify_contracts/          ← 共享契约层（从 runtime/_models/ 整包迁出）
    core.py                  ← RunState, RuntimeConfig, ExecutionGate, RouteDecision, ...
    decision.py              ← ClarificationState, DecisionState, DecisionSubmission, ...
    handoff.py               ← RuntimeHandoff, RecoveredContext, RuntimeResult, ...
    artifacts.py             ← PlanArtifact, KbArtifact
    proposal.py              ← PlanProposalState

  canonical_writer/          ← 写层（StateStore + IO + invariants）
    __init__.py              # re-export StateStore
    store.py                 # StateStore 类 + normalize_session_id + _stamp_provenance
    io.py                    # read_runtime_handoff + _read_json/_write_json
    invariants.py            # 从 state_invariants.py 迁出
    _time.py                 # iso_now（4 处重复的统一源）
    _resume.py               # CheckpointRequestError + validate_develop_resume_context

  runtime/                   ← 编排层（engine/gate/router 等核心逻辑）
    models.py                ← 临时兼容桥：re-export from sopify_contracts
    _models/                 ← 删除（已迁出）
    state.py                 ← 临时兼容桥：re-export StateStore from canonical_writer
    state_invariants.py      ← 临时兼容桥：re-export from canonical_writer.invariants
    handoff.py               ← build_runtime_handoff 留此处（engine 耦合），read 已迁出

  依赖方向（严格单向）:
    sopify_contracts ← canonical_writer ← runtime
                     ← 新宿主
```

### 提取目标分析

**层次一：sopify_contracts/（共享契约层）**

从 `runtime/_models/` 整包平移，改 package name + 修内部 import。

| 文件 | LOC | 类型数 | 说明 |
|------|-----|--------|------|
| core.py | 330 | 6 | RunState, RuntimeConfig, ExecutionGate, RouteDecision, ExecutionSummary, SkillMeta + 辅助 |
| decision.py | 547 | 10 | ClarificationState, DecisionState, DecisionSubmission + 7 个子类型 |
| handoff.py | 170 | 4 | RuntimeHandoff, RecoveredContext, RuntimeResult, SkillActivation |
| artifacts.py | 61 | 2 | PlanArtifact, KbArtifact |
| proposal.py | 71 | 1 | PlanProposalState |
| **合计** | **1,179** | **23** | **零 engine 依赖，自洽包** |

> 迁移成本低：_models/ 仅互相引用 + 标准库。改 package 后修内部 import 路径即可，无逻辑变更。

**层次二：canonical_writer/（写层）**

StateStore 及其直接依赖提取：

| 组件 | 来源 | LOC (估) | 目标 |
|------|------|----------|------|
| StateStore 类 | state.py | ~276 | canonical_writer/store.py |
| state_invariants | state_invariants.py | ~100 | canonical_writer/invariants.py |
| IO helpers | state.py 内 | ~15 | canonical_writer/io.py |
| read_runtime_handoff | handoff.py | ~15 | canonical_writer/io.py |
| iso_now | state.py 内 | ~3 | canonical_writer/_time.py |
| normalize_session_id | state.py 内 | ~12 | canonical_writer/store.py |
| _stamp_provenance | state.py 内 | ~30 | canonical_writer/store.py |
| _validate_resume | state.py 内 | ~18 | canonical_writer/_resume.py |
| checkpoint_request 片段 | checkpoint_request.py | ~63 | canonical_writer/_resume.py |
| **canonical_writer 总计** | | **~530 LOC** | |

> P5 口径"~210 LOC candidate-kernel"= get/set/clear 方法族。实际含随迁辅助 ~530 LOC。

**不随迁（留 runtime）**：
- build_runtime_handoff (~230 LOC) — engine 耦合 builder
- checkpoint_request.py 主体 (~330 LOC) — 依赖 runtime.clarification
- state.py 非 StateStore 部分（local_* 函数族 ~35 LOC、session cleanup ~57 LOC、stable_request_sha1/summarize_request_text ~13 LOC）

**P6 总移动量**：~1,179 (sopify_contracts) + ~530 (canonical_writer) = **~1,709 LOC**，其中 sopify_contracts 是纯平移（零逻辑变更），canonical_writer 是提取（需解依赖）。

### S1: writer_input 契约规格 + models 分割分析 ✅

已完成。输出：`writer_input_contract.md`。

关键结论：
1. StateStore 9 类 writer-facing 直接类型 + 7 类结构依赖，但与 engine-only 类型在 decision.py 内链式引用，不可按消费者拆
2. 推翻原假设"按 writer/engine 拆 models.py"→ 改为"整包迁出 _models/ 为 sopify_contracts/"
3. Writer-side invariants 5 个函数（validate_phase, _validate_state_resume_contract, validate_paired_host_truth_write, validate_resolution_id, normalize_session_id）
4. Caller-side preconditions = 构造合法对象 + 正确 phase + 完整 resume_context
5. IO 契约 = atomic write via NamedTemporaryFile + replace, utf-8, indent=2, sort_keys=True

### S2: 物理提取

分两步：

**S2.1: sopify_contracts/ 建立**
1. `git mv runtime/_models/ sopify_contracts/`（保留 git history）
2. 修内部 import：`from .core import ...` 不变（包内相对引用不受 rename 影响）
3. 创建 `sopify_contracts/__init__.py`：re-export 全部 23 个公开类型
4. `runtime/models.py` 改为：`from sopify_contracts import *`（deprecated bridge）
5. 所有 `from runtime._models.xxx import` → `from sopify_contracts.xxx import`
6. 所有 `from .models import` / `from runtime.models import` → 按需切换（S3 兼容桥期间可暂不改）

**S2.2: canonical_writer/ 建立**
```
canonical_writer/
  __init__.py           # re-export StateStore
  store.py              # StateStore 类 + normalize_session_id + _stamp_provenance
  io.py                 # read_runtime_handoff + _read_json + _write_json
  invariants.py         # 从 state_invariants.py 迁出
  _time.py              # iso_now (4 处重复的统一源)
  _resume.py            # CheckpointRequestError + validate_develop_resume_context + 常量
```

canonical_writer 依赖图：`canonical_writer → sopify_contracts`（无 runtime 依赖）。

### S3: 消费者重接线

**sopify_contracts 消费者**（~34 文件 import from runtime.models / runtime._models）：

| 消费者分类 | 文件数 | 策略 |
|-----------|--------|------|
| runtime 内部 | ~30 | `from runtime.models import X` 暂不改（走 deprecated bridge） |
| tests | ~4 | `from runtime.models import X` 或 `from runtime._models.xxx import X` → 切换 |

**canonical_writer 消费者**（原 StateStore 消费者，~15 文件）：

| 消费者分类 | 文件数 | 策略 |
|-----------|--------|------|
| runtime 核心（engine, gate, bridges） | ~10 | import 路径切换 |
| installer（inspection.py） | 1 | import 路径切换 |
| scripts | 2 | import 路径切换 |
| tests | ~5 | import 路径切换 + fixture 不变 |

**临时兼容桥（仅过渡用，非长期设计）**：
- `runtime/models.py` → `from sopify_contracts import *`（deprecated，全量 re-export）
- `runtime/state.py` → `from canonical_writer import StateStore`（deprecated）
- `runtime/state_invariants.py` → `from canonical_writer.invariants import *`（deprecated）

目标：S4 阶段所有消费者切换到新路径后，移除全部兼容桥。

### S4: 验证 + 清理

1. 721+ tests 全过（零行为变更）
2. iso_now 重复清理：4 处定义 → 统一从 `canonical_writer/_time.py` 导入
3. runtime 内部 import 从兼容桥切换到直接 import sopify_contracts / canonical_writer
4. 移除临时兼容桥（确认无旧路径引用后删除 re-export）
5. 删除 `runtime/_models/`（已迁出到 sopify_contracts/）
6. canonical_writer/ import 审计：仅依赖 sopify_contracts + 标准库
7. 蓝图同步：design.md 三层分离表标"已提取"

## 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| _models/ 迁出后 import 路径大面积变更 | 中 | S2.1 先建 runtime/models.py 兼容桥，所有 `from runtime.models import` 继续工作 |
| 提取后循环导入 | 中 | sopify_contracts 零 engine 依赖（已确认）；canonical_writer 仅依赖 sopify_contracts |
| 兼容桥残留变双归属 | 中 | S4 显式移除桥 + grep 审计，tasks 有独立 checklist 项 |
| invariant 遗漏 | 低 | S1 已逐方法列 invariant（见 writer_input_contract.md §3），S4 测试兜底 |
| 消费者遗漏 | 低 | grep 全量扫描，CI 兜底 |
| sopify_contracts 命名后续争议 | 低 | 当前覆盖全部 23 个类型 + 辅助函数，语义中性 |
