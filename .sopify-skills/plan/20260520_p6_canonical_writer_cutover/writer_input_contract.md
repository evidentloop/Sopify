# Writer Input Contract

P6 S1 输出。定义 canonical_writer (StateStore) 的外部接口、类型边界、不变量归属、IO 契约。

## 1. 方法清单与入参类型

### 1.1 直接写入方法

| 方法 | 入参类型 | 必要字段 | 前置条件 |
|------|---------|---------|---------|
| `set_current_run(run_state)` | RunState | run_id, status, stage, route_name, title, created_at, updated_at | 无 |
| `set_last_route(decision)` | RouteDecision | route_name, request_text, reason | 无 |
| `set_current_plan(artifact)` | PlanArtifact | plan_id, title, summary, level, path, files, created_at | 无 |
| `set_current_clarification(cs)` | ClarificationState | clarification_id, phase, resume_context | phase ∈ {analyze, develop}；develop 需 resume_context 完整 |
| `set_current_decision(ds)` | DecisionState | decision_id, phase, resume_context, active_checkpoint | phase ∈ {design, execution_gate, develop}；develop/execution_gate 需 resume_context 完整 |
| `set_current_handoff(handoff)` | RuntimeHandoff | schema_version, route_name, run_id | 无 |
| `set_current_archive_receipt(handoff)` | RuntimeHandoff | 同上 | 无 |

### 1.2 复合/便利方法

| 方法 | 入参 | 说明 |
|------|-----|------|
| `set_host_facing_truth(*, run_state, handoff, resolution_id, truth_kind)` | RunState + RuntimeHandoff + str + str | Hotfix 白名单限定的成对写；校验 run_id 匹配 + truth_kind 白名单 + resolution_id 非空 |
| `set_current_clarification_response(*, response_text, response_fields, response_source, response_message)` | 关键字参数 | 读 → 更新 → 写；内部调 set_current_clarification |
| `set_current_decision_submission(submission)` | DecisionSubmission | 读 → 更新 → 写；内部调 set_current_decision |
| `update_active_run(*, stage, status)` | 关键字参数 | 读 → 更新 → 写 |

### 1.3 构造/初始化

| 方法 | 入参 | 说明 |
|------|-----|------|
| `__init__(config, session_id)` | RuntimeConfig + str\|None | config 提供 workspace_root / state_dir 等路径；session_id 经 normalize_session_id 校验 |

## 2. models.py 分割分析

### 2.1 发现：_models/ 已经是自洽无依赖包

`runtime/_models/` 目录（1,179 LOC）：
- `core.py` (330 LOC): RunState, RuntimeConfig, ExecutionGate, RouteDecision, ExecutionSummary, SkillMeta + 辅助
- `decision.py` (547 LOC): ClarificationState, DecisionState, DecisionSubmission + 7 个子类型
- `handoff.py` (170 LOC): RuntimeHandoff, RecoveredContext, RuntimeResult, SkillActivation
- `artifacts.py` (61 LOC): PlanArtifact, KbArtifact
- `proposal.py` (71 LOC): PlanProposalState

**关键发现：`_models/` 的所有文件仅互相引用 + 标准库，零 runtime engine 依赖。**

`runtime/models.py` (47 LOC) 是纯 facade，从 `_models/` 子包 re-export 全部 23 个公开类型。

### 2.2 Writer-facing vs Engine-only 分类

**Writer-facing（StateStore 方法签名中直接出现）**：

| 类型 | 来源 | 理由 |
|------|------|------|
| RunState | _models/core.py | set_current_run, update_active_run, set_host_facing_truth |
| RuntimeHandoff | _models/handoff.py | set_current_handoff, set_host_facing_truth, set_current_archive_receipt |
| RouteDecision | _models/core.py | set_last_route |
| PlanArtifact | _models/artifacts.py | set_current_plan |
| ClarificationState | _models/decision.py | set_current_clarification, set_current_clarification_response |
| DecisionState | _models/decision.py | set_current_decision, set_current_decision_submission |
| DecisionSubmission | _models/decision.py | set_current_decision_submission |
| RuntimeConfig | _models/core.py | __init__ |
| ExecutionGate | _models/core.py | 嵌入在 RunState 中（transitive） |

