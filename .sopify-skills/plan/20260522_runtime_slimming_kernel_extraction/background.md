# 变更提案: Runtime Slimming — Orchestration Kernel Extraction

## 需求背景

当前蓝图已经把 `runtime` 的产品定位收敛为 **可选增强 / 参考实现**，并且 P6 已完成 `sopify_contracts + canonical_writer + runtime` 的三层物理分离。用户现在要回答的不是"runtime 是否还能删一点"，而是：

1. **runtime 中哪些面是核心编排（gate / route / handoff / checkpoint），必须保留为 orchestration kernel**
2. **哪些面是 deep-only 长尾，可以退场**
3. **保留面如何与 runtime 其余面解耦，使退场不破坏安装链路和诊断工具**

现状里已经有足够多的原则性结论，但它们分散在 blueprint 与多次归档里：

- `blueprint/design.md` 明确写了：`runtime` 是参考实现与迁移层，不是 truth source
- P4b/P4b.5/P5/P6 已经分别回答了 keep-list、可选性、surface shrinkage、canonical writer cutover
- 但仓库里还没有一个专门的活动方案，把“删除就绪”收敛成**可执行的文件级审计清单**

这导致当前只能回答方向，不能直接回答：

- 哪些 `runtime/*.py` 已经是 keep-list 外且零消费者
- 哪些模块虽然不是新宿主接入前提，但仍被老宿主/installer/tests 依赖
- 哪些 builder / writer / facade 还没有迁出，因而不能整包删除
- 何时可以从“legacy reference”升级到“无消费者后下线”

本任务的目标就是把这些问题收口成一个标准方案包：**先做审计，再在同一包内执行有依据的删除**。重点不是“先删后证”，而是“先证后删”。

还需要补一个更强的前提：`blueprint/design.md` 已明确当前**无线上用户、零迁移负担**。因此，当前代码里仍存在的 Codex/Claude deep runtime 路径、installer 兼容逻辑、bundle smoke 或测试消费者，只能证明“技术现状仍有引用”，**不能自动推导出“这些路径必须继续维护”**。

换句话说，本次审计不能把“有消费者”直接等同于“不能删”。它必须额外回答：

1. 若维护者决定继续保留 legacy deep runtime 路径，哪些面构成真实阻塞
2. 若维护者决定目标态优先、允许 legacy consumer 与 runtime 一起退场，哪些阻塞会随之消失

这也意味着，本包不应停在“审计报告完成”。如果审计已经足以把一批面稳定归类为 `delete_now`，那么继续拖到下一个包再动刀，价值不高，反而会把证据和实施切开。更合理的节奏是：

1. 审计产出三张表与推荐策略
2. 维护者确认采用哪条口径
3. 在同一包里删除已获准的 `delete_now` 面
4. 若采用 `target-state-first`，再按明确批准范围同步删除 `co-delete candidate`

当前还有一个现实判断需要提前写清：在 `legacy-preserving` 口径下，本包大概率只能删掉很少量真正无人消费的旧面；真正有量级的删除只会出现在 `target-state-first`。换句话说，本次审计的真正价值不主要是“找出几个零散文件”，而是为维护者提供足够信息，决定是否正式弃养 legacy deep runtime 路径，并接受相关 scripts/tests/bridge 一起退场。

## 已确认决策（2026-05-22，修订 2026-05-22）

维护者已在 **2026-05-22** 明确确认：本包后续实施按 **`target-state-first`** + **orchestration kernel extraction** 推进。

核心方向：
- 停止维护 deep-capable host（Claude / Codex / Copilot）的宿主专属 legacy glue（bridge / renderer / bundle / smoke），但 kernel 通过协议对所有 deep-capable host 保持可达
- 不是"全删 runtime"，而是把现有 runtime 缩成一个极薄的 orchestration kernel
- kernel 保留核心编排确定性（gate / route / handoff / checkpoint state transitions），其余面全部退场
- canonical_writer 继续做写层，sopify_contracts 继续做类型层，kernel 做控制层

该决策的含义不是"先删再看"，也不是"重建 runtime"，而是：

1. 先把仍需保留的非 runtime 面从 runtime / bundle / deep entry 契约上解耦
2. 定义并提取 orchestration kernel（最小编排闭环）
3. 再让 `runtime/` 中非 kernel 面与 legacy deep consumers 同步退场

