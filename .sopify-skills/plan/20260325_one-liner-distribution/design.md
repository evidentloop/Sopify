# 技术设计: one-liner-distribution

## 技术方案

- 核心目标:
  - 把当前 repo-local 安装链路收成官方一行接入入口；
  - 让“安装完成并可验证”成为默认用户体验；
  - 保持 Sopify 现有 `install -> payload -> bootstrap -> status/doctor` 主链不变。
- 实现要点:
  - 入口脚本必须薄；
  - 安装逻辑仍只有一套单一事实源；
  - 一行入口和 repo-local 入口最终调用同一套 facade；
  - 安装完成后优先给用户状态真相，而不是只打印“success”。

## 设计原则

1. `one-liner-distribution` 是分发入口产品化，不是新的 installer 子系统。
2. 分发入口必须复用现有 `scripts/install_sopify.py` 背后的安装能力；不允许复制 payload / bootstrap / doctor 业务逻辑。
3. 入口缩短不能以降低可审计性为代价；inspect-first 路径必须保留。
4. 当前阶段优先解决“怎么更快开始用”，不把范围扩到 runtime gate、bridge、发布渠道或多宿主增长。
5. v1 的 stable 来源模型固定为“release asset bootstrap script + 同 tag GitHub source archive”，不另造第二套 release bundle 格式。
6. public stable release 的 tag 直接复用被选中 build 的现有版本字符串；release title 只做人类可读层，不新增第二套版本体系。

## 1. 产品形态

### 1.1 对外入口

v1 将入口明确分成 stable / inspect-first / dev 三层：

1. stable one-liner
   - macOS / Linux: `curl -fsSL https://github.com/<owner>/<repo>/releases/latest/download/install.sh | bash -s -- --target <host:lang>`
   - Windows: 指向同一 latest release asset 的 PowerShell 入口
2. stable inspect-first
   - 先下载与 stable one-liner 同一份 release asset
   - 人工查看
   - 再执行
3. dev / maintainer 入口
   - `raw/main/install.sh`
   - 只出现在开发者文档或贡献文档，不进入 README 首屏

对 Sopify 来说，这三层入口的职责不同：

1. stable one-liner 是官方推广入口，解决“第一步太长”的问题；
2. stable inspect-first 是官方审计入口，和 one-liner 保持同源可比对；
3. dev 入口服务维护者与开发者，不参与对外稳定承诺。

补充约束：

1. `releases/latest/download/<asset>` 是 stable channel，而不是 immutable address；
2. stable channel 跟随最新正式 release，不跟随 `main` 漂移；
3. inspect-first 必须和 stable one-liner 指向同一来源模型。
4. `main` 上的脚本内容保留 dev 默认语义；release asset 是发布时渲染出的 stable 版本，二者不能混成同一默认 source ref。

### 1.2 保留 repo-local 开发者路径

以下入口继续保留：

1. `bash scripts/install-sopify.sh --target ...`
2. `python3 scripts/install_sopify.py --target ...`

原因：

1. 仓库开发者与 CI 仍需要本地路径；
2. 分发入口本质上是这些入口的包装层，不是替代品；
3. 只要三者最终调用同一套 facade，就不会形成长期分叉。

## 2. 批判学习后的 Sopify-native 方案

### 2.1 从 HelloAGENTS 学什么

只学习以下三点：

1. 安装命令要短；
2. 环境检查与回退逻辑应前置；
3. 安装后必须给用户明确的诊断与下一步。

不采用：

1. v1 同时铺很多安装渠道；
2. 以 package registry 发布为首期前置条件；
3. 以新增更多宿主来证明“接入能力更强”。

### 2.2 从 Superpowers 学什么

只学习：

1. 给用户一个更自然的宿主接入面；
2. 安装文档尽量短，不让用户先理解内部结构。

不采用：

1. 让 agent 自己阅读长安装文档并即席执行；
2. 让 README 成为主要安装逻辑承载面。

Sopify 的安装结果必须继续由脚本与 doctor 证明，而不是由 prompt 或说明文档“推断应该成功”。

### 2.3 从 Spec Kit 学什么

只学习：

1. shell / PowerShell 双入口；
2. one-liner 与 inspect-first 并存；
3. 把“最短路径”变成文档首屏。

不采用：

1. `uvx` / init tool 的一次性模型；
2. 直接把 Sopify 伪装成通用项目初始化 CLI；
3. 为了 package-friendly 而重写当前 installer core。

## 3. 分层架构

### 3.1 Layer A: remote wrappers

新增两个 root 级入口：

1. `install.sh`
2. `install.ps1`

职责只允许包含：

1. 环境检查
2. 参数解析与最小交互
3. `main` 分支中的 root 脚本默认保留 dev 语义，例如 `SOURCE_REF="main"`，服务 `raw/main` / maintainer 入口
4. stable channel 下执行发布时渲染后的 release asset；该 asset 内固定 `SOURCE_REF="<release_tag>"`，再下载同 tag 的 GitHub source archive 到临时目录
5. dev channel 下才允许直接走 `raw/main` 或 repo-local snapshot
6. v1 可接受维护者在 release checklist 中用一条 `sed` 等价命令把 `SOURCE_REF="main"` 渲染成当前 release tag，不要求额外构建系统
7. 解析并透传 resolved source metadata（至少包含 source channel、resolved ref/tag、asset name）
8. 调用 Python facade

