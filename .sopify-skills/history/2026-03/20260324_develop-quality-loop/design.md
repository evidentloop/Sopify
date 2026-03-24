# 技术设计: develop-quality-loop

## 技术方案

- 核心目标:
  - 给 `develop` 阶段补一个默认开启、单代理可落地的质量闭环；
  - 把“验证是否跑过、失败为什么、是否该退回 plan review”从自由文本提升为机器可消费的结构化结果；
  - 保持 Sopify 现有的 `execution_gate + handoff + develop_checkpoint + replay` 主链不变。
- 实现要点:
  - 先写清 contract，再改 runtime；
  - 先解决“怎么发现验证、怎么处理失败、怎么记录结果”，不扩到完整自动化平台；
  - 失败时优先给出下一步动作，而不是仅给出一段错误文本。

## 设计原则

1. `develop-quality-loop` 是执行纪律增强，不是新的 runtime 子系统。
2. v1 不依赖原生子智能体或 hooks；现有 `continue_host_develop` 主链即可落地。
3. 机器事实仍优先存在 handoff / replay / state 中，技能文档只是规则镜像，不替代 runtime contract。
4. 默认 fail-visible，不允许“没有跑验证但像是已经验证过”的静默成功。

## 1. 验证命令发现 contract

### 1.1 发现顺序

v1 统一按以下优先级发现验证命令：

1. `.sopify-skills/project.md` 的 `verify` 长期约定
   - 这是项目级单一事实源，适合声明“本仓库默认怎么验证 develop 改动”。
2. 项目原生脚本/配置
   - 例如 `package.json scripts`
   - `pyproject.toml` / `pytest` 约定
   - `Makefile` / `justfile` 中稳定的测试目标
3. 显式降级
   - 如果没有稳定命令，不能静默当作成功；
   - 必须返回 `not_configured` 或 `skipped_with_reason`，并写明原因。

### 1.2 v1 输出字段

无论命令最终是否可执行，discover 步骤都应产生统一结果，最少包含：

1. `verification_source`
   - `project_contract`
   - `project_native`
   - `not_configured`
2. `command`
3. `scope`
4. `reason_code`（当无法执行或必须跳过时）

命名约束：

1. discover 阶段统一使用 `verification_source`，不再混用 `discovery_source`
2. `verification_source` 只表达来源，不复用为结果态
3. `configured / discovered / skipped_with_reason` 这类自然语言别名不进入 runtime contract

### 1.3 边界

1. v1 只覆盖少量稳定来源，不追求扫描所有可能的脚本生态。
2. 没有稳定命令时允许降级，但必须对宿主与 replay 可见。
3. `project.md` 一旦显式配置 verify 约定，应高于临时 heuristics。

## 2. 任务级验证与失败处理

### 2.1 质量循环时机

每个 develop task 在被标记 `[x]` 之前，按以下顺序处理：

1. 完成本 task 的代码修改
2. 发现验证命令
3. 执行验证
4. 进行两阶段复审
5. 只有通过后才把 task 标记为完成

补充约束：

1. task 完成态不是主观判断，而是 task-level machine contract
2. 只有当本轮质量结果里存在 `verification_source`、`command`、`result` 时，才允许把 task 标记为完成
3. “应该没问题”“改动很小先跳过验证”都属于未验证，不应进入完成态
4. task-level 结果态统一为 `passed / retried / failed / skipped / replan_required`；`verification_source` 与 `result` 是两套不同字段，不混用

### 2.2 重试策略

v1 固定最多重试一次：

1. 第一次验证失败：
   - 允许带失败上下文做一次修复重试
2. 第二次仍失败：
   - 停止自动重试
   - 进入结构化根因分类
   - 决定继续 develop、提示环境问题，或回退到 plan review

### 2.3 根因分类

v1 先固定 4 类，避免无限自由发挥：

1. `logic_regression`
2. `environment_or_dependency`
3. `missing_test_infra`
4. `scope_or_design_mismatch`

处理口径：

1. `logic_regression`
   - 仍可停留在 `continue_host_develop`
2. `environment_or_dependency`
   - 可见标注“代码未必有问题，但当前环境不能证明通过”
3. `missing_test_infra`
   - 允许保持任务未验证完成，并把补测要求写入结果
4. `scope_or_design_mismatch`
   - 不继续盲修，优先回到 `review_or_execute_plan` 或触发 develop checkpoint

