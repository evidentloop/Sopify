# P5 S3: Provisional Adjudication Table

> 基于 S1 全量清点（模块级 + 行级拆分），按 sub-surface 粒度裁定。
> S2 证据型候选（Shadow Writer / Onboarding Proof）尚未就绪，相关面标为 provisional。
>
> **裁定四分类**（定义见 design.md:64-68）：
> - **keep-cross-tier**: 所有梯度宿主都需要
> - **keep-deep-only**: 仅 deep_verified 宿主需要
> - **keep-candidate-kernel**: 当前 deep-only，但 P6 extractable kernel 的候选组成
> - **delete**: 无消费者或已被替代
>
> **evidence_status** 取值：
> - **ready**: 无需额外证据，可直接裁定
> - **pending-shadow-writer**: 依赖 Shadow Writer Gap Analysis 结论
> - **pending-onboarding**: 依赖 Copilot Onboarding Proof 结论

---

## 1. Cross-Tier Surfaces (keep-cross-tier)

> 所有梯度宿主消费的 contract 面。P5 动作：确认 contract 文档覆盖。

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 1.1 | `_models/core.py` — RunState, PlanArtifact, SkillActivation, SkillMeta | cross-tier (P4d 已验证 payload_capable 可读) | ready | **keep-cross-tier** | low | ~330 LOC。纯 schema dataclass。已通过 P4d smoke test |
| 1.2 | `_models/handoff.py` — RuntimeHandoff model (读取面) | cross-tier | ready | **keep-cross-tier** | low | ~170 LOC schema 定义 |
| 1.3 | `_models/decision.py` — DecisionState, ClarificationState model (读取面) | cross-tier | ready | **keep-cross-tier** | low | ~547 LOC schema + enum 定义 |
| 1.4 | `handoff.py` — schema constants + reader + observability | cross-tier | ready | **keep-cross-tier** | low | ~60 LOC。路径常量 + JSON 读取 |
| 1.5 | `decision.py` — 路径常量 + response parser + readback + payload text | cross-tier | ready | **keep-cross-tier** | low | ~200 LOC |
| 1.6 | `clarification.py` — 路径常量 + response parser + form/submission | cross-tier | ready | **keep-cross-tier** | low | ~200 LOC |
| 1.7 | `state.py` — StateStore path constants (文件路径定义) | cross-tier | ready | **keep-cross-tier** | low | ~30 LOC 路径常量，被 payload_capable 宿主引用 |
| 1.8 | `knowledge_layout.py` — 知识路径常量 | cross-tier | ready | **keep-cross-tier** | low | ~100 LOC |
| 1.9 | `entry_guard.py` — PENDING_ACTIONS 常量 | cross-tier | ready | **keep-cross-tier** | low | 常量定义部分。entry guard 逻辑本身是 deep-only |
| 1.10 | `installer/models.py` — cross-tier 注册类型 (SupportTier, FeatureId, EnhancementGroup, HostCapability) | cross-tier 语义承载 | ready | **keep-cross-tier** | medium | 类型定义是 cross-tier，但物理位置在 installer 内部。存在循环依赖 models↔hosts。provisional 建议：拆出到独立模块 |

**Cross-tier 小计**: ~2,500 LOC

---

## 2. Candidate-Kernel Surfaces (keep-candidate-kernel)

> 当前仅 deep host 使用，但如果 P6 需要 extractable kernel，这些是组成候选。P5 只识别形状，不改造。

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 2.1 | `handoff.py` — build_runtime_handoff + artifact collectors + guardrail | deep-only (写入路径) | **pending-shadow-writer** | **keep-candidate-kernel** | medium | ~230 LOC。Shadow Writer 结论 A/B → 确认 kernel，结论 C → 降为 keep-deep-only |
| 2.2 | `handoff.py` — write_runtime_handoff | deep-only (写入路径) | **pending-shadow-writer** | **keep-candidate-kernel** | high | ~10 LOC。canonical state 写入点。Shadow Writer 需判断是否允许非 deep host 写入 |
| 2.3 | `state.py` — StateStore get/set/clear 全系列 | deep-only (读写路径) | **pending-shadow-writer** | **keep-candidate-kernel** | medium | ~210 LOC。canonical 文件读写核心。Shadow Writer 结论直接决定此面命运 |
| 2.4 | `decision.py` — build_* 构建器 + submission writer + 状态转换 | deep-only (写入路径) | **pending-shadow-writer** | **keep-candidate-kernel** | medium | ~180 LOC。DecisionState 生产逻辑 |
| 2.5 | `clarification.py` — build_clarification_state + stale transition | deep-only (写入路径) | **pending-shadow-writer** | **keep-candidate-kernel** | low | ~50 LOC。结构简单 |

