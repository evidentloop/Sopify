# 技术设计: 规划流程与方案包物化解耦

## 技术方案
- 核心目标:
  - 把 `planning intent` 与 `plan package materialization` 拆成不同 contract
  - 让非显式规划请求可以先分析 / 澄清 / 设计分叉，再确认是否建包
  - 保持已有 `review_or_execute_plan` 与 `confirm_execute` 语义不变
- 实现要点:
  - 用 `plan_package_policy` 取代 `should_create_plan` 的双重语义
  - 用 `current_plan_proposal.json` 承载 proposal pending 的机器事实
  - 用 `confirm_plan_package` 作为建包前停点
- 文档定位:
  - 本 plan 独立于 `20260326_phase1-2-3-plan`
  - 不占用 program plan 中的 `A / D / B1 / B2 / C / B3` 拆分槽位

## 设计原则

### 1. planning 不等于 materialization
进入 `workflow / light_iterate / plan_only` 只表示需要规划，不默认表示要立刻创建 `.sopify-skills/plan/...`

### 2. 显式建包与非显式规划必须分开
显式建包：

1. `~go plan`
2. `new plan / create plan / 新建 plan`
3. 明确要求“写入方案包 / 写到 background.md design.md tasks.md / 写入 .sopify-skills/plan/...”

非显式规划：

1. `给我方案建议`
2. `这个需求怎么拆`
3. `分析下这个方向`
4. `为什么生成了 plan`
5. `不要再生成 plan`

### 3. 建包确认不替代其他 checkpoint
`~go plan` 只跳过 `confirm_plan_package`，不跳过：

1. `answer_questions`
2. `confirm_decision`
3. `confirm_execute`

### 4. 已有停点语义不污染

1. `confirm_plan_package`：确认是否物化方案包
2. `review_or_execute_plan`：plan artifact 已存在，等待评审或继续执行
3. `confirm_execute`：develop 前最后一次确认

## 合约设计

### A. RouteDecision 合约
新增字段：

`plan_package_policy = "none" | "confirm" | "immediate"`

语义：

1. `none`
   - 不物化 plan package
2. `confirm`
   - 允许 planning 继续，但在建包前停在 `confirm_plan_package`
3. `immediate`
   - planning 完成后直接创建 plan package

兼容策略：

1. 暂保留 `should_create_plan`
2. `should_create_plan` 仅作为 `plan_package_policy == immediate` 的派生值
3. engine / handoff / output 逐步迁移为以 `plan_package_policy` 为准

### B. Proposal 状态文件
新增：

`current_plan_proposal.json`

建议 v1 字段：

1. `schema_version`
2. `checkpoint_id`
3. `reserved_plan_id`
4. `topic_key`
5. `proposed_level`
6. `proposed_path`
7. `analysis_summary`
8. `estimated_task_count`
9. `candidate_files`
10. `request_text`
11. `created_at`
12. `updated_at`

字段语义：

1. `topic_key`
   - planning 收敛后的稳定 topic slug
   - 在 planning 收敛时确定；若存在 clarification / decision，则在其收口后确定；若不存在，则由初始 planning 收敛结果直接确定
   - 作为 `reserved_plan_id` 与 `proposed_path` 的推导来源

约束：

1. `topic_key` 在同一 proposal 生命周期内不得漂移
2. `proposed_path` confirm 前后必须保持一致
3. `reserved_plan_id` 是未来真正 scaffold 使用的 slug
4. v1 不单独引入 `proposal_id`
5. 如果 confirm 后重新生成 path，则视为 contract break

### C. 新停点
新增：

1. `required_host_action = confirm_plan_package`
2. `route_name = plan_proposal_pending`
3. `current_run.stage = plan_proposal_pending`
4. `handoff_kind = plan_proposal`

gate 约束：

1. `confirm_plan_package` 进入 `CHECKPOINT_ONLY`
2. 宿主只允许展示 proposal 摘要并等待确认
3. 宿主不得直接跳过到 `review_or_execute_plan` 或普通咨询输出

### D. checkpoint contract
建议在 generic checkpoint schema 中新增：

1. `checkpoint_kind = plan_proposal`

理由：

1. proposal 阶段没有 `current_plan`
2. 不能复用 `execution_confirm`
3. 不能只靠 `Next` 文案

### E. Router pending classifier
必须新增：

`_classify_pending_plan_proposal()`

它要处理的输入：

1. `继续 / next`
   - 进入 `plan_proposal_pending`
   - `active_run_action = confirm_plan_proposal`
2. `status`
   - `active_run_action = inspect_plan_proposal`
   - 行为：只读取当前 `current_plan_proposal.json` 并返回 proposal 摘要 / next hint，不修改 proposal 内容或 identity，handoff 保持 `confirm_plan_package`
3. 修订意见
   - `active_run_action = revise_plan_proposal`
4. `取消`
   - `active_run_action = cancel`
5. `~go exec`
   - 不允许穿透，必须回到 proposal checkpoint

不建议新增 `resume_plan_proposal` 路由；v1 统一复用 `plan_proposal_pending + active_run_action`

## 流转设计

### Flow 1 | 非显式复杂请求
1. 用户发起复杂请求
2. router 进入 `workflow` 或 `light_iterate`
3. runtime 执行 analyze / clarification / decision
4. planning 收敛后生成 proposal，不生成 plan artifact
5. 写入 `current_plan_proposal.json`
6. handoff 停在 `confirm_plan_package`
7. 用户回复 `继续 / next`
8. runtime 按 `reserved_plan_id` 创建 plan scaffold
9. 清理 `current_plan_proposal.json`
10. handoff 停在 `review_or_execute_plan`
11. 用户再确认后，若 gate ready，则进入 `confirm_execute`

