---
plan_id: 20260522_runtime_slimming_kernel_extraction
feature_key: runtime_slimming_kernel_extraction
level: standard
lifecycle_state: archived
knowledge_sync:
  project: skip
  background: skip
  design: skip
  tasks: skip
archive_ready: true
plan_status: completed
---

# 任务清单: Runtime Slimming — Orchestration Kernel Extraction

## 完成标志

本方案完成标志：

1. 已产出 4 张输出表：
   - kernel 模块边界表（extract-to-kernel 清单）
   - 删除候选表（delete_now + co-delete）
   - 整包退役阻塞表
   - consumer 决策表
2. 已定义 orchestration kernel 边界（模块 / 文件 / 职责）
3. 维护者已确认 kernel 范围与退场范围
4. 已完成 kernel 提取与非 kernel 面删除，并记录实施结果
5. 已完成最小必要验证与文档同步，足以决定归档或继续拆下一实施包

## 状态概览 (2026-05-26)

> **runtime/ 当前**: 37 个 .py 文件, 16,286 LOC

| 阶段 | 状态 | 摘要 |
|------|------|------|
| 1. 蓝图 delta 校验 | ✅ 完成 | 5 项审计全通过 |
| 2. 当前消费者扫描 | ✅ 完成 | 4 类清单 + consumer 判定 |
| 3. 删除就绪结论 | ✅ 完成 | kernel 边界锁定, 退场量级 ~38K LOC |
| 4. 审计后删除 | ✅ 完成 | 4.1-4.13B 全部完成; 4.12 naming polish ✅ |
| 5. 文档更新 | ✅ 完成 | 5.1-5.7 全部完成; 5.4 deferred=docs-only; 5.5 B-lite; 5.6 grep 通过 |
| 6. contract 面清理 + engine 重构 | ✅ 完成 | 6.1-6.6 全部收完, −6,400+ LOC |

### 执行顺序说明

实际执行顺序并非文档编号顺序。Topic 6 是在 4.10d 之后、4.2-4.6 之前执行的：

```
4.1 → 4.7-4.10 → 4.10a → 4.10b(partial) → 4.10c → 4.10d(W1-W3)
                                                       ↓
                                               6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6
                                                                                  ↓
                                                              P4.6-A → 4.13-A → 4.13-B → 后续: 4.10b / 4.13-PhaseB / 5.x
```

## 1. 蓝图 delta 校验 ✅
- [x] 1.1 确认 `blueprint/design.md` 中与 runtime 删除相关的正式约束仍成立
- [x] 1.2 以 P4b / P4b.5 / P5 / P6 为既有基线，只列出本次审计新增的 delta，不重复复述已裁定结论
- [x] 1.3 明确本次审计命中的蓝图分层、非目标与不重复范围
- [x] 1.4 引用 `design.md` L727 前提，明确"当前存在消费者"不等于"维护者必须继续保留该路径"
- [x] 1.5 把 `deferred` 生命周期语义冲突记为副发现，暂不先改 registry contract

## 2. 当前消费者扫描 ✅
- [x] 2.1 扫描 `installer/`、`scripts/`、`tests/`、宿主接入路径对 `runtime/*` 的直接 import / 调用
- [x] 2.2 区分 `sopify_contracts` / `canonical_writer` 已覆盖能力与仍留在 `runtime` 的生产职责
- [x] 2.3 形成 `extract-to-kernel` / `delete_now` / `keep_for_legacy_runtime` / `blocking_full_retirement` 四类清单
- [x] 2.4 对每个 consumer 标记 `must_keep` / `keep_if_preserving_legacy` / `co-delete_candidate`
- [x] 2.5 补充 `plan_registry.py` 对 `deferred` 的实际 reconcile 行为，判断其属于本主题的哪个 consumer / contract 边界

> **S2 advisor 修正 (2026-05-22):**
> 1. `canonical_writer/_resume.py` 不是 runtime 依赖 — 是已成功下沉的共享校验逻辑
> 2. `models.py`(DEPRECATED) / `state.py`(runtime helper) / `config.py`(config loader) 不是内核候选
> 3. `go_plan_runtime.py` 是产品决策，不默认算内核
> 4. 测试分两类：legacy tests 共删 vs gate/checkpoint contract tests 必须重建

## 3. 删除就绪结论 (S3 — ✅ 全部完成)
- [x] 3.1 产出文件级删除候选表，明确每个候选的依据和风险
  > design.md §S3.1: runtime/ 42 entries ~18.8K + scripts/ 15 entries (7 co-delete + 4 release cutover + 3 in-place cutover + 1 产品决策) + tests/ 全分类
  > agent 扫描结果经 target-state-first + kernel context scope 护栏修正
- [x] 3.2 分别产出"保留 legacy 路径"与"目标态优先、允许同步退场"两种口径下的阻塞表
  > design.md §S3.2: legacy-preserving 下几乎无法删除；target-state-first 下全部阻塞项已有解除方案
- [x] 3.3 给出推荐策略、删除准入范围与后续实施切片建议
  > design.md §S3.3: 退场量级 ~28K+ LOC，S4 优先级 cutover→拆分→替换→批删→thin shell→测试
- [x] 3.4 明确 `target-state-first` 下退场后的保留面清单（双栏）：
  - **retain-as-is**：`sopify_contracts/`、`canonical_writer/`、`.sopify-skills/` — 无 runtime 代码依赖，可直接保留
  - **retain-after-decoupling**：`installer/validate.py`、`installer/bootstrap_workspace.py`、`installer/inspection.py`、`scripts/install_sopify.py`、`scripts/sopify_init.py` — 当前仍有 runtime import / bundle 验证硬依赖，需先解耦再保留
