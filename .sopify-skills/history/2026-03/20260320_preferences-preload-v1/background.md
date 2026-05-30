# 变更提案: 宿主偏好预载入（`preferences-preload-v1`）

## 需求背景

当前仓库已经有 [`preferences.md`](.sopify-skills/user/preferences.md) 作为长期偏好落点，但它还没有成为稳定的 LLM 输入源。

这意味着：

1. 即使偏好已经写入文件，只要宿主在进入 Sopify 前不主动读取，LLM 本轮仍可能完全看不到
2. `preferences.md` 的真实路径受 `workspace_root + plan.directory` 共同决定，宿主一旦硬编码默认路径，在自定义 `plan.directory` 下就会失效
3. 长期偏好属于 workspace-scope 协作规则，不等同于 active-flow runtime state；若直接塞进 `RecoveredContext`，会破坏状态分层语义
4. 偏好缺失或读取异常不应阻断主链路，否则会把“协作风格”误升级为“执行门禁”

因此，本期不追求“更聪明的偏好系统”，而是先把“宿主稳定预载入偏好”做成最小、明确、可验证的契约。

## 目标

### 1. 稳定读取

- 宿主在每次 Sopify 调用前，都按当前工作区与当前配置稳定尝试读取 `preferences.md`
- 路径解析必须与 runtime 的配置优先级保持一致

### 2. 稳定消费

- 若读取成功，长期偏好以固定前缀注入 LLM
- 固定优先级为：当前任务明确要求 > `preferences.md` > 默认规则

### 3. 稳定降级

- 首版采用 `fail-open with visibility`
- `missing / invalid / read_error` 都不阻断主链路，但宿主必须可观测

### 4. 语义不越界

- 这是宿主 preflight 能力，不是 runtime 新阶段
- 首版不修改 `RecoveredContext` 语义
- 首版不引入新的 checkpoint、artifact 或自动归纳链路

## 非目标

本轮明确不做以下内容：

- 不把 `preferences` 升级为 runtime 的门禁机制
- 不把 `preferences.md` 结构化塞进 `RecoveredContext`
- 不做偏好分类、自动归纳、自动提炼
- 不新增 `preferences_artifact`
- 不扩大 `.sopify-skills/` 的自动扫描范围

## 核心问题拆解

### 1. 路径怎么稳定解析

必须先按 runtime 相同优先级解析 `plan.directory`，再定位：

```text
<workspace_root>/<plan.directory>/user/preferences.md
```

这里的关键不是“知道默认路径”，而是“不能依赖默认路径”。

### 2. 宿主在什么时机必须读取

最小闭环应覆盖三类时机：

- 原始用户请求准备进入 Sopify router 之前
- 需要恢复 Sopify 主链路之前
- 准备再次发起新的 Sopify LLM 回合之前

纯 helper / bridge 的无 LLM 机器调用不在首版范围内。

### 3. 读取后如何进入模型

首版不做解析推理，只做稳定注入：

- 注入固定前缀
- 直接附带 `preferences.md` 原文
- 用固定优先级约束消费顺序

这样才能先验证“稳定读到”和“稳定生效”。

### 4. 失败时如何处理

首版采用 `fail-open with visibility`：

- 不阻断主链路
- 不静默吞掉状态
- 宿主内部对 `loaded / missing / invalid / read_error` 有清晰区分

## 成功标准

满足以下条件即可认为本期目标成立：

1. 当用户自定义 `plan.directory` 时，宿主仍能命中正确的 `preferences.md`
2. 当 `preferences.md` 缺失或异常时，Sopify 主链路仍可继续
3. 当 `preferences.md` 可读时，LLM 收到稳定、可复用的偏好注入块
4. 当前显式任务能覆盖长期偏好，长期偏好能覆盖默认规则
5. 文档口径在 blueprint、[`README.md`](README.md) 与 [`README_EN.md`](README_EN.md) 中保持一致

## 风险评估

### 风险 1

如果宿主仍硬编码默认路径，`plan.directory` 一旦自定义，偏好就会静默失效。

缓解：

- 路径解析必须显式复用 runtime 同级配置优先级
- 针对自定义 `plan.directory` 增加测试

### 风险 2

如果把偏好塞进 `RecoveredContext`，会让 durable rule 与 active-flow state 混层。

缓解：

- 首版只做宿主 preflight 注入
- 把结构化暴露延后为后续能力

### 风险 3

如果读取失败被静默吞掉，问题会长期存在但难以排查。

缓解：

- 固化 `loaded / missing / invalid / read_error`
- 要求宿主可观测，但不要求升级成用户门禁

## 规划结论

`preferences-preload-v1` 应被收口为一条很窄的主线：

1. 宿主在进入 Sopify 前按配置稳定解析 `preferences.md`
2. 成功时以固定前缀注入 LLM
3. 失败时 `fail-open with visibility`
4. 保持当前任务 > 偏好 > 默认规则，不改 runtime 状态模型

在这条主线稳定之前，不应把精力分散到 `RecoveredContext` 扩展、偏好分类或自动归纳上。
