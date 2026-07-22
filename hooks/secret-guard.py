#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash) — blocks commands that would DUMP a secret into
context, while allowing sanctioned USE of secrets.

Blocks:
  - Full-environment dumps:            `printenv`, bare `env`, `env | ...`
  - Shell tracing that expands values: `set -x`, `set -o xtrace`
  - Reading a known secret store with a DUMP tool
      (cat/less/head/tail/grep/xxd/base64/strings/awk/sed/...) e.g. `cat .env`
  - GitHub-token dump vectors:          `gh auth token`, `echo "$GH_TOKEN"`,
      `printf '%s' "$GITHUB_TOKEN"` (sanctioned `gh` use is left untouched)

Allows (does NOT block):
  - Using a secret via a binary that reads it itself: `ssh -i key.pem`,
    `curl --cert key.pem`, `openssl ... key.pem` — the value never enters context.
  - Referencing a secret by env-var name: `curl -H "Authorization: Bearer $TOKEN"`.

On block: exits 0 with a deny decision + a reason that points the agent at the
"use, don't read" pattern and the SECRET REQUEST escalation.
"""
import json
import re
import sys

DUMP_TOOLS = r"(?:cat|bat|less|more|head|tail|nl|tac|grep|egrep|fgrep|rg|ag|xxd|od|hexdump|strings|base64|awk|sed|cut|tr)"

# Path fragments that identify a known secret store.
SECRET_PATH = re.compile(
    r"""(?xi)
    (?:^|[\s='"/])                 # boundary
    (?:
        \.env(?:\.[\w.-]+)?\b      # .env, .env.local, .env.production
      | id_rsa\b | id_ed25519\b
      | /credentials\b | (?<![\w.])credentials\b
      | [\w.-]*\.pem\b | [\w.-]*\.key\b | [\w.-]*\.p12\b | [\w.-]*\.pfx\b
      | service-account[\w.-]*\.json\b
      | [\w.-]*\.tfvars\b
      | kubeconfig\b
      | \.aws/ | \.ssh/ | \.kube/ | \.config/gcloud/
      | \.netrc\b
    )
    """,
)

BARE_ENV_DUMP = re.compile(r"(?:^|[;&|]\s*)env\s*(?:\||>|;|&|$)")
PRINTENV = re.compile(r"(?:^|[;&|]\s*)printenv\b")
SET_TRACE = re.compile(r"(?:^|[;&|]\s*)set\s+(?:-x\b|-o\s+xtrace\b)")
DUMP_OF_SECRET = re.compile(rf"\b{DUMP_TOOLS}\b[^;&|]*")

# `gh auth token` (and its arg variants, e.g. `gh auth token --hostname github.com`)
# — the canonical command that prints a GitHub token. The leading boundary also
# catches command substitution (`$(gh auth token)`, `` `gh auth token` ``). Requiring
# `auth token` as whole words means `gh auth status` / `gh auth login` and every other
# `gh` subcommand (pr/label/api/...) are NOT matched — only the token-print vector is.
GH_TOKEN_DUMP = re.compile(r"(?:^|[\s;&|(`])gh\s+auth\s+token\b")

# echo/printf of the GitHub-token env vars in `$VAR`, `"$VAR"`, or `${VAR}` form —
# the print vectors the base PRINTENV/BARE_ENV_DUMP regexes miss. Keyed to a print
# builtin so a sanctioned `gh` command that merely references the var (e.g.
# `gh pr create --body "$GITHUB_TOKEN"`) is NOT matched: we block the print vector,
# not the use vector. The trailing `\b` prevents `$GH_TOKENS`-style false matches.
GH_TOKEN_ENV_PRINT = re.compile(
    r"(?:^|[\s;&|(`])(?:echo|printf|print)\b[^;&|]*"
    r"\$\{?(?:GH_TOKEN|GITHUB_TOKEN)\b\}?"
)

DENY_REASON = (
    "Blocked: this command would print a secret into the transcript. "
    "Do not read secret material into context. Instead USE it without reading it: "
    "reference it by env-var name ($TOKEN / os.environ / python-dotenv), or let a binary "
    "read the key itself (ssh -i <keypath>, curl --cert <path>). "
    "If the secret is not available, halt and return `SECRET REQUEST: <need>` asking the "
    "operator to export it or add it to a gitignored .env — never work around this block."
)


def is_blocked(command: str) -> bool:
    if PRINTENV.search(command) or BARE_ENV_DUMP.search(command) or SET_TRACE.search(command):
        return True
    # GitHub-token dump vectors (`gh auth token`, echo/printf of GH_TOKEN/GITHUB_TOKEN).
    if GH_TOKEN_DUMP.search(command) or GH_TOKEN_ENV_PRINT.search(command):
        return True
    # A dump tool whose argument list references a secret store.
    for m in DUMP_OF_SECRET.finditer(command):
        if SECRET_PATH.search(m.group(0)):
            return True
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # can't parse — do not interfere
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command:
        return 0
    if is_blocked(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": DENY_REASON,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
