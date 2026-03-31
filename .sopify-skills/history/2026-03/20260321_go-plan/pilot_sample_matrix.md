# Pilot Sample Matrix

## Purpose

This file defines the first-round candidate sample pool for the promotion gate pilot of "first-principles collaboration rules layered rollout".

It satisfies the current plan requirements for:

- minimum sample pool size: `>= 45`
- analyze-applicable samples: `>= 30`
- control samples: `>= 15`
- pilot coverage across `runtime/infra`, `business`, and `sdk/tool + quick-fix/control`

This is a candidate pool for the first round, not the final scored pilot report.

## Environment Mapping

- `runtime/infra`: `/Users/weixin.li/Desktop/vs-code-extension/sopify-skills`
- `business`: `/Users/weixin.li/NIO_Project/EQUITY/freyr-h5pages`
- `sdk/tool + quick-fix/control`: `/Users/weixin.li/NIO_Project/rs-sdk`

Backup pools, not counted in the first 45:

- `/Users/weixin.li/NIO_Project/EQUITY/equity-front-ai-demo/equity-front`
- `/Users/weixin.li/NIO_Project/EQUITY/freyr-cards`

## Allocation Summary

| Repo | Environment | Total | Analyze | Control |
| --- | --- | ---: | ---: | ---: |
| `sopify-skills` | runtime/infra | 15 | 9 | 6 |
| `freyr-h5pages` | business | 15 | 14 | 1 |
| `rs-sdk` | sdk/tool + quick-fix/control | 15 | 7 | 8 |
| Total | - | 45 | 30 | 15 |

## Classification Rules

Analyze-applicable labels:

- `A1`: target is still ambiguous; clarification should happen first
- `A2`: the request gives an implementation path, not the real goal
- `A3`: a lower-cost or lower-risk alternative likely exists
- `A4`: architecture, contract, or long-term strategy split

Control labels:

- `C1`: quick-fix or low-risk direct edit; should not be stretched
- `C2`: pure consult or already-clear request; should not trigger challenge mode

Expected behavior:

- `Trigger`: deep interaction should trigger
- `No Trigger`: deep interaction should not trigger

## Candidate Samples

### 1. sopify-skills

| ID | Label | Bucket | Expected | Candidate Request |
| --- | --- | --- | --- | --- |
| `SOP-01` | `A4` | Analyze | Trigger | 把 `runtime_gate` 和 `preferences_preload` 的 helper 合并成一个统一入口，减少 manifest 里的 limits 配置重复。 |
| `SOP-02` | `A4` | Analyze | Trigger | `current_handoff.json` 和 `current_run.json` 里都有 execution gate，是否应该收敛成一个唯一机器事实源？ |
| `SOP-03` | `A2` | Analyze | Trigger | 把 `~go exec` 改成普通开发主链路默认入口，省掉执行确认。 |
| `SOP-04` | `A1` | Analyze | Trigger | 优化当前 decision checkpoint 体验，让用户觉得更顺一点。 |
| `SOP-05` | `A3` | Analyze | Trigger | compare 结果现在读起来太重，想加更多解释文本；有没有更轻的改法？ |
| `SOP-06` | `A4` | Analyze | Trigger | consult 路由要不要直接在 runtime 里生成正文回答，而不是只写 handoff？ |
| `SOP-07` | `A4` | Analyze | Trigger | `topic_key` 要不要重新参与 no-active-plan 自动复用？ |
| `SOP-08` | `A1` | Analyze | Trigger | 想把 blueprint 和 `project.md` 的职责再统一一下，避免用户看不懂。 |
| `SOP-09` | `A2` | Analyze | Trigger | 去掉 runtime gate，宿主直接调用默认 runtime 入口就行。 |
| `SOP-10` | `C1` | Control | No Trigger | 补一行 README 里的 runtime gate helper 路径说明。 |
| `SOP-11` | `C1` | Control | No Trigger | 修一个 `tests/test_runtime.py` 里断言文案的 typo。 |
| `SOP-12` | `C2` | Control | No Trigger | 解释一下 `execution_confirm_pending` 和 `decision_pending` 的区别。 |
| `SOP-13` | `C2` | Control | No Trigger | 看下 `current_run.json` 当前状态是什么意思。 |
| `SOP-14` | `C1` | Control | No Trigger | 给 manifest 某个 limits 字段补一个简短注释。 |
| `SOP-15` | `C2` | Control | No Trigger | 这个 plan 现在还有哪些风险点？ |

### 2. freyr-h5pages

