# P1.5-D: Verifier Minimum Normative Slice — 任务

## 任务清单

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| T1 | §6 Verifier 段添加升格状态标注 | `protocol.md` | ✅ |
| T2 | §6 Verifier 字段表格 → RFC 2119 改写 | `protocol.md` | ✅ |
| T3 | §6 消费路径注释 → 独立消费路径段 | `protocol.md` | ✅ |
| T4 | §6 新增 Verifier 消费路径规则（verdict + evidence + source） | `protocol.md` | ✅ |
| T5 | §7 存储位置 → normative/deferred 边界收紧 | `protocol.md` | ✅ |
| T6 | design.md 引用 §7 → §6 修正 | `design.md` | ✅ |
| T7 | tasks.md D 状态标记完成 | `tasks.md` | ✅ |
| T8 | 全量 pytest 确认无回归 | — | ✅ |

## 任务说明

### T1: 升格状态标注

在 `### Verifier（外部验证器）` 标题后、字段表格前，添加升格 blockquote（与 B 的 Receipt 升格模式一致）。

### T2: 字段表格改写

将现有 4 行表格从"说明"列改为 RFC 2119 语义：
- verdict: MUST + 可消费判定标识约束
- evidence: MUST + 结构化要求
- source: MUST + provenance 语义
- scope: SHOULD + 降级影响

### T3-T4: 消费路径

现有段尾注释是一段文字。改写为独立的"Verifier 消费路径"段，包含 verdict/evidence/source 三组消费规则；scope 保留字段级 SHOULD。

### T5: §7 存储位置收紧

替换"具体字段与路径待 Validator/Receipt 接口稳定后正式化"为 normative/deferred 边界声明。

### T6: 引用修正

design.md `§7` → `§6`（方案级收敛引用修正）。