**Candidate-kernel 小计**: ~680 LOC (全部 pending-shadow-writer)

---

## 3. Deep-Only Surfaces (keep-deep-only)

> 仅 deep_verified 宿主消费，non-deep 宿主不消费。P5 动作：标记为 deep-only scope。

### 3a. 引擎核心 (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.1 | `engine.py` — 完整 runtime 引擎 | deep-only | ready | **keep-deep-only** | low | ~2,729 LOC。runtime 执行核心 |
| 3.2 | `router.py` — 路由选择 | deep-only | ready | **keep-deep-only** | low | ~783 LOC |
| 3.3 | `gate.py` — Gate 授权控制 | deep-only | ready | **keep-deep-only** | low | ~941 LOC。编排层，与 engine 紧耦合 |
| 3.4 | `output.py` — 输出渲染 | deep-only | ready | **keep-deep-only** | low | ~620 LOC |
| 3.5 | `context_snapshot.py` — 上下文快照 | deep-only | ready | **keep-deep-only** | low | ~973 LOC |
| 3.6 | `context_v1_scope.py` — 上下文 v1 scope | deep-only | ready | **keep-deep-only** | low | ~329 LOC |
| 3.7 | `failure_recovery.py` — 故障恢复 | deep-only | ready | **keep-deep-only** | low | ~719 LOC |
| 3.8 | `cli_interactive.py` — CLI 交互层 | deep-only | ready | **keep-deep-only** | low | ~412 LOC |
| 3.9 | `action_projection.py` — 动作面投影 | deep-only | ready | **keep-deep-only** | low | ~220 LOC |

### 3b. 决策/策略 (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.10 | `decision_bridge.py` — confirm_decision CLI 桥接 | deep-only | ready | **keep-deep-only** | low | ~864 LOC |
| 3.11 | `decision_tables.py` — 决策表引擎 | deep-only | ready | **keep-deep-only** | low | ~1,632 LOC |
| 3.12 | `decision_policy.py` — 决策策略 | deep-only | ready | **keep-deep-only** | low | ~434 LOC |
| 3.13 | `clarification_bridge.py` — answer_questions CLI 桥接 | deep-only | ready | **keep-deep-only** | low | ~401 LOC |
| 3.14 | `handoff.py` — route→handoff 映射 + host_action 策略 + 门控 | deep-only | ready | **keep-deep-only** | low | ~100 LOC |
| 3.15 | `handoff.py` — resume context + execution summary | deep-only | ready | **keep-deep-only** | low | ~50 LOC |
| 3.16 | `decision.py` — 触发策略 + 选项匹配 | deep-only | ready | **keep-deep-only** | low | ~220 LOC |
| 3.17 | `clarification.py` — 触发策略 + 事实推断 | deep-only | ready | **keep-deep-only** | low | ~130 LOC |

### 3c. Validator-bearing (deep-only, 可提取)

