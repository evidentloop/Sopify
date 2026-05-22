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

## 审计边界

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
| **retain-as-kernel** | orchestration kernel（待 S3 审计确定具体模块：gate / route / handoff / checkpoint state） | 在 `runtime/` 原地瘦身保留最小编排闭环，删除其余面 |

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
| `runtime/` 非 kernel 面 | 待 S3 定 | 待 S3 定 | 原 ~54 文件 ~23.8K；kernel 提取后剩余面退场 |
| runtime-coupled scripts | ~12 | ~4K | |
| runtime-coupled tests | ~17 | ~15.3K | |
| **合计（预估）** | **待 S3 定** | **<43K** | 原估 ~43K，减去 kernel 保留量 |

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
