---
plan_id: 20260320_kb_layout_v2
feature_key: kb-layout-v2
level: standard
lifecycle_state: archived
blueprint_obligation: review_required
archive_ready: true
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
---

# 任务清单: Sopify KB Layout V2（`kb-layout-v2`）

## 评分

- 方案质量: 9.8/10
- 落地就绪: 9.4/10

评分理由：

- 优点: V2 收敛了目录、生命周期、消费契约、同步契约与 bootstrap 索引契约；同时“不兼容双轨、README 纯索引、关键 contract 直接冻结”已经把主要设计摇摆点提前消掉。
- 扣分: resolver、README renderer、manifest 扩展与 `knowledge_sync` 仍需落成稳定实现与测试，当前加分来自方案确定性提升，而不是实现已经完成。

## A. 已冻结决策

- [x] A.1 长期知识层只保留 `project.md + blueprint/*`
- [x] A.2 `wiki/overview.md` 从主结构退役
- [x] A.3 不引入 `blueprint/modules/*`
- [x] A.4 `history/*` 只作为显式 finalize 后的归档层
- [x] A.5 `project.md` 纳入长期知识层，但保持技术约定单一职责
- [x] A.6 所有正式方案包默认附带“方案质量 / 落地就绪”评分
- [x] A.7 首次安装且无 plan 时，`blueprint/README.md` 必须进入零 plan 模式
- [x] A.8 `blueprint/README.md` 必须支持渐进式披露，不得膨胀成总说明书
- [x] A.9 `kb_init: full` 不再回到 `wiki/* + history/*` 旧世界，只能显式提前物化 deep blueprint
- [x] A.10 一次性切断 `wiki/*` 与 `blueprint_obligation` 的默认兼容双轨
- [x] A.11 `blueprint/README.md` 固定为纯索引页，最多保留索引级简单描述
- [x] A.12 `L0/L1/L2/L3`、共享 renderer、manifest V2 knowledge contract 与 `knowledge_sync` 直接冻结为正式 contract

## B. 按改动顺序拆解的实施清单

### 1. 冻结 V2 目录与 bootstrap 行为

- [x] 1.1 更新 `runtime/kb.py`：
  - 去掉默认创建 `wiki/overview.md`
  - 去掉默认创建 `history/index.md`
  - 首次触发只创建 `blueprint/README.md`、`project.md`、`user/preferences.md`
- [x] 1.2 重定义 `kb_init: full`：
  - 不再创建 `wiki/*`
  - 不再预建 `history/*`
  - 只允许显式提前物化 `blueprint/background.md`、`blueprint/design.md`、`blueprint/tasks.md` 与 `user/feedback.jsonl`
- [x] 1.3 更新 bootstrap 相关测试：
  - 首次触发最小骨架
  - `kb_init: full` 不回退到旧结构
  - 首次 plan 补齐 blueprint 深层文件
  - 首次触发前不出现 history

验收标准：

- 新工作区首次触发只出现最小骨架
- 未进入 plan 前无 `background.md / design.md / tasks.md`
- `kb_init: full` 不再生成 `wiki/*` 或 `history/*`
- 未 finalize 前无真实 history 索引

### 2. 冻结 Bootstrap Blueprint Contract 与 README 渐进式披露

- [x] 2.1 抽取共享 `blueprint index renderer` 或同等职责实现
- [x] 2.2 更新 `runtime/kb.py`：
  - 首次安装 / 首次触发且无 plan 时，生成 `L0 bootstrap` README
  - 只写可验证事实，不写推测性目标或死链接
- [x] 2.3 更新 `runtime/engine.py` 与 `runtime/kb.py::ensure_blueprint_scaffold`：
  - 首次进入 plan 生命周期后刷新 README
  - deep blueprint 已物化但无 active plan 时输出 `L1`
  - active plan 已创建时输出 `L2`
- [x] 2.4 更新 `runtime/finalize.py`：
  - 通过共享 renderer 刷新 README
  - 根据是否存在 active plan / history 物化不同披露层级
- [x] 2.5 为 blueprint README 披露逻辑补测试：
  - 无 plan / 无 history
  - 深层 blueprint 已存在但无 active plan
  - active plan 存在
  - finalize 后出现 history

验收标准：

- README 在 bootstrap / first plan / first finalize 三个阶段使用同一套渲染规则
- 首次安装时不会生成推测性长期结论
- README 永远只做入口索引，不出现不存在文件的死链接

### 3. 落 manifest V2 knowledge contract

- [x] 3.1 更新 `runtime/manifest.py`：
  - 新增 `kb_layout_version`
  - 新增 `knowledge_paths`
  - 新增 `context_profiles`
- [x] 3.2 为 manifest 扩展补测试，确保 bundle contract 可稳定产出
- [x] 3.3 明确 `history_lookup` 是显式 profile，不属于默认规划/开发上下文

验收标准：

- manifest 能表达 V2 的长期知识路径与消费 profile
- 宿主不需要再猜长期知识文件位置

### 4. 引入统一 knowledge resolver

- [x] 4.1 新增 `runtime/knowledge_layout.py` 或同等职责模块：
  - 解析长期知识路径
  - 暴露 context profile -> file list 的统一接口
  - 暴露 `materialization_stage`
  - 缺失 deep blueprint 时只返回当前存在文件，不把缺文件异常外抛给调用方
