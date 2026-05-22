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

## 1. 蓝图 delta 校验
- [ ] 1.1 确认 `blueprint/design.md` 中与 runtime 删除相关的正式约束仍成立
- [ ] 1.2 以 P4b / P4b.5 / P5 / P6 为既有基线，只列出本次审计新增的 delta，不重复复述已裁定结论
- [ ] 1.3 明确本次审计命中的蓝图分层、非目标与不重复范围
- [ ] 1.4 引用 `design.md` L727 前提，明确“当前存在消费者”不等于“维护者必须继续保留该路径”
- [ ] 1.5 把 `deferred` 生命周期语义冲突记为副发现，暂不先改 registry contract

## 2. 当前消费者扫描
- [ ] 2.1 扫描 `installer/`、`scripts/`、`tests/`、宿主接入路径对 `runtime/*` 的直接 import / 调用
- [ ] 2.2 区分 `sopify_contracts` / `canonical_writer` 已覆盖能力与仍留在 `runtime` 的生产职责
- [ ] 2.3 形成 `extract-to-kernel` / `delete_now` / `keep_for_legacy_runtime` / `blocking_full_retirement` 四类清单
- [ ] 2.4 对每个 consumer 标记 `must_keep` / `keep_if_preserving_legacy` / `co-delete_candidate`
- [ ] 2.5 补充 `plan_registry.py` 对 `deferred` 的实际 reconcile 行为，判断其属于本主题的哪个 consumer / contract 边界

## 3. 删除就绪结论
- [ ] 3.1 产出文件级删除候选表，明确每个候选的依据和风险
- [ ] 3.2 分别产出“保留 legacy 路径”与“目标态优先、允许同步退场”两种口径下的阻塞表
- [ ] 3.3 给出推荐策略、删除准入范围与后续实施切片建议
- [ ] 3.4 明确 `target-state-first` 下退场后的保留面清单（双栏）：
  - **retain-as-is**：`sopify_contracts/`、`canonical_writer/`、`.sopify-skills/` — 无 runtime 代码依赖，可直接保留
  - **retain-after-decoupling**：`installer/validate.py`、`installer/bootstrap_workspace.py`、`installer/inspection.py`、`scripts/install_sopify.py`、`scripts/sopify_init.py` — 当前仍有 runtime import / bundle 验证硬依赖，需先解耦再保留
- [ ] 3.5 明确退场量级修正：`runtime/` ~23.8K + runtime-coupled scripts ~4K + runtime-coupled tests ~15.3K ≈ **43K LOC**
- [ ] 3.6 产出 retain-after-decoupling 五文件 cutover 表：列出当前耦合、替代依据（payload-only / `sopify.json` / canonical state）、保留后的行为边界
- [ ] 3.7 明确 `installer/runtime_bundle.py` 为 pure legacy surface，归入 Step 3 同步退场而不是 Step 2 解耦保留
- [ ] 3.8 记录 Step 2 固定执行顺序：`installer/inspection.py` → `scripts/sopify_init.py` → `installer/validate.py` → `installer/bootstrap_workspace.py` → `scripts/install_sopify.py`
- [ ] 3.9 确认 orchestration kernel extraction 作为本包内执行目标，不另开独立方案包
- [ ] 3.10 定义 orchestration kernel 最小模块边界：确定 gate / route / handoff / checkpoint 各由哪些 `runtime/*.py` 承载
- [ ] 3.11 确认 kernel 与 `sopify_contracts` / `canonical_writer` 的接口约定，确保 kernel 不反向依赖 runtime 其余面
- [ ] 3.12 列出 kernel 需要保留的最小测试覆盖面

