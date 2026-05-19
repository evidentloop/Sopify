# 技术设计: P4d GitHub Copilot CLI 试点接入

## 技术方案

### 总体策略

在不引入 runtime 的前提下，通过 prompt 资产 + installer adapter 让 Copilot CLI 成为一个"智能消费者"：能读取 deep host 产生的全部 contract 文件，理解语义，并据此接续工作。同时以 shadow experiment 方式验证轻量 handoff writer 的可行性。

### S1: Prompt 资产设计

**来源**：从 `Codex/Skills/CN/AGENTS.md` 派生（仅中文版，EN 按社区需求后续扩展）

**裁剪策略**：

| 段落类型 | 保留/裁剪 | 理由 |
|----------|----------|------|
| Convention 结构说明 | ✅ 保留 | 目录布局、文件用途通用 |
| Plan/history/blueprint 读取 | ✅ 保留 | Convention 层核心 |
| Output 格式模板 | ✅ 保留 | 统一输出 |
| Runtime gate 执行 (§8.1) | ❌ 裁剪 | 依赖 runtime |
| `~go` 命令路由 | ❌ 裁剪 | 依赖 runtime router |
| Handoff 写入 | ❌ 裁剪 | 产生 machine truth |
| State 文件管理 | ❌ 裁剪 | 写操作依赖 runtime |

**新增段落**：

1. **接续增强消费**：读 `current_handoff.json` → 优先消费 `required_host_action`、`recommended_skill_ids`、`artifacts` 决定接续策略（不依赖 route_name，不消费 last_route.json）
2. **交互增强消费**：检查 `current_handoff.json.artifacts.decision_checkpoint` / `current_clarification.json` / `current_decision.json` → 呈现给用户
3. **审计增强消费**：读 `current_gate_receipt.json` 作为上一轮执行的审计历史证据（不作为当前轮次的授权依据，protocol.md 明确禁止复用）
4. **入口语义**：Inspect / Continue / Start New Work 判定逻辑

**禁止消费面**（对齐 design.md forbidden surface 表）：
- ❌ `last_route.json`（F2 forbidden，可从 handoff 派生）
- ❌ Route name 全集 / route taxonomy 语义（F3 forbidden）
- ❌ Gate 三元组直渲（F4 forbidden）
- ❌ Output 渲染文案措辞（F7 forbidden）

**交付格式**：`.github/copilot-instructions.md`（Copilot CLI 原生 repo-level prompt 注入路径）+ `Copilot/Skills/CN/` 目录（对齐现有 host 资产结构）。仅中文版，EN 按社区需求快速扩展。

### S2: Installer Adapter 设计

```python
# installer/hosts/copilot.py
class CopilotHost:
    name = "copilot"
    support_tier = SupportTier.payload_capable
    declared_enhancements = [
        EnhancementGroup.CONTINUATION,
        # INTERACTION / AUDIT 待 S3 验证通过后按结果追加
    ]
    prompt_target = ".github/copilot-instructions.md"
    payload_targets = ["Copilot/Skills/CN/"]
```

### S3: Continuation Smoke 设计

**前置条件**：需要一组有意义的 state 文件。当前 handoff 为 null。

**获取方式**：在 Codex/Claude 中执行一个 plan（或手动构造 fixture），产生：
- `current_handoff.json` — 含 canonical `required_host_action` 值（如 `confirm_decision`、`continue_host_develop`）
- `current_gate_receipt.json` — 含 `gate_passed: true`, evidence 字段
- pending checkpoint 文件（clarification 或 decision）

**验证方法**：在 Copilot CLI 中启动会话，观察其能否：
1. 消费 `current_handoff.json` 的 `required_host_action` + `artifacts`，结合 `plan/` 和 `current_run.json`，正确复述当前上下文
2. 识别 pending checkpoint 类型（clarification/decision）并呈现给用户
3. 读取 gate_receipt 作为上一轮的审计历史记录（非当前轮授权证明）

