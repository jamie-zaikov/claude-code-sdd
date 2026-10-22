#!/usr/bin/env python3
r"""
PreToolUse hook (matcher: Bash|PowerShell) — blocks commands that would DUMP a
secret into context, while allowing sanctioned USE of secrets. Both shell tools are
checked with the union of the Bash and PowerShell rules (a Bash command can start
`pwsh -c ...` and vice versa). Paths match with `/` or `\` separators and drive
letters (`C:\Users\me\.aws\credentials`).

Blocks:
  - Full-environment dumps:            `printenv`, bare `env`, `env | ...`
  - Shell tracing that expands values: `set -x`, `set -o xtrace`
  - Reading a known secret store with a DUMP tool
      (cat/less/head/tail/grep/xxd/base64/strings/awk/sed/...) e.g. `cat .env`
  - GitHub-token dump vectors:          `gh auth token`, `echo "$GH_TOKEN"`,
      `printf '%s' "$GITHUB_TOKEN"` (sanctioned `gh` use is left untouched)

  - PowerShell dump vectors: Get-Content/gc/cat/type/Select-String on a secret
      store; env-drive reads (`Get-ChildItem env:`, `gci env:`, `dir env:`,
      `ls env:`); printing a secret-shaped `$env:NAME` (bare, echo, Write-Output,
      Write-Host, ...); `[Environment]::GetEnvironmentVariable(s)`;
      `Set-PSDebug -Trace 1|2`.

Allows (does NOT block):
  - Using a secret via a binary that reads it itself: `ssh -i key.pem`,
    `curl --cert key.pem`, `openssl ... key.pem` — the value never enters context.
  - Referencing a secret by env-var name: `curl -H "Authorization: Bearer $TOKEN"`,
    and in PowerShell `curl.exe -H "Authorization: Bearer $env:TOKEN"`.

Limits: a regex guard stops the common dump vectors, not every exfiltration (e.g. a
script file that prints a variable, or an obfuscated command, is not detected).

On block: exits 0 with a deny decision + a reason that points the agent at the
"use, don't read" pattern and the SECRET REQUEST escalation.
"""
import json
import re
import sys

# The harness's shell tools: Bash (Git Bash on Windows) and the built-in PowerShell tool.
SHELL_TOOLS = ("Bash", "PowerShell")

DUMP_TOOLS = r"(?:cat|bat|less|more|head|tail|nl|tac|grep|egrep|fgrep|rg|ag|xxd|od|hexdump|strings|base64|awk|sed|cut|tr)"

