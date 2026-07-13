# SDD secret-handling hooks

Two harness-enforced safeguards that keep secret *values* out of the transcript while still
letting agents *use* secrets. They apply to the main session **and every subagent**.

- **`secret-guard.py`** — PreToolUse (Bash). Blocks commands that would *dump* a secret into
  context (`printenv`, bare `env`, `set -x`, and dump-tools like `cat`/`grep`/`base64` reading a
  known secret store). Allows sanctioned *use* (`ssh -i key`, `curl --cert key`, `$TOKEN`
  references). On block it returns a deny reason pointing the agent at the `SECRET REQUEST`
  escalation.
- **`secret-redact.py`** — PostToolUse (Bash). Backstop that scrubs secret-shaped strings
  (AWS/GitHub/Slack/Google/Stripe tokens, JWTs, auth headers, private-key blocks, `secret=…`
  pairs) out of Bash output via `updatedToolOutput` before the model reads it. Only rewrites
  output when it finds a match.

These are the enforcement layer; the *policy* lives in `CLAUDE.md` ("Secret Handling — use,
don't read") and in each agent's Secret Handling section.

## Install (machine-level, in `~/.claude/`)

The scripts and their registration are machine config, so they live in `~/.claude/`, not in this
repo's tracked tree. To set up on a new machine:

```bash
mkdir -p ~/.claude/hooks
cp hooks/secret-guard.py hooks/secret-redact.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.py
```

Then add to `~/.claude/settings.json`:

```jsonc
"permissions": {
  "deny": [
    "Read(**/.env)", "Read(**/.env.*)", "Read(**/*.pem)", "Read(**/*.key)",
    "Read(**/id_rsa*)", "Read(**/id_ed25519*)", "Read(**/*.p12)", "Read(**/*.pfx)",
    "Read(**/credentials)", "Read(**/service-account*.json)", "Read(**/*.tfvars)",
    "Read(**/kubeconfig)", "Read(**/.netrc)",
    "Read(~/.aws/**)", "Read(~/.ssh/**)", "Read(~/.kube/**)", "Read(~/.config/gcloud/**)"
  ]
},
"hooks": {
  "PreToolUse":  [ { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/secret-guard.py" } ] } ],
  "PostToolUse": [ { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/secret-redact.py" } ] } ]
}
```

## Test

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' | python3 hooks/secret-guard.py   # → deny JSON
printf '%s' '{"tool_name":"Bash","tool_response":{"stdout":"k=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"}}' | python3 hooks/secret-redact.py   # → redacted
```
