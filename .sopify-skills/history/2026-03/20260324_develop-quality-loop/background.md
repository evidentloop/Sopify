# 变更提案: develop-quality-loop

## 需求背景

当前 Sopify 的差异化已经不在“能不能做 plan / handoff / checkpoint”，而在“能不能默认把代码改对、验证掉、把失败说清楚”。这一层目前仍有明显缺口：

1. `Codex/Skills/*/sopify/develop/references/develop-rules.md` 只要求“验证修改正确性”，但没有定义验证命令发现顺序、无命令时如何显式降级、失败后是否重试、以及什么时候应该退回 plan review。
2. `runtime/engine.py` 与 `runtime/develop_checkpoint.py` 已经具备 `continue_host_develop` / `review_or_execute_plan` 的恢复骨架，但 develop 阶段缺少一套稳定的质量闭环 contract，失败原因仍容易停留在自由文本。
3. `runtime/replay.py`、`current_handoff.json`、`current_run.json` 目前主要记录 route、decision、compare 与 execution gate；develop task 的验证结果、重试次数、根因分类与 review 结论还没有明确的落盘方式。
4. 结果是 Sopify 的 runtime 契约很强，但在“帮用户写代码”最关键的开发态体验上，还没有把契约优势转成用户可感知的默认质量保障。

这正是 steering plan 已经明确的下一条优先实现线：不先做子智能体平台，不先做分发，而是先补 develop 质量循环。

评分:
- 方案质量: 8.5/10
- 落地就绪: 8/10

评分理由:
- 问题定义、参考来源、影响文件区和现有 runtime 恢复骨架都已经明确，适合直接拆成实现任务；
- 但 v1 仍需要主动收窄边界，避免把“验证循环”扩成全自动测试平台或新的 meta runtime。

## 变更内容

1. 为 develop 阶段建立一个单代理可落地的质量循环：`任务执行 -> 验证命令发现 -> 验证执行 -> 两阶段复审 -> 结构化记录`。
2. 把验证命令发现顺序写实为显式 contract：优先 `project.md` 的长期约定，再看项目原生脚本/配置，最后才进入可见降级，而不是静默跳过。
3. 定义验证失败后的最小自动处置：最多重试一次；连续失败时输出结构化根因分类，并根据分类决定继续 develop 还是回退到 plan review。
4. 把质量结果暴露到 handoff / replay / state，让宿主、复盘与后续恢复都能看到“做了什么验证、为什么失败、下一步该怎么走”。

## 范围边界

本 plan 的 v1 范围仅包含：

1. `develop` 规则与镜像文档：
   - `Codex/Skills/CN/skills/sopify/develop/`
   - `Codex/Skills/EN/skills/sopify/develop/`
   - `Claude/Skills/CN/skills/sopify/develop/`
   - `Claude/Skills/EN/skills/sopify/develop/`
   - `runtime/builtin_skill_packages/develop/skill.yaml`
2. develop 执行与恢复相关 runtime：
   - `runtime/engine.py`
   - `runtime/develop_checkpoint.py`
   - `runtime/handoff.py`
   - `runtime/replay.py`
   - `runtime/state.py`
3. 与质量结果相关的测试面：
   - `tests/test_runtime_engine.py`
   - `tests/test_runtime_replay.py`
   - 视 contract 变更需要，补 `tests/test_runtime_summary.py` / `tests/test_runtime_execution_gate.py`
4. 项目级长期约定入口：
   - `.sopify-skills/project.md`

## 非目标

本 plan 明确不包含：

1. 原生子智能体编排、hook-first 验证框架，或 Ralph Loop / Break-Loop 的完整实现复刻。
2. `runtime_gate` 核心 contract 改造、graceful degradation 设计、distribution / installer 产品化。
3. 多宿主 scaffold 扩张、lightweight skill registration、更多 plan lifecycle 元系统增强。
4. 把原始 stderr / stack trace 全量写入 durable state；v1 只落结构化摘要与下一步动作。

## 成功标准

这条实现线完成后，至少要满足以下结果：

1. 每个 develop task 在被标记完成前，至少同时有明确的 `verification_source`（`project_contract / project_native / not_configured` 之一）和 `result`（`passed / retried / failed / skipped / replan_required` 之一）；若未实际执行验证，必须附 `reason_code`。
2. 验证失败不会无限重试；最多重试一次，第二次失败后必须输出结构化根因分类，例如：
   - `logic_regression`
   - `environment_or_dependency`
   - `missing_test_infra`
   - `scope_or_design_mismatch`
3. develop 阶段新增两阶段复审：
   - `spec_compliance`
   - `code_quality`
4. handoff / replay / session 恢复时都能看到最近一次质量结果，而不是只能从自由文本猜测。
5. v1 在没有原生子智能体平台的前提下也可落地，不引入新的默认绕过入口。

## 风险评估

- 风险: 验证命令发现做得过宽，容易把 heuristics 变成新的不透明黑盒。
  - 缓解: v1 只支持有限顺序：`project.md verify` > 项目原生脚本/配置 > 可见降级；不追求“全栈自动识别”。

- 风险: 把验证失败都当成“继续修”会形成低质量重试循环。
  - 缓解: 固定最多一次重试；第二次失败必须分类，并允许 `scope_or_design_mismatch` 直接回到 `review_or_execute_plan`。

- 风险: 质量结果记录过重，导致 state / replay 变成日志转储。
  - 缓解: durable artifact 只保留命令、状态、摘要、分类、下一步动作；原始输出只在当前执行上下文短暂使用。

- 风险: develop 规则、runtime 行为和测试断言三处口径漂移。
  - 缓解: 把“规则镜像 + runtime contract + tests”作为同一个 implementation group 落地，不接受单边更新。

## 实施顺序备注

上游 `20260320_helloagents_integration_enhancements` 已归档，原先的实施顺序前置依赖已满足；但本 plan 仍应先通过 pre-flight，补齐执行范围、统一 contract 命名并确认首个落地切片，再进入实际 implementation。
