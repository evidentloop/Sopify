# 变更提案: B1 升级为全局 Bundle + 本地 Thin Stub/Pin + Ignore/兼容迁移 + CLI 渲染收口

## 需求背景
当前 `.sopify-runtime/` 仍以 vendored bundle 的形式落到每个项目仓库里，这带来三个已确认的推广阻力：

1. workspace 侵入性偏高
   首次触发后会出现控制面目录，用户体感是“工具代码被打进了项目里”。
2. ignore 策略缺口
   当前 bootstrap 不负责给目标仓库补 ignore，容易把运行时目录直接暴露成脏改动。
3. control-plane 与 knowledge-plane 耦合仍然偏重
   若后续要做 host-aware preflight、dual-host 共存、版本 pin 与 no-silent-downgrade，可复用的重逻辑更适合留在宿主全局 payload 中，而不是继续 per-workspace 复制。
4. CLI 直接暴露结构化错误树的体验偏硬
   当 `ingress_contract_invalid` 或类似 contract 直接落成嵌套 JSON / reason tree 时，普通开发者很难在终端第一眼看懂“哪一层错了、该改哪里”。

基于前面的设计收口，本轮不再把这件事拆成“先 B1，后中期优化”两期，而是直接把原 `Plan B1` 升级为一次完整的 control-plane decoupling 子 plan：

- 全局保留 versioned runtime bundle 实体
- workspace 只保留极薄的 `.sopify-runtime/manifest.json` thin stub / pin
- bootstrap 同时补齐 ignore、host-aware preflight、legacy fallback 与可观测 reason code

本次回并现有 B1 的补充收口已经拍板，新增范围约束如下：

- 维持当前认证/权限边界，不把本轮扩展成权限行为改造
- B1 只新增 CLI 人类可读渲染层，不扩展为自动迁移器或历史 bundle 清理器
- `Migration Utility` 与 `prune` 明确降级为 `post-B1 backlog`

另外，当前已新增一个更前置的状态机门禁：`20260327_hotfix`。它不改变 B1 的 control-plane 目标，但会阻塞所有依赖 runtime 协商态唯一事实源的切片，原因是：

1. stale-state / ghost proposal / contradictory handoff 属于 runtime 基础一致性问题，不属于 B1 control-plane decoupling 本身
2. 如果带着这个缺陷直接推进 `runtime gate / doctor / status / smoke` 的恢复与验收，B1 会出现历史状态相关的随机失败
3. 因此 B1 当前只允许与该 Hotfix 并行推进纯 filesystem / manifest / payload index / thin stub / ignore 方向的结构工作

## 核心目标
1. 把重型 runtime bundle 从 workspace 默认体验中移走，保留 workspace-local 的最小控制面入口。
2. 明确 thin stub / global bundle / legacy vendored fallback 的优先级与契约，禁止 silent downgrade。
3. 保持 `manifest-first / runtime gate / preferences preload / handoff-first` 这条控制面主链可审计、可迁移、可回退。
4. 在不改变机器契约与现有认证边界的前提下，为 `status / doctor / CLI 面板` 增加友好的错误渲染层。
5. 在 `20260326_phase1-2-3-plan` 总纲中同步这条新 child plan 与 `20260327_hotfix` 的优先级 / 依赖关系，避免 program plan 与执行 plan 漂移。

## 变更内容
本 plan 聚焦以下范围：

1. control-plane contract
   - thin stub schema
   - global payload bundle index schema
   - stub-first / global-bundle-second / legacy-fallback-third 的解析顺序
   - 新 reason code 与降级可见性
2. installer / preflight / diagnostics
   - `installer/bootstrap_workspace.py`
   - `runtime/workspace_preflight.py`
   - `installer/payload.py`
   - `installer/validate.py`
   - `installer/inspection.py`
   - `runtime/output.py` 或等价 CLI 渲染适配层
   - `scripts/sopify_status.py`
   - `scripts/sopify_doctor.py`
   - `scripts/check-install-payload-bundle-smoke.py`
3. program sync
   - 现有总纲 `20260326_phase1-2-3-plan` 的优先级 / 依赖章节
   - 相关任务清单同步

