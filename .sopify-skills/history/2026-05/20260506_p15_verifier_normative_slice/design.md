# P1.5-D: Verifier Minimum Normative Slice — 设计

## 设计决策

### D1: §6 Verifier 字段 RFC 2119 升格

将 protocol.md §6 Verifier 字段从 informative 表格升格为 normative：

| 字段 | 升格前 | 升格后 |
|------|--------|--------|
| `verdict` | 列出固定值域 | **MUST** 提供可被 Validator 消费的判定标识；具体值域允许实现细化，canonical 值域待后续正式化 |
| `evidence` | "支撑判定的具体事实" | **MUST** 提供可 machine-readably 消费的证据（如文件路径、行号、代码片段等） |
| `source` | "验证器标识" | **MUST** 标识验证器来源，供 Validator 和宿主解释 evidence provenance |
| `scope` | "验证范围" | **SHOULD** 提供；缺失不阻断 contract 成立，但会降低证据解释力 |

### D2: Verifier 消费路径 — contract 口径

在 §6 Verifier 段之后新增消费路径规则：

**verdict 消费规则：**
- Validator **MUST** 将 Verifier verdict 视为授权风险因子
- Verifier **MAY** 使用实现特定的更细粒度枚举
- Validator / 宿主 **SHOULD** 能将实现特定枚举归一化到稳定语义层
- canonical verdict 值域与完整 normalization mapping 留待后续里程碑正式化；在此之前 verdict **MUST NOT** 被当作自授权信号

**evidence 消费规则：**
- Verifier evidence **MUST** 进入 Sopify 的后续证据链
- 当存在结构化 handoff 承载位点时，**SHOULD** 挂载到 handoff
- receipt / history / plan metadata 的具体 attachment 位置与 wire format 继续 **deferred**

**source 消费规则：**
- source **MUST** 标识验证器来源，供 Validator 和宿主解释 evidence provenance
- 是否基于 source 做差异化处理不在 D scope

**关键设计点：** 消费路径的 normative 重点在"消费语义"（谁必须看、怎么用），不在"存储拓扑"（存哪个字段、什么路径）。避免反向制造新的 runtime 实现承诺。

### D3: protocol.md §7 存储位置收紧

原文："具体字段与路径待 Validator/Receipt 接口稳定后正式化。"

修改为：明确 normative/deferred 边界。evidence 挂载的消费规则 → normative（见 §6）；attachment 的 wire format → deferred。

### D4: design.md 引用修正

原文："subject identity / verdict shape 见 `protocol.md §7`"
修正："subject identity 见 `protocol.md §7`；verdict shape 见 `protocol.md §6`"

§7 是 Subject Identity & Review Wire Contract，Verifier 在 §6。

### D5: §6 升格状态标注

参考 B 对 Receipt 的升格模式（protocol.md §7 ExecutionAuthorizationReceipt），在 §6 Verifier 段开头添加升格状态标注：

> **升格状态**：`§6` 整体仍为 informative/draft；其中 `### Verifier` 子段从 informative 升格为 **normative**（P1.5-D 升格）。字段约束使用 RFC 2119 表述。消费路径为 normative 声明。evidence attachment wire format 为 deferred。

## Scope 边界

### In-scope

1. protocol.md §6 Verifier 字段 → RFC 2119 升格
2. protocol.md §6 新增消费路径段（verdict + evidence + source 消费规则）
3. protocol.md §7 存储位置 → normative/deferred 边界收紧
4. design.md 引用 §7 → §6 修正
5. tasks.md D 状态标记

### Out-of-scope

- runtime Verifier 实现
- evidence attachment 完整 schema / wire format
- canonical 预算扩展（receipt 字段维持 8 个）
- 测试矩阵（无代码变更）
- §7 Review Wire Contract 升格（仍 informative/draft）

## 验收标准

1. protocol.md §6 Verifier 四字段有明确 RFC 2119 等级（MUST × 3, SHOULD × 1）
2. protocol.md §6 消费路径段存在且包含 verdict/evidence/source 三组规则
3. protocol.md §7 存储位置不再有"待稳定后正式化"的悬空表述，normative/deferred 边界清晰
4. design.md 引用从 §7 修正为 §6
5. tasks.md D 标记完成
6. 无 runtime 代码变更
7. 全量 pytest 通过（确认文档改动不破坏任何测试）
