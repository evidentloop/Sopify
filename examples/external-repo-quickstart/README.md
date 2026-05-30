# External Repo Quickstart

Add Sopify to any existing repository so your AI host can resume work, track
decisions, and persist project knowledge.

## Prerequisites

- Git repository (local or remote)
- Python 3.11+
- An AI host: **Copilot**, **Codex**, or **Claude**

## Step 1 — Install

Run from your project root:

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

Replace `copilot` with `codex:en-US` or `claude:en-US` for other hosts.

Expected output (Copilot):

```
Sopify installed successfully.

Installed:
  Host: Copilot (copilot:en-US)
  Language: English
  Host prompt: installed
  Version: 2026-05-30.193318
  File: /path/to/your-project/.github/copilot-instructions.md

Next:
  1. Open Copilot in your project directory.
  2. Sopify instructions are loaded automatically — start your task.
```

Expected output (Codex / Claude):

```
Sopify installed successfully.

Installed:
  Host: Codex (codex:en-US)
  Language: English
  Host prompt: updated
  Runtime: ~/.codex/sopify
  Version: 2026-05-30.193318
  Runtime action: updated

Project:
  Prewarmed: /path/to/your-project
  Bundle: /path/to/your-project/.sopify-runtime

Next:
  1. Reopen Codex in that project.
  2. Type: ~go

Diagnostics:
  Runtime smoke check passed.
  Run again with `--verbose` for full install details.
```

## Step 2 — Verify

**Copilot** creates a single instruction file:

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | Sopify instructions — loaded automatically by Copilot |

**Codex / Claude** also create a workspace marker:

```bash
cat .sopify-skills/sopify.json
```

```json
{
  "bundle_version": "2026-05-30.193318",
  "capabilities": [
    "runtime_gate"
  ],
  "locator_mode": "global_first",
  "schema_version": "1",
  "workspace_kind": "external"
}
```

## Step 3 — Start Using

Open the project in your AI host and begin working.

- **Copilot**: instructions are loaded automatically — start your task directly.
- **Codex / Claude**: type `~go` to start a managed workflow.

## What Happens Next

Once Sopify is active in your project:

1. **Start** — ask your AI host to begin or continue a task
2. **Pause** — Sopify stops when facts are missing or a decision needs you
3. **Resume** — work picks up from project state, even on a different host

Project knowledge accumulates in `.sopify-skills/`:

```
.sopify-skills/
├── sopify.json       # workspace marker (Codex/Claude only)
├── project.md        # technical conventions (created on first use)
├── blueprint/        # design baseline (created when needed)
├── plan/             # active plans
├── history/          # archived plans
└── state/            # transient runtime state (git-ignored)
```

## Cleanup

To remove Sopify from your project:

```bash
rm -rf .sopify-skills/ .sopify-runtime/
rm -f .github/copilot-instructions.md
# Then remove the sopify-managed block from .gitignore
```

## Further Reading

- [How Sopify Works](../../docs/how-sopify-works.en.md)
- [Main README](../../README.md)
- [Contributing](../../CONTRIBUTING.md)
