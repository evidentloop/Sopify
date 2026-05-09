# 技术设计: P4b Runtime Surface Consolidation

## 方案概述

分 4 个阶段顺序执行（硬约束，不可并行跳跃）：
0. Test inventory re-audit + hard/soft gate matrix
1. CI / release-preflight 真实降载
2. Runtime 旧面删除（prove-kept-or-delete）
3. Implementation-mirror tests 收口

原则："先删后并，不先设计新结构"。

## Scope 边界

### 在 scope 内

- 删除 keep-list 外的 compat / bridge / fallback / dead code
- Test inventory re-audit：纠正 contract / implementation-mirror 误分类
- CI + release-preflight 真实降载：hard gate 仅含 contract + smoke + distribution + eval，implementation-mirror 降为 advisory
- 删除保护对象已不存在的 implementation-mirror tests
- 删完后评估是否有结构性合并价值（非 LOC 驱动，不预先承诺）

### 不在 scope 内

- 不改 machine contract / protocol 语义
- 不扩 canonical budget（削减预算表的 target/hard max 不变）
- 不做 output.py 改造（属 P4c）
- 不改 host adapter / installer
- 不预先设计新模块结构

## 阶段设计

### Phase 0: Test Inventory Re-audit + Hard/Soft Gate Matrix

当前测试分类存在**语义失真**：23 个测试文件标为 contract，但其中多个实际测试 runtime 内部实现（如 `test_runtime_failure_recovery.py`、`test_runtime_router.py`），只有 1 个标为 implementation-mirror（`test_runtime_knowledge_layout.py`）。如果不先纠正分类，Phase 2 删代码会触发标为 contract 的测试红灯，卡死 hard gate。

注意：混合文件（如 engine.py）的测试可能部分是 contract、部分是 mirror——engine.py 本身在主链上，但也包含大量 compat/bridge/旧 route 胶水。对此类文件需要**用例级**而非文件级判定。

**混合文件分类承载机制**：在测试文件头部保留 `# Test classification: contract`（表示文件主体分类），对其中属于 implementation-mirror 的用例方法加 `@pytest.mark.implementation_mirror` marker。CI/preflight 按 marker 选择性跳过：hard gate 用 `-m "not implementation_mirror"` 运行，soft gate 用 `-m implementation_mirror` 运行。不拆文件，避免增加文件数。

**产出物**：
1. 每个 `tests/test_*.py` 的 contract / implementation-mirror / smoke / distribution 重标（混合文件的测试按用例粒度判定）
2. Hard/soft gate matrix：contract + smoke + distribution + eval = hard gate；implementation-mirror = soft gate（advisory）
3. 判定标准（锚点优先级）：测试用例的保护对象在 **keep-list** 或 **canonical main chain** 或 **distribution/install user-facing contract** 中 → contract；否则 → implementation-mirror。CI hard gate 是这些锚点的投影结果，不反过来作为分类的原始事实

### Phase 1: CI / Release-Preflight 真实降载

当前 `.github/workflows/ci.yml:80` 直接跑 `python3 -m unittest discover tests -v`（全量单测硬阻断 CI），`scripts/release-preflight.sh:67` 跑 `python3 -m pytest "$ROOT_DIR/tests" -v`（全量单测硬阻断发布）。两者的 runner 还不一致（unittest vs pytest）。如果只改 preflight 文案分层而不改 CI test selection，Phase 2 删代码仍会卡死。

**当前 gate 项（release-preflight.sh）**：
1. sync skills
2. verify sync
3. version consistency
4. builtin catalog drift
5. fail-close contract
6. context checkpoints
7. runtime unit tests（`pytest tests`）
8. install/payload bootstrap smoke
9. prompt runtime gate smoke
10. bundle runtime smoke
11. optional skill eval quality gate

**收口策略**：不删除任何 gate 项。将 gate 分为两层：
- **hard gate**（blocking）：contract checks (1-6) + smoke (8-10) + eval (11)
- **soft gate**（advisory，不阻断发布/CI）：implementation-mirror tests (7)

落实到两个入口：
- `scripts/release-preflight.sh:67`：将 `pytest tests` 替换为仅跑 hard gate 分类的测试；implementation-mirror 测试降为 advisory（失败不阻断）
- `.github/workflows/ci.yml:80`：将 `unittest discover tests` 替换为仅跑 hard gate 分类的测试；implementation-mirror 测试降为 advisory step

hard/soft 边界由 Phase 0 产出的测试分类决定，不由测试框架（unittest vs pytest）决定。

### Phase 2: Runtime 旧面删除（prove-kept-or-delete）