## 4. 审计后删除
- [x] 4.1 维护者已在 **2026-05-22** 确认采用 `target-state-first` 口径，并锁定本包后续删除范围以“先解耦保留面，再同步退场 runtime + legacy deep path”为准
- [ ] 4.2 删除所有已批准的 `delete_now` 面（不含 kernel 保留模块）
- [ ] 4.3 若采用 `target-state-first`，同步删除已批准的 `co-delete candidate` 及其对应 legacy consumer（不含 kernel 保留模块）
- [ ] 4.4 记录每个删除项的依据、影响范围与验证结果
- [ ] 4.5 明确哪些 `keep_for_legacy_runtime` / `blocking_full_retirement` 面留待后续包处理
- [ ] 4.6 若采用 `target-state-first`，显式确认以下同步退场范围（不限于 `*_runtime.py`）：
  - legacy `scripts/*_runtime.py` 全组退场：`clarification_bridge_runtime.py`、`decision_bridge_runtime.py`、`preferences_preload_runtime.py`、`plan_registry_runtime.py`、`develop_callback_runtime.py`
  - `scripts/runtime_gate.py`、`scripts/sopify_runtime.py`、`scripts/go_plan_runtime.py` 不作为 legacy surface 原样保留；若 S3 审计确认 kernel 仍需 host-facing 最小链路，则新增全新薄壳入口替代，名称与数量以最小够用为准
  - `scripts/check-runtime-smoke.sh`、`scripts/sync-runtime-assets.sh`
  - `scripts/check-prompt-runtime-gate-smoke.py`、`scripts/check-install-payload-bundle-smoke.py`（按审计结果判定）
  - `scripts/check-host-doc-contract.py`（按 runtime 依赖程度判定）
  - `tests/test_runtime_*`、`tests/runtime_test_support.py`、`tests/test_bundle_smoke.py`（按 runtime import 判定）
  - `installer/runtime_bundle.py`（pure legacy runtime bundle sync surface，直接退场）
- [ ] 4.7 对 retain-after-decoupling 五文件（`installer/validate.py`、`installer/bootstrap_workspace.py`、`installer/inspection.py`、`scripts/install_sopify.py`、`scripts/sopify_init.py`），在删除 runtime 前同步去除 runtime import 和 bundle 硬依赖，确保安装链路可用
- [ ] 4.8 `scripts/sopify_status.py` / `scripts/sopify_doctor.py` 不单列 cutover；仅验证其通过 `installer/inspection.py` 的改造继续可用
- [ ] 4.9 Step 2 具体落地顺序按 `inspection.py` 优先执行，避免 Step 3 删除 runtime 后 `status` / `doctor` 先发生 import failure
- [ ] 4.10 提取 orchestration kernel：在 `runtime/` 原地瘦身，清理 non-kernel 依赖，确保 kernel 可独立运行（不新建并行目录）
- [ ] 4.10a 若 S3 审计确认 kernel 仍需宿主入口，仅新增最小数量的全新薄壳脚本：只负责参数解析、调用 kernel、读写冻结 contract；不得复用 legacy bridge / renderer / preload / bundle 逻辑
- [ ] 4.11 kernel 验证：确认 gate → route → handoff → checkpoint 链路在 kernel-only 模式下可用

## 5. 文档更新
- [ ] 5.1 按审计结果决定是否需要回写 `blueprint/tasks.md`
- [ ] 5.2 若形成稳定边界变化，再同步 `blueprint/design.md` 或 `project.md`
- [ ] 5.3 若维护者决定弃养 legacy deep runtime 路径，把该决策显式回写到长期文档而不是只留在临时审计结论
- [ ] 5.4 若 `deferred` 语义需要统一，单列为后续 contract 决策项，不在本审计中顺手修补
- [ ] 5.5 对齐 user-facing docs/examples：更新 `README.md`、`examples/external-repo-quickstart/README.md`、`examples/external-repo-quickstart/sopify.json.example`，移除或改写因 runtime slimming 失实的安装目标、能力矩阵、目录树、bootstrap 叙述、`runtime_gate` 描述。不做产品定位刷新或营销文案重写
- [ ] 5.6 文档验收：grep 验证 user-facing docs 不再宣称已删除的 runtime surface / deep runtime path / runtime bundle smoke
- [ ] 5.7 完成后归档审计结论或继续拆下一实施包
