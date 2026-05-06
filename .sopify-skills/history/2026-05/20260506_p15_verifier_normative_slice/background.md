# P1.5-D: Verifier Minimum Normative Slice — 背景

## 触发背景

P1.5 的授权脊柱已完成三个切片：

- **C**（PR #23）：Plan Materialization Auth Boundary — `immediate` → `authorized_only`
- **B**（PR #25）：Authorization Contract Spec — ExecutionAuthorizationReceipt 8-field normative
- **A**（PR #25）：DECISION_REJECT Surface — reject 从 consult 伪装剥离为独立 non-family surface

D 是 P1.5 → P2 的桥接切片。P2 的 Local Action Contracts 需要 Verifier 输出作为 Validator 授权判定的风险因子输入。当前 protocol.md §6 Verifier 段是 informative（有字段表格但无 RFC 2119 语义），消费路径只有一句泛话（"验证结果进入 handoff/receipt"），不构成可执行的 contract 口径。

## 核心问题

1. **§6 Verifier 字段无 normative 约束**：verdict/evidence/source/scope 列出了但没有 MUST/SHOULD 等级
2. **消费路径是泛话**："进入 handoff/receipt" 不说明 Validator 怎么消费 verdict、evidence 在证据链中的挂载规则
3. **design.md 引用漂移**：写 "verdict shape 见 protocol.md §7" — Verifier 实际在 §6
4. **§7 存储位置段有悬空尾巴**："具体字段与路径待稳定后正式化" — 与 D 目标矛盾，需收紧 deferred 边界

## 约束

- 纯 spec / docs slice，不改 runtime 代码
- 不定义 evidence attachment 完整 schema / wire format
- 不扩 canonical 预算（receipt 字段维持 8 个，不新增）
- 不做 Verifier runtime 实现
- 消费路径重点在"消费语义"，不在"存储拓扑"