| ID | Label | Bucket | Expected | Candidate Request |
| --- | --- | --- | --- | --- |
| `FH5-01` | `A1` | Analyze | Trigger | 在权益中心支持“首任车主备案 V2.0”，先帮我分析要落哪些页面和模块。 |
| `FH5-02` | `A2` | Analyze | Trigger | 直接在 `charging_piles` 页面里塞一个备案弹窗，先这样做最快。 |
| `FH5-03` | `A4` | Analyze | Trigger | NIO、Alps、Firefly 的备案页是共用一套，还是按品牌拆开做？ |
| `FH5-04` | `A3` | Analyze | Trigger | 想把 `shared` 里的 Layout 复制到 `apps/cn/nio` 本地改，避免影响别的品牌。 |
| `FH5-05` | `A1` | Analyze | Trigger | 优化 offline 包访问备案页的体验。 |
| `FH5-06` | `A4` | Analyze | Trigger | 新页面配置放 `default.config.json`，还是走 Polaris 远端配置？ |
| `FH5-07` | `A3` | Analyze | Trigger | 备案流程想加本地缓存，避免重复填写，先帮我判断最小改法。 |
| `FH5-08` | `A4` | Analyze | Trigger | 多品牌埋点是走统一 tracker 规则，还是页面自己各自打点？ |
| `FH5-09` | `A2` | Analyze | Trigger | 只要补一个 router hash alias，就算支持离线备案页了吧？ |
| `FH5-10` | `A1` | Analyze | Trigger | 把权益中心首页改得更清晰一点，但我还没想好范围。 |
| `FH5-11` | `A4` | Analyze | Trigger | 通用备案表单组件应该放 `shared/`，还是先只在 `apps/cn/nio` 落地？ |
| `FH5-12` | `A3` | Analyze | Trigger | 想为所有页面都加一层新的 fetch 封装，先评估是不是值得。 |
| `FH5-13` | `A1` | Analyze | Trigger | 想补一套 debug 流程，让每个 brand 本地都能稳定跑起来。 |
| `FH5-14` | `A4` | Analyze | Trigger | 品牌配置和地区配置要不要拆成两层 provider？ |
| `FH5-15` | `C1` | Control | No Trigger | 把 `apps/cn/nio/README.md` 里的 `build:web` 和 `build:offline` 说明补完整。 |

### 3. rs-sdk

| ID | Label | Bucket | Expected | Candidate Request |
| --- | --- | --- | --- | --- |
| `RS-01` | `A4` | Analyze | Trigger | `hooks` 和 `config-provider` 要不要继续共用一套 build/doc pipeline，还是按包拆开？ |
| `RS-02` | `A2` | Analyze | Trigger | 业务项目里的 fetch 逻辑我想直接复制进 `hooks` 包，先这样快点上线。 |
| `RS-03` | `A3` | Analyze | Trigger | `rs-cli` 新增模板生成时，是否应该先复用现有 shared utils，而不是重写一套 prompts 流程？ |
| `RS-04` | `A1` | Analyze | Trigger | 优化 `config-provider` 的接入体验。 |
| `RS-05` | `A4` | Analyze | Trigger | `config-provider` 要不要统一合并 offline 配置和 runtime 配置能力？ |
| `RS-06` | `A3` | Analyze | Trigger | 想在 `hooks` 里新增一套 `useRequest`，先帮我判断是不是重复建设。 |
| `RS-07` | `A4` | Analyze | Trigger | `doc-sites` 和各 package 的 README，到底谁应该是真正文档源？ |
| `RS-08` | `C1` | Control | No Trigger | 修 `hooks` README 里一个示例拼写问题。 |
| `RS-09` | `C1` | Control | No Trigger | 给 `rs-cli` 增加 `--help` 文案说明。 |
| `RS-10` | `C2` | Control | No Trigger | 解释一下 `hooks` 和 `config-provider` 的职责区别。 |
| `RS-11` | `C1` | Control | No Trigger | 给 `config-provider` 的 story 文档补一个 README 链接。 |
| `RS-12` | `C1` | Control | No Trigger | 调整 CLI banner 文案和输出样式。 |
| `RS-13` | `C2` | Control | No Trigger | 看下 `packages/cli` 现在支持哪些子命令。 |
| `RS-14` | `C1` | Control | No Trigger | 把某个 package 的测试脚本命名和根脚本对齐。 |
| `RS-15` | `C2` | Control | No Trigger | 帮我 review 一下 `config-provider` README 的使用说明是否自洽。 |

## Selection Notes

- First-round scoring should keep the current `45` as the minimum auditable pool.
- Execution order is fixed as:
  - `Batch 1`: `sopify-skills` as `plan-core pilot`
  - `Batch 2`: `freyr-h5pages`
  - `Batch 3`: `rs-sdk`
- `Batch 1` is not just another repo batch; it is the first stop-check for whether plan-related triggering is directionally correct.
- The final scored set may reorder individual samples, but should preserve:
  - `runtime/infra`: 15
  - `business`: 15
  - `sdk/tool + quick-fix/control`: 15
  - `analyze`: 30
  - `control`: 15
- Backup repos should only be used when one of the primary pools lacks natural samples of the required type.

## Follow-up Work

The next artifacts should build on this file:

1. trigger matrix
2. human review rubric
3. `pilot_round1_review_sheet.md` as the row-level first-round pilot run log
4. `external_archive://pilot_round1/**` as the completed cross-repo evidence set
5. standalone decision-pass closure after the full-round evidence