## 影响范围
- 模块:
  - `installer/bootstrap_workspace.py`
  - `runtime/workspace_preflight.py`
  - `installer/payload.py`
  - `installer/validate.py`
  - `installer/inspection.py`
  - `installer/hosts/base.py`
  - `installer/hosts/codex.py`
  - `installer/hosts/claude.py`
  - `runtime/gate.py`
  - `runtime/manifest.py`
  - `runtime/output.py`
  - `scripts/sopify_status.py`
  - `scripts/sopify_doctor.py`
  - `scripts/check-install-payload-bundle-smoke.py`
  - `tests/test_installer.py`
  - `tests/test_installer_status_doctor.py`
  - `tests/test_distribution.py`
  - `tests/test_runtime_gate.py`
  - `tests/test_bundle_smoke.py`
- 文件边界:
  - 仅处理 control-plane / installer / diagnostics / compatibility
  - 仅补 CLI 渲染适配层，不改 `primary_code / action_level / evidence / violations[]` 的机器契约
  - `runtime/state.py / runtime/router.py / runtime/engine.py / runtime/handoff.py` 的协商态一致性修复由 `20260327_hotfix` 单独承接，不并入本 plan
  - 不改变 `.sopify-skills/plan/blueprint/history` 的知识路径 contract
  - 不进入 `B2 / B3 / Plan C` 的路径或状态机重构

## 非目标
1. 不把 `.sopify-runtime` 并入 `.sopify-skills`
2. 不修改 `plan_path / finalize / history / knowledge_layout` 的现有语义
3. 不实现 Ghost State / Ghost Knowledge / suspend-side-task 行为
4. 不在本轮改写 `ExecutionGate` 的核心字段名或 `gate_status` 值集
5. 不在本轮提供一键 `Migration Utility`；仅允许补迁移可见性、提示与说明
6. 不在本轮提供完整的 `prune / deactivate / clean` 命令；历史 bundle 清理延后到 post-B1 backlog

## Post-B1 Backlog
- Migration Utility
  - 提供类似 `~go doctor --fix` / `bootstrap_workspace.py --migrate` 的升级入口，安全扫描旧 vendored `.sopify-runtime/` 后替换为 thin stub
- Bundle prune
  - 提供轻量 `prune` 能力，回收未被任何 thin stub 引用的历史 `bundles/<version>/`

## 风险评估
- 风险: 只改 thin stub 字段、不改 bootstrap / validate / inspection 判定器，会导致所有新 workspace 被误判为 `INCOMPATIBLE`
- 缓解: 同时拆分 workspace stub 校验与 global bundle 校验，统一更新 installer / doctor / smoke

- 风险: dual-host 场景继续靠 `.codex -> .claude` 固定探测，可能拿错 payload
- 缓解: preflight 明确切到 host-aware payload 解析，禁止再依赖目录探测顺序做最终判定

- 风险: payload 从单 `bundle/` 改为 versioned index 后，doctor / inspection / validate / smoke 任一链路没跟上都会造成伪失败
- 缓解: 把 payload indexing 与 diagnostics 视为同一原子范围，测试一次性补齐

- 风险: ignore 直接改 repo `.gitignore` 可能制造额外脏 diff
- 缓解: 默认优先 `.git/info/exclude`，只有“提交版本锁”模式才写 `.gitignore`；非 git 仓库显式降级但不阻断

- 风险: legacy vendored fallback 如果不可观测，会让行为漂移难以排查
- 缓解: 新增 `stub 优先 / vendored fallback / no_silent_downgrade` 的 reason code 矩阵，并在 status / doctor / bootstrap 输出中可见

- 风险: 直接把结构化 contract 原样打印到 CLI，会让小白用户只看到 JSON 树，却不知道哪个字段需要修
- 缓解: 在 CLI 渲染层按 `primary_code + evidence` 转成人类可读提示，同时保留原始结构给 IDE / 调试模式消费

- 风险: 跳过 `20260327_hotfix` 直接推进涉及 checkpoint 恢复与 handoff 唯一出口的 B1 切片，会把 stale-state 问题带进验收，导致 `runtime gate / doctor / status / smoke` 出现 flaky failure
- 缓解: 将该 Hotfix 作为 B1 的显式前置门禁；当前 B1 只并行纯 filesystem / manifest / payload index / thin stub / ignore 脚手架

## 评分
- 方案质量: 9/10
- 落地就绪: 9/10
- 评分理由: 主体 control-plane 范围已冻结，CLI 渲染补充面清晰，且 `Migration Utility / prune` 已显式降到 post-B1 backlog；剩余复杂度主要集中在 diagnostics 与验证收口