### S3.5: 轻量 Handoff Writer Shadow Experiment

**定位**：shadow experiment，不直接写 canonical `current_handoff.json`。写入独立文件 `state/copilot_handoff_shadow.json`，不影响 deep host 的 canonical state。

**目的**：验证"交接层可从 runtime 中独立拆出"这个假设，为 P5/P6 提供证据。

**写入 schema**（canonical handoff 字段子集 + experimental 标记，不等同于 canonical handoff）：
```json
{
  "schema_version": "1.0",
  "experimental": true,
  "writer": "copilot-lightweight",
  "handoff_kind": "<session 类型>",
  "required_host_action": "<canonical 值: continue_host_develop|continue_host_consult|answer_questions|confirm_decision>",
  "plan_id": "<活跃 plan ID, nullable>",
  "plan_path": "<活跃 plan 路径, nullable>",
  "artifacts": {},
  "notes": "<本次执行摘要>",
  "updated_at": "<ISO timestamp>"
}
```

> 此 schema 是 canonical handoff 的字段子集，不是"兼容替代品"。S3.5 的产出是字段覆盖率 / 缺口 / 对接续影响的 gap analysis，不是"兼容/不兼容"二元结论。

**不写**：`current_gate_receipt.json`（授权证据需 Validator）、`last_route.json`（forbidden surface）

**验证方法**（lab-only harness，不声称"真实双向接续已成立"）：
1. Copilot session 结束 → 写入 shadow handoff（独立文件）
2. Lab-only：手动将 shadow 文件拷贝为 `current_handoff.json` → 在 Codex 中执行 schema replay / consumption check
3. 产出 gap analysis 表：字段覆盖率 / 缺失字段 / 对接续行为的影响程度
4. 评估：轻量 writer 能覆盖 canonical handoff 多少比例？缺失部分是否阻断接续？

**战略意义**：产出为 P5/P6 的 working hypothesis 输入。若 gap analysis 显示覆盖率足够 + 缺失不阻断 → P5 有证据评估"handoff 生产层可从 runtime 拆出"假设。

### S4: 入口语义设计

三种入口在 Copilot prompt 中的表达：

| 入口 | 触发条件 | 行为 |
|------|---------|------|
| Inspect Active Work | 有活跃 handoff 且 user 未明确说"继续" | 展示当前状态摘要（消费 required_host_action + artifacts），不执行 |
| Continue Active Work | 有活跃 handoff 且 user 明确要求继续 | 消费 handoff，按 required_host_action 接续 |
| Start New Work | user 说"开新任务" | 若有活跃 handoff → 显式仲裁提示；否则正常开始 |

**不绑定关键词**：宿主自行选择暴露形式（protocol 要求），Copilot 用自然语言理解触发。

**不依赖 route taxonomy**：入口判定基于 `required_host_action`，不消费 route_name 语义。

## 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| State 文件为空，smoke 无法验证 | 高 | 手动构造 fixture 或先在 Codex 中执行一轮 |
| Copilot instructions 长度限制 | 中 | 裁剪后 prompt 应 <4K tokens，在限制内 |
| Shadow writer 产出与 canonical 差距大 | 中 | P4d 只验证方向，差距记录入结论供 P5 消费 |

## 验收标准

**P4d 通过条件（= S3 通过）**：
- Copilot/Skills/CN/ 资产存在且可被 installer 安装
- Installer `copilot` adapter 注册，声明 `payload_capable + CONTINUATION`
- Continuation smoke S3 场景 1 通过：Copilot 正确消费 `current_handoff.json` 的 `required_host_action` + `artifacts`，结合 plan/run 上下文完成接续复述

**补强证据（加分项，不卡 P4d 通过判定）**：
- 交互增强：识别 pending clarification/decision 并呈现（S3 场景 2）
- 审计增强：读取 gate_receipt 作为审计历史记录（S3 场景 3）
- 入口语义 3 种路径验证通过（S4）
- Shadow writer gap analysis 表（S3.5）

