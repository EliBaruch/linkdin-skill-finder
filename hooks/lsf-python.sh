#!/usr/bin/env bash
# Locate a Python interpreter and run the given script, passing stdin through.
# Mirrors the pattern used by the official security-guidance plugin.
# If no Python is found, exit silently so the hook never blocks the session.

SCRIPT="$1"
shift 2>/dev/null || true

for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1; then
    exec "$py" "$SCRIPT" "$@"
  fi
done

# No Python available — do nothing, succeed quietly.
exit 0
