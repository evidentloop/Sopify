#!/usr/bin/env bash
set -euo pipefail

SOURCE_CHANNEL="dev"
SOURCE_REF="main"

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [init] [--workspace <path>] [--no-copilot]

Bootstrap remains available as a compatibility alias for:
  install.sh --target copilot

This initializes a Sopify workspace in your project by creating the minimal
activation markers and, by default, Copilot instruction files.

Options:
  --workspace <path>     Target project directory (default: current directory).
  --no-copilot           Skip Copilot instruction file distribution.
  --ref <tag-or-branch>  Advanced: override the source ref.
  --language <lang>      Output language: en-US or zh-CN.
  -h, --help             Show this help.
EOF
}

FORWARDED_ARGS=()
HAS_INIT=false
HAS_WORKSPACE=false
HAS_REF=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    init)
      HAS_INIT=true
      shift
      ;;
    --workspace|--workspace=*|-w)
      HAS_WORKSPACE=true
      FORWARDED_ARGS+=("$1")
      if [[ "$1" != --workspace=* && "$1" != -w ]]; then
        shift
        FORWARDED_ARGS+=("$1")
      elif [[ "$1" == -w ]]; then
        shift
        FORWARDED_ARGS+=("$1")
      fi
      shift
      ;;
    --ref|--ref=*)
      HAS_REF=true
      FORWARDED_ARGS+=("$1")
      if [[ "$1" == "--ref" ]]; then
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          echo "bootstrap.sh: --ref requires a value." >&2
          exit 1
        fi
        shift
        FORWARDED_ARGS+=("$1")
      fi
      shift
      ;;
    *)
      FORWARDED_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$HAS_INIT" != true ]]; then
  :
fi
if [[ "$HAS_WORKSPACE" != true ]]; then
  FORWARDED_ARGS+=("--workspace" ".")
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$HAS_REF" != true ]]; then
  FORWARDED_ARGS=(--ref "$SOURCE_REF" "${FORWARDED_ARGS[@]}")
fi
exec bash "$ROOT_DIR/install.sh" --target copilot "${FORWARDED_ARGS[@]}"