方法论：不按文件修枝，而是按 P4a frozen surface 反推。对每个 runtime 文件/函数，验证三个条件：
1. 在 keep-list 15 条中？
2. 在 ActionProposal → Validator → Handoff/Receipt/Archive 主链调用图上？
3. 在 distribution/install user-facing contract 中？

三个都不命中 → 默认整段删除，不做精细缝合。三个命中任一 → 保留，仅删其内部 legacy wrapper/fallback 分支。CI hard gate 是上述三个锚点的投影，不反过来作为保留依据。

以下 Tier 分层是 prove-kept-or-delete 验证的预期结果排序，不是穷举清单——验证中发现的额外可删面直接归入对应 Tier。按削减信心和影响面分 3 个 tier 执行：

**Tier 1: 高信心删除（~700–1,000 LOC）**

| 文件 | 动作 | 估算 LOC | 理由 |
|------|------|---------|------|
| decision_bridge.py (864) | 大幅裁剪或整体删除 | 180–220 | CLI fallback/text renderer bridge；如 plan_orchestrator 不再消费则可整体删 |
| clarification_bridge.py (401) | 大幅裁剪或整体删除 | 140–180 | host-side bridge helper；同上 |
| workspace_preflight.py (925) | 裁剪 legacy/fallback 段 | 220–320 | vendored fallback、legacy workspace entry、LEGACY_* 分支 |
| plan_orchestrator.py (272) | 裁剪 bridge 胶水 | 120–180 | CLI/bridge wrapper；如 bridge 文件删除则大部分可删 |

**Tier 2: 中信心删除（~600–1,000 LOC）**

| 文件 | 动作 | 估算 LOC | 理由 |
|------|------|---------|------|
| failure_recovery.py (719) | 裁剪 legacy 恢复路径 | 250–400 | legacy snapshot handling + 通用 evaluator |
| context_snapshot.py (973) | 裁剪 compat 字段 | 50–80 | current_plan_proposal compat、legacy global review state |
| router.py (795) | 裁剪旧分支分类 | 40–80 | old-branch / fallback classification |
| gate.py (941) | 仅裁剪 legacy wrapper/fallback | 15–30 | action_proposal_retry 主路径在 keep-list（blueprint design.md:354），不可删；仅删周边 legacy 分支（如 _fallback_state_contract 等） |
| message_templates.py (265) | 精简模板 | 20–60 | 渲染模板胶水 |
| action_intent.py (884) | 裁剪 fallback | 20–40 | DECISION_FALLBACK_ROUTER、allow_current_plan_fallback |

**Tier 3: engine.py 专项（~1,200–1,800 LOC）**

engine.py (2,737 LOC, 68 functions) 是最大单点。需要逐段审查：
- 旧 route 处理函数（已不在 canonical route family 内的）
- checkpoint 编排中支持被裁剪 checkpoint type 的段落
- compat/bridge 胶水（调用 decision_bridge / clarification_bridge 的段）
- 已被 Tier 1 删除的文件的调用残留

engine.py 不预先承诺削减量——Tier 1 + Tier 2 删完后，根据调用图残留再定。

### Phase 3: Implementation-mirror Tests 收口

Phase 0 已完成测试分类重标，Phase 2 删完后，找出保护对象已不存在的 mirror tests：
- 对应 runtime 模块已删除的测试文件（Phase 0 已重标为 implementation-mirror）
- 测试 compat/bridge 行为的用例
- 测试已删除 route/checkpoint type 的用例

当前 `tests/` 共 19,158 LOC。预计可清理与 Phase 2 删除面对应的测试代码。

注意：Phase 0 的 re-audit 是本阶段可执行的前提。如果跳过 Phase 0，大量实际测试内部实现的文件仍标为 contract，Phase 2 删代码后 hard gate 会红，本阶段会退化为"边删代码边争论测试标签"。

## Phase 2 执行结论

### 全量 prove-kept-or-delete 扫描结果

