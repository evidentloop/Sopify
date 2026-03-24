# 项目技术约定

## Runtime 快照
- 项目名：sopify-skills
- 工作目录：`/Users/weixin.li/Desktop/vs-code-extension/sopify-skills`
- 运行时目录：`.sopify-skills`
- 根配置：`sopify.config.yaml`
- 已识别清单：暂未识别
- 已识别顶层目录：tests、docs、scripts

## 使用约定
- 这里只沉淀可复用的长期技术约定。
- 一次性实现细节不默认写入本文件。
- 当约定发生变化时，应以代码现状为准并同步更新。

## 文档边界
- `project.md`：只放跨任务可复用的技术约定。
- `blueprint/background.md`：放长期目标、范围与非目标。
- `blueprint/design.md`：放模块、宿主、目录与知识消费契约。
- `blueprint/tasks.md`：只保留未完成长期项与明确延后项。

## Develop 质量约定

- `continue_host_develop` 仍是宿主负责真实代码修改的正式模式；runtime 只负责 machine-readable quality contract、checkpoint callback 与 replay/handoff 落盘。
- develop 质量循环的正式发现顺序固定为：`.sopify-skills/project.md verify` > 项目原生脚本/配置 > `not_configured` 可见降级。
- develop 质量结果的正式字段固定为：`verification_source / command / scope / result / reason_code / retry_count / root_cause / review_result`。
- `result` 的稳定值域固定为：`passed / retried / failed / skipped / replan_required`；`root_cause` 的稳定值域固定为：`logic_regression / environment_or_dependency / missing_test_infra / scope_or_design_mismatch`。
- 当 `result == replan_required` 或 `root_cause == scope_or_design_mismatch` 时，宿主不得继续盲修；必须改走 `scripts/develop_checkpoint_runtime.py` 的 checkpoint callback。
- 当前仓库暂不在 `project.md` 固定单一默认 verify 命令；在解释器基线统一到 Python 3.11+ 之前，未识别到稳定命令时应走 `not_configured` 可见降级，而不是假定默认测试入口存在。