> 这些面的 **disposition 是 keep-deep-only**（当前消费者是 deep host）。
> 但它们包含可提取的验证逻辑，是蓝图 Validator 物理分层的候选代码。
> **Validator 提取是 P6+ 决策，不是 P5 裁定分类。**

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.18 | `action_intent.py` — 动作提案验证 + 主体绑定 + 授权降级/拒绝 | deep-only | ready | **keep-deep-only** | low | ~450 LOC 验证逻辑可提取。蓝图 Validator 候选 |
| 3.19 | `deterministic_guard.py` — 确定性 checkpoint 守卫 | deep-only | ready | **keep-deep-only** | low | ~200 LOC 验证逻辑可提取 |
| 3.20 | `workspace_preflight.py` — 工作区预检 + 宿主能力授权 | deep-only | ready | **keep-deep-only** | medium | ~250-350 LOC 部分可提取。依赖 installer 类型 |
| 3.21 | `installer/validate.py` — 安装验证 + capability 检查 | deep-only | ready | **keep-deep-only** | low | ~100-150 LOC 部分可提取 |
| 3.22 | `gate.py` — Gate 授权逻辑中的验证部分 | deep-only | ready | **keep-deep-only** | — | ~150-200 LOC。与 engine 紧耦合，**不可提取** |

### 3d. 知识/Plan/Archive (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.23 | `kb.py` — 知识库操作 | deep-only | ready | **keep-deep-only** | low | ~463 LOC |
| 3.24 | `plan_scaffold.py` — Plan 脚手架生成 | deep-only | ready | **keep-deep-only** | low | ~464 LOC |
| 3.25 | `archive_lifecycle.py` — 归档生命周期管理 | deep-only | ready | **keep-deep-only** | low | ~831 LOC |
| 3.26 | `plan_registry.py` — Plan 注册表 | deep-only | ready | **keep-deep-only** | low | ~200 LOC |

### 3e. 其他 runtime (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.27 | `develop_callback.py` — develop 回调 | deep-only | ready | **keep-deep-only** | low | ~597 LOC |
| 3.28 | `develop_quality.py` — develop 质量检查 | deep-only | ready | **keep-deep-only** | low | ~403 LOC |
| 3.29 | `checkpoint_request.py` — checkpoint 请求 | deep-only | ready | **keep-deep-only** | low | ~390 LOC |
| 3.30 | `manifest.py` — bundle manifest 生成 | deep-only | ready | **keep-deep-only** | low | ~475 LOC |
| 3.31 | `preferences.py` — 偏好加载 | deep-only | ready | **keep-deep-only** | low | ~200 LOC |
| 3.32 | `config.py` — RuntimeConfig 加载 | deep-only | ready | **keep-deep-only** | low | ~100 LOC |
| 3.33 | `resolution_planner.py` — 解决方案规划 | deep-only | ready | **keep-deep-only** | low | ~150 LOC |
| 3.34 | `sidecar_classifier_boundary.py` — Sidecar 分类器 | deep-only | ready | **keep-deep-only** | low | ~100 LOC |
| 3.35 | `vnext_phase_boundary.py` — VNext 阶段边界 | deep-only | ready | **keep-deep-only** | low | ~100 LOC |
| 3.36 | `builtin_catalog.py` — 内置 skill 目录 | deep-only | ready | **keep-deep-only** | low | ~100 LOC |
| 3.37 | `state.py` — 会话生命周期 + 原子 IO + 保留策略 | internal | ready | **keep-deep-only** | low | ~200 LOC |

### 3f. Installer (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.38 | `installer/hosts/base.py` — HostAdapter 接口 | deep-only | **pending-onboarding** | **keep-deep-only** | low | ~122 LOC。Onboarding Proof 若发现非 deep 路径需要 host adapter → 重评 |
| 3.39 | `installer/hosts/codex.py` — Codex adapter | deep-only | ready | **keep-deep-only** | low | ~57 LOC |
| 3.40 | `installer/hosts/claude.py` — Claude adapter | deep-only | ready | **keep-deep-only** | low | ~57 LOC |
| 3.41 | `installer/hosts/__init__.py` — Host 注册表 | deep-only | ready | **keep-deep-only** | low | ~66 LOC |
| 3.42 | `installer/bootstrap_workspace.py` — Workspace bootstrap | deep-only | **pending-onboarding** | **keep-deep-only** | medium | ~1,358 LOC。Onboarding Proof 结论影响：非 deep 接入是否需要简化 bootstrap? |
| 3.43 | `installer/inspection.py` — 安装状态检查/doctor | deep-only | ready | **keep-deep-only** | low | ~1,360 LOC |
| 3.44 | `installer/distribution.py` — 分发逻辑 | deep-only | ready | **keep-deep-only** | low | ~415 LOC |
| 3.45 | `installer/payload.py` — Payload bundle 管理 | deep-only | ready | **keep-deep-only** | low | ~260 LOC |
| 3.46 | `installer/outcome_contract.py` — 安装结果契约 | deep-only | ready | **keep-deep-only** | low | ~155 LOC |
| 3.47 | `installer/runtime_bundle.py` — Runtime bundle 辅助 | deep-only | ready | **keep-deep-only** | low | ~47 LOC |
| 3.48 | `installer/models.py` — installer-specific 类型 (InstallError, InstallResult, parse_install_target) | deep-only | ready | **keep-deep-only** | low | installer-specific 部分，与 1.10 cross-tier 类型拆分后留在 installer |

