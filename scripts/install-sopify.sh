#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run the Sopify installer." >&2
  exit 1
fi

exec python3 "$ROOT_DIR/scripts/install_sopify.py" \
  --source-channel repo-local \
  --source-resolved-ref working-tree \
  --source-asset-name scripts/install-sopify.sh \
  "$@"
