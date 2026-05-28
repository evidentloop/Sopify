# 任务清单: 输出契约提示层与模板结构约束

目录: `.sopify-skills/plan/20260528_output_contract_enforcement/`

> **范围说明**：覆盖 `skills/zh/` + `skills/en/`（ZH/EN 对称）。0 脚本、0 配置、0 runtime 改动。

## 1. 输出契约参考文档

- [x] 1.1 创建 `skills/zh/skills/sopify/references/output-contract.md`：必需 section 契约表 + 条件增强触发规则 + 输出前自检清单 + 输出路径说明
- [x] 1.2 创建 `skills/en/skills/sopify/references/output-contract.md`（EN 对等）
- [x] 1.3 在 `analyze/SKILL.md` 资源导航加引用行（ZH + EN）
- [x] 1.4 在 `design/SKILL.md` 资源导航加引用行（ZH + EN）
- [x] 1.5 在 `develop/SKILL.md` 资源导航加引用行（ZH + EN）

## 2. develop 自检规则

- [x] 2.1 在 `develop/references/develop-rules.md` 步骤 2.5 后追加 2.6 输出前自检子节（ZH + EN）

## 3. 测试

- [x] 3.1 在 `tests/test_golden_snapshots.py` 新增模板结构断言测试（验证 required markers 存在）
- [x] 3.2 在 `tests/test_golden_snapshots.py` 新增内联断言（验证 output-contract.md 被 rendered prompt 包含）
- [x] 3.3 更新 `tests/golden-snapshots.json`（hash 因 SKILL.md 加引用行而变化）
- [x] 3.4 运行 `pytest tests/test_golden_snapshots.py` 全部通过