**Writer-facing 的结构依赖（不在 StateStore 签名，但是 writer-facing 类型的子组件）**：

| 类型 | 说明 |
|------|------|
| DecisionCheckpoint | DecisionState.active_checkpoint 的类型 |
| DecisionField | DecisionCheckpoint.fields 的元素类型 |
| DecisionOption | DecisionField.options 的元素类型 |
| DecisionCondition | DecisionField.conditions 的元素类型 |
| DecisionValidation | DecisionField.validations 的元素类型 |
| DecisionRecommendation | DecisionCheckpoint.recommendations 的元素类型 |
| DecisionSelection | DecisionSubmission.selections 的元素类型 |

**Engine-only（StateStore 不使用）**：

| 类型 | 来源 | 使用者 |
|------|------|--------|
| RecoveredContext | _models/handoff.py | context_recovery.py |
| RuntimeResult | _models/handoff.py | engine.py 返回值 |
| SkillActivation | _models/handoff.py | output.py, skill_runner.py |
| SkillMeta | _models/core.py | skill_registry.py, skill_resolver.py |
| ExecutionSummary | _models/core.py | checkpoint_request.py, handoff.py |
| KbArtifact | _models/artifacts.py | kb.py, engine.py |
| PlanProposalState | _models/proposal.py | plan_orchestrator.py |

### 2.3 分割方案评估

**方案 α：按 writer/engine 拆分类型**
- writer-facing 类型迁入 canonical_writer/models.py
- engine-only 类型留 runtime/_models/
- ❌ 问题：ClarificationState 迁出但其引用的 core 辅助函数（_json_mapping 等）和子类型都在同一个 decision.py 中。拆分会打断 `_models/` 内部的 cross-file import 关系

**方案 β：整包迁出 _models/ 作为共享基础层**
- 整个 `_models/` 迁入共享位置（如顶层 `sopify_models/` 或 `canonical_writer/_models/`）
- runtime/models.py 变为 re-export 桥
- ✅ 优点：_models/ 已自洽，零拆分成本，无回指
- ❌ 问题：canonical_writer 包含了 RecoveredContext/RuntimeResult 等它不需要的类型
- 命名问题：如果放在 canonical_writer/ 下，暗示 writer 拥有所有类型

**方案 γ（已拍板）：_models/ 迁出为独立顶层 `sopify_contracts/`**
- `sopify_contracts/` = 当前 `_models/` 直接平移，改 package name
- `runtime/models.py` → re-export from `sopify_contracts`（deprecated bridge）
- `canonical_writer/` → import from `sopify_contracts`
- ✅ 命名中性：不暗示任何模块所有权（含 RuntimeResult/SkillMeta 等超出 state 范畴的类型）
- ✅ 零拆分成本：_models/ 整包搬
- ✅ 清晰分层：sopify_contracts（共享类型层）→ canonical_writer（写层）→ runtime（编排层）
- 代价：多一个顶层目录

**对比原 P6 设计**：

原设计说"writer-facing 类型迁出 → canonical_writer/models.py"。但分析后发现：
1. writer-facing 和 engine-only 类型**在同一文件中互相依赖**（decision.py 内所有类型链式引用）
2. 按 writer/engine 拆分 decision.py ≈ 重写 547 LOC，引入新的交叉引用
3. `_models/` 作为整体已经自洽，不需要拆

**结论**：models.py 分割的答案是"不按 writer/engine 拆分文件，而是整包迁出作为共享基础层"。

## 3. 不变量归属

### 3.1 Writer-side invariants（canonical_writer 拥有）