补充约束：

1. `root_cause` 不是每个 task 都需要的通用字段
2. 只有进入失败收口或重试路径时，才要求 `root_cause` 必须存在
3. 因此“先改改试试”不属于可接受的失败处理路径；至少要先把失败归到已有根因分类之一

## 3. 两阶段复审

### 3.1 Stage A: spec compliance

这一层回答“是不是做对了当前 task”，最少检查：

1. 是否满足任务目标与边界
2. 是否没有明显 overbuild / underbuild
3. 是否引入了新的用户决策分叉或范围变化

若发现范围已变，不能只在实现里硬顶过去，应优先复用 `runtime/develop_checkpoint.py` 的现有分叉能力。

### 3.2 Stage B: code quality

这一层回答“做法是否可接受”，最少检查：

1. 风格与现有代码一致
2. 没有显著可预见的安全/稳定性回退
3. 修改面与 task 规模匹配
4. 关键注释、测试、知识同步是否达到当前任务所需最低标准

### 3.3 与 v1 边界的关系

1. 两阶段复审先作为 develop 规则与 runtime 结果的一部分落地；
2. 不要求独立 reviewer agent；
3. 也不要求像 Superpowers 那样引入完整两阶段子智能体审查平台。

当独立 code review agent 可用时（如 `sopify-code-review`），Stage 1/2 可升级为隔离 reviewer dispatch，仅传递最小必要上下文，不继承实现者历史；当前 v1 架构不需要改动，只替换执行方式。

## 4. handoff / replay / state 记录

### 4.1 handoff

`current_handoff.json.artifacts` 需要新增 develop 质量结果摘要，至少能回答：

1. 最近处理的 `task_refs`
2. `verification_source`
3. `command`
4. `result`
5. `retry_count`
6. `root_cause`
7. `review_result`
8. 下一步是继续 develop，还是回到 plan review / 用户拍板

这里记录的是摘要，不是原始日志。

### 4.2 replay

`runtime/replay.py` 需要支持 develop 质量事件，让 `session.md` / `breakdown.md` 不再只看到 route/decision，还能看到：

1. 哪个 task 跑了验证
2. 为什么被判定为通过、重试或失败
3. review 是因为 spec 还是 code quality 挡下来的

同时沿用现有脱敏策略，不把 secret-bearing 输出直接写进 replay。

### 4.3 state / resume

`current_run.json` 继续保留 coarse-grained machine truth，不承载详细日志。

如果 develop 中途需要 checkpoint：

1. `resume_context.verification_todo`
2. `resume_context.working_summary`
3. `resume_context.task_refs`
4. `resume_after`

这些已有字段就足够承载“恢复后还差什么验证 / review”，尽量不新增平行状态文件。

## 5. 可能影响的实现面

### 5.1 规则镜像

需要同步更新：

1. `Codex/Skills/CN/skills/sopify/develop/references/develop-rules.md`
2. `Codex/Skills/EN/skills/sopify/develop/references/develop-rules.md`
3. `Claude/Skills/CN/skills/sopify/develop/references/develop-rules.md`
4. `Claude/Skills/EN/skills/sopify/develop/references/develop-rules.md`

### 5.2 runtime

优先关注：

1. `runtime/engine.py`
2. `runtime/develop_checkpoint.py`
3. `runtime/handoff.py`
4. `runtime/replay.py`
5. `runtime/state.py`

### 5.3 tests

优先关注：

1. `tests/test_runtime_engine.py`
2. `tests/test_runtime_replay.py`
3. 视 contract 变更需要，补 `tests/test_runtime_summary.py`
4. 若执行前/恢复前 contract 受影响，再看 `tests/test_runtime_execution_gate.py`

## 6. 不纳入 v1 的内容

1. 不新增 `runtime_gate` 的 degrade contract。
2. 不把 `status/doctor` 并入本 plan。
3. 不做多宿主或原生 subagent capability 检测。
4. 不做广覆盖自动验证发现器；先做小而稳的 contract。

## 7. 交付判定

本 plan 的 implementation 完成时，至少应能证明：

1. develop 规则不再只有“验证修改正确性”这类抽象要求；
2. runtime 能稳定表达验证发现、一次重试、根因分类与两阶段复审结果；
3. handoff / replay / state 对 develop 质量结果可见；
4. 整个闭环仍兼容现有 `execution_gate` 与 `develop_checkpoint` 主链。
