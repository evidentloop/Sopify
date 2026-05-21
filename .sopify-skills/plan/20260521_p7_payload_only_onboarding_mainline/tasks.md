---
plan_id: 20260521_p7_payload_only_onboarding_mainline
feature_key: p7_payload_only_onboarding_mainline
level: standard
lifecycle_state: active
---

# 任务清单

## 决策记录

| DR | 决策 | 约束 |
|----|------|------|
| DR-1 版本锚点 | `.sopify-skills/sopify.json`（极简，~5 字段） | 版本真值只在此文件，不重复 |
| DR-2 Repo-local 激活载体 | repo-local pointer 不是统一文件模型；仅在宿主需要 repo-local discovery 时，写入宿主原生 instruction 文件 | Codex/Claude 默认不写 repo-local header；具体文件名到实现切片再落 |
| DR-3 Bootstrap 入口 | `python3 -m sopify_bootstrap` canonical，`curl\|bash` convenience | init 最小产出 = sopify.json + ignore block；pointer 按宿主需要追加，不是默认产物 |

**定性：** P7 不是从 0 到 1 的全局化。全局发动机已就位，P7 只替换 repo 内的 legacy 激活物（`.sopify-runtime/manifest.json` → 统一 workspace marker）。统一的只有 sopify.json；本地 pointer 不是统一文件模型，而是宿主适配策略。

## S1: 激活物迁移方案分析 + 新 marker/pointer 模型定义

- [x] 现状全链路走读：全局发动机 + repo thin stub 的消费者全景
- [x] `.sopify-runtime/manifest.json` thin stub 字段清单 + 6 个生产消费者映射
- [x] 版本锚点迁移方案评估 → DR-1 APPROVED: `.sopify-skills/sopify.json`
- [x] prompt 分发模型修订 → DR-2 APPROVED: 全局 prompt + repo 轻量 pointer
- [x] bootstrap 入口决策 → DR-3 APPROVED: `python3 -m sopify_bootstrap` canonical
- [x] P7 定性校正：不是 greenfield 全局化，而是 repo 激活物迁移
- [x] 决策拍板（DR-1/2/3 全部 APPROVED，含约束条件）

## S2: 激活物迁移实现（统一 marker + dual-path detection）

- [x] `.sopify-skills/sopify.json` schema + 读写逻辑
- [x] 6 个生产消费者检测路径迁移（`.sopify-runtime/manifest.json` → `sopify.json`，dual-path fallback）
- [x] workspace detection 锚点切换（祖先扫描改为 `sopify.json`）
- [x] dual-write 过渡期：bootstrap 同时写 sopify.json + legacy stub
- [x] legacy field merge：sopify.json 为 primary marker 时，从 legacy stub 补入 `legacy_fallback`/`ignore_mode` 等字段
- [x] 全量回归：721 passed

## S3: repo-local activation adapter + Copilot 资产重构 + diagnostics

- [ ] repo-local activation adapter：按宿主类型决定是否写本地 inst 文件（managed block upsert）
  - 全局 prompt 型（Codex/Claude）：默认不写 repo-local header
  - 本地 inst 文件型（Copilot）：
    - 轻入口：`.github/copilot-instructions.md`（managed block upsert）
    - 重说明：`.github/instructions/sopify.instructions.md`
    - 验证目标 Copilot 运行面是否真吃 path-specific instructions；如不吃，重说明内联到轻入口
- [ ] Copilot 资产重构：从 `Copilot/Skills/CN/COPILOT.md`（P4d seed）提炼 bootstrap 产物
  - 去掉 pilot-only 语气，对齐 sopify.json + bootstrap/install 叙事
  - 拆成轻入口 + 重说明两层
  - 原 COPILOT.md 保留为 source seed / reference
- [ ] 外部 repo 首次 bootstrap 的 diagnostics 输出（缺什么报什么）
- [ ] 错误路径覆盖：未初始化 / 版本不匹配 / payload 缺失
- [ ] status 命令适配外部 repo 场景
- [ ] 约束：只做 happy path + 常见错误路径，不动 deep installer doctor 逻辑

## S4: 发布链 + example

- [ ] release asset 结构定义
- [ ] install/bootstrap 命令文档
- [ ] examples/ 包含至少 1 个可独立跟随的端到端 demo
- [ ] README 更新（含接入步骤 + 视觉资产）

## S5: Smoke test + 验收

- [ ] 机器 smoke test：bootstrap → state write → handoff consume（端到端）
- [ ] 至少 1 个非 Sopify repo 走通全链路
- [ ] receipt + 蓝图同步 + history 归档
