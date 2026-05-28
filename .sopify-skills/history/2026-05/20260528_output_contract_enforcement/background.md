# 变更提案: 输出契约提示层与模板结构约束

## 需求背景

Sopify 有 6 个输出模板（analyze ×2、design ×1、develop ×3），但缺少两层保障：

1. **无契约提示**：模板定义了验证表格、必需 section，但宿主没有显式自检规则，遵守与否全凭 LLM 自觉。
2. **无条件增强指引**：analyze/design/consult 场景在复杂情况下应升级为表格/对比结构，但模板是静态的，没有"何时增强"的触发规则。
3. **consult 零模板**：咨询问答是最高频场景之一，但没有任何输出指引。

根因：`20260527_skill_writing_quality` 修复了模板内容和 render 管线，但未补宿主侧自检规则和条件增强指引。

**runtime 背景**：runtime 正在逐步退场。本期不追加 gate/routing 渲染器改动、不实现 bridge validator。所有增强走 prompt/skill/template 层，对所有宿主（Copilot/Codex/Claude）统一生效。

评分:
- 方案质量: 8/10
- 落地就绪: 9/10

评分理由:
- 优点: 纯 prompt 层改动，不侵入 runtime、不新增配置/脚本，所有宿主统一受益
- 扣分: 提示层无法 100% 强制 LLM 遵守，真正的机器强制需后续 bridge/schema（列为显式债务）

## 变更内容

1. **新增输出契约参考文档**：`references/output-contract.md`，定义每类输出的 required sections、表格列约束、条件增强与表达选型（含 DO/DON'T）、输出前自检清单。通过 render 管线内联到所有宿主 prompt。
2. **补 develop 自检规则**：在 `develop-rules.md` 中加输出前自检子节。
3. **补 golden snapshot 结构断言**：在 `test_golden_snapshots.py` 中加模板结构验证 + 验证 output-contract.md 被内联。

## 影响范围

- 新增: `skills/{zh,en}/skills/sopify/references/output-contract.md`（ZH + EN）
- 修改: `skills/{zh,en}/skills/sopify/analyze/SKILL.md`（加引用行）
- 修改: `skills/{zh,en}/skills/sopify/design/SKILL.md`（加引用行）
- 修改: `skills/{zh,en}/skills/sopify/develop/SKILL.md`（加引用行）
- 修改: `skills/{zh,en}/skills/sopify/develop/references/develop-rules.md`（加自检子节）
- 修改: `tests/test_golden_snapshots.py`（加结构断言）
- 修改: `tests/golden-snapshots.json`（hash 更新）

## 风险评估

- 风险: 结构断言过严，正常模板改动频繁导致测试脆弱
- 缓解: 结构断言只验必需 section 存在（如表头 `| 任务 |`、`Changes:`、`Next:`），不验具体内容；表格列允许场景化省略

## 明确不做

- 不修改 gate/routing 渲染器（runtime 正在退场，gate 输出职责不变）
- 不实现 bridge validator 代码（列为后续显式债务）
- 不新增 `output_contract.yaml` 配置文件
- 不给 consult 创建独立 skill 目录
- 不对简单问答强制表格
- 不修改 `protocol.md`（输出路径职责写在 output-contract.md 即可，不需要另开一个文件）

## 显式后续债务

- bridge/schema validator：当 host bridge 落地时，可基于 output-contract.md 的 required sections 做 advisory 校验。本期只留文档化设计意图，不写代码。
