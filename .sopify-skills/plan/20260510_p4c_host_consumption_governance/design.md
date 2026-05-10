# 设计: P4c Host Consumption Governance

## 切片架构

```
P4c-1 契约投影层
  │
  ├──→ P4c-2 增强声明/检测层（硬依赖：引用 P4c-1 的 FeatureId 体系）
  │
  └──→ P4c-3a 渲染与 truth-source 收敛层（弱依赖：deep_verified 裁定可能影响渲染）
       P4c-3b 首接触与 prompt 收敛层（与 3a 可拆开执行）
                                                    ‖ 并行
                                         P4c-4 文档与披露层
                                                    │
                              P4c-3b + P4c-4 ───→ P4c-5 Prompt Asset 结构收口
```

执行序：P4c-1 → P4c-2 + P4c-3a（可并行）→ P4c-3b ‖ P4c-4（可并行，但 P4c-4 中依赖 AGENTS.md 最终文本的部分需 3b 稳定后收口）→ P4c-5（可选收口）

## P4c-1: 契约投影层

**问题**：消费矩阵（design.md S2）停留在"人类可读表格"，没有翻译成机器可检查的映射。deep_verified 列还有"预期 required†"待裁定。

**交付**：
1. FeatureId → 梯度投影矩阵：每个可消费 contract 面有唯一 FeatureId，映射到 convention_only / payload_capable / deep_verified 各自的 required / optional / forbidden
2. deep_verified "预期 required†" 最终裁定：逐项确认是 required 还是 optional，消除 †

**边界**：
- 不新增 state 文件，投影矩阵是 metadata（不是 machine truth）
- 不改 ladder 准入定义
- 格式待裁定（YAML？design.md 内联表？独立 JSON schema？）
- **Gate**：格式和权威存放位置（任务 1.2）必须先定，否则后续编写和落地可能返工

**验收**：
- 消费矩阵中每个"预期 required†"都已变成 required 或 optional（不含 †）
- 投影矩阵有唯一权威存放位置，消费方式明确
- 投影矩阵与 P4b.5 消费矩阵一致（不矛盾）

## P4c-2: 增强声明/检测层

**问题**：P4b.5 定义了三组 opt-in 增强（接续/交互/审计），但宿主没有标准方式声明自己启用了哪组。系统也没有检测/校验机制。

**交付**：
1. 增强声明协议：宿主通过什么机制告诉系统"我支持接续增强"？选项空间：
   - 宿主 manifest 字段
   - installer bridge config
   - 无显式声明，按能力检测（文件是否存在）
2. 增强校验逻辑：系统如何验证宿主声明与实际能力一致
3. 本地可验证样例或参考接入证明，证明声明方式与检测逻辑可跑通

**边界**：
- 依赖 P4c-1 的 FeatureId 体系
- 不新增 machine truth
- 不改 installer 的核心安装流
- 校验可以是 advisory（警告而非阻断），具体策略待裁定
- **不做宿主真实接入试点**：真实宿主适配器演示属 P4d。P4c 只做定义 + 本地验证

**验收**：
- 有文档化的增强声明方式
- 声明方式与消费矩阵、投影矩阵一致
- 有本地可验证样例证明声明 + 检测逻辑可跑通

## P4c-3a: 渲染与 truth-source 收敛层

**问题**：output / doctor / handoff 渲染仍混合 forbidden surface leak 和 truth source 越界。

**交付**：

1. **Output contract convergence**：
   - 状态符语义：canonical route family → 符号映射
   - Next 降级：明确为 human hint，宿主消费 handoff 不依赖 Next
   - Changes 重定义：loaded_files 从 Changed 中拆出
   - Gate 行简化：默认输出不暴露 gate 三元组

2. **doctor/status 只渲染 truth**：不作为 truth source

3. **handoff rendering 只消费结构化字段**：不做语义推断

**边界**：
- 涉及 output.py / message_templates / doctor 渲染
- 不改 contract 文件 schema（P4a 保护）
- 验证方式：output 相关测试 + 手工对比

**验收**：
- output 默认渲染中无 F3-F7 forbidden surface 值直接暴露
- doctor/status 只读取 machine truth 渲染，不衍生新 truth
- handoff 渲染只消费 current_handoff.json 结构化字段

## P4c-3b: 首接触与 prompt 收敛层

**问题**：首接触路径暴露 blueprint/checkpoint taxonomy 等内部概念；prompt 可能定义 route taxonomy。

**交付**：

1. **首接触感知收敛**：
   - 新用户只感知"中断可恢复"+"需要拍板时会停"
   - doctor/status 不主动呈现 checkpoint taxonomy
   - ~go 入口不前置 blueprint 概念

