#!/usr/bin/env bash
# Deploy Claude Code configuration from this repo to ~/.claude
#
# Usage:
#   bash deploy.sh [--dry-run] [--diff] [--help] [DIR ...]
#
# Positional:
#   DIR    Optional list of directories to sync (default: all).
#          Valid: agents, commands, rules, skills, recipes
#
# Options:
#   --dry-run    Preview without copying
#   --diff       Show file-level diff against existing target (implies --dry-run)
#   --help, -h   Show this help and exit
#
# Examples:
#   bash deploy.sh                        # sync everything
#   bash deploy.sh --dry-run              # preview full sync
#   bash deploy.sh recipes commands       # sync only these two
#   bash deploy.sh --diff                 # show diffs against current ~/.claude

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude"
DRY_RUN=false
SHOW_DIFF=false

ALL_DIRS=("agents" "commands" "rules" "skills" "recipes")
DIRS=()

show_help() {
  sed -n '2,/^$/p; /^$/q' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- Parse arguments -------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true; shift ;;
    --diff)     SHOW_DIFF=true; DRY_RUN=true; shift ;;
    --help|-h)  show_help ;;
    --*)        echo "Error: unknown option '$1'. Run with --help." >&2; exit 1 ;;
    *)          DIRS+=("$1"); shift ;;
  esac
done

# Default to all directories if none specified
if [[ ${#DIRS[@]} -eq 0 ]]; then
  DIRS=("${ALL_DIRS[@]}")
fi

# Validate every requested directory
for dir in "${DIRS[@]}"; do
  found=false
  for valid in "${ALL_DIRS[@]}"; do
    [[ "$dir" == "$valid" ]] && { found=true; break; }
  done
  if ! $found; then
    echo "Error: '$dir' is not a valid directory." >&2
    echo "Valid: ${ALL_DIRS[*]}" >&2
    exit 1
  fi
done

# --- Banner ---------------------------------------------------------------
if $DRY_RUN; then
  if $SHOW_DIFF; then
    echo "=== DIFF MODE — showing changes against $TARGET_DIR ==="
  else
    echo "=== DRY RUN — no files will be copied ==="
  fi
fi
echo "Source: $SCRIPT_DIR"
echo "Target: $TARGET_DIR"
echo "Dirs:   ${DIRS[*]}"
echo ""

# --- Sync logic -----------------------------------------------------------
sync_dir() {
  local name="$1"
  local src="$SCRIPT_DIR/$name"
  local dest="$TARGET_DIR/$name"

  if [[ ! -d "$src" ]]; then
    echo "  SKIP $name/ (not found in repo)"
    return
  fi

  local file_count
  file_count=$(find "$src" -type f ! -name "*.pyc" ! -path "*/__pycache__/*" | wc -l | tr -d ' ')

  if $SHOW_DIFF; then
    if [[ -d "$dest" ]]; then
      local diff_output
      diff_output=$(diff -rq "$dest" "$src" 2>/dev/null || true)
      if [[ -n "$diff_output" ]]; then
        echo "  DIFF $name/ ($file_count files in source):"
        echo "$diff_output" | sed 's/^/    /'
      else
        echo "  ✅ $name/ identical to source ($file_count files)"
      fi
    else
      echo "  NEW  $name/ ($file_count files — would be created)"
    fi
    return
  fi

  if $DRY_RUN; then
    echo "  WOULD sync $name/ ($file_count files)"
    return
  fi

  mkdir -p "$dest"
  # `$src/.` copies CONTENTS (including dotfiles) into dest — does not nest a subdirectory
  if ! cp -R "$src/." "$dest/"; then
    echo "  ❌ FAILED to sync $name/ — investigate above" >&2
    return 1
  fi
  echo "  ✅ $name/ synced ($file_count files)"
}

for dir in "${DIRS[@]}"; do
  sync_dir "$dir"
done

# --- CLAUDE.md template (only if user has none) ---------------------------
TEMPLATE="$SCRIPT_DIR/CLAUDE.TEMPLATE.md"
if [[ -f "$TEMPLATE" ]]; then
  if [[ -f "$TARGET_DIR/CLAUDE.md" ]]; then
    echo "  SKIP CLAUDE.md (already exists in $TARGET_DIR/)"
  elif $DRY_RUN; then
    echo "  WOULD copy CLAUDE.TEMPLATE.md -> $TARGET_DIR/CLAUDE.md"
  else
    cp "$TEMPLATE" "$TARGET_DIR/CLAUDE.md"
    echo "  ✅ CLAUDE.md created from template"
  fi
fi

# --- Footer ---------------------------------------------------------------
echo ""
if $DRY_RUN; then
  echo "Done (no changes applied). Re-run without --dry-run to deploy."
else
  echo "Done. Restart Claude Code to pick up changes."
fi
