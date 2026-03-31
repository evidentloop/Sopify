# Pilot Round 1 Review Sheet

## Purpose

This sheet records the row-level audit log for the completed `45`-sample first-round pilot.

Use it together with:

- `pilot_sample_matrix.md`
- `trigger_matrix.md`
- `pilot_review_rubric.md`

This file is detailed audit evidence backing the final aggregation and decision pass. It is not the summary decision artifact itself.

Post-v1 note:

- `Batch 2/3` now serve as post-v1 calibration work.
- They do not block `v1 implementation complete`.
- Their output calibrated trigger wording, example boundaries, and threshold realism without reopening the `v1` layering decision.
- Local `evidence/pilot_round1/**` files were externalized on `2026-03-31`; use `external_archive://...` locators in this sheet (see `evidence_archive_notice.md`).

## Review Flow

1. Run Batch 1 first: `sopify-skills` (`SOP-01` to `SOP-15`).
2. Treat Batch 1 as `plan-core pilot`; prioritize plan / decision / execution-confirm / meta-review related samples.
3. Run the sample in the target repo and keep the raw conversation / transcript.
4. Save the evidence path first, then fill the row.
5. Judge `actual_behavior`, `trigger_correctness`, `helpfulness`, `light_scene_harm`, and `extra_turns` using `pilot_review_rubric.md`.
6. After Batch 1, do a stop-check before continuing to `freyr-h5pages` and `rs-sdk`.
7. After all `45` rows are filled, update the aggregation worksheet and compare against the current pilot target thresholds.

## Batch 2/3 Result Artifacts

- Batch 2 evidence: `external_archive://pilot_round1/freyr-h5pages/batch2_observations.md`
- Batch 2 stop-check: `external_archive://pilot_round1/freyr-h5pages/batch2_stopcheck.md`
- Batch 3 evidence: `external_archive://pilot_round1/rs-sdk/batch3_observations.md`
- round aggregation: `external_archive://pilot_round1/round1_aggregation.md`

## Batch Order

| Batch | Repo | Role | Samples | Decision Gate |
| --- | --- | --- | --- | --- |
| `batch_1` | `sopify-skills` | `plan-core pilot` | `SOP-01` to `SOP-15` | finish first, then decide whether to continue |
| `batch_2` | `freyr-h5pages` | `business validation` | `FH5-01` to `FH5-15` | run only after Batch 1 is acceptable |
| `batch_3` | `rs-sdk` | `sdk/tool + control validation` | `RS-01` to `RS-15` | run only after Batch 1 is acceptable |

## Batch 1 Stop-Check

Before entering Batch 2, explicitly review whether Batch 1 already shows any of the following:

- plan scenarios are systematically over-triggered and become obviously heavier
- clear `A2/A4` plan samples are frequently under-triggered
- `C1/C2` control samples in `sopify-skills` show obvious regression
- reviewers no longer trust the current trigger boundary for plan-related requests

If any of the above is true, hold rollout and revise rules before continuing.

## Round Metadata

| Field | Value |
| --- | --- |
| `round_id` | `pilot_round_1` |
| `rule_version` | `first_principles_layering_v1_pilot` |
| `workspace_scope` | `preferences.md + analyze subset` |
| `promotion_target_thresholds` | `helpfulness >= 80% ; false_positive <= 10% ; false_negative <= 20% ; median_extra_turns <= 1` |
| `batch_1_focus` | `plan-core pilot in sopify-skills` |
| `review_window` | `2026-03-22` |
| `reviewers` | `codex` |
| `notes` | `45-row pilot aggregation completed; final promotion decision deferred by current scope` |

## Aggregation Worksheet

Fill these values after the 45 rows are reviewed.

| Metric | Value | Notes |
| --- | --- | --- |
| `expected_trigger_count` | `30` | `A1/A2/A3/A4` |
| `expected_no_trigger_count` | `15` | `C1/C2` |
| `intervention_count` | `30` | `consult_challenge_trigger + deep_trigger + light_clarification` |
| `helpful_count` | `29` | only `helpful` |
| `over_trigger_count` | `0` | only on expected `no_trigger` rows |
| `under_trigger_count` | `0` | only on expected `trigger` rows |
| `helpfulness_rate` | `96.7%` | `29 / 30` |
| `false_positive_rate` | `0%` | `0 / 15` |
| `false_negative_rate` | `0%` | `0 / 30` |
| `median_extra_turns` | `0` | intervention samples only |
| `quick_fix_regression` | `no` | `15` control samples show no regression |
| `promotion_ready_decision` |  | `hold / review / propose-promotion` |

