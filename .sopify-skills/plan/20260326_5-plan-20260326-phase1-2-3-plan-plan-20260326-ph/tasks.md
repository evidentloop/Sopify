---
plan_id: 20260326_5-plan-20260326-phase1-2-3-plan-plan-20260326-ph
feature_key: 5-plan-20260326-phase1-2-3-plan-plan-20260326-ph
level: standard
lifecycle_state: active
knowledge_sync:
  project: review
  background: review
  design: review
  tasks: review
archive_ready: false
---

# 任务清单: B1 文档收口后的实施与验证

## 0. 范围冻结
说明：Section 0 属于前置对齐 / 验证项，用于确保本 plan、program plan 与 `design.md` 已冻结结论保持一致；默认不引入新的产品拍板，勾选标准以文档与实施边界对齐完成为准。
- [x] 0.1 将本 plan 明确定位为原 `Plan B1` 的升级版：`global bundle + thin stub/pin + ignore + compatibility`
- [x] 0.2 显式锁定非目标：不进入 `B2 / B3 / Plan C`，不修改 `.sopify-skills` knowledge contract，不并入 `execution gate / risk classifier` 的 `auth_boundary` 误报修复，不交付 `Migration Utility / prune`
- [x] 0.3 在 `20260326_phase1-2-3-plan` 中同步当前优先级与依赖章节
- [x] 0.4 冻结本轮允许触达的实现面：`bootstrap_workspace.py / payload.py / validate.py / inspection.py / workspace_preflight.py / hosts/* / runtime/manifest.py / runtime/gate.py / runtime/output.py / sopify_status.py / sopify_doctor.py / smoke/tests`
- [x] 0.5 冻结本轮统一解析顺序：`stub -> global bundle -> global manifest -> gate/preload -> legacy fallback`
- [x] 0.6 冻结本轮统一迁移原则：`stub 优先`、`fallback 可见`、`no_silent_downgrade`

## 0.C | 本轮补充冻结
- [x] 0.C.1 明确保持现有认证边界（`option_1`）：本轮不允许修改认证/权限行为
- [x] 0.C.2 明确 B1 只新增 CLI 渲染层：机器契约保持不变，CLI 只做人类可读适配
- [x] 0.C.3 明确 `Migration Utility` 与 `prune` 仅记 `post-B1 backlog`，不纳入本轮 DoD

## 0.H | 前置门禁
- [x] 0.H.1 在本 plan 与 `20260326_phase1-2-3-plan` 中同步 `20260327_hotfix` 为 pre-B1 prerequisite，不把 stale-state Hotfix 并回 B1 实现面
- [x] 0.H.2 将所有触碰 `runtime/state.py / runtime/context_recovery.py / runtime/router.py / runtime/engine.py / runtime/handoff.py / runtime/_models/proposal.py` 协商态一致性的 B1 子任务标记为 `blocked by 20260327_hotfix`
- [x] 0.H.3 将所有依赖 checkpoint / handoff 唯一出口的 `runtime gate / doctor / status / smoke / regression` 验收标记为 `blocked by 20260327_hotfix`
- [x] 0.H.4 明确仅 `bootstrap / thin stub / payload index / manifest / ignore / host adapter` 的纯 filesystem / contract 脚手架可与 Hotfix 并行
- [x] 0.H.5 为并行切片冻结硬边界：不得 `import runtime.state`，不得读取 `.sopify-skills/state/*.json`，不得根据 `current_handoff.json / current_run.json` 推导业务逻辑
- [x] 0.H.6 约定以 `20260327_hotfix` 的 H5 通过作为解除 B1 状态链路阻塞的唯一门
  `20260327_hotfix` 的文档边界、冻结结论与 blocked/parallel-allowed 标签已完成同步；真实 `runtime_gate` smoke 已通过，现可优先恢复 `4.3 / 4.4 / 4.5 / 5.4` 这组此前被门禁压住的切片。

