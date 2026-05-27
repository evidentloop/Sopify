# 背景

## 来源

P0→P7 主航道全部完成，runtime slimming Phase 1 已归档。项目即将进入推广阶段，但当前仓库对外面存在三个结构问题：

1. **宿主级内容重复**：Claude EN/CN + Codex EN/CN = 4 套完整 skill tree，Claude EN ≈ Codex EN（仅 1 行 config path 差异），维护任何 skill 内容需改 4 处。
2. **Copilot 二等公民**：host registry 只注册 claude/codex（`installer/hosts/__init__.py:14`），Copilot 全走 special-case（20+ 处硬编码），只有 CN 无 EN，无 skill subtree。
3. **bundle 命名与 runtime 耦合**：`runtime_bundle.py` 打包 3 件套（runtime + sopify_contracts + canonical_writer），名字暗示 runtime 是核心；installer 仍耦合 `runtime.manifest`、`runtime.config`、`runtime.context_snapshot`。

## 触发场景

- 推广前最忌讳"目录很多、概念很多、安装路径不一致"
- 每次改 skill 内容要同步 4 套文件，高出错风险
- 新宿主接入需要大量 copy-paste 现有 host adapter + 手工复制 skill tree

## 影响范围

主要改动集中在：
- `skills/en/` + `skills/zh/`（新建，从 Codex EN/CN 移入——Codex 是 CONTRIBUTING.md 定义的唯一真源）
- `Claude/`、`Codex/`、`Copilot/` 目录（删除或降级为 generated）
- `installer/hosts/`（新增 copilot adapter，统一 registry）
- `installer/runtime_bundle.py` → `installer/sopify_bundle.py`（命名收口）
- header 模板（新建 `header.md.template` + `skills/hosts.yaml`）

## 约束

- 不降低现有安装体验——三宿主 × 双语言全部可用
- 不引入新的顶层目录层级（不搞 `hosts/` 嵌套）
- 不过度设计 Copilot surface 形态——先统一源和安装链，再定展平 vs 分文件
- 蓝图方向：统一、收缩、精简——每一步必须是减法
- runtime 退场不进本包
