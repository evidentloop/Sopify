#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="evidentloop"
REPO_NAME="sopify"
ASSET_NAME="install.sh"
SOURCE_CHANNEL="dev"
SOURCE_REF="main"

usage() {
  cat <<'EOF'
Usage: install.sh [--target <host[:lang]>] [--ref <tag-or-branch>]

Install Sopify for a supported AI host.

Use `--target copilot` to bootstrap the current workspace and write Copilot
instruction files. For Codex / Claude, this installs the host prompt and
Sopify runtime only; project files are initialized later when you run `~go`
inside a workspace.

Options:
  --target <host[:lang]> Host and language to install, for example codex:zh-CN
                         or copilot.
  --workspace <path>     For copilot: target project directory (defaults to
                         current directory). For other hosts: advanced prewarm.
  --language <lang>      Copilot only: bootstrap output language (en-US/zh-CN).
  --no-copilot           Copilot only: skip Copilot instruction file
                         distribution and only write workspace markers.
  --verbose              Show full diagnostic install details.
  --ref <tag-or-branch>  Advanced: override the source ref.
  -h, --help             Show this help.
EOF
}

fail() {
  local phase="$1"
  local reason_code="$2"
  local detail="$3"
  local next_step="$4"
  {
    echo "Sopify install failed: $detail"
    echo
    echo "Fix:"
    echo "  $next_step"
    echo
    echo "Diagnostics:"
    echo "  reason_code: $reason_code"
    echo "  phase: $phase"
  } >&2
  exit 1
}

log_step() {
  echo "Sopify: $1" >&2
}

require_command() {
  local command_name="$1"
  local reason_code="$2"
  local next_step="$3"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "preflight" "$reason_code" "Missing required command: $command_name" "$next_step"
  fi
}

FORWARDED_ARGS=()
REF_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --ref)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        fail "input" "MISSING_REF_VALUE" '`--ref` requires a value.' "Pass --ref <tag-or-branch>, or omit the flag."
      fi
      REF_OVERRIDE="$2"
      FORWARDED_ARGS+=("$1" "$2")
      shift 2
      ;;
    --ref=*)
      REF_OVERRIDE="${1#*=}"
      if [[ -z "$REF_OVERRIDE" ]]; then
        fail "input" "MISSING_REF_VALUE" '`--ref` requires a value.' "Pass --ref <tag-or-branch>, or omit the flag."
      fi
      FORWARDED_ARGS+=("$1")
      shift
      ;;
    *)
      FORWARDED_ARGS+=("$1")
      shift
      ;;
  esac
done

RESOLVED_REF="${REF_OVERRIDE:-$SOURCE_REF}"
if [[ -z "$RESOLVED_REF" ]]; then
  fail "input" "MISSING_SOURCE_REF" "No source ref was resolved for the installer." "Retry with --ref <tag-or-branch>, or inspect the release asset rendering."
fi

log_step "Checking requirements..."
require_command "curl" "MISSING_CURL" "Install curl, or use the inspect-first flow to download the release asset manually."
require_command "tar" "MISSING_TAR" "Install tar, or use a machine with basic archive support."
require_command "python3" "MISSING_PYTHON3" "Install Python 3, then rerun the installer."

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sopify-install.XXXXXX")"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ARCHIVE_URL="https://codeload.github.com/${REPO_OWNER}/${REPO_NAME}/tar.gz/${RESOLVED_REF}"
ARCHIVE_PATH="$TMP_DIR/source.tar.gz"

log_step "Downloading Sopify source (${RESOLVED_REF})..."
if ! curl -fsSL "$ARCHIVE_URL" -o "$ARCHIVE_PATH"; then
  fail "download" "SOURCE_FETCH_FAILED" "Failed to download source archive: $ARCHIVE_URL" "Check network access, verify the ref exists, or use the inspect-first path."
fi

log_step "Unpacking installer..."
if ! tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"; then
  fail "unpack" "SOURCE_EXTRACT_FAILED" "Failed to extract source archive: $ARCHIVE_PATH" "Retry the installer or inspect the downloaded archive locally."
fi

SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
  fail "unpack" "SOURCE_ROOT_MISSING" "The extracted source archive did not contain a repository root directory." "Retry the installer or inspect the downloaded archive locally."
fi

ENTRYPOINT="$SOURCE_DIR/scripts/install_sopify.py"
if [[ ! -f "$ENTRYPOINT" ]]; then
  fail "unpack" "INSTALL_ENTRYPOINT_MISSING" "Missing install entrypoint inside source archive: $ENTRYPOINT" "Retry the installer or inspect the downloaded archive locally."
fi

log_step "Running installer..."
python3 "$ENTRYPOINT" \
  --source-channel "$SOURCE_CHANNEL" \
  --source-resolved-ref "$RESOLVED_REF" \
  --source-asset-name "$ASSET_NAME" \
  "${FORWARDED_ARGS[@]}"
exit $?
