# 任务清单: 推广前大收口整合

目录: `.sopify-skills/plan/20260529_pre_launch_consolidation/`

## 1. D2: 输出增强系统 [Wave 1]

- [ ] 1.1 升级 `skills/zh/skills/sopify/references/output-contract.md`：§1 gate 排除 Rich Readable + §3 整体升级（允许层 / 交付物条款 / 发现报告条款 / 密度梯度 / emoji 纪律 / markdown-only 表格）+ 新增 §5 脱敏规则
- [ ] 1.2 同步升级 `skills/en/skills/sopify/references/output-contract.md`
- [ ] 1.3 修改 `skills/zh/skills/sopify/develop/SKILL.md`：输出选择逻辑引用更新后的 §3 条款
- [ ] 1.4 同步修改 `skills/en/skills/sopify/develop/SKILL.md`

## 2. D3: 命令面收敛 [Wave 1]

- [ ] 2.1 修改 `runtime/router.py`：删除 `~go exec` regex 路由（L18），`~go` 增加活动 plan 自动检测逻辑
- [ ] 2.2 修改 `runtime/entry_guard.py`：bypass 列表移除 `~go exec` 条目
- [ ] 2.3 修改 `runtime/engine.py`：`exec_plan` 路由逻辑保留但不再由独立命令触发，由 `~go` 自动路由
- [ ] 2.4 更新 `.sopify-skills/blueprint/protocol.md`：`~go exec` 标注已移除，`~go` 自动检测活动 plan
- [ ] 2.5 更新 `skills/*/skills/sopify/develop/SKILL.md`：激活条件从 `exec_plan` 改为 `workflow + active_plan`
- [ ] 2.6 运行现有测试套件验证无回归：`python3 -m pytest tests -v`

## 3. D5: 发布前工程收口 [Wave 1]

### 3A. 原有清理项

- [ ] 3.1 清理 `.sopify-skills/project.md` 中的绝对路径 `/Users/weixin.li/...`
- [ ] 3.2 处理 `.sopify-skills/blueprint/skill-standards-refactor.md`：有效内容合并到 design.md，文件移至 history/
- [ ] 3.3 撰写人类可读的 CHANGELOG release note（覆盖 P0→P7 主线 + 本次收口）
- [ ] 3.4 清理 `.sopify-skills/plan/_registry.yaml` 不再活跃的条目
- [ ] 3.5 [手工] 设置 GitHub repo metadata：description / topics / social preview（需进 GitHub UI 操作）

### 3B. 审计修复 — 🔴 阻断级

- [ ] 3.6 `.gitignore` 补全：添加 `.env`、`.venv/`、`dist/`、`build/`、`.claude/settings.local.json`
- [ ] 3.7 `git rm --cached .claude/settings.local.json` 取消追踪本地配置
- [ ] 3.8 删除 `installer/bootstrap_workspace.py:450` 的 `~summary` 残留 regex
- [ ] 3.9 `bootstrap.sh` init 参数处理：移除 help 中的 init 描述或实际接入逻辑

### 3C. 审计修复 — 🟡 建议级

- [ ] 3.10 `scripts/sopify_init.py` docstring 补全 `--no-copilot`、`--language` 参数说明
- [ ] 3.11 `examples/external-repo-quickstart/README.md` 修正 `.github/instructions/sopify.instructions.md` 为实际安装路径
- [ ] 3.12 `install.sh` 添加 `python`/`py` 回退链（与 `install.ps1` 对齐）
- [ ] 3.13 `examples/sopify.config.yaml` 补全缺失配置项（`advanced.kb_init` 等）
- [ ] 3.14 `CONTRIBUTING.md` 更新 `scripts/install-sopify.sh` 等旧脚本路径引用
- [ ] 3.15 删除 `tests/test_action_intent.py` 中 `~compare` 死测试（L351-353, L368-370）
- [ ] 3.16 绝对路径清理（scope：6 个文件，3.1/3.7 已处理的除外，不做 git history rewrite）：`.sopify-skills/history/` 5 文件 + `tests/fixtures/current_gate_receipt.json`，替换为相对路径或占位符
- [ ] 3.17 D5 完成后运行测试套件验证无回归：`python3 -m pytest tests -v`

