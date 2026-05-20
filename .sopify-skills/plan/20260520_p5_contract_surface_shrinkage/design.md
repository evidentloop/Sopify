# 技术设计: P5 Contract Surface Shrinkage

## 技术方案

### 总体策略

按 "清点 → 证据收集 → 裁定 → 执行" 四步推进。先做全量清点（哪些面只有 deep host 在用），再用证据型候选的产出填补未验证项，然后出裁定表，最后执行删/降级。

### 待裁定的 Surface 分类

| 分类 | 说明 | 来源 |
|------|------|------|
| **Runtime 状态管理面** | state machine, route engine, gate controller | P4b 审计 |
| **Installer 面** | HostAdapter, payload bundle, home_root 部署 | P4d D3 |
| **Manifest/Bridge 面** | SupportTier enum, FeatureId, capability projection | P4c |
| **Handoff 生产面** | RuntimeHandoff writer, RunState writer, DecisionState writer | P4d S3.5 (未验证) |
| **Output 渲染面** | output.py 中 deep-only 渲染逻辑 | P4c 渲染收敛 |

### S1: Deep-Only Surface 全量清点

遍历 runtime 代码 (~24K LOC)，标注每个 public surface 的消费者：

| 消费者类型 | 判定逻辑 |
|-----------|---------|
| deep_verified only | 仅 Codex/Claude adapter 调用，convention/payload 宿主不触达 |
| cross-tier | 所有梯度宿主都可能消费（通过 contract/protocol） |
| internal | runtime 内部调用，无外部消费面 |

**输出**：`surface_inventory.md` — 每个面的名称、消费者类型、当前状态、初步裁定建议

### S2: 证据依赖（P5 消费，不拥有）

> P5 依赖以下证据型候选的产出作为裁定输入。这些项目在蓝图 tasks.md 中独立注册为证据型候选，P5 消费其结论，不拥有其执行。如果证据尚未就绪，P5 可先基于 S1 清点出 provisional 裁定，证据到位后修订。

#### 依赖 1: Shadow Writer Gap Analysis

**P5 需要的结论**：convention-mode 宿主能否自产 canonical handoff（A/B/C 结论）+ canonical writer authority 轴是否需要独立建模。

**如何影响裁定**：
- 结论 A（可行）→ handoff 生产面可标为 keep-candidate-kernel
- 结论 B（部分可行）→ 常见路径面 candidate-kernel，复杂路径面 keep-deep-only
- 结论 C（不可行）→ handoff 生产面标为 keep-deep-only

#### 依赖 2: Copilot Payload-Only Onboarding Proof

**P5 需要的结论**：任意 repo 接入路径是否可行 + 卡点清单。

**如何影响裁定**：
- 如果 onboarding 可行 → installer 面中 non-deep 部分可标为 delete
- 如果 onboarding 有卡点 → 相关面暂标 keep-deep-only，等卡点解决后重评

### S3: 裁定表

消费 S1 清点 + S2 证据，产出最终裁定表：

| 字段 | 说明 |
|------|------|
| Surface 名称 | 被裁定的面 |
| 当前消费者 | deep_verified / cross-tier / internal |
| P4d/S2 证据 | 新宿主是否需要 |
| 裁定 | keep-cross-tier / keep-deep-only / keep-candidate-kernel / delete |
| 执行步骤 | 具体代码/文档变更 |

**裁定四分类**：
- **keep-cross-tier**：所有梯度宿主都需要，确认 contract 文档覆盖
- **keep-deep-only**：仅 deep_verified 宿主需要，标记为 deep-only scope，non-deep 宿主不消费
- **keep-candidate-kernel**：当前仅 deep host 使用，但如果未来需要 extractable runtime kernel（P6 决策），这些面是候选内核的组成部分。P5 只识别形状，不设计产品
- **delete**：无消费者或已被替代，移除代码

> **"Canonical writer authority"轴**：当前能力梯度（convention_only / payload_capable / deep_verified）建模的是消费能力，未独立建模生产权限。S2.1 Shadow Writer Analysis 的额外产出应包括：是否需要将"谁有权写 canonical state"独立建模为正交轴，还是可以通过 protocol 声明式规则 + Validator 校验覆盖。

### S4: 执行裁定

按 S3 裁定表逐项执行：
- **delete**: 移除代码 + 更新 import + 确认测试不依赖
- **keep-deep-only**: 标记为 deep-only scope，移入或标注 deep-host-specific 区域
- **keep-cross-tier**: 无变更，仅确认 contract 文档覆盖
- **keep-candidate-kernel**: 标记为 candidate kernel，记录进最小必留面清单（P6 输入），当前不改造

### S5: 结论报告

标准 receipt 格式。核心产出：
1. 裁定表执行结果
2. 最小必留面清单（P6 输入）
3. Shadow Writer 结论对 Runtime-optional 论题的影响
4. LOC 变化量

## 待决策项

| # | 决策点 | 选项 | 建议 | 依赖 |
|---|--------|------|------|------|
| D1 | Shadow Writer 先做还是后做 | A) 先于 S1 B) 与 S1 并行 C) S1 后再做 | B — 并行效率最高，但 S3 裁定需要等 S2 结论 | — |
| D2 | 清点粒度 | A) 函数级 B) 模块级 C) 文件级 | B — 模块级平衡精度与工作量 | — |
| D3 | Onboarding Proof 是否阻塞 P5 裁定 | A) 阻塞（必须等结论） B) 不阻塞（可先出 provisional 裁定） | B — onboarding 证据补充但不阻塞 shrinkage 主线 | — |
| D4 | 裁定执行是否一次性 | A) 一次性全量执行 B) 分批执行（按风险分级） | B — 先执行低风险（明确 deep-only），高风险等复审 | — |

## 风险

| 风险 | 缓解 |
|------|------|
| Shadow Writer 结论为"不可行"，影响 Runtime-optional 叙事 | P5 裁定表仍有价值——即使 runtime 不能完全 optional，deep-only 面仍需清理 |
| 删除面导致 deep host regression | 执行前跑现有测试套件（717 tests baseline）|
| 清点工作量超预期（24K LOC） | 先做模块级扫描，只对可疑模块深入函数级 |
