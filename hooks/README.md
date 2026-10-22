# SDD secret-handling hooks

Two harness-enforced safeguards that keep secret *values* out of the transcript while still
letting agents *use* secrets. They apply to the main session **and every subagent**, for both
shell tools: `Bash` (Git Bash on Windows) and the built-in `PowerShell` tool on Windows.

- **`secret-guard.py`** — PreToolUse (`Bash|PowerShell`). Blocks commands that would *dump* a
  secret into context and allows sanctioned *use*. On block it returns a deny reason pointing the
  agent at the `SECRET REQUEST` escalation.
- **`secret-redact.py`** — PostToolUse (`Bash|PowerShell`). Backstop that scrubs secret-shaped
  strings (AWS/GitHub/Slack/Google/Stripe tokens, JWTs, auth headers, private-key blocks,
  `secret=…` pairs) out of shell output via `updatedToolOutput` before the model reads it. Only
  rewrites output when it finds a match.

These are the enforcement layer; the *policy* lives in `CLAUDE.md` ("Secret Handling — use,
don't read") and in each agent's Secret Handling section.

## Supported protection vectors

Both tools are checked with the same rule set (a Bash command can start `pwsh -c …` and the
reverse). Secret-store paths match with `/` or `\` separators and drive letters
(`C:\Users\me\.aws\credentials`, `/c/Users/me/.ssh/id_rsa`).

| Blocked (dump) | Examples |
|---|---|
| Full-environment dumps | `printenv`, bare `env`, `Get-ChildItem env:`, `gci env:`, `dir env:`, `ls env:`, `[Environment]::GetEnvironmentVariable(s)` |
| Tracing that expands values | `set -x`, `set -o xtrace`, `Set-PSDebug -Trace 1` / `2` |
| A dump tool reading a secret store | `cat .env`, `grep … ~/.aws/credentials`, `Get-Content .env`, `gc C:\proj\.env`, `type …\id_rsa`, `Select-String -Path .env`, `[IO.File]::ReadAllText(…)` |
| Printing a token variable | `echo "$GH_TOKEN"`, `gh auth token`, a bare `gcloud auth print-access-token`; in PowerShell any secret-shaped `$env:NAME` (…TOKEN, …SECRET, …PASSWORD, …API_KEY, …) printed bare or by `echo` / `Write-Output` / `Write-Host` |

| Allowed (use) | Examples |
|---|---|
| A binary reads the key itself | `ssh -i key.pem`, `curl --cert key.pem` |
| A secret passed by env-var name | `curl -H "Authorization: Bearer $TOKEN"`, `curl.exe -H "Authorization: Bearer $env:TOKEN"` |

**Limits.** These are regex hooks. They stop the common dump vectors; they do **not** stop every
exfiltration. A script file that prints a variable, an encoded or obfuscated command, a network
upload, or a non-shell tool is not detected. The deny rules and the redaction backstop reduce the
exposure further, but the policy ("use, don't read" + `SECRET REQUEST`) is the primary control.

## Install

The installer sets everything up (it asks first, or use `--hooks` / `--yes`):

```bash
./install.sh                                    # macOS, Linux, Git Bash on Windows
```

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1     # Windows PowerShell / pwsh
```

It copies the scripts to `<claude home>/hooks/`, then edits `<claude home>/settings.json`:

- adds the `permissions.deny` rules below (keeps every rule you already have);
- registers each hook **once**, in exec form, with the absolute interpreter path and the absolute
  script path (exec form runs without a shell, so paths with spaces need no quoting):

```jsonc
"hooks": {
  "PreToolUse":  [ { "matcher": "Bash|PowerShell", "hooks": [ { "type": "command",
      "command": "/abs/path/to/python3", "args": [ "/abs/path/to/.claude/hooks/secret-guard.py" ] } ] } ],
  "PostToolUse": [ { "matcher": "Bash|PowerShell", "hooks": [ { "type": "command",
      "command": "/abs/path/to/python3", "args": [ "/abs/path/to/.claude/hooks/secret-redact.py" ] } ] } ]
}
```

Managed entries are found by **identity** (the script name `secret-guard.py` / `secret-redact.py`
in `command` or `args`). An older entry such as `python3 ~/.claude/hooks/secret-guard.py` is
replaced, never duplicated. Unrelated settings and hooks are preserved. Before a change it writes
`settings.json.bak` (the state just before) and, once, `settings.json.sdd-orig.bak` (the state
before the first SDD change). The write is atomic. A reinstall that changes nothing leaves the file
and its backups untouched.

**Fail-closed.** The installer runs the exact commands it is about to register with synthetic
payloads (Bash and PowerShell; a dump must be denied, a normal command allowed, a token redacted)
before it writes, and verifies `settings.json` again after it writes. Malformed or wrong-shape
JSON, a failed write, or a failed self-test exits non-zero with `NOT PROTECTED` and leaves
`settings.json` unchanged. Check an installation at any time with
`python3 install.py --verify [--claude-home PATH]`.

The installer resolves the interpreter once. **Re-run it after you move or upgrade Python** — a hook
whose interpreter path no longer exists fails as a non-blocking hook error, which means no
protection.

Deny rules (gitignore-style; `~/` is home-relative on every platform, and the harness normalizes
Windows paths to forward slashes, so the same rules cover Windows; the `AppData` rule is gcloud's
Windows config dir):

```jsonc
"Read(**/.env)", "Read(**/.env.*)", "Read(**/*.pem)", "Read(**/*.key)",
"Read(**/id_rsa*)", "Read(**/id_ed25519*)", "Read(**/*.p12)", "Read(**/*.pfx)",
"Read(**/credentials)", "Read(**/service-account*.json)", "Read(**/*.tfvars)",
"Read(**/kubeconfig)", "Read(**/.netrc)",
"Read(~/.aws/**)", "Read(~/.ssh/**)", "Read(~/.kube/**)", "Read(~/.config/gcloud/**)",
"Read(~/AppData/Roaming/gcloud/**)"
```

`uninstall.sh` / `uninstall.ps1` remove the two hook entries and only the deny rules the installer
added; rules that existed before the install stay.

## Test

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' | python3 hooks/secret-guard.py   # → deny JSON
echo '{"tool_name":"PowerShell","tool_input":{"command":"Get-ChildItem env:"}}' | python3 hooks/secret-guard.py   # → deny JSON
printf '%s' '{"tool_name":"Bash","tool_response":{"stdout":"k=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"}}' | python3 hooks/secret-redact.py   # → redacted
```

The full suite covers both tools: `tests/test_secret_guard_powershell.py` and
`tests/test_windows_install.py` (which runs the exact commands from a generated `settings.json`).
