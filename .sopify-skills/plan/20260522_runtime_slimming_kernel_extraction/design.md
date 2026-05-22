# 技术设计: Runtime Slimming — Orchestration Kernel Extraction

## 技术方案
- 核心目标: 把 `runtime/` 从 23.8K LOC 的完整 deep runtime 瘦身为一个极薄的 **orchestration kernel**，保留核心编排确定性（gate → route → handoff → checkpoint），删除其余全部 deep-only 面。
- 实现要点:
  - 以 `blueprint/design.md` keep-list、persistence red line、runtime retirement 路线为准绳做审计
  - 以当前代码消费者和生产者关系为准，不以历史口头判断代替现状扫描
  - 以 `design.md` L727 的“无线上用户、零迁移负担”为约束，避免把 legacy consumer 自动上升为保留义务
  - 区分四类结论：`extract-to-kernel`、`delete_now`、`keep_for_legacy_runtime`、`blocking_full_retirement`
  - kernel 定义标准：只保留编排闭环最小面（ingress/gate、route classification、handoff production、checkpoint state transitions），其余降级或删除

## 已锁定实施口径（2026-05-22，修订 2026-05-22）

维护者已在 **2026-05-22** 确认本包采用 **`target-state-first`** + **orchestration kernel extraction**：

1. 停止维护 deep-capable host（Claude / Codex / Copilot）的宿主专属 legacy glue（bridge / renderer / bundle / smoke），但 kernel 通过协议对所有 deep-capable host 保持可达
2. 允许 `runtime/` 中非 kernel 面与 legacy deep consumers 同步退场
3. 不把 gate / router / handoff builder / engine 编排层塞进 `canonical_writer`，而是保留为独立的 orchestration kernel
4. 删除前先处理仍需保留的非 runtime 面，避免安装链路、workspace marker、status/doctor 当场断裂
5. 从现有 `runtime/` 中提取最小编排核（gate / route / handoff / checkpoint state transitions），不重建一整套 runtime
6. kernel 若未来不需要 deep path，可继续收缩；若需保深编排，也有最小稳定层可用

这意味着本包的 Phase B 以**两个前置条件**为门槛：
1. 保留面（5 文件）是否完成解耦
2. orchestration kernel 边界是否已明确且提取完成

## Kernel 形态定性

本包的 kernel **不是 skill、不是纯 protocol、不是脚本优先**，而是：

> **Protocol-first + validator-centered + lightweight orchestration kernel**

具体含义：
- **protocol-first**：协议定义语义真相，kernel 是协议的参考实现，不拥有协议定义权
- **validator-centered**：验证体系（contract freeze、persistence red line、machine truth 校验）是兜底层
- **lightweight kernel-backed**：保留一个极薄的可执行编排核，提供 deep path 的确定性体验

落地形态：
- 原地瘦身 `runtime/`，不新建 `runtime2/`、`orchestrator/`、`kernel_runtime/` 等并行目录
- `sopify_contracts` + `canonical_writer` 继续做共享类型层和写层
- legacy `*_runtime.py` 不作为保留面沿用；若 S3 审计确认 kernel 仍需 host-facing 最小链路，则新增全新薄壳入口，核心逻辑留在薄模块内
- skill 继续只服务 analyze/design/develop，不接管状态机

### 5 条实施红线

1. **不新开第二条实现线** — 不建并行产品目录，先在现有 `runtime/` 内收缩到只剩 kernel
2. **不新增机器真相** — 继续只用现有 canonical_writer + sopify_contracts + frozen contract，不发明新 state、新 manifest、新 capability 家族
3. **不再承接宿主 UX 外围** — kernel 不负责安装、bundle、渲染文案、smoke shell、bridge CLI，只负责状态迁移和结构化决策
4. **不保留"全功能 engine"** — engine 缩成 transition coordinator，不再当"大总管"
5. **不改主协议语义** — 宿主继续消费 handoff/current_* 等冻结 contract，不重写 protocol，只把生产者缩薄

## S3 Kernel Boundary Audit (2026-05-22)

> 本节由 S1 蓝图校验 + S2 消费者扫描 + advisor 四点修正 共同输入，产出 kernel 精确边界。
> **所有判定均为工作假设，待维护者审计确认后方可作为 S4 执行依据。**

### 架构总览

![Kernel Architecture](kernel-architecture.svg)

### 🔴 LOC 预算现实

| 范围 | 当前 LOC | 备注 |
|------|---------|------|
| kernel core (7 files) | 3,238 | gate.py / entry_guard / execution_gate / router / handoff / checkpoint_request / checkpoint_materializer |
| kernel support (3 files) | 698 | config / state / deterministic_guard — 入口支撑层，不是内核本体 |
| 优先拆分对象 (1 file) | 973 | context_snapshot — 拆出最小快照解析，其余共删 |
| 非内核但可暂留 (1 file) | 130 | gate_output — text rendering，不算内核 |
| **kernel core + support** | **~3,936** | 瘦身方向，不锁具体 LOC 目标 |

> **重要: 1-2K 是理想方向，不是第一刀的硬约束。**
> S4 的首轮目标是"去依赖、拆非核心分支、保 contract 不断"，不按 LOC 倒推重写。
> 如果为了强行压到 1.8K 而拆碎 handoff/gate/router，反而会把可收敛的删改做成二次架构设计。

### 表1: Kernel 第一圈精确边界

<!-- 注释约定:
     - "非内核 runtime 依赖" = 依赖了不在第一/第二圈的 runtime 模块
     - 这些依赖在 S4 瘦身时必须切断（删除调用、提为参数、或判定对应模块升入内核）
     - "判定" 是 S4 动作建议，不是当前状态 -->

| 模块 | LOC | 内核依赖 | 非内核 runtime 依赖 | 判定 |
|------|-----|---------|---------------------|------|
| `gate.py` | 946 | config, entry_guard, state | engine, action_intent, preferences, workspace_preflight | **内核核心，需重度瘦身** |
| `entry_guard.py` | 54 | 无 | 无 | **原样保留** |
| `execution_gate.py` | 351 | config(via models) | knowledge_sync | **保留，轻度解耦** |
| `router.py` | 783 | context_snapshot, entry_guard | clarification, decision, skill_resolver | **内核核心，需重度瘦身** |
| `handoff.py` | 618 | checkpoint_request, deterministic_guard, entry_guard, state | action_projection, clarification, decision_policy, decision, develop_quality, resolution_planner, sidecar_classifier_boundary, vnext_phase_boundary | **内核核心，需最重度瘦身 (8 个非内核依赖)** |
| `checkpoint_request.py` | 319 | models(deprecated) | clarification | **保留，1 个可切依赖** |
| `checkpoint_materializer.py` | 167 | models(deprecated), checkpoint_request | 无 | **原样保留** |

