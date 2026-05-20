# 变更提案: P5 Contract Surface Shrinkage

## 需求背景

Sopify 主航道 P0→P4d 已全部完成。P4d（Copilot CLI 试点）证明了一个 `payload_capable` 宿主能纯靠 protocol + frozen contract 完成接续消费，不需要 runtime。这给出了判断依据：runtime/installer/manifest/bridge 中有哪些面仅 deep host 在用、新宿主不需要。

P5 = 拿着 P4d 的证据，逐项清点这些面，做三选一：**保留 / 降级为 deep-only / 删除**。

### P4d 提供的关键证据

| 已证明 | 含义 |
|--------|------|
| Handoff 消费（reading frozen contract） | 新宿主不需要 runtime 来读接续状态 |
| Decision/Clarification 消费 | INTERACTION 面可脱 runtime 消费 |
| Gate receipt 消费（审计历史） | AUDIT 面可脱 runtime 消费 |
| 入口语义（Inspect/Continue/Start New/~go 拒绝） | 入口判定可纯靠 protocol 指导 |

| 未验证 | 含义 |
|--------|------|
| Handoff 生产（writing canonical state） | 需要 Shadow Writer Gap Analysis |
| Workspace bootstrap | 需要 Onboarding Proof |
| 任意 repo 分发/初始化 | 需要 Onboarding Proof |

### 前置里程碑链

P0 → P1 → P1.5 → P2 → P3a → P3b → P4a → P4b → P4b.5 → P4c → P4d → **P5**

### 核心验证目标

1. 确定每个 deep-only contract surface 的处置：keep-cross-tier / keep-deep-only / keep-candidate-kernel / delete
2. 识别最小必留面清单 + candidate extractable kernel 形状（P6 Runtime Sunset 的输入，不预设产品形态）
3. 确定 convention-mode 宿主的 handoff 生产可行性（Shadow Writer Analysis 的结论）
4. 识别"canonical writer authority"是否需要独立建模为正交轴（当前能力梯度仅覆盖消费能力，未覆盖生产权限）

## 边界

- **在范围内**：
  - deep-only contract surface 全量清点与裁定
  - runtime 代码中 deep-only 面的标记/降级/删除执行
  - installer/manifest/bridge 中仅 deep host 消费的面的清理
  - Shadow Writer Gap Analysis 结论消费（证据型候选独立产出，P5 消费不拥有）
  - Copilot Onboarding Proof 结论消费（证据型候选独立产出，P5 消费不拥有）

- **不在范围内**：
  - 设计新的 "lightweight runtime" 产品形态（属 P6）
  - Copilot installer mainline 接入（D2 决策：独立路径）
  - 新增 machine truth 或 protocol 扩展
  - Runtime 全面重写或架构变更

- **依赖的证据输入**：
  - Copilot Payload-Only Onboarding Proof（证据型候选，tasks.md）
  - Shadow Writer Gap Analysis（证据型候选，tasks.md）
  - P4d receipt 中的 Runtime Surface 证据汇总表

## 架构定位

```
P4d 证据 ─────────────────────┐
                               ▼
Shadow Writer Analysis ──► P5 裁定表 ──► P6 Runtime Sunset
                               ▲
Onboarding Proof ─────────────┘

P5 裁定表 = 每个 surface 的 keep / downgrade / delete 判定
         + 最小必留面清单
         + convention-mode 生产可行性结论
```

**角色**：P5 是"拆脚手架"——拿着证据删/降级不需要的面，不是建新东西。产出是一张裁定表和最小必留面清单，供 P6 消费。
