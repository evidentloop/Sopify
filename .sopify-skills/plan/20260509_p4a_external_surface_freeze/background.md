# 变更提案: P4a External Surface Freeze

## 需求背景

P3b 完成了外围清理（replay 下线、tests 分类、README 降噪、release gate 修复）。当前 runtime 约 25K LOC，P4b 目标减至 <20K。但 P4b 不能盲砍——需要先确认"哪些面是外部消费者依赖的，不可删"。

P4a 的唯一目的是**画出不可删红线**，为 P4b 减重和 P4c 宿主消费治理提供硬边界。

## 与蓝图里程碑的关系

- **P4a**（tasks.md）：本方案包是 P4a 的完整执行包
- **前提**：P3b 已完成（外围面已清理）
- **下游**：P4b（Runtime Surface Consolidation）消费 keep-list 作为减重红线；P4c（Host Consumption Governance）消费 output.py 审计分类作为收敛输入

## Plan Intake Checklist

1. **主命中里程碑**：P4a（External Surface Freeze）
2. **改动性质**：contract acceptance boundary — 冻结外部消费面定义，不做实现变更
3. **Machine truth 变更**：无。不新增、删除、替代任何 action / route / state / checkpoint / receipt
4. **Legacy surface**：不涉及
5. **Core promotion rule / hard max 影响**：无
