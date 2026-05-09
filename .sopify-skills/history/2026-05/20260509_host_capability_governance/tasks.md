---
plan_id: 20260509_host_capability_governance
feature_key: host_capability_governance
level: standard
lifecycle_state: archived
knowledge_sync:
  project: skip
  background: skip
  design: update
  tasks: update
archive_ready: true
plan_status: completed
---

# 任务清单: 第三方宿主能力边界治理（P4a→P4c bridge）

## 当前阶段目标

定义宿主能力梯度和准入规则，产出治理结论供 P4c 消费。纯文档/设计变更，不改运行代码。

## S1: 治理结论落地

- [x] 1.1 tasks.md 长期项"第三方 CLI 宿主能力边界治理"标记为已设计，关联本方案包
- [x] 1.2 blueprint/design.md 新增 Host Capability Ladder 表（3 级 canonical 梯度定义 + 与 SupportTier 的 legacy 映射关系）
- [x] 1.3 blueprint/design.md 新增接入判定 Checklist（覆盖蓝图全部边界：官方入口 / payload 落点 / repo-local 优先级 / skills 目录支持）
- [x] 1.4 blueprint/design.md 定义 Convention Quickstart 最小交付面（adoption guide / reading order，非 normative 内容）
- [x] 1.5 blueprint/design.md 定义 Prompt 镜像治理原则（prompt asset 属于 payload/install surface；现有目录树是 legacy exception）

## 完成标准

- [x] 3 级梯度定义清晰，每级有明确进入条件
- [x] 接入判定 Checklist 可独立执行（不依赖口头知识）
- [x] Convention Quickstart 最小交付面有明确边界（是什么/不是什么）
- [x] Prompt 镜像治理原则明确（新宿主不进现有目录树）
- [x] 无运行代码变更
