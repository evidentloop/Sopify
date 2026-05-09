---
plan_id: 20260509_p4b_runtime_surface_consolidation
feature_key: p4b_runtime_surface_consolidation
level: standard
lifecycle_state: active
knowledge_sync:
  project: skip
  background: skip
  design: update
  tasks: update
archive_ready: false
plan_status: active
---

# 任务清单: P4b Runtime Surface Consolidation

## 当前阶段目标

runtime/*.py 从 25,534 LOC 削减到 <20,000 LOC。先删后并，不先设计新结构。

## Phase 0: Test Inventory Re-audit + Hard/Soft Gate Matrix

- [ ] 0.1 盘点所有 tests/test_*.py 的当前分类标记（contract / implementation-mirror / smoke / distribution）
- [ ] 0.2 对每个标为 contract 的测试，验证其保护对象是否在 keep-list / canonical main chain / distribution·install user-facing contract 中；不命中者重标为 implementation-mirror
- [ ] 0.3 产出 hard/soft gate matrix：contract + smoke + distribution + eval = hard gate；implementation-mirror = soft gate（advisory）
- [ ] 0.4 提交 re-audit 结果，作为 Phase 1 降载的分类依据

## Phase 1: CI / Release-Preflight 真实降载

- [ ] 1.1 release-preflight.sh 分层：hard gate (contract + smoke + distribution + eval) vs soft gate (implementation-mirror advisory)
- [ ] 1.2 ci.yml test step 降载：将 `python3 -m unittest discover tests -v` 替换为仅跑 hard gate 分类的测试；implementation-mirror 测试降为 advisory step（失败不阻断 CI）
- [ ] 1.3 验证 hard gate 通过（contract + smoke + distribution + eval 在当前代码上绿）
- [ ] 1.4 验证 implementation-mirror advisory 在当前代码上也绿（基线确认）

## Phase 2: Runtime 旧面删除（prove-kept-or-delete）

方法论：对每个 runtime 文件/函数，验证是否在 keep-list / 主链调用图 / distribution·install user-facing contract 中。三个都不命中 → 默认整段删除。

### Tier 1: 高信心删除

- [ ] 2.1 decision_bridge.py 裁剪或删除（~180–220 LOC）
- [ ] 2.2 clarification_bridge.py 裁剪或删除（~140–180 LOC）
- [ ] 2.3 workspace_preflight.py legacy/fallback 段删除（~220–320 LOC）
- [ ] 2.4 plan_orchestrator.py bridge 胶水裁剪（~120–180 LOC）
- [ ] 2.5 Tier 1 完成后跑 pytest，确认主链完整

### Tier 2: 中信心删除

- [ ] 2.6 failure_recovery.py legacy 恢复路径裁剪（~250–400 LOC）
- [ ] 2.7 context_snapshot.py compat 字段删除（~50–80 LOC）
- [ ] 2.8 router.py 旧分支分类裁剪（~40–80 LOC）
- [ ] 2.9 gate.py 仅裁剪 legacy wrapper/fallback（~15–30 LOC）；action_proposal_retry 主路径在 keep-list，不可删
- [ ] 2.10 message_templates.py 模板精简（~20–60 LOC）
- [ ] 2.11 action_intent.py fallback 裁剪（~20–40 LOC）
- [ ] 2.12 其他散布 compat 清理（~100–200 LOC）
- [ ] 2.13 Tier 2 完成后跑 pytest，确认主链完整

### Tier 3: engine.py 专项

- [ ] 2.14 engine.py 调用图审查（Tier 1+2 删除后，找残留调用）
- [ ] 2.15 engine.py 旧 route 处理函数裁剪
- [ ] 2.16 engine.py checkpoint 编排段裁剪（被裁 checkpoint type 相关）
- [ ] 2.17 engine.py compat/bridge 胶水清理
- [ ] 2.18 Tier 3 完成后跑 pytest + LOC 盘点
- [ ] 2.19 评估是否有结构性合并价值（非 LOC 驱动）；如纯删后仍 >20K，优先继续发现可删语义死面，不做格式性压缩

## Phase 3: Implementation-mirror Tests 收口（依赖 Phase 0 re-audit）

- [ ] 3.1 找出保护对象已不存在的 implementation-mirror tests（Phase 0 已完成重标）
- [ ] 3.2 删除对应测试代码
- [ ] 3.3 最终 pytest 全绿确认
- [ ] 3.4 最终 LOC 盘点（runtime/*.py + tests/*.py）

## 完成标准

- [ ] runtime/*.py LOC < 20,000
- [ ] pytest 全绿
- [ ] P4a keep-list 内面全部保留
- [ ] ActionProposal → Validator → Handoff/Receipt/Archive 主链完整
- [ ] 削减预算表的 target/hard max 未被突破