- [x] 3.5 明确退场量级修正：`runtime/` 非 kernel ~18.8K + runtime-coupled scripts ~4K + runtime-coupled tests ~15.3K ≈ **~38K LOC**（减去 kernel core+support ~5K 及 kernel 等价覆盖 tests）
- [x] 3.6 产出 retain-after-decoupling 五文件 cutover 表：列出当前耦合、替代依据（payload-only / `sopify.json` / canonical state）、保留后的行为边界
- [x] 3.7 明确 `installer/runtime_bundle.py` 为 pure legacy surface，归入 Step 3 同步退场而不是 Step 2 解耦保留
- [x] 3.8 记录 Step 2 固定执行顺序：`installer/inspection.py` → `scripts/sopify_init.py` → `installer/validate.py` → `installer/bootstrap_workspace.py` → `scripts/install_sopify.py`
- [x] 3.9 确认 orchestration kernel extraction 作为本包内执行目标，不另开独立方案包
- [x] 3.10 定义 orchestration kernel 最小模块边界：三层分类，详见 design.md §S3 Kernel Boundary Audit
  > **kernel core** (7): gate.py / entry_guard.py / execution_gate.py / router.py / handoff.py / checkpoint_request.py / checkpoint_materializer.py
  > **kernel support** (3+1): config.py / state.py / deterministic_guard.py + context_snapshot.py(暂保留，router 重度依赖)
  > **非内核可暂留**: gate_output.py — text rendering，不计入 kernel
  > **删除**: models.py (DEPRECATED)
  > LOC 现状 kernel core+support ~3.9K + context_snapshot 973 → 瘦身方向收敛但不锁具体 LOC 目标
- [x] 3.11 确认 kernel 与 `sopify_contracts` / `canonical_writer` 的接口约定，确保 kernel 不反向依赖 runtime 其余面
  > kernel 对外依赖: sopify_contracts (类型) + canonical_writer (写+时间) + stdlib
  > 14 个非内核 runtime 依赖必须在 S4 切断，详见 design.md §非内核 runtime 依赖汇总
- [x] 3.12 列出 kernel 需要保留的最小测试覆盖面
  > **保留等价覆盖** 7 个: test_runtime_gate / test_runtime_execution_gate / test_runtime_router / test_runtime_state / test_runtime_sample_invariant_gate / test_contract_consistency / test_runtime_config
  > **共删** 2 个: test_context_checkpoints / test_runtime_failure_recovery
  > "保留等价覆盖" ≠ 原封不动搬，具体重写方式在 S4 按实际 kernel 接口决定

## 4. 审计后删除 (⚠️ 部分完成 — 剩余项见"后续路线"节)
- [x] 4.1 维护者已在 **2026-05-22** 确认采用 `target-state-first` 口径，并锁定本包后续删除范围以“先解耦保留面，再同步退场 runtime + legacy deep path”为准
- [x] 4.2 删除所有已批准的 `delete_now` 面（不含 kernel 保留模块） ✅ 已通过 4.10d Wave 1-3 + 6.1 + 6.4 全部执行完
- [x] 4.3 若采用 `target-state-first`，同步删除已批准的 `co-delete candidate` 及其对应 legacy consumer（不含 kernel 保留模块） ✅ 同上
- [x] 4.4 记录每个删除项的依据、影响范围与验证结果 ✅ tasks.md 执行备注 + commit message = 删除记录; 不另开 delete ledger
- [x] 4.5 明确哪些 `keep_for_legacy_runtime` / `blocking_full_retirement` 面留待后续包处理 ✅ 刷新至 6.6 后现实 (2026-05-24)
  > **A2 判定表已同步** (见上方 4.10b A2 节):
  > - skill_registry / skill_resolver: 已删 (6.4)
  > - plan_registry: 6.5 裁定为独立治理层保留
  > - plan_scaffold: blocker 从 engine.py → _planning.py; 结构决策归 4.10b
  > - 5 个 retained 模块判定不变
  > **当前 keep_for_legacy / blocking 面**: 不再有 runtime 模块级的 blocking 面; scripts/installer 层剩余阻塞已移入 4.13 installer 瘦身
