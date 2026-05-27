#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: scripts/sync-skills.sh

Render host distribution files from skills/ source of truth:
  - skills/zh/header.md.template -> Codex/Skills/CN/AGENTS.md (with codex vars)
  - skills/zh/header.md.template -> Claude/Skills/CN/CLAUDE.md (with claude vars)
  - skills/en/header.md.template -> Codex/Skills/EN/AGENTS.md (with codex vars)
  - skills/en/header.md.template -> Claude/Skills/EN/CLAUDE.md (with claude vars)
  - skills/{zh,en}/skills/sopify/* -> {Codex,Claude}/Skills/{CN,EN}/skills/sopify/*
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

RENDER_SCRIPT="$ROOT_DIR/scripts/render-host-skills.py"
HOSTS_FILE="$ROOT_DIR/skills/hosts.yaml"

if [[ ! -f "$RENDER_SCRIPT" ]]; then
  echo "Missing render script: $RENDER_SCRIPT" >&2
  exit 1
fi
if [[ ! -f "$HOSTS_FILE" ]]; then
  echo "Missing hosts file: $HOSTS_FILE" >&2
  exit 1
fi

# Maps: source lang -> dist lang dir, host_id -> dist top dir + header filename
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

sync_host_lang() {
  local host_id="$1"
  local src_lang="$2"
  local dist_lang
  local host_dir
  local header_file
  local skills_source
  local dist_dir

  dist_lang="$(dist_lang_dir "$src_lang")"
  host_dir="$(host_top_dir "$host_id")"
  header_file="$(host_header_file "$host_id")"
  skills_source="$ROOT_DIR/skills/$src_lang/skills/sopify"
  dist_dir="$ROOT_DIR/$host_dir/Skills/$dist_lang"

  if [[ ! -d "$skills_source" ]]; then
    echo "Missing source skills: $skills_source" >&2
    exit 1
  fi

  mkdir -p "$dist_dir/skills/sopify"

  python3 "$RENDER_SCRIPT" \
    --hosts-file "$HOSTS_FILE" \
    --skills-root "$ROOT_DIR/skills" \
    --lang "$src_lang" \
    --host "$host_id" \
    --output "$dist_dir/$header_file"

  rsync -a --delete --exclude .DS_Store --exclude Thumbs.db \
    "$skills_source/" "$dist_dir/skills/sopify/"
}

for host_id in codex claude; do
  for src_lang in zh en; do
    sync_host_lang "$host_id" "$src_lang"
  done
done

echo "Rendered skills/ -> Codex + Claude distribution for CN and EN."