## 4. D1: README 重写与视觉资产升级 [Wave 2]

> 吸收 Wave 1 中 D3/D5 产生的 README 变更需求，一次性完整重写。

- [ ] 4.1 用 tech-graph skill 生成简化版 3 层架构图 SVG — ✅ 已完成（方案阶段产出）
- [ ] 4.2 用 tech-graph skill 生成方向依赖关系图 — ✅ 已完成（方案阶段产出）
- [ ] 4.3 重写 `README.md` 结构（Hero 精简 + "See It In Action" + 3 故事场景 Why + 精简 FAQ），同时吸收：
  - 删除 `~go exec` 命令行（来自 D3）
  - 更新 copilot target 状态（来自 D5）
  - 替换架构图为简化版
- [ ] 4.4 同步重写 `README.zh-CN.md`
- [ ] 4.5 设计新 cover 图方案（场景图：Start → Pause → Resume 跨宿主流）
- [ ] 4.6 替换 `assets/sopify-architecture.svg` 为简化版
- [ ] 4.7 更新 `docs/how-sopify-works.en.md` 和 `docs/how-sopify-works.md` 中过时命令引用
- [ ] 4.8 用 tech-graph 重画 how-sopify-works 的 4 张技术图为 SVG（workflow / checkpoint / plan-lifecycle / harness 映射，ZH + EN 各一版，共 8 个），并在 4.7 中一并更新图片引用

## 5. D4: 首次触达链路优化 [Wave 2]

- [ ] 5.1 在 `install.sh` 安装完成后增加结构化欢迎信息输出（含推荐首次操作）
- [ ] 5.2 在 `install.ps1` 同步增加欢迎信息
- [ ] 5.3 在 skill prompt 层增加空白状态检测：仅对空白 `.sopify-skills/` 触发首次引导，非空时静默跳过
- [ ] 5.4 更新 `examples/external-repo-quickstart/`：补充端到端截图和预期输出
- [ ] 5.5 验证：跑一次完整的外部 repo quickstart 链路

## 6. D6: 推广内容矩阵 [Wave 3]

- [ ] 6.1 撰写掘金主文草稿："AI 编程的失忆症——我如何用 Sopify 解决"
- [ ] 6.2 撰写 V2EX 讨论帖草稿："AI 编程的 3 个隐藏问题"
- [ ] 6.3 撰写 GitHub Blog 英文稿草稿："Beyond chat: resumable AI coding with Sopify"
- [ ] 6.4 准备即刻/X 短内容素材（截图 + 一句话 + 链接）× 3 条
- [ ] 6.5 交付给用户审阅修改后发布

## 7. D7: Runtime Phase 2 收缩 [Wave 4 — 仅方案]

- [ ] 7.1 完成 installer 5 文件的依赖分析
- [ ] 7.2 设计 installer 解耦方案（每个文件的 runtime import 替代路径）
- [ ] 7.3 设计 runtime/ 降级标注方案
- [ ] 7.4 输出 D7 独立方案包骨架，供推广后执行

## 8. 文档更新

- [ ] 8.1 更新 `.sopify-skills/blueprint/README.md` 托管区块（当前焦点 + 活动 plan）

## 执行波次总览

| 波次 | 方向 | 任务数 | 说明 | README 策略 |
|------|------|--------|------|------------|
| Wave 1 | D2 + D3 + D5 | 27 | 内核收口 + 审计修复（D2=4, D3=6, D5=17） | **不碰 README** |
| Wave 2 | D1 + D4 | 13 | 体验层：README 统一重写 + 首次触达 + 技术图 SVG 化 | **一次性完整重写** |
| Wave 3 | D6 | 5 | 推广内容 | — |
| Wave 4 | D7 | 4 | Runtime 收缩方案（不执行） | — |
| — | D8 | 1 | 文档同步 | — |
| **合计** | | **50** | （其中 2 项已在方案阶段完成） | |

**README 编辑策略：** 所有影响 README 的任务全部推迟到 Wave 2 D1 统一重写。README 文件只被完整改一次。

**发布门槛：** D5-3B（阻断级审计） + D2 + D3 + D1 = 最小可发布集；D4 / D6 / D8 可发布后推进。
