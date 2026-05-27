#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sopify-sync-check.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

usage() {
  cat <<'EOF'
Usage: scripts/check-skills-sync.sh

Check whether host distribution files (Codex/*, Claude/*) match the
rendered output from skills/ source of truth.
On mismatch, run:
  bash scripts/sync-skills.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

RENDER_SCRIPT="$ROOT_DIR/scripts/render-host-skills.py"
HOSTS_FILE="$ROOT_DIR/skills/hosts.yaml"
status=0

dist_lang_dir() {
  case "$1" in
    zh) echo "CN" ;; en) echo "EN" ;;
    *) echo "Unknown source lang: $1" >&2; exit 1 ;;
  esac
}
host_top_dir() {
  case "$1" in
    codex) echo "Codex" ;; claude) echo "Claude" ;;
    *) echo "Unknown host: $1" >&2; exit 1 ;;
  esac
}
host_header_file() {
  case "$1" in
    codex) echo "AGENTS.md" ;; claude) echo "CLAUDE.md" ;;
    *) echo "Unknown host: $1" >&2; exit 1 ;;
  esac
}

check_host_lang() {
  local host_id="$1"
  local src_lang="$2"
  local dist_lang
  local host_dir
  local header_file
  local skills_source
  local dist_dir
  local label
  local diff_file
  local expected_header

  dist_lang="$(dist_lang_dir "$src_lang")"
  host_dir="$(host_top_dir "$host_id")"
  header_file="$(host_header_file "$host_id")"
  skills_source="$ROOT_DIR/skills/$src_lang/skills/sopify"
  dist_dir="$ROOT_DIR/$host_dir/Skills/$dist_lang"
  label="$host_id:$src_lang ($dist_lang)"
  diff_file="$TMP_DIR/${host_id}_${src_lang}.diff"
  expected_header="$TMP_DIR/${host_id}_${src_lang}.expected.md"

  python3 "$RENDER_SCRIPT" \
    --hosts-file "$HOSTS_FILE" \
    --skills-root "$ROOT_DIR/skills" \
    --lang "$src_lang" \
    --host "$host_id" \
    --output "$expected_header"

  if ! diff -u "$expected_header" "$dist_dir/$header_file" >"$diff_file" 2>&1; then
    echo "[$label] Header mismatch: $host_dir/Skills/$dist_lang/$header_file"
    head -n 40 "$diff_file"
    status=1
  fi

  if ! diff -ru -x .DS_Store -x Thumbs.db "$skills_source" "$dist_dir/skills/sopify" >"$diff_file" 2>&1; then
    echo "[$label] Skill directory mismatch"
    head -n 60 "$diff_file"
    status=1
  fi
}

for host_id in codex claude; do
  for src_lang in zh en; do
    check_host_lang "$host_id" "$src_lang"
  done
done

if [[ "$status" -ne 0 ]]; then
  echo
  echo "Sync check failed. Run: bash scripts/sync-skills.sh"
  exit 1
fi

echo "Sync check passed: all distribution files match skills/ source."
