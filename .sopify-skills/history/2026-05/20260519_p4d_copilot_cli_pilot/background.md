# 变更提案: P4d GitHub Copilot CLI 试点接入

## 需求背景

Sopify 主航道 P0→P4c 已全部完成。P4d 是下一主线里程碑："选 1 个非 deep 宿主做试点（payload_capable + 接续增强），不接完整 runtime。验证官方最低新宿主画像是否成立、P4b.5/P4c 的分层是否真正降低接入成本。"

### 为什么选 GitHub Copilot CLI

1. **design.md 明确列为合法中间层宿主**："qoder/copilot 等宿主合法停在中间层——支持 payload 安装但不要求完整 runtime 深适配"
2. **当前已事实消费约定层**：本会话已在读取 `.sopify-skills/` 目录结构、blueprint、plan、state，证明物理路径可达
3. **跨宿主接续天然可测**：与 deep host (Codex/Claude) 同仓库共存，Codex→Copilot 接续场景零额外配置

### 核心验证目标

- P4b.5/P4c 的三级梯度 + 增强组合设计是否在真实宿主上 work
- "读冻结 contract 文件即可接续"的断言是否成立
- 接入成本到底多少（从零到可用的工时/改动量）

## 边界

- **在范围内**：payload_capable + CONTINUATION 消费验证（P4d 通过条件）、INTERACTION/AUDIT 消费验证（加分项）、入口语义验证（加分项）、shadow handoff writer experiment（隔离试验，不进默认产品面）
- **不在范围内**：runtime 执行、canonical state 文件写入、`~go` 命令、workspace bootstrap
- **不消费 forbidden surface**：不读 `last_route.json`（F2）、不依赖 route taxonomy 语义（F3）
- **不改 protocol/design**：P4d 消费现有冻结 contract，不新增 machine truth
- **Shadow writer 边界**：写入独立 shadow 文件，不覆盖 canonical state；产出为 P5 证据，不是 P4d canonical 方案

## 架构定位

```
Deep Host (Codex/Claude)          Non-Deep Host (Copilot CLI)
┌─────────────────────┐           ┌─────────────────────────────┐
│ Runtime Gate (§8.1) │           │                             │
│ Router / Engine     │  writes→  │  reads canonical state:     │
│ Handoff Writer      │──────────▶│  - current_handoff.json     │
│ State Manager       │           │  - current_gate_receipt.json│
│ ~go Routing         │           │  - plan/ + checkpoint       │
└─────────────────────┘           │                             │
                                  │  writes shadow state:       │
                                  │  - copilot_handoff_shadow   │
                                  │    (experimental, P5 证据)  │
                                  │                             │
                                  │  Prompt asset 消费          │
                                  │  Convention 结构消费        │
                                  └─────────────────────────────┘
```

**角色**：智能消费者——读取 deep host 产生的 state，理解语义并接续执行，但不产生新的 machine truth。

**Handoff 单向性**：P4d canonical 层面仅验证 Deep→Copilot 消费路径。Copilot→Deep 方向通过 shadow experiment 验证可行性（见 tasks.md D1/D2）。
