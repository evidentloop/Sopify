---
plan_id: 20260508_p3b_perimeter_cleanup
feature_key: p3b_perimeter_cleanup
level: standard
lifecycle_state: active
knowledge_sync:
  project: aligned
  background: aligned
  design: aligned
  tasks: aligned
archive_ready: false
---

# 任务清单: P3b Perimeter Cleanup

## 当前阶段目标

以 P3a 完成为前提。清理外围面，为 P4 系列减重扫清障碍。1 个方案包，4 个内部切片。

## S1: Release Gate + Evals 卫生

- [x] 1.1 `release-preflight.sh`：从 `unittest discover` 改为 `pytest`
- [x] 1.2 `evals/skill_eval_report.json` 加入 `.gitignore`；baseline 和 SLO 文件保留
- [x] 1.3 验证：`bash scripts/release-preflight.sh` 正常退出
- [x] 1.4 (补) CONTRIBUTING.md / CONTRIBUTING_CN.md / scripts/sync-runtime-assets.sh 中 unittest discover 统一为 pytest

## S2: Replay 下线 + 旧概念清理 + Runtime 外围残留

### replay 能力下线

- [x] 2.1 删除 `.sopify-skills/replay/` 目录数据
- [x] 2.2 删除 `runtime/replay.py`（整文件）
- [x] 2.3 移除 `runtime/engine.py` 中 replay 事件发射（含 L1704-1705 skill 映射分支）
- [x] 2.4 移除 `runtime/develop_callback.py` 中 replay 记录
- [x] 2.5 移除 `runtime/handoff.py` 中 `replay_session_dir` 附件（约 L347-348）
- [x] 2.6 移除 `runtime/output.py` 中 replay 展示
- [x] 2.7 `runtime/builtin_catalog.py`：删除 workflow-learning skill entry（L92-101）
- [x] 2.8 删除 `runtime/builtin_skill_packages/workflow-learning/skill.yaml`
- [x] 2.9 更新 `runtime/builtin_catalog.generated.json`：移除 workflow-learning 条目（L196-201 及相关 replay 引用）
- [x] 2.10 移除 `runtime/router.py` 中 replay route 分支（L290-296）
- [x] 2.11 清 README / README.zh-CN.md / docs 中对 replay 和 workflow-learning 的引用

### 旧概念清理（P3a 已 sunset surface 残留）

- [x] 2.12 tests 中验证 P3a 已 sunset surface 的断言——更新或删除
- [ ] 2.13 prompt 中引用已 sunset contract 的段落——清除（prompt asset 本体含 replay 字面量，待 prompt asset 整体更新时处理）
- [x] 2.14 handoff/output 旧兼容投影——清除
- [x] 2.15 reason phrasing / phase label 特判——清除

### replay / workflow-learning 测试引用清理

- [x] 2.16 `tests/test_runtime_router.py`：replay route 测试（L152-158, L617-651）——删除
- [x] 2.17 `tests/test_runtime_decision.py`：`replay_session_dir=None` 引用（L604）——清除
- [x] 2.18 `tests/test_runtime_sample_invariant_gate.py`：replay_required 相关断言（L92-107）——清除
- [x] 2.19 `tests/test_runtime_skill_registry.py`：workflow-learning assertIn（L61）——删除
- [x] 2.20 `tests/test_installer.py`：replay 相关引用（L895）——已清除 gitignore 断言；L1301/L1354 footer 断言保留（prompt asset 未更新，注释标注）
- [ ] 2.21 清理 tests/__pycache__ 中 replay 相关 .pyc

### Runtime 外围残留

- [x] 2.22 scripts / config 中对 P3a 已删 surface 的引用残留——清除（check-runtime-smoke.sh, develop_callback_runtime.py, bootstrap_workspace.py, manifest.py, checkpoint_request.py）

### S2 验证（硬验收）

- [x] 2.V1 `pytest` 全通过（684 passed, 49 subtests）
- [x] 2.V2 `grep -rn "replay" runtime/*.py | grep -v "^Binary" | grep -v __pycache__` 仅剩注释（config.py:90 sunset 注释, router.py:377 deprecated 注释）
- [x] 2.V3 `grep -rn "workflow.learning" runtime/*.py | grep -v __pycache__` 无命中
- [x] 2.V4 `python3 -c "from runtime.builtin_catalog import load_builtin_skills; from pathlib import Path; skills = load_builtin_skills(repo_root=Path('.'), language='zh-CN'); assert 'workflow-learning' not in [s.name for s in skills]"` workflow-learning 不在枚举中
- [x] 2.V5 `test -f runtime/builtin_skill_packages/workflow-learning/skill.yaml && echo FAIL || echo OK` 输出 OK
- [x] 2.V6 `grep -c "workflow-learning" runtime/builtin_catalog.generated.json` 输出 0
- [x] 2.V7 `grep -c 'replay_session_dir' runtime/handoff.py` 输出 0
- [x] 2.V8 `grep -rn "replay" tests/*.py | grep -v __pycache__` 仅剩 test_installer.py footer 字面量（prompt asset 待更新）

## S3: Tests 分类标注

- [x] 3.1 `tests/test_*.py` + `tests/protocol/test_*.py` 按 contract / smoke / distribution / implementation-mirror 标注（31 文件）
- [x] 3.2 分类汇总：contract 23 | smoke 1 | distribution 6 | implementation-mirror 1（test_runtime_knowledge_layout.py）
- [x] 3.3 验证：所有 test 文件都有 `# Test classification:` 标注；`pytest` 684 passed, 49 subtests

## S4: CHANGELOG 压缩 + README 首屏降噪

### CHANGELOG 去文件列表化

- [x] 4.1 旧 102 条自动生成条目直接压成阶段摘要（不逐条迁移）
- [x] 4.2 新条目格式只保留 Summary + Changed，不列文件
- [x] 4.3 修 `scripts/release-draft-changelog.py` 只产摘要，不产文件清单
- [x] 4.4 同步更新 `CONTRIBUTING.md` changelog 说明

### README 首屏降噪与默认入口翻转

- [ ] 4.5 首屏只保留 3 件事：中断可恢复 + 需要拍板时会停 + 安装入口
- [ ] 4.6 默认叙事以 Convention（纯协议、无 runtime）为入口
- [ ] 4.7 Runtime（完整编排、gate、checkpoint）定位为增强路径
- [ ] 4.8 plan lifecycle / blueprint / runtime gate / checkpoint taxonomy / task size routing / .sopify-runtime 等内部术语降级到二级文档
- [ ] 4.9 `.sopify-runtime` 只作为后台实现细节出现，不作为用户首接触概念
- [ ] 4.10 同步更新 README.zh-CN.md

### S4 验证

- [ ] 4.V1 README 首屏 < 50 行
- [ ] 4.V2 首屏不出现 blueprint / checkpoint taxonomy / runtime state / .sopify-runtime 等术语
- [ ] 4.V3 Convention 作为默认叙事出现在 Runtime 之前
- [ ] 4.V4 `pytest` 全通过

## 完成标准

- [ ] `pytest` 全通过
- [ ] `release-preflight.sh` 正常退出
- [ ] `grep -rn "replay" runtime/*.py` 无生产代码命中
- [ ] README 首屏符合降噪标准
- [ ] 所有 test 文件有分类标注
- [ ] CHANGELOG 无文件列表格式条目
