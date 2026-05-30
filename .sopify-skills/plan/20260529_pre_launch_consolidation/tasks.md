# 任务清单: 推广前大收口整合

目录: `.sopify-skills/plan/20260529_pre_launch_consolidation/`

## 价值分级说明

| 标签 | 含义 | 门槛 |
|------|------|------|
| 🔴 P0 | 发布阻断 | 不完成不打 tag、不推广 |
| 🟡 P1 | 发布前应做 | 推广前应完成，但不阻断 tag |
| 🟢 P2 | 发布后迭代 | 推广后按反馈优先级迭代 |
| 📌 | README 硬前置 | 该任务产出直接影响 README 内容正确性，必须在 D1 4.3 之前完成 |

---

## 1. D2: 输出增强系统 [Wave 1] 🟡 P1

- [ ] 1.1 升级 `skills/zh/skills/sopify/references/output-contract.md`：§1 gate 排除 Rich Readable + §3 整体升级（允许层 / 交付物条款 / 发现报告条款 / 密度梯度 / emoji 纪律 / markdown-only 表格）+ 新增 §5 脱敏规则
- [ ] 1.2 同步升级 `skills/en/skills/sopify/references/output-contract.md`
- [ ] 1.3 修改 `skills/zh/skills/sopify/develop/SKILL.md`：输出选择逻辑引用更新后的 §3 条款
- [ ] 1.4 同步修改 `skills/en/skills/sopify/develop/SKILL.md`

## 2. D3: 命令面收敛 [Wave 1] 🔴 P0

> 📌 README 硬前置（2.1/2.2/2.3/2.5/2.7）：移除 `~go exec` 后，D1 4.3 README 重写才能写出正确的命令表。2.4 为文档更新，非 README 硬前置。

- [x] 2.1 修改 `runtime/router.py`：删除 `~go exec` regex 路由（L18），`~go` 增加活动 plan 自动检测逻辑
- [x] 2.2 修改 `runtime/entry_guard.py`：bypass 列表移除 `~go exec` 条目
- [x] 2.3 修改 `runtime/engine.py`：`exec_plan` 路由逻辑保留但不再由独立命令触发，由 `~go` 自动路由
- [x] 2.4 更新 `.sopify-skills/blueprint/protocol.md`：`~go exec` 标注已移除，`~go` 自动检测活动 plan
- [x] 2.5 更新 `skills/*/skills/sopify/develop/SKILL.md`：激活条件从 `exec_plan` 改为 `workflow + active_plan`（⚠️ 与 D2 1.3/1.4 改同一文件，建议同波次顺序执行：先 D2 再 D3）
- [-] 2.6 ~~运行测试套件~~ — 已合并到 3.17（Wave 1 末尾统一跑一次）
- [x] 2.7 🔴 全仓 `~go exec` 引用收口（29 处 / 7 文件，2.1-2.3 之外）：`runtime/output.py`（4 处 exec_handoff/next_exec 消息）、`runtime/clarification.py`（1 处命令列表）、`runtime/_planning.py`（1 处拒绝消息）、`runtime/handoff.py`（1 处注释）、`scripts/check-prompt-runtime-gate-smoke.py`（1 处测试用例）、`tests/test_runtime_engine.py`（19 处测试）、`tests/test_runtime_router.py`（2 处测试）

## 3. D5: 发布前工程收口 [Wave 1]

### 3A. 原有清理项 🟡 P1

> 📌 README 前置：3.3 CHANGELOG 和 3.5 repo metadata 为 README 提供上下文。

- [ ] 3.1 清理 `.sopify-skills/project.md` 中的绝对路径 `/Users/weixin.li/...`
- [ ] 3.2 处理 `.sopify-skills/blueprint/skill-standards-refactor.md`：有效内容合并到 design.md，文件移至 history/
- [ ] 3.3 撰写人类可读的 CHANGELOG release note（覆盖 P0→P7 主线 + 本次收口）
- [ ] 3.4 清理 `.sopify-skills/plan/_registry.yaml` 不再活跃的条目
- [ ] 3.5 [手工] 设置 GitHub repo metadata：description / topics / social preview（需进 GitHub UI 操作）

### 3B. 审计修复 — 🔴 P0 阻断级 📌

> 📌 README 前置：3.6-3.7 修复安全问题后，README 安装指引才可信。

- [x] 3.6 📌 `.gitignore` 补全：添加 `.env`、`.venv/`、`dist/`、`build/`、`.claude/settings.local.json`、`.agents/history/`
- [x] 3.7 📌 `git rm --cached .claude/settings.local.json` 取消追踪本地配置
- [x] 3.8 删除 `installer/bootstrap_workspace.py:450` 的 `~summary` 残留 regex
- [x] 3.9 `bootstrap.sh` init 参数处理：移除 help 中的 init 描述或实际接入逻辑

