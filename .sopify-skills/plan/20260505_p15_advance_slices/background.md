# 变更提案: P1.5 先行切片（Convention 入口 + Compliance Suite + 辅助层预清理）

## 需求背景

P1 Subject Identity Binding 已完成（92 tests green，归档于 `history/2026-05/20260504_subject_identity_binding`）。蓝图 `tasks.md` P1.5 段落登记了三项可先行切片，不受 P1.5 主体（Execution Authorization Spine）的前置约束，可立即执行。

三项缺口：

1. **Convention 入口缺失**：README 只有 runtime 安装路径（`README.md:47-145`）。外部宿主开发者无法通过 README 找到 non-runtime quickstart。protocol.md §4 已有样例、§5 已有合规清单，但 README 未串联引用。
2. **Protocol 合规测试不存在**：`tests/protocol/` 目录不存在。protocol.md §5 定义了 6 条最小合规项，但没有可自动运行的断言。现有 92 个测试全部绑定 runtime 实现，不独立于 runtime 验证协议合规性。
3. **daily_summary 体验增强层**：`runtime/daily_summary.py`（1,133 行）是非核心增强模块，蓝图已确认为低风险预清理首刀候选。

评分:
- 方案质量: 8/10
- 落地就绪: 8/10

评分理由:
- 优点: 三个切片边界清晰、均不改 machine contract、有明确验收标准
- 扣分: daily_summary 依赖图比最初分析更宽（涉及 output.py、_models/summary.py、test_support），清理范围需精确控制

## Plan Intake Checklist

1. **命中蓝图里程碑**：P1.5 可先行切片（主）；不进入 P1.5 主体
2. **改动性质**：presentation-only + protocol 下界验证 + 非核心模块清理；均不构成 contract acceptance boundary
3. **新增 machine truth**：否 — 不新增/删除/替代 action / route / state / checkpoint / receipt 中任何 machine truth
4. **Legacy surface 影响**：daily_summary 不是 machine truth surface；`_render_daily_summary_output` 在 output.py 中是 daily_summary 专属渲染，删除不影响其他 route 的输出
5. **Core/validator authority 影响**：无

## 影响范围

- 模块: README（文档层）、tests/protocol/（新建）、runtime/daily_summary + 关联引用（删除/清理）、blueprint/（回写）
- 文件: 10+ 文件，横跨 README / tests / runtime / blueprint

## 风险评估

- 风险: daily_summary 的 `_models/summary.py`（473 行，16 个 class）可能被 daily_summary 之外的模块消费
- 缓解: 清理前先验证 `_models/summary.py` 中各 class 的消费方，仅删除 daily_summary 专属 class；若有共用 class 则保留