- [x] 4.6 scripts / installer / evals legacy surface 退场 (2026-05-24 裁定; 2026-05-25 P4.6-A 执行完毕)
  > **裁定口径**: 不是主链路 (gate → machine truth → handoff → host consume) 就干掉。CI/release pipeline 引用是"活跃流程依赖"，不是"必须保留的产品能力"。
  >
  > ### 🟢 KEEP — 主链路或活跃 CI 硬约束 (3 个)
  > | 文件 | 理由 |
  > |------|------|
  > | `scripts/runtime_gate.py` (129) | 产品 gate 入口，所有宿主第一跳 |
  > | `scripts/release-preflight.sh` (196) | release 编排器，pre-commit hook 入口 |
  > | `scripts/generate-builtin-catalog.py` (225) | CI 活跃 (ci.yml:44)，builtin_catalog.py 仍被 manifest 消费 |
  >
  > ### 🔴 P4.6-A 已执行 — 独立死面退场 ✅ (5 个目标, 7 文件, −251 LOC)
  > | 文件 | LOC | 执行结果 |
  > |------|-----|----------|
  > | `scripts/check-host-doc-contract.py` | 74 | ✅ 已删 |
  > | `scripts/preferences_preload_runtime.py` | 72 | ✅ 已删 + manifest/preflight/smoke/tests 联动清理 |
  > | `scripts/plan_registry_runtime.py` | 109 | ✅ 已删 + manifest/sync-assets/tests 联动清理 |
  > | `scripts/check-skill-eval-gate.py` | 305 | ✅ 已删 + ci.yml/release-preflight/CONTRIBUTING×2/blueprint 联动清理 |
  > | `evals/` (整组) | ~50 | ✅ 已删 (baseline/slo + untracked report) |
  >
  > ### ➡️ 原 P4.6-B 目标 → 移入 4.13 installer 瘦身
  > | 文件 | 原裁定 | 新状态 | 理由 |
  > |------|--------|--------|------|
  > | `scripts/check-prompt-runtime-gate-smoke.py` (369) | DELETE | KEEP+SLIM | release gate 活跃依赖，产品决策: 项目级安装保留 |
  > | `scripts/check-install-payload-bundle-smoke.py` (~200) | DELETE | KEEP+SLIM | 同上 |
  > | `installer/runtime_bundle.py` (~80) | DELETE | REWRITE | 壳套壳 (Python→bash→rsync)，能力保留实现重写 |
  > | `scripts/sync-runtime-assets.sh` (124) | DELETE | REWRITE | 同上，co-rewrite with runtime_bundle.py |
  >
  > ### 🟡 CUTOVER — 路径名冻结太深，需先改引用者 (2 个, 不变)
  > | 文件 | LOC | 阻塞 |
  > |------|-----|------|
  > | `scripts/sopify_runtime.py` | 157 | entry_guard.py + installer/bootstrap+validate + pre-commit + CONTRIBUTING |
  > | `scripts/check-runtime-smoke.sh` | 239 | ci.yml:91 + release-preflight + installer/validate.py |
  >
  > ### 已删 (4.10d / 6.x 已执行)
  > - ~~`clarification_bridge_runtime.py`~~ ✅ 4.10d W3
  > - ~~`decision_bridge_runtime.py`~~ ✅ 4.10d W3
  > - ~~`develop_callback_runtime.py`~~ ✅ 4.10d W2
  > - ~~`go_plan_runtime.py`~~ ✅ 4.10d W3
- [x] 4.7 对 retain-after-decoupling 五文件（`installer/validate.py`、`installer/bootstrap_workspace.py`、`installer/inspection.py`、`scripts/install_sopify.py`、`scripts/sopify_init.py`），在删除 runtime 前同步去除 runtime import 和 bundle 硬依赖，确保安装链路可用
  > **S4 Step 1 已完成**: validate/bootstrap 裁剪为 kernel-only bundle 验证，sopify_init/install_sopify 去除 preferences_preload。payload.py 同步裁剪 _REQUIRED_BUNDLE_CAPABILITIES。inspection.py 保留 resolve_context_snapshot（context_snapshot 已重分类为 kernel support）。75 installer tests pass。
- [x] 4.8 `scripts/sopify_status.py` / `scripts/sopify_doctor.py` 不单列 cutover；仅验证其通过 `installer/inspection.py` 的改造继续可用
  > 27 status/doctor tests pass (preferences_preload 降级为 fail，符合预期)
- [x] 4.9 Step 2 具体落地顺序按 `inspection.py` 优先执行，避免 Step 3 删除 runtime 后 `status` / `doctor` 先发生 import failure
  > inspection.py 保留 resolve_context_snapshot import，不再需要单独脱钩
- [x] 4.10 Step 2: retained kernel/support 模块的 `from .models` → `from sopify_contracts.*` 机械 rewire
  > **已完成 9 files**: config.py, state.py, deterministic_guard.py, router.py, handoff.py, checkpoint_request.py, checkpoint_materializer.py, execution_gate.py, context_snapshot.py。runtime/models.py 保留为非内核消费者的过渡桥，Step 3 删除。
  > **不在 Step 2**: skill_resolver.py（非内核，Step 3 co-delete/reclassify）、gate_output.py（无 .models import）、entry_guard.py（无 .models import）、tests（走 bridge 仍合法，Step 3 同步处理）。
  > **Step 1b**: check-runtime-smoke.sh 删除 sopify.json 断言（install-time artifact，非 engine 产物）。release-preflight.sh 全链恢复通过。其余 release chain 脚本（check-install-payload-bundle-smoke.py, check-skill-eval-gate.py, generate-builtin-catalog.py）暂不改——runtime 导入仍合法。
- [x] 4.10a **Step 3 Package B: kernel orchestration seam extraction** ✅
  > **新建** `runtime/_kernel_turn.py` (~720 LOC)，导出 `execute_kernel_turn()`。
  > gate.py / cli.py / plan_orchestrator.py 全部切换到 `from ._kernel_turn import execute_kernel_turn`。
  > engine.py `run_runtime()` 降级为 lazy-import wrapper（-611 LOC 净减），但仍作为兼容入口存在。所有 helper 函数保留原位。
  > 7 处 test mock patch 更新。743 tests pass，release-preflight 全链通过。
  >
  > **Advisor review 3 findings 处理**:
  > - Finding 1 (High): _kernel_turn 仍从 engine.py import 29 helpers — 接受为过渡状态，engine import 已分组标注 (18 kernel path + 11 non-kernel handler)，Package A 内联/删除
  > - Finding 2 (Medium): ✅ 修复 — `from .models` 全部替换为 `from sopify_contracts.*`
  > - Finding 3 (Medium): ✅ 修复 — docstring 精确描述过渡状态和未达目标
  >
  > **Package B 实际达成**:
  > 1. retained callers (gate/cli/plan_orchestrator) 不再直接引用 engine.run_runtime 符号 ✅
  > 2. _kernel_turn 不消费 runtime.models bridge ✅
  > 3. gate.py 不再直接 import engine 模块（但通过 _kernel_turn → engine helpers 仍有间接依赖）✅
  >
  > **Package B 未达**:
  > - engine.py 实现依赖未切断（_kernel_turn → engine 29 helpers，间接拉入 engine 导入链）
  > - run_runtime() 兼容 wrapper 仍在 engine.py，尚未删除
  > - _kernel_turn 仍包含 11 个 non-kernel route handler 的分发逻辑
  > - 以上均属 Package A 范围
