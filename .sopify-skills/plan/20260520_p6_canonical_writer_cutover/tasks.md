---
plan_id: 20260520_p6_canonical_writer_cutover
feature_key: p6_canonical_writer_cutover
level: standard
lifecycle_state: active
---

# 任务清单

## 决策记录

### DR-1: 共享契约层先行（整包迁出）

- **决策**：`runtime/_models/`（1,179 LOC）整包迁出为顶层 `sopify_contracts/`。不接受 δ（canonical_writer → runtime._models）作为目标态
- **S1 发现**：_models/ 已自洽零 engine 依赖；按 writer/engine 拆 decision.py = 打断 547 LOC 链式引用
- **不接受**："models.py 留在 runtime 里但算共享层" 的口径
- **路径**：_models/ 整包迁出 → runtime/models.py 变 re-export bridge（deprecated）→ S4 移除

### DR-2: read_runtime_handoff 迁出

- **决策**：纯 IO + 反序列化（~15 LOC）迁入写层（canonical_writer/io.py）。build_runtime_handoff（~230 LOC，engine 耦合）留 runtime
- **理由**：canonical_writer.get_current_handoff() 需要 reader → 留 runtime = 回指

### DR-3: writer_input 不进 protocol

- **决策**：当前是 P6 内部设计契约。成熟后再评估协议化进 protocol.md
- **理由**：过早协议化 = 过早承诺

## S1: writer_input 契约规格 + models 分割分析 ✅

- [x] 逐方法列出 StateStore 每个 set 方法的入参类型 + 必要字段 + 前置条件
- [x] models.py 分割分析 → 结论：不按 writer/engine 拆，整包迁出 _models/ 为 sopify_contracts/
- [x] 分离 writer-side invariant（5 个函数）vs caller-side precondition
- [x] IO 契约文档：atomic write + utf-8 + indent=2 + sort_keys
- [x] Observability 契约：writer stamp + written_at + state_kind/scope
- [x] 输出 `writer_input_contract.md`

## S2: 物理提取（两步）

### S2.1: sopify_contracts/ 共享契约层 ✅

- [x] `git mv runtime/_models/ sopify_contracts/`（保留 git history）
- [x] 创建 `sopify_contracts/__init__.py`：re-export 全部 23 个公开类型
- [x] 修内部 import（无需修改，相对导入自动适配）
- [x] `runtime/models.py` 改为 `from sopify_contracts import *`（deprecated bridge）
- [x] 全量 `from runtime._models.xxx import` → `from sopify_contracts.xxx import`（tests 等直接引用 _models 的）
- [x] import 审计：确认 sopify_contracts/ 无 runtime.* 依赖
- [x] bundle 基础设施更新（sync-runtime-assets.sh, validate.py, runtime_bundle.py, bootstrap_workspace.py, inspection.py）
- [x] 测试 copytree/rmtree 模式修复（test_installer_status_doctor.py ×3, test_runtime_gate.py ×1, check-install-payload-bundle-smoke.py ×1）
- [x] 全量测试通过：721 passed

### S2.2: canonical_writer/ 写层

- [ ] 创建 `canonical_writer/` 目录 + `__init__.py`
- [ ] 从 state.py 提取 StateStore 类 → `canonical_writer/store.py`
- [ ] 从 state.py 提取 IO helpers（_read_json, _write_json）→ `canonical_writer/io.py`
- [ ] 从 handoff.py 提取 read_runtime_handoff → `canonical_writer/io.py`
- [ ] 迁移 state_invariants.py → `canonical_writer/invariants.py`
- [ ] 提取 iso_now → `canonical_writer/_time.py`（4 处重复的统一源）
- [ ] 提取 normalize_session_id, _stamp_provenance, _validate_resume → `canonical_writer/store.py` / `_resume.py`
- [ ] 从 checkpoint_request.py 提取 CheckpointRequestError + validate_develop_resume_context + 常量 (~63 LOC) → `canonical_writer/_resume.py`
- [ ] import 审计：确认 canonical_writer/ 仅依赖 sopify_contracts + 标准库

## S3: 消费者重接线

- [ ] runtime 核心文件（engine, gate, bridges 等 ~10 文件）import 路径切换
- [ ] installer/inspection.py import 路径切换
- [ ] scripts/ import 路径切换
- [ ] tests/ import 路径切换
- [ ] 临时兼容桥（仅过渡用）：
  - [ ] runtime/models.py → `from sopify_contracts import *`（deprecated，全量 re-export）
  - [ ] runtime/state.py → re-export StateStore（deprecated）
  - [ ] runtime/state_invariants.py → re-export invariants（deprecated）

## S4: 验证 + 清理

- [ ] 全量测试回归：721+ tests 全过
- [ ] iso_now 重复清理：4 处定义统一为从 `_time.py` 导入
  - `runtime/handoff.py:_iso_now` (line 168)
  - `runtime/decision.py:iso_now` (line 609)
  - `runtime/clarification.py:iso_now` (line 389)
  - `runtime/state.py:iso_now` (line 317) → 迁入 canonical_writer/_time.py
- [ ] 移除临时兼容桥：确认无旧路径引用后删除所有 re-export
- [ ] 删除 `runtime/_models/`（已迁出到 sopify_contracts/）
- [ ] canonical_writer/ import 审计：仅依赖 sopify_contracts + 标准库
- [ ] sopify_contracts/ import 审计：仅依赖标准库
- [ ] state.py / state_invariants.py 瘦身确认
- [ ] 蓝图同步：design.md 三层分离表 canonical writer 列标"已提取"

## S5: 结论报告

- [ ] 标准 receipt 格式
- [ ] 提取前后 LOC 对比（sopify_contracts ~1,179 + canonical_writer ~530）
- [ ] 三层依赖图（sopify_contracts ← canonical_writer ← runtime，无回指）
- [ ] writer_input contract 可用性评估
- [ ] 归档至 history/