### 3g. Scripts (deep-only)

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 3.49 | `scripts/sopify_runtime.py` — 主 runtime 入口 | deep-only | ready | **keep-deep-only** | low | ~220 LOC |
| 3.50 | `scripts/runtime_gate.py` — Gate 入口 | deep-only | ready | **keep-deep-only** | low | ~129 LOC |
| 3.51 | `scripts/decision_bridge_runtime.py` — 决策桥接入口 | deep-only | ready | **keep-deep-only** | low | ~171 LOC |
| 3.52 | `scripts/clarification_bridge_runtime.py` — 澄清桥接入口 | deep-only | ready | **keep-deep-only** | low | ~160 LOC |
| 3.53 | `scripts/develop_callback_runtime.py` — develop 回调入口 | deep-only | ready | **keep-deep-only** | low | ~123 LOC |
| 3.54 | `scripts/plan_registry_runtime.py` — plan 注册表入口 | deep-only | ready | **keep-deep-only** | low | ~109 LOC |
| 3.55 | `scripts/install_sopify.py` — 安装脚本 | deep-only | ready | **keep-deep-only** | low | ~220 LOC |
| 3.56 | `scripts/check-install-payload-bundle-smoke.py` — 安装 smoke 测试 | deep-only | ready | **keep-deep-only** | low | ~359 LOC |
| 3.57 | `scripts/check-*.py` (其他) — 维护/检查脚本 | internal | ready | **keep-deep-only** | low | ~2,000 LOC。内部工具，不对外暴露 |

**Deep-only 小计**: ~20,800 LOC

---

## 4. Delete Candidates (delete)

> 低风险删除候选。P5 S4 执行前需确认无其他引用。

| # | surface | current_consumer | evidence_status | provisional_disposition | execution_risk | notes |
|---|---------|-----------------|----------------|------------------------|---------------|-------|
| 4.1 | `handoff.py` — 工具函数 (重复辅助) | internal | ready | **delete** (low-risk) | low | ~60 LOC。需确认无其他调用点 |
| 4.2 | `state.py` — 工具函数 (重复辅助) | internal | ready | **delete** (low-risk) | low | ~50 LOC。同上 |
| 4.3 | `_models/` — 工具函数 | internal | ready | **delete** (low-risk) | low | ~27 LOC |

**Delete 小计**: ~137 LOC

---

## 5. 裁定汇总

| disposition | surface 数 | LOC | 占比 | evidence 状态 |
|-------------|-----------|-----|------|--------------|
| **keep-cross-tier** | 10 | ~2,500 | ~10% | 全部 ready |
| **keep-candidate-kernel** | 5 | ~680 | ~2.7% | **全部 pending-shadow-writer** |
| **keep-deep-only** | 40 | ~20,800 | ~82% | 大部分 ready，3 面 pending-onboarding |
| **delete** | 3 | ~137 | ~0.5% | 全部 ready |
| **validator-bearing (分析标注)** | — | ~1,000-1,200 | ~4-5% | ready | 
| **总计** | 58 | ~25,300 | — | — |

