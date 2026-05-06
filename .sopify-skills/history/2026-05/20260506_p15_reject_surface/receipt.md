# Receipt: P1.5-A DECISION_REJECT Surface 收口

outcome: passed
date: 2026-05-06

## Summary

DECISION_REJECT 从 consult 伪装剥离为独立 non-family surface `proposal_rejected`。Engine/Handoff/Output 四层对齐：route_name、handoff_kind="reject"、reject_reason_code 结构化 artifact、phase label/status message/next hint/status symbol 全链路投影。合入 main（PR #24→#25, commit 77e7ec7）。

## Key Decisions

1. reject 使用独立 route_name `proposal_rejected`，不继续借 consult 路由（T1-A）
2. handoff_kind 新增 `"reject"` 映射，required_host_action 保持 `continue_host_consult`（不破 canonical 5 预算）（T2-A/T2-B）
3. output 投影全链路对齐：_PHASE_LABELS / _status_message / _handoff_next_hint / _status_symbol 均新增 reject 分支（T3-A~T3-D）
4. design.md Non-family Surfaces 表注册 `proposal_rejected` 为跨路由错误面（T4-A）

## Verification

- 全量 pytest 通过（含 reject 路由断言、handoff 结构断言、真 consult 不回归、digest mismatch + missing plan_subject 均命中新 surface）
- Stale receipt cross-run 集成测试已补充（plan/p15-final 交付）

## Impact on Blueprint

- tasks.md: P1.5-A 标记完成
- design.md: Non-family Surfaces 表新增 proposal_rejected