| 不变量 | 来源 | 校验内容 |
|--------|------|---------|
| validate_phase | state_invariants.py | state_kind → 允许的 phase 枚举检查 |
| _validate_state_resume_contract | state.py:374-391 | develop/execution_gate phase 的 resume_context 必填字段 |
| validate_paired_host_truth_write | state_invariants.py | run_id 匹配 + truth_kind 白名单 |
| validate_resolution_id | state_invariants.py | resolution_id 非空 |
| normalize_session_id | state.py:456-467 | session_id 安全字符校验（防路径注入） |

### 3.2 Writer-side provenance stamping（canonical_writer 拥有）

| 函数 | 来源 | 行为 |
|------|------|------|
| _stamp_clarification_provenance | state.py:340-354 | 向 resume_context 注入 checkpoint_id + owner 元数据 |
| _stamp_decision_provenance | state.py:357-371 | 同上模式，多支持 execution_gate phase |
| stamp_run_resolution_id | state_invariants.py:54-56 | 向 RunState 注入 resolution_id |
| stamp_handoff_resolution_id | state_invariants.py:59-71 | 向 RuntimeHandoff 注入 resolution_id + truth_kind |
| observability block 构建 | set_current_run, _set_handoff_file | 向 payload 注入 observability 元数据 |

### 3.3 Caller-side preconditions（调用方负责，NOT writer 校验）

- 构造合法的 RunState / DecisionState / ClarificationState 对象（字段完整性由 dataclass 定义保证）
- 提供正确的 phase 值（writer 做枚举校验，但语义正确性是调用方职责）
- develop 阶段提供完整 resume_context（writer 做结构校验，但内容正确性是调用方职责）
- set_host_facing_truth 的 resolution_id 来源于调用方的业务流

## 4. IO 契约

### 4.1 文件路径 convention

```
{workspace_root}/.sopify-skills/state/
  ├── current_run.json          # global scope
  ├── last_route.json
  ├── current_plan.json
  ├── current_handoff.json
  ├── current_archive_receipt.json
  ├── current_clarification.json
  ├── current_decision.json
  └── sessions/
      └── {session_id}/
          ├── current_run.json  # session scope
          ├── last_route.json
          └── ...
```

路径由 `RuntimeConfig.state_dir` 确定。session_id 经 `normalize_session_id` 校验后作为目录名。

### 4.2 Atomic write 语义

```python
# _write_json 实现：
# 1. 在目标文件同目录创建 NamedTemporaryFile
# 2. json.dump 写入临时文件（ensure_ascii=False, indent=2, sort_keys=True, trailing newline）
# 3. temp_path.replace(path) — 原子替换
```

同一文件系统上 `replace()` 是原子操作。跨文件系统场景未处理（当前不需要）。

### 4.3 JSON encoding 约定

- `ensure_ascii=False`：保留 Unicode 字符
- `indent=2`：人类可读
- `sort_keys=True`：确定性输出（diff 友好）
- 尾部换行：`handle.write("\n")`
- 编码：utf-8

### 4.4 Read 语义

```python
# _read_json 实现：
# 1. path.exists() check → None if missing
# 2. json.loads(path.read_text("utf-8"))
# 3. 返回 dict（不校验 schema）
```

注意：_read_json 不做 error handling（OSError/JSONDecodeError 上抛）。
对比 `_read_json_file`（state.py:499-506）有异常捕获 + isinstance 校验，但仅用于 session cleanup 场景，非 StateStore 主路径。

## 5. Observability 契约

### 5.1 通用 observability 字段

所有带 observability block 的写操作包含：

| 字段 | 值 | 说明 |
|------|---|------|
| state_kind | "current_run" / "current_handoff" / "current_archive_receipt" | 标识哪个状态文件 |
| state_scope | "session" / "global" | 来自 StateStore.scope |
| writer | "runtime.state" | P6 后改为 "canonical_writer" |
| written_at | iso_now() | UTC ISO 8601, 无微秒 |
| workspace_root | str(config.workspace_root) | 绝对路径 |
| runtime_root | 相对路径 | relative_to(workspace_root) |
| state_path | 相对路径 | 状态文件的 workspace-relative 路径 |
| session_id | str | 仅 session scope 时包含 |

