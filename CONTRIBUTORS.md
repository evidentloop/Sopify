# Contributors

This repository recognizes both human maintainers and AI-assisted collaboration.

GitHub's automatic contributor graph only reflects commits tied to GitHub accounts. AI assistants acknowledged here are repository collaborators, but they do not appear as first-class GitHub contributors unless GitHub account attribution exists.

## Human Maintainers

- Sanze Li

## AI Assistants

- Claude (Anthropic) — architecture discussion, code review, plan drafting, implementation assistance
- ChatGPT (OpenAI) — consultation, analysis, implementation assistance

## Commit-Level Attribution

This repository's `commit-msg` hook appends the following trailers by default:

```text
Co-authored-by: Claude <claude@anthropic.com>
Co-authored-by: ChatGPT <chatgpt@openai.com>
```

Set `SOPIFY_DISABLE_AI_ATTRIBUTION=1` for a single commit if you need to skip those trailers locally.

Set `SOPIFY_DISABLE_RELEASE_HOOK=1` only for maintainer/debug scenarios. It disables the entire `commit-msg` hook, which also skips the default AI attribution trailers.
