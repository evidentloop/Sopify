---
plan_id: 20260509_p4b_runtime_surface_consolidation
feature_key: p4b_runtime_surface_consolidation
level: standard
lifecycle_state: completed
knowledge_sync:
  project: skip
  background: skip
  design: update
  tasks: update
archive_ready: false
plan_status: completed
---

# 任务清单: P4b Runtime Surface Consolidation

## 当前阶段目标

runtime/*.py 从 25,534 LOC 削减到 <20,000 LOC。先删后并，不先设计新结构。

**P4b-close 结论**：prove-kept-or-delete 全量扫描后，runtime 在当前 contract 约束下已接近最小可行体积。实际可删死代码仅 15 LOC（已删除）。最终 baseline：24,334 LOC。<20K 目标在不改 distribution/installer contract 的约束下不可达。

## Phase 0: Test Inventory Re-audit + Hard/Soft Gate Matrix

- [x] 0.1 盘点所有 tests/test_*.py 的当前分类标记（contract / implementation-mirror / smoke / distribution）
- [x] 0.2 对每个标为 contract 的测试，验证其保护对象是否在 keep-list / canonical main chain / distribution·install user-facing contract 中；不命中者重标为 implementation-mirror
- [x] 0.3 产出 hard/soft gate matrix：contract + smoke + distribution + eval = hard gate；implementation-mirror = soft gate（advisory）
- [x] 0.4 提交 re-audit 结果，作为 Phase 1 降载的分类依据

## Phase 1: CI / Release-Preflight 真实降载

- [x] 1.1 release-preflight.sh 分层：hard gate (contract + smoke + distribution + eval) vs soft gate (implementation-mirror advisory)
- [x] 1.2 ci.yml test step 降载：将 `python3 -m unittest discover tests -v` 替换为仅跑 hard gate 分类的测试；implementation-mirror 测试降为 advisory step（失败不阻断 CI）
- [x] 1.3 验证 hard gate 通过（contract + smoke + distribution + eval 在当前代码上绿）
- [x] 1.4 验证 implementation-mirror advisory 在当前代码上也绿（基线确认）

## Phase 2: Runtime 旧面删除（prove-kept-or-delete）

方法论：对每个 runtime 文件/函数，验证是否在 keep-list / 主链调用图 / distribution·install user-facing contract 中。三个都不命中 → 默认整段删除。

### Tier 1: 高信心删除 → 全部偏离预期，不可删

- [x] 2.1 decision_bridge.py → **保留**：绑定 distribution anchor（manifest/installer/smoke），超出 P4b scope
- [x] 2.2 clarification_bridge.py → **保留**：同上
- [x] 2.3 workspace_preflight.py → **保留**：vendored fallback 是 bundle 部署生产路径，LEGACY_FALLBACK_SELECTED 有 hard gate 覆盖
- [x] 2.4 plan_orchestrator.py → **保留**：bridge 保留后胶水不可删
- [x] 2.5 Tier 1 完成后跑 pytest，确认主链完整 ✅

### Tier 2: 中信心删除 → 仅 9 LOC 死代码

- [x] 2.6 failure_recovery.py → **0 LOC**：全部在 distribution anchor 上
- [x] 2.7 context_snapshot.py → **0 LOC**：内部调用，改行为有风险
- [x] 2.8 router.py → **9 LOC 已删**：`_contains_intent` (3) + `_runtime_skill` (6) 确认死代码
- [x] 2.9 gate.py → **0 LOC**：`_action_proposal_from_command_alias` 在主路径上
- [x] 2.10 message_templates.py → **0 LOC**：被 scripts 消费
- [x] 2.11 action_intent.py → **0 LOC**：`resolve_action_proposal` 被 gate.py 调用
- [x] 2.12 其他散布 compat 清理 → **0 LOC**：全量扫描无更多死代码
- [x] 2.13 Tier 2 完成后跑 pytest，确认主链完整 ✅ 653 passed

### Tier 3: engine.py 专项 → 仅 6 LOC 死代码

- [x] 2.14 engine.py 全量死函数扫描 → `_phase_for_route` (6 LOC) 确认死代码，**已删**
- [x] 2.15-2.18 engine.py 全量验证完成，无更多可删面
- [x] 2.19 结构性合并评估 → **不适用**：死代码仅 15 LOC，无合并目标

## Phase 3: Implementation-mirror Tests 收口

Phase 2 未删除任何 contract surface，mirror tests 保护对象均仍存在，无需收口。

- [x] 3.1 找出保护对象已不存在的 implementation-mirror tests → **无**（Phase 2 未删面）
- [x] 3.2-3.3 不需要执行
- [x] 3.4 最终 LOC 盘点：runtime/*.py = 24,334 LOC；tests 未变

## 完成标准（修订后）

- [x] prove-kept-or-delete 全量扫描完成，所有 runtime 文件/函数已验证锚点命中
- [x] 确认可删死代码已删（15 LOC）
- [x] pytest hard gate 全绿（653 passed）
- [x] P4a keep-list 内面全部保留
- [x] ActionProposal → Validator → Handoff/Receipt/Archive 主链完整
- [x] 结论文档已写入 design.md
- [ ] ~~runtime/*.py LOC < 20,000~~ → 不可达，原因见 design.md Phase 2 执行结论