## 0.A 实施顺序约束
- [ ] 0.A.1 以已冻结 stub schema、Primary Outcome Contract、Host Ingress Contract 与 payload index contract 为先，bootstrap / preflight / diagnostics 全部按同一套 contract 落实现
- [ ] 0.A.2 `workspace classifier`、`validate`、`inspection` 三处必须同轮收口，禁止只改单点判定器
- [ ] 0.A.3 `host-aware preflight` 与 `payload index` 必须在 `doctor/status/smoke` 之前稳定，否则 diagnostics 会持续漂移；其中 payload-manifest 的 host-delegated 指针字段名固定为 `active_version`
- [ ] 0.A.4 测试、迁移说明、自检脚本放在最后收口，但 `primary_code` 矩阵与 hint contract 必须先补齐再补测试

## 0.B | 首次写入许可模型
- [ ] 0.B.1 按已冻结结论落首次写入许可模型的入口边界与触发优先级：显式强意图命令、`confirm_bootstrap` checkpoint、禁止纯语义自动 bootstrap，并明确 `~go / ~go plan` 何时可直接落 thin stub
- [ ] 0.B.2 按已冻结白名单落宿主入口：明确 `~go / ~go plan / ~go init` 的许可语义，以及 `~compare / 未激活仓库上的 ~go finalize` 默认不触发 bootstrap；其中 `~go init` 只作为合法入口，不阻塞 `B1` 主链交付
- [ ] 0.B.3 按已冻结职责边界收敛语义判定层：只允许输出结构化 intent proposal，不得直接驱动 `bootstrap / plan scaffold / proposal materialization / workspace write`
- [ ] 0.B.4 按已冻结生成物边界落首次 auto-bootstrap：默认只写 thin stub，不默认生成 `sopify.config.yaml`
- [ ] 0.B.5 按已冻结路由语义落实“已激活 workspace”后续行为：继续走 `consult / minimal / adaptive`，不得把激活态等同于“所有请求都强管控”
- [ ] 0.B.6 按已冻结授权位置收敛 host ingress / preflight：首次写入许可必须发生在宿主入口前置决策，不得下沉到 repo-local runtime 内部再确认
- [ ] 0.B.7 按已冻结规则落实 brake layer 的最小覆盖面：`不要改 / 先分析 / 只解释 / 不写文件 / explain-only` 等高确定性表达优先阻断写入意图
- [ ] 0.B.8 按已冻结规则落 `monorepo` 首次激活默认 root 逻辑：`显式 root 指定 > 最近的有效 ancestor marker > 当前 cwd`；`sopify.config.yaml` 不作为上层复用信号；向上 walk 命中的第一个 ancestor marker 只有通过最低有效性才允许复用，若最低有效性失败则立即停止并 `fail-closed` 回退 `cwd`；`repo-root` 级激活必须显式指定
- [ ] 0.B.9 按已冻结边界落实 marker 最低有效性：仅用于 root 选择，定义为 `JSON 可解析 + schema_version 存在`，不提前承担 `preflight / validate` 的 stub 健康度校验
- [ ] 0.B.10 按已冻结降级策略落 `readonly / non-interactive / non-git / monorepo 歧义` 的 `confirm_bootstrap` 回退条件：不得卡在确认、不得 silent activation、不得静默写到错误 root
  评审记录：`preflight block` 回合下的 receipt/state fallback 路径目前固定为 `.sopify-skills/...`，作为 pre-config fail-safe contract 明确保留；本轮不追随 custom `plan.directory`，避免 block 分支重新依赖 config。
  评审记录：payload manifest 存在但 JSON 非法/非 object 时，doctor 侧当前仍统一折叠为 `MISSING_REQUIRED_FILE`；已评审为 diagnostics debt，后续在 reason-code matrix 阶段细化，不作为当前阻断项。