对全部 runtime/*.py（24,354 LOC、20+ 文件）执行 prove-kept-or-delete 方法论，结论如下：

**Tier 1 结果（全部偏离预期）**：

| 文件 | 原估 LOC | 实际可删 | 原因 |
|------|---------|---------|------|
| decision_bridge.py | 180–220 | **0** | 不在 engine/gate 主链上，但绑定 distribution anchor（manifest.py、entry_guard.py、installer/validate.py、installer/runtime_bundle.py、check-runtime-smoke.sh）。删除需同步改 distribution 面，超出 P4b scope（"不改 host adapter / installer"）|
| clarification_bridge.py | 140–180 | **0** | 同上，distribution anchor 绑定 |
| workspace_preflight.py | 220–320 | **0** | vendored fallback (228 LOC) 是 bundle 部署下的生产路径（installer 包不可用时必须走），11 个 hard gate 测试验证。LEGACY_FALLBACK_SELECTED 分支被 5 个 hard gate 测试文件覆盖，是活跃 contract |
| plan_orchestrator.py | 120–180 | **0** | bridge 文件保留后，桥接胶水不可删 |

**Tier 2 结果（极小量）**：

| 文件 | 原估 LOC | 实际可删 | 原因 |
|------|---------|---------|------|
| failure_recovery.py | 250–400 | **0** | 全部在 distribution anchor 上 |
| context_snapshot.py | 50–80 | **0** | `_should_ignore_legacy_global_review_state` 被内部调用，改变行为有风险 |
| router.py | 40–80 | **9** | `_contains_intent` (3 LOC) + `_runtime_skill` (6 LOC) 确认死代码 |
| gate.py | 15–30 | **0** | `_action_proposal_from_command_alias` 在主路径上（gate.py:173），非 legacy |
| message_templates.py | 20–60 | **0** | 全部被 scripts 消费 |
| action_intent.py | 20–40 | **0** | `resolve_action_proposal` 被 gate.py:84 主动调用 |

**Tier 3（engine.py 补充扫描）**：

| 函数 | 可删 LOC |
|------|---------|
| `_phase_for_route` | **6** |

**全量死代码总计：15 LOC**（router.py 9 + engine.py 6）。已删除并通过 hard gate 验证。

### 根因分析

P4b 原假设"fallback/bridge/compat 是可删旧面"不成立。实际复核发现：

1. **vendored fallback 是生产路径**：workspace_preflight.py 的 except ModuleNotFoundError 块在 bundle 部署中（无 installer 包）是唯一可用路径
2. **bridge 文件绑定 distribution anchor**：虽不在 engine/gate 主链上，但 manifest、installer、smoke 均依赖其存在
3. **legacy 分支有活跃 contract 覆盖**：LEGACY_FALLBACK_SELECTED、legacy helper argv 等被 hard gate 测试保护
4. **runtime 代码密度高**：全量死函数扫描仅发现 3 个（15 LOC），其余均在 3 个锚点（keep-list / 主链 / distribution）至少命中一个

### 结论

**runtime 在当前 contract 约束下已接近最小可行体积。** <20K LOC 目标在"不改 host adapter / installer、不删 contract surface"的约束下不可达。

P4b 的实际交付物不是 LOC 削减，而是：
1. Phase 0：test re-audit 建立了 653 hard / 31 soft gate 的分类基线
2. Phase 1：CI + preflight 真实降载，解锁未来删代码时的 gate 隔离能力
3. Phase 2：prove-kept-or-delete 全量扫描，用 evidence 证明了 runtime 的真实状态

### 后续方向建议（不在 P4b scope 内执行）

进一步缩减 runtime 需要改变约束条件，有三个独立方向：

**(A) Contract Surface Shrinkage**：显式删除部分 contract surface（如 bridge capability、legacy fallback contract），允许 manifest/installer/smoke/tests 跟着同步收缩。这不是"删实现"而是"少承诺能力"。需要独立的 blast radius 分析。

**(B) Canonical Registry Consolidation**：对暂时保留的 contract，将分散在 runtime/manifest/installer/tests 的重复投影收拢为单一事实源。前提是定量验证"真重复" LOC 足够大（建议 >500 LOC 才值得投入）。注意过度设计风险。

**(C) Runtime Sunset Roadmap**：战略层面，将 runtime 从"必须依赖"降级为"可选适配层"，新宿主默认走 Protocol/Convention 模式。这是蓝图层面的方向决策（background.md:7, protocol.md:31），不适合作为战术执行计划。

推荐顺序：P4b-close → (A) 设计审计（不改代码）→ P4c。

## 红线约束

- ActionProposal → Validator → Handoff/Receipt/Archive 主链完整
- P4a keep-list 内保留，keep-list 外默认删除
- 不允许在 release gate 未降载前同步大规模删除 runtime 与 mirror tests
- 削减预算表的 target/hard max 不变
- 不先承诺合并方案——删完再评估是否有结构性合并价值（非 LOC 驱动）

## 风险

- **削减不足风险**：纯删估计到 22–23K，距 <20K 有 2–3K 缺口。缓解：prove-kept-or-delete 方法论比按文件修枝更激进，可能发现更多可删面；Tier 3 engine.py 专项可能补足；仅在有结构性价值时合并，不做 LOC 化妆
- **主链回归风险**：删错导致 canonical flow 断裂。缓解：每个 tier 完成后跑 pytest，Phase 1 已保留 hard gate
- **engine.py 风险**：2.7K LOC 的巨型文件改动面大。缓解：不预先承诺削减量，逐段审查
- **测试分类失真风险**：23 个 contract 中有多个实际测试内部实现。缓解：Phase 0 先做 re-audit，不跳过
