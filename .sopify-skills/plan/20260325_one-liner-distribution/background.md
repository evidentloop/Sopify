# 变更提案: one-liner-distribution

## 需求背景

当前 Sopify 已经具备较完整的接入内核：

1. `scripts/install_sopify.py` 能安装宿主提示层、global payload，并按需预热 workspace bundle。
2. `sopify status` / `sopify doctor` 已能把宿主支持矩阵、workspace 状态与诊断结果做成机器可读与用户可读输出。
3. 首次在项目仓库触发 Sopify 时，workspace 仍可按现有 bootstrap 主链自动补齐 `.sopify-runtime/`。

但从新用户角度看，当前第一步仍然偏“仓库开发者路径”而不是“产品接入路径”：

1. README 的安装方式仍要求先拿到仓库，再调用 `bash scripts/install-sopify.sh --target ...`。
2. 用户虽然最终能得到可诊断的状态面，但第一步路径本身不够短，也没有把“装完后立刻验证是否接入成功”收成默认体验。
3. 现有安装入口更像 repo-local helper，而不是一个可公开传播的官方接入命令。

同时，当前仓库已经存在一条面向 repo/main 的时间戳版本线：

1. release-relevant commit 会通过本地 hook 触发 `release-sync`，同步 README badge、CHANGELOG 与 `SOPIFY_VERSION`
2. 这类版本更适合作为 repo/main 侧的开发版本与追踪版本
3. 它并不天然等同于“外部用户可放心跟随的 stable 安装版本”
4. 但它本身已经是精确 build id，和现有工具链天然兼容，不需要再发明第二套版本编号

因此，本轮除了把入口缩短，还必须补齐“官方 stable 入口到底指向什么”的来源模型，而不是只解决脚本托管地址。

本轮真正要解决的是“用户如何更快开始用 Sopify”，而不是继续优化 runtime 内部结构。因此，这条实现线应定位为分发入口产品化，而不是新的 installer / runtime 子系统。

同时需要先承认两个现有实现事实：

1. `run_install()` 依赖的是完整 `repo_root`，而不是单个 Python 文件。宿主提示层源目录、`installer/` 模块、`runtime/` 目录以及 `scripts/sync-runtime-assets.sh` 都来自仓库快照。因此，v1 必须明确 stable 来源模型为“release asset 作为 bootstrap 入口 + 同 tag GitHub source archive 作为实际安装快照”；不采用“两个脚本 asset 直接完成全部安装”，也不在 v1 引入新的自定义 release bundle 格式。
2. `--workspace` 只代表“安装时顺手预热某个仓库”，不是接入 Sopify 的必填项。默认 one-liner 安装完成的事实是“宿主提示层 + global payload 已就绪”；workspace bundle 会在用户首次进入项目仓库触发 Sopify 时，由现有 bootstrap / preflight 主链自动补齐。这是正常主路径，不是降级路径。

## 外部参考与批判学习

本 plan 会参考 HelloAGENTS、Superpowers、Spec Kit，但只学习对 Sopify 当前阶段真正有帮助的部分：

1. HelloAGENTS
   - 值得学: 多渠道接入、安装后验证、失败后给用户明确下一步。
   - 不照抄: 同时铺很多渠道、同时覆盖很多宿主。Sopify 当前正式宿主仍只有 `codex / claude`，不应借分发之名扩大支持面。
2. Superpowers
   - 值得学: 按宿主给出自然的安装入口，让用户先完成接入，而不是先理解内部结构。
   - 不照抄: 依赖 agent 自己去读取长安装说明或自由执行文档。Sopify 需要的是确定性的安装、bootstrap 与 doctor 结果，而不是 prompt 驱动的安装说明书。
3. Spec Kit
   - 值得学: shell / PowerShell 双入口、一键路径与 inspect-first 路径并存、把“最短路径”收成官方入口。
   - 不照抄: `uvx` / 初始化型工具模型。Spec Kit 更像一次性项目初始化；Sopify 是宿主提示层 + payload + workspace bundle 的持续接入，不应伪装成纯一次性 CLI。

收口后的学习原则只有三条：

1. 入口要短；
2. 安装逻辑仍只有一套事实源；
3. 装完必须马上可验证、可诊断。

