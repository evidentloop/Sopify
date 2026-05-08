---
plan_id: 20260508_p3b_perimeter_cleanup
feature_key: p3b_perimeter_cleanup
level: light
lifecycle_state: active
knowledge_sync:
  project: aligned
  background: aligned
  design: aligned
  tasks: aligned
archive_ready: false
---

# P3b: Perimeter Cleanup 方案包

## Plan Intake Checklist

1. **主命中里程碑**：P3b（Perimeter Cleanup）
2. **改动性质**：execution strategy / implementation wave — 不定义新 contract，只清理/下线已确认的旧面
3. **Machine truth 变更**：删除 replay route（已从 consult canonical family 移除，design.md 已反映）；删除 workflow-learning skill entry（builtin_catalog.py）。不新增 machine truth
4. **Legacy surface**：replay / workflow-learning 已在 design.md 标注 P3b sunset；无需替代 contract
5. **Core promotion rule / hard max 影响**：无

## Scope

清理 P3a 后的外围面，为 P4 系列减重扫清障碍。4 个内部切片，按依赖顺序执行。

### 不在 scope 内

- 不改 gate/router 核心逻辑
- 不改 protocol.md 或 design.md 的 contract 定义（blueprint truth 已在本轮之前完成）
- 不做 P4a 级别的 external surface freeze
- 不做 README 产品重设计（只做首屏降噪，产品定位不变）

## Approach

1 个方案包，4 个内部切片，按依赖顺序串行。每切片完成后跑 test 验证。

## Tasks

### S1: Release Gate + Evals 卫生

- [ ] `release-preflight.sh`：从 `unittest discover`（当前环境挂死）改为 `pytest`
- [ ] `evals/skill_eval_report.json` 加入 `.gitignore`；baseline 和 SLO 文件保留

验证：`bash scripts/release-preflight.sh` 正常退出；`git status` 不再显示 `skill_eval_report.json`

### S2: Replay 下线 + 旧概念清理 + Runtime 外围残留

**replay 能力下线：**
- [ ] 删除 `.sopify-skills/replay/` 目录数据
- [ ] 移除 `runtime/replay.py` 写入逻辑
- [ ] 移除 `runtime/engine.py` 中 replay 事件发射
- [ ] 移除 `runtime/develop_callback.py` 中 replay 记录
- [ ] 移除 `runtime/handoff.py` 中 `replay_session_dir` 附件（约 L347-348）
- [ ] 移除 `runtime/output.py` 中 replay 展示
- [ ] `runtime/builtin_catalog.py`：删除 workflow-learning skill entry（L92-100）
- [ ] 清 README / README.zh-CN.md / docs 中对 replay 和 workflow-learning 的引用

**旧概念清理（P3a 已 sunset surface 残留）：**
- [ ] tests 中验证 P3a 已 sunset surface 的断言——更新或删除
- [ ] prompt 中引用已 sunset contract 的段落——清除
- [ ] handoff/output 旧兼容投影——清除
- [ ] reason phrasing / phase label 特判——清除

**Runtime 外围残留：**
- [ ] tests / prompt / projection / docs 中对 P3a 已删 surface 的引用残留——清除

验证：`pytest` 全通过；`grep -r replay runtime/` 无生产代码命中；`grep -r workflow.learning runtime/` 无生产代码命中

### S3: Tests 分类标注

- [ ] `tests/test_*.py` 按以下 4 类标注（注释或 pytest marker）：
  - `contract`（必保）：验证外部消费面 / machine truth schema
  - `smoke`（必保）：端到端最小路径验证
  - `distribution`（必保）：安装/分发/打包验证
  - `implementation-mirror`（可砍）：只镜像内部实现细节，P4b 减重候选
- [ ] 输出分类汇总表（几个 contract / smoke / distribution / implementation-mirror）

验证：所有 test 文件都有明确分类标注；`pytest` 全通过

### S4: CHANGELOG 压缩 + README 首屏降噪

**CHANGELOG 去文件列表化：**
- [ ] 旧 102 条自动生成条目直接压成阶段摘要（不逐条迁移）
- [ ] 新条目格式只保留 Summary + Changed，不列文件
- [ ] 修 `scripts/release-draft-changelog.py` 只产摘要，不产文件清单
- [ ] 同步更新 `CONTRIBUTING.md` changelog 说明

**README 首屏降噪与默认入口翻转：**
- [ ] 首屏只保留 3 件事：中断可恢复 + 需要拍板时会停 + 安装入口
- [ ] 默认叙事以 Convention（纯协议、无 runtime）为入口
- [ ] Runtime（完整编排、gate、checkpoint）定位为增强路径
- [ ] plan lifecycle / blueprint / runtime gate / checkpoint taxonomy / task size routing / .sopify-runtime 等内部术语降级到二级文档
- [ ] `.sopify-runtime` 只作为后台实现细节出现，不作为用户首接触概念
- [ ] 同步更新 README.zh-CN.md

验证：README 首屏 < 50 行；首屏不出现 blueprint / checkpoint taxonomy / runtime state / .sopify-runtime 等术语；`pytest` 全通过

## 完成标准

- [ ] `pytest` 全通过
- [ ] `release-preflight.sh` 正常退出
- [ ] `grep -r replay runtime/` 无生产代码命中
- [ ] README 首屏符合降噪标准
- [ ] 所有 test 文件有分类标注
- [ ] CHANGELOG 无文件列表格式条目
