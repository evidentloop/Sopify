---
plan_id: 20260510_p4c_host_consumption_governance
feature_key: p4c_host_consumption_governance
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

# 任务: P4c Host Consumption Governance

总方向：Protocol-first / Validator-centered / Runtime-optional（tasks.md:9）
产品锚：Protocol 是新宿主的唯一硬依赖；Runtime 是确定性加固线，不是接入前提。

---

## 跨切片 invariant（每个切片必须遵守）

- [x] 0.1 任何改动不得引入对 F1-F8 forbidden surface 的新宿主依赖（design.md S1）— 验证通过：4 prompt files 已收敛到 protocol.md §8 引用，无 forbidden surface 新依赖
- [x] 0.2 不改 ladder 定义（三级梯度准入条件不变）— 验证通过：blueprint/design.md:431-433 仍为 3 级
- [x] 0.3 不新增 machine truth（state 文件 / checkpoint 类型 / contract 文件）— 验证通过：无新增
- [x] 0.4 不改 P4a keep-list schema — 验证通过：blueprint/design.md:363-379 仍为 15 项
- [x] 0.5 不让 payload_capable 依赖 runtime/ 模块 — 验证通过：blueprint/design.md:681 明确

---

## P4c-1: 契约投影层

- [x] 1.1 审计 deep_verified 列各项"预期 required†"，逐项准备裁定清单
- [x] 1.2 确定投影矩阵的格式、权威存放位置、消费方式

> **Gate**: 未完成 1.2，不进入 1.3-1.5。

- [x] 1.3 基于 1.2 产出 FeatureId → 梯度投影矩阵
- [x] 1.4 完成 deep_verified 各项最终 required / optional 裁定，消除 †
- [x] 1.5 验证投影矩阵与 P4b.5 消费矩阵一致，无矛盾

## P4c-2: 增强声明/检测层

- [x] 2.1 调研增强声明的最小可行方案（manifest / bridge config / capability detection）
- [x] 2.2 选定最小可行声明机制
- [x] 2.3 定义声明协议（格式、字段、放置位置）
- [x] 2.4 定义检测/校验逻辑（advisory / fail-closed / host-visible diagnostics）
- [x] 2.5 产出本地可验证样例或参考接入证明，证明声明方式与检测逻辑可跑通

## P4c-3a: 渲染与 truth-source 收敛层

- [x] 3a.1 状态符语义：canonical route family → 符号映射
- [x] 3a.2 Next 降级：明确为 human hint，移除对 required_host_action + route_name 的机器依赖
- [x] 3a.3 Changes 重定义：loaded_files 从 Changed 拆出，或重命名为 Touched/Files
- [x] 3a.4 Gate 行简化：默认输出不暴露 gate_status/blocking_reason/plan_completion 三元组
- [x] 3a.5 doctor/status 只渲染 machine truth，不作为 truth source（删除跨 session 聚合，退回单一 global snapshot）
- [x] 3a.6 handoff rendering 只消费 current_handoff.json 结构化字段，不做语义推断（删除 _execution_gate/_state_conflict_payload/_quarantined_items 的 recovered_context fallback；_core_lines/_status_message 的 route_name 分支渲染未改动）

## P4c-3b: 首接触与 prompt 收敛层

