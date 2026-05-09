# 变更提案: P4b Runtime Surface Consolidation

## 需求背景

P4a 已冻结外部消费面 keep-list（15 条），Host Capability Governance bridge 已落地。现在有明确的红线边界：keep-list 内保留，keep-list 外默认可删。

当前 `runtime/*.py` 共 25,534 LOC，55 个 .py 文件。蓝图目标 <20,000 LOC，需削减 ~5,500+ LOC。

### 削减预算实况

两轮代码审计结论：

| 削减来源 | 估算 LOC | 备注 |
|----------|---------|------|
| engine.py 旧路由/bridge/checkpoint 胶水 | 1,200–1,800 | 最大单点；需逐段验证 |
| failure_recovery.py legacy 恢复路径 | 250–400 | 明确的 legacy 快照处理 |
| decision_bridge.py 全文或大部分 | 180–220 | CLI fallback/text renderer bridge |
| workspace_preflight.py fallback/legacy | 220–320 | 最强 fallback 文件 |
| clarification_bridge.py 全文或大部分 | 140–180 | host-side bridge helper |
| plan_orchestrator.py bridge 胶水 | 120–180 | CLI/bridge wrapper |
| context_snapshot.py compat 字段 | 50–80 | legacy global review state |
| router.py 旧分支 | 40–80 | old-branch classification |
| gate.py legacy wrapper/fallback | 15–30 | action_proposal_retry 主路径在 keep-list（blueprint design.md:354），不可删；仅删周边 legacy 分支 |
| message_templates.py 模板精简 | 20–60 | 渲染模板胶水 |
| action_intent.py fallback | 20–40 | decision fallback router |
| 其他散布 compat | 100–200 | archive_lifecycle, context_v1_scope 等 |
| **合计** | **2,355–3,590** | **实际：15 LOC** |

**P4b-close 结论**：prove-kept-or-delete 全量扫描证明，原估计基于错误假设（fallback/bridge/compat 被视为"可删旧面"，实际多已变为 machine contract / distribution contract / hard gate 保护面）。实际死代码仅 15 LOC。最终 baseline：24,334 LOC。详见 design.md Phase 2 执行结论。

## 与蓝图里程碑的关系

- **定位**：P4b Runtime Surface Consolidation（tasks.md P4b 节）
- **前提**：P4a freeze 已完成（keep-list 是红线）
- **下游**：P4c Host Consumption Governance（P4b 减完旧面后 P4c 治理范围更小）

## Plan Intake Checklist

1. **主命中里程碑**：P4b
2. **改动性质**：runtime code reduction — 删除 compat/bridge/fallback/dead code
3. **Machine truth 变更**：无。不改 machine contract、不改 protocol 语义、不扩 canonical budget
4. **Legacy surface**：大量 legacy surface 将被删除
5. **Core promotion rule / hard max 影响**：无（削减预算表的 target/hard max 不变）
