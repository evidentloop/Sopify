# 变更提案: 推广前大收口整合

## 需求背景

Sopify 主航道 P0→P7 全部完成，核心产品（Protocol + Validator + canonical_writer + 一键 bootstrap）功能就绪。从"可用"到"值得推广"之间存在系统性收口缺口：用户首次触达的 README、产品输出质量、命令面复杂度、工程遗留物、安装脚本健壮性，都直接影响推广转化率。

本方案包是推广前最后一轮系统性优化，覆盖 7 个方向 + 全仓审计修复。

### 驱动因素

**产品层面：**

1. **竞品对标压力**：OpenSpec（营销口号 + walkthrough）、Spec-Kit（文档站 + 生态扩展）、Superpowers（叙事引导）、HelloAGENTS（交付证据链）——Sopify 技术深度足够但"第一印象"感染力不足
2. **输出质量差距**：output-contract.md 过度约束（"同一回复最多选一种主结构"），导致宿主输出只能是"合规的表格"，而非真正好读的交付物
3. **命令面冗余**：`~go exec` 作为 legacy 命令仍暴露给用户，蓝图 P4d Companion 已明确应被 host-level 入口语义取代
4. **首次触达断层**：安装完成到 `~go` 之间缺少引导和 wow moment
5. **推广内容缺位**：无掘金/V2EX/英文博客等推广文章

**工程层面（全仓审计发现）：**

6. **本地配置泄露**：`.claude/settings.local.json` 含开发者绝对路径且被 git 追踪；`.agents/history/` 同理
7. **陈旧引用残留**：`~summary` regex 在 installer 遗漏；`~compare` 测试断言未清理
8. **安装脚本缺陷**：`bootstrap.sh` 接受 `init` 参数但静默忽略；`sopify_init.py` docstring 缺参数说明；`install.sh` 无 `python`/`py` 回退
9. **文档不一致**：`external-repo-quickstart` 引用不存在路径；`examples/sopify.config.yaml` 不完整；`CONTRIBUTING.md` 引用旧脚本
10. **.gitignore 缺失**：`.env`、`.venv/`、`.claude/settings.local.json`、`.agents/history/` 未忽略

### 横向竞品快照

| 项目 | 定位 | 对 Sopify 的启发 |
|------|------|----------------|
| OpenSpec | Spec-first 框架 | 营销口号感染力、"see it in action" |
| Spec-Kit | 企业级 Spec 工具 | 文档站专业度、生态扩展模式 |
| Superpowers | Agent 行为纪律 | 叙事引导、过程可见性 |
| HelloAGENTS | AI CLI 工作流层 | 交付证据链、产品化包装 |

Sopify 的不可替代面：**可验证的便携式证据与授权语义**（fail-closed 授权回执 + 跨宿主可恢复状态 + 可审计项目记忆）。推广策略围绕这一核心，不在 spec 方法论或 agent 编排上与竞品正面竞争。

评分:
- 方案质量: 8/10
- 落地就绪: 7/10

评分理由:
- 优点: 7 方向 + 审计修复覆盖完整，发布门槛明确，图形资产 tech-graph 自主执行消除外部依赖
- 扣分: Wave 2 cover 封面仍需人工介入；推广文章需用户审阅发布

## 变更内容

按执行波次排列（详见 design.md 技术方案）：

**Wave 1（内核收口 + 工程修复）：**
1. **D2: 输出增强系统** — output-contract.md Rich Readable 层 + 交付物增强条款
2. **D3: 命令面收敛** — 直接移除 `~go exec` 用户命令，`~go` 自动检测活动 plan
3. **D5: 发布前工程收口** — 绝对路径清理、.gitignore 补全、陈旧引用修复、安装脚本修复、文档一致性修复

**Wave 2（体验层）：**
4. **D1: README 重写与视觉资产升级** — 吸收 Wave 1 所有 README 变更，一次性完整重写
5. **D4: 首次触达链路优化** — 安装后欢迎信息 + 空白状态引导

**Wave 3（推广放大）：**
6. **D6: 推广内容矩阵** — 掘金 / V2EX / 英文 / 社交短内容

**Wave 4（推广后推进）：**
7. **D7: Runtime Phase 2 收缩** — 仅方案设计，不执行

## 影响范围

- 模块: skills（ZH + EN）、README、assets、runtime（router/guard/engine）、installer、docs、.sopify-skills、examples、tests
- 文件: 预估 50-60 个文件变更

## 风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| D7 runtime 收缩暴露隐藏依赖 | installer 链路 | D7 仅出方案，推广后独立执行 |
| D5 审计修复范围大 | 意外回归 | 修复后跑完整测试套件验证 |
| D1 cover 封面图需人工设计 | 交付节奏 | 技术图用 tech-graph 自主生成；仅 cover 封面（4.5）需人工介入 |
| `.gitignore` 变更影响其他开发者 | 工作流 | 仅添加通用忽略项，不删除现有条目 |