- [x] 3b.1 首接触感知收敛：新用户只感知"中断可恢复"+"需要拍板时会停" *(scope: 4 prompt files 核心理念/Core Philosophy 前插 2 条用户感知——中断可恢复 + 决策前停车；不含 KB 输出面重设计)*
- [x] 3b.2 doctor/status 不主动呈现 checkpoint taxonomy *(scope: _STAGE_LABELS 7 entries + _CHECKPOINT_LABELS 4 entries 映射 raw → human-readable；render_status_text 3 处 + doctor evidence 1 处去 raw code；修复 82886b3 遗留 workspace_preflight_contract 测试断裂)*
- [x] 3b.3 ~go 默认入口不前置 blueprint 概念 *(scope: Quick Reference 删除 Blueprint 路径行；A6 生命周期保留原文——文件路径引用非概念暴露)*
- [x] 3b.4 prompt 不定义机器契约（不定义路由表、不维护 state 写入语义） *(scope: 删除 Routing Decision 整段——Entry Point Flow 路由树 + Route Types 路由类型表；宿主接入约定 ref 移到 C3 Notes 后；4 prompt files 净 -140 行)*
- [x] 3b.5 消除 F5/F6 leak：移除 Entry Guard Reason 等内部守卫码直接暴露；消除 route_name / taxonomy 在 prompt 及默认可见路径中的直接暴露 *(scope: 3b.5-A 删除 dead rendering code commit 6ed2182; 3b.5-B 删除 prompt 中 14 Note + Host Integration Contract + Quick Reference runtime helpers 三大块，替换为 3 条高层义务 + protocol.md §8 引用)*

## P4c-4: 文档与披露层

- [x] 4.1 protocol.md 唯一合规入口：接入文档统一指向 *(scope: 新增 protocol.md §8 Deep Host 运行时集成协议，含 §8.1 Gate-First / §8.2 Post-Run Handoff / §8.3 宿主行为边界 / §8.4 Runtime Helper 索引 / §8.5 State 文件索引；4 prompt files 全部指向 §8)*
- [x] 4.2 文档披露梯度落地 *(scope: protocol.md 新增文档披露梯度权威映射表——Layer 0 Protocol §1-§3 / Layer 1 Lifecycle §4-§5 / Layer 2 Integration §6-§8+prompt / Layer 3 Reference design.md+ADR；含 tier↔layer 桥接 + KB 分层解耦声明)*
- [x] 4.3 Builtin skill capability disclosure：AGENTS.md 投影 + builtin_catalog truth source *(scope: 4 prompt files 技能引用段——明确 runtime 管理的工作流技能、按需加载、不支持独立调用、truth source 指向 builtin_catalog.generated.json)*
- [x] 4.4 design.md 结构整理：Host Capability Governance 从审计增量记录改为稳定主题章节 *(scope: Persistence Surface/Keep-list/Output Audit 提升为独立 ##；HCG 拆为 10 个主题 ### —— 能力梯度/接入判定/禁止消费面/契约消费矩阵/增强组合与声明/官方接入画像/Convention Quickstart/Prompt 镜像/模块依赖审计/长期边界；去除 S1-S4 过程标签和 L-number 引用，provenance 降为括号注释)*

## P4c-5: Prompt Asset 结构收口（可选收口项）

> **Optional Gate**: 仅当 P4c-1~4 完成且主链已满足验收时，才进入 5.1-5.4。
> **非阻塞**: P4c 主链验收不以 5.x 完成为前提。若时间预算不足，可延期至后续里程碑。

> **跳过判定**：P4c-3b/4 完成后 prompt 文件已 ~373 行、分层清晰（C→A→X→P→Skill→QuickRef）、CN/EN 已对齐，无显著重复段落。进一步结构重排的收益低于语义漂移风险。若未来有 prompt asset 对外发布或 First-Use Adoption Proof 需要，可顺带执行。

- [-] 5.1 AGENTS.md / CLAUDE.md 重复段落抽取，压缩长段说明 — 跳过：P4c-3b 已删 ~140 行，当前无显著重复
- [-] 5.2 "硬契约 / 宿主行为 / 参考说明" 分层重排 — 跳过：已分层（C/A/X/P + protocol.md §8 引用）
- [-] 5.3 CN / EN 镜像结构对齐 — 跳过：已对齐
- [-] 5.4 验证零语义漂移：重排前后语义完全一致 — 跳过：无实质改动

## 收尾

- [x] 6.1 自检：跨切片 invariant 全部通过 — 0.1-0.5 全部验证 PASS
- [x] 6.2 自检：P4c 前提声明红线无违反 — 6/6 红线无违反
- [x] 6.3 自检：P4c-1/2/3a/3b/4/5 的依赖顺序未被打破 — P4c-5 显式跳过
- [ ] 6.4 提交方案包 — frontmatter 已补充，待归档
