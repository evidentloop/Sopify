# Protocol Commit + 最小跨宿主 Smoke

scope: protocol.md 进版本控制 + 最小 Convention 模式 roundtrip 验证
status: 待确认

---

## 1. protocol.md commit 准入条件

只修阻断项，不扩概念。当前 protocol.md（239 行）已结构完整。

**必须修的阻断项：** 无。审查后未发现断链引用、未完成段落或空表。§6 和 §7 已标注 `informative / draft`，这是诚实标注，不需要为了 commit 强行升级为 normative。

**commit 内容：**
- `git add .sopify-skills/blueprint/protocol.md`
- 连同当前工作树中 blueprint/ 下已修改的 7 个文件一起提交（design.md / background.md / tasks.md / ADR-013 / ADR-016 / README.md / ADR README）
- commit message: `docs(blueprint): commit protocol.md v0 + three-layer model alignment`

**不做：** 不改 §6/§7 的 draft 标注；不新增段落；不调整现有措辞。

---

## 2. 最小 smoke 目标

验证 Convention 模式的最小可消费性：**Host A write → Host B read + continue**。

- Host A（当前 sopify-skills + Claude Code）：产出一个 light plan，走到至少一个 task done
- Host B（第二宿主，可以是 Cursor / Codex / 手动脚本模拟）：只读取 Host A 的产出，基于文件事实继续下一个 pending task
- **不要求** finalize、归档、blueprint 回写。这些留给下一步

---

## 3. 输入输出

### Host A 产出（write 侧）

| 文件 | 内容 |
|------|------|
| `.sopify-skills/project.md` | 已存在 ✅ |
| `.sopify-skills/blueprint/{background,design,tasks}.md` | 已存在 ✅ |
| `.sopify-skills/blueprint/protocol.md` | commit 后存在 ✅ |
| `.sopify-skills/plan/YYYYMMDD_smoke_test/plan.md` | light plan：title + scope + approach + 内联 tasks（≥2 tasks，1 done / 1 pending） |

### Host B 消费（read+continue 侧）

| 步骤 | 读取文件 | 成功证据 |
|------|---------|---------|
| 识别项目 | `project.md` | 正确输出项目名 |
| 理解上下文 | `blueprint/background.md` | 能复述 Sopify 定位（不要求精确措辞） |
| 定位活动 plan | `plan/YYYYMMDD_smoke_test/plan.md` | 正确识别 1 done + 1 pending |
| 继续执行 | 同上 | 在 plan.md 中把 pending task 标为 done 或 in_progress |

**Host B 最小证据：** plan.md 的 task 状态被正确更新（pending → in_progress 或 done），且更新内容与 plan scope 一致。

---

## 4. 验收标准

| # | 条件 | 判定 |
|---|------|------|
| 1 | `protocol.md` 在 `git status` 中不再是 `??` | pass/fail |
| 2 | Host B（非 Host A 的宿主/模型）成功读取 project.md + blueprint/ + plan/ | pass/fail |
| 3 | Host B 正确识别 pending task 并更新状态 | pass/fail |
| 4 | Host B 未依赖 `state/` 目录下任何文件（Convention 模式验证） | pass/fail |

4 条全 pass = smoke 通过。任一 fail = 记录失败原因，作为 protocol.md 下一轮修订输入。

---

## 5. 明确非目标

- **不做** 多宿主完整 review loop（§7 multi-host review 不在 smoke 范围）
- **不做** 第二套 runtime（Host B 只消费文件，不运行 Python runtime）
- **不做** full conformance 测试（只验证 Convention 模式最小下界）
- **不做** finalize / archive / blueprint 回写（smoke 到 "continue" 即止）
- **不做** acceptance gate 自动化（先手动验证，gate 雏形留给 smoke 通过后）