## 1. P0 | Bootstrap 与 Ignore 基线
- [ ] 1.1 盘点 bootstrap 当前写路径、ancestor `marker` 探测与 `target_root` 解析逻辑，标出必须拆除的 vendored 前提，并移除 `config` 参与 root 复用的旧分支
- [ ] 1.2 按已冻结 contract 落 `ignore_mode = exclude | gitignore | noop`：git 默认 `.git/info/exclude`，显式 commit-lock 才写 `.gitignore`，non-git visible `noop`
- [ ] 1.3 设计 `.git/info/exclude` 写入策略：优先使用 `BEGIN/END sopify-managed` block 承载 Sopify 条目，best-effort 幂等追加，不覆盖用户自定义条目，不以文件锁或严格去重为前提
- [ ] 1.4 按 bootstrap-time explicit choice 落 commit-lock / `ignore_mode`：写入 thin stub、保持 sticky workspace policy、仅允许显式 re-bootstrap / update 切换；v1 至少对 Sopify 可安全归属的旧 managed block / 已知条目做确定性 reconciliation，超出安全判定范围的残留给出可见提示与手动 remediation，不要求完整 clean/deactivate
- [ ] 1.5 设计 non-git repository 的 reason code、可见提示与 fail-open 行为
- [ ] 1.6 明确 bootstrap 输出需要暴露的 observability 字段：ignore_target、ignore_mode、reason_code、workspace_kind、target_root、root_resolution_source；并暴露仅覆盖 `thin stub + managed block` 的手动停用路径
- [ ] 1.7 明确 `confirm_bootstrap` 文案与 direct-write 提示：至少暴露 `target_root / root_resolution_source / fallback_reason`，且不暗示会自动清理 `.sopify-skills/state/` 或知识库

## 2. P1 | Thin Stub Contract
- [ ] 2.1 按已冻结 schema 落 workspace-local thin stub：`schema_version / stub_version / bundle_version / required_capabilities / locator_mode / legacy_fallback / ignore_mode / written_by_host`
- [ ] 2.2 落 thin stub 的最小有效性规则、缺失字段降级规则与 schema evolution 兼容策略，并显式区分“root 选择最低有效性”与“preflight 合同有效性”；至少覆盖 `locator_mode` 缺失视为 `global_first`、`bundle_version` 缺失或 `null` 视为 host-delegated、禁用 semver range / `latest` / 空字符串
  进展记录：当前已落过渡态实现。workspace `.sopify-runtime/manifest.json` 在保持旧 vendored entry 字段兼容的前提下，开始写入 thin stub 字段，并在 `validate.py / inspection.py / bootstrap_workspace.py` 中统一校验默认值与冲突规则；完整 `stub-only` 收口仍待 payload index 与入口链切换后继续推进。
  阶段标签：`B1 compatibility phase`。在本阶段，`stub-only => non-ready` 是预期行为，不视为 defect；`ready` 仍要求 manifest 合同通过且 workspace runtime 文件完整。
- [ ] 2.3 将 workspace classifier 从“整包文件存在”改为“stub 有效 + global bundle 可解析”
- [ ] 2.4 拆分三层职责：root 选择最低有效性、workspace stub 校验、global bundle 校验、legacy vendored 校验
- [ ] 2.5 明确 bootstrap 生成物只写 thin stub，不再复制重型 runtime bundle；thin stub 写入采用同目录临时文件 + 原子替换，不引入跨平台文件锁前提
- [ ] 2.6 落 legacy vendored fallback 决策表与观测字段：`global_only + missing/incompatible -> no fallback`；`global_first + legacy_fallback=true + missing/incompatible -> visible legacy fallback`；禁止 silent downgrade
- [ ] 2.7 明确 `runtime/manifest.py` 与 installer contract 的边界，避免 stub 与 global bundle manifest 混用

