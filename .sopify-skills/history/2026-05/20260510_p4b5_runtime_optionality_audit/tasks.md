# 任务清单: P4b.5 Runtime Optionality & Host Onboarding Audit

lifecycle_state: active
plan_status: drafting
蓝图命中: P4b.5（tasks.md:60-66）
前置里程碑: P4b（已完成）、Host Capability Governance bridge（已完成）

## Plan Intake Checklist

1. **主命中哪个蓝图里程碑？** → P4b.5 runtime_optionality_audit
2. **定义的是 contract acceptance boundary 还是 execution strategy？** → contract acceptance boundary（消费矩阵 + forbidden surface）→ 结论进 blueprint
3. **是否新增/删除/替代 machine truth？** → 否。只对现有 machine truth 做层级归位
4. **若涉及 legacy surface，替代 contract 是否已稳定？** → N/A，不涉及替代
5. **若影响 Core promotion rule / hard max / ownership / validator authority？** → 不影响

## 文档顺序（按依赖关系）

S1 → S2 → S3 → S4

- S1 Forbidden surface 是 S2 consumption matrix 的前提（先知道"不能碰什么"才能定义"能碰什么"）
- S2 的接续/授权/checkpoint 三分类是 S3 blast radius 的输入
- S3 的审计结论是 S4 P4c boundary 的依据

## 任务

### S1: Forbidden Surface 正面化

- [x] 1.1 从 design.md:340, 366 收集所有隐式 forbidden 面
- [x] 1.2 从 design.md:368-393 Output Rendering Audit 收集已标记为 internal_taxonomy_leak 的面
- [x] 1.3 将收集结果整理为显式禁止清单（适用所有三级梯度）
- [x] 1.4 写入 blueprint/design.md Host Capability Governance 节

### S2: Consumption Matrix

- [x] 2.1 对接续锚点三件套（handoff / run / plan）在每级梯度归位
- [x] 2.2 对授权凭证三件套（gate_receipt / ExecutionAuthorizationReceipt / archive_receipt）在每级梯度归位
  - 包括裁定 gate_receipt 消费者投影差异（design.md:354 vs 364）
  - EAR 归位理由不得以"无 runtime"为由，须以"该梯度是否承诺消费此协议面"为判据
- [x] 2.3 对 pending checkpoint（clarification / decision）在 payload_capable 做 required / optional / forbidden 裁定
- [x] 2.4 对长期知识面（blueprint / plan / history / protocol / preferences）确认所有梯度 readable
- [x] 2.5 物化 payload_capable 内部 opt-in 增强组合：产出一张组合表，至少覆盖接续增强 / 交互增强 / 审计增强 3 组 canonical 组合；每组定义消费哪些 contract、支持什么场景、组合间依赖链与互斥关系
- [x] 2.6 将完整矩阵 + 增强组合写入 blueprint/design.md

### S3: Blast Radius 审计

- [x] 3.1 列出 runtime/ 所有顶层模块
- [x] 3.2 对每个模块评估在每级梯度的必需性（需要 / 不需要）
  - 严守"生产者 vs 消费者"区分：新宿主消费持久化 contract 文件不等于接入契约上依赖 runtime 模块
- [x] 3.3 写入审计结论

### S4: P4c Boundary Statement

- [x] 4.1 从 S1-S3 提取 P4c 可假设的 invariant
- [x] 4.2 从 S2 的裁定结果推导 P4c 需做的实施项
- [x] 4.3 从 forbidden surface 推导 P4c 不能做的事
- [x] 4.4 更新 blueprint/tasks.md P4c 段，补充验收前提

### 收尾

- [x] 5.1 自检：方案包内容是否与 design.md 现有 ladder 一致（不重定义）
- [x] 5.2 自检：是否有任何"实现层变更"混入（不改代码/schema）
- [x] 5.3 提交方案包
