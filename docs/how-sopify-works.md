# Sopify 如何工作

## 设计来源：Harness Engineering

Sopify 借鉴 harness engineering 的设计思路，但不把它作为仓库首页定位。这里说明的是设计来源，不是产品口号。

<div align="center">
<img src="../assets/sopify-harness-cn.png" width="800" alt="Harness Engineering → Sopify 映射" />
</div>

官方参考：[`Harness engineering: leveraging Codex in an agent-first world`](https://openai.com/zh-Hans-CN/index/harness-engineering/)

## 主工作流

<div align="center">
<img src="../assets/sopify-workflow-cn.svg" width="800" alt="Sopify 主工作流" />
</div>

工作流要点：

- 每次进入 Sopify 前都先经过 runtime gate
- 只有代码任务才进入复杂度分流
- 标准主链路优先依赖 handoff contract，而不是猜测 `Next:` 文案

### Checkpoint 暂停与恢复

工作流图中的 checkpoint 节点会在两种场景暂停执行：

- `answer_questions` 用于补事实，不提前物化正式 plan
- `confirm_decision` 用于拍板分叉，确认后再恢复默认 runtime 入口

## 目录结构与层级

```text
.sopify-skills/
├── blueprint/                   # L1 长期蓝图（git tracked）
│   ├── README.md
│   ├── background.md
│   ├── design.md
│   └── tasks.md
├── plan/                        # L2 活跃方案（git tracked）
│   ├── _registry.yaml           # 本地 machine registry（继续 ignored）
│   └── YYYYMMDD_feature/
├── history/                     # L3 已归档方案（git tracked）
│   ├── index.md
│   └── YYYY-MM/
├── state/                       # 运行态 machine truth（始终 ignored）
│   ├── current_handoff.json
│   ├── current_run.json
│   ├── current_decision.json
│   ├── current_gate_receipt.json
│   ├── last_route.json
│   └── sessions/<session_id>/...   # 并发 review 隔离
├── user/
│   ├── preferences.md
│   └── feedback.jsonl
└── project.md
```

层级说明：

- `blueprint/` 承载长期知识与稳定契约
- `plan/` 保存当前工作方案，不等同于长期蓝图；目录本身纳入版本管理，但 `_registry.yaml` 继续保持本地忽略
- `history/` 只存已收口方案，并纳入版本管理
- `state/` 是宿主与 runtime 的本地运行态数据层

## 附录：Plan 生命周期

<div align="center">
<img src="../assets/sopify-plan-lifecycle-cn.png" width="800" alt="Sopify Plan 生命周期" />
</div>

附录只用于说明维护者视角的收口过程；普通用户理解主工作流即可。
