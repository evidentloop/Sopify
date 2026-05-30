# 任务清单: 推广前大收口整合

目录: `.sopify-skills/plan/20260529_pre_launch_consolidation/`

## 价值分级说明

| 标签 | 含义 | 门槛 |
|------|------|------|
| 🔴 P0 | 推广阻断 | 不完成不推广 |
| 🟡 P1 | 推广前应做 | 显著提升推广效果 |
| 🟢 P2 | 推广后迭代 | 按反馈优先级迭代 |
| 📌 | README 硬前置 | 该任务产出直接影响 README 内容正确性，必须在 D1 4.3 之前完成 |

---

## ✅ 已完成方向

### D3: 命令面收敛 — ✅ 全部完成
- [x] 2.1 `runtime/router.py` ~go exec 路由移除 + 活动 plan 自动检测
- [x] 2.2 `runtime/entry_guard.py` bypass 列表清理
- [x] 2.3 `runtime/engine.py` exec_plan 改为 ~go 自动路由
- [x] 2.4 `protocol.md` 文档更新
- [x] 2.5 `develop/SKILL.md` 激活条件更新
- [-] 2.6 运行测试套件 — 已合并到 3.17（Wave 1 末尾统一跑一次）
- [x] 2.7 全仓 29 处 ~go exec 引用收口

### D5-3B: 安全修复 — ✅ 全部完成
- [x] 3.6 .gitignore 补全
- [x] 3.7 本地配置取消追踪
- [x] 3.8 bootstrap ~summary 残留删除
- [x] 3.9 bootstrap.sh init 参数清理

### D1: README 重写 — ✅ 核心完成
- [x] 4.1 架构图 SVG 生成
- [x] 4.2 方向依赖关系图
- [x] 4.3 README.md 全面重写（Hero + See It In Action + 3 故事 + 命令表）
- [x] 4.4 README.zh-CN.md 同步重写
- [x] 4.6 architecture.svg 替换为简化版
- [x] 3.11 安装路径修正
- [x] 3.12 install.sh python 回退链
- [x] 3.15 死测试删除

---

## 待执行任务（按推广优先级排序）

### Wave A: 首次触达优化 🔴 P0

> 新用户 install 后的前 60 秒体验。推广文章 CTA 直接导向这个链路。

- [-] 5.1 `install.sh` 欢迎信息 — 跳过：现有输出已包含结构化引导（宿主 + 版本 + Next: ~go）
- [-] 5.2 `install.ps1` 欢迎信息 — 跳过：同 5.1
- [-] 5.3 空白状态检测 — 跳过：~go 已自动处理空白 `.sopify-skills/` 初始化
- [x] 5.4 `examples/external-repo-quickstart/` 补充预期输出 + 关键步骤说明
- [x] 5.5 端到端验证：在干净环境跑一次完整 quickstart 链路

### Wave B: 文档 + 仓库打磨 🟡 P1

> README → docs 点击体验不断层 + 仓库专业度

- [-] 4.7 更新 `docs/how-sopify-works.en.md` + `.md` 内容（移除过时描述，对齐当前行为）
- [ ] 4.8 用 tech-graph 重画 4 张技术图为 SVG（workflow / checkpoint / plan-lifecycle / harness，ZH+EN 共 8 个）
- [x] 3.18 创建 `.github/ISSUE_TEMPLATE/`：bug_report.md + feature_request.md
- [x] 3.1 清理 `.sopify-skills/project.md` 中的绝对路径
- [x] 3.16 绝对路径清理（`.sopify-skills/history/` 5 文件 + test fixture 1 文件）
- [x] 3.3 撰写 CHANGELOG release note（覆盖 P0→P7 主线 + 本次收口）
- [x] 3.10 `scripts/sopify_init.py` docstring 补全
- [x] 3.13 `examples/sopify.config.yaml` 补全缺失配置项
- [-] 3.14 `CONTRIBUTING.md` 更新旧脚本路径引用 — 跳过：脚本实际存在，引用未断
- [x] 3.17 统一运行测试套件验证无回归
- [x] 8.1 更新 `.sopify-skills/blueprint/README.md` 托管区块

### Wave C: 输出增强 🟡 P1

> 提升 Sopify 每次输出的人类可读性。不影响用户可见安装面，但提升使用体感。

