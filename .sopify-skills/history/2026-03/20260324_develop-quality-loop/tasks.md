---
plan_id: 20260324_develop-quality-loop
feature_key: develop-quality-loop
level: standard
lifecycle_state: archived
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: true
---

# 任务清单: develop-quality-loop

## Group 0 — Pre-flight 准入检查

- [x] 0.1 上游 `20260320_helloagents_integration_enhancements` 已归档，原先的实施顺序前置依赖已满足
- [x] 0.2 在进入 Group 1 前，复核本 plan 是否已经达到 implementation-ready：执行范围、统一 contract 命名、首个落地切片与验证方式都已明确；本轮确认首个落地切片就是四套 develop 规则镜像 + `runtime/builtin_skill_packages/develop/skill.yaml`

**Gate — Group 0 完成后：**
- [x] 0.G 0.2 已通过，进入 Group 1 的实际实施

## Group 1 — 固化 v1 contract 与规则镜像

- [x] 1.1 在 `Codex/Skills/*/sopify/develop/references/develop-rules.md` 与 `Claude/Skills/*/sopify/develop/references/develop-rules.md` 中固化 `verify` contract 的最小字段、统一命名与写法边界：统一使用 `verification_source / command / scope / result / reason_code / retry_count / root_cause / review_result`，不再混用 `discovery_source / status / configured / discovered` 等别名，并明确 `.sopify-skills/project.md verify` 只作为后续长期约定落点
- [x] 1.2 在 `Codex/Skills/*/sopify/develop/references/develop-rules.md` 与 `Claude/Skills/*/sopify/develop/references/develop-rules.md` 中，把“验证修改正确性”改成显式质量循环：验证发现、验证执行、一次重试、根因分类、两阶段复审，并用简短镜像说明固化“无验证证据不算完成”及少量高频逃逸路径（如 overbuild / underbuild / “应该没问题”）
- [x] 1.3 复核 `runtime/builtin_skill_packages/develop/skill.yaml` 的描述与 contract version 是否仍与新规则一致；本轮更新描述并保持 `contract_version: "1"`，避免 skill 元数据先于 runtime contract 升级

**Gate — Group 1 完成后：**
- [x] 1.G develop 的文字规则已经存在单一口径，且显式包含验证发现顺序、统一 contract 命名、重试上限、根因分类、两阶段复审四节，不再依赖聊天上下文补充解释

验收标准:

- Codex / Claude / CN / EN 四套镜像不再各自发挥
- v1 contract 明确说明“无验证命令时如何可见降级”
- 规则文本不再依赖聊天上下文解释

## Group 2 — 接入 task-level 质量循环

- [x] 2.1 在 `runtime/engine.py` 中为 develop task loop 加入验证命令发现与执行挂点，不绕过现有 `execution_gate` / `develop_checkpoint` 主链，并把 `verification_source / command / result` 作为 task 完成前必须具备的 machine contract；本轮通过 `continue_host_develop` handoff + quality helper 形成 host-owned task loop 挂点
- [x] 2.2 实现验证发现优先级：`.sopify-skills/project.md verify` > 项目原生脚本/配置 > `not_configured / skipped_with_reason`
- [x] 2.3 实现“最多一次重试”与结构化根因分类：`logic_regression` / `environment_or_dependency` / `missing_test_infra` / `scope_or_design_mismatch`，并要求失败/重试路径上必须存在 `root_cause`
- [x] 2.4 当失败本质是范围变化或设计分叉时，复用 `runtime/develop_checkpoint.py` 回到 `review_or_execute_plan` 或 `confirm_decision`，而不是继续盲修

**Gate — Group 2 完成后：**
- [x] 2.G develop loop 已能表达 `passed / retried / failed / skipped / replan_required` 等稳定结果，且不存在静默跳过与无限重试

验收标准:

- 验证是否执行过、为何失败、下一步怎么走，都有机器可读结果
- `scope_or_design_mismatch` 不会被错误地当成“再试一次”
- v1 仍可在单代理模式下成立

## Group 3 — 两阶段复审与结果记录

- [x] 3.1 定义 `spec_compliance` 与 `code_quality` 两阶段复审的最小检查项，并同步到 develop 规则镜像
- [x] 3.2 扩展 `runtime/handoff.py` / `runtime/engine.py` 产出的 artifacts，使其至少包含最近一次 task 的 `verification_source / command / result / retry_count / root_cause / review_result`
- [x] 3.3 扩展 `runtime/replay.py` 的 develop 事件与 `session.md` / `breakdown.md` 渲染，让复盘能直接看到质量闭环结果
- [x] 3.4 复核 `runtime/state.py` 与 checkpoint `resume_context` 的最小字段，保证恢复链路能看到 `task_refs / working_summary / verification_todo / resume_after`

**Gate — Group 3 完成后：**
- [x] 3.G `current_handoff.json.artifacts` 已包含 `task_refs / verification_source / command / result / retry_count / root_cause / review_result`，`replay` 至少新增一条 develop 质量事件，且 checkpoint `resume_context` 保留 `verification_todo`

验收标准:

- handoff 对宿主可消费
- replay 对复盘可消费
- state 对恢复可消费

## Group 4 — 测试补齐

- [x] 4.1 在 `tests/test_runtime_engine.py` 中补 discovery priority、一次重试、根因分类、回退 plan review、无命令显式降级等行为测试
- [x] 4.2 在 `tests/test_runtime_replay.py` 中补 develop 质量事件渲染与脱敏测试
- [-] 4.3 summary / execution gate 可见面本轮未新增 develop 质量字段，因此不单独补 `tests/test_runtime_summary.py` 与 `tests/test_runtime_execution_gate.py`