# Path fragments that identify a known secret store.
SECRET_PATH = re.compile(
    r"""(?xi)
    (?:^|[\s='"/\\:])              # boundary (`\` and `C:` for Windows paths)
    (?:
        \.env(?:\.[\w.-]+)?\b      # .env, .env.local, .env.production
      | id_rsa\b | id_ed25519\b
      | [/\\]credentials\b | (?<![\w.])credentials\b
      | [\w.-]*\.pem\b | [\w.-]*\.key\b | [\w.-]*\.p12\b | [\w.-]*\.pfx\b
      | service-account[\w.-]*\.json\b
      | [\w.-]*\.tfvars\b
      | kubeconfig\b
      | \.aws[/\\] | \.ssh[/\\] | \.kube[/\\] | \.config[/\\]gcloud[/\\]
      | AppData[/\\]Roaming[/\\]gcloud[/\\]
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

# `gcloud [flags] auth [application-default] print-access-token` / `print-identity-token` print a
# live credential to stdout. Used inline as a command substitution (`-H "Authorization: Bearer
# $(gcloud auth print-access-token)"`) the token flows into the consuming binary and never reaches
# the transcript — that is the sanctioned USE vector and stays allowed. A bare call — the observed
# leak was an "auth check" with a misordered `2>&1 >/dev/null` — prints it, so it is blocked.
# Global flags (`gcloud --quiet auth ...`), release tracks (`gcloud beta auth ...`), and flags
# between the words (`auth --account=x print-...`) are all the same call.
_G_ARGS = r"[^()|;&`\n]*?"
GCLOUD_TOKEN_PRINT = re.compile(
    rf"\bgcloud\b{_G_ARGS}\bauth\b{_G_ARGS}\bprint-(?:access|identity)-token\b"
)
# The inline use: `$(gcloud ... print-...-token [flags])`; flags may carry one level of parens
# (`--format='value(x)'`). No pipe, `;`, or `&` inside — `$(... | tee f)` writes the token out.
GCLOUD_TOKEN_SUBST = re.compile(
    rf"\$\(\s*gcloud\b{_G_ARGS}\bauth\b{_G_ARGS}\bprint-(?:access|identity)-token\b"
    r"(?:[^()|;&`\n]|\([^()|;&`\n]*\))*\)"
)
# Contexts that defeat the inline exemption, because the token lands somewhere printable: a variable
# (`T=$(...)`, `T="x$(...)"`, `export T=...`), an array (`a=( $(...) )`), a parameter-expansion
# default (`${X:-$(...)}`), or a print/dump consumer on the same line (`echo $(...)`).
GCLOUD_TOKEN_PARKED = re.compile(
    r"(?:\b[A-Za-z_]\w*=[^\s;&|]*|=\(\s*|\$\{[^}]*)\$\(\s*gcloud\b"
)
GCLOUD_TOKEN_CONSUMER = re.compile(r"(?:^|[\s;&|(`])(?:echo|printf|print|cat|tee|xargs)(?![\w-])")


def _gcloud_token_leak(command: str) -> bool:
    if not GCLOUD_TOKEN_PRINT.search(command):
        return False
    if GCLOUD_TOKEN_PARKED.search(command) or GCLOUD_TOKEN_CONSUMER.search(command):
        return True
    return bool(GCLOUD_TOKEN_PRINT.search(GCLOUD_TOKEN_SUBST.sub("", command)))

# --- PowerShell vectors (PowerShell is case-insensitive, so these are (?i)) ------------------
# A PowerShell statement ends at `;`, `|`, or a newline.
_PS_SEG = r"[^;|\n]*"
# Cmdlets and aliases that print a file's content. `(?<![\w-])` keeps `--type` / `Foo-gc` out.
PS_DUMP_OF_SECRET = re.compile(
    r"(?i)(?<![\w-])(?:Get-Content|gc|type|cat|Select-String|sls|Format-Hex|fhx|more|Get-Item|gi)"
    r"(?![\w-])" + _PS_SEG
)
PS_FILE_READ = re.compile(r"(?i)\[(?:System\.)?IO\.File\]::ReadAll(?:Text|Lines|Bytes)\s*\(" + _PS_SEG)
# The `env:` drive lists names AND values. `(?<![\w$])` keeps `$env:NAME` (a variable) out.
PS_ENV_DRIVE = re.compile(
    r"(?i)(?<![\w-])(?:Get-ChildItem|gci|dir|ls|Get-Item|gi|Get-Content|gc|cat|type)(?![\w-])"
    r"[^;|\n]*?(?<![\w$])env:"
)
PS_ENV_API = re.compile(r"(?i)\[(?:System\.)?Environment\]::GetEnvironmentVariables?\b")
PS_TRACE = re.compile(r"(?i)\bSet-PSDebug\b[^;|\n]*-Trace\s*:?\s*[12]\b")
# A secret-shaped environment variable name in `$env:NAME` or `${env:NAME}` form.
_PS_SECRET_VAR = (
    r"\$\{?env:\w*(?:token|secret|passw(?:or)?d|pwd|api_?key|access_?key|private_?key"
    r"|credential|auth)\w*\}?"
)
# Printing it: a print cmdlet/alias in the same statement ...
PS_SECRET_PRINT = re.compile(
    r"(?i)(?<![\w-])(?:echo|write|Write-Output|Write-Host|Write-Information|Write-Verbose"
    r"|Write-Debug|Write-Warning|Write-Error|Out-Host|Out-String|Out-Default)(?![\w-])"
    + _PS_SEG + _PS_SECRET_VAR
)
# ... or the bare expression as a whole statement (PowerShell prints an unconsumed value).
PS_SECRET_BARE = re.compile(
    r"(?i)(?:^|[;\n{(])\s*[\"']?" + _PS_SECRET_VAR + r"[\"']?\s*(?:$|[;\n|})])"
)


def _powershell_blocked(command: str) -> bool:
    if PS_ENV_DRIVE.search(command) or PS_ENV_API.search(command) or PS_TRACE.search(command):
        return True
    if PS_SECRET_PRINT.search(command) or PS_SECRET_BARE.search(command):
        return True
    for pat in (PS_DUMP_OF_SECRET, PS_FILE_READ):
        for m in pat.finditer(command):
            if SECRET_PATH.search(m.group(0)):
                return True
    return False


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
    # A gcloud token print outside a sanctioned inline `$(...)` use prints a live credential.
    if _gcloud_token_leak(command):
        return True
    # A dump tool whose argument list references a secret store.
    for m in DUMP_OF_SECRET.finditer(command):
        if SECRET_PATH.search(m.group(0)):
            return True
    # PowerShell vectors apply to both tools (`pwsh -c "gci env:"` can run from Bash).
    return _powershell_blocked(command)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # can't parse — do not interfere
    if data.get("tool_name") not in SHELL_TOOLS:
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