- [x] 4.10b **Step 3 Package A: _kernel_turn → engine 依赖切断 + 合同面审计 + 批量删除** — re-scoped / partial close (2026-05-23); **plan_scaffold 单职责重构 + runtime/plan/ 包化** ✅ 完成 (2026-05-25)
  > 判断边界: 按"当前宿主可见 contract 还在不在"删，不按模块名猜测。行为还需要但文件不需要时，优先内联到 retained 模块；不新造模块/层次/public surface。
  >
  > **A1: _kernel_turn → engine 依赖切断（仅切实现耦合，不删功能面）** ✅ 完成
  > - 将 18 个 kernel-path helpers + 9 个 transitive deps（共 27 项: 4 constants + 23 functions）从 engine.py 内联到 _kernel_turn.py
  > - 完成标志: `from .engine import (kernel path 组)` 全部删除，_kernel_turn.py 对 engine.py 的 import 仅剩 11 个 non-kernel handler
  > - 延后: `_kernel_turn.py` 命名暂不调整；待 retained 模块集合稳定后在 4.12 统一评估
  >
  > **A2: live contract audit** ✅ 完成 (2026-05-23)
  >
  > 审计口径: 先锁主链保留项，再对弱连接叶子施加删除压力。审计单位是行为面，不是 helper 同权逐判。
  > contract 证据面: router.py SUPPORTED_ROUTE_NAMES / output.py:178 / gate.py / tests。
  >
  > **行为面判定 (engine.py → _kernel_turn.py 的 10 个 import)**:
  > - retain (engine import): planning 主链 / state_conflict / cancel_active / clarification_resume / decision_resume / archive_lifecycle / proposal→exec / generated_files / activation 元数据
  > - **deleted** ✅ 2141ed6: runtime skill 执行 sidecar（_find_skill + runtime_skill_id 分支 + skill_runner.py，-187 LOC）
  >
  > **第二层模块重分类** (原 S3.1 co-delete → 实际 retained):
  > | 模块 | LOC | 新分类 | 关键证据 |
  > |------|-----|--------|---------|
  > | `archive_lifecycle.py` | 832 | **retain as module** ✅ 维护者确认 | _kernel_turn.py:53-59; 蓝图 canonical capability |
  > | `kb.py` | 464 | **retain as module** ✅ 维护者确认 | _kernel_turn.py:63,534 bootstrap_kb |
  > | `clarification.py` | 387 | **retain as module** ✅ 维护者确认 | router + checkpoint_request + handoff + _kernel_turn |
  > | `decision.py` | 605 | **retain as module** ✅ 维护者确认 | router + handoff + _kernel_turn |
  > | `context_recovery.py` | 94 | **retain as module** ✅ 维护者确认 | _kernel_turn.py:35 recover_context |
  > | `plan_registry.py` | 953 | **retain as independent governance layer** ✅ 6.5 裁定 | _planning.py + archive_lifecycle + output; YAML 写入已迁出到 _yaml.py |
  > | `skill_registry.py` | — | **deleted** ✅ 6.4 | discovery 退场 |
  > | `skill_resolver.py` | — | **deleted** ✅ 6.4 | resolve_route_candidate_skills 退场，candidate_skill_ids 改为静态 tuple |
  > | `plan_scaffold.py` | 466→~200 | **refactored → runtime/plan/ package** ✅ 4.10b 完成 (2026-05-25) | 拆为 scaffold/lookup/intent/identity 4 个单职责模块 + registry.py 迁入; create_plan_scaffold() registry side-effect 上提到 _planning.py; 626 tests green |
  > | `skill_runner.py` | — | **deleted** ✅ 4.10b A3 | 悬空路径 |
  >
  > 5 个模块 (archive_lifecycle / kb / clarification / decision / context_recovery) 经维护者确认为 retain as module。
  > plan_registry.py 经 6.5 裁定为独立治理层保留; YAML 写入迁出到 _yaml.py。
  > skill_registry / skill_resolver: 6.4 已删除 (discovery 退场)。
  > plan_scaffold.py: 维护者确认**暂时保留独立模块**；不内联到 `_planning.py`。后续只允许收窄到 scaffold creation + artifact return，不再承载 planning/gate/state 判断。
  >
  > **A3: 立即删除面** ✅ 收口
  > - 已完成: runtime skill execution sidecar (-187 LOC) ✅ 2141ed6
  > - 否决: 38 项大内联方案（~1,655 LOC 搬进 _kernel_turn.py 是换文件名不收缩）
  > - 剩余: plan_scaffold.py 已完成单职责重构 ✅ (2026-05-25)：拆为 runtime/plan/{scaffold,lookup,intent,identity,registry}.py; create_plan_scaffold() 不再含 registry write
  > - engine.py: 6.6 完成后已瘦身至 343 LOC（conflict/cancel + activation + archive + run_runtime wrapper）；planning 主块已迁出到 _planning.py
  > - S3.1 大 co-delete 表不再作为执行清单；已降级为旧假设