#### gate.py 瘦身注释 (946 → 目标 ~300 LOC)

```
当前职责（过重）:
  1. config 加载 + state cleanup          ← 保留（内核配置入口）
  2. workspace preflight                   ← 砍掉（不属于编排，属于安装验证）
  3. preferences preload                   ← 砍掉（不属于 gate 判定，属于 UX 增强）
  4. engine 全流程调用 (run_runtime)       ← 砍掉（engine → transition coordinator，不从 gate 直调）
  5. action_intent 解析                    ← 砍掉或降级（属于路由前预处理，可合并到 router）
  6. gate 合约构建 + receipt 写入          ← 保留（内核核心）
  7. handoff 归一化                        ← 保留（内核核心）

S4 目标: gate.py 只负责 "config → state → gate 合约 → receipt"，其余职责通过调用方或 thin shell 承担
```

#### router.py 瘦身注释 (783 → 目标 ~200 LOC)

```
当前职责（过重）:
  1. route classification (consult/workflow/plan_only/resume/cancel)  ← 保留（内核核心）
  2. clarification response 解析 + submission 判定                    ← 降级为协议接口，不直接导入 clarification 模块
  3. decision response 解析 + submission 判定                         ← 降级为协议接口，不直接导入 decision 模块
  4. state conflict 路由                                              ← 保留（依赖 context_snapshot，已在第二圈）
  5. skill_resolver 候选技能选择                                      ← 砍掉（属于 skill dispatch，非编排）
  6. complexity 启发式                                                ← 砍掉（属于 UX 策略，非编排判定）

S4 目标: router.py 只负责 "snapshot → route decision"，clarification/decision 通过协议接口而非直接 import
```

#### handoff.py 瘦身注释 — 两刀策略 (advisor 批判 #5)

```
当前职责（过重，13 个 runtime 依赖）:
  1. checkpoint_request → handoff payload 最小转换      ← 保留（内核核心）
  2. entry_guard contract 构建                           ← 保留（已在第一圈）
  3. deterministic_guard 评估                            ← 保留（已在 kernel support）
  4. state 辅助 (request hash / text summary)            ← 保留（已在 kernel support）
  5. required_host_action / artifact 组装                ← 保留（deep host 真正消费的东西）
  6. action_projection 构建                              ← 第一刀砍（属于 host UX 增强）
  7. clarification form 构建 + submission state           ← 第一刀砍（非编排核心）
  8. decision policy 检查                                 ← 第一刀砍（属于策略层）
  9. decision path 常量                                   ← 第一刀砍（非核心）
  10. develop_quality contract 构建                       ← 第一刀砍（属于质量增强）
  11. resolution_planner 恢复计划                         ← 第一刀砍（属于诊断层）
  12. sidecar_classifier_boundary                         ← 第一刀砍（属于分类器边界）
  13. vnext_phase_boundary                                ← 第一刀砍（属于版本迁移）

S4 两刀策略:
  第一刀: 砍 sidecar / resolution_planner / vnext / develop_quality / action_projection / decision_policy
          保住一个完整的最小 handoff producer（不拆碎 contract 生产逻辑）
  第二刀: 观察第一刀后的 LOC 和耦合状态，再决定是否进一步压缩

注意: 不要为了缩 LOC 把 contract 生产逻辑拆碎。
      required_host_action、artifact 组装、entry guard 附着是 deep host 真正消费的东西。
```

### 表2: 第二圈分层判定

<!-- 修订说明 (advisor 批判 2-4):
     - 原"第二圈"过于扁平，把 rendering/config/diagnostics 和 kernel 核心混在一起
     - 现拆为三个分层: kernel support / 优先拆分对象 / 非内核可暂留
     - 避免把 support 面误当 kernel 本体 -->

#### kernel support — 入口支撑层（保留，但不是内核第一等公民）

<!-- config/state/deterministic_guard 被广泛 import，但它们不参与 gate→route→handoff→checkpoint 编排决策。
     保留原因是被 kernel core 直接依赖；但"被很多文件 import"不等于"属于内核本体"。-->

| 模块 | LOC | 被谁依赖 | 定性 |
|------|-----|---------|------|
| `config.py` | 236 | gate.py + 13 外部文件 | 配置加载器，kernel 启动时需要但不参与编排判定 |
| `state.py` | 137 | gate.py, handoff.py, scripts, tests | 时间戳/hash/session cleanup 辅助，observability 性质 |
| `deterministic_guard.py` | 325 | handoff.py, tests | fail-closed 守卫逻辑，低耦合但属于安全策略层 |

#### 优先拆分对象 — context_snapshot.py

<!-- advisor 批判 #4: 不应默认"保留并瘦身"，而应当成 S4 优先拆分目标。
     真正 kernel 需要的可能只是:
       1. 读取 current_*
       2. 选主作用域
       3. 基本一致性检查
     其余 quarantine/conflict_artifacts/diagnostics 属于可删除的非核心分支。-->

| 模块 | LOC | 被谁依赖 | 定性 |
|------|-----|---------|------|
| `context_snapshot.py` | 973 | router.py, installer/inspection.py(已脱钩), tests | **暂保留为内核支撑**: router.py 重度依赖(resolve_context_snapshot + 9 字段 + conflict_artifacts)，Step 2 不拆。非内核消费方(engine/context_recovery/develop_callback) Step 3 随模块删除自然消失 |

#### 非内核但可暂留 — gate_output.py

<!-- advisor 批判 #2: gate_output.py 本质是 text rendering，且依赖 installer.outcome_contract。
     不应算进 orchestration kernel 预算。可以暂时留在 repo 但不标为内核。-->

| 模块 | LOC | 被谁依赖 | 定性 |
|------|-----|---------|------|
| `gate_output.py` | 130 | scripts/runtime_gate.py, tests | **非内核**: text rendering + 依赖 installer.outcome_contract。可暂留，不计入 kernel |

#### 确认删除

| 模块 | LOC | 被谁依赖 | 定性 |
|------|-----|---------|------|
| `models.py` | 50 | 8 个内核模块(core 5 + support 3) + context_snapshot, tests | **删除**: DEPRECATED re-export facade，消费方改为 `from sopify_contracts` |

### 表3: Host-Facing 最小入口职责表

<!-- 注释约定:
     - "职责" = 从协议角度，host 为什么需要这个入口
     - "当前形态" = legacy 脚本是薄壳还是含业务逻辑
     - S4 动作 = 不保留旧脚本，按职责需要决定是否新建 thin shell -->