**Gate — Group 4 完成后：**
- [x] 4.G 新质量循环由稳定测试覆盖，且不回归现有 `execution_gate` / `develop_checkpoint` / replay contract；已使用 Python 3.11.13 执行 `tests.test_runtime_engine` 与 `tests.test_runtime_replay`

验收标准:

- 关键分支都能通过 deterministic tests 复现
- 失败路径与恢复路径都有断言
- contract 变化有对应测试兜底

## Group 5 — 文档与知识同步

- [x] 5.1 当 verify contract 稳定后，再把长期约定写入 `.sopify-skills/project.md`
- [x] 5.2 仅在 develop 质量 contract 成为长期项目规则时，更新 `.sopify-skills/blueprint/` 或 README 面向用户的说明；本轮同步到 `blueprint/design.md` 的 develop callback 长期事实
- [x] 5.3a 冻结 About / README `为什么选择 Sopify` 的顶层叙事口径：从“功能列表”切到“认知偏移 -> 机器可读协议 -> 可积累文本资产 -> cross-session continuity”的价值链，并确保不抢先承诺未落地行为

  5.3a 落版口径冻结：

  - About 固定使用英文：`Turn one-shot AI coding into a recoverable, reviewable, cross-session workflow for long-lived repos.`
  - README 中文副标题改为“面向长期项目的可恢复、可复盘、可沉淀 AI 编程工作流”；README_EN 副标题改为 `A recoverable, reviewable, cross-session AI coding workflow for long-lived repos`
  - 首页主术语统一使用“机器可读协议 / machine-readable protocols”，不再把“机器契约 / machine contracts”作为首屏主术语；“框架 / framework”一并从副标题移除
  - “长期项目 / long-lived repos”按分层表达：About 结尾限定，副标题显式定位，Why 第 1 段用“随着仓库增长...”隐含带出场景，“什么时候最有价值”再显式校准预期
  - `为什么选择 Sopify` 固定重写为三段：问题段先讲“决策依据散落在对话里，用户认知、AI 理解和代码现状会逐渐偏离”；机制段只讲用户能感知到的后果，明确“缺事实时停下来补事实、需要拍板时等待确认、中断后从当前状态恢复”，并补一条诚实声明“基础过程记录会自动产生，长期复利取决于是否持续 finalize 和维护知识资产”；结果段统一收口到“工作可以稳定推进、可复盘、可延续，下次从当前状态继续，而不是重新发现上下文”
  - `核心特性 / Key Features` 版位替换为“你会实际感受到什么 / What You'll Actually Notice”，固定只写用户感受，不写 handoff / checkpoint / manifest-first / runtime gate 等内部术语；建议 4 条分别覆盖：关键节点不会由 AI 自行拍板、中断后可以从上次停点恢复、方案/历史/蓝图沉淀为项目资产、简单任务保持轻量而复杂任务再进入完整流程
  - Why 段下方新增“什么时候最有价值”，不使用“更适合谁”；明确“长期维护的复杂仓库、需要跨 session 连续性和可审计性”与“愿意维护 plan / blueprint / finalize 收口的工作流”两类高价值场景，并补一句“如果只做一次性小改动、不关心后续沉淀，收益会明显降低”
  - 原 Why 段中的任务类型对比表迁移到 Quick Start，位置固定为“安装说明之后、首次使用示例之前”；迁移后改成入口引导表，标题建议为“根据任务规模选入口 / Choose an entry by task size”，去掉“传统方式”对比列，只保留“任务类型 | Sopify 处理方式”
  - 当前 README / README_EN 在顶层特性后的 design rationale 自述直接删除，不留替换句；设计哲学、Harness Engineering、manifest-first、handoff/checkpoint/runtime gate 等解释统一收拢到 `docs/how-sopify-works.md` 与 `docs/how-sopify-works.en.md`
  - 宿主支持说明移到安装章节，多模型对比留在独立章节，不再占用顶层叙事位
  - 禁止承诺口径固定为：不写“防止/消除偏移”，统一写“降低偏移、让偏移可见/可恢复/可纠正”；不写“机器强制执行、无法绕过”，统一按“机器可读协议”表述；不写“知识会自动越用越好”，必须保留“长期复利依赖 finalize 与维护”的限定；不把“自适应路由”写成首页第一卖点，只写成降低使用成本的辅助能力
- [x] 5.3b 按 5.3a 的冻结口径实际更新 `README.md / README_EN.md`：完成副标题、Why 三段、“你会实际感受到什么”、“什么时候最有价值”、Quick Start 入口表迁移与 design rationale 清理，并在完成后回填验收

**Gate — Group 5 完成后：**
- [x] 5.G 技能规则、runtime contract、测试与知识库同步口径一致，且 implementation order 未漂移

验收标准:

- 长期文档只沉淀稳定约定
- README 不抢先承诺尚未落地的行为
- 不把 implementation order 和 planning order 混回一起

## 明确延后项

- [-] 6.1 原生子智能体编排、SubagentStop hook、完整 Ralph Loop / Break-Loop 复刻
- [-] 6.2 `runtime-gate-degradation-mode`
- [-] 6.3 `status/doctor` 与 host capability registry 实现
- [-] 6.4 `one-liner-distribution` 与安装渠道产品化
- [-] 6.5 面向所有生态的广覆盖自动验证发现器
