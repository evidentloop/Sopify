# 变更提案: 规划流程与方案包物化解耦

## 需求背景
当前 runtime 把“需要 planning”与“立即创建 `.sopify-skills/plan/...`”混成同一个动作，导致两类真实问题：

1. 复杂请求一旦被路由到 `workflow / light_iterate`，就会直接物化 plan package
2. “给我方案建议”“这个需求怎么拆”“为什么生成了 plan”“不要再生成 plan”这类请求，缺少稳定的 planning / consult / materialization 边界

这不是单纯的 router 关键词问题，更深一层的根因是当前 `should_create_plan` 同时承载了两层语义：

1. 进入 planning 流程
2. 立即写 plan artifact

因此本 plan 的目标不是只改词表，而是把 planning intent 与 plan package materialization 拆成两个 host-visible contract。

这是一份独立修正 plan，不并入 `20260326_phase1-2-3-plan` 的 program-level 路线；后者继续只承载推广方向总纲、优先级与后续大项拆分。

## 变更内容
本 plan 负责定义并收口以下内容：

1. 在 runtime contract 中引入 `plan_package_policy = none | confirm | immediate`
2. 新增 proposal 阶段状态文件 `current_plan_proposal.json`
3. 新增独立停点 `confirm_plan_package`
4. 新增 proposal pending 路由与确认 / 修订 / 取消语义
5. 明确 `~go plan` 只跳过“是否建包”确认，不跳过 clarification / decision

本 plan 不直接处理：

1. 风险自适应打断本身
2. Ghost / Suspend / Side Task
3. `light` 级任务的多停点 UX 优化

## 影响范围
- 模块:
  - `runtime/_models/core.py`
  - `runtime/state.py`
  - `runtime/router.py`
  - `runtime/engine.py`
  - `runtime/handoff.py`
  - `runtime/checkpoint_request.py`
  - `runtime/checkpoint_materializer.py`
  - `runtime/gate.py`
  - `runtime/entry_guard.py`
  - `runtime/output.py`
  - `runtime/plan_orchestrator.py`
  - `tests/test_runtime_router.py`
  - `tests/test_runtime_engine.py`
  - `tests/test_runtime_gate.py`
  - `Codex/Skills/CN/AGENTS.md`
  - `Codex/Skills/EN/AGENTS.md`
  - `Claude/Skills/CN/CLAUDE.md`
  - `Claude/Skills/EN/CLAUDE.md`
- 文件边界:
  - 新增 session-scope proposal state
  - 扩展 checkpoint 与 handoff contract
  - 不改已有 plan artifact 模板内容

## 风险评估
- 风险: 只修 router 词表，不拆 planning/materialization contract，会在新的模糊复杂请求上再次误生成 plan
  - 缓解: 在 `RouteDecision` 与 engine 之间显式拆出 `plan_package_policy`

- 风险: 新增 `confirm_plan_package` 但没有 proposal pending classifier，`继续 / next` 会卡死
  - 缓解: 单独设计 `_classify_pending_plan_proposal()`，不复用 `resume_active`

- 风险: proposal 展示的路径与 confirm 后真实落盘路径漂移，破坏用户心智
  - 缓解: proposal 生成时保留 `reserved_plan_id`，并强约束 `proposed_path` confirm 前后不变

- 风险: 把“同意建包”“评审 plan”“执行前确认”合并为一个停点，导致状态机语义混乱
  - 缓解: 明确保留三个独立停点：
    - `confirm_plan_package`
    - `review_or_execute_plan`
    - `confirm_execute`
