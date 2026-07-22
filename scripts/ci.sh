#!/usr/bin/env bash
# scripts/ci.sh — this repo's concrete build/test/lint entrypoint (dogfood; FR-21, FR-15).
#
# Invoked by BOTH the sdd-build-test-lint CI workflow (`bash scripts/ci.sh`) and
# the pre-push hook (via this shebang when executable, else `sh`), so CI and the
# local gate run identical checks (FR-16, NFR-3). It runs the SDD framework's own
# checks and exits NON-ZERO on the first failure.
#
# Checks:
#   1. `python3 -m py_compile` on the hook scripts and the shared scanner.
#   2. secret-guard.py / secret-redact.py smoke test — the exact commands
#      documented in hooks/README.md. The token-shaped fixture for the redact
#      test is assembled from fragments at runtime so no secret-shaped literal is
#      stored in this file (the repo's own secret-scan gate would otherwise flag
#      it).
#   3. `bash -n` on install.sh, plus `shellcheck install.sh` when shellcheck is
#      available. shellcheck's ABSENCE is not a failure (skipped gracefully); a
#      shellcheck FINDING is a check failure.

set -euo pipefail

# Resolve the repo root from this script's own location so it works regardless
# of the caller's CWD (CI runs from the repo root; the pre-push hook may not).
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_ROOT"

say() { printf '%s\n' "$*"; }

# --- 1. Byte-compile the Python scripts ------------------------------------
say "==> py_compile: hook scripts + shared scanner"
python3 -m py_compile \
  hooks/secret-guard.py \
  hooks/secret-redact.py \
  .github/scripts/sdd-secret-scan.py
say "    ok"

# --- 2. secret-guard / secret-redact smoke test ----------------------------
# Mirrors the commands in hooks/README.md.
say "==> smoke: secret-guard.py denies a secret-store read"
guard_out=$(printf '%s' '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' \
  | python3 hooks/secret-guard.py)
case "$guard_out" in
  *'"permissionDecision": "deny"'*) say "    ok (deny emitted)" ;;
  *) say "    FAIL: secret-guard.py did not deny reading a secret store"
     say "$guard_out"
     exit 1 ;;
esac

say "==> smoke: secret-redact.py scrubs a token-shaped string"
# Assemble the token-shaped fixture from fragments; no full literal is stored.
gh_prefix='ghp_'
gh_body='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
fixture="k=${gh_prefix}${gh_body}"
redact_in=$(printf '{"tool_name":"Bash","tool_response":{"stdout":"%s"}}' "$fixture")
redact_out=$(printf '%s' "$redact_in" | python3 hooks/secret-redact.py)
case "$redact_out" in
  *"$gh_body"*) say "    FAIL: secret-redact.py left the token-shaped value in its output"
                exit 1 ;;
  *'[REDACTED-SECRET]'*) say "    ok (value redacted)" ;;
  *) say "    FAIL: secret-redact.py produced no redaction output"
     say "$redact_out"
     exit 1 ;;
esac

# --- 3. Shell lint: install.sh ---------------------------------------------
say "==> bash -n: install.sh"
bash -n install.sh
say "    ok"

if command -v shellcheck >/dev/null 2>&1; then
  say "==> shellcheck: install.sh"
  shellcheck install.sh
  say "    ok"
else
  say "==> shellcheck: not installed — skipping (advisory; not a failure)"
fi

say ""
say "ci.sh: all checks passed."
