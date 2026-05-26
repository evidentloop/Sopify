# Receipt: Runtime Slimming — Orchestration Kernel Extraction

## 基本信息

| 字段 | 值 |
|------|------|
| Plan ID | 20260522_runtime_slimming_kernel_extraction |
| 状态 | **全部完成** |
| 主分支 PRs | #38, #39, #40, #41, #42, #43 + closeout PR |
| 前置 | P7 Payload-Only Onboarding Mainline ✅ |

---

## 核心结论（一句话）

runtime/ 从 ~22K LOC / 51 文件收至 37 文件 / 16,286 LOC。contract 面清理 −6,400 LOC，34 退役测试块清理 −1,400 LOC，kernel orchestration 提取并重命名为 `_orchestration.py`，`plan_scaffold.py` 拆分为 `runtime/plan/` 包。Phase 2（installer 解耦 + runtime/ 全删）留作后续。

---

## 决策记录

| ID | 决策 | 理由 |
|----|------|------|
| DR-1 | `_kernel_turn.py` → `_orchestration.py`（保留下划线前缀） | 模块为内部实现，underscore 语义一致 |
| DR-2 | `execute_kernel_turn()` 函数名不改 | 50+ test callers 通过 `run_runtime()` wrapper 间接调用，改名成本远超收益 |
| DR-3 | 不删 `check-runtime-smoke.sh` | 被 installer/runtime_bundle.py 打包进 bundle，有 6 处活跃 consumer |
| DR-4 | `deferred` 保持文档层面术语 | 不升格为 registry/runtime 正式状态/枚举值 |
| DR-5 | `legacy_fallback` stub 字段已退役 | `_legacy_payload_bundle_version()` / `_legacy_bundle_manifest_path()` 保留为 versioned layout 兼容路径 |
| DR-6 | 不删 `run_runtime()` wrapper | engine.py 中 50+ test callers 仍经此入口 |

---

## 阶段执行历史

| 阶段 | 摘要 | 状态 |
|------|------|------|
| 1. 蓝图 delta 校验 | 5 项审计全通过 | ✅ |
| 2. 当前消费者扫描 | 4 类清单 + consumer 判定 | ✅ |
| 3. 删除就绪结论 | kernel 边界锁定，退场量级 ~38K LOC | ✅ |
| 4. 审计后删除 | 4.1-4.13B 全部完成 | ✅ |
| 5. 文档更新 | 5.1-5.7 全部完成 | ✅ |
| 6. contract 面清理 + engine 重构 | 6.1-6.6 全部收完，−6,400+ LOC | ✅ |

---

## 主要 PR 清单

| PR | 标题 | 关键变更 |
|----|------|---------|
| #38 | 4.13-B: runtime bundle rewrite + handoff semantic fix + test cleanup | Bundle 纯 Python 重写 + 34 退役测试块删除 |
| #39 | fix: remove workspace stub assertion from repo-local runtime smoke | Smoke 断言修正 |
| #40 | fix: smoke-stub-assertion | Smoke stub 断言修复 |
| #41 | refactor(4.10b): split plan_scaffold.py into runtime/plan/ package | 466 LOC → 5 个模块化文件 |
| #42 | test: add 4.11 kernel turn direct tests | 5 个 `execute_kernel_turn()` 合同测试 |
| #43 | refactor: rename _kernel_turn.py → _orchestration.py + docstring polish | 模块重命名 + 3 处 import 更新 + docstring 完善 |

---

## 测试验证

| 范围 | 结果 |
|------|------|
| 全量回归 | 631 tests passed |
| Smoke (bash) | ✅ check-runtime-smoke.sh |
| Smoke (install) | ✅ check-install-payload-bundle-smoke.py |
| Smoke (prompt gate) | ✅ check-prompt-runtime-gate-smoke.py |

---

## 已知限制

| 限制 | 说明 |
|------|------|
| Phase 2 未启动 | installer 5 文件解耦 + runtime/ 全删 + legacy deep path 退场 |
| `run_runtime()` 未删 | 50+ test callers 仍依赖此 wrapper |
| `discovered_skills` 空 tuple | RuntimeResult 字段保留，值始终为空 |
| bare-text ingress heuristic | `_ACTION_KEYWORDS` / `estimate_complexity()` 仍在 router.py |

---

## Follow-up

| 事项 | 来源 |
|------|------|
| Runtime retirement Phase 2 | blueprint/tasks.md |
| Skill packaging / localization governance | blueprint/tasks.md |
| Post-runtime skeleton governance | blueprint/tasks.md |

---

## 蓝图变更

| 文件 | 变更 |
|------|------|
| `blueprint/README.md` | 当前活动 plan = 暂无；最近归档指向本包 |
| `blueprint/tasks.md` | 新增 Skill packaging + Post-runtime governance 候选 |
