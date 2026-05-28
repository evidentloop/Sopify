# 技术设计: 输出契约提示层与模板结构约束

## 设计原则

所有增强走 prompt/skill/template 层，不碰 runtime。原因：
- runtime 正在退场，不应追加投入
- prompt 层改动对 Copilot/Codex/Claude 统一生效
- 提示层无法 100% 强制 LLM，但可以显著提高一致性

## 输出契约参考文档

### 定位

一个共享参考文档（类似 `shared-writing-dna.md`），定义所有阶段输出的 required/adaptive 规则。通过 render 管线内联到所有宿主 prompt。

落点：`skills/zh/skills/sopify/references/output-contract.md`

render 管线已在 `20260527` 修复中支持顶层 `references/` 内联，所以新文件自动进入所有宿主的 managed block。

### 内容结构（最终 4 section）

```
1. 输出路径说明（gate 摘要 ≠ 最终回复，不写死 runtime 文件名）
2. 必需 section 契约表（per output type）+ 表格列约束
3. Conditional Enhancement & Format Selection（合并条件触发 + 信息形状选型 + DO/DON'T）
4. 输出前自检清单（mandatory pre-output check）
```

### 必需 section 契约

| 输出类型 | 必需 section | 必需表格 | 状态符约束 |
|---------|-------------|---------|-----------|
| develop/success | 复审结论行、验证摘要、Changes、Next | 验证摘要表 | ✓ 仅当全部 passed |
| develop/partial | 未完成项、验证摘要、Changes、Next | 未完成项表 + 验证摘要表 | 必须 ! |
| develop/quick-fix | 验证摘要、Changes、Next | 验证摘要简表 | ✓ 仅当全部 passed |
| analyze/success | 假设与前提、信息缺口、下一步理由、Changes、Next | — | — |
| analyze/question | 问题列表、Next | — | 必须 ? |
| design/summary | 评分行、Changes、Next | — | — |
| consult | Changes、Next | — (adaptive) | — |

表格列约束：只展示当前场景有信息量的列。success 场景下全部 `reason_code=—` 时，可省略该列。列省略只影响最终展示，不影响内部验证判断。

### Conditional Enhancement & Format Selection

合并条件触发与信息形状选型为单一决策表：

| 触发条件 | 推荐表达 | 典型场景 |
|---------|---------|---------|
| 多项对比/取舍（>2 方案） | 表格 | 方案取舍、风险对比、宿主能力对比 |
| 流程/调用/生命周期 | 编号序列 | SDK 流程、gate → route → handoff |
| 文件/组件/模块组成 | 树状结构 | 组件拆分、模块结构、方案文件组织 |
| 评分维度需可见化 | 评分表 | analyze 评分 |
| 简单问答/状态确认 | 保持简洁 | 单一问题回答、状态确认 |

约束：同一回复最多选一种主结构，避免表格 + 树 + 流程叠加。

附 DO/DON'T 短规则（3+3 条），防止漏增强和过度增强。

## develop 自检子节

在 `develop-rules.md` 步骤 2.5（两阶段复审）后追加"输出前自检"：

```
### 2.6 输出前自检

完成两阶段复审后，输出最终摘要前必须检查：

1. 状态符是否正确：`✓` 仅当全部 `result=passed` 且 `reason_code=—`；否则必须 `!`。
2. 必需表格是否存在：success/partial 必须有验证摘要表；partial 必须有未完成项表。
3. 复审结论行是否存在：success 必须有 `spec_compliance` + `code_quality` 各一句依据。
4. footer 是否完整：`Changes:` + `Next:` 必须存在。
```

## golden snapshot 结构断言

在 `test_golden_snapshots.py` 中新增两组测试：

**1. 模板结构断言**（验证模板文件包含 required markers）：

```python
@pytest.mark.parametrize("template_path,required_markers", [
    ("develop/assets/output-success.md", ["| 任务 |", "| 验证来源 |", "Changes:", "Next:"]),
    ("develop/assets/output-partial.md", ["| 任务 |", "| 阻塞原因 |", "| 验证来源 |", "Changes:", "Next:"]),
    ("develop/assets/output-quick-fix.md", ["| 验证来源 |", "Changes:", "Next:"]),
    ("analyze/assets/success-output.md", ["假设与前提:", "已识别信息缺口:", "Changes:", "Next:"]),
    ("design/assets/output-summary.md", ["方案质量:", "落地就绪:", "Changes:", "Next:"]),
])
def test_template_required_sections(template_path, required_markers):
    ...
```

**2. 内联断言**（验证 output-contract.md 出现在各宿主的 rendered prompt 中）：

直接检查 render_single_file() 输出是否包含 `output-contract.md` 的关键标记。

覆盖 ZH + EN 两个语言目录。

## 不变项

- 各 skill 执行流程不变
- gate/routing 摘要渲染器不变
- 不新增脚本、不新增配置文件
- develop 模板内容不变（只加规则引用和自检）