| 职责 | 当前实现 | 当前形态 | runtime 导入 | S4 动作 |
|------|---------|---------|-------------|---------|
| **Ingress gate** — host 调用入口闸门，获取 gate 合约 + receipt | `scripts/runtime_gate.py` | 薄壳 → `gate.enter_runtime_gate()` | gate, gate_output | **in-place cutover**: 路径名被 manifest/test 冻结，原地重写内容为 thin shell |
| **Default raw entry** — 用户请求的默认 runtime 入口 | `scripts/sopify_runtime.py` | **含业务逻辑** (direct-entry blocking, receipt writing) | cli, config, entry_guard, gate, output, router, state | **in-place cutover**: guard/receipt 逻辑上移到内核；原地重写为 thin shell |
| **Develop callback** — continue-host-develop 回调 | `scripts/develop_callback_runtime.py` | 薄壳 → `runtime.develop_callback` | config, develop_callback | **in-place cutover**: 原地重写为 thin shell |
| **Plan helper** — `~go plan` 产品入口 | `scripts/go_plan_runtime.py` | 产品辅助 → `plan_orchestrator.run_plan_loop()` | cli, config, output, plan_orchestrator | **产品决策**: 路径名被 manifest 冻结；若删除需同步改 manifest/test/doc |

#### 入口设计原则

```
1. 路径名可能被 manifest/test/doc 冻结 → 优先 in-place cutover（重写内容、保留路径）
2. 重写后的内容：
   - 只做: argparse → 调用 kernel 函数 → 输出 JSON/text → exit code
   - 不做: config 加载、state 管理、receipt 写入（属于 kernel 内部）
3. 若确认路径名未被冻结，可改名或删除；但需在 S4 验证
4. go_plan 的去留是产品决策，不在 kernel architecture scope
```

### 表4: Gate/Checkpoint 测试重建清单

<!-- 注释约定:
     - "必须重建" = 测试的 contract/invariant 在内核中仍然成立，删掉就失去回归保护
     - "可随 legacy 共删" = 测试的对象本身会被删除
     - 重建 ≠ 原封不动搬，而是提取 contract invariant 写新测试 -->

| 测试文件 | 测试层级 | 判定 | 重建注释 |
|---------|---------|------|---------|
| `test_runtime_gate.py` | 内核: gate 合约、entry-guard contract、receipt 行为 | **必须保留等价覆盖** | 提取 gate 入口合约断言 + receipt 结构校验；删除 engine 调用相关 case |
| `test_runtime_execution_gate.py` | 内核: blocked/ready/decision_required 状态转换 | **必须保留等价覆盖** | 保留状态转换矩阵测试；去掉 plan-file 解析细节 |
| `test_runtime_router.py` | 内核: consult/workflow/plan_only/resume/cancel 路由不变量 | **必须保留等价覆盖** | 保留路由判定断言；skill_resolver 相关 case 删除 |
| `test_runtime_state.py` | 内核: checkpoint/handoff 状态不变量、conflict 检测 | **必须保留等价覆盖** | 保留 paired write 不变量 + resolution ID 校验 |
| `test_runtime_sample_invariant_gate.py` | 内核: gate 矩阵对齐、side-effect 映射 | **必须保留等价覆盖** | 保留矩阵完整性断言；replay 行为测试按瘦身后范围裁剪 |
| `test_contract_consistency.py` | 内核: schema/manifest 冻结、allowed response modes | **必须保留等价覆盖** | 整体保留（已是 contract freeze 测试，接近不变） |
| `test_runtime_config.py` | kernel support: config 加载行为 | **必须保留等价覆盖** | config.py 保留为 kernel support，对应测试保留 |
| `test_context_checkpoints.py` | 实现细节: CLI/commit/PR 元数据 checkpoint 规则 | **可随 legacy 共删** | 测试对象是 CLI 检查脚本，非内核编排 |
| `test_runtime_failure_recovery.py` | 恢复表形状、allowed-response-mode 行为 | **大概率共删** | 除非明确保留 failure-recovery contract 作为内核策略 |

**统计: 保留等价覆盖 7 个 / 共删 2 个**

> "保留等价覆盖" ≠ 原封不动搬。测试可以重写、合并、简化，只要等价的 contract invariant 仍有覆盖即可。
> 具体重建方式在 S4 执行时按实际 kernel 接口决定，不在 S3 预锁。

### 非内核 runtime 依赖汇总 (S4 必须切断)

<!-- 这 14 个模块被 hub 三巨头 (gate/router/handoff) 依赖，但不在内核范围内。
     S4 瘦身的核心任务就是切断这些依赖链。 -->

| 非内核模块 | 被谁依赖 | 切断方式 |
|-----------|---------|---------|
| `engine` | gate.py | 删除 `run_runtime` 调用，engine 降为 transition coordinator |
| `action_intent` | gate.py | 删除或合并到 router 前处理 |
| `preferences` | gate.py | 删除 preload 调用（属于 UX 增强，非 gate 判定） |
| `workspace_preflight` | gate.py | 删除 preflight 调用（属于安装验证，非编排） |
| `knowledge_sync` | execution_gate.py | 改为可选导入或删除 |
| `clarification` | router.py, handoff.py, checkpoint_request.py | 降为协议接口（不直接 import，通过数据传入） |
| `decision` | router.py, handoff.py | 降为协议接口 |
| `skill_resolver` | router.py | 删除（属于 skill dispatch） |
| `action_projection` | handoff.py | 删除（属于 host UX 增强） |
| `decision_policy` | handoff.py | 删除（属于策略层） |
| `develop_quality` | handoff.py | 删除（属于质量增强） |
| `resolution_planner` | handoff.py | 删除（属于诊断层） |
| `sidecar_classifier_boundary` | handoff.py | 删除（属于分类器边界） |
| `vnext_phase_boundary` | handoff.py | 删除（属于版本迁移） |

### Kernel Context Scope 判定标准 (S4 执行护栏)

<!-- 这 4 条是 S3 审计后维护者+advisor 达成一致的 kernel scope 判定标准。
     S4 执行时所有"这个要不要留"的问题，先过这 4 条。-->

1. **Kernel 对 machine truth 的关系：读消费者 + 写生产者，不是 owner**
   - 读: current_run / current_handoff / current_clarification / current_decision / current_plan（通过最小 snapshot resolver）
   - 写: gate receipt + handoff payload + checkpoint request（通过 canonical_writer.StateStore）
   - machine truth 的存储层在 `canonical_writer`，不在 kernel

2. **Kernel 只保留支撑 gate / route / handoff / checkpoint 的最小上下文**
   - current_run, current_handoff, current_clarification, current_decision, 必要时 current_plan
   - 少量用于 contract/receipt 的稳定字段
   - 不保留 session 级 last_route、quarantine、conflict artifacts 等运行时局部语境

