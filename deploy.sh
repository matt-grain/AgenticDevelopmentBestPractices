#!/usr/bin/env bash
# Deploy Claude Code configuration from this repo to ~/.claude
# Usage: bash deploy.sh [--dry-run]
#
# This script copies agents, commands, rules, and skills from the repo
# to the user's ~/.claude directory, which is where Claude Code reads them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN — no files will be copied ==="
fi

# Directories to sync (source relative to repo root)
DIRS=("agents" "commands" "rules")

copy_dir() {
  local src="$SCRIPT_DIR/$1"
  local dest="$TARGET_DIR/$1"

  if [[ ! -d "$src" ]]; then
    echo "  SKIP $1/ (not found in repo)"
    return
  fi

  if $DRY_RUN; then
    echo "  WOULD sync $src/ -> $dest/"
    return
  fi

  mkdir -p "$dest"
  # Use cp -r to copy contents, overwriting existing files
  cp -r "$src/"* "$dest/" 2>/dev/null || true
  echo "  ✅ $1/ synced"
}

echo "Deploying from: $SCRIPT_DIR"
echo "Deploying to:   $TARGET_DIR"
echo ""

for dir in "${DIRS[@]}"; do
  copy_dir "$dir"
done

# Copy CLAUDE.md template if it exists and user doesn't have one
if [[ -f "$SCRIPT_DIR/CLAUDE.TEMPLATE.md" && ! -f "$TARGET_DIR/CLAUDE.md" ]]; then
  if $DRY_RUN; then
    echo "  WOULD copy CLAUDE.TEMPLATE.md -> ~/.claude/CLAUDE.md"
  else
    cp "$SCRIPT_DIR/CLAUDE.TEMPLATE.md" "$TARGET_DIR/CLAUDE.md"
    echo "  ✅ CLAUDE.md created from template"
  fi
else
  echo "  SKIP CLAUDE.md (already exists or no template)"
fi

echo ""
if $DRY_RUN; then
  echo "Done (dry run). Re-run without --dry-run to apply."
else
  echo "Done. Restart Claude Code to pick up changes."
fi
