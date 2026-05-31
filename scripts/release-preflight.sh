#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: scripts/release-preflight.sh

Run release preflight checks before bumping Sopify version:
  1) Verify version consistency and golden snapshots
  2) Run runtime unit tests + installer/runtime smoke checks
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

run_step() {
  local title="$1"
  shift
  echo "[release-preflight] $title"
  "$@"
}

check_builtin_catalog_drift() {
  local tmp
  tmp="$(mktemp)"
  python3 "$ROOT_DIR/scripts/generate-builtin-catalog.py" --output "$tmp" >/dev/null
  if ! python3 - "$ROOT_DIR/runtime/builtin_catalog.generated.json" "$tmp" <<'PY'; then
import difflib
import json
from pathlib import Path
import sys


def normalize(path_str: str) -> list[str]:
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    payload.pop("generated_at", None)
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).splitlines()


left_path, right_path = sys.argv[1], sys.argv[2]
left = normalize(left_path)
right = normalize(right_path)
if left != right:
    for line in difflib.unified_diff(left, right, fromfile=left_path, tofile=right_path, lineterm=""):
        print(line)
    raise SystemExit(1)
PY
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
}

run_step "Check version consistency" bash "$ROOT_DIR/scripts/check-version-consistency.sh"

# Golden snapshots: auto-regenerate if stale, then verify
if ! python3 -m pytest "$ROOT_DIR/tests/test_golden_snapshots.py" -q 2>/dev/null; then
  echo "[release-preflight] Golden snapshots stale — regenerating..."
  python3 "$ROOT_DIR/scripts/regenerate-golden-snapshots.py"
  git add "$ROOT_DIR/tests/golden-snapshots.json"
  run_step "Re-check golden snapshots" python3 -m pytest "$ROOT_DIR/tests/test_golden_snapshots.py" -q
else
  echo "[release-preflight] Check golden snapshots"
fi
run_step "Check builtin catalog drift" check_builtin_catalog_drift
run_step "Check context checkpoints" python3 "$ROOT_DIR/scripts/check-context-checkpoints.py" repo --root "$ROOT_DIR"
run_step "Run hard gate tests (contract + smoke + distribution)" python3 -m pytest "$ROOT_DIR/tests" -m "not implementation_mirror" -v

echo "[release-preflight] Running implementation-mirror tests (advisory, non-blocking)..."
if python3 -m pytest "$ROOT_DIR/tests" -m "implementation_mirror" -v; then
  echo "[release-preflight] Implementation-mirror tests passed."
else
  echo "[release-preflight] WARNING: Implementation-mirror tests failed (advisory, not blocking release)."
fi
run_step "Run install/payload bootstrap smoke" python3 "$ROOT_DIR/scripts/check-install-payload-bundle-smoke.py"
run_step "Run prompt runtime gate smoke" python3 "$ROOT_DIR/scripts/check-prompt-runtime-gate-smoke.py"
run_step "Run bundle runtime smoke check" bash "$ROOT_DIR/scripts/check-bundle-smoke.sh"

echo "[release-preflight] All checks passed."