明确禁止：

1. 直接复制宿主安装逻辑
2. 直接复制 payload / bootstrap / doctor 逻辑
3. 在 shell / PowerShell 中手写宿主矩阵与状态判断

补充说明：

1. v1 不采用“自定义整仓库 release asset”方案；
2. 也不采用“stable 脚本再零散下载若干 Python 文件”方案；
3. 统一依赖 GitHub 自带的同 tag source archive，保持现有 `repo_root` 假设成立。
4. `raw/main/install.sh` 与 `releases/latest/download/install.sh` 是语义不同的两个入口，不共享同一默认 source ref。

### 3.2 Layer B: distribution facade

新增共享 Python facade，例如：

1. `installer/distribution.py`

建议职责：

1. 统一承接分发入口参数与 source metadata
2. 复用现有 `run_install()` 或将其抽成底层 install API
3. 在 install 结果后附加 post-install verification 结果
4. 生成更适合公开安装入口的渲染文本

它与当前 installer core 的关系应是：

1. installer core 继续负责“怎么安装”
2. distribution facade 负责“如何以分发入口方式调用并展示结果”

### 3.3 Layer C: existing install core

现有核心链路保持不变：

1. 宿主提示层安装
2. global payload 安装
3. 可选 workspace bootstrap
4. payload / bundle smoke

这里不新增新的安装真相源。

### 3.4 Layer D: post-install verification

安装完成后，distribution facade 优先直接复用现有 inspection API，而不是通过 subprocess 再跑 CLI：

1. `installer.inspection.build_status_payload`
2. `installer.inspection.build_doctor_payload`
3. `installer.inspection.render_status_text`
4. `installer.inspection.render_doctor_text`

v1 不要求把完整 JSON 原样打印给用户，但必须保证用户能看到：

1. 当前 target
2. host install 是否成功
3. payload 是否就绪
4. workspace bundle 是否健康
5. 若异常，reason code 与建议动作

补充约束：

1. 无 `--workspace` 时，不得偷偷用 `cwd` 充当 workspace root
2. inspection / distribution 层需要显式支持“workspace 未请求”的渲染语义

## 4. 参数与交互策略

### 4.1 `--target`

v1 规则：

1. 非交互模式必须显式传 `--target`
2. 交互式 TTY 中若未提供 `--target`，可按 registry 给出有限选择：
   - `codex:zh-CN`
   - `codex:en-US`
   - `claude:zh-CN`
   - `claude:en-US`

不做：

1. 自动猜测当前宿主
2. 默认选择某个宿主

### 4.2 `--workspace`

v1 规则：

1. `--workspace` 是 prewarm 参数，不是接入 Sopify 的必填项
2. 显式传入时，按现有语义执行 workspace bootstrap
3. 未传时，保留当前默认行为: 只安装 host prompt + payload
4. 若在交互式 TTY 且当前目录像真实项目仓库，可额外提示是否用当前目录预热，但不作为静默默认

这样既保留“最快安装”，也不会把当前目录自动写脏。

补充约束：

1. README 首屏的推荐 one-liner 不展示 `--workspace`
2. `--workspace` 只出现在 Quick Start 后续步骤或高级用法中
3. post-install 无 `--workspace` 时，应明确告知 `workspace will bootstrap on first project trigger`

### 4.3 stable channel / `--ref` override

v1 的默认版本行为固定如下：

1. 未提供 `--ref` 时，远程 stable 入口默认解析到 GitHub Releases latest asset
2. `--ref <tag>` 作为 expert / override 能力，可显式 pin 到某个正式 release
3. `--ref main` 或其他 branch 只服务开发者 / 维护者路径，不进入 README 首屏
4. `--ref` 保留在 contract 中，但不作为新用户第一步要学的概念

明确不做：

1. 自动解析多种 release channel 并智能回退
2. 将 `main` 伪装成官方稳定入口

原因：

1. 现在真正缺的是更短入口与稳定来源模型，不是完整版本分发系统；
2. stable 和 dev 必须显式分层，避免 README 文案与实际执行内容漂移。

### 4.4 发布节奏与版本策略

当前仓库已有基于 release hook 的时间戳版本，用于同步 README badge、CHANGELOG 与 `SOPIFY_VERSION`。这类版本继续视为 repo/main 侧的开发版本，不直接等同于公开 stable release。

v1 的公开版本策略固定如下：

