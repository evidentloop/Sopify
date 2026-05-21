# P6 Receipt: Canonical Writer Cutover

## 基本信息

| 字段 | 值 |
|------|------|
| Plan ID | 20260520_p6_canonical_writer_cutover |
| 状态 | **完成** |
| 分支 | plan/p6-canonical-writer-cutover |
| 前置 | P5 Contract Surface Shrinkage ✅ |

---

## 核心结论（一句话）

runtime/ 的写层（StateStore + invariants + IO）和共享类型层（_models/）已物理分离为三个独立包：`sopify_contracts`（1,227 LOC 共享类型）、`canonical_writer`（605 LOC 写层）、`runtime`（编排层）。依赖方向严格单向：sopify_contracts ← canonical_writer ← runtime，无回指。新宿主可直接 import canonical_writer 获得完整写能力，无需依赖 runtime。

---

## 提取前后对比

### LOC 变动

| 模块 | 提取前 | 提取后 | 说明 |
|------|--------|--------|------|
| sopify_contracts/ | 0（不存在） | 1,227 LOC (6 files) | 从 runtime/_models/ 整包迁出 |
| canonical_writer/ | 0（不存在） | 605 LOC (6 files) | 从 runtime/state.py + state_invariants.py + handoff.py + checkpoint_request.py 提取 |
| runtime/state.py | ~500 LOC | ~130 LOC | 仅保留 runtime-specific helpers |
| runtime/state_invariants.py | ~110 LOC | 已删除 | 所有消费者直接引用 canonical_writer.invariants |
| runtime/_models/ | 1,179 LOC | 已删除 | 整包迁至 sopify_contracts/ |

### 分支总 diff（vs main）

```
62 files changed, 1,405 insertions(+), 551 deletions(+)
```

### 新增顶层包

| 包 | 文件 | LOC | 职责 |
|----|------|-----|------|
| sopify_contracts/ | __init__.py, core.py, decision.py, handoff.py, artifacts.py, proposal.py | 1,227 | 共享类型定义（23 个公开类型，零外部依赖） |
| canonical_writer/ | __init__.py, store.py, io.py, invariants.py, _time.py, _resume.py | 605 | StateStore + IO + invariants + 时间戳 + resume 校验 |

---

## 三层依赖图（已验证）

```
sopify_contracts/          仅依赖标准库
       ↑
canonical_writer/          仅依赖 sopify_contracts + 标准库
       ↑
runtime/                   依赖 canonical_writer + sopify_contracts
       ↑
新宿主                     直接依赖 canonical_writer + sopify_contracts（跳过 runtime）
```

**依赖验证方法**：AST 扫描 canonical_writer/ 和 sopify_contracts/ 全量 import，确认无 runtime.* 引用。

---

## 决策记录

| ID | 决策 | 理由 |
|----|------|------|
| DR-1 | 共享契约层先行（_models/ 整包迁出为 sopify_contracts/） | _models/ 已自洽零 engine 依赖；按 writer/engine 拆 decision.py = 打断 547 LOC 链式引用 |
| DR-2 | read_runtime_handoff 迁入写层 | 纯 IO + 反序列化 ~15 LOC；build_runtime_handoff ~230 LOC engine 耦合留 runtime |
| DR-3 | writer_input 不进 protocol | 当前是 P6 内部设计契约，成熟后再评估协议化 |

---

## 执行历史

| Commit | 阶段 | 说明 |
|--------|------|------|
| 392f528 | Plan | 标准方案包 |
| 578b9e5 | S0 | 架构决策 DR-1/2/3 + 共享基础层设计 |
| 3ac2ed7 | S1 | writer_input 契约完成 + γ 架构拍板 |
| 215178e | S2.1 | sopify_contracts/ 共享契约层提取 |
| a7be092 | S2.2 | canonical_writer/ 写层提取 |
| 5a1a2d4 | S3 | 消费者重接线（非 runtime 生产消费者切换新路径） |
| ad799a3 | S4 | 代码清理 + 文档同步（iso_now 统一、桥移除、import 重接线、writer stamp 切换） |

---

## 残留项

### runtime/models.py（deprecated re-export facade）

仍有 3 处测试消费者（runtime_test_support.py, test_action_intent.py, test_runtime_gate.py）通过 `from runtime.models import ...` 引用。模块已标 DEPRECATED，功能上是 sopify_contracts 的 re-export。后续测试重构时可切换为直接 import sopify_contracts。

### 全量测试回归

S2.1/S2.2/S3 各阶段均在完整 Python 环境验证 721 passed。S4 代码清理后全量回归已独立确认：721 passed, 49 subtests passed（Python 3.14.4, pytest 9.0.3）。

---

## writer_input 契约可用性评估

`writer_input_contract.md` 定义了 canonical_writer (StateStore) 的完整外部接口：

- **7 个直接写入方法** + 4 个复合方法 + 构造函数
- **不变量归属**明确：5 个 writer-side invariant、4 个 provenance stamp、4 项 caller-side precondition
- **IO 契约**：atomic write + utf-8 + indent=2 + sort_keys + 尾部换行
- **Observability 契约**：writer stamp "canonical_writer" + written_at + state_kind/scope

**可用性结论**：新宿主可凭此文档 + canonical_writer 包完成状态写入集成，无需阅读 runtime 源码。契约当前为 P6 内部设计文档（DR-3），待实际新宿主接入后再评估协议化进 protocol.md。

---

## 蓝图变更

| 文件 | 变更 |
|------|------|
| `plan/.../design.md` | 三层分离架构图标"已提取完成"，各层 LOC 标注实际值 |
| `blueprint/tasks.md` | P6 标完成 + archive_ready |
| `blueprint/README.md` | 最近归档指向 P6 |

---

## 产出文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `writer_input_contract.md` | S1 产出 | StateStore 外部接口 + 类型边界 + 不变量 + IO 契约 |
| `background.md` | 方案背景 | P6 proposal |
| `design.md` | 技术设计 | 三层分离架构 + 决策记录 + 提取目标分析 |
| `tasks.md` | 任务清单 | S1-S4 完成记录 |
| `receipt.md` | 本文件 | P6 结论报告 |