### 5.2 domain-specific observability 字段

**current_run** 额外：run_id, route_name, stage, status, request_excerpt, request_sha1, owner_session_id, owner_host, owner_run_id, resolution_id

**current_handoff / current_archive_receipt** 额外：run_id, route_name, required_host_action, resolution_id（如有 resolution_id stamp 则额外 host_truth_write_kind, host_truth_paired_write）

**current_plan / last_route / current_clarification / current_decision**：不带 observability block（通过 to_dict() 的内部字段隐含时间戳）

### 5.3 Provenance timestamp

- `iso_now()`: `datetime.now(timezone.utc).replace(microsecond=0).isoformat()`
- 格式示例: `"2026-05-20T08:30:00+00:00"`
- 注意：`local_iso_now()` 是另一个函数（本地时间），NOT writer observability 用

## 6. 架构结论（已拍板）

### 6.1 models.py 分割决策

**决策：γ — 整包迁出 _models/ 为 `sopify_contracts/`。**

理由：
1. writer-facing 类型有 9+7=16 个（直接 + 结构依赖），engine-only 有 7 个
2. 但两组类型在 `_models/` 中通过文件内 import 链式关联
3. 按 writer/engine 边界拆分 = 重写 `_models/decision.py` (547 LOC) 的 import 结构
4. `_models/` 整包零 runtime engine 依赖（已确认），是天然的共享基础层
5. 命名 `sopify_contracts/` 而非 `state_contracts/`：包内含 RuntimeResult/SkillMeta/PlanProposalState 等超出 state 范畴的类型

**已否决方案**：
- α（按 writer/engine 拆分类型）：打断 decision.py 链式引用，成本高
- δ（canonical_writer → runtime._models）：与 DR-1 "不接受留在 runtime 里算共享层" 正面冲突

### 6.2 checkpoint_request 提取范围确认

StateStore 使用 checkpoint_request.py 的符号：
- `CheckpointRequestError` (line 41): 异常类，1 LOC
- `validate_develop_resume_context` (line 68-100): 33 LOC
  - 调用 `develop_resume_context_issue` (line 45-65): 21 LOC
  - 使用 `DEVELOP_RESUME_CONTEXT_REQUIRED_FIELDS` (line 30-36): 常量
  - 使用 `DEVELOP_RESUME_AFTER_ACTIONS` (line 38): 常量

提取清单（精确 LOC）：
```
CheckpointRequestError            1 LOC
DEVELOP_RESUME_CONTEXT_REQUIRED_FIELDS  7 LOC (含注释)
DEVELOP_RESUME_AFTER_ACTIONS      1 LOC
develop_resume_context_issue      21 LOC
validate_develop_resume_context   33 LOC
─────────────────────────────────
合计                              ~63 LOC
```

### 6.3 非 StateStore 但需随迁的辅助

| 辅助 | LOC | 理由 |
|------|-----|------|
| iso_now | 3 | StateStore 硬依赖，4 处重复的统一源 |
| normalize_session_id | 12 | StateStore.__init__ 调用 |
| _stamp_clarification_provenance | 15 | set_current_clarification 调用 |
| _stamp_decision_provenance | 15 | set_current_decision 调用 |
| _validate_state_resume_contract | 18 | set_current_clarification / set_current_decision 调用 |
| _read_json / _write_json | 13 | StateStore 实例方法，随类迁移 |
| stable_request_sha1 | 6 | 非 StateStore 直接依赖，但 observability 生态配套。**不随迁** |
| summarize_request_text | 7 | 同上。**不随迁** |
| local_* 函数族 | ~35 | local_iso_now, local_now 等。**不随迁**（非 writer 依赖） |
| cleanup_expired_session_state | 22 | session 清理策略。**不随迁**（gate 策略逻辑） |
| _session_dir_updated_at / _parse_iso_datetime / _read_json_file | 35 | session 清理辅助。**不随迁** |
