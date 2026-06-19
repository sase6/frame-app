#!/usr/bin/env bash
#
# Boot entry point for the frame: sync to the latest origin/main, then launch
# the app. Intended to be what runs on the Pi (by hand, or from a systemd
# service / cron @reboot).
#
# The whole body is wrapped in { ... } so bash reads the entire script into
# memory before executing it. sync.sh below force-resets the repo and can
# overwrite this very file via git; reading it up front avoids corrupting the
# running script mid-execution.
#
{
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Syncing with origin/main..."
if ./sync.sh; then
  echo "Sync complete."
else
  # Don't strand the frame if the network is down - boot with whatever code
  # is already on disk.
  echo "Sync failed (offline?); starting with the existing code." >&2
fi

echo "Starting app..."
exec python3 app.py

exit 0
}