3. **Runtime 局部语境、诊断解释上下文、策略附加上下文不进入 kernel**
   - ❌ route 内部启发式痕迹
   - ❌ sidecar / boundary / resolution planner 诊断上下文
   - ❌ output/rendering 为宿主解释而拼出的本地解释层
   - ❌ skill dispatch / preferences preload / workspace preflight 附加上下文
   - 判定标准: "这个上下文是协议要求的 machine truth，还是为了调试/解释方便而生的？" — 后者不进 kernel

4. **context_snapshot / handoff 的具体裁剪标准**
   - context_snapshot: 只留 "读 current_* → 选主作用域 → 基本一致性检查"，quarantine/conflict/diagnostics 整体剥掉
   - handoff: 只留 required_host_action + 最小 artifacts，局部策略上下文整体剥掉

### S4 最小路线 — 不做二次架构设计

<!-- advisor 总结: S4 第一刀以去依赖、拆非核心分支为主，不按 LOC 倒推重写。
     两个核心护栏:
     1. 不被 1-2K 数字绑架
     2. 不把 text rendering、config loader、diagnostics snapshot 误当 kernel 本体 -->

```
Step 1: installer/scripts cutover — 保护安装链路 (第一刀: inspection.py)
  - 执行顺序: inspection.py → sopify_init.py → validate.py → bootstrap_workspace.py → install_sopify.py
  - inspection.py 是首个外部 blocker (L32-33 直接 import runtime.config / runtime.context_snapshot)
  - status/doctor 通过 inspection 改造继续可用，不单列 cutover

Step 1b: release 链 cutover
  - check-runtime-smoke.sh: 删除 sopify.json 断言 (install-time artifact, 非 engine 产物) ✅
  - release-preflight.sh 全链恢复通过 ✅
  - check-install-payload-bundle-smoke.py / check-skill-eval-gate.py / generate-builtin-catalog.py: 暂不改 (runtime 导入仍合法)

Step 2: retained kernel/support 模块的 models.py import rewire ✅
  - 9 files 机械 rewire: config, state, deterministic_guard, router, handoff,
    checkpoint_request, checkpoint_materializer, execution_gate, context_snapshot
  - `from .models import X` → `from sopify_contracts.{artifacts,core,decision,handoff} import X`
  - runtime/models.py 保留为非内核消费者过渡桥，Step 3 co-delete
  - 不在 Step 2: skill_resolver.py (非内核 co-delete)、gate_output.py / entry_guard.py (无 .models)
  - tests 继续走 runtime.models bridge，Step 3 删 facade 时同步处理
  - handoff/router 的非内核模块依赖 (action_projection, skill_resolver 等) 属 Step 3，不在 Step 2

Step 3: 非 kernel 批量删除 + in-place cutover 入口脚本
  - ~40 非 kernel 模块批量删除
  - 入口脚本 in-place cutover: 路径名被 manifest/test 冻结 → 原地重写
    只做: argparse → 调用 kernel → JSON/text 输出 → exit code
    不做: config 加载、state 管理、receipt 写入（属于 kernel 内部）

Step 4: 用等价覆盖测试守住 contract
  - 7 个 contract test 保留等价覆盖
  - 2 个 legacy test 共删
  - 具体重写方式按实际 kernel 接口决定
```

## S3.1 文件级删除候选表 (target-state-first)

<!-- S3.1-3.3 由 S2 消费者扫描 + S3 kernel 定义 + kernel context scope 护栏共同推导。
     注意: agent 扫描结果经过以下修正:
     1. "blocking_full_retirement" 在 target-state-first 下不成立（无在线用户，L727）
     2. "keep_for_legacy_runtime" 在 target-state-first 下全部降为 co-delete
     3. 脚本 smoke/sync 不是 "keep"，是 co-delete
     4. 大量测试不需要 "preserve-equivalent"，只有 gate/route/handoff/checkpoint 合约测试需要 -->

### runtime/ 非内核模块 (42 entries, ~18.8K LOC)

<!-- 42 = 1 rewrite-first (models.py) + 40 co-delete + 1 rewrite (__init__.py) -->

| 分类 | 文件 | LOC | 说明 |
|------|------|-----|------|
| **rewrite-first** | `models.py` | 50 | DEPRECATED re-export facade；被 8 个内核模块(core: execution_gate/router/handoff/checkpoint_request/checkpoint_materializer + support: config/state/deterministic_guard)直接 import → 必须先将 `from .models` 改为 `from sopify_contracts`，然后才能删除 |
| **co-delete** | `engine.py` | 2,728 | 全功能 engine，kernel 不保留 |
| **co-delete** | `decision_tables.py` | 1,632 | 决策表数据，非编排核 |
| **co-delete** | `plan_registry.py` | 1,012 | 计划注册存储，非编排核 |
| **co-delete** | `workspace_preflight.py` | 958 | 安装验证，非编排核 |
| **co-delete** | `action_intent.py` | 884 | 动作意图，非编排核 |
| **co-delete** | `decision_bridge.py` | 864 | 兼容桥接，非编排核 |
| **co-delete** | `archive_lifecycle.py` | 831 | 归档生命周期，非编排核 |
| **co-delete** | `failure_recovery.py` | 719 | 故障恢复，非编排核 |
| **co-delete** | `output.py` | 620 | 渲染输出，非编排核 |
| **co-delete** | `decision.py` | 607 | 决策对象，非编排核 |
| **co-delete** | `develop_callback.py` | 599 | 开发回调管道，非编排核 |
| **co-delete** | `manifest.py` | 475 | manifest 加载，非编排核 |
| **co-delete** | `kb.py` | 463 | 知识库访问，非编排核 |
| **co-delete** | `plan_scaffold.py` | 464 | 计划脚手架，非编排核 |
| **co-delete** | `decision_policy.py` | 434 | 决策策略，非编排核 |
| **co-delete** | `cli_interactive.py` | 412 | 交互 CLI，非编排核 |
| **co-delete** | `develop_quality.py` | 403 | 质量检查，非编排核 |
| **co-delete** | `clarification_bridge.py` | 401 | 兼容桥接，非编排核 |
| **co-delete** | `clarification.py` | 386 | 交互流程，非编排核 |
| **co-delete** | `context_v1_scope.py` | 329 | v1 上下文规则，非编排核 |
| **co-delete** | `plan_orchestrator.py` | 272 | 计划编排，非编排核 |
| **co-delete** | `builtin_catalog.py` | 267 | 内置目录，非编排核 |
| **co-delete** | `message_templates.py` | 265 | 消息模板，非编排核 |
| **co-delete** | `_yaml.py` | 264 | YAML 工具（被 kernel support config.py 使用 → S4 需判定: 内联或保留） |
| **co-delete** | `skill_registry.py` | 255 | 技能注册，非编排核 |
| **co-delete** | `action_projection.py` | 249 | 动作投影，非编排核 |
| **co-delete** | `resolution_planner.py` | 216 | 诊断恢复，非编排核 |
| **co-delete** | `vnext_phase_boundary.py` | 210 | 版本边界，非编排核 |
| **co-delete** | `sidecar_classifier_boundary.py` | 205 | 分类器边界，非编排核 |
| **co-delete** | `preferences.py` | 182 | 偏好预加载，非编排核 |
| **co-delete** | `decision_templates.py` | 164 | 决策模板，非编排核 |
| **co-delete** | `skill_schema.py` | 140 | 技能 schema，非编排核 |
| **co-delete** | `knowledge_layout.py` | 135 | 知识布局，非编排核 |
| **co-delete** | `cli.py` | 113 | CLI 入口，非编排核 |
| **co-delete** | `context_builder.py` | 112 | 上下文组装，非编排核 |
| **co-delete** | `skill_resolver.py` | 111 | 技能解析，非编排核 |
| **co-delete** | `context_recovery.py` | 93 | 上下文恢复，非编排核 |
| **co-delete** | `skill_runner.py` | 85 | 技能执行，非编排核 |
| **co-delete** | `checkpoint_cancel.py` | 80 | checkpoint 取消，非编排核 |
| **co-delete** | `knowledge_sync.py` | 66 | 知识同步，非编排核 |
| **rewrite** | `__init__.py` | 33 | 改为只导出 kernel 面 |

