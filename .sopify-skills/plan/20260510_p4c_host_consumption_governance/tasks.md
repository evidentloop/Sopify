# 任务: P4c Host Consumption Governance

总方向：Protocol-first / Validator-centered / Runtime-optional（tasks.md:9）
产品锚：Protocol 是新宿主的唯一硬依赖；Runtime 是确定性加固线，不是接入前提。

---

## 跨切片 invariant（每个切片必须遵守）

- [ ] 0.1 任何改动不得引入对 F1-F8 forbidden surface 的新宿主依赖（design.md S1）
- [ ] 0.2 不改 ladder 定义（三级梯度准入条件不变）
- [ ] 0.3 不新增 machine truth（state 文件 / checkpoint 类型 / contract 文件）
- [ ] 0.4 不改 P4a keep-list schema
- [ ] 0.5 不让 payload_capable 依赖 runtime/ 模块

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

- [ ] 3b.1 首接触感知收敛：新用户只感知"中断可恢复"+"需要拍板时会停"
- [ ] 3b.2 doctor/status 不主动呈现 checkpoint taxonomy
- [ ] 3b.3 ~go 默认入口不前置 blueprint 概念
- [ ] 3b.4 prompt 不定义机器契约（不定义路由表、不维护 state 写入语义）
- [ ] 3b.5 消除 F5/F6 leak：移除 Entry Guard Reason 等内部守卫码直接暴露；消除 route_name / taxonomy 在 prompt 及默认可见路径中的直接暴露

## P4c-4: 文档与披露层

- [ ] 4.1 protocol.md 唯一合规入口：接入文档统一指向
- [ ] 4.2 文档递进顺序：Layer 0 → 1 → 2 → 3 落地
- [ ] 4.3 Builtin skill capability disclosure：AGENTS.md 投影 + builtin_catalog truth source
- [ ] 4.4 若前述切片稳定，收口时整理 design.md 结构，将 S1-S4 内化为稳定章节（非阻塞）

## P4c-5: Prompt Asset 结构收口（可选收口项）

> **Optional Gate**: 仅当 P4c-1~4 完成且主链已满足验收时，才进入 5.1-5.4。
> **非阻塞**: P4c 主链验收不以 5.x 完成为前提。若时间预算不足，可延期至后续里程碑。

- [ ] 5.1 AGENTS.md / CLAUDE.md 重复段落抽取，压缩长段说明
- [ ] 5.2 "硬契约 / 宿主行为 / 参考说明" 分层重排
- [ ] 5.3 CN / EN 镜像结构对齐
- [ ] 5.4 验证零语义漂移：重排前后语义完全一致

## 收尾

- [ ] 6.1 自检：跨切片 invariant 全部通过
- [ ] 6.2 自检：P4c 前提声明红线无违反
- [ ] 6.3 自检：P4c-1/2/3a/3b/4/5 的依赖顺序未被打破
- [ ] 6.4 提交方案包