- [x] 4.2 更新 `runtime/decision.py`，改走 resolver
- [x] 4.3 更新 `runtime/clarification.py`，改走 resolver
- [x] 4.4 更新 `runtime/finalize.py` 中对 blueprint / project / history 的路径引用，改走 resolver
- [x] 4.5 为 resolver 补测试：
  - consult profile
  - plan profile
  - clarification profile
  - decision profile
  - finalize profile
  - `L0 bootstrap` 下 deep blueprint 缺失时的 fail-open 行为

验收标准：

- runtime 不再散落硬编码长期知识路径
- `wiki/*` 不再作为默认知识消费目标
- route 在 `L0/L1/L2/L3` 下都能得到稳定、可预测的知识文件集合

### 5. 落最小 `knowledge_sync` 契约

- [x] 5.1 更新 `runtime/plan_scaffold.py`：
  - 在 plan front matter 中加入最小 `knowledge_sync` 矩阵
  - 新生成 plan 不再把 `blueprint_obligation` 当正式判断字段
- [x] 5.2 更新 `runtime/execution_gate.py`：
  - 停止依赖 `blueprint_obligation`
  - 改按 `knowledge_sync` 与 plan 完整性判断执行前 gate
- [x] 5.3 更新 `runtime/finalize.py`：
  - 读取 `knowledge_sync`
  - 以 `skip / review / required` 为准做同步检查
- [x] 5.4 保持 `history` 只承接归档，不做长期正文回灌
- [x] 5.5 为 finalize / execution gate 行为补测试：
  - `review` 允许继续但有提示
  - `required` 缺失更新时阻断
  - 首次 finalize 创建 `history/index.md`
  - 新 plan 使用 `knowledge_sync`
  - 旧 `blueprint_obligation` 不再作为 canonical contract

验收标准：

- plan 对长期知识的影响被结构化表达
- finalize 能稳定检查最小同步义务

### 6. 一次性同步对外口径与实施清单

- [x] 6.1 更新 `README.md`：
  - 替换目录结构为 V2
  - 删除 `wiki/*` 主结构描述
  - 修改 bootstrap / finalize 预期结果
  - 增加 KB 职责矩阵表，至少覆盖：`Path | Layer | Responsibility | Created When | Default Consumer | Git Default`
- [x] 6.2 更新仓库内 blueprint 文档口径：
  - `blueprint/README.md` 的长期索引说明
  - `blueprint/tasks.md` 后续只保留未完成长期项
  - 明确 `project.md` 的职责边界，不与 `background/design` 重复
  - `blueprint/README.md` 最多保留轻量入口表：`Entry | Meaning | Status`
  - `blueprint/design.md` 以消费契约表固定 profile：`Context Profile | Reads | Fail-open Rule | Notes`
- [x] 6.3 更新 `skills/zh/skills/sopify/kb/SKILL.md`
- [x] 6.4 更新 `skills/zh/skills/sopify/templates/SKILL.md`
- [x] 6.5 更新 `skills/zh/skills/sopify/develop/references/develop-rules.md`
- [x] 6.6 更新 `skills/zh/skills/sopify/develop/assets/output-success.md`
- [x] 6.7 若需要，同步 `Codex/Skills/*` 与 `Claude/Skills/*` 中对 KB 结构的描述
- [x] 6.8 把“方案评分”固定纳入方案包输出模板或生成约定

验收标准：

- 根 `README.md` 以职责矩阵明确长期知识层、当前工作层、归档层与运行态层
- `blueprint/README.md` 仍保持轻量索引，不膨胀成长说明书
- `blueprint/design.md` 以表格固定 `context profile` 的默认消费契约
- runtime、skills、templates、README、tests 全部指向 V2
- 新方案包默认自带评分区块

## C. 推荐执行顺序

1. 先改 `runtime/kb.py` 与相关 bootstrap tests，冻结目录、`kb_init: full` 与 progressive 生命周期
2. 再落共享 `blueprint index renderer`，补齐 Stage A / B / C 的 README 渐进式披露
3. 再落 `runtime/manifest.py` 与 stage-aware knowledge resolver
4. 然后实现 `knowledge_sync`，并同步切掉 `execution_gate.py` / `finalize.py` 对 `blueprint_obligation` 的旧依赖
5. 最后统一 README、blueprint、skills、templates、tests 与输出评分格式

## D. 交付检查点

- [x] D.1 新工作区首次触发时不再出现 `wiki/overview.md`
- [x] D.2 新工作区首次触发时不再出现 `history/index.md`
- [x] D.3 首次 plan 后才补齐深层 blueprint
- [x] D.4 首次 finalize 后才生成 history 索引与归档
- [x] D.5 首次安装且无 plan 时，README 只输出零 plan 索引，不出现推测性内容或死链接
- [x] D.6 README 在 bootstrap / first plan / first finalize 三个阶段遵守同一套渐进式披露规则
- [x] D.7 `kb_init: full` 不再生成 `wiki/*` 或预建 `history/*`
- [x] D.8 runtime 默认长期知识消费全部通过 V2 resolver，且在缺失 deep blueprint 时 fail-open
- [x] D.9 新 plan 的正式同步契约已切为 `knowledge_sync`
- [x] D.10 方案包输出默认带评分
