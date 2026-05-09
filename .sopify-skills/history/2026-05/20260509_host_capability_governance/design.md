# 技术设计: 第三方宿主能力边界治理

## 方案概述

1 个方案包，纯文档/设计变更。产出：**blueprint/design.md** 新增 canonical 治理结论（4 项），blueprint/tasks.md 只负责长期项状态和链接。

## Scope 边界

### 在 scope 内

1. **Host capability ladder** — 冻结 convention_only / payload_capable / deep_verified 三级 canonical 梯度，定义每级的 contract 准入条件；将 SupportTier 明确标记为 legacy projection
2. **接入判定 checklist** — 新宿主准入时需回答的问题清单，覆盖蓝图点名的全部边界：官方入口 / payload 落点 / repo-local 优先级 / skills 目录支持
3. **Convention quickstart 最小交付面** — 定义要交付什么（adoption guide / reading order），不新增 normative 内容，不复述 schema
4. **Prompt 镜像治理原则** — prompt asset 属于 payload/install surface；现有 Claude/Codex 目录树是 legacy exception，不再扩张

### 不在 scope 内

- 不改 installer/models.py 的 SupportTier 代码（代码对齐可以是后续实施项）
- 不指定下一个官方深适配目标
- 不改 runtime 代码
- 不做 Convention quickstart 的完整实现（只定义最小交付面）
- 不做 quickstart normative 内容（protocol.md 是唯一合规入口）

## Canonical 落点

**blueprint/design.md** 承载所有 canonical 治理结论（梯度表 + checklist + quickstart 定义 + prompt 治理原则）。blueprint/tasks.md 只负责长期项状态和到 design.md 的链接。P4c 消费单一 truth source。

## 设计要点

### 1. Host Capability Ladder（Canonical 产品真相）

> 蓝图总纲：Protocol-first / Validator-centered / Runtime-optional。
> convention_only 的"合格"是看能消费哪些 contract，不是看有没有某个安装动作。

| 梯度 | 含义 | 进入条件（contract 准入） | SupportTier 映射（legacy） |
|------|------|--------------------------|--------------------------|
| `convention_only` | 只支持 Convention 协议；无 payload、无 runtime | 能消费 protocol.md §1-§4；有 .sopify-skills/ 目录结构；遵守 repo-local 优先级；能消费宿主侧 skill/prompt disclosure surface（不把未冻结 workspace 路径当作协议前提） | 无直接对应；当前 DOCUMENTED_ONLY 或 EXPERIMENTAL 可作为临时映射 |
| `payload_capable` | 支持 payload 安装；能消费 prompt asset | convention_only 全部条件 + payload 落点 + prompt asset 消费。workspace bootstrap 和 handoff contract 消费为可选增强项，不阻断进入此级别 | BASELINE_SUPPORTED 可作为临时映射 |
| `deep_verified` | 完整深适配；installer + runtime + smoke | payload_capable 全部条件 + workspace bootstrap + handoff contract 消费 + host adapter + smoke 验证 | DEEP_VERIFIED（codex, claude） |

> **payload_capable 关于 workspace bootstrap 和 handoff 的定位**：这两项是可选增强项（opt-in），不是准入门槛。这允许 qoder/copilot 等宿主合法停在中间层——支持 payload 安装但不要求完整 runtime 深适配——而不是被迫二选一（纯文档 or deep adapter）。

### 2. 接入判定 Checklist

新宿主接入时需回答（覆盖蓝图 tasks.md:105 全部边界）：

**Convention 层（convention_only 准入）**
- [ ] 是否支持 Convention 协议（.sopify-skills/ 目录结构 + plan lifecycle）
- [ ] 是否遵守 repo-local 优先级（workspace 配置优先于全局配置）
- [ ] 是否能消费宿主侧 skill/prompt disclosure surface（不把未冻结 workspace 路径当作协议前提）

**Payload 层（payload_capable 准入）**
- [ ] 是否支持 payload 安装（prompt asset 落点 + payload bundle）
- [ ] 是否支持 workspace bootstrap（KB init）— 可选增强
- [ ] 是否能消费 handoff contract（gate receipt 中 state.current_handoff_path 指向的 handoff 文件）— 可选增强

**Deep 层（deep_verified 准入）**
- [ ] 是否需要官方 installer/hosts/* 适配
- [ ] 是否值得进 --target 参数和 README 安装矩阵
- [ ] 是否有 smoke 验证覆盖

只有 payload_capable 以上才进 installer；convention_only 宿主只做文档支持。

### 3. Convention Quickstart 最小交付面

**定位**：adoption guide / reading order。**不是**第二规范源。

- 提供 protocol.md 面向外部宿主的阅读顺序指引（按 Layer 0→3 披露顺序）
- 提供 compliance check 的运行入口（指向 Protocol Compliance Suite Phase 1 已有基础）
- **不新增 normative 内容**：protocol.md 是唯一合规入口
- **不复述 schema**：只引用、不重新定义
- 本包只定义"quickstart 要交付什么"，不做完整实现

### 4. Prompt 镜像治理原则

- **原则**：prompt asset 属于 payload/install surface（P4a keep-list 已冻结此消费面）
- **现有目录树是 legacy exception**：Claude/Skills/ 和 Codex/Skills/ 两棵树只维护现有内容，不再扩张
- **新宿主不进现有目录树结构**：新宿主如需 prompt asset，走 payload 机制
- 讨论框架不是"要不要再开目录树"，而是"payload 机制是否满足需求"

## 风险

- **过度设计风险**：在 bridge 中做了太多 P4c 应该做的事。缓解：只产出治理结论，不改代码
- **SupportTier 代码对齐风险**：canonical 3 级和代码 4 级 enum 暂不同步。缓解：本包只定义映射关系，代码改动留给后续；SupportTier 被标记为 legacy projection，不影响 canonical 梯度的权威性
