# P5 S1: Surface Inventory — Deep-Only Contract Surface 全量清点

> 模块级清点。基于代码扫描 + public API 分析。
> 分类标准：谁是这个面的消费者？
> ⚠️ 这是模块级估算，非精确代码归属审计。mixed 模块内部可能同时含 cross-tier schema 和 deep-only 逻辑。

## 分类定义

| 类型 | 含义 |
|------|------|
| **cross-tier** | 所有梯度宿主都可能消费（通过 protocol/contract） |
| **deep-only** | 仅 deep_verified 宿主消费（Codex/Claude adapter 调用） |
| **internal** | runtime 内部调用，无外部消费面 |
| **candidate-kernel-bearing** | 当前 deep-only，但模块内含有可能需要提取的 schema/逻辑（整模块不等于整体都是 kernel 候选）|

## 代码规模

| 目录 | LOC | 文件 | 角色 |
|------|-----|------|------|
| runtime/ | ~25,500 | 61 | 核心运行时 |
| installer/ | ~4,500 | 13 | 安装器 |
| scripts/ | ~4,300 | 22 | 脚本/桥接入口 |
| tests/ | ~19,700 | 36 | 测试（不计入裁定） |
| **validator/** | **0** | **0** | ⚠️ 无独立包——蓝图三层语义成立，但代码物理分层尚未兑现。验证逻辑散在 gate.py, workspace_preflight.py, action_intent.py, installer/validate.py 中 |

---

## A. Runtime Public API (runtime/__init__.py)

| 导出符号 | 类型 | 消费者分类 | 说明 |
|----------|------|-----------|------|
| `run_runtime` | function | deep-only | 完整 runtime 执行入口，仅 deep host 通过 gate 调用 |
| `RuntimeConfig` | model | deep-only | runtime 配置，仅 runtime 执行路径需要 |
| `RuntimeResult` | model | deep-only | runtime 执行结果，仅 output 渲染消费 |
| `RunState` | model | cross-tier | P4d 证明 payload_capable 可读 current_run.json |
| `RouteDecision` | model | deep-only | 路由决策，属 runtime 内部状态机 |
| `PlanArtifact` | model | cross-tier | Plan 产出物，所有梯度可读 |
| `RecoveredContext` | model | deep-only | 上下文恢复，runtime 专属 |
| `SkillActivation` | model | cross-tier | Skill 激活描述 |
| `SkillMeta` | model | cross-tier | Skill 元数据 |
| `render_runtime_output` | function | deep-only | 输出渲染，仅 runtime 执行后调用 |
| `render_runtime_error` | function | deep-only | 错误渲染，仅 runtime 执行后调用 |
| `preload_preferences` | function | deep-only | 偏好预加载，runtime 执行前调用 |
| `preload_preferences_for_workspace` | function | deep-only | 同上 |
| `resolve_preferences_path` | function | deep-only | 同上 |
| `PreferencesPreloadResult` | model | deep-only | 同上 |

**统计**：15 个导出中 10 个 deep-only，5 个 cross-tier。

---

## B. Runtime 核心模块

### B1. 状态机 / 引擎 (deep-only 核心)

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| engine.py | 2,729 | deep-only | 完整 runtime 引擎 |
| router.py | 783 | deep-only | 路由选择 |
| gate.py | 941 | deep-only | Gate 授权控制 |
| action_intent.py | 884 | deep-only | 动作意图解析 |
| action_projection.py | ~220 | deep-only | 动作面投影 |
| workspace_preflight.py | 925 | deep-only | 工作区预检 |
| failure_recovery.py | 719 | deep-only | 故障恢复 |
| deterministic_guard.py | 325 | deep-only | 确定性守卫 |
| cli_interactive.py | 412 | deep-only | CLI 交互层 |
| context_snapshot.py | 973 | deep-only | 上下文快照 |
| context_v1_scope.py | 329 | deep-only | 上下文 v1 scope |

**小计**: ~8,240 LOC — 全部 deep-only

### B2. 决策/澄清 (mixed)

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| decision.py | 611 | candidate-kernel | DecisionState schema——P4d 证明 payload_capable 可读，但写入逻辑嵌于此 |
| decision_bridge.py | 864 | deep-only | confirm_decision CLI 桥接，需 runtime |
| decision_tables.py | 1,632 | deep-only | 决策表引擎 |
| decision_policy.py | 434 | deep-only | 决策策略 |
| clarification.py | 391 | candidate-kernel | ClarificationState schema——同上 |
| clarification_bridge.py | 401 | deep-only | answer_questions CLI 桥接 |

**小计**: ~4,333 LOC — 大部分 deep-only，schema 部分是 candidate-kernel

### B3. Handoff / State (mixed)

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| handoff.py | 655 | candidate-kernel | RuntimeHandoff schema + writer。schema 是 cross-tier 消费；writer 是 deep-only 但 candidate-kernel（Shadow Writer 评估对象） |
| state.py | 506 | candidate-kernel | StateStore + canonical 文件路径。路径常量是 cross-tier 消费；读写逻辑 deep-only |
| _models/core.py | 330 | mixed | RunState cross-tier；RuntimeConfig/RouteDecision deep-only |
| _models/handoff.py | ~170 | mixed | RuntimeHandoff model cross-tier；builder deep-only |
| _models/decision.py | 547 | mixed | Decision/Clarification models cross-tier；policy deep-only |

**小计**: ~2,208 LOC — schema 部分 cross-tier，写入逻辑 candidate-kernel

### B4. 输出渲染 (deep-only)

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| output.py | 620 | deep-only | 完整输出渲染（phase labels, status, next steps）|

### B5. 知识 / Plan / Archive (mixed)

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| kb.py | 463 | deep-only | 知识库操作（blueprint writeback 等）|
| plan_scaffold.py | 464 | deep-only | Plan 脚手架生成 |
| archive_lifecycle.py | 831 | deep-only | 归档生命周期管理 |
| plan_registry.py | ~200 | deep-only | Plan 注册表 |
| knowledge_layout.py | ~100 | cross-tier | 知识路径常量 |

**小计**: ~2,058 LOC — 大部分 deep-only，知识路径常量 cross-tier

### B6. 其他 runtime 模块

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| develop_callback.py | 597 | deep-only | develop 回调 |
| develop_quality.py | 403 | deep-only | develop 质量检查 |
| checkpoint_request.py | 390 | deep-only | checkpoint 请求 |
| manifest.py | 475 | deep-only | Bundle manifest 生成 |
| entry_guard.py | 54 | deep-only | Entry guard 常量（但 PENDING_ACTIONS 常量是 cross-tier schema） |
| preferences.py | ~200 | deep-only | 偏好加载 |
| config.py | ~100 | deep-only | RuntimeConfig 加载 |
| resolution_planner.py | ~150 | deep-only | 解决方案规划 |
| sidecar_classifier_boundary.py | ~100 | deep-only | Sidecar 分类器 |
| vnext_phase_boundary.py | ~100 | deep-only | VNext 阶段边界 |
| builtin_catalog.py | ~100 | deep-only | 内置 skill 目录 |

---

## C. Installer

| 模块 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| models.py | 183 | cross-tier 语义承载点 | SupportTier, FeatureId, EnhancementGroup, HostCapability——产品注册模型。当前是 installer 内部代码，尚非冻结的公共 contract 包 |
| hosts/base.py | 122 | deep-only | HostAdapter 接口——hardcodes header+home_root+skills/sopify 结构 |
| hosts/codex.py | 57 | deep-only | Codex adapter |
| hosts/claude.py | 57 | deep-only | Claude adapter |
| hosts/__init__.py | 66 | deep-only | Host 注册表（仅 Codex/Claude） |
| bootstrap_workspace.py | 1,358 | deep-only | Workspace bootstrap——当前仅 deep host 路径 |
| inspection.py | 1,360 | deep-only | 安装状态检查/doctor |
| distribution.py | 415 | deep-only | 分发逻辑 |
| validate.py | 388 | deep-only | 安装验证 |
| payload.py | 260 | deep-only | Payload bundle 管理 |
| outcome_contract.py | 155 | deep-only | 安装结果契约 |
| runtime_bundle.py | 47 | deep-only | Runtime bundle 辅助 |

**统计**: models.py 是 cross-tier 语义承载点（但内部混着 installer-specific 类型），其余全部 deep-only

> **⚠️ installer/models.py 边界发现**：
> - runtime/workspace_preflight.py 直接 import `InstallError`
> - scripts/check-enhancement-declaration.py import `EnhancementGroup`, `SupportTier`
> - 存在循环依赖：models.py → hosts/ → models.py（通过 lazy import 绕过）
> - 文件内混着 cross-tier 类型（SupportTier, FeatureId, EnhancementGroup, HostCapability）和 installer-specific 类型（InstallError, InstallResult, parse_install_target）
> - **provisional 建议**：cross-tier 类型应拆出为独立模块或包；installer-specific 类型留在 installer/

---

## D. Scripts / 桥接入口

| 脚本 | LOC | 消费者 | 说明 |
|------|-----|--------|------|
| sopify_runtime.py | ~220 | deep-only | 主 runtime 入口 |
| runtime_gate.py | 129 | deep-only | Gate 入口 |
| decision_bridge_runtime.py | 171 | deep-only | 决策桥接入口 |
| clarification_bridge_runtime.py | 160 | deep-only | 澄清桥接入口 |
| develop_callback_runtime.py | 123 | deep-only | develop 回调入口 |
| plan_registry_runtime.py | 109 | deep-only | plan 注册表入口 |
| install_sopify.py | 220 | deep-only | 安装脚本 |
| check-install-payload-bundle-smoke.py | 359 | deep-only | 安装 smoke 测试 |
| 其他 check-*.py | ~2,000 | internal | 维护/检查脚本 |

---

## 汇总

| 分类 | 模块数 | 估算 LOC | 占比 | 说明 |
|------|--------|---------|------|------|
| **deep-only** | ~45 | ~22,000 | ~86% | 按模块级清点，约 86% LOC 目前服务于 deep-only 路径 |
| **cross-tier** | ~8 | ~1,500 | ~6% | 所有梯度宿主消费的 contract 面 |
| **candidate-kernel-bearing** | ~5 | ~2,000 | ~8% | 模块内含 cross-tier schema + deep-only writer 混合代码 |

### cross-tier 面（所有梯度需要）

1. `RunState` model
2. `PlanArtifact` model
3. `SkillActivation` / `SkillMeta` models
4. `RuntimeHandoff` schema（读取面）
5. `DecisionState` / `ClarificationState` schema（读取面）
6. `installer/models.py` 注册模型
7. `knowledge_layout.py` 路径常量
8. State 文件路径常量

### candidate-kernel 面（Shadow Writer 评估对象）

1. `handoff.py` — handoff 写入逻辑 + 状态转移映射
2. `state.py` — StateStore 读写核心
3. `decision.py` — DecisionState 构建
4. `clarification.py` — ClarificationState 构建
5. `_models/` — 共享 schema 定义

### ⚠️ 关键发现

1. **蓝图三层代码物理分层未兑现**——蓝图定义 "Protocol → Validator (~2K) → Runtime (~24K)" 三层，但代码中无 `validator/` 目录。验证逻辑散在 gate.py, workspace_preflight.py, action_intent.py, installer/validate.py 中。蓝图语义成立，实现物理分层待做。
2. **按模块级清点，约 86% LOC 目前服务于 deep-only 路径**——仅 ~14% 的代码面向 cross-tier 或含 candidate-kernel 逻辑。mixed 模块内部待第二轮细拆。
3. **candidate-kernel 集中在 state 读写 + schema**——handoff.py, state.py, decision.py, clarification.py 是 mixed 模块，模块级标记不等于整体都是 kernel 候选。
4. **installer 几乎全是 deep-only**——唯一的 cross-tier 语义承载点是 models.py，但它当前仍是 installer 内部代码，非冻结公共 contract 包。

### S1 第一轮收敛方向（已在第二轮完成）

1. ✅ Mixed 模块内部拆分
2. ✅ Validator 逻辑定位
3. ✅ installer/models.py 位置分析

---

## S1 第二轮: Sub-Surface 拆分表

> 仅覆盖 3 组高价值区域。行级分析。

### 区域 1: Candidate-Kernel-Bearing 模块拆分

#### runtime/handoff.py (655 LOC)

| sub_surface | kind | consumer | disposition | LOC |
|-------------|------|----------|-------------|-----|
| schema constants + reader + observability | read-schema / path-constant | cross-tier | keep-cross-tier | ~60 |
| route→handoff 映射 + host_action 策略 + 门控 | policy | deep-only | keep-deep-only | ~100 |
| resume context + execution summary | bridge-entry | deep-only | keep-deep-only | ~50 |
| build_runtime_handoff + artifact collectors + guardrail | bridge-entry | deep-only | **candidate-kernel** | ~230 |
| write_runtime_handoff | write-path | deep-only | **needs-shadow-writer** | ~10 |
| 工具函数 (重复辅助) | validation | internal | delete | ~60 |

#### runtime/state.py (506 LOC)

| sub_surface | kind | consumer | disposition | LOC |
|-------------|------|----------|-------------|-----|
| StateStore path constants + get/set/clear 全系列 | write-path | deep-only | **candidate-kernel** | ~210 |
| 会话生命周期 + 原子 IO + 保留策略 | validation / policy | internal | keep-deep-only | ~200 |
| 工具函数 (重复辅助) | validation | internal | delete | ~50 |

#### runtime/decision.py (611 LOC)

| sub_surface | kind | consumer | disposition | LOC |
|-------------|------|----------|-------------|-----|
| 路径常量 + response parser + readback + payload text | read-schema | cross-tier | keep-cross-tier | ~200 |
| build_* 构建器 + submission writer + 状态转换 | bridge-entry / write-path | deep-only | **candidate-kernel** | ~180 |
| 触发策略 + 选项匹配 | policy / validation | deep-only / internal | keep-deep-only | ~220 |

#### runtime/clarification.py (391 LOC)

| sub_surface | kind | consumer | disposition | LOC |
|-------------|------|----------|-------------|-----|
| 路径常量 + response parser + form/submission | read-schema | cross-tier | keep-cross-tier | ~200 |
| build_clarification_state + stale transition | bridge-entry / write-path | deep-only | **candidate-kernel** | ~50 |
| 触发策略 + 事实推断 | policy / validation | deep-only | keep-deep-only | ~130 |

#### runtime/_models/ (1,047 LOC)

| sub_surface | kind | consumer | disposition | LOC |
|-------------|------|----------|-------------|-----|
| 全部 dataclass 模型 (core + handoff + decision) | read-schema | cross-tier | **keep-cross-tier** | ~1,020 |
| 工具函数 | validation | internal | delete | ~27 |

**_models/ 是纯 cross-tier，不是 candidate-kernel。**

---

### 区域 2: Validator 逻辑分布

| 文件 | 验证 LOC | 类型 | 可提取? | 核心功能 |
|------|---------|------|---------|---------|
| action_intent.py | ~450 | validation + authorization | ✅ | 动作提案验证、主体绑定、授权降级/拒绝、stale receipt |
| deterministic_guard.py | ~200 | validation + guard | ✅ | 确定性 checkpoint 守卫、fail-closed |
| workspace_preflight.py | ~250-350 | validation + authorization | ⚠️ 部分 | 工作区预检、宿主能力授权（依赖 installer） |
| installer/validate.py | ~100-150 | validation | ⚠️ 部分 | 安装验证、capability 检查 |
| gate.py | ~150-200 | authorization + receipt | ❌ 编排层 | Gate 编排（与 engine 紧耦合） |

**可提取验证核心**: ~1,000-1,200 LOC → 与蓝图 "~2K Validator" 目标大致吻合

---

### 区域 3: installer/models.py 依赖边界

**消费者**: installer/ 内部 + runtime/workspace_preflight.py + scripts/ + tests/
**循环依赖**: models.py ↔ hosts/（lazy import 绕过）
**类型混合**: cross-tier 语义 (SupportTier, FeatureId 等) + installer-specific (InstallError, InstallResult 等)
**provisional 建议**: cross-tier 注册类型应独立化

---

## S1 综合结论

### 三个核心问题

| 问题 | 回答 |
|------|------|
| Schema 和 writer 拆清了吗？ | ✅ 是。cross-tier schema (读) 和 deep-only writer (写) 逻辑上清晰可分 |
| Validator 逻辑在哪？ | ✅ 定位完成。~1K-1.2K LOC 可提取，主要在 action_intent + deterministic_guard |
| candidate-kernel 里哪些是真候选？ | ✅ 已区分。真 kernel = **写入逻辑 ~670 LOC**，_models/ 是纯 cross-tier 不是 kernel |

### 修订后量化

| 分类 | LOC | 占比 | 说明 |
|------|-----|------|------|
| pure deep-only | ~20,800 | ~82% | 引擎/路由/gate/output/策略/编排 |
| cross-tier schema + read | ~2,500 | ~10% | _models/ + path constants + parsers + form builders |
| candidate-kernel (writer) | ~670 | ~2.6% | handoff/state/decision/clarification 写入逻辑 |
| validator-extractable | ~1,000-1,200 | ~4-5% | action_intent + deterministic_guard + preflight |
| deletable | ~150 | ~0.6% | 重复工具函数 |
