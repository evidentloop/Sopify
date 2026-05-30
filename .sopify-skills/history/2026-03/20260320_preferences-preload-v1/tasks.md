---
plan_id: 20260320_preferences-preload-v1
feature_key: preferences-preload-v1
level: standard
lifecycle_state: archived
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
blueprint_obligation: review_required
archive_ready: true
---

# 任务清单: 宿主偏好预载入（`preferences-preload-v1`）

## 0. 本轮边界

- [x] 0.1 本期能力固定为“宿主 preflight 读取长期偏好”，不是 runtime 新阶段
- [x] 0.2 本期固定优先级为：当前任务明确要求 > `preferences.md` > 默认规则
- [x] 0.3 本期明确不修改 `RecoveredContext` 语义
- [x] 0.4 本期明确不引入 `preferences_artifact`、偏好分类或自动归纳

验收标准：

- 文档与实现都不把 `preferences` 描述为 checkpoint 或 execution gate
- 首版边界在 blueprint、README 与计划文档中保持一致

## 1. 路径与时机契约

- [x] 1.1 宿主按 runtime 同级配置优先级解析 `plan.directory`
- [x] 1.2 宿主按 `workspace_root / plan.directory / user/preferences.md` 计算真实路径
- [x] 1.3 宿主在“进入 Sopify router 前”尝试读取偏好
- [x] 1.4 宿主在“恢复 Sopify 主链路前”尝试重新读取偏好
- [x] 1.5 宿主在“再次发起新的 Sopify LLM 回合前”尝试重新读取偏好
- [x] 1.6 纯 helper / bridge 的无 LLM 机器调用明确排除在首版范围外

验收标准：

- 默认与自定义 `plan.directory` 都能命中正确路径
- 工作区切换后不会沿用上一个工作区的偏好路径
- 进入 LLM 前的三类关键时机都已覆盖

## 2. 消费与优先级契约

- [x] 2.1 固化 `loaded / missing / invalid / read_error` 四态
- [x] 2.2 `loaded` 时注入稳定前缀与 `preferences.md` 原文
- [x] 2.3 `missing / invalid / read_error` 时继续主链路，但宿主内部可观测
- [x] 2.4 固化“当前任务 > preferences > 默认规则”的消费顺序
- [x] 2.5 为宿主内部测试与日志定义最小 `PreferencesPreloadResult` contract

验收标准：

- 偏好读取失败不会阻断主链路
- 偏好读取成功时，LLM 能收到稳定前缀与原文
- 当前任务显式要求仍可覆盖长期偏好
- 宿主能区分“没文件”和“读失败”，不再静默吞状态

## 3. 文档对齐

- [x] 3.1 blueprint 已补齐 `preferences-preload-v1` 的背景、设计与任务口径
- [x] 3.2 [`README.md`](README.md) 已补齐中文宿主接入口径
- [x] 3.3 [`README_EN.md`](README_EN.md) 已同步英文宿主接入口径
- [x] 3.4 实现阶段补充对应测试说明与必要代码注释，确保机器契约可维护

验收标准：

- 中文与英文文档不再出现“单语存在、另一侧缺失”的漂移
- 文档描述与最终实现的状态枚举、路径规则、优先级规则一致

## 4. 后续延后项

- [-] 4.1 runtime 独立 `preferences_artifact` 延后评估
- [-] 4.2 偏好结构化暴露延后评估，但首版不塞进 `RecoveredContext`
- [-] 4.3 偏好分类、自动归纳、自动提炼延后评估
- [-] 4.4 面向调试的更强可观察性界面延后评估

验收标准：

- 首版实现不被后续增强项拖重
- 延后项都有清晰挂载点，但不会反向污染本期范围

## 推荐实施顺序

1. 先实现路径解析与载入时机
2. 再实现注入格式、状态枚举与优先级
3. 最后补测试、代码注释与文档收口
