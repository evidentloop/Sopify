# External Repo Quickstart

Add Sopify to any existing repository so your AI host can resume work, track
decisions, and persist project knowledge.

## Prerequisites

- Git repository (local or remote)
- Python 3.11+
- An AI host: **Copilot**, **Codex**, or **Claude**

## Step 1 — Bootstrap

Run from your project root:

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target copilot
```

Or clone and run locally:

```bash
git clone https://github.com/evidentloop/sopify.git /tmp/sopify
python3 /tmp/sopify/scripts/sopify_init.py init --workspace .
```

Expected output:

```
✓ Sopify workspace ready
  path:    /path/to/your-project
  version: 2026-05-21.101226

Next steps:
  Open an AI host (Copilot / Codex / Claude) in this directory to start using Sopify.
```

## Step 2 — Verify

Check what was created:

```bash
cat .sopify-skills/sopify.json
```

```json
{
  "bundle_version": "2026-05-21.101226",
  "capabilities": [
    "preferences_preload",
    "runtime_gate"
  ],
  "locator_mode": "global_first",
  "schema_version": "1",
  "workspace_kind": "external"
}
```

The bootstrap also updated:

| File | Purpose |
|------|---------|
| `.sopify-skills/sopify.json` | Workspace marker — version anchor + capability declaration |
| `.gitignore` | Managed ignore block — excludes transient state from version control |
| `.github/copilot-instructions.md` | Copilot instruction entry — tells Copilot about Sopify conventions |
| `.github/instructions/sopify.instructions.md` | Detailed Copilot instructions — full rule set |

## Step 3 — Start Using

Open the project in your AI host and begin working. Sopify uses project
conventions to make AI decisions visible and resumable.

For **Codex** or **Claude** users: if you haven't installed Sopify globally yet,
run the full installer first:

```bash
curl -fsSL https://github.com/evidentloop/sopify/releases/latest/download/install.sh | bash -s -- --target codex:en-US
```

Then use `~go` to start a managed workflow.

For **Copilot** users: the workspace is ready. Full trigger wiring is coming in
a future release. `bootstrap.sh` still works as a compatibility alias, but the
recommended entrypoint is now `install.sh --target copilot`.

## What Happens Next

Once Sopify is active in your project:

1. **Start** — ask your AI host to begin or continue a task
2. **Pause** — Sopify stops when facts are missing or a decision needs you
3. **Resume** — work picks up from project state, even on a different host

Project knowledge accumulates in `.sopify-skills/`:

```
.sopify-skills/
├── sopify.json       # workspace marker (created by bootstrap)
├── project.md        # technical conventions (created on first use)
├── blueprint/        # design baseline (created when needed)
├── plan/             # active plans
├── history/          # archived plans
└── state/            # transient runtime state (git-ignored)
```

## Cleanup

To remove Sopify from your project:

```bash
rm -rf .sopify-skills/
rm -f .github/copilot-instructions.md
rm -rf .github/instructions/sopify.instructions.md
# Then remove the sopify-managed block from .gitignore
```

## Further Reading

- [How Sopify Works](../../docs/how-sopify-works.en.md)
- [Main README](../../README.md)
- [Contributing](../../CONTRIBUTING.md)
