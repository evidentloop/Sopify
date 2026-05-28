# Sopify Output Contract

All stages (analyze / design / develop / consult) must follow this contract for final replies. Each section governs one output decision dimension.

## 1. Output Path Responsibilities

- **Gate summary**: Routing status from the gate/routing phase. Contains phase title, status line, Context, Changes, Next. Does not contain verification tables, review conclusions, or other skill-level content.
- **Host completion reply**: The final summary after skill execution. Must follow the corresponding template, including required sections and enhancements when triggered.
- Gate summary ≠ final reply. The gate tells the host what to do; the host outputs results per template after completing the work.

## 2. Required Sections

| Output Type | Required Sections | Required Tables | Status Symbol |
|------------|------------------|----------------|---------------|
| develop/success | Review conclusion, verification summary, Changes, Next | Verification table | ✓ only when all passed |
| develop/partial | Incomplete items, verification summary, Changes, Next | Incomplete table + verification table | Must use ! |
| develop/quick-fix | Verification summary, Changes, Next | Simplified verification table | ✓ only when all passed |
| analyze/success | Assumptions, identified gaps, next-step rationale, Changes, Next | — | — |
| analyze/question | Question list, Next | — | Must use ? |
| design/summary | Score lines, Changes, Next | — | — |
| consult | Changes, Next | — (adaptive) | — |

Table column rule: only show columns that carry meaningful information for the current scenario. When all `reason_code=—` in a success scenario, that column may be omitted. Column omission only affects final display, not internal verification logic.

## 3. Conditional Enhancement & Format Selection

Do not force structure on every scenario. Decide whether and how to enhance based on information shape and trigger conditions:

| Trigger Condition | Recommended Format | Typical Scenarios |
|------------------|-------------------|-------------------|
| Multi-item comparison/tradeoff (>2 options) | Table | Solution tradeoffs, risk comparison, host capability comparison |
| Flow/invocation/lifecycle | Numbered sequence | SDK flows, gate → route → handoff |
| File/component/module composition | Tree structure | Component breakdown, module structure, plan file organization |
| Score dimensions need visibility | Score table | analyze scoring |
| Simple Q&A/status confirmation | Keep concise | Single question answers, status confirmations |

Constraint: use at most one primary structure per reply; avoid stacking table + tree + flow.

**DO:**
- Use a comparison table when multi-option tradeoffs are present — make differences visible at a glance
- Simplify verification summary on success when all passed — omit columns with no information
- Keep plain text when information shape does not match any structure

**DON'T:**
- Multi-option tradeoffs without comparison structure = missed enhancement
- Forcing tables on simple Q&A = over-enhancement
- Mixing two or more primary structures in one reply = cognitive overload

## 4. Pre-output Self-check

Before outputting the final reply, verify:

1. Required sections present: check §2 for the current output type.
2. Status symbol correct: `✓` only when all `result=passed` and `reason_code=—`; otherwise `!`.
3. Footer complete: `Changes:` + `Next:` must be present.
4. Conditional enhancement applied: if the reply meets a §3 trigger condition, use the corresponding structured format.