- [x] 4.10c Step 3 Package C: models.py bridge 退场 ✅ 完成 (2026-05-23)
  > **C1: retained 模块 rewire** ✅ 完成 (dbd1bc6)
  > 9 个 A2 retained 非 kernel 模块已从 `from .models` 切到 `sopify_contracts.*`:
  > archive_lifecycle / clarification / context_recovery / decision / kb /
  > output / plan_registry / skill_registry / skill_resolver
  >
  > **C2: legacy 消费者清理 + models.py 删除** ✅ 完成 (e346583)
  > 13 个 runtime 模块 + 3 个 test 文件 rewired to sopify_contracts.*
  > runtime/models.py 已删除 (-50 LOC): 仓库零消费者
  > C1+C2 合计: 22 个文件 rewired, 740 tests pass, 纯 import rewire, 零行为变更
- [x] 4.10d Step B: mainline-only slimming — 非主链功能层删除 ✅ 完成 (2026-05-23)
  > 目标切换: 从 contract-preserving slimming 切到 mainline-only slimming
  > 明确接受退化: fail-close validator / context-checkpoint / future-boundary / observability
  > 2026-05-23 文档收口: canonical 主链改为 `gate → current_* machine truth → handoff → host consume rule`；
  > clarification/decision checkpoint 为分叉，不是每轮必经主干。后续删除以 keep-list 为准，不再以 runtime 文件完整性为目标。
  >
  > **Wave 1 — 非主链功能模块删除 (-2,708 LOC runtime)**:
  > - 删除 9 个 runtime 模块: message_templates(265), context_builder(112), context_v1_scope(329),
  >   resolution_planner(216), sidecar_classifier_boundary(205), vnext_phase_boundary(210),
  >   action_projection(249), develop_quality(403), failure_recovery(719)
  > - handoff.py: 删除 boundary artifact 构建/develop_quality/action_projection/tradeoff_signal + observability fallback
  > - decision_tables.py: 去除 context_v1_scope + failure_recovery validator hooks
  > - handoff.py: 移除 CHECKPOINT_REASON_MISSING_BUT_TRADEOFF_DETECTED 无用 import
  > - decision_policy.py: 原计划删除后恢复——主链测试证明 decision checkpoint 依赖它
  > - 删除 5 个测试文件: test_context_v1_scope, test_contract_consistency, test_runtime_failure_recovery,
  >   test_runtime_message_templates, test_runtime_sample_invariant_gate
  >
  > **Wave 2 — develop_callback 彻底退役 (-601 LOC runtime, -82 LOC script)**:
  > - 删除 runtime/develop_callback.py + scripts/develop_callback_runtime.py
  > - engine.py: is_develop_callback_state/develop_resume_after 改为 fail-close（非静默 stub）
  > - manifest.py: 清除 develop_callback/develop_quality/develop_resume 全部声明
  > - installer/{runtime_bundle,bootstrap_workspace,validate,payload}.py: 清除 develop_callback 引用
  > - scripts/sync-runtime-assets.sh: 清除 develop_callback 条目
  > - blueprint/protocol.md: continue_host_develop 条目标注 develop_callback 已退役
  > - blueprint/design.md: Develop callback 章节标注已退役
  > - tests/runtime_test_support.py: 清除 develop_callback + decision_bridge 导入
  >
  > **Wave 3 — CLI bridge / orchestration 外围删除 (-1,952 LOC runtime, -3 scripts)**:
  > - 删除 4 个 runtime 模块: decision_bridge(864), clarification_bridge(403),
  >   cli_interactive(412), plan_orchestrator(273)
  > - 删除 3 个 scripts: clarification_bridge_runtime, decision_bridge_runtime, go_plan_runtime
  > - manifest.py: 清除 decision_bridge/clarification_bridge/planning_mode_orchestrator 声明
  > - installer/runtime_bundle.py: 清除 bridge 必需路径
  > - scripts/sync-runtime-assets.sh: 清除 bridge/orchestrator 条目
  > - blueprint/protocol.md: Helper 索引清除已删 scripts
  > - tests/runtime_test_support.py: 清除 clarification_bridge + plan_orchestrator 导入
  >
  > **主链测试**: 112 passed (gate/router/execution_gate)
  > **累计删减**: ~5,261 LOC runtime + 3 scripts + 5 test files
  > **已知遗留声明**: runtime/contracts/decision_tables.yaml 仍引用 failure_recovery_table/host_message_templates/action_projection；
  >   tests/pytest_entries/fail_close_contract_entry.py 仍 import failure_recovery（import 会断）
  > **接受退化**: 非主链测试可能 fail，后续不救
- [x] 4.11 kernel 验证：确认 gate → route → handoff → checkpoint 链路在 kernel-only 模式下可用
  > **coverage audit** ✅ 完成 (2026-05-23):
  > - gate.py / router.py / checkpoint_request.py / checkpoint_materializer.py 均有直接 contract/integration 覆盖
  > - end-to-end 真实链路存在：`test_runtime_engine.py` 中有 6+ integration tests 通过 `run_runtime()` 走完 gate → _kernel_turn → route → handoff → checkpoint
  > - 结论: 对 C1 (`from .models` → `from sopify_contracts.*`) 机械 rewire，无需先补测试；现有测试足以捕获 import 断裂
  >
  > **直测完成** (2026-05-26):
  > - `tests/test_runtime_kernel_turn.py`: 5 cases 直接调 `execute_kernel_turn()`
  >   1. plan_only 主链 → handoff
  >   2. active develop state planning 复用 existing plan + continue_host_develop handoff
  >   3. decision_resume 经 kernel seam 正常分发
  >   4. state_conflict inspect 严格只读（store 不变, last_route 不写）
  >   5. state_conflict abort tombstone 语义（plan/run 存活, stage 不变）
  > - 全量 631 passed, 49 subtests passed
