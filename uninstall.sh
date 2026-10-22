#!/usr/bin/env bash
# SDD Global Uninstaller — POSIX / Git Bash shim. All logic lives in uninstall.py; this shim only
# finds Python >= 3.9 (scripts/find-python.sh) and runs it with the same arguments.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=""      # set by sdd_find_python
PY_ARGS=""
# shellcheck disable=SC1091  # sourced helper; lint it directly (shellcheck scripts/find-python.sh)
. "${SCRIPT_DIR}/scripts/find-python.sh"

if ! sdd_find_python; then
  echo "[err]   Python 3.9 or later was not found (tried: python3, py -3, python)." >&2
  exit 1
fi

# shellcheck disable=SC2086  # PY_ARGS is empty or the single flag -3
exec "$PY" $PY_ARGS "${SCRIPT_DIR}/uninstall.py" "$@"
