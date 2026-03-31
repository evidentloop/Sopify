# Evidence Archive Notice

## Background

To reduce repository size and simplify history paths, the local evidence bundle under `evidence/pilot_round1/**` was externalized on `2026-03-31`.

## What Changed

- Removed local directory: `evidence/pilot_round1/**`
- Replaced in-plan evidence references with `external_archive://pilot_round1/...`

## Retrieval Contract

- `external_archive://` is an external archive locator, not a local filesystem path.
- If audit replay is needed, request the corresponding artifact from maintainers using the full `external_archive://...` locator in the review docs.

## Compatibility Note

This change only affects historical evidence storage paths. Runtime `history/index.md` and plan lifecycle behavior are unchanged.