该决策同时排除了三种错误口径：

1. **有消费者 = 必须保留**
   - 不成立。当前无线上用户、零迁移负担，legacy consumer 只代表现状，不代表长期义务
2. **canonical_writer 已能替代全部接续编排**
   - 不成立。`canonical_writer` 已覆盖 canonical state 写层，但 gate / router / handoff builder / engine orchestration 仍在 `runtime`
3. **重建完整 runtime**
   - 不成立。kernel extraction 的目标是保留最小编排闭环，不是重新发育一整套 runtime。若 kernel 需要的模块超过合理范围，应回退审视 kernel 边界

因此，本包的真实执行顺序已经收敛为：

1. 回写长期决策到 blueprint
2. 解耦 retain-after-decoupling 面（5 文件）
3. 定义并提取 orchestration kernel（从 runtime/ 中分离最小编排闭环）
4. 删除 `runtime/` 中非 kernel 面 + legacy deep path
5. 做硬验证并记录剩余保留面

其中，retain-after-decoupling 面已收敛为 5 个文件：

1. `installer/validate.py`
2. `installer/bootstrap_workspace.py`
3. `installer/inspection.py`
4. `scripts/install_sopify.py`
5. `scripts/sopify_init.py`

同时明确：

1. `installer/runtime_bundle.py` 不是“保留后解耦”面，而是 pure legacy surface，应在 runtime 退场时直接同步删除
2. `scripts/sopify_status.py` / `scripts/sopify_doctor.py` 本身不含 runtime 逻辑，不列入独立解耦清单；它们的变化应通过 `installer/inspection.py` 的 cutover 吸收

## 包边界约束

本次处理继续使用当前方案包 `20260522_runtime_slimming_kernel_extraction`，**不开新方案包**。

orchestration kernel extraction 已确认为本包内执行目标，不是独立新主线。

因此，后续所有与本主题直接相关的工作都应先挂在当前包内推进：

1. retain-after-decoupling 五文件 cutover
2. orchestration kernel 定义与提取
3. runtime 非 kernel 面 / legacy deep path 同步退场
4. 删除后的验证与长期文档回写

另外，当前已经识别出一个**制度层副发现**：`deferred` 在 `project.md` 与部分 plan frontmatter 中被当作合法生命周期使用，但 `runtime/plan_registry.py` 的 `snapshot.lifecycle_state` 不支持该值，只能通过 `governance.status=deferred` 绕开。

这个冲突应在本次审计中被记录为 delta，但**不在本轮先改 registry contract**。原因很简单：手工改 `_registry.yaml` 不会稳定，读时 reconcile 仍会回写成当前受支持值。是否扩展 registry lifecycle contract，还是收紧 `project.md` / plan frontmatter 的语义，等消费者扫描与推荐策略完成后再一起裁定。

评分:
- 方案质量: 8/10
- 落地就绪: 9/10

评分理由:
- 优点: 目标明确，蓝图约束和历史证据都已存在，适合直接做收敛型审计。
- 扣分: 仍需实际扫描消费者与生产职责，才能把“可删”从原则判断变成精确清单。

## 变更内容
1. 建立一份专门针对 `runtime` 删除就绪的活动方案包。
2. 明确“可删旧面”与“不可整包下线”的边界。
3. 产出面向后续实施的文件级审计任务与验收标准。

## 影响范围
- 模块: `.sopify-skills/plan/`, `.sopify-skills/blueprint/README.md`
- 文件:
  - `.sopify-skills/plan/20260522_runtime_slimming_kernel_extraction/background.md`
  - `.sopify-skills/plan/20260522_runtime_slimming_kernel_extraction/design.md`
  - `.sopify-skills/plan/20260522_runtime_slimming_kernel_extraction/tasks.md`
  - `.sopify-skills/plan/_registry.yaml`
  - `.sopify-skills/blueprint/README.md`

## 风险评估
- 风险: 若在同一包里把“审计”和“删除”混成一次无门槛推进，容易从 `delete_now` 滑向未审清的 contract 面或 legacy 路径。
- 缓解: 本 plan 采用双口径审计 + 中途确认门槛，显式区分 `delete_now`、`keep_for_legacy_runtime`、`blocking_full_retirement`，并要求删除动作只能消费已获准清单。