## 3. P2 | Host-Aware Preflight
- [ ] 3.1 为 preflight 入口补正式 ingress contract：`activation_root / host_id / payload_root` 为必填输入，`requested_root` 为可选 observability 输入且推荐宿主在可确定时提供；不再默认靠目录探测推断宿主
- [ ] 3.2 将 payload root 解析责任收拢到 `installer/hosts/*` 与 host base contract
- [ ] 3.3 移除把 `.codex -> .claude` 固定探测顺序当成最终 payload 选择逻辑的实现
- [ ] 3.4 固化 `stub -> global bundle -> manifest-first gate/preload -> legacy fallback` 的解析顺序
  进展记录：当前已支持显式 `payload_root` 与 `host_id` 进入 preflight；在提供显式 ingress 信息时，不再把 `.codex -> .claude` 固定顺序当作最终 payload 选择逻辑。兼容阶段下，legacy home/env 扫描仍保留为 fallback，以避免提前切断现有宿主链路。
- [ ] 3.5 明确 dual-host 同仓库下的选择规则、冲突提示与 `host_mismatch / ingress_contract_invalid` 的产出边界，并让 monorepo root 复用结果进入同一 observability 词汇表
- [ ] 3.6 确保 gate / preload 的入口仍由 resolved global bundle manifest 暴露，而不是宿主侧硬编码

## 4. P3 | Payload Index 与 Diagnostics
- [ ] 4.1 定义 payload-manifest 中的 versioned bundle index schema，与 `bundles/<version>/` 布局对应，并包含 host-delegated 模式所需的唯一 `active_version` 指针；其值格式必须与 thin stub 的 `bundle_version` Exact Pin 一致
- [ ] 4.2 将 `installer/payload.py` 从单 `bundle/` 假设改为按 `bundle_version` 两态查找目标 bundle：Exact Pin 精确命中，Host-Delegated 读取唯一 `active_version` 指针
- [ ] 4.3 同步更新 `validate.py`、`inspection.py` 的 bundle discovery 与兼容性判定
- [ ] 4.4 同步更新 `scripts/sopify_status.py`、`scripts/sopify_doctor.py` 的可见输出，展示 stub/global/legacy 解析结果，并针对 `global_bundle_missing / global_bundle_incompatible / global_index_corrupted / legacy_fallback_selected` 提供不同的 actionable hint
- [ ] 4.5 同步更新 `scripts/check-install-payload-bundle-smoke.py` 与 distribution 相关校验入口
- [ ] 4.6 在迁移窗口内兼容旧 `bundle/` 结构，但明确标记为 legacy source，不再作为默认目标态
- [ ] 4.7 确保 payload index 升级后，installer / doctor / status / smoke 消费的是同一套 reason code 与 source-kind 词汇

## 4.A | CLI Rendering Layer
- [ ] 4.A.1 冻结 CLI 渲染适配层边界：只消费 `primary_code + action_level + evidence` 与 `violations[]`，不反向定义新的机器字段
- [ ] 4.A.2 为 `ingress_contract_invalid` 设计终端友好渲染：把 `activation_root / host_id / payload_root` 的 violation 渲染成字段级高亮与明确 remediation，不直接裸打嵌套 JSON 错误树
- [ ] 4.A.3 为 `global_bundle_missing / global_bundle_incompatible / global_index_corrupted / legacy_fallback_selected` 定义分码渲染文案，保证 `status / doctor / CLI 面板` 行为一致
- [ ] 4.A.4 保留原始结构化 contract 的 debug / `--json` 出口，避免 CLI 友好文案反向污染 IDE / 自动化消费路径
- [ ] 4.A.5 为终端渲染补示例或快照，覆盖“普通用户视图”和“调试原始视图”两层输出

