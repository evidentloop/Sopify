# 变更提案: 第三方宿主能力边界治理（P4a→P4c bridge）

## 需求背景

P4a freeze 已完成，外部消费面 keep-list 已落地。P4c 需要做宿主消费治理（prompt 不定义 machine truth、doctor/status 只渲染 truth、handoff rendering 只消费结构化字段）。但 P4c 目前缺少一个前置输入：什么样的宿主可以以什么级别接入？

蓝图的治理方向是 3 级 canonical 梯度：convention_only / payload_capable / deep_verified。这是产品真相层。当前 `installer/models.py` 的 4 级 `SupportTier`（deep_verified / baseline_supported / documented_only / experimental）是实现层枚举，应被视为 legacy projection。

本 bridge 的职责：先冻结 canonical 梯度定义，再把 SupportTier 降级为实现层映射。代码对齐留给后续里程碑。

如果不先定义清楚，P4c 落地时就会边做边发明"什么宿主算哪一级"，团队会先问"落哪个 enum"而不是"满足哪个 contract"，甚至把"能读 AGENTS.md"误判为"应成为官方 target"。

## 与蓝图里程碑的关系

- **定位**：tasks.md 未完成长期项"第三方 CLI 宿主能力边界治理（P4a→P4c bridge）"
- **前提**：P4a freeze 已完成
- **下游**：P4c（Host Consumption Governance）消费本包结论，为 convention_only 第三方宿主保留合法位置

## Plan Intake Checklist

1. **主命中里程碑**：P4a→P4c bridge（长期项，不属于 P4b/P4c 正文）
2. **改动性质**：contract acceptance boundary — 定义宿主能力梯度和准入规则
3. **Machine truth 变更**：无。不新增、删除、替代任何 action / route / state / checkpoint / receipt
4. **Legacy surface**：SupportTier 4 级体系将被定义为 legacy projection；本包不改代码，只做设计决策
5. **Core promotion rule / hard max 影响**：无