## Batch 1 Interim Stop-Check

- `batch_1` status: completed for `sopify-skills`
- Interim evidence: `external_archive://pilot_round1/sopify-skills/batch1_observations.md`
- Interim decision: `hold`
- Stop-check summary: `external_archive://pilot_round1/sopify-skills/batch1_stopcheck.md`

## Batch 2/3 Current Status

- `batch_2`: completed as repo-grounded post-v1 calibration review for `freyr-h5pages`
- `batch_3`: completed as repo-grounded post-v1 calibration review for `rs-sdk`
- final promotion decision remains unset until `round1_aggregation.md` is filled

## Review Table

Allowed values:

- `expected_behavior`: `trigger` / `no_trigger`
- `actual_behavior`: `deep_trigger` / `consult_challenge_trigger` / `light_clarification` / `direct_no_trigger`
- `trigger_correctness`: `correct_trigger` / `over_trigger` / `under_trigger`
- `helpfulness`: `helpful` / `neutral` / `not_helpful` / `n/a`
- `light_scene_harm`: `none` / `minor` / `major` / `n/a`
- `extra_turns`: `0` / `1` / `2` / `3+`
- `final_disposition`: `accepted` / `partially_accepted` / `rejected`

Signal basis shorthand:

- `A1` -> `W1 + (W2 or W3)` or `W1 + S2`
- `A2` -> `S2`
- `A3` -> `S3 (+W3)`
- `A4` -> `S1 (+S4)`
- `C1` -> `N1`
- `C2` -> `N2/N3`

