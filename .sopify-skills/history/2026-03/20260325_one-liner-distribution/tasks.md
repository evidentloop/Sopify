---
plan_id: 20260325_one-liner-distribution
feature_key: one-liner-distribution
level: standard
lifecycle_state: archived
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: true
plan_status: completed
---

# 任务清单: one-liner-distribution

固定约束已收口到 `background.md` / `design.md`，本文件只保留可执行任务。

## Group 1 — 分发 contract 与 facade

- [x] 1.1 新增共享 distribution facade（`installer/distribution.py`），统一承接 one-liner 入口参数、安装调用与结果渲染
- [x] 1.2 基于现有 `run_install()` 接入可复用分发入口 API，补齐 `source_metadata` 透传与 distribution 输出 contract，避免 shell / PowerShell 入口直接各自拼逻辑
- [x] 1.3 固定 distribution facade 的最小输入字段：`target / workspace / ref_override / interactive / source_channel / source_metadata`
- [x] 1.4 固定 distribution facade 的最小输出字段：install result + post-install verification summary + resolved source metadata + next step

**Gate — Group 1 完成后：**
- [x] 1.G repo-local installer 与 one-liner 入口已经可以调用同一套 Python facade，不再存在第二套安装逻辑

验收标准:

- 远程入口和本地入口共享单一事实源
- facade 只做编排与渲染，不吞掉 installer core 语义
- 后续 shell / PowerShell 改动不会影响 install 真相源

## Group 2 — root 级 one-liner 入口

- [x] 2.1 新增 root `install.sh`；stable 路径固定为“执行 GitHub Releases latest asset -> 解析当前 release tag -> 下载同 tag 的 GitHub source archive 到临时目录 -> 调用 snapshot 内的 Python facade”
- [x] 2.2 新增 root `install.ps1`，保持与 `install.sh` 等价的参数面、channel 语义和错误语义
- [x] 2.3 固定 v1 的远程基础参数面：`--target`、`--workspace`
- [x] 2.4 固定 `--ref` 为 override / expert 参数：默认不出现在 README 首屏，可用于 pin 到 tag，也可供开发者 pin 到 `main` 或 branch
- [x] 2.5 固定 release asset 发布 contract：每次正式 release 至少上传 `install.sh` / `install.ps1`；stable 安装源码来自同 tag 的 GitHub source archive；public stable release 的 tag 直接复用被选中 build 的现有版本字符串；v1 不引入自定义 release bundle asset，也不要求 CI 自动上传
- [x] 2.6 固定脚本渲染 checklist：`main` 分支中的 root 脚本保留 dev 默认语义（例如 `SOURCE_REF="main"`）；发布 stable asset 时必须将 source ref 渲染为当前 release tag，v1 可接受 `sed` 等价步骤
- [x] 2.7 非交互模式下缺少 `--target` 直接失败；交互式 TTY 才允许有限 target 选择

**Gate — Group 2 完成后：**
- [x] 2.G macOS/Linux 与 Windows 都存在官方 stable one-liner 入口，inspect-first 与 one-liner 指向同一来源模型，且二者不会复制 Python installer 业务逻辑

验收标准:

- shell / PowerShell 双入口语义一致
- stable 来源模型已明确，不再存在“release asset 或 repo snapshot”二选一歧义
- `raw/main` 脚本与 stable release asset 的 source ref 语义已明确分层
- `--target` 行为明确，不靠黑盒猜测宿主
- 远程脚本保持 thin wrapper，不滑成第二个 installer

## Group 3 — 安装后验证与用户可见结果

- [x] 3.0 调整 `installer/inspection.py` 的 `build_status_payload / build_doctor_payload` workspace 输入契约，使 inspection / distribution 层显式支持“workspace 未请求”语义；无 `--workspace` 时跳过 workspace 相关检查并渲染 `not requested / will bootstrap on first project trigger`；CLI `sopify status/doctor` 继续传当前目录，不破坏现有命令语义
- [x] 3.1 distribution facade 在 install 完成后优先复用 `installer.inspection` 的 `build_status_payload / build_doctor_payload / render_*` API 收集并渲染 `status / doctor` 摘要，而不是通过 subprocess 调 CLI；无 `--workspace` 时不得默认拿 `cwd` 充当 workspace root
- [x] 3.2 安装结果显式展示 `source_channel / resolved_release_tag_or_ref / asset_name`
- [x] 3.3 若提供 `--workspace`，安装结果中显式展示 workspace bundle 状态与 bootstrap 结果；未提供时输出 `will bootstrap on first project trigger`
- [x] 3.4 失败路径统一输出 reason code、失败阶段与建议下一步，而不是只输出原始错误文本
- [x] 3.5 成功路径统一输出宿主级 next step，例如“去 `codex` / `claude` 中触发 Sopify”；未提供 `--workspace` 时补充“workspace bootstrap 会在首次触发时自动完成，无需手动操作”

**Gate — Group 3 完成后：**
- [x] 3.G 用户在 one-liner 安装结束后，不必手动再查文档，也能知道当前是否已成功接入以及下一步怎么做

验收标准:

- 安装结果默认可诊断
- 状态面复用现有 inspection API，不额外引入一条 subprocess 维护面
- `status / doctor` 成为用户第一层可见真相，而不是隐藏在 README 深处
- 无 `--workspace` 的安装结果不会被误渲染成“缺失”或“未知”
- 成功与失败路径都能给出明确动作

