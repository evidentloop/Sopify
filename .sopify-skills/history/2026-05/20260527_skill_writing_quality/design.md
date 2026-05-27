# 技术设计: Skill 写作质量收敛

## 共享写作 DNA

### 定位

6 条底层哲学规则，每条防止一类 LLM 输出事故。Karpathy 路线：规则少、每条有明确防护对象。

落点：`skills/zh/skills/sopify/references/shared-writing-dna.md`

### 6 条规则

| # | 规则名 | 一句话定义 | 防什么事故 |
|---|--------|----------|----------|
| 1 | 事实与推断分离 | 推断必须标注"推断"或"可能"，量化指标需来源 | 猜测写成结论 |
| 2 | 一概念一术语 | 同一实体全文同名，首次出现注释英文 | 术语混乱 |
| 3 | 最小化输出范围 | 输出范围 = 任务范围，不加未要求的 section，不做投机抽象 | 方案包膨胀 |
| 4 | 中英文排版 | 中英文间加空格，中文正文全角标点，专有名词官方大小写 | 排版不一致 |
| 5 | 段落约束 | 段落 ≤ 7 行，一段一论点，最多三级标题 | 长段落 |
| 6 | 引用可验证 | 文件路径、函数名、类名引用需确保实际存在 | 幻觉引用 |

### 引用方式

在每个 skill 的 SKILL.md 资源导航中新增一行：

```
- 共享写作规范：`../references/shared-writing-dna.md`（所有输出遵循）
```

DNA 是叠加层，不替代各 skill 的行为规则（analyze-rules / design-rules / develop-rules）。

## 输出模板重写

重写而非追加。保持 C2 output 契约（header 行 + `---` + `Changes:` + `Next:`），扩展核心信息区。

### analyze/success-output.md

当前 11 行，缺失决策依据。重写后补充：
- 假设与前提区块（当 auto_decide=true 补充的假设在此可见）
- 已识别信息缺口（影响 + 建议动作）
- 下一步理由（为什么进入 design / 需要再追问）

### develop/output-success.md

当前 13 行，缺失验证证据。重写后补充：
- 验证摘要表（`verification_source` / `command` / `result` / `reason_code` / `retry_count`）
- 复审结论行（`spec_compliance` + `code_quality`，强制带 1 句依据）

### develop/output-partial.md

当前 13 行，缺失结构化失败信息。重写后补充：
- 未完成项表（`reason_code` / `root_cause`，root_cause 可选，未到失败收口时填 `—`）
- 验证摘要表（同 success，含 `reason_code` 列）

### develop/output-quick-fix.md

当前 10 行，无验证。重写后补充：
- 验证摘要表（4 列简表：`Source` / `Command` / `Result` / `reason_code`）

### 状态符硬约束

在 `develop-rules.md` 两阶段复审后追加：`✓` 仅当所有验证行 `result=passed` 且 `reason_code=—`；否则必须用 `!`。防止"表格记录了 skipped，标题还显示成功"的矛盾。

## 不变项

- design-template.md 结构不变（保持 3 section）
- 各 skill 执行流程不变
- 不新增脚本、不新增配置文件

## render 管线修复

`installer/hosts/base.py` `render_single_file()` 新增顶层 `references/` inline 步骤（+8 行），放在 skill 遍历之前。确保共享 DNA 内容出现在 managed block 中，且在约束在前、技能在后的正确位置。修改完全照已有 `references/assets/scripts/` inline 模式写。
