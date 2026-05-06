# Receipt: P1.5-D Verifier Minimum Normative Slice

outcome: passed
date: 2026-05-06

## Summary

protocol.md §6 Verifier 从 informative 升格为 normative。verdict/evidence/source MUST，scope SHOULD（RFC 2119 表述）。消费路径 contract 口径：verdict → Validator 风险因子，evidence → 证据链 + handoff SHOULD，receipt deferred。design.md §7→§6 引用修正。纯 spec/docs slice，零 runtime 代码变更。合入 main（PR #26→#27, commit dfaac8b）。

## Key Decisions

1. verdict/evidence/source 三字段升格为 MUST（T2/T4）
2. scope 保持 SHOULD——缺失不阻断 contract 成立，但降低证据解释力（T2）
3. verdict 是 Validator 授权风险因子，MUST NOT 被当作自授权信号（T4）
4. evidence attachment wire format 继续 deferred——当前只定义消费语义，不定义存储拓扑（T4）
5. §7 存储位置 deferred 边界收紧——明确 deferred 而非"待后续正式化"的模糊措辞（T5）

## Verification

- 全量 pytest 通过（无 runtime 变更，无回归风险）
- protocol.md / design.md 引用一致性人工复核

## Impact on Blueprint

- tasks.md: P1.5-D 标记完成
- protocol.md: §6 Verifier 升格 normative + 消费路径 contract
- design.md: §7→§6 引用修正
