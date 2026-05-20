---
plan_id: 20260520_p5_contract_surface_shrinkage
feature_key: p5_contract_surface_shrinkage
level: standard
lifecycle_state: active
---

# 任务清单

## S1: Deep-Only Surface 全量清点 ✅

- [x] Runtime 模块级扫描：标注每个模块的外部消费者类型（deep_verified / cross-tier / internal）
- [x] Installer 面清点：HostAdapter, payload bundle, SupportTier 映射
- [x] Manifest/Bridge 面清点：FeatureId, capability projection, bridge capability
- [x] Output 渲染面清点：deep-only 渲染逻辑 vs 通用渲染
- [x] 输出 `surface_inventory.md`（两轮：模块级 + 行级 sub-surface 拆分）

## S2: 证据依赖消费

> P5 消费以下证据型候选的结论，不拥有其执行。

### 依赖 1: Shadow Writer Gap Analysis

- [ ] 确认证据已就绪（或标记为 pending，先出 provisional 裁定）
- [ ] 消费 A/B/C 结论，映射到 S3 裁定表
- [ ] 消费 canonical writer authority 轴建模建议

### 依赖 2: Copilot Payload-Only Onboarding Proof

- [ ] 确认证据已就绪（或标记为 pending，先出 provisional 裁定）
- [ ] 消费 onboarding 可行性结论 + 卡点清单，映射到 S3 裁定表

## S3: 裁定表 (provisional 已产出)

- [x] 消费 S1 产出，生成 provisional 裁定表（58 面 × 4-way 裁定 × evidence_status）→ `provisional_adjudication.md`
- [x] 确定最小必留面清单 + candidate extractable kernel 形状（~680 LOC, 5 面 pending-shadow-writer）
- [ ] S2 证据就绪后，将 provisional 升级为 final 裁定表
- [ ] 用户确认 final 裁定表

## S4: 执行裁定

- [ ] 低风险项执行（明确 deep-only 的标记/降级/删除）
- [ ] 高风险项执行（需 shadow writer 结论支撑的面）
- [ ] 执行后测试套件回归验证
- [ ] design.md / protocol.md 同步更新（如有 contract 面变更）

## S5: 结论报告

- [ ] 标准 receipt 格式
- [ ] 裁定表执行结果
- [ ] 最小必留面清单（P6 输入）
- [ ] LOC 变化量统计
- [ ] 归档至 history/

## 决策记录

（执行过程中填写）