- [x] 4.12 post-cutover naming/comment polish ✅ 完成
  > **命名决策**: `runtime/_kernel_turn.py` → `runtime/_orchestration.py`
  > - 保留下划线 internal 语义（external 进入点仍为 gate.py）
  > - `execute_kernel_turn()` 函数名保留不改，不扩大变更面
  > - 不留 `_kernel_turn.py` 兼容 shim — 内部模块不承诺 import 稳定性
  > - 理由：orchestration 是稳态职责描述，kernel_turn 带迁移过程味道
  >
  > **docstring/comment polish**:
  > - `_orchestration.py` 模块 docstring 重写（去迁移语言，写稳态描述）
  > - `_derived_resolution_id()` 加 docstring（优先级链说明）
  > - `_result_state_store_for_route()` 加 docstring（store 选择逻辑说明）
  > - `engine.py` 模块 docstring 更正（"Top-level orchestration" → legacy wrapper）
  > - `run_runtime()` deprecation docstring 修正（去 "will be removed in Package A"）
  > - `state.py` / `context_snapshot.py` 注释同步更新
  >
  > **import 更新**: gate.py, cli.py, engine.py (3 处), test_runtime_orchestration.py (1 处)
  > **测试**: 全量 631 passed, 49 subtests passed — 0 行为变更

## 5. 文档更新 (⚠️ 部分完成 — 剩余项见"后续路线"节)
- [x] 5.1 按审计结果决定是否需要回写 `blueprint/tasks.md`
  > 已回写：Runtime retirement cutover 进度、测试基线 743→619
- [x] 5.2 若形成稳定边界变化，再同步 `blueprint/design.md` 或 `project.md`
  > 已回写 `blueprint/design.md` / `blueprint/protocol.md`：冻结 mainline-only keep-list，明确 checkpoint 是主链分叉而非每轮必经主干
- [x] 5.3 若维护者决定弃养 legacy deep runtime 路径，把该决策显式回写到长期文档而不是只留在临时审计结论
  > 已明确后续 slimming 口径：保 gate + machine truth + handoff + host consume rule，其余 runtime 内围能力默认可删/可内联
- [x] 5.4 `deferred` 语义统一 ✅ 完成 — docs tightening，不升格为 registry 状态
  > **决策**: "deferred" 保持文档层面术语，不进入 registry/runtime 作为正式状态/枚举值。
  > **理由**: runtime 代码中无 `deferred` 作为正式状态（唯一出现是 `_orchestration.py:390` 自然英语注释）。
  > 现有 3 处使用各自合理，不需要统一：
  > - `protocol.md:188,205,373` — RFC 风格 "wire format 未定义"，标准用法
  > - `blueprint/tasks.md:121` — "Registry 状态：active + governance deferred"，治理语境
  > - `ADR/README.md:26` — ADR-008 "deferred / scoped"，ADR 状态标签
  > **不做**: 不改 registry parser/schema/test expectation，不新增 deferred 枚举
- [x] 5.5 对齐 user-facing docs ✅ 完成 — B-lite 最小修正
  > grep 审计发现 README.md / README.zh-CN.md / examples/ 已无过时引用。
  > 唯一 stale：CONTRIBUTING.md:47 硬编码 `.sopify-runtime/scripts/runtime_gate.py enter` 作为 first host hop。
  > 修正：对齐 CN 版表述 — "走 selected bundle 的 `runtime_gate_entry`，仅 repo-local 开发态直接调用 `scripts/runtime_gate.py enter`"。
  > CONTRIBUTING_CN.md 已准确，无需改动。
- [x] 5.6 文档验收 ✅ grep 通过
  > 9 个关键词全 repo 扫描：`_kernel_turn` / `engine.run_runtime` / `decision_bridge` / `develop_callback` /
  > `go_plan_helper` / `plan_orchestrator` / `.sopify-runtime/manifest.json` / `sopify_runtime_entry` / `check-runtime-smoke.sh`
  > 结论：历史文档保留原引用（是记录不是活跃约束）；合法 consumer 不改；user-facing docs 仅 CONTRIBUTING.md 一处已修正。
- [x] 5.7 完成后归档审计结论或继续拆下一实施包
  > 决策：本包继续承接剩余工作 (4.10b/4.11/4.12/4.13 Phase B/5.4/5.5/5.6)，不拆新包

## 6. contract 面清理 + engine 重构 ✅ (原"下一轮收缩"，已全部完成)

> 进入条件: 5427520 (mainline-only control plane) 已提交
> 口径: 上一轮删的是代码/模块；这一轮清的是 legacy data contract + 边缘能力 contract + 结构重构

- [x] 6.1 **decision_tables legacy contract 清除** (难度: 中偏高) — ✅ 已执行: 全删
  > 执行结果: decision_tables.py (1,602 LOC) + runtime/contracts/ 整组 (928 LOC) + test_runtime_decision_tables.py + 2 fixtures 全删 = **-3,543 LOC**
  > decision_templates.py (164 LOC) 确认保留 — 被 decision.py:13 消费，与 decision_tables 完全独立
  > 同步清理: test_action_intent.py (删 3 个 decision-table 测试类)、check-context-checkpoints.py (checkpoint A scope/files 裁剪)
  > 额外修复: test_context_checkpoints.py + test_release_hooks.py 3 个 pre-existing failures (commit 5427520 遗留的 resolution_planner/context_v1_scope 引用断裂)
  > 验证: 281 tests pass (含 action_intent/context_checkpoints/release_hooks 扩展验证)
