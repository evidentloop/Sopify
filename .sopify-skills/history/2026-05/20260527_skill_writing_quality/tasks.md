# 任务清单: Skill 写作质量收敛

目录: `.sopify-skills/plan/20260527_skill_writing_quality/`

> **范围说明**：覆盖 `skills/zh/` + `skills/en/`（ZH/EN 对称）。0 脚本、0 配置。

## 1. 共享写作 DNA

- [x] 1.1 创建 `skills/zh/skills/sopify/references/shared-writing-dna.md`（6 条规则，~50 行）
- [x] 1.2 创建 `skills/en/skills/sopify/references/shared-writing-dna.md`（EN 对等）
- [x] 1.3 在 `analyze/SKILL.md` 加核心哲学声明 + 资源导航引用行（ZH + EN）
- [x] 1.4 在 `design/SKILL.md` 加核心哲学声明 + 资源导航引用行（ZH + EN）
- [x] 1.5 在 `develop/SKILL.md` 加核心哲学声明 + 资源导航引用行（ZH + EN）

## 2. 输出模板重写

- [x] 2.1 重写 `analyze/assets/success-output.md`：补充假设与前提、已识别信息缺口、下一步理由（ZH + EN）
- [x] 2.2 重写 `develop/assets/output-success.md`：加入验证摘要表 + 复审结论（ZH + EN）
- [x] 2.3 重写 `develop/assets/output-partial.md`：加入未完成项表 + 验证摘要表（ZH + EN）
- [x] 2.4 重写 `develop/assets/output-quick-fix.md`：加入验证摘要表（ZH + EN）
- [x] 2.5 模板 v2 加固：验证表补 reason_code 列，复审行强制带依据，root_cause 改可选，quick-fix 保持 4 列简表（ZH + EN）

## 3. root_cause 扩展

- [x] 3.1 在 `develop/references/develop-rules.md` 增加第 5 个 root_cause 值 `human_action_required` + 路由约束（ZH + EN）
- [x] 3.2 在 `develop/references/develop-rules.md` 增加状态符硬约束：✓ 仅当全部 result=passed 且 reason_code=—（ZH + EN）

## 4. render 管线修复

- [x] 4.1 在 `installer/hosts/base.py` `render_single_file()` 增加顶层 `references/` inline 步骤（+8 行）

## 5. EN description 修正

- [x] 5.1 修正 `analyze/SKILL.md` description 翻译腔（"routes…through" → 自然 EN）
- [x] 5.2 修正 `design/SKILL.md` description 翻译腔 + 删除多余 "validated" 修饰词

## 6. 验证

- [x] 6.1 更新 golden snapshot（6 个 hash：copilot zh-CN/en-US × 3 轮更新 + skills en-US）→ `pytest tests/test_golden_snapshots.py` 8/8 通过