### 3C. 审计修复 — 🟡 P1 建议级

- [ ] 3.10 `scripts/sopify_init.py` docstring 补全 `--no-copilot`、`--language` 参数说明
- [x] 3.11 📌 `examples/external-repo-quickstart/README.md` + `docs/getting-started.md` 修正 `sopify.instructions.md` 为实际安装路径（getting-started.md 有 3 处、quickstart 有 2 处）
- [x] 3.12 📌 `install.sh` 添加 `python`/`py` 回退链（与 `install.ps1` 对齐）
- [ ] 3.13 `examples/sopify.config.yaml` 补全缺失配置项（`advanced.kb_init` 等）
- [-] 3.14 📌 `CONTRIBUTING.md` 更新 `scripts/install-sopify.sh` 等旧脚本路径引用 — 脚本实际存在，引用未断
- [x] 3.15 删除 `tests/test_action_intent.py` 中 `~compare` 死测试（L351-353, L368-370）
- [ ] 3.16 绝对路径清理（scope：6 个文件，3.1/3.7 已处理的除外，不做 git history rewrite）：`.sopify-skills/history/` 5 文件 + `tests/fixtures/p4d_smoke/current_gate_receipt.json`，替换为相对路径或占位符
- [ ] 3.17 Wave 1 末尾统一运行测试套件验证无回归：`python3 -m pytest tests -v`（D2 + D3 + D5 全部完成后统一跑一次）
- [ ] 3.18 🟡 创建 `.github/ISSUE_TEMPLATE/`：bug_report.md + feature_request.md（标准 issue 模板）

## 4. D1: README 重写与视觉资产升级 [Wave 2] 🔴 P0

> ⚠️ 前置条件：D3 2.1/2.2/2.3/2.5/2.7 完成 + D5-3B 全部完成 + 所有 📌 标记任务完成。
> README 文件只被完整改一次，吸收 Wave 1 全部 📌 产出。

- [x] 4.1 用 tech-graph skill 生成简化版 3 层架构图 SVG — ✅ 已完成（方案阶段产出）
- [x] 4.2 用 tech-graph skill 生成方向依赖关系图 — ✅ 已完成（方案阶段产出）
- [x] 4.3 🔴 重写 `README.md` 结构（Hero 精简 + "See It In Action" + 3 故事场景 Why + 精简 FAQ），同时吸收：
  - 删除 `~go exec` 命令行（来自 D3）
  - 更新 copilot target 状态（来自 D5）
  - 替换架构图为简化版
  - **新增 哲学宣言**：Hero 区增加 3-5 行核心理念（参考 Superpowers/OpenSpec 风格，突出"证据驱动 + 跨宿主可恢复 + 决策可追溯"）
  - **新增 "See It In Action"**：首屏放一个真实 `~go` 会话片段（ASCII 会话 demo 或终端截图），让用户秒懂产品价值
- [x] 4.4 🔴 同步重写 `README.zh-CN.md`
- [ ] 4.5 🟡 设计新 cover 图方案（场景图：Start → Pause → Resume 跨宿主流）
- [x] 4.6 🔴 替换 `assets/sopify-architecture.svg` 为简化版
- [ ] 4.7 🟡 更新 `docs/how-sopify-works.en.md` 和 `docs/how-sopify-works.md` 中过时命令引用
- [ ] 4.8 🟢 用 tech-graph 重画 how-sopify-works 的 4 张技术图为 SVG（workflow / checkpoint / plan-lifecycle / harness 映射，ZH + EN 各一版，共 8 个），并在 4.7 中一并更新图片引用

## 5. D4: 首次触达链路优化 [Wave 2] 🟡 P1

- [ ] 5.1 在 `install.sh` 安装完成后增加结构化欢迎信息输出（含推荐首次操作）
- [ ] 5.2 在 `install.ps1` 同步增加欢迎信息
- [ ] 5.3 在 skill prompt 层增加空白状态检测：仅对空白 `.sopify-skills/` 触发首次引导，非空时静默跳过
- [ ] 5.4 更新 `examples/external-repo-quickstart/`：补充端到端截图和预期输出
- [ ] 5.5 验证：跑一次完整的外部 repo quickstart 链路

## 6. D6: 推广内容矩阵 [Wave 3]

### 6A. 推广文章 🟡 P1