- [x] 6.2 **router ingress / checkpoint reply 协议拆分** (难度: 中) ✅ 2026-05-24
  > 目标: 把 router 的主请求入口协议与 checkpoint 回复协议拆开，结束两类语义长期混跑
  > ingress 终态: 普通 host request 优先只吃 ActionProposal，不再依赖 `_CONTINUE_KEYWORDS` / `_CANCEL_KEYWORDS` 这类自由文本猜测
  > checkpoint 终态: clarification / decision 继续保留轻量自然语言回复解析，只负责 `继续` / `取消` / `choose` / answer 这类 checkpoint reply
  > 直接收益: router 从"富文本分类器"收敛成"主入口控制层 + checkpoint 回复层"两块，后续才能继续清 candidate_skill_ids 链和宿主面遗留 skill contract
  > 联动面: router.py / gate.py / _kernel_turn.py / action_intent.py / clarification.py / decision.py / handoff.py + 对应 tests
  > engine 关联: 顺手收掉 engine ingress 薄层（`_derive_route_from_authorized_proposal`），不扩散到 planning / checkpoint resume 主块
  > kernel extraction 遗留债: `_make_run_id` / `_make_run_state` / `_snapshot_has_global_execution_truth` 目前在 engine.py 与 _kernel_turn.py 双份；本题开始前先消重，避免后续双边修改分叉
  > 边界: 本题不顺手重做 decision/clarification capability，只拆协议边界；普通主请求与 checkpoint reply 的 contract 要分别写清
  > **6.2 结果备注 (技术债标记)**:
  > - confirmed decision 双路径语义: caller gate (router.py:270) 放 confirmed 进 _classify_pending_decision，但内部 pending/collecting 自动恢复路径和 confirmed 的 materialize 路径是两条隐含语义，无显式注释。6.6 拆 _handle_decision_resume 时必须识别。
  > - _enter_active_develop_context 白盒化: 原端到端 run_runtime("继续") 改为手工拼 RunState + RuntimeHandoff + stamp_handoff_resolution_id。不再覆盖 resume → develop_pending → handoff 端到端路径。测试形态债，不阻塞 6.3-6.5。
  > - exec_plan → handoff 缺口: exec_plan route 不产生 RuntimeHandoff（result.handoff is None），3 个测试删掉了 handoff 断言。预存问题，deferred to 6.6。
  > - router-side derive focused test: ✅ 已补 6 个正向测试 (DeriveRouteTests in test_runtime_router.py)，覆盖 cancel_flow session/global scope + checkpoint_response pending/terminal/empty。
- [x] 6.3 **recommended_skill_ids contract 裁定** (难度: 低，纯决策) ✅ 裁定完成
  > **裁定结果: C1 — 删除 recommended_skill_ids + 改 protocol**
  > 关键证据:
  > - 宿主文档（COPILOT.md、full.md、lightweight.md）接续逻辑 100% 靠 required_host_action，零处消费 recommended_skill_ids
  > - runtime 内部 recommended_skill_ids 只透传不做决策
  > - protocol.md:410 已同步修改：宿主接续依据收口为 required_host_action + artifacts + machine truth
  > 对 6.4 的指令:
  > - 删 RuntimeHandoff.recommended_skill_ids 字段
  > - 删 skill_registry.py / skill_resolver.py / skill_schema.py
  > - candidate_skill_ids 保留为内部字段（checkpoint materializer 恢复链需要），不再往宿主面扩散
- [x] 6.4 **skill discovery 退场 + recommended_skill_ids 删除** (已完成)
  > 删除范围:
  > - skill_registry.py (255) + skill_resolver.py (111) = ~366 LOC 删除
  > - skill_schema.py (140) 保留：generate-builtin-catalog.py (CI/preflight 依赖) 仍需要 normalize_skill_manifest
  > - RuntimeHandoff.recommended_skill_ids 字段删除（sopify_contracts/handoff.py）
  > - handoff.py:143 的 recommended_skill_ids 透传删除
  > - _kernel_turn.py:151 / engine.py:537 的 recommended_skill_ids 搬运删除
  > - protocol.md:410 宿主接续依据改写
  > - tests/fixtures/p4d_smoke/current_handoff.json 删除 recommended_skill_ids 字段
  > 保留范围:
  > - builtin_catalog.py (267 LOC) 被 manifest.py:12 直接依赖，不可随 skill_registry 一起删
  > - candidate_skill_ids 保留为内部字段（checkpoint materializer 恢复链需要）
  > - Router/derive 里的 candidate_skill_ids 改为硬编码静态 tuple（已经事实静态化，只去掉 resolve 调用壳）
  > SkillRegistry.discover() 调用点退场: router.py / _kernel_turn.py / engine.py / tests
  > 不在本题处理: host bare-text ingress fallback、authorized ActionProposal complexity heuristic（modify_files / propose_plan 仍经 estimate_complexity() 落 quick_fix / light_iterate / workflow + plan_level）
  > 明确保留: checkpoint local reply grammar / checkpoint reply NLP（clarification / decision / state_conflict）
  > 事实债记录: 当前仍存在两层猜测
  > - host bare-text ingress 仍依赖 _ACTION_KEYWORDS / _ARCHITECTURE_KEYWORDS + estimate_complexity()
  > - authorized ActionProposal derive 仍依赖同一套 complexity heuristic
  > 上述两层待单独题处理；代码收口前不得先改协议宣称其已退役
- [x] 6.5 **plan_registry 结构重构审计** (已完成)
  > 范围: plan_registry.py (1,013 LOC) + plan_scaffold.py (464 LOC)
  > 裁定: plan_registry 作为独立治理层保留; YAML 写入 helper 迁出到 `_yaml.py`
  > plan_scaffold.py: 6.6 之前 blocked by engine.py; **6.6b 之后消费者变为 `_planning.py`**（`_advance_planning_route → create_plan_scaffold`），不再被 engine.py 直接消费
  > 消费者 (6.6 后): _planning.py (create_plan_scaffold) + archive_lifecycle.py + output.py
  > 后续: plan_scaffold 保留独立模块，但需按主链单职责口径继续瘦身
