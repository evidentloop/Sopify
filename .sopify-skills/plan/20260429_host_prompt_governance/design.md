# Design: Host Prompt Governance

> **定位**：`20260424_lightweight_pluggable_architecture` 总纲的独立治理包。
> **前置**：`20260428_action_proposal_boundary` P0 完成后暴露 4×510 行 prompt 的三层重复维护成本。
> **目标**：建立 prompt 作为 runtime contract 适配层的治理体系，实现渐进式披露，瘦身至核心层 ≤120 行 / 全量 ≤280 行，沉淀工程原则。

---

## 痛点分析

### P1 — 三重重复 (核心问题)

Gate/handoff 协议在 CLAUDE.md 中展开 3 次：

| 位置 | 行数 | 内容 |
|------|------|------|
| C3 说明块 (lines 142-158) | ~17 行 | gate 条件 + handoff dispatch 逐条展开 |
| 宿主接入约定 (lines 316-348) | ~32 行 | 同一协议换个角度重述 |
| 快速参考 mega-paragraph (line 503) | ~1 行(≈50 行压缩) | 第三次全量重述 |

**~100 行说同一件事：** gate → check 4 conditions → dispatch by required_host_action。

### P2 — 全量 dump (无渐进式披露)

对比参照：andrej-karpathy-skills CLAUDE.md 66 行 4 原则。核心哲学：
- **"If you write 200 lines and it could be 50, rewrite it"**
- 每条规则通过 "删掉后行为是否真的变化" 测试
- 不为假设场景写规则，不为不可能的错误写防御

当前 511 行里 A2 工具映射、A3 平台适配、runtime helper 路径表等，90% 请求根本用不到但每次占满 context window。

### P3 — CN/EN 同步靠人工

4 个 variant (Claude CN/EN, Codex CN/EN) 各 ~510 行，人工 diff 同步。pre-commit sync check 只验证对齐，不从单一源生成。

### P4 — 与 ADR-016 不对齐

ADR-016 确立 Protocol-first / Runtime-optional 三层架构。prompt 应体现这个分层，不应把 runtime 实现细节（helper 路径、gate 内部行为）和 protocol 层（目录约定、方案包结构）平铺在一起。

---

## 底层哲学

> 以下 3 条哲学从 Sopify 架构实践中提炼，待本包完成后沉淀至 blueprint。
> 它们是 prompt 治理的根基——prompt 的每一行都应服务于这 3 条哲学中的至少一条。

### 哲学 1: Loop-first (循环优先)

每个有意义的工作单元都是独立闭环：**produce → verify (isolated) → accumulate → produce**。

- produce: 按复杂度自适应选择快速修复 / 轻量迭代 / 完整方案
- verify: 在独立上下文中验证产出（非生产者自验；cross-review 是该模式的参考实现）
- accumulate: 沉淀到 blueprint/history，构建项目记忆
- loop: 新任务从积累出发，不从零开始

没有 verify 的 produce 是猜测。没有 accumulate 的 verify 是浪费。没有读回 accumulate 的 loop 是断裂的。

### 哲学 2: Wire-composable (线可组合)

独立 loop 通过**线**（机器契约 / 协议约定）组合成大 loop。Sopify 是串联这些小 loop 的线本身——control plane 不做节点内部的事，它负责串联和传递状态。

**线独立于 session / model / host：**
- 中断恢复：读取 handoff + run state → 不同 session 精确继续
- 模型接力：同一组 state 文件，不同 LLM 都能消费
- 宿主携带：`.sopify-skills/` 是纯文件协议，不绑定 runtime

**线的显隐程度可调：**

| 显隐 | 实现 | 适用 |
|------|------|------|
| 显式 (Runtime) | gate JSON → handoff JSON → checkpoint JSON | 确定性门控 / 审计 / 恢复 |
| 隐式 (Convention) | SKILL.md + 目录约定 + lifecycle 规则 | 轻量任务 / 新宿主接入 |

这与 ADR-016 Protocol-first / Runtime-optional 完全对齐——Protocol 定义节点的输入输出 schema，Runtime 是可选的"加固线"。

### 哲学 3: Surface-shared (面共享)

所有线共享一个知识面（blueprint / history）。知识面是跨 session / model / host 的**共享工作记忆**，不只是归档系统。

- 一条线的 accumulate 通过面成为任意线的 produce 输入
- 包括不同 session 中同一条线的续接（跨 session 接力的知识基底）
- blueprint 的读（先验构建）和写（知识沉淀）同等重要

**Sopify 的不可替代性 = 线 + 面的组合。** 宿主 2027 年可以原生做节点（plan/checkpoint），但跨 session/model/host 的线和面需要独立于宿主的文件协议承载——这就是 Protocol-first 的底层论据，也是总纲生存性测试的根基。

### 拓扑全景

```
Sopify = 一条大 loop，串联多个独立小 loop，共享一个知识面

大 loop ──→ [小 loop: 分析] ──→ [小 loop: 设计] ──→ [小 loop: 开发] ──→ [小 loop: 验证] ──→ accumulate ──→ ↩
               p→v→a→p              p→v→a→p              p→v→a→p              p→v→a→p
               (独立)                (独立)                (独立)                (独立)
                                     ↑                                           ↑
                              线 = gate/handoff                           cross-review
                              (显式 or 隐式)                              (独立验证节点)

所有 accumulate 写入同一个知识面：blueprint / history
所有 produce 从同一个知识面读取先验
线可在不同 session / model / host 间中断恢复
```