- [ ] 6.1 撰写掘金主文草稿："AI 编程的失忆症——我如何用 Sopify 解决"
- [ ] 6.2 撰写 V2EX 讨论帖草稿："AI 编程的 3 个隐藏问题"
- [ ] 6.3 撰写 GitHub Blog 英文稿草稿："Beyond chat: resumable AI coding with Sopify"（同步发 dev.to）
- [ ] 6.4 准备即刻/X 短内容素材（截图 + 一句话 + 链接）× 3 条
- [ ] 6.5 交付给用户审阅修改后发布

### 6B. 社区基建 🟢 P2

> 建议在首篇推广文章发布、收到真实用户反馈后再建。空社区是负信号。

- [ ] 6.6 创建 Discord 服务器（频道：announcements / general / feedback），README 加 badge
- [ ] 6.7 在 GitHub repo Settings → Features 中开启 Discussions

## 7. D7: Runtime Phase 2 收缩 [Wave 4 — 仅方案] 🟢 P2

- [ ] 7.1 完成 installer 5 文件的依赖分析
- [ ] 7.2 设计 installer 解耦方案（每个文件的 runtime import 替代路径）
- [ ] 7.3 设计 runtime/ 降级标注方案
- [ ] 7.4 输出 D7 独立方案包骨架，供推广后执行

## 8. 文档更新 🟡 P1

- [ ] 8.1 更新 `.sopify-skills/blueprint/README.md` 托管区块（当前焦点 + 活动 plan）

---

## 执行波次总览

| 波次 | 方向 | 任务数 | 价值分级 | 说明 | README 策略 |
|------|------|--------|---------|------|------------|
| Wave 1 | D5-3B + D3 | 11 | 🔴 P0 | 安全修复 + 命令面收敛 + 全仓引用收口 | **不碰 README** |
| Wave 1 | D2 + D5-3A/3C | 18 | 🟡 P1 | 输出增强 + 工程清理 | **不碰 README** |
| Wave 2 | D1 (4.3/4.4/4.6) | 3 | 🔴 P0 | README 统一重写（含哲学宣言 + See It In Action） | **一次性完整重写** |
| Wave 2 | D1 (其余) + D4 | 10 | 🟡-🟢 | 视觉资产 + 首次触达 + 技术图 SVG 化 | 不再碰 README |
| Wave 3 | D6-A | 5 | 🟡 P1 | 推广文章 | — |
| Wave 3 | D6-B | 2 | 🟢 P2 | 社区基建（建议推广后再建） | — |
| Wave 4 | D7 | 4 | 🟢 P2 | Runtime 收缩方案（不执行） | — |
| — | D8 | 1 | 🟡 P1 | 文档同步 | — |
| **合计** | | **54** | | 已完成 2 + 已合并 1，**待执行 51** | |

## README 依赖链

```
Wave 1 📌 硬前置（必须在 D1 4.3 之前完成）
  ├── D5-3B 3.6/3.7: .gitignore + local config 清理（安全可信）
  ├── D3 2.1-2.3/2.5/2.7: ~go exec 全仓移除（命令表正确）
  ├── D5-3C 3.11: 安装路径修正（quickstart 指引正确）
  ├── D5-3C 3.12: install.sh python 回退（安装指引正确）
  └── D5-3C 3.14: CONTRIBUTING.md 路径更新（贡献指南正确）

Wave 1 非前置（完成更好，不阻断 README）
  ├── D5-3A 3.3: CHANGELOG（README 不直接引用）
  ├── D5-3A 3.5: repo metadata（GitHub UI 操作）
  └── D2 1.1-1.4: output-contract 定稿（README 不引用 contract 条款）
        ↓
Wave 2 D1 4.3/4.4: README 一次性完整重写
        ↓
Wave 3 D6: 推广文章（引用 README 截图/链接）
```

## 发布门槛

> 口径：下表只计 `[ ]` 待执行项，不含已完成 `[x]` 和已合并 `[-]`。

| 门槛 | 包含任务编号 | 待执行数 | 说明 |
|------|------------|----------|------|
| 🔴 **最小可发布集** | D5-3B: 3.6/3.7/3.8/3.9 (4) + D3: 2.1/2.2/2.3/2.5/2.7 (5) + D1: 4.3/4.4/4.6 (3) | **12** | 安全 + 命令面 + README |
| 🟡 **推荐发布集** | 最小集 + D2: 1.1-1.4 (4) + D3: 2.4 (1) + D5-3A: 3.1-3.5 (5) + D5-3C: 3.10-3.18 (9) + D1: 4.5/4.7 (2) + D4: 5.1-5.5 (5) + D6-A: 6.1-6.5 (5) + D8: 8.1 (1) | **+32 = 44** | 全面打磨 + 推广 |
| 🟢 **完整集** | 推荐集 + D1: 4.8 (1) + D6-B: 6.6/6.7 (2) + D7: 7.1-7.4 (4) | **+7 = 51** | 含发布后迭代项 |
