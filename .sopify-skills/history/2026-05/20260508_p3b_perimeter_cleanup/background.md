# 变更提案: P3b Perimeter Cleanup

## 需求背景

P3a 完成了 contract-aligned surface cleanup（legacy 删除、routing 收敛）。但 P3a 后仍然残留一批外围噪音：

1. **replay / workflow-learning 已死未葬**：蓝图已判定下线（design.md consult family 已移除、background.md 已标注），但 runtime 代码仍在写入 replay 事件、builtin_catalog 仍导出 workflow-learning、README 仍提及。这会持续污染 P4 系列的减重边界。

2. **Release gate 挂死**：`release-preflight.sh` 使用 `unittest discover`，在当前环境无法正常退出，导致 release 流程断裂。

3. **Tests 缺分类**：tests 全部平铺，无法区分 contract（必保）和 implementation-mirror（P4b 可砍）。P4b 减重没有分类基础就会变成逐个判断，效率极低。

4. **README 首屏偏重**：首屏暴露 plan lifecycle / blueprint / runtime gate / checkpoint taxonomy 等内部术语，与 P4c"首接触只暴露可恢复 + 拍板"的验收目标矛盾。不在 P3b 清掉，P4c 就没有干净起点。

## 与蓝图里程碑的关系

- **P3b**（tasks.md）：本方案包是 P3b 的完整执行包
- **前提**：P3a 已完成（legacy surface 已删除、routing 已收敛）
- **下游**：P4a（External Surface Freeze）依赖 P3b 清理后的干净外围面

## Plan Intake Checklist

1. **主命中里程碑**：P3b（Perimeter Cleanup）
2. **改动性质**：execution strategy / implementation wave — 不定义新 contract，只清理/下线已确认的旧面
3. **Machine truth 变更**：删除 replay route（已从 consult canonical family 移除）；删除 workflow-learning skill entry（builtin_catalog.py）。不新增 machine truth
4. **Legacy surface**：replay / workflow-learning 已在 design.md 标注 P3b sunset；无需替代 contract
5. **Core promotion rule / hard max 影响**：无
