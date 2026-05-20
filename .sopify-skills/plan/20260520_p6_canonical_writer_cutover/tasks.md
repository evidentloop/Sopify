---
plan_id: 20260520_p6_canonical_writer_cutover
feature_key: p6_canonical_writer_cutover
level: standard
lifecycle_state: active
---

# 任务清单

## 决策记录

### DR-1: 共享基础层先行

- **决策**：先建顶层共享 state/model/IO 基础层（canonical_writer/），再在其上放 StateStore
- **不接受**："models.py 留在 runtime 里但算共享层" 的口径
- **路径**：writer-facing 类型迁出 → runtime/models.py 临时 re-export → 逐步清理

### DR-2: read_runtime_handoff 迁出

- **决策**：纯 IO + 反序列化（~15 LOC）迁入共享层。build_runtime_handoff（~230 LOC，engine 耦合）留 runtime
- **理由**：canonical_writer.get_current_handoff() 需要 reader → 留 runtime = 回指

### DR-3: writer_input 不进 protocol

- **决策**：当前是 P6 内部设计契约。成熟后再评估协议化进 protocol.md
- **理由**：过早协议化 = 过早承诺

## S1: writer_input 契约规格 + models 分割分析

- [ ] 逐方法列出 StateStore 每个 set 方法的入参类型 + 必要字段 + 前置条件
- [ ] models.py 分割分析：哪些类型是 writer-facing（必须迁出）vs engine-only（留 runtime）
- [ ] 分离 writer-side invariant（writer 自行校验）vs caller-side precondition（caller 负责）
- [ ] IO 契约文档：文件路径 convention、atomic write 语义、JSON encoding
- [ ] Observability 契约：writer stamp、timestamp、provenance 规则
- [ ] 输出 `writer_input_contract.md`

## S2: 物理提取（方案 A 已拍板：canonical_writer/ 顶层模块）

- [ ] 创建 `canonical_writer/` 目录 + `__init__.py`
- [ ] 从 runtime/models.py 迁出 writer-facing 类型 → `canonical_writer/models.py`（过渡命名，S1 分析后可能改为 state_models.py / contracts.py）
- [ ] 从 state.py 提取 StateStore 类 → `canonical_writer/store.py`
- [ ] 从 state.py 提取 IO helpers（_read_json, _write_json）→ `canonical_writer/io.py`
- [ ] 从 handoff.py 提取 read_runtime_handoff → `canonical_writer/io.py`
- [ ] 迁移 state_invariants.py → `canonical_writer/invariants.py`
- [ ] 提取 iso_now → `canonical_writer/_time.py`（4 处重复的统一源）
- [ ] 提取 normalize_session_id, _stamp_provenance, _validate_resume → `canonical_writer/store.py` / `_resume.py`
- [ ] 从 checkpoint_request.py 提取 CheckpointRequestError + validate_develop_resume_context + 常量 (~60 LOC) → `canonical_writer/_resume.py`
- [ ] import 审计：确认 canonical_writer/ 无 runtime.* 依赖

## S3: 消费者重接线

- [ ] runtime 核心文件（engine, gate, bridges 等 ~10 文件）import 路径切换
- [ ] installer/inspection.py import 路径切换
- [ ] scripts/ import 路径切换
- [ ] tests/ import 路径切换
- [ ] 临时兼容桥（仅过渡用）：
  - [ ] runtime/state.py → re-export StateStore（deprecated）
  - [ ] runtime/models.py → re-export 已迁出的 writer-facing 类型（deprecated），engine-only 类型继续原位
  - [ ] runtime/state_invariants.py → re-export invariants（deprecated）

## S4: 验证 + 清理

- [ ] 全量测试回归：721+ tests 全过
- [ ] iso_now 重复清理：4 处定义统一为从 `_time.py` 导入
  - `runtime/handoff.py:_iso_now` (line 168)
  - `runtime/decision.py:iso_now` (line 609)
  - `runtime/clarification.py:iso_now` (line 389)
  - `runtime/state.py:iso_now` (line 317) → 迁入 canonical_writer/_time.py
- [ ] 移除临时兼容桥：确认无旧路径引用后删除所有 re-export
- [ ] canonical_writer/ import 审计：无 engine/gate/router 等 runtime 核心依赖
- [ ] state.py / models.py / state_invariants.py 瘦身确认
- [ ] 蓝图同步：design.md 三层分离表 canonical writer 列标"已提取"

## S5: 结论报告

- [ ] 标准 receipt 格式
- [ ] 提取前后 LOC 对比
- [ ] canonical_writer/ 依赖图（证明无 runtime 回指）
- [ ] writer_input contract 可用性评估
- [ ] 归档至 history/
