# Receipt: P1.5-B Authorization Contract Spec

outcome: passed
date: 2026-05-06

## Summary

ExecutionAuthorizationReceipt 8-field spec 从 ADR-017 "方向"升格为 normative（protocol §7 + ADR-017 RFC 2119 表述）。Runtime 实现：generate_proposal_id + host reject、engine post-gate receipt generation、RunState persistence + handoff exposure、stale detection fail-closed（integrity → binding → freshness 三级校验）。合入 main（PR #25, commit f98ef6d）。

## Key Decisions

1. Receipt 8 字段严格对齐 ADR-017（plan_id / plan_path / plan_revision_digest / gate_status / action_proposal_id / authorization_source / fingerprint / authorized_at）（T2-A）
2. `generate_proposal_id()` 确定性 sha256 + host 传入 proposal_id 显式 reject（T2-B）
3. Receipt 生成时机在 evaluate_execution_gate() 之后（deferred to post-gate），非 Validator 阶段（T3-A）
4. authorization_source shape 严格匹配 `{kind: "request_hash", request_sha1: ...}`（T3-A）
5. 无新 receipt 时，所有 RunState 重建分支 carry-forward 旧 receipt（T3-C）
6. Stale detection: plan content 变更 / plan 目录删除 / gate_status 变更 → 全部 DECISION_REJECT，不降级 consult（T4-A）

## Verification

- 全量 pytest 通过
- T5-C 端到端集成测试 7 条全部交付（正面链路 + 负面路径 + carry-forward + stale cross-run，plan/p15-final 交付）

## Impact on Blueprint

- tasks.md: P1.5-B 标记完成，D 前置条件已满足
- protocol.md: §7 receipt 字段升格 normative + 命名对齐注释
- ADR-017: ExecutionAuthorizationReceipt 升格 normative