- [x] 6.6 **engine decomposition** (已完成)
  > 终态:
  > - `_planning.py` (1496 LOC): planning 主链 + resume + gate checkpoint + execution-resume
  > - `engine.py` (343 LOC): conflict/cancel + activation + archive + run_runtime wrapper
  > - `_kernel_turn.py` (783 LOC): 纯编排 — store/promotion/receipt/handoff
  > - import 面: _planning×7 + engine×5 = 12 (原 engine×9 + 7 隐藏重复 = 16)
  >
  > 分步:
  > - 6.6a: 删 engine.py 10 个 A1-era 死代码函数 (−219 LOC)
  > - 6.6b: planning pipeline → _planning.py + 消除 7 双份 helper + resolve_execution_resume 下沉
  >
  > owner map:
  > - _kernel_turn: store resolution, promotion, handoff ownership, result store selection, 总编排
  > - _planning: planning 主链, clarification/decision resume, execution-resume gate mutation
  > - engine: conflict/cancel, activation, archive, run_runtime deprecated wrapper

## 后续路线 — 未完成项汇总

> 以下按建议执行顺序排列。编号保留原文引用以便追溯。

### Tier 1: 收口与阻塞解除

| 编号 | 内容 | 当前状态 | 备注 |
|------|------|----------|------|
| 4.10b | plan_scaffold.py (466 LOC) 处置 | 暂时保留独立模块 | 后续仅做主链单职责瘦身：scaffold creation + artifact return，不承载 planning/gate/state 判断 |
| 4.2 | 删除已批准的 `delete_now` 面 | ✅ 已关 | 4.10d Wave 1-3 + 6.1 + 6.4 全部执行完 |
| 4.3 | co-delete candidate 同步删除 | ✅ 已关 | 同上 |
| 4.4 | 记录删除依据 / 影响 / 验证结果 | ✅ 已关 | tasks.md + commit = 记录 |
| 4.5 | 标记 legacy/blocking 面后续处理 | ✅ A2 表已刷新至 6.6 后现实 | |

### Tier 2: Installer 瘦身 (4.13, 新立项)

> **产品前提**: 项目级安装保留。瘦身方向不是删安装链，而是收过渡态为正式实现。
>
> **Phase A — ✅ 全部完成**:
> - ✅ 4.13-A: 停写 legacy workspace stub (.sopify-runtime/manifest.json)，收敛到单 marker (.sopify-skills/sopify.json) + stub 合同对齐 + 文档同步
> - ✅ 4.13-B: sync-runtime-assets.sh 壳套壳重写为纯 Python (installer/runtime_bundle.py shutil.copytree + write_bundle_manifest) + bundle contract 测试对齐 + bash 脚本删除
>
> **Phase B — ✅ 完成（smoke 稳态化 + legacy_fallback 判定）**:
> - ✅ check-runtime-smoke.sh: 删除 2 条 legacy 反向断言（wiki overview / history index 不存在检查 — 4.13-A 已收口），其余 ~28 条稳态 contract 保留。脚本保留不删（6 处 bundle/installer 活跃 consumer）
> - ✅ check-prompt-runtime-gate-smoke.py: 6 个场景全部确认为稳态 gate contract，加 stable contract 标注。与 install smoke 一起加入 CI
> - ✅ check-install-payload-bundle-smoke.py: 已是稳态 contract，无需重设计。加入 CI
> - ✅ legacy_fallback 判定: 作为 workspace stub 字段已退役（4.13-A 停写 legacy stub）。`_legacy_payload_bundle_version()` / `_legacy_bundle_manifest_path()` 保留为 versioned layout 兼容路径（bootstrap_workspace.py / validate.py / workspace_preflight.py 共 ~60 LOC），有 hard gate 测试保护，后续随 bundle layout 正式固定后收口
> - 不碰 bootstrap_workspace.py 核心逻辑（1507 LOC 风险隔离）

### Tier 3: 验证与 polish

| 编号 | 内容 | 当前状态 |
|------|------|----------|
| 4.11 | kernel 验证 (gate→route→handoff→checkpoint) | ✅ 完成 — `test_runtime_orchestration.py` (5 cases) |
| 4.12 | naming/comment polish | ✅ 完成 — `_kernel_turn.py` → `_orchestration.py` + docstring polish |

### Tier 4: 文档更新

| 编号 | 内容 | 当前状态 |
|------|------|----------|
| 5.1 | 回写 `blueprint/tasks.md` | ✅ 已执行 |
| 5.4 | `deferred` 语义统一 | ✅ 完成 — docs tightening，不升格为 registry 状态 |
| 5.5 | user-facing docs 更新 (README / examples) | ✅ 完成 — B-lite: CONTRIBUTING.md host-hop 修正 |
| 5.6 | 文档验收 grep | ✅ 通过 — 9 关键词全扫，仅 1 处已修 |
| 5.7 | 归档审计结论或继续拆下一实施包 | ✅ 决策：本包继续，不拆 |

### 已知技术债 (不在本包范围)

- **bare-text ingress heuristic**: `_ACTION_KEYWORDS` / `estimate_complexity()` 仍在 router.py，待单独题处理
- **run_runtime() wrapper**: engine.py 中 50+ test callers 仍经此入口，未删
- ~~**22 个 pre-existing test failures**: test_runtime_engine.py 中 develop_callback / bundle / go_plan_helper / plan_orchestrator 相关~~ → **已清理** (4.13-B: 34 退役测试块删除)
- **discovered_skills 空 tuple**: RuntimeResult 字段保留，值始终为空
- **shell 层退场 (manifest / output / workspace_preflight)**: 属独立工作流，不在本包