评分:
- 方案质量: 9.0/10
- 落地就绪: 9.0/10

评分理由:
- 优点: 现有 install / bootstrap / status / doctor 主链已经存在，且 stable/dev 分层、版本策略、release asset 渲染 contract、workspace 懒加载语义都已收口，方案边界清晰，对用户价值直接。
- 扣分: 仍需在实现层补齐 root script 渲染、inspection API 调整与 release smoke 收口；整体已可执行，但还不是零风险落地。

## 变更内容

1. 新增官方 stable 分发入口：
   - `install.sh`（macOS / Linux）
   - `install.ps1`（Windows）
   - 默认指向 GitHub Releases latest asset，而不是 `raw/main`
   - asset 本身只承担 bootstrap；实际安装从同一 release tag 的 GitHub source archive 临时展开后执行
   - `main` 分支中的脚本保留 dev 默认语义；stable asset 在发布时渲染出固定 release tag 的版本
2. 新增 stable inspect-first 路径：
   - 下载与 stable one-liner 同一份 release asset
   - 允许人工查看后再执行
3. 保留 `raw/main` 与 repo-local `scripts/install-sopify.sh` / `scripts/install_sopify.py` 作为 dev / maintainer 入口，不与官方 stable 入口混用。
4. 为远程入口新增一个薄 distribution facade，复用当前 installer core，而不是复制安装逻辑。
5. 默认把“安装后立刻给出 status / doctor 摘要 + resolved source metadata”做成用户第一感知。
6. 在 README / README_EN 中把 stable one-liner 放到安装章节首屏，同时保留 inspect-first；`raw/main` 只进入维护者文档。

## 范围边界

本 plan 的 v1 范围只包括：

1. root 级远程分发脚本：
   - `install.sh`
   - `install.ps1`
2. distribution facade：
   - 新增共享编排层（可落在 `installer/distribution.py` 或等效模块）
   - 抽出远程分发共用的参数、来源元数据、结果渲染与 post-install verification 逻辑
3. 复用现有安装主链：
   - `scripts/install_sopify.py`
   - `installer/payload.py`
   - `installer/inspection.py`
   - `scripts/sopify_status.py`
   - `scripts/sopify_doctor.py`
4. stable release asset contract：
   - latest release 至少提供 `install.sh` / `install.ps1`
   - stable 脚本默认再下载同 tag 的 GitHub source archive 到临时目录，并从 snapshot 内运行 `scripts/install_sopify.py`
   - public stable release 的 tag 直接复用被选中 build 的现有版本字符串，不新增第二套 semver
   - release title 可做人类可读摘要，但 GitHub Release tag、stable asset 内嵌 source ref、README badge、CHANGELOG latest、`SOPIFY_VERSION` 在该 release commit 上保持同一 build version
   - v1 不新增自定义 release bundle 格式，只定义手动发布约定，不要求 CI 自动上传
5. 安装与分发相关文档：
   - `README.md`
   - `README_EN.md`
   - `CONTRIBUTING.md`
   - `CONTRIBUTING_CN.md`
6. 分发 smoke / contract 测试：
   - 临时 HOME
   - 临时 workspace
   - shell / PowerShell 参数对齐
   - stable / dev channel 对齐

## 非目标

本 plan 明确不包含：

1. `runtime-gate-degradation-mode`
2. PyPI / npm / Homebrew 等渠道发布
3. 新增 `codex / claude` 之外的宿主
4. 重做 `scripts/install_sopify.py` 的 installer core 语义
5. 将分发入口扩成新的“全局 Sopify 产品 CLI”
6. 默认 host bridge 安装主链、Cursor 插件、Cursor CLI parity
7. 要求 CI 自动创建 GitHub Release 或自动上传 release asset
8. 为 v1 补完整的 sha256 校验链
9. 将每次 release-relevant commit 自动升级为公开 stable release
10. 为 v1 设计新的自定义 release bundle / 仓库打包格式

## 前置条件

1. 在 README 首屏切换到 stable one-liner 之前，必须先发布第一个 public stable release。
2. 该 release 至少要让 `releases/latest/download/install.sh` 与 `install.ps1` 可访问。
3. 首屏文案切换不能早于 stable URL 的真实可用时间点。