1. GitHub Release 只在维护者显式确认“可作为官方稳定入口”时创建
2. `releases/latest` 是 stable channel，更新频率低于日常 commit 节奏
3. v1 只要求定义 release asset 发布 contract，不要求 CI 自动发布
4. release asset 固定至少包含 `install.sh` 与 `install.ps1`
5. stable release 的 tag 直接复用被选中 build 的现有版本字符串，不新增 semver 映射层
6. stable 安装所需源码默认来自同 tag 的 GitHub source archive，而不是额外上传的自定义 bundle asset
7. release title 可做人类可读摘要，但 GitHub Release tag、stable asset 内嵌 source ref、README badge、CHANGELOG latest、`SOPIFY_VERSION` 在该 release commit 上应保持同一 build version

这样可以同时保留：

1. `main` 的快速演进
2. stable one-liner 的可预期来源
3. 后续接入自定义域名时 contract 不变

### 4.5 首个 public stable release 前置条件

1. README 首屏切换到 stable one-liner 之前，必须先发布第一个 public stable release
2. 该 release 必须让 `releases/latest/download/install.sh` 与 `install.ps1` 实际可访问
3. 不允许出现 README 已承诺 stable URL，但 latest release 仍为空的状态

## 5. 结果渲染

### 5.1 基础结果

安装完成后，输出至少包含：

1. `target`
2. `source channel`
3. `resolved release tag / ref`
4. `asset name`
5. `host root`
6. `payload root`
7. `workspace`
8. `bundle root`
9. `smoke`

workspace 字段的 v1 语义固定如下：

1. 无 `--workspace`: `will bootstrap on first project trigger`
2. 有 `--workspace`: `pre-warmed at <path>`

### 5.2 追加的用户态信息

distribution facade 需要比 repo-local installer 多给两类信息：

1. 当前状态真相
   - 已安装什么
   - 哪一段完成了
   - 哪一段没完成
2. 下一步动作
   - 去哪个宿主里触发 Sopify
   - 若未传 `--workspace`，明确说明首次在项目仓库触发时会自动 bootstrap
   - 若失败，先看 `status` 还是 `doctor`
3. 来源真相
   - 当前走的是 stable 还是 dev
   - 最终解析到哪个 release tag / ref
   - 使用了哪个 asset

### 5.3 文案原则

1. 对用户讲“当前状态”和“下一步”，不讲内部实现细节
2. 对失败讲 reason code 和修复建议，不讲堆栈
3. 不把 README 上的安装文案写成内部维护文档

## 6. 测试与验证

### 6.1 contract tests

需要补的稳定验证至少包括：

1. shell / PowerShell 参数语义对齐
2. 远程入口只调用 facade，不复制 install 逻辑
3. 非交互模式下缺少 `--target` 会失败
4. 交互模式下 target 选择只来自 installable host registry
5. stable 默认解析到 GitHub Releases latest asset
6. stable 安装流程会进一步解析到同 tag source archive，而不是退回 `raw/main`
7. public stable release 的 tag 与 stable asset 中渲染出的 source ref 保持一致
8. `--ref` 作为 override 时，不会污染 stable 默认行为

### 6.2 smoke

需要增加 clean-environment smoke：

1. 临时 HOME
2. 临时 workspace
3. 走 one-liner facade
4. 验证 host prompt / payload / bootstrap / smoke / status / doctor 的组合结果
5. 验证 stable 输出能展示 resolved tag / asset name
6. 验证 stable 脚本与同 tag source archive 的组合可以独立完成安装

补充边界：

1. pre-release / CI smoke 只验证本地脚本渲染、参数 contract 与 installer 主链，不依赖真实 GitHub Release
2. 真实 `releases/latest` 下载验证归入 post-release maintainer manual smoke

### 6.3 回归边界

必须保证以下回归不出现：

1. repo-local installer 行为被破坏
2. `status` / `doctor` contract 被分发入口绕开
3. one-liner 成功但 repo-local install 失败，或反之
4. stable README 入口意外回退到 `raw/main`

## 7. v1 不做的事

1. 不引入 PyPI / npm / Homebrew 渠道
2. 不改 runtime gate contract
3. 不把 `default-host-bridge-install` 并入本 plan
4. 不把 Cursor 插件或其他宿主分发线绑进来
5. 不实现完整自更新机制
6. 不要求 CI 自动创建 GitHub Release 或上传 release assets
7. 不在 v1 实现 release asset 的 sha256 校验链
8. 不把每次 release-relevant commit 自动升级为公开 stable release

## 8. 交付判定

本 plan 的 v1 交付完成时，至少应满足：

1. README 首屏已经提供 Sopify 官方 one-liner
2. README 首屏使用 stable latest release URL，而不是 `raw/main`
3. stable 脚本会解析并下载同 tag GitHub source archive，而不是依赖 `main`
4. 远程脚本与 repo-local 安装共用同一安装真相源
5. 安装完成后默认给出 status / doctor 摘要，以及 resolved source metadata
6. 无 `--workspace` 的安装仍被视为完整接入；workspace 会在首次项目触发时自动 bootstrap
7. 用户可以在不 clone 仓库的前提下完成基础接入
8. README 切 stable 首屏前，latest release 已真实存在且可用
9. 这条线没有改动 runtime gate、checkpoint、plan lifecycle 主契约
