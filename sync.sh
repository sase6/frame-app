#!/usr/bin/env bash
#
# Force-sync this repo's working tree to match origin/main exactly.
# WARNING: this DISCARDS all local changes — uncommitted edits, staged
# changes, local commits, and untracked files are wiped. Use only when you
# want the folder to be a pristine copy of the latest remote main.
#
# This script excludes itself from cleanup so it survives the sync.
#
set -euo pipefail

BRANCH="main"

# Resolve the repo root from the script's own location, so it works no
# matter where it's invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$(basename "${BASH_SOURCE[0]}")"
cd "$SCRIPT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Refusing to run: $SCRIPT_DIR is not a git repo." >&2
  exit 1
fi

echo "Fetching origin..."
git fetch origin --prune

echo "Resetting $BRANCH to origin/$BRANCH (discarding local commits & edits)..."
git checkout -B "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"

echo "Removing untracked files & directories (keeping $SELF)..."
git clean -fd -e "$SELF"

# Ensure local data files exist. These are gitignored, so the clean step
# above leaves them untouched and they persist across syncs — we only
# create them the first time, or if they were manually removed.
if [[ ! -d album ]]; then
  echo "Creating album/ folder..."
  mkdir -p album
fi
if [[ ! -f settings.json ]]; then
  echo "Creating settings.json..."
  echo '{}' > settings.json
fi

echo "Done. Now at: $(git rev-parse --short HEAD) $(git log -1 --format=%s)"
