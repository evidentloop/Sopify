---
name: design
description: Design phase entry. Aggregates plan-level selection, task breakdown, and package output rules; loads references/assets/scripts on demand.
---

# Design (Entry)

> Core philosophy: A plan's value lies in the clarity of its trade-offs, not in its coverage.

## When to activate

- Entering the design phase (`workflow` / `plan_only` / `light_iterate`).
- Need to convert requirements into a plan package and task list.

## Execution skeleton

1. Load `references/design-rules.md`.
2. Decide `light/standard/full` from explicit change signals.
3. Generate the plan files from the matching templates in `assets/`.
4. Produce the task list and validate task granularity.
5. Add the scoring block to the formal plan package and render the scored summary with `assets/output-summary.md`.

## Resource navigation

- Long rules: `references/design-rules.md`
- Shared writing standards: `../references/shared-writing-dna.md` (apply to all output)
- Output contract: `../references/output-contract.md` (required sections, conditional enhancement, self-check)
- Templates: `assets/*.md`
- Deterministic level selector: `scripts/select_plan_level.py`

## Deterministic logic first

Use the selector when `plan.level=auto` must be auditable:

```bash
python3 skills/en/skills/sopify/design/scripts/select_plan_level.py \
  --file-count 6 \
  --new-feature \
  --cross-module
```

The script returns JSON with the suggested level and explicit reasons.

## Boundaries

- This skill does not execute code changes directly; hand off to `develop`.
- This skill does not replace runtime routing; it defines the plan structure and task contract only.