> **⚠ `_yaml.py` 特殊处理**: config.py (kernel support) 通过 `from ._yaml import` 依赖它。
> S4 需决定: 将 YAML 加载逻辑内联到 config.py，还是保留 `_yaml.py` 作为 kernel utility。

### scripts/ 退场+cutover 清单 (15 entries)

<!-- 7 co-delete + 4 cutover (release 联动) + 3 in-place cutover + 1 产品决策
     advisor 修正: 原表漏了 check-install-payload-bundle-smoke / check-skill-eval-gate / generate-builtin-catalog
     这些脚本在 release 主链上，cutover 工作量被低估。
     entry→新 shell 表述也不准确 — 若 manifest/test 冻结了路径名，实际是 in-place cutover，不是改名退场。-->

| 分类 | 文件 | LOC | 说明 |
|------|------|-----|------|
| **co-delete** | `clarification_bridge_runtime.py` | 160 | legacy bridge |
| **co-delete** | `decision_bridge_runtime.py` | 171 | legacy bridge |
| **co-delete** | `preferences_preload_runtime.py` | 72 | legacy helper |
| **co-delete** | `plan_registry_runtime.py` | 109 | legacy helper |
| **co-delete** | `check-prompt-runtime-gate-smoke.py` | 369 | runtime smoke 脚本 |
| **co-delete** | `check-runtime-smoke.sh` | 268 | runtime bundle smoke |
| **co-delete** | `sync-runtime-assets.sh` | 137 | runtime 资产同步 |
| **cutover (release 联动)** | `check-install-payload-bundle-smoke.py` | ~369 | L144+ 强校验 sopify_runtime.py/go_plan_runtime.py/runtime_gate.py 存在；release-preflight.sh 调用 |
| **cutover (release 联动)** | `check-skill-eval-gate.py` | ~100 | L17 直接 import runtime.config/router/skill_registry |
| **cutover (release 联动)** | `generate-builtin-catalog.py` | ~100 | L17 直接 import runtime._yaml/runtime.skill_schema |
| **cutover (release 联动)** | `release-preflight.sh` | 83 | L75-77 串联上述脚本；是 release 主链，不是"待评估" |
| **in-place cutover** | `runtime_gate.py` | 129 | manifest/test 冻结路径名 → 原地重写为 thin shell，不改名 |
| **in-place cutover** | `sopify_runtime.py` | 157 | manifest/test 冻结路径名 → 原地重写为 thin shell，不改名 |
| **in-place cutover** | `develop_callback_runtime.py` | 123 | 原地重写为 thin shell |
| **产品决策** | `go_plan_runtime.py` | 76 | manifest 冻结路径名；若删除需同步改 manifest/test/doc |

### tests/ 退场清单

<!-- advisor 修正: 原表只覆盖 test_runtime_* 命名的测试。
     实际还有一批非 test_runtime_* 但冻结 runtime contract 的测试需要处理。-->

#### A. kernel 合约测试（保留等价覆盖）

| 文件 | LOC | 说明 |
|------|-----|------|
| `test_runtime_gate.py` | ~43 | gate 合约 |
| `test_runtime_execution_gate.py` | 133 | 状态转换 |
| `test_runtime_router.py` | 260 | 路由不变量 |
| `test_runtime_state.py` | 240 | 状态不变量 |
| `test_runtime_sample_invariant_gate.py` | 140 | gate 矩阵 |
| `test_contract_consistency.py` | 43 | schema 冻结 |
| `test_runtime_config.py` | 71 | config 加载（kernel support 模块保留） |

#### B. 需人工审查（可能嵌入 kernel 不变量）

| 文件 | LOC | 说明 |
|------|-----|------|
| `test_runtime_engine.py` | 3,666 | engine 退场但可能嵌入 gate/handoff 集成不变量 |

#### C. 非 test_runtime_* 但冻结 runtime contract 的测试（S4 cutover 联动）

<!-- 这批测试不叫 test_runtime_* 但内部冻结了 runtime 路径/脚本/能力:
     - 硬编码 bundle manifest 中 runtime 脚本路径
     - subprocess 直调 scripts/runtime_gate.py
     - 固定校验 runtime_gate / preferences_preload 能力
     必须在 S4 cutover 时同步改写。-->

| 文件 | LOC | 冻结内容 | S4 处理 |
|------|-----|---------|---------|
| `test_installer.py` | ~230+ | L751+ 校验 bundle 含 sopify_runtime.py / go_plan_runtime.py / runtime_gate.py | cutover: 改写 manifest 期望值 |
| `test_installer_status_doctor.py` | ~80+ | L80+ 校验 runtime_gate / preferences_preload / .sopify-runtime | cutover: 改写能力/路径期望 |
| `test_action_intent.py` | ~983 | subprocess 调 scripts/runtime_gate.py | cutover 或 co-delete（视 action_intent 是否保留） |
| `test_runtime_decision.py` | ~900 | 直调 bridge 脚本 | co-delete（bridge 退场） |
| `test_context_v1_scope.py` | — | 引用 deterministic_guard | 跟随 kernel support 保留 |

#### D. co-delete（非内核 runtime 测试）

