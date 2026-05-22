# Getting Started with Sopify

This guide walks through adding Sopify to an existing repository and using it
with your preferred AI host.

## Overview

Sopify adds resumable, traceable AI workflows to any project. After setup:

- Work pauses automatically when facts are missing or a decision needs you
- Work resumes from where it stopped — even on a different AI host
- Plans, decisions, and reviews persist as reusable project assets

## Requirements

- Git repository (local or remote)
- Python 3.11+
- An AI host: Copilot, Codex, or Claude

## Quick Setup (One Command)

From your project root:

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

This creates:

| File | Purpose |
|------|---------|
| `.sopify-skills/sopify.json` | Workspace marker — tells the host that Sopify is active |
| `.gitignore` | Managed block — excludes transient state from version control |
| `.github/copilot-instructions.md` | Copilot entry — project-level instruction for Copilot |
| `.github/instructions/sopify.instructions.md` | Copilot detail — full Sopify rule set |

> **Skip Copilot files:** Pass `--no-copilot` with `--target copilot` if you only want workspace markers.

## Inspect-First Setup

Review the script before running:

```bash
curl -fsSL -o sopify-install.sh https://github.com/evidentloop/sopify/releases/latest/download/install.sh
less sopify-install.sh
bash sopify-install.sh --target copilot
```

Or clone and run the Python entry point directly:

```bash
git clone https://github.com/evidentloop/sopify.git /tmp/sopify
python3 /tmp/sopify/scripts/sopify_init.py init --workspace .
```

## Host-Specific Setup

### Codex / Claude

These hosts use a global prompt header. Install Sopify globally first, then
bootstrap individual projects:

```bash
# Global install (one-time)
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target codex:en-US

# Workspace bootstrap (per project)
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

After install, use `~go` in your AI host to start a managed workflow.

### Copilot

Copilot discovers instructions via project-level files. The install command
writes `.github/copilot-instructions.md` and
`.github/instructions/sopify.instructions.md` automatically.

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

Copilot reads project-level instruction files across its supported surfaces
(VS Code Chat, Copilot CLI, Cloud Agent, Code Review — as of May 2025).
Full trigger wiring (equivalent to Codex/Claude `~go`) is coming in a future
release.

## Verify Setup

After bootstrap, check the workspace marker:

```bash
cat .sopify-skills/sopify.json
```

Expected output:

```json
{
  "bundle_version": "2026-05-21.101226",
  "capabilities": ["preferences_preload", "runtime_gate"],
  "locator_mode": "global_first",
  "schema_version": "1",
  "workspace_kind": "external"
}
```

## Using Sopify

### Start a Task

Open your AI host in the project directory and describe what you want to do:

```text
Fix the typo on line 42 in src/utils.ts
```

For managed workflows with planning and review:

```text
~go Add user authentication with JWT
```

### Commands

> **Note:** These commands currently work in Codex and Claude. Copilot trigger
> wiring is coming in a future release — see [Host-Specific Setup](#copilot).

| Command | Description |
|---------|-------------|
| `~go` | Automatically route and run the full workflow |
| `~go plan` | Plan only — analyze and produce a plan without executing |
| `~go finalize` | Close out the current plan |

Most users only need `~go`.

### What Gets Created

As you work, Sopify creates project knowledge in `.sopify-skills/`:

```
.sopify-skills/
├── sopify.json       # workspace marker (from bootstrap)
├── project.md        # technical conventions (auto-created)
├── blueprint/        # design baseline
├── plan/             # active work packages
├── history/          # archived completed work
└── state/            # transient runtime state (git-ignored)
```

- `blueprint/`, `plan/`, `history/` are tracked by git — they are your project memory
- `state/` is transient and git-ignored — it holds runtime session data

## Updating

Re-run the install command to update the workspace marker and instruction files:

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

The workspace bootstrap path is idempotent — it preserves existing settings and only updates
what changed.

## Removing Sopify

```bash
rm -rf .sopify-skills/
rm -f .github/copilot-instructions.md
rm -rf .github/instructions/sopify.instructions.md
```

Then remove the `# BEGIN sopify-managed` / `# END sopify-managed` block from
your `.gitignore`.

## Further Reading

- [How Sopify Works](./how-sopify-works.en.md) — workflow, checkpoints, directory structure
- [External Repo Quickstart](../examples/external-repo-quickstart/README.md) — minimal step-by-step demo
- [Contributing](../CONTRIBUTING.md) — development and validation guidelines