## Group 4 — 首个 stable release 与 README 收口

- [x] 4.1（用户任务）在 README 首屏切换 stable one-liner 之前，先发布第一个 public stable release，使 `releases/latest/download/install.sh` / `install.ps1` 可用
- [x] 4.1a（用户任务）确认当前 remote 指向 `sopify-ai/sopify`，并将本轮 one-liner-distribution 实现推送到目标分支
- [x] 4.1b（用户任务）运行 `bash scripts/check-version-consistency.sh`，确认将要公开发布的 build version / tag
- [x] 4.1c（用户任务）运行 `python3 scripts/render-release-installers.py --release-tag "$TAG" --output-dir "$OUT_DIR"`，渲染 stable `install.sh` / `install.ps1` asset
- [x] 4.1d（用户任务）在 GitHub `sopify-ai/sopify` 创建同 tag 的 public Release，并上传 `$OUT_DIR/install.sh` 与 `$OUT_DIR/install.ps1`
- [x] 4.1e（用户任务）手动验证 `releases/latest/download/install.sh` / `install.ps1` 可访问，且 stable 安装输出展示 `source channel / resolved source ref / asset name`
- [x] 4.1f（用户任务）只有在 4.1e 验证通过后，才切 `README.md` / `README.zh-CN.md` 首屏安装入口到 stable one-liner
- [x] 4.2 在 `README.md` 的安装章节首屏提供 official stable one-liner（GitHub Releases latest asset），主命令不带 `--workspace`，并保留 inspect-first 变体
- [x] 4.3 在 `README.zh-CN.md` 中同步中文 stable 入口与 inspect-first 变体，主命令不带 `--workspace`
- [x] 4.4 inspect-first 明确下载与 stable one-liner 同一份 release asset，而不是另一套脚本来源
- [x] 4.5 `raw/main` dev 入口只出现在 `CONTRIBUTING*` 或维护者文档，不进入 README 首屏
- [x] 4.6 将当前 repo-local `scripts/install-sopify.sh` 入口下沉为开发者/源码安装路径，不再占用首屏主入口
- [x] 4.7 让 Quick Start 与 status/doctor 说明对齐，明确 `--workspace` 是高级 prewarm 用法、默认首次项目触发会自动 bootstrap
- [x] 4.8 更新 `CONTRIBUTING.md` / `CONTRIBUTING_CN.md`：明确 `raw/main` dev 入口、repo-local 安装路径、stable/dev 分层与 release asset 渲染约定

**Gate — Group 4 完成后：**
- [x] 4.G 新用户从 README 首屏即可完成安装、验证与首次触发，不必先理解仓库内部结构，且 stable URL 不是悬空入口

验收标准:

- 首个 public stable release 已存在
- 官方入口足够短
- inspect-first 仍可用
- README 不承诺尚未落地的渠道

## Group 5 — smoke 与回归测试

- [x] 5.1 增加 clean HOME + temp workspace 的分发 smoke，覆盖 host prompt、payload、workspace bootstrap、post-install verification
- [x] 5.2 增加 shell / PowerShell 参数 contract 测试，保证 `--target / --workspace / --ref(override)` 与 stable/dev channel 语义一致
- [x] 5.3 增加“one-liner 与 repo-local installer 结果一致”的回归测试
- [x] 5.4 增加“远程入口缺少 Python / 缺少 target / workspace 非目录”等高频错误路径测试
- [x] 5.5 增加 pre-release / CI smoke 边界说明：`5.1-5.4` 只验证本地脚本渲染、参数 contract 与 installer 主链，不依赖真实 GitHub Release
- [x] 5.6 增加 post-release maintainer manual smoke：确认 latest release 含 `install.sh` / `install.ps1`，stable 脚本能解析到同 tag source archive，且输出可展示 resolved tag / asset name；该项不作为 CI 自动 gate

**Gate — Group 5 完成后：**
- [x] 5.G one-liner 入口已由稳定 smoke 与 contract tests 覆盖，且不回归现有 install / bootstrap / doctor 主链

验收标准:

- 新入口不是只靠 README 手测
- 关键失败路径都有 deterministic coverage
- pre-release CI 与 post-release manual smoke 的边界清晰
- 分发入口与 installer core 不会悄悄漂移

## 明确延后项

- [-] 6.1 PyPI 发布
- [-] 6.2 npm wrapper / `npx sopify`
- [-] 6.3 Homebrew formula
- [-] 6.4 自动解析 latest release 与自更新
- [-] 6.5 `runtime-gate-degradation-mode`
- [-] 6.6 `default-host-bridge-install`
- [-] 6.7 `cursor-plugin-install`
- [-] 6.8 release asset 的 sha256 校验链
- [-] 6.9 GitHub Release / asset upload 的 CI 自动化

## 推荐实施顺序

1. Group 1: 先抽 distribution facade，固定单一事实源
2. Group 2: 先锁定 stable 来源模型，再补 `install.sh / install.ps1`
3. Group 3: 再把 `status / doctor` 摘要接到安装结果中
4. Group 4: 先发第一个 public stable release，再切 `README.md` / `README.zh-CN.md` 首屏入口
5. Group 5: 用 smoke 与 contract tests 收口