| 文件 | LOC | 说明 |
|------|-----|------|
| `test_context_checkpoints.py` | ~129 | CLI 元数据规则 |
| `test_runtime_failure_recovery.py` | ~100 | 恢复表形状 |
| `test_runtime_plan_reuse.py` | 326 | 计划复用 |
| `test_runtime_plan_registry.py` | 374 | 计划注册 |
| `test_runtime_preferences.py` | 68 | 偏好 |
| `test_runtime_decision_tables.py` | 368 | 决策表 |
| `test_runtime_skill_registry.py` | 380 | 技能注册 |
| `test_runtime_output_rendering.py` | 287 | 渲染输出 |
| `test_runtime_kb.py` | 164 | KB |
| `test_runtime_message_templates.py` | 76 | 消息模板 |
| `test_runtime_plan_scaffold.py` | 85 | 计划脚手架 |
| `test_bundle_smoke.py` | 85 | bundle smoke |
| `runtime_test_support.py` | ~150 | 测试支撑模块 |

## S3.2 阻塞表 (双口径)

### legacy-preserving 口径

| 阻塞项 | 涉及模块 | 解除条件 |
|--------|---------|---------|
| engine 是 gate/router/handoff 调用枢纽 | `engine.py` (2,728 LOC) | 不可解除；保留 legacy 则 engine 必须存在 |
| 宿主仍 import runtime 入口 | `__init__.py`, scripts/*.py | 不可解除；保留 legacy 则所有 runtime surface 必须存在 |
| installer 直接 import runtime | `inspection.py` L32-33 | 需先完成 inspection cutover |
| runtime tests 覆盖 engine 路径 | `test_runtime_engine.py` (3,666 LOC) | 不可解除；保留 legacy 则测试必须存在 |

**结论: legacy-preserving 下几乎无法删除任何 runtime 模块（高度耦合）。**

### target-state-first 口径

| 阻塞项 | 涉及模块 | 解除条件 |
|--------|---------|---------|
| installer/inspection.py import 级依赖 | `inspection.py` L32-33 | Step 1 第 1 个 cutover (已有方案) |
| installer/validate.py 路径级依赖 | `validate.py` L166-181 | Step 1 第 3 个 cutover (已有方案) |
| installer/bootstrap_workspace.py 路径级依赖 | `bootstrap_workspace.py` L102-117 | Step 1 第 4 个 cutover (已有方案) |
| scripts/sopify_init.py 能力声明 | `sopify_init.py` L27 | Step 1 第 2 个 cutover (已有方案) |
| scripts/install_sopify.py 文案 | `install_sopify.py` | Step 1 第 5 个 cutover (已有方案) |
| `_yaml.py` 被 kernel support config.py 依赖 | `_yaml.py` | Step 2 判定: 内联或保留 |
| `test_runtime_engine.py` 可能嵌入 kernel 不变量 | `test_runtime_engine.py` | Step 4 逐 case 人工审查 |
| release-preflight.sh 串联 runtime smoke 脚本 | `release-preflight.sh` L75-77 | Step 1b cutover: 移除或改写 runtime smoke 调用 |
| check-install-payload-bundle-smoke.py 冻结 runtime 脚本路径 | `check-install-payload-bundle-smoke.py` L144+ | Step 1b cutover: 改写路径期望值 |
| check-skill-eval-gate.py import runtime 模块 | `check-skill-eval-gate.py` L17 | Step 1b cutover: 改为 kernel 接口或删除 |
| generate-builtin-catalog.py import runtime 模块 | `generate-builtin-catalog.py` L17 | Step 1b cutover: 改为 sopify_contracts 或删除 |
| 非 test_runtime_* 测试冻结 runtime 路径/能力 | `test_installer.py`, `test_installer_status_doctor.py`, `test_action_intent.py` | Step 1b cutover: 同步改写期望值 |
| models.py 被 8 个内核模块 import | `models.py` | rewrite-first: 先改 8 个内核模块(core 5 + support 3)的 `from .models` → `from sopify_contracts`，再删；context_snapshot(优先拆分)也需同步改 |

**结论: target-state-first 下无硬阻塞，但 cutover 联动面比原估多 ~8-10 个文件（release 链 + 非 runtime 命名测试 + models.py rewire）。**

## S3.3 推荐策略

1. **采用 target-state-first 口径** — 维护者已于 2026-05-22 确认 (tasks.md 4.1 ✅)
2. **退场量级**: runtime/ 非 kernel ~18.8K + scripts co-delete ~1.3K + tests co-delete ~2.6K + test_runtime_engine ~3.7K(待审查) ≈ **~26.4K LOC** 直接退场；加上 kernel 瘦身砍掉的代码，总退场量 **~28K+ LOC**
3. **cutover 真实范围**: 原估 5 文件 (installer/scripts 解耦)；实际需加上 release 链 4 脚本 + 非 runtime 命名测试 3-5 个 + models.py rewire = **~12-15 个文件需 cutover**
4. **S4 执行优先级**: Step 2 cutover (installer/scripts 5 文件，inspection.py 第一刀) → release 链 cutover (4 脚本) → kernel extraction (含 models.py rewire + context_snapshot/handoff 拆分) → 非 kernel 批量删除 → in-place 入口 cutover → 等价覆盖测试 → 非 runtime 命名测试 cutover
5. **风险最低路径**: 先完成 installer cutover (inspection.py 第一刀) 保护安装链路 + release 链路，再做 runtime/ 内部 kernel extraction (models.py rewire + 瘦身)和批量删除
6. **test_runtime_engine.py 特殊处理**: 3,666 LOC 不做盲删，S4 先逐 case 审查是否有 gate/handoff 集成不变量需要提取

### 在范围内

1. `runtime/` 目录内模块、facade、builder、state 生产职责的现状梳理
2. `installer/`、`scripts/`、`tests/`、宿主路径对 `runtime` 的直接消费者扫描
3. 与 `sopify_contracts/`、`canonical_writer/` 的职责重叠与剩余耦合分析
4. 形成删除候选清单与整包退役阻塞项清单
5. 在审计完成并确认口径后，执行受控删除

### 不在范围内

1. 在未完成审计和口径确认前，直接大规模删除 `runtime` 代码
2. 修改 protocol / blueprint 的长期契约
3. 改写 installer 总体架构
4. 为了“删得动”而先引入新的 machine truth
5. 在未完成消费者扫描前，先修改 `plan_registry` 的 lifecycle contract

## 分类口径

## 决策前提

本审计默认同时保留两种判断口径：

1. **legacy-preserving**
   - 假设维护者决定继续维护 Codex/Claude deep runtime 路径或相关 installer/bundle 验证链
   - 此时现有 consumer 可能构成真实阻塞

2. **target-state-first**
   - 假设维护者接受 blueprint 目标态优先，允许 legacy consumer 与 runtime 一起退场
   - 此时“消费者存在”本身不构成阻塞，除非它命中 keep-list 或冻结 contract

因此，所有“不能删”的判断都必须回答一个附加问题：**这是契约性必须保留，还是仅仅因为当前仓库里还有一个可一起删除的 legacy consumer？**

### K. `extract-to-kernel`

满足以下条件的面应提取为 orchestration kernel 组成部分：

1. 属于 gate → route → handoff → checkpoint 编排闭环的最小必要模块
2. 不属于 output rendering、host bridge、bundle smoke、skill dispatch 等可由宿主或其他层承担的职责
3. 提取后可独立于 runtime 其余面运行，仅依赖 `sopify_contracts` 和 `canonical_writer`
4. 不要求保留完整 engine 全家桶

### A. `delete_now`

满足以下条件的面可直接进入下一实施包：

1. 不在 `blueprint/design.md` keep-list 内
2. 不承担冻结 contract 的生产职责
3. 无 runtime 主链、installer、scripts、tests、宿主路径消费者
4. 删除后不破坏当前 `payload_capable` / `deep_verified` 已声明能力
5. 删除后可由现有验证链或补充的最小验证动作证明无回归

### B. `keep_for_legacy_runtime`

满足以下任一条件的面，当前仍应保留为 legacy runtime 组成部分：

1. 仍承担 `current_*` / receipt / handoff 等冻结 contract 的生产职责
2. 在 **legacy-preserving** 前提下，仍被 Codex/Claude 老路径、installer、bundle smoke 或 runtime tests 直接消费
3. 属于 engine 耦合 builder，尚未有 `canonical_writer` 替代

注意：第 2 条只说明“若决定继续维护对应 legacy 路径，则它不能单独删除”；**不说明该路径本身必须保留**。

### C. `blocking_full_retirement`

这类不是“现在不能删一个文件”那么简单，而是整包下线 `runtime/` 的阻塞条件：

1. 在 **决定继续保留 legacy deep path** 的前提下，老宿主仍直接 import `runtime/*`
2. 某些冻结 contract 仍只能由 runtime builder 生成，且没有允许一并退场的替代策略
3. installer / smoke / release 验证仍要求 runtime 参考实现存在，且这些验证链本身被判定为要保留
4. 运行期 machine truth 的写入路径还没有完全从 runtime 脱钩

若某个“阻塞项”可以通过**同步删除对应 legacy consumer** 一并消失，则它应标为 `co-delete candidate`，而不是直接归入 `blocking_full_retirement`。

## 实施门槛

本包采用两阶段推进：

### Phase A: Audit

产出三张表与推荐策略，明确：

1. 哪些面属于 `delete_now`
2. 哪些面只在 `legacy-preserving` 前提下需要保留
3. 哪些面属于真正的 `blocking_full_retirement`

### Phase B: Controlled deletion

只有在 Phase A 完成后，才进入删除：

1. `delete_now` 可直接删除
2. `co-delete candidate` 仅在维护者确认 `target-state-first` 且明确批准同步退场范围后删除
3. `keep_for_legacy_runtime` 与 `blocking_full_retirement` 默认不在本包删除范围

这保证本包是“审计后开始删”，而不是“边审边盲删”。

### 删除量级预判

基于当前代码形态，需提前接受一个不对称现实：

1. **legacy-preserving**
   - 预计删除量很小
   - `runtime` 内部 54 个模块、约 23.8K LOC 高度耦合
   - 大部分模块会因为 engine / gate / state / handoff / route 主链关系，落入 `keep_for_legacy_runtime`

2. **target-state-first**
   - 预计删除量显著
   - 一旦允许 `scripts/*_runtime.py`、`tests/test_runtime_*`、bundle smoke、legacy bridge 与 `runtime/` 同步退场，删除规模会从“若干旧面”跃迁到“整条 deep runtime 路径”

因此，本包在 `target-state-first` 下的核心目标不应表述成“温和清理 runtime”，而应表述成：

- 判定是否可以让 **runtime 主线 + legacy deep consumers** 一起退场
- 明确退场后仓库的保留面（双栏分类）

### 保留面分类

| 类别 | 内容 | 条件 |
|------|------|------|
| **retain-as-is** | `sopify_contracts/`、`canonical_writer/`、`.sopify-skills/` | 无 runtime 代码依赖，可直接保留 |
| **retain-after-decoupling** | `installer/validate.py`、`installer/bootstrap_workspace.py`、`installer/inspection.py`、`scripts/install_sopify.py`、`scripts/sopify_init.py` | 当前仍有 runtime import / bundle 验证硬依赖，需先解耦 |
| **retain-as-kernel** | orchestration kernel 三层: kernel core (7 模块) + kernel support (3 模块) + 优先拆分 context_snapshot；gate_output 非内核可暂留。详见 §S3 Kernel Boundary Audit | 在 `runtime/` 原地瘦身保留最小编排闭环，删除其余面 |

retain-after-decoupling 的已知耦合点：

1. `installer/validate.py` L166-171 — 必需文件列表含 `runtime/*.py`
2. `installer/bootstrap_workspace.py` L102-111 — bundle manifest 含 `runtime/` 和 `scripts/*_runtime.py`
3. `installer/inspection.py` L32 — `from runtime.config import ...`
4. `scripts/install_sopify.py` L51-52 — 用户面描述仍把 Codex/Claude 安装面表述成“Sopify runtime”
5. `scripts/sopify_init.py` L27 — `_WORKSPACE_CAPABILITIES = ["preferences_preload", "runtime_gate"]`

这些耦合点在 Phase B 删除 runtime 时必须同步修正，否则安装链路立即断裂。

额外判定：

1. `installer/runtime_bundle.py` 是 pure legacy runtime bundle surface，不属于 retain-after-decoupling，应在 runtime 退场时直接同步删除
2. `scripts/sopify_status.py` / `scripts/sopify_doctor.py` 不列入独立解耦清单；它们只是 `installer/inspection.py` 的薄入口，变化应由 inspection cutover 吸收

### Step 2 Cutover 表（5 文件）

| 文件 | 当前 runtime 耦合 | cutover 动作 | 替代依据 / 替代能力 | cutover 后保留行为 |
|---|---|---|---|---|
| `installer/validate.py` | bundle 必需文件列表含 `runtime/`、`scripts/*_runtime.py`、`tests/test_runtime.py`；stub 默认能力为 `runtime_gate` / `preferences_preload` | 删除 runtime bundle 路径校验与 runtime smoke 假设；把 workspace/stub 校验切到 payload-only 能力口径 | `.sopify-skills/sopify.json`；payload / bundle manifest 的稳定能力字段；`state_write` + `handoff_consume` | 继续负责安装后结构校验，但不再验证 deep runtime entry |
| `installer/bootstrap_workspace.py` | materialize / compare `.sopify-runtime/` bundle；要求 `runtime/`、`*_runtime.py`、`test_runtime.py`；legacy fallback 仍围绕 workspace runtime | 停止把 workspace 视为 vendored runtime bundle；收敛到 payload-first bootstrap + workspace marker | `.sopify-skills/sopify.json`；payload manifest；P7 payload-only onboarding 主线 | 继续负责 workspace bootstrap，但不再写入或校验 workspace runtime bundle |
| `installer/inspection.py` | 直接 import `runtime.config` / `runtime.context_snapshot`；状态诊断围绕 runtime bundle、runtime_gate、workspace runtime health | 改为 payload-only / canonical-state inspection；去掉 runtime gate 和 workspace bundle 专属诊断 | `canonical_writer` + `sopify_contracts` 的 canonical state 文件；payload/stub 元数据；workspace marker | `status` / `doctor` 继续可用，但只报告 payload、workspace marker、canonical state 健康 |
| `scripts/install_sopify.py` | 文案、成功路径和验证链仍默认“安装 Sopify runtime” | 更新为 payload-only / control-plane 安装叙事；不再把 runtime 作为保留能力宣传 | P7 的 payload-only onboarding 口径；payload install + bootstrap + inspection | 保留为官方安装入口，但不再承诺 deep runtime 能力 |
| `scripts/sopify_init.py` | `capabilities = [\"preferences_preload\", \"runtime_gate\"]`；ignore block 含 `.sopify-runtime/` | 改写 workspace marker 能力口径，去掉 runtime gate 声明与 legacy runtime 遗留项 | `.sopify-skills/sopify.json`；`state_write` + `handoff_consume` | 保留为 workspace 初始化入口，但只声明 payload-only 能力 |

Step 2 的边界故意收紧：

1. 只处理上表 5 个文件
2. 不把 `installer/runtime_bundle.py` 放进“解耦后保留”
3. 不单独列 `scripts/sopify_status.py` / `scripts/sopify_doctor.py`
4. 不在这一阶段保留任何 legacy `*_runtime.py`；若 kernel 仍需 host-facing 最小链路，只允许新增全新薄壳入口，不沿用旧 bridge/helper

### Step 2 执行顺序

Step 2 不按“改动最小优先”，而按“最硬 runtime 依赖优先”推进：

1. `installer/inspection.py`
   - 原因：这是 5 个文件里唯一的 **import 级** runtime 依赖（`from runtime.config ...` / `from runtime.context_snapshot ...`）
   - 若它不先 cutover，后续一旦 runtime 退场，`status` / `doctor` 会先于其他面发生 import failure
2. `scripts/sopify_init.py`
   - 先收敛 workspace marker 的 capability 口径
3. `installer/validate.py`
   - 再收敛 required files / required capabilities
4. `installer/bootstrap_workspace.py`
   - 最后再处理最重的 workspace bootstrap / bundle materialization 分支
5. `scripts/install_sopify.py`
   - 在前面 4 个结构和验证入口稳定后，统一更新用户面叙事与安装链路入口

该顺序的目标不是减少编辑次数，而是避免出现“字符串级耦合都改完了，但 `inspection.py` 还在 import `runtime.*`，导致 Step 3 一删 runtime 就炸”的假收敛。

### 当前包继续承接，不新开包

当前主题继续使用本包推进，orchestration kernel extraction 作为本包内执行目标。

原因：

1. `target-state-first` + kernel extraction 已锁定，本轮主线是 kernel 提取 + 非 kernel 面退场
2. 新开包会把 kernel 定义与退场执行切开，导致上下文割裂
3. kernel 的具体模块边界由 S2/S3 审计确定，不预设

### 退场量级（修正后，含 kernel 提取）

| 退场对象 | 文件数 | LOC | 备注 |
|---|---|---|---|
| `runtime/` 非 kernel 面 | ~42 | ~18.8K | 原 54 文件 23.8K，减去 kernel 12 模块 ~5K（瘦身前）；瘦身后 kernel ~2.5K，退场量更大 |
| runtime-coupled scripts | ~12 | ~4K | |
| runtime-coupled tests | ~17 | ~15.3K | |
| **合计（预估）** | **~71** | **~38K** | 原估 43K，减去 kernel ~2.5K（瘦身后）+ kernel tests ~2.5K（重建不删） |

## 输出物设计

本方案期望输出三类结果：

1. **删除候选表**
   - 文件 / 符号
   - 当前消费者
   - keep-list 命中情况
   - 建议动作

2. **整包退役阻塞表**
   - 阻塞项
   - 对应模块
   - 解除条件
   - 依赖的后续任务

3. **consumer 决策表**
   - consumer
   - 当前用途
   - 契约命中情况
   - 分类：`must_keep` / `keep_if_preserving_legacy` / `co-delete_candidate`

4. **实施记录**
   - 已删除文件 / 符号
   - 对应分类依据
   - 验证结果

5. **建议后续切片**
   - `runtime old-surface cleanup`
   - `legacy host consumer migration`
   - `runtime producer extraction`

6. **保留面清单（target-state-first 后）**
   - 退场后仍需保留的模块 / 文件
   - 保留理由
   - 与 runtime 的断开方式
7. **retain-after-decoupling cutover 表**
   - 仅覆盖 5 个文件
   - 明确当前耦合、替代依据、保留后的行为边界

## 审计副发现处理

当前已知一个与本主题强相关、但不应抢跑修改的副发现：

- `deferred` 生命周期语义在 `project.md`、plan frontmatter、`_registry.yaml` / `plan_registry.py` 之间不一致

本次处理原则：

1. 记录为审计 delta
2. 在消费者扫描中补充 `plan_registry.py` 的真实行为与覆盖范围
3. 在推荐策略阶段再决定：
   - 扩 registry contract 支持 `deferred`
   - 还是收紧长期文档，不再把 `deferred` 当作 lifecycle 真值

在此之前，不做“手工改 `_registry.yaml` 统一一下”这种会被 reconcile 覆盖的表面修补。

## 架构设计

审计读取顺序：

1. `blueprint/design.md`
   - 三层定位
   - persistence red line
   - keep-list
   - runtime retirement 路线
2. `history/2026-05/20260509_p4b_*`
3. `history/2026-05/20260510_p4b5_*`
4. `history/2026-05/20260520_p5_*`
5. `history/2026-05/20260520_p6_*`
6. 当前代码消费者扫描

判定原则：

- 蓝图判断“什么合法”
- 代码判断“现在谁还在用”
- 决策再判断“这个 consumer 是不是值得继续保留”
- 只有三者都支持删除，才进入 `delete_now`
- 删除阶段只消费 `delete_now` 与经确认的 `co-delete candidate`

## 安全与性能
- 安全: 先审计、再确认、后删除；不允许未分类面直接进入删除。
- 性能: 以 `rg` 和定向文件读取为主，避免全仓库无差别深扫。
