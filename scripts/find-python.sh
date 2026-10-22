# shellcheck shell=sh
# scripts/find-python.sh — the ONE interpreter-resolution policy for SDD shell entrypoints.
#
# Sourced (never executed) by install.sh / uninstall.sh. Sets PY (and PY_ARGS for `py -3`) to the
# first candidate that runs and is Python >= 3.9, in this order:
#     python3   (macOS / Linux / Git Bash with a python3 on PATH)
#     py -3     (the Windows Python launcher; Git Bash often has no python3)
#     python    (Windows python.org / Microsoft Store installs)
# A Microsoft Store "App execution alias" stub fails the version probe and is skipped.
# install.ps1 / uninstall.ps1 use the same order. The ci-templates pre-push hook and scripts/ci.sh
# carry an inline copy of the same order because they must work stand-alone in a downstream repo.
# shellcheck disable=SC2034  # PY / PY_ARGS are read by the sourcing script
sdd_find_python() {
  PY=""
  PY_ARGS=""
  for cand in python3 "py -3" python; do
    exe=${cand%% *}
    args=""
    [ "$exe" != "$cand" ] && args=${cand#* }
    command -v "$exe" >/dev/null 2>&1 || continue
    # shellcheck disable=SC2086  # $args is a single literal flag or empty
    if "$exe" $args -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      PY=$exe
      PY_ARGS=$args
      return 0
    fi
  done
  return 1
}