- [ ] 1.1 升级 zh `output-contract.md`：§3 整体升级（密度梯度 / emoji 纪律 / 交付物分段叙事 / 发现报告分组）+ §5 脱敏规则
- [ ] 1.2 同步升级 en `output-contract.md`
- [ ] 1.3 修改 zh `develop/SKILL.md`：输出选择逻辑引用更新后的 §3
- [ ] 1.4 同步修改 en `develop/SKILL.md`

### Wave D: 推广文章 🟡 P1

> 所有用户可见面就绪后最后写。AI 协助撰写，用户审阅发布。

- [ ] 6.1 掘金主文草稿："AI 编程的失忆症——我如何用 Sopify 解决"
- [ ] 6.2 V2EX 讨论帖草稿："AI 编程的 3 个隐藏问题"
- [ ] 6.3 GitHub Blog / dev.to 英文稿草稿："Beyond chat: resumable AI coding with Sopify"
- [ ] 6.4 即刻/X 短内容素材（截图 + 一句话 + 链接）× 3 条
- [ ] 6.5 交付用户审阅修改后发布

### Wave E: 延后项 🟢 P2

> 推广后按反馈迭代。

- [ ] 7.1 Runtime installer 依赖分析
- [ ] 7.2 installer 解耦方案设计
- [ ] 7.3 runtime/ 降级标注方案
- [ ] 7.4 D7 独立方案包骨架
- [ ] 6.6 Discord 服务器（等有真实用户再建）
- [ ] 6.7 GitHub Discussions 开启
- [ ] 3.2 skill-standards-refactor.md 归档
- [ ] 3.4 registry 不活跃条目清理
- [ ] 3.5 [手工] GitHub repo metadata（description / topics / social preview）
- [ ] 4.5 新 cover 图方案（场景图版）

---

## 执行波次总览

| 波次 | 方向 | 待执行 | 优先级 | 并行关系 |
|------|------|--------|--------|---------|
| Wave A | 首次触达 | 5 | 🔴 P0 | 可立即开始 |
| Wave B | Docs + 打磨 | 10 | 🟡 P1 | 与 A/C 并行 |
| Wave C | 输出增强 | 4 | 🟡 P1 | 与 A/B 并行 |
| Wave D | 推广文章 | 5 | 🟡 P1 | 等 A+B 完成 |
| Wave E | 延后 | 10 | 🟢 P2 | 推广后 |
| **合计** | | **34** | | 已完成 20/54 |

## 依赖关系

```
Wave A (首次触达) ─────┐
Wave B (docs + 打磨) ──┼──→ Wave D (推广文章) ──→ 发布推广
Wave C (输出增强) ─────┘         ↑ 引用最终状态

Wave E (延后) ──→ 推广后按反馈迭代
```

## README 依赖链

```
Wave 1 📌 硬前置（必须在 D1 4.3 之前完成）
  ├── D5-3B 3.6/3.7: .gitignore + local config 清理（安全可信）
  ├── D3 2.1-2.3/2.5/2.7: ~go exec 全仓移除（命令表正确）
  ├── D5-3C 3.11: 安装路径修正（quickstart 指引正确）
  ├── D5-3C 3.12: install.sh python 回退（安装指引正确）
  └── D5-3C 3.14: CONTRIBUTING.md 路径引用核对（当前已确认无需改动）

Wave 1 非前置（完成更好，不阻断 README）
  ├── D5-3A 3.3: CHANGELOG（README 不直接引用）
  ├── D5-3A 3.5: repo metadata（GitHub UI 操作）
  └── Wave C 1.1-1.4: output-contract / develop 输出增强（README 不直接引用）
        ↓
Wave B D1 4.3/4.4: README 一次性完整重写
        ↓
Wave D 6.1-6.5: 推广文章（引用 README 截图 / 链接）
```


## 推广就绪门槛

| 门槛 | 包含波次 | 待执行数 | 说明 |
|------|---------|----------|------|
| 🔴 **最小可推广** | Wave A | **5** | 首次触达就绪，即可开始推广 |
| 🟡 **推荐推广集** | Wave A + B + C + D | **24** | 全面打磨 + 文章就绪 |
| 🟢 **完整集** | 全部 | **34** | 含推广后迭代项 |
