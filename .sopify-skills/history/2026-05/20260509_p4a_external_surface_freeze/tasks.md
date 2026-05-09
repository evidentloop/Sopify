---
plan_id: 20260509_p4a_external_surface_freeze
feature_key: p4a_external_surface_freeze
level: standard
lifecycle_state: archived
knowledge_sync:
  project: skip
  background: skip
  design: update
  tasks: skip
archive_ready: true
plan_status: completed
---

# 任务清单: P4a External Surface Freeze

## 当前阶段目标

冻结不可删外部消费面 keep-list，为 P4b 减重和 P4c 宿主消费治理提供硬边界。纯文档变更，不写运行代码。

## S1: Frozen External Surface 表

- [x] 1.1 design.md 新增 "Frozen External Surface" 节，定义表结构（6 列）
- [x] 1.2 逐条填入 protocol.md normative surfaces（Verifier、ExecutionAuthorizationReceipt、Subject Identity）
- [x] 1.3 逐条填入 gate_receipt 宿主可消费字段（current_gate_receipt.json schema）
- [x] 1.4 逐条填入 handoff machine truth（current_handoff.json 宿主可消费字段子集，不冻 Python API）
- [x] 1.5 逐条填入 archive truth 持久化/导出字段（ArchiveCheckResult + ArchiveApplyResult）
- [x] 1.6 逐条填入 install contract（SOURCE_CHANNEL / SOURCE_REF / --ref）
- [x] 1.7 逐条填入 builtin_catalog contract（generated.json schema / metadata contract；明确标注不冻具体 skill 枚举和 Python API 签名）
- [x] 1.8 逐条填入 skill_eval gate（门禁存在性 + baseline/SLO artifact contract；明确标注不冻具体维度 taxonomy 或分数阈值）
- [x] 1.9 逐条填入 persistence surface 红线（基于已有分层表，补充 freeze_level）

## S2: output.py 字段审计表

- [x] 2.1 design.md 新增 "Output Rendering Audit" 节，定义审计表结构（3 列 + 可选 note）
- [x] 2.2 逐字段填入 output.py 渲染内容分类（不做动作决策，动作留给 P4c）
- [x] 2.3 标注已知热点：gate 三元组 leak、Changes 混层、Next 推导、phase label

## 完成标准

- [x] design.md Frozen External Surface 表覆盖所有外部消费者依赖的 surface
- [x] 每行 non-goals 列不为空（防过度冻结）
- [x] design.md Output Rendering Audit 表覆盖 output.py 所有渲染字段（只分类，不含动作决策列）
- [x] 无运行代码变更
- [x] pytest 不受影响（纯文档变更）
