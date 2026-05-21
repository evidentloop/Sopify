# P7 Background: Repo 激活模型迁移（Copilot-first 验收）

## 一句话

全局发动机已经就位；P7 把 repo 内的旧激活物（`.sopify-runtime/manifest.json` thin stub）替换为统一 workspace marker（`.sopify-skills/sopify.json`），repo-local pointer 按宿主需要决定是否追加，让任何外部 repo 都能最小代价接入。

## 动机

- P4d 证明了 repo-local 手工接入可行
- P6 把 StateStore/invariants/IO 切成独立包，新宿主可直接 import
- 全局发动机（`~/.codex/sopify/` payload manifest + versioned bundles + bootstrap helper）已在 installer 主线中就位
- 但 repo 内的 workspace 检测仍依赖 legacy `.sopify-runtime/manifest.json`（8 字段 thin stub）
- 外部 repo 接入时看到 `.sopify-runtime/` 和 `.sopify-skills/` 两个目录，心智负担高
- 需要把 repo 内激活物收敛为统一的新模型，并提供 bootstrap 命令 + diagnostics

## 目标态

P7 完成后：

1. repo 内只有 `.sopify-skills/` 一个 Sopify 目录；repo-local pointer 仅在宿主需要 repo-local discovery 时才追加（Codex/Claude 默认不写）
2. `.sopify-runtime/manifest.json` legacy stub 不再需要，激活物统一为 `.sopify-skills/sopify.json`
3. 完整 prompt asset 留在全局安装位置（`~/<host_dir>/<header_file>`），不落入 repo
4. 首次进入工作流有明确的 bootstrap 命令（`python3 -m sopify_bootstrap init`）+ diagnostics 反馈
5. 接续链路可走通（handoff 消费 + state 写入 via canonical_writer）
6. 统一的只有 sopify.json；repo-local pointer 是宿主适配策略，不是统一文件模型

## 不在范围

- 全局发动机改造（`~/.codex/sopify/` payload/bundle 层已就位，不动）
- Deep runtime 改动（runtime/ 目录本体不动）
- protocol.md 修改（P7 是激活物迁移，不是协议修订）
- 大规模 installer 重写（只做消费者检测路径的最小迁移）
- 人工试点验证（用机器 smoke 替代）

## 前置

| 依赖 | 状态 |
|------|------|
| P4d Copilot CLI Pilot | ✅ |
| P5 Contract Surface Shrinkage | ✅ |
| P6 Canonical Writer Cutover | ✅ |

## 最小交付证据

1. 至少 1 个非 Sopify repo 完成 Copilot + Sopify workspace 初始化并走通接续消费
2. 接入后只有 `.sopify-skills/` 一个 Sopify 目录（或明确记录为何 `.sopify-runtime/` stub 仍需保留）
3. 机器 smoke test 覆盖接入 happy path（bootstrap → state write → handoff consume）
4. README / examples 包含可独立跟随的端到端 demo

## 吸收项

- **Copilot Payload-Only Onboarding Proof**（原证据候选，tasks.md L97-103）→ 升级为 P7 主体
- **First-Use Adoption Proof**（原证据候选，tasks.md L69-79）→ 发布链 + examples + 视觉资产部分并入 P7