> 总计 ~25,300 LOC 与 S1 模块级口径 ~25,500 LOC 存在 ~200 LOC 近似差值，来源于行级拆分时的估算四舍五入和重叠排除。两个口径均为估算，不影响裁定结论。

> **validator-bearing** 不是裁定分类，是分析维度。这些面的裁定是 keep-deep-only (§3c)。
> LOC 重叠：validator-bearing 的 LOC 已包含在 keep-deep-only 中。

---

## 6. Evidence-Pending 面清单

### 6a. Pending Shadow Writer (5 面, ~680 LOC)

| surface | 影响 | Shadow Writer 结论映射 |
|---------|------|----------------------|
| 2.1 handoff build_runtime_handoff | kernel 形状 | A/B→保持 kernel, C→降为 deep-only |
| 2.2 handoff write_runtime_handoff | canonical write 权 | A→允许非 deep 写, B→受限写, C→deep-only |
| 2.3 state StateStore get/set/clear | state 读写核心 | A→kernel, B→部分 kernel, C→deep-only |
| 2.4 decision build_* + writer | decision 生产 | A/B→kernel, C→deep-only |
| 2.5 clarification build + transition | clarification 生产 | A/B→kernel, C→deep-only |

**如果 Shadow Writer = C（不可行）**：全部降为 keep-deep-only，candidate-kernel 归零。P5 收益 = 清晰化 deep-only boundary + delete ~137 LOC。

### 6b. Pending Onboarding (3 面, ~1,480 LOC)

| surface | 影响 | Onboarding 结论映射 |
|---------|------|-------------------|
| 3.38 installer/hosts/base.py | host adapter 接口 | 非 deep 需要 adapter → 重评 |
| 3.42 installer/bootstrap_workspace.py | bootstrap 路径 | 简化 bootstrap 需求 → 部分可删或拆分 |
| 1.10 installer/models.py cross-tier 类型 | 独立化时机 | onboarding 确认需要 → 优先拆出 |

---

## 7. P5 可立即执行的裁定

不依赖任何证据即可推进的项：

| 类别 | 动作 | 面数 | LOC |
|------|------|------|-----|
| keep-cross-tier (ready) | 确认 contract 文档覆盖 | 9 | ~2,370 |
| keep-deep-only (ready) | 标记 deep-only scope | 37 | ~19,320 |
| delete (ready) | 低风险删除候选 — 确认无引用后删除 | 3 | ~137 |
| **可执行小计** | | **49** | **~21,827** |
| **需等证据** | | **8** | **~2,160** |

---

## 8. Provisional 架构观察

### 8.1 Canonical Writer Authority（正交轴）

当前 4 分类不覆盖"谁有权写 canonical state"。§2 candidate-kernel 的 5 个面全部是 **writer 逻辑**，这不是巧合——kernel 的本质就是写入权限边界。

Shadow Writer Gap Analysis 需要回答的核心问题：
- 非 deep host 需要写 canonical state 吗？（如果不需要 → writer 留在 deep-only 即可）
- 如果需要 → 谁授权？protocol 声明式规则还是 Validator 校验？

### 8.2 Validator 物理分层

S1 已定位 ~1K-1.2K LOC 可提取验证逻辑（§3c）。蓝图预估 ~2K LOC Validator 层。差距来源：
- gate.py ~150-200 LOC 验证逻辑与 engine 紧耦合，不可提取
- 部分验证逻辑嵌在 engine.py 流程中，未计入
- 蓝图 2K 包含了目标态 Validator 的新增代码（目前不存在的校验规则）

**结论**：Validator 物理分层是 P6+ 决策。P5 仅识别形状 + 标注位置。

### 8.3 installer/models.py 拆分

models.py 混着 cross-tier 语义类型和 installer-specific 类型。循环依赖 models↔hosts 增加了拆分复杂度。

**Provisional 建议**：
1. cross-tier 类型 (SupportTier, FeatureId, EnhancementGroup, HostCapability) → 独立化为 `contract/` 或 `_models/installer_contract.py`
2. installer-specific 类型 → 留在 `installer/models.py`
3. 执行时机：等 Onboarding Proof 结论确认后再决定