## 成功标准

完成后至少满足以下结果：

1. 新用户可以通过一条官方命令完成 `codex` 或 `claude` 的基础接入，而不必先手动 clone 仓库。
2. README 首屏官方入口固定走 GitHub Releases latest asset，而不是 `raw/main`。
3. 远程入口不复制 install / payload / bootstrap / doctor 的业务逻辑，只做环境检查、源码下载和 installer facade 调用。
4. 安装完成后，用户能直接看到：
   - 当前走的是 stable 还是 dev
   - 解析到的 release tag / ref
   - 使用了哪个 asset
   - 宿主提示层是否安装完成
   - payload 是否完整
   - workspace 是否已预热，或将在首次项目触发时自动 bootstrap
   - 下一步该去哪里触发 Sopify
5. one-liner 失败时，能明确区分：
   - 缺少 Python
   - 目标宿主不受支持
   - payload / bundle 安装失败
   - workspace bootstrap 失败
6. README 首屏安装说明以 stable one-liner 为主，但同时保留 inspect-first 变体，不把远程脚本执行写成唯一正确姿势。
7. 公开 stable release 由维护者显式发布，不与 repo/main 的时间戳开发版本混淆。

## 风险评估

- 风险: 远程脚本逐渐长成第二套 installer，后续与 repo-local 入口漂移。
  - 缓解: 远程脚本固定为 thin wrapper；业务逻辑统一下沉到 Python facade。

- 风险: 为了做“真正一行安装”而过早引入 PyPI / npm / Homebrew，范围从产品接入滑向发布工程。
  - 缓解: v1 只做 release asset bootstrap + 同 tag source archive 下载，不进入 package registry。

- 风险: stable 与 dev 没有清晰分层，README 文案与实际执行内容随 `main` 漂移。
  - 缓解: stable 只指向 GitHub Releases latest asset；`raw/main` 只保留给维护者路径。

- 风险: `main` 脚本与 stable release asset 共用同一份默认 source ref，导致 dev 入口误拉取旧 tag 或不存在的 release。
  - 缓解: `main` 脚本保持 dev 默认语义；发布时再渲染 stable asset，把 source ref 固定为当前 release tag。

- 风险: release asset contract 未定义，导致 stable URL 存在但 latest release 中没有对应资产。
  - 缓解: 将 `install.sh` / `install.ps1` 作为正式 release 的必备资产写入 plan 与 smoke checklist；v1 先采用手动发布约定。

- 风险: README 首屏改成 stable one-liner 时，`latest` 还没有对应 public release，导致官方入口悬空。
  - 缓解: 把“先发布第一个 public stable release”设为 README 切换前置条件，不满足前不得切首屏。

- 风险: 分发入口为了“更智能”而默认猜宿主、猜 workspace，结果让失败更难诊断。
  - 缓解: 非交互模式要求显式 `--target`；交互模式只做有限提示，不做黑盒猜测。

- 风险: 安装成功但用户仍不知道下一步如何触发 Sopify，导致“装上了但没开始用”。
  - 缓解: 安装结果默认附带 status / doctor 摘要与宿主级 next step；无 `--workspace` 时明确提示“首次在项目仓库触发时会自动 bootstrap”。

## 实施前最终收口

为避免本轮再次退化成“讨论分发很好，但落地变成渠道工程”，先固定七条约束：

1. 当前真正要解决的是“更快接入”，不是“更多渠道”。
2. 当前唯一正式宿主仍是 `codex / claude`；分发入口不扩宿主面。
3. 现有 `status / doctor / bootstrap` 是这条线的底座，不另造平行诊断面。
4. 官方 stable 入口固定使用 GitHub Releases latest asset，脚本再解析到同 tag 的 GitHub source archive 执行安装；`raw/main` 不进入 README 首屏。
5. 公开 stable release 的 tag 直接复用被选中 build 的现有版本字符串，不新增第二套 semver；release title 只做人类可读摘要。
6. `--workspace` 是 prewarm，不是安装必填；默认安装完成后，workspace 会在首次项目触发时自动 bootstrap。
7. 只要 one-liner 已能稳定调用既有 install 主链、输出可见验证结果，并明确展示来源元数据，就算 v1 成立；渠道扩展一律后置。