---

## Prompt 工程原则

> **Prompt 是 runtime contract 的适配层，不是事实源。**
> 每条原则都服务于底层哲学（Loop-first / Wire-composable / Surface-shared）。

7 条工程原则（沉淀至 `.sopify-skills/blueprint/prompt-governance.md`）：

0. **Loop-aligned** — prompt 的每一节都服务于 produce→verify→accumulate→produce 循环中的至少一环。不服务于任何一环的内容删除。
1. **Prompt 不定义机器契约** — 引用 runtime 输出，不在 prompt 里展开算法
2. **Prompt 不维护两份路由表** — 一处定义，其他处引用
3. **每条规则通过删除测试** — 删掉这行，宿主行为是否真的变化？不变则删
4. **渐进式披露** — 按触发路径分层加载，不全量 dump
5. **单源生成** — 从模板生成 4 个 variant，不手工同步
6. **行数硬上限** — 核心层 ≤ 120 行，含扩展层 ≤ 280 行

---

## 渐进式披露架构

对齐 ADR-016 三层模型 + 知名项目渐进式写法：

```
Layer 0 — Protocol (始终加载, ≤120 行)
├── 底层公理 (Loop-first / Wire-composable / Surface-shared) (~20 行)
├── 角色定义 + 路由入口表 (~20 行)  ← 一处定义，不重复
├── 输出格式约束 (~25 行)
├── 工作流模式 + 复杂度判定 (~20 行)
├── 目录结构 + 生命周期 (含"读"环节) (~20 行)
└── 配置默认值 (~15 行)  ← 去掉 multi_model.* 后

Layer 1 — Gate Contract (gate 触发时注入, ~40 行)
├── gate 4 条件校验 (~10 行)  ← 一次性定义
├── required_host_action dispatch 表 (~20 行)
└── ActionProposal capability 声明 (~10 行)

Layer 2 — Phase Execution (进入具体阶段时注入, ~30 行/阶段)
├── P1 需求分析流程 + 输出模板
├── P2 方案设计流程 + 输出模板
└── P3 开发实施流程 + 输出模板

Layer 3 — Reference (按需查阅, 不注入 prompt)
├── runtime helper 路径表 → 迁入 project.md 或 README
├── 平台适配 (A3) → 迁入 project.md
├── 工具映射 (A2) → 宿主自带，不需要 prompt 重复
└── 配置项说明 → 迁入 sopify.config.yaml 注释
```

**预期效果：**
- Layer 0 alone: ~120 行 (覆盖 80% 场景)
- Layer 0 + Layer 1: ~160 行 (覆盖 95% 场景)
- 全量 (L0+L1+L2): ~280 行 (对比当前 511 行, -45%)
- Layer 3 不进 prompt，迁到文档

---

## CN/EN 同步方案

**单源模板 + 构建生成：**

```
prompts/
├── base.template.md          # 共享骨架 (Layer 0 + 占位符)
├── gate-contract.partial.md  # Layer 1
├── phase-*.partial.md        # Layer 2
├── vars/
│   ├── claude-cn.yaml        # 变量: lang, encoding, tool_mapping
│   ├── claude-en.yaml
│   ├── codex-cn.yaml
│   └── codex-en.yaml
└── build-prompts.py          # 模板 + 变量 → 4 个 CLAUDE.md/AGENTS.md
```

差异维度只有 3 项：
- 语言 (zh-CN / en)
- 宿主工具名 (Read/Grep/Edit vs cat/grep/apply_patch)
- 入口文件名 (CLAUDE.md vs AGENTS.md)

---

## 与总纲对齐

- **ADR-016 Protocol-first**: prompt 分层 = Protocol 层始终加载 + Runtime 细节按需注入
- **ADR-013 产品定位**: prompt 只声明 control plane 能力，不展开执行细节
- **轻量化可插拔**: prompt 本身也是可插拔的——Layer 1/2 可独立更新不影响 Layer 0

---

## 执行范围

### Phase 1: 审计与原则沉淀
- 逐行标注 CLAUDE.md 每个区块：重复 / 唯一事实源 / 可迁移 / 可删除
- 撰写 `.sopify-skills/blueprint/prompt-governance.md` (6 条原则)
- 用户确认

### Phase 2: 渐进式披露重构
- 实现分层结构 (Layer 0 ≤ 120 行)
- 重构 Claude CN prompt 为 Layer 0
- 验证 runtime 行为不变（全量测试通过）
- 1 轮 dogfood

### Phase 3: 单源生成
- 实现 `build-prompts.py` 模板引擎
- 从模板重新生成 4 个 variant
- 集成到 pre-commit hook（替代当前 sync check）
- 验证生成结果与手工版功能一致

### Phase 4: 准入脚本
- `check-prompt-governance.py`：
  - 行数上限检查 (Layer 0 ≤ 120, 全量 ≤ 280)
  - 必需区块存在性检查
  - 重复模式检测（同一 key 出现 >1 次则报警）
  - 与 runtime gate contract 版本一致性检查

## 不做

- 不改 runtime gate / engine / router 逻辑
- 不改机器契约定义（只改 prompt 中的引用方式）
- 不合并到 legacy_feature_cleanup 包
- 不在本包实施前删除 ~compare（那是 cleanup 包的事）
