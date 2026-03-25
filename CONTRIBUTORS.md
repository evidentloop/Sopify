# Contributors

This repository recognizes both human maintainers and AI-assisted collaboration.

GitHub's automatic contributor graph only reflects commits tied to GitHub accounts. AI assistants acknowledged here are repository collaborators, but they do not appear as first-class GitHub contributors unless GitHub account attribution exists.

## Human Maintainers

- Sanze Li

## AI Assistants

- Claude (Anthropic) — architecture discussion, code review, plan drafting, implementation assistance
- ChatGPT (OpenAI) — consultation, analysis, implementation assistance

## Commit-Level Attribution

This repository no longer appends standard AI `Co-authored-by` trailers by default.

AI participation is acknowledged here at the repository level so GitHub's contributor graph remains tied to human commit authors unless a maintainer explicitly adds co-author trailers by hand.

Set `SOPIFY_DISABLE_RELEASE_HOOK=1` only for maintainer/debug scenarios. It disables the entire `commit-msg` hook.
