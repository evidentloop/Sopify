# 变更提案: Skill 写作质量收敛

## 需求背景

Sopify 三个核心 skill（analyze / design / develop）各自有行为规则，但缺少共享的写作基线，且输出模板与规则定义脱节。

**缺口 1：无共享写作基线**

三个 skill 没有统一的排版、术语、段落约束。用户在不同阶段看到的文档风格不连贯。需要一组底层哲学级规则（≤ 6 条），每条防止一类 LLM 输出事故。

**缺口 2：输出模板与规则脱节**

模板是 LLM 的实际执行蓝图，缺字段 = 缺输出：
- `develop-rules.md` 定义了验证契约字段（`verification_source` / `result` / `reason_code` / `retry_count` / `root_cause` / `review_result`），但 3 个输出模板均未体现
- `analyze/assets/success-output.md` 过薄——不含假设、信息缺口、下一步理由

**缺口 3：render 管线顶层 references/ 盲区**

`render_single_file()` 只遍历 `{skill}/references/`，不处理 `sopify/references/`（顶层共享目录）。DNA 文件放在正确的语义位置但不会被 inline 到 Copilot managed block 中。

评分:
- 方案质量: 8/10
- 落地就绪: 9/10

评分理由:
- 优点: 范围可控（2 新建 + 19 修改），不侵入 skill 执行流程，render 管线修复仅 +8 行
- 扣分: kb/templates SKILL.md 结构性技术债不在本期范围

## 变更内容

1. **新增共享写作 DNA**：创建 `shared-writing-dna.md`（6 条规则，~50 行），三个 skill 的 SKILL.md 各自引用
2. **重写 4 个输出模板**：完整重拍（非追加），对齐 rules 定义的字段

## 影响范围

- 新增: `skills/{zh,en}/skills/sopify/references/shared-writing-dna.md`（ZH + EN）
- 修改: `skills/{zh,en}/skills/sopify/analyze/SKILL.md`（加哲学声明 + 引用行）
- 修改: `skills/{zh,en}/skills/sopify/analyze/assets/success-output.md`（重写）
- 修改: `skills/{zh,en}/skills/sopify/design/SKILL.md`（加哲学声明 + 引用行 + EN description 修正）
- 修改: `skills/{zh,en}/skills/sopify/develop/SKILL.md`（加哲学声明 + 引用行）
- 修改: `skills/{zh,en}/skills/sopify/develop/assets/output-success.md`（重写）
- 修改: `skills/{zh,en}/skills/sopify/develop/assets/output-partial.md`（重写）
- 修改: `skills/{zh,en}/skills/sopify/develop/assets/output-quick-fix.md`（重写）
- 修改: `skills/{zh,en}/skills/sopify/develop/references/develop-rules.md`（+human_action_required）
- 修改: `installer/hosts/base.py`（render 管线支持顶层 references/）
- 修改: `tests/golden-snapshots.json`（6 个 hash 更新）

## 风险评估

- 风险: DNA 规则与各 skill 自有规则重叠
- 缓解: DNA 只含底层哲学（排版/术语/段落/事实/范围/引用），不与 analyze 追问规则、develop 验证循环重叠
- 风险: 模板重写后格式变化影响已有输出习惯
- 缓解: 保持 C2 输出模板的 header/footer 契约不变，仅在核心信息区扩展结构化字段
