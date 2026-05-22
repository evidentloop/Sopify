---
plan_id: 20260520_p6_canonical_writer_cutover
feature_key: p6_canonical_writer_cutover
level: standard
lifecycle_state: archived
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

### S2.2: canonical_writer/ 写层 ✅

- [x] 创建 `canonical_writer/` 目录 + `__init__.py`
- [x] 从 state.py 提取 StateStore 类 → `canonical_writer/store.py`
- [x] 从 state.py 提取 IO helpers（_read_json, _write_json）→ `canonical_writer/io.py`（standalone 函数）
- [x] 从 handoff.py 提取 read_runtime_handoff → `canonical_writer/io.py`
- [x] 迁移 state_invariants.py → `canonical_writer/invariants.py`
- [x] 提取 iso_now → `canonical_writer/_time.py`
- [x] 提取 normalize_session_id, _stamp_provenance, _validate_resume → `canonical_writer/store.py`
- [x] 从 checkpoint_request.py 提取 CheckpointRequestError + validate_develop_resume_context + develop_resume_context_issue + 常量 → `canonical_writer/_resume.py`
- [x] import 审计：canonical_writer/ 仅依赖 sopify_contracts + 标准库 ✓
- [x] 兼容桥建立：runtime/state.py, runtime/state_invariants.py, runtime/checkpoint_request.py, runtime/handoff.py
- [x] bundle 基础设施更新（sync-runtime-assets.sh, validate.py, runtime_bundle.py, bootstrap_workspace.py, inspection.py）
- [x] 测试 copytree/rmtree 模式修复 ×6
- [x] 全量测试通过：721 passed

## S3: 消费者重接线 ✅

非 runtime 生产消费者已切换到新路径（直接 import canonical_writer / sopify_contracts）：

- [x] installer/payload.py — `from canonical_writer import iso_now`
- [x] installer/inspection.py — `from canonical_writer import StateStore`
- [x] scripts/sopify_runtime.py — iso_now 从 canonical_writer，stable_request_sha1/summarize 留 runtime.state
- [x] scripts/check-skill-eval-gate.py — `from canonical_writer import StateStore`
- [x] tests/runtime_test_support.py — StateStore/iso_now 从 canonical_writer，invariants 从 canonical_writer.invariants，local_day_now 留 runtime.state
- [x] tests/test_runtime_state.py — `from canonical_writer.invariants import validate_phase`
- [x] tests/test_runtime_gate.py — StateStore/iso_now 从 canonical_writer，stable_request_sha1 留 runtime.state
- [x] 全量测试通过：721 passed

## S4: 代码清理完成，验收待 S5

### 代码清理

- [x] iso_now 重复清理：runtime/handoff.py 改为 `from canonical_writer._time import iso_now`；decision.py / clarification.py 的本地 iso_now 定义已删除，统一到 canonical_writer._time
- [x] 删除 `runtime/_models/`：S2.1 git mv 迁出到 sopify_contracts/ 时已删除
- [x] 删除 `runtime/state_invariants.py`：原为 canonical_writer.invariants 的纯 re-export 桥，所有消费者已直接引用 canonical_writer，桥已无引用
- [x] runtime/state.py re-export 移除：StateStore / iso_now / normalize_session_id 的 re-export 已删除，仅保留 runtime-specific helpers
- [x] runtime/checkpoint_request.py re-export 瘦身：仅保留 CheckpointRequestError + validate_develop_resume_context 两项实际依赖
- [x] runtime/ 全量 import 重接线：engine.py / gate.py / develop_callback.py 等 20 个文件直接 import canonical_writer / sopify_contracts
- [x] writer observability stamp：canonical_writer/store.py L75/L242 从 `"runtime.state"` 改为 `"canonical_writer"`
- [x] canonical_writer/ import 审计：仅依赖 sopify_contracts + 标准库
- [x] sopify_contracts/ import 审计：仅依赖标准库

### 兼容桥降级说明（非临时桥，保留为 runtime 层 API）

原计划"确认无旧路径引用后删除所有 re-export"。实际结论：以下模块不是临时桥，而是 runtime 层自身对外 API 或内部逻辑的宿主，保留合理：

- runtime/models.py — sopify_contracts 的 deprecated re-export facade。仍有 3 处测试消费者（runtime_test_support.py, test_action_intent.py, test_runtime_gate.py）。保留为测试兼容层，标 DEPRECATED
- runtime/state.py — re-export 已移除；现仅保留 runtime-specific helpers（~130 LOC），是 runtime 自有逻辑而非桥
- runtime/checkpoint_request.py — 仍拥有 checkpoint 请求的 runtime-side 逻辑（build_scope_clarification_form 等），非纯 re-export 桥
- runtime/handoff.py — 仍拥有 build_runtime_handoff（engine 耦合逻辑），read_runtime_handoff 已迁至 canonical_writer/io.py

### 待 S5

- [ ] 全量测试回归确认
- [ ] 蓝图同步：design.md 三层分离表标"已提取"

## S5: 结论报告 ✅

- [x] 标准 receipt 格式 → `history/2026-05/20260520_p6_canonical_writer_cutover/receipt.md`
- [x] 提取前后 LOC 对比（sopify_contracts 1,227 LOC + canonical_writer 605 LOC）
- [x] 三层依赖图验证通过（sopify_contracts ← canonical_writer ← runtime，无回指）
- [x] writer_input contract 可用性评估完成
- [x] 归档至 history/ — plan 文件已复制到 `history/2026-05/20260520_p6_canonical_writer_cutover/`
