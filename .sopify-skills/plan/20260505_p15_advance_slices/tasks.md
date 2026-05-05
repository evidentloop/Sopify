# 任务清单: P1.5 先行切片

目录: `.sopify-skills/plan/20260505_p15_advance_slices/`

## 1. Convention 入口兑现

- [ ] T1-A: 在 README.md Quick Start 章节内增加 Convention Mode 子段落
  - 描述 3 步最小路径（读 blueprint → 写 plan → 归档 + receipt）
  - 引用 protocol.md §4 样例 A 和 §5 合规检查清单
  - 验收: 段落存在 + 内容准确引用协议文档
- [ ] T1-B: 在 README.zh-CN.md 同步增加对应中文段落
  - 验收: 中文段落结构与英文一致
- [ ] T1-C: 运行 `pytest tests/test_check_readme_links.py` 验证链接完整性
  - 验收: 测试通过

## 2. Protocol Compliance Suite Phase 1

- [ ] T2-A: 新建 `tests/protocol/__init__.py` + `tests/protocol/test_convention_compliance.py` 骨架
  - 验收: `pytest tests/protocol/` 可运行（即使 0 test）
- [ ] T2-B: 实现断言 1-2（project.md 存在 + blueprint 三件套存在）
  - 使用 tmp_path fixture 构建最小 `.sopify-skills/` 目录
  - 验收: 正向（结构完整）和反向（缺文件）均测试
- [ ] T2-C: 实现断言 3-4（plan 创建 + plan.md 必需字段）
  - 在 tmp_path 下创建 plan/YYYYMMDD_feature/plan.md
  - 验证 title / scope / approach / tasks 区块存在
  - 验收: 正向 + 反向（缺必需字段时失败）
- [ ] T2-D: 实现断言 5（归档 + receipt.md）
  - 在 tmp_path 下创建 history/YYYY-MM/feature/receipt.md
  - 验证 receipt.md 存在
  - 验收: 正向 + 反向
- [ ] T2-E: 实现断言 6（knowledge_sync / blueprint 回写，标记 skip）
  - 用 `pytest.mark.skip(reason="Convention 下界推荐项，Phase 1 不强制")` 标记
  - 验收: 测试文件中存在该 test case 但 skip
- [ ] T2-F: 验证 `pytest tests/protocol/` 不 import 任何 `runtime.*` 模块
  - 验收: `grep -rn "from runtime\|import runtime" tests/protocol/` 无匹配

## 3. 低风险辅助层预清理（daily_summary）

- [ ] T3-A: 验证 `_models/summary.py` 中各 class 的消费方
  - grep 全量引用，确认哪些 class 仅被 daily_summary 消费
  - 记录结论到本任务备注（共用 class 保留，专属 class 删除）
  - 验收: 消费方分析结果记录完毕
- [ ] T3-B: 删除 `runtime/daily_summary.py` + 清理 `runtime/engine.py` 中的 import 和调用点
  - 删除 engine.py:18 的 import
  - 删除或替换 engine.py:1009 的调用分支
  - 验收: engine.py 不再引用 daily_summary
- [ ] T3-C: 清理 `runtime/output.py` 中 `_render_daily_summary_output` 函数和调用入口
  - 删除 output.py:689 函数定义
  - 删除 output.py:212 调用分支
  - 验收: output.py 不再引用 daily_summary
- [ ] T3-D: 清理 `runtime/_models/summary.py` + `runtime/models.py` re-export
  - 按 T3-A 结论删除 daily_summary 专属 class
  - 清理 models.py 中对应的 re-export
  - 验收: 无 daily_summary 专属 class 残留
- [ ] T3-E: 清理测试文件
  - 删除 `tests/test_runtime_summary.py`（175 行）
  - 清理 `tests/runtime_test_support.py:47` 的 import
  - 清理 `tests/test_runtime_engine.py:2338` 的 mock patch
  - 验收: 测试文件不再引用 daily_summary
- [ ] T3-F: 全量 `pytest` 验证 + `grep` 残留检查
  - `pytest` 全量通过
  - `grep -rn "daily_summary" --include="*.py"` 无残留
  - 验收: 零引用 + 零断裂

## 4. 蓝图回写

- [ ] T4-A: 更新 `blueprint/README.md` 当前焦点
  - 反映先行切片执行完成状态
- [ ] T4-B: 更新 `blueprint/tasks.md` P1.5 先行切片状态标记
