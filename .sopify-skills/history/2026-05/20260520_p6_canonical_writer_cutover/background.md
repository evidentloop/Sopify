# 变更提案: P6 Canonical Writer Cutover / Runtime Retirement

## 需求背景

P5 完成了全量 contract surface 裁定，核心结论：

- **candidate-kernel = StateStore ~210 LOC**（P5 收口口径：get/set/clear 方法族 + 不变量校验）。StateStore 类整体 ~276 LOC（runtime/state.py:40-315），含 IO 辅助和内部 provenance 逻辑。P6 提取范围以 candidate-kernel ~210 LOC 为主体，辅助逻辑按依赖随迁
- builder 逻辑（build_runtime_handoff, build_decision_state 等 ~470 LOC）深度耦合 engine，不可迁移
- 当前无线上用户，零迁移负担，可直接面向目标态

P6 = 把 P5 识别的形状变成现实：**提取 canonical writer，定义 writer_input 契约，让新宿主能直接适配写入层**。runtime 降为 legacy reference implementation。

### 前置里程碑链

P0 → … → P4d → P5 → **P6**

### P5 提供的关键输入

| 输入 | 内容 |
|------|------|
| candidate-kernel | StateStore get/set/clear ~210 LOC（P5 口径）。类整体 ~276 LOC 含 IO/provenance 辅助 |
| writer 依赖 | 4 内部模块：models(cross-tier), state_invariants, handoff(read_only), checkpoint_request(仅 2 符号) |
| writer 消费者 | ~15 文件：engine, gate, develop_callback, bridges, installer/inspection 等 |
| 内部辅助 | iso_now, normalize_session_id, _stamp_provenance, _validate_state_resume_contract, _read_json/_write_json |
| Invariants | phase validation, resolution_id validation, paired truth write, session_id normalization |
| 循环导入 | state.py → handoff.py 单向（非循环），但 iso_now 5 处重复因其他链路导致 |
| Blueprint 方向 | 三层分离：payload_capable(消费) / canonical writer(生产) / runtime(legacy) |

### 核心验证目标

1. StateStore + 必要辅助可独立于 engine 运行（物理解耦）
2. writer_input 契约足够明确，新宿主不需要理解 engine 内部即可生产 canonical state
3. runtime 消费者可无感切换到新 writer 模块（行为不变，721+ tests 全过）