## 5. P4 | Compatibility / Observability / Tests
说明：`5.1 / 5.2` 是 `5.3 / 5.A.*` 的前置物；未补齐 `primary_code` 矩阵与 hint contract 前，不得启动 P4 测试。
- [ ] 5.1 定义完整 `primary_code` 矩阵：`stub_selected / stub_invalid / global_bundle_missing / global_bundle_incompatible / global_index_corrupted / legacy_fallback_selected / legacy_fallback_blocked / host_mismatch / ingress_contract_invalid / non_git_workspace / ignore_written / root_reuse_ancestor_marker / invalid_ancestor_marker / root_confirm_required`
- [ ] 5.2 将 `primary_code + action_level + typed evidence` 接入 bootstrap、preflight、validate、inspection、status、doctor 与 CLI 渲染层的输出面，并冻结 reason-code-specific 的用户可见 hint 分类
- [ ] 5.3 补回归测试矩阵：new workspace、legacy vendored workspace、dual-host same repo、non-git workspace、commit-lock mode、monorepo nearest-ancestor-marker reuse、monorepo invalid-nearest-ancestor-marker fail-closed、monorepo explicit-root override；其中 dual-host same repo 只断言 `host_mismatch + typed evidence`，不绑定提示文案模板
- [ ] 5.4 补 smoke 验证矩阵：一次安装、bootstrap、global bundle 解析、fallback visibility、默认入口不变
- [ ] 5.5 更新迁移说明：新仓库、已 bootstrap 仓库、旧 vendored 仓库分别怎么过渡，并确保迁移说明与 `doctor / status` 的 actionable hint 一致；本轮仅补可见性与说明，不提供一键迁移器
- [ ] 5.6 更新安装输出与自检脚本，确保用户能看到“当前走的是 stub/global/legacy 哪条路径”
- [ ] 5.7 （待确认是否纳入本轮）为 installer 入口补 Python 最低版本 preflight：覆盖 `install.sh / scripts/install-sopify.sh / scripts/install_sopify.py` 三入口，在 `Python < 3.11` 时稳定输出明确的 `phase / reason_code / detail / next_step`，避免在导入 `StrEnum` 前直接抛原始 traceback；若确认纳入，本任务同时要求补最小回归验证

## 5.A 验证分层
- [ ] 5.A.1 单测先覆盖 contract 与判定器：stub validity、payload index、host-aware resolution、fallback gating、`ingress_contract_invalid` 的 `violations[]` 顺序与短路规则，以及 CLI 渲染层的字段级映射；dual-host 相关断言只覆盖 `host_mismatch + typed evidence`，不覆盖提示文案模板
- [ ] 5.A.2 集成测试覆盖 bootstrap -> preflight -> gate entry 的主链，不允许只测单函数
- [ ] 5.A.3 smoke 最后验证“一次安装 + 多仓触发 bootstrap + 默认入口不变”

## 6. 总验收门
- [ ] 6.1 新 workspace 默认不再复制重型 vendored runtime bundle
- [ ] 6.2 旧 workspace 仍能运行，且 fallback 可见
- [ ] 6.3 `doctor / status / smoke` 与新 payload index 结构保持一致
- [ ] 6.4 program plan 与 child plan 的优先级、边界、依赖保持一致
- [ ] 6.5 dual-host 同仓库不再靠目录探测顺序选 payload
- [ ] 6.6 git 仓库默认不制造 repo-level 脏 diff；commit-lock mode 行为可解释、可控
- [ ] 6.7 monorepo 首次激活默认不静默爬升到 `repo-root`；仅在最近的有效 ancestor marker 命中时复用上层，命中无效 ancestor marker 时立即 `fail-closed` 回退 `cwd`
- [ ] 6.8 本轮没有把 `A / B2 / C / B3` 的任务或语义，或 `execution gate / risk classifier` 的误报修复偷偷并入 B1

## 7. Post-B1 Backlog
- Direct switch preparation checklist
  - host first-hop 改造完成，不再依赖 workspace-local scripts 作为默认入口
  - `no workspace scripts` smoke 全绿
  - 回滚验证通过
  - 仅在上述门槛都满足后，才允许把 `stub-only` 从 non-ready 提升为 ready
- Migration Utility
  - 目标是为旧 vendored workspace 提供可确认的一键升级路径，但不属于当前 B1 交付门
- Bundle prune
  - 目标是清理未被任何 thin stub 引用的历史 `bundles/<version>/`，但不属于当前 B1 交付门