| sample_id | environment | repo | label | signal_basis | expected_behavior | candidate_request | actual_behavior | trigger_correctness | helpfulness | light_scene_harm | extra_turns | final_disposition | evidence_path | notes | reviewer | reviewed_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SOP-01 | runtime/infra | sopify-skills | A4 | S1 (+S4) | trigger | 把 `runtime_gate` 和 `preferences_preload` 的 helper 合并成一个统一入口，减少 manifest 里的 limits 配置重复。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-01 | 以 `consult + analyze challenge` 轻量进入长期 contract 分析，符合本轮 phase-1 范围。 | codex | 2026-03-22 |
| SOP-02 | runtime/infra | sopify-skills | A4 | S1 (+S4) | trigger | `current_handoff.json` 和 `current_run.json` 里都有 execution gate，是否应该收敛成一个唯一机器事实源？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-02 | 现在能显式识别为 `A4` 机器事实源问题，不再漏掉。 | codex | 2026-03-22 |
| SOP-03 | runtime/infra | sopify-skills | A2 | S2 | trigger | 把 `~go exec` 改成普通开发主链路默认入口，省掉执行确认。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-03 | 先挑战 shortcut 路径假设，而不是被 active plan 的 execution confirm 抢路。 | codex | 2026-03-22 |
| SOP-04 | runtime/infra | sopify-skills | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 优化当前 decision checkpoint 体验，让用户觉得更顺一点。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-04 | 模糊体验诉求保持轻量 challenge，不再被误拉长。 | codex | 2026-03-22 |
| SOP-05 | runtime/infra | sopify-skills | A3 | S3 (+W3) | trigger | compare 结果现在读起来太重，想加更多解释文本；有没有更轻的改法？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-05 | `A3` 的更轻路径信号已被保留下来。 | codex | 2026-03-22 |
| SOP-06 | runtime/infra | sopify-skills | A4 | S1 (+S4) | trigger | consult 路由要不要直接在 runtime 里生成正文回答，而不是只写 handoff？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-06 | consult/runtime contract 分叉已能在轻量 challenge 中暴露。 | codex | 2026-03-22 |
| SOP-07 | runtime/infra | sopify-skills | A4 | S1 (+S4) | trigger | `topic_key` 要不要重新参与 no-active-plan 自动复用？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-07 | 长期复用策略问题已进入 `A4` challenge。 | codex | 2026-03-22 |
| SOP-08 | runtime/infra | sopify-skills | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 想把 blueprint 和 `project.md` 的职责再统一一下，避免用户看不懂。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-08 | 仍维持轻量，不再错误进入 planning / execution-confirm。 | codex | 2026-03-22 |
| SOP-09 | runtime/infra | sopify-skills | A2 | S2 | trigger | 去掉 runtime gate，宿主直接调用默认 runtime 入口就行。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-09 | shortcut 提案已先进入 challenge，而不是直接被 active plan 截胡。 | codex | 2026-03-22 |
| SOP-10 | runtime/infra | sopify-skills | C1 | N1 | no_trigger | 补一行 README 里的 runtime gate helper 路径说明。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-10 | 已回到 `quick_fix`，轻场景不再退化。 | codex | 2026-03-22 |
| SOP-11 | runtime/infra | sopify-skills | C1 | N1 | no_trigger | 修一个 `tests/test_runtime.py` 里断言文案的 typo。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-11 | typo fix 已稳定回到 `quick_fix`。 | codex | 2026-03-22 |
| SOP-12 | runtime/infra | sopify-skills | C2 | N2/N3 | no_trigger | 解释一下 `execution_confirm_pending` 和 `decision_pending` 的区别。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-12 | 纯解释问题保持 direct consult。 | codex | 2026-03-22 |
| SOP-13 | runtime/infra | sopify-skills | C2 | N2/N3 | no_trigger | 看下 `current_run.json` 当前状态是什么意思。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-13 | 纯状态解释问题保持 direct consult。 | codex | 2026-03-22 |
| SOP-14 | runtime/infra | sopify-skills | C1 | N1 | no_trigger | 给 manifest 某个 limits 字段补一个简短注释。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-14 | 注释级请求已回到 `quick_fix`。 | codex | 2026-03-22 |
| SOP-15 | runtime/infra | sopify-skills | C2 | N2/N3 | no_trigger | 这个 plan 现在还有哪些风险点？ | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/sopify-skills/batch1_observations.md#sop-15 | plan meta-review bypass 继续生效。 | codex | 2026-03-22 |
| FH5-01 | business | freyr-h5pages | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 在权益中心支持“首任车主备案 V2.0”，先帮我分析要落哪些页面和模块。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-01 | 现有 `firstOwnerFiling` 已具备完整多页流程与接口层，触发后能把问题从“新开页面”改成“基于现有流扩展 V2.0”。 | codex | 2026-03-22 |
| FH5-02 | business | freyr-h5pages | A2 | S2 | trigger | 直接在 `charging_piles` 页面里塞一个备案弹窗，先这样做最快。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-02 | `charging_piles` 是独立权益确认流；现有备案流程已拆成独立 route tree，直接塞弹窗属于明显路径先行。 | codex | 2026-03-22 |
| FH5-03 | business | freyr-h5pages | A4 | S1 (+S4) | trigger | NIO、Alps、Firefly 的备案页是共用一套，还是按品牌拆开做？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-03 | 当前只有 NIO 具备 `firstOwnerApi*` 与 `filingDetail` 配置，品牌拆分是明确的长期 contract 问题。 | codex | 2026-03-22 |
| FH5-04 | business | freyr-h5pages | A3 | S3 (+W3) | trigger | 想把 `shared` 里的 Layout 复制到 `apps/cn/nio` 本地改，避免影响别的品牌。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-04 | `firstOwnerFiling` 已直接复用 shared Layout；更低成本的替代是局部包装或扩 props，而不是复制共享组件。 | codex | 2026-03-22 |
| FH5-05 | business | freyr-h5pages | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 优化 offline 包访问备案页的体验。 | light_clarification | correct_trigger | helpful | n/a | 1 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-05 | 线下体验问题已被现有 alias/hash/root redirect/App guard 分散，先问清入口痛点比直接展开方案更合适。 | codex | 2026-03-22 |
| FH5-06 | business | freyr-h5pages | A4 | S1 (+S4) | trigger | 新页面配置放 `default.config.json`，还是走 Polaris 远端配置？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-06 | 仓库已形成“静态网关/路径进 config，动态内容进 Polaris”的分层，这类配置归属需要先讲 contract。 | codex | 2026-03-22 |
| FH5-07 | business | freyr-h5pages | A3 | S3 (+W3) | trigger | 备案流程想加本地缓存，避免重复填写，先帮我判断最小改法。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-07 | 现有流程已具备 draft save/detail 与 Pinia store，先复用服务端草稿比新增本地缓存层更小更稳。 | codex | 2026-03-22 |
| FH5-08 | business | freyr-h5pages | A4 | S1 (+S4) | trigger | 多品牌埋点是走统一 tracker 规则，还是页面自己各自打点？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-08 | 各 brand 都有 tracker/apm 配置，但实现并不完全一致；先分清公共 pageview 与页面业务事件边界是有价值的。 | codex | 2026-03-22 |
| FH5-09 | business | freyr-h5pages | A2 | S2 | trigger | 只要补一个 router hash alias，就算支持离线备案页了吧？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-09 | 现有备案页 alias 已齐备；离线访问还依赖根重定向、hash/history 模式与流程守卫，单点 alias 不是完整目标。 | codex | 2026-03-22 |
| FH5-10 | business | freyr-h5pages | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 把权益中心首页改得更清晰一点，但我还没想好范围。 | light_clarification | correct_trigger | helpful | n/a | 1 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-10 | 这是典型业务侧模糊目标，先缩清“哪一个首页、清晰指什么、优先改信息结构还是入口曝光”是必要的一步。 | codex | 2026-03-22 |
| FH5-11 | business | freyr-h5pages | A4 | S1 (+S4) | trigger | 通用备案表单组件应该放 `shared/`，还是先只在 `apps/cn/nio` 落地？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-11 | 现在只有 NIO 有完整备案流，组件归属不应先抽象到 `shared/`，这是典型的复用边界判断题。 | codex | 2026-03-22 |
| FH5-12 | business | freyr-h5pages | A3 | S3 (+W3) | trigger | 想为所有页面都加一层新的 fetch 封装，先评估是不是值得。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-12 | 仓库已统一在 `@nio-wad/hooks.fetch` 之上按页面/域做薄封装；再加一层全局 fetch 很可能重复建设。 | codex | 2026-03-22 |
| FH5-13 | business | freyr-h5pages | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 想补一套 debug 流程，让每个 brand 本地都能稳定跑起来。 | light_clarification | correct_trigger | helpful | n/a | 1 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-13 | 根脚本与 shared 已有多品牌 debug 入口，先问清当前失败品牌/环境/账号注入缺口，比直接新建统一 debug 层更有效。 | codex | 2026-03-22 |
| FH5-14 | business | freyr-h5pages | A4 | S1 (+S4) | trigger | 品牌配置和地区配置要不要拆成两层 provider？ | consult_challenge_trigger | correct_trigger | neutral | n/a | 0 | partially_accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-14 | 这是合理的长期边界问题，但当前 repo 主要是按 app/config 文件注入，`provider` 语言略超前，触发正确但收益一般。 | codex | 2026-03-22 |
| FH5-15 | business | freyr-h5pages | C1 | N1 | no_trigger | 把 `apps/cn/nio/README.md` 里的 `build:web` 和 `build:offline` 说明补完整。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/freyr-h5pages/batch2_observations.md#fh5-15 | 边界清晰的 README 补充仍应保持 `quick_fix`，不能被业务上下文拉重。 | codex | 2026-03-22 |
| RS-01 | sdk/tool + quick-fix/control | rs-sdk | A4 | S1 (+S4) | trigger | `hooks` 和 `config-provider` 要不要继续共用一套 build/doc pipeline，还是按包拆开？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-01 | 根脚本已统一编排 `build:doc/build:lib`，但包内仍各自维护实现；这是典型“统一编排 vs 独立包边界”问题。 | codex | 2026-03-22 |
| RS-02 | sdk/tool + quick-fix/control | rs-sdk | A2 | S2 | trigger | 业务项目里的 fetch 逻辑我想直接复制进 `hooks` 包，先这样快点上线。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-02 | `hooks` 已有 `useFetch/useNativeFetch` 与 interceptor 机制，直接搬业务 fetch 逻辑进通用包是明显路径先行。 | codex | 2026-03-22 |
| RS-03 | sdk/tool + quick-fix/control | rs-sdk | A3 | S3 (+W3) | trigger | `rs-cli` 新增模板生成时，是否应该先复用现有 shared utils，而不是重写一套 prompts 流程？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-03 | `@rs-sdk/shared` 目前更偏工程配置共享，不是成熟的 CLI prompts 抽象；触发后能避免“为了复用而复用”。 | codex | 2026-03-22 |
| RS-04 | sdk/tool + quick-fix/control | rs-sdk | A1 | W1 + (W2 or W3) or W1 + S2 | trigger | 优化 `config-provider` 的接入体验。 | light_clarification | correct_trigger | helpful | n/a | 1 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-04 | “接入体验”未指明是离线接入、runtime 注册、文档入口还是 DX，先缩窄痛点比直接开方案更稳。 | codex | 2026-03-22 |
| RS-05 | sdk/tool + quick-fix/control | rs-sdk | A4 | S1 (+S4) | trigger | `config-provider` 要不要统一合并 offline 配置和 runtime 配置能力？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-05 | 包内其实已经同时存在 `OfflineConfigProvider` 和 `RuntimeConfigProvider`；真正问题是能力边界是否继续分层，而不是简单“合并/不合并”。 | codex | 2026-03-22 |
| RS-06 | sdk/tool + quick-fix/control | rs-sdk | A3 | S3 (+W3) | trigger | 想在 `hooks` 里新增一套 `useRequest`，先帮我判断是不是重复建设。 | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-06 | 现有 `useFetch/useNativeFetch` 已覆盖核心请求抽象；新增 `useRequest` 很可能只是换名重包。 | codex | 2026-03-22 |
| RS-07 | sdk/tool + quick-fix/control | rs-sdk | A4 | S1 (+S4) | trigger | `doc-sites` 和各 package 的 README，到底谁应该是真正文档源？ | consult_challenge_trigger | correct_trigger | helpful | n/a | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-07 | 当前 repo 已出现 README、story、doc-sites 三套入口不一致，属于真实的文档事实源分叉。 | codex | 2026-03-22 |
| RS-08 | sdk/tool + quick-fix/control | rs-sdk | C1 | N1 | no_trigger | 修 `hooks` README 里一个示例拼写问题。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-08 | 纯 README typo 修复应保持轻量。 | codex | 2026-03-22 |
| RS-09 | sdk/tool + quick-fix/control | rs-sdk | C1 | N1 | no_trigger | 给 `rs-cli` 增加 `--help` 文案说明。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-09 | CLI help 文案补充属于边界明确的小改。 | codex | 2026-03-22 |
| RS-10 | sdk/tool + quick-fix/control | rs-sdk | C2 | N2/N3 | no_trigger | 解释一下 `hooks` 和 `config-provider` 的职责区别。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-10 | 这是纯职责解释题，不应强拉成架构讨论。 | codex | 2026-03-22 |
| RS-11 | sdk/tool + quick-fix/control | rs-sdk | C1 | N1 | no_trigger | 给 `config-provider` 的 story 文档补一个 README 链接。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-11 | 文档互链补充仍是 bounded docs tweak。 | codex | 2026-03-22 |
| RS-12 | sdk/tool + quick-fix/control | rs-sdk | C1 | N1 | no_trigger | 调整 CLI banner 文案和输出样式。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-12 | 虽然牵涉 CLI 体验，但请求边界清晰，仍应保持 quick-fix。 | codex | 2026-03-22 |
| RS-13 | sdk/tool + quick-fix/control | rs-sdk | C2 | N2/N3 | no_trigger | 看下 `packages/cli` 现在支持哪些子命令。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-13 | 直接回答即可；当前 CLI 只有 `init` 子命令。 | codex | 2026-03-22 |
| RS-14 | sdk/tool + quick-fix/control | rs-sdk | C1 | N1 | no_trigger | 把某个 package 的测试脚本命名和根脚本对齐。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-14 | 命名对齐类小修不该被拉成策略讨论。 | codex | 2026-03-22 |
| RS-15 | sdk/tool + quick-fix/control | rs-sdk | C2 | N2/N3 | no_trigger | 帮我 review 一下 `config-provider` README 的使用说明是否自洽。 | direct_no_trigger | correct_trigger | n/a | none | 0 | accepted | external_archive://pilot_round1/rs-sdk/batch3_observations.md#rs-15 | 这是已有文档的一次直接 review，不需要额外 challenge 模式。 | codex | 2026-03-22 |

## Notes

- If a sample is clearly mislabeled after execution, do not silently overwrite the row.
- Record the original row first, then explain the reclassification reason in `notes`.
- `4.3` should only be considered complete after this sheet has real reviewed outcomes, not just prefilled rows.