2. **prompt 不定义机器契约**：prompt 内容不定义路由表、不维护 state 写入语义

3. **F5/F6 leak 消除**：移除 Entry Guard Reason 等内部守卫码直接暴露；消除 route_name / taxonomy 在 prompt 及默认可见路径中的直接暴露

**边界**：
- 涉及宿主 prompt asset（AGENTS.md / CLAUDE.md）和部分 runtime 渲染
- 与 P4c-3a 可拆开执行，但同属可见面收敛大主题

**验收**：
- 首接触路径无 blueprint/checkpoint taxonomy 主动暴露
- prompt 内容中无 route taxonomy 定义或 state 写入语义指令
- 无 F5/F6 直接暴露

## P4c-4: 文档与披露层

**问题**：接入文档入口分散，builtin skill 能力未稳定表达，design.md 需要结构整理。

**交付**：
1. **protocol.md 唯一合规入口**：接入文档统一指向 protocol.md
2. **文档递进顺序**：Layer 0 Protocol ≤120 行 → Layer 1 Gate → Layer 2 Phase → Layer 3 Reference（不进 prompt）
3. **Builtin skill capability disclosure**：AGENTS.md 只做消费投影，builtin_catalog 为唯一 truth source
4. **design.md 结构整理**（非阻塞收口项）：若前述切片稳定，将 S1-S4 增量段内化为稳定章节结构

**边界**：
- 不改代码（除非 AGENTS.md 生成逻辑需调整）
- 不预设 builtin skill 独立调用（需先有 invocation contract）
- 与 P4c-3a/3b 可并行
- 4.4 design.md 结构整理不阻塞其他切片

**验收**：
- 新宿主接入者从 protocol.md 出发，可沿递进层级逐层深入
- AGENTS.md 内容与 builtin_catalog 一致
- design.md Host Capability Governance 节为稳定章节结构（非 S1/S2/S3/S4 增量追加）

> **P4c-4 与 P4c-5 边界**：P4c-4 只验语义与 truth-source 一致性，不验 prompt asset 的结构瘦身；AGENTS.md / CLAUDE.md 的重排、压缩、镜像对齐统一归 P4c-5。

## P4c-5: Prompt Asset 结构收口（非阻塞收口项）

**问题**：P4c-3b 和 P4c-4 完成语义收敛后，AGENTS.md / CLAUDE.md 仍可能结构臃肿（当前各 ~466-468 行）。重复段落、长段说明堆砌、参考信息与硬契约混排等问题需要整理。

**定位**：在 P4c-3b 与 P4c-4 语义收敛完成后，对 AGENTS.md / CLAUDE.md 做零语义漂移的结构整理，降低臃肿度和重复度，使 prompt asset 更适合作为稳定消费投影层。此切片不新增治理结论，不改变任何 contract 含义，不阻塞 P4c 主链验收。P4c-5 不是 P4c 主链验收前提；仅当前 1-4 切片已完成且仍有预算时执行。若未执行，不影响 P4c 主链收口。

**可以做**：
1. 把已经被 P4c-3b / P4c-4 裁清的内容重新分层
2. 抽掉重复段落，压缩长段说明
3. 把"硬契约 / 宿主行为 / 参考说明"拆成更稳定结构
4. 对齐 CN / EN 镜像结构
5. 让 AGENTS.md / CLAUDE.md 更像"消费投影"，不再像"内嵌参考手册"

**不能做**：
1. 不新增任何 machine contract
2. 不新增任何 host capability 定义
3. 不重开 builtin skill 语义
4. 不引入 skill-standards-refactor 全量目标
5. 不借机改 route / checkpoint / state 语义
6. 不阻塞 P4c 主链验收

**验收**：
- AGENTS.md / CLAUDE.md 结构更清晰，重复度降低
- 语义与 P4c-3b / P4c-4 完成后的版本完全一致（零语义漂移）
- CN / EN 镜像结构对齐

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| P4c-1 投影矩阵格式争议 | 阻塞 P4c-2 | 1.2 前置为硬 gate，先定载体再写内容 |
| P4c-3a output 改动范围失控 | 切片过大 | 按 output 子项逐个推进，发现过大时再拆 |
| P4c-2 增强检测机制过度设计 | 偏离审计路线 | 最小可行：文件存在检测 + manifest 声明，不做自动化 |
| P4c-3a output 改动引入回归 | 测试失败 | 先跑 baseline 测试，改动后对比 |
| P4c-2 越界到 P4d 试点 | 职责串线 | 只做本地可验证样例，不做真实宿主适配器演示 |
| P4c-5 滑入语义重构 | scope 污染 | 严格零语义漂移，只做结构重排；gate: P4c-3b + P4c-4 完成后才进入 |