### Flow 2 | 显式 `~go plan`
1. 用户输入 `~go plan ...`
2. planning 正常进行
3. clarification / decision 仍然有效
4. 跳过 `confirm_plan_package`
5. engine 在 immediate 路径中按与 proposal 路径相同的 slug 规则直接生成 `reserved_plan_id`
6. 该路径不写 `current_plan_proposal.json`
7. 基于该 `reserved_plan_id` 创建 plan scaffold
8. handoff 停在 `review_or_execute_plan`
9. 不直接进入 develop

### Flow 3 | 善后 / 元问题
以下请求应优先走 consult，不进入新 plan scaffold：

1. `为什么生成了 plan`
2. `不要再生成 plan`
3. `分析下为什么会命中 guard`
4. `这是 bug 吗`

### Flow 4 | Proposal pending 下的修订
1. proposal pending 阶段，用户提交修订意见
2. router 进入 `plan_proposal_pending`
3. classifier 产出 `active_run_action = revise_plan_proposal`
4. engine 基于原 proposal + 修订意见重新跑 planning 收敛
5. 允许刷新：
   - `analysis_summary`
   - `estimated_task_count`
   - `candidate_files`
   - `proposed_level`
   - `updated_at`
   - 说明：`proposed_level` 只影响后续 scaffold 的内部文件结构与模板深度，不参与 proposal identity/path；level 变化本身不得触发 `proposed_path` 重算
6. 保持不变：
   - `checkpoint_id`
   - `topic_key`
   - `reserved_plan_id`
   - `proposed_path`
7. engine 回写 `current_plan_proposal.json`
8. handoff 回到 `confirm_plan_package`

边界：
1. `revise_plan_proposal` 只允许 proposal envelope 内修订，不允许借修订重建新的 topic/path 身份
2. 若修订意见要求改变 `topic_key` 或 `proposed_path`，应视为退出当前 proposal，改走新的 planning 请求，而不是在原 proposal 上漂移

边界处理：
1. engine 一旦判定 revise 需要改变 `topic_key` 或 `proposed_path`，不得在原 proposal 上原地改写 identity/path
2. 当前 `current_plan_proposal.json` 必须在退出判定成立后立即清理；旧 proposal 不得在新的 planning 进行中继续暴露为机器事实来源
3. “同一轮”指同一次 engine/runtime 调用内完成旧 proposal 清理并继续新的 planning；宿主不应看到“旧 proposal 已退出但尚未进入新稳定停点”的中间 handoff
4. engine 应在该次调用内把该请求转入新的 planning 请求继续处理，而不是把它当作 revise 成功后回到原 `confirm_plan_package`
5. 新 planning 的稳定停点取决于新的收敛结果，可为：
   - `answer_questions`
   - `confirm_decision`
   - 新的 `confirm_plan_package`
6. 只有当新 planning 再次收敛为 proposal 时，才允许写入新的 `current_plan_proposal.json`；该 proposal 必须使用新的 `checkpoint_id / topic_key / reserved_plan_id / proposed_path`

## 影响点

### 1. state
- `runtime/state.py` 新增 proposal 的读写接口
- session-first，语义与 clarification / decision 一致

### 2. router
- 去掉裸词 `plan` 的 process force 语义
- 增加 consult/meta-debug bypass
- 增加 pending proposal classifier

### 3. engine
- 支持 proposal-first 再 materialize
- 支持 confirm 后复用 `reserved_plan_id`
- 避免在 proposal pending 时写 `current_plan.json`

### 4. handoff / gate / output
- 新增 `confirm_plan_package`
- 新增 proposal checkpoint artifact
- 新增对应的 next hint / output label

### 5. host docs
- repo 内宿主源文档需要显式收口 `confirm_plan_package` 的消费规则
- 宿主看到 `confirm_plan_package` 时必须停住
- 不得把它当普通 `continue_host_workflow`

## 非目标
1. 不处理 `light` 任务是否减少确认次数
2. 不一并重构 `ExecutionGate`
3. 不修改 Ghost / Suspend / Side Task 方案
4. 不修改现有 plan artifact 模板结构

## 待确认决策
1. 非显式复杂请求是否先停在 `confirm_plan_package`
   - 建议：是
2. `confirm_plan_package` 是否进入 `CHECKPOINT_ONLY`
   - 建议：是
3. `proposed_path` 是否 confirm 前后不变
   - 建议：是
4. `~go plan` 是否只跳建包确认，不跳其他 checkpoint
   - 建议：是

## 验收门
1. 非显式复杂请求不会在无确认时创建 `.sopify-skills/plan/...`
   - 显式回归样例：`那你执行吧 逻辑严谨`
   - 预期：允许进入 planning / proposal flow，但不得直接物化正式 plan package
2. `current_plan_proposal.json` 与 handoff checkpoint 内容一致
3. `continue / next` 能从 proposal pending 正常确认建包
4. `proposed_path` 与最终落盘 path 一致
5. `~go plan` 仍允许 clarification / decision，不绕过其他 checkpoint
6. `review_or_execute_plan` 与 `confirm_execute` 的原语义不漂移
7. 若 revise 需要改变 `topic_key` 或 `proposed_path`，系统必须退出当前 proposal 并进入新的 planning 结果，不得静默漂移旧 proposal 的 identity/path
