---
plan_id: 20260522_runtime_slimming_kernel_extraction
feature_key: runtime_slimming_kernel_extraction
level: standard
lifecycle_state: active
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: false
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

## 4. 审计后删除
- [x] 4.1 维护者已在 **2026-05-22** 确认采用 `target-state-first` 口径，并锁定本包后续删除范围以“先解耦保留面，再同步退场 runtime + legacy deep path”为准
- [ ] 4.2 删除所有已批准的 `delete_now` 面（不含 kernel 保留模块）
- [ ] 4.3 若采用 `target-state-first`，同步删除已批准的 `co-delete candidate` 及其对应 legacy consumer（不含 kernel 保留模块）
- [ ] 4.4 记录每个删除项的依据、影响范围与验证结果
- [ ] 4.5 明确哪些 `keep_for_legacy_runtime` / `blocking_full_retirement` 面留待后续包处理
- [ ] 4.6 若采用 `target-state-first`，显式确认以下同步退场范围（不限于 `*_runtime.py`）：
  - legacy `scripts/*_runtime.py` bridge/helper 退场：`clarification_bridge_runtime.py`、`decision_bridge_runtime.py`、`preferences_preload_runtime.py`、`plan_registry_runtime.py`
  - 以下入口脚本 in-place cutover（路径名被 manifest/test 冻结 → 原地重写内容，不新建并行文件）：
    - `scripts/runtime_gate.py` → in-place cutover: 原地重写为 thin shell (argparse → kernel → exit code)
    - `scripts/sopify_runtime.py` → in-place cutover: guard/receipt 逻辑上移到内核，原地重写为 thin shell
    - `scripts/develop_callback_runtime.py` → in-place cutover: 原地重写为 thin shell
    - `scripts/go_plan_runtime.py` → 产品决策: 路径名被 manifest 冻结，若删除需同步改 manifest/test/doc
  - `scripts/check-runtime-smoke.sh`、`scripts/sync-runtime-assets.sh`
  - `scripts/check-prompt-runtime-gate-smoke.py` — co-delete: runtime smoke 脚本
  - `scripts/check-install-payload-bundle-smoke.py` — cutover (release 联动): L159 冻结入口路径，改写路径期望值
  - `scripts/check-skill-eval-gate.py` — cutover: 改为 kernel 接口或删除
  - `scripts/generate-builtin-catalog.py` — cutover: 改为 sopify_contracts 或删除
  - `scripts/release-preflight.sh` — cutover: 移除或改写 runtime smoke 调用
  - `scripts/check-host-doc-contract.py`（按 runtime 依赖程度判定）
  - `tests/test_runtime_*`、`tests/runtime_test_support.py`、`tests/test_bundle_smoke.py`（按 runtime import 判定）
  - `installer/runtime_bundle.py`（pure legacy runtime bundle sync surface，直接退场）
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
- [ ] 4.10b **Step 3 Package A: 批量删除 + kernel helpers 内联**
  > 范围: (1) 批量删除 ~40 非内核模块 (~18.8K LOC); (2) 将 18 个 kernel helpers 从 engine.py 内联到 _kernel_turn.py; (3) 删除 11 个 non-kernel route handler import 及对应调用点; (4) 删除 engine.py; (5) 清理 models.py bridge 消费者
- [ ] 4.10c Step 3 Package C: models.py bridge 退场
  > 范围: (1) 删除 runtime/models.py; (2) tests 从 runtime.models → sopify_contracts; (3) manifest/protocol 表面收缩
- [ ] 4.11 kernel 验证：确认 gate → route → handoff → checkpoint 链路在 kernel-only 模式下可用

## 5. 文档更新
- [ ] 5.1 按审计结果决定是否需要回写 `blueprint/tasks.md`
- [ ] 5.2 若形成稳定边界变化，再同步 `blueprint/design.md` 或 `project.md`
- [ ] 5.3 若维护者决定弃养 legacy deep runtime 路径，把该决策显式回写到长期文档而不是只留在临时审计结论
- [ ] 5.4 若 `deferred` 语义需要统一，单列为后续 contract 决策项，不在本审计中顺手修补
- [ ] 5.5 对齐 user-facing docs/examples：更新 `README.md`、`examples/external-repo-quickstart/README.md`、`examples/external-repo-quickstart/sopify.json.example`，移除或改写因 runtime slimming 失实的安装目标、能力矩阵、目录树、bootstrap 叙述、`runtime_gate` 描述。不做产品定位刷新或营销文案重写
- [ ] 5.6 文档验收：grep 验证 user-facing docs 不再宣称已删除的 runtime surface / deep runtime path / runtime bundle smoke
- [ ] 5.7 完成后归档审计结论或继续拆下一实施包
