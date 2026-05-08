# 技术设计: P3b Perimeter Cleanup

## 方案概述

1 个方案包，4 个内部切片，按依赖顺序串行执行。每切片完成后跑 `pytest` 验证。

## Scope 边界

### 在 scope 内

- Release gate 从 unittest 改 pytest
- replay 能力下线（代码 + 数据 + 文档引用）
- P3a 旧概念残留清理
- Tests 分类标注
- CHANGELOG 去文件列表化
- README 首屏降噪与 Convention 默认入口翻转

### 不在 scope 内

- 不改 gate/router 核心决策逻辑
- 不改 protocol.md 或 design.md 的 contract 定义（blueprint truth 已在之前收敛）
- 不做 P4a 级别的 external surface freeze
- 不做 README 产品重设计（只做首屏降噪，产品定位不变）
- 不改 builtin_catalog.py 的导出接口形态（只删 workflow-learning entry，schema 不变）

## 切片设计与风险

### S1: Release Gate + Evals 卫生

**变更面**：`scripts/release-preflight.sh`、`.gitignore`

**风险**：低。release-preflight.sh 是 CI 辅助脚本，改 test runner 不影响 runtime。

**验证**：`bash scripts/release-preflight.sh` 正常退出；`git status` 不再显示 `skill_eval_report.json`

### S2: Replay 下线 + 旧概念清理 + Runtime 外围残留

**变更面**：
- `runtime/replay.py`（整文件删除）
- `runtime/engine.py`（replay 事件发射 + L1704-1705 skill 映射分支移除）
- `runtime/develop_callback.py`（replay 记录移除）
- `runtime/handoff.py`（replay_session_dir 附件移除，约 L347-348）
- `runtime/output.py`（replay 展示移除）
- `runtime/builtin_catalog.py`（workflow-learning entry 删除，L92-101）
- `runtime/builtin_skill_packages/workflow-learning/skill.yaml`（整文件删除）
- `runtime/builtin_catalog.generated.json`（workflow-learning 条目移除）
- `runtime/router.py`（replay route 分支移除，L290-296）
- `.sopify-skills/replay/`（目录数据删除）
- README / README.zh-CN.md / docs 中 replay / workflow-learning 引用
- tests 中 replay / workflow-learning 相关断言（test_runtime_router, test_runtime_decision, test_runtime_sample_invariant_gate, test_runtime_skill_registry, test_installer）

**风险**：中。
- 核心判断：replay 是 append-only 写入，无回读消费者。gate.py / router.py 不读 replay 数据。下线不影响主链决策。
- 潜在风险点：handoff.py 中 `replay_session_dir` 作为 artifact 附件传递。移除后需确认 handoff rendering 不因缺少字段而异常。
- 旧概念清理涉及 tests，可能有断言依赖已删 surface 的测试用例——需逐个判断是删除还是改写。

**验证（硬验收）**：
- `pytest` 全通过
- `grep -rn "replay" runtime/*.py` 无生产代码命中
- `grep -rn "workflow.learning" runtime/*.py` 无命中
- `python3 -c "from runtime.builtin_catalog import load_builtin_skills; ..."` 确认 workflow-learning 不在枚举中
- `test -f runtime/builtin_skill_packages/workflow-learning/skill.yaml` 返回不存在
- `grep -c "workflow-learning" runtime/builtin_catalog.generated.json` 输出 0
- `grep -c 'replay_session_dir' runtime/handoff.py` 输出 0；另需手动触发一次 develop → handoff 流程确认无 KeyError/AttributeError
- `grep -rn "replay" tests/*.py` 无命中或仅剩不相关字面量

### S3: Tests 分类标注

**变更面**：`tests/test_*.py`（注释或 pytest marker）

**风险**：低。只添加标注，不改测试逻辑。

**分类规则**：
| 分类 | 定义 | P4b 处置 |
|------|------|---------|
| contract | 验证外部消费面 / machine truth schema | 必保 |
| smoke | 端到端最小路径验证 | 必保 |
| distribution | 安装/分发/打包验证 | 必保 |
| implementation-mirror | 只镜像内部实现细节 | 可砍候选 |

**验证**：所有 test 文件都有明确分类标注；`pytest` 全通过；输出分类汇总

### S4: CHANGELOG 压缩 + README 首屏降噪

**变更面**：
- `CHANGELOG.md`（旧条目压缩 + 格式声明更新）
- `scripts/release-draft-changelog.py`（只产摘要）
- `CONTRIBUTING.md`（changelog 说明同步）
- `README.md` + `README.zh-CN.md`（首屏重写）

**风险**：中。
- CHANGELOG 压缩是不可逆的信息损失（旧 102 条文件列表会被压成摘要），但这些信息在 git log 中仍可追溯。
- README 首屏重写是产品叙事变更。核心约束：Convention 为默认入口，Runtime 为增强路径。.sopify-runtime 不出现在首接触面。
- 首屏降噪直接影响 P4c 验收 (b) 的前提条件。

**验证**：
- README 首屏 < 50 行
- 首屏不出现 blueprint / checkpoint taxonomy / runtime state / .sopify-runtime 等术语
- Convention 作为默认叙事出现在 Runtime 之前
- `pytest` 全通过
