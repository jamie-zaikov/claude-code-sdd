"""Run the EXACT hook commands (exec form: command + args, no shell) with synthetic payloads.

Exec-form hooks are spawned without a shell, so an argv of [command, *args] is the same process
the harness starts. Fixtures are harmless: no real secret is read; the token-shaped string for the
redact check is assembled from fragments so no secret-shaped literal is stored in this file.
"""

import json
import subprocess
from typing import List, Tuple

from .settings import DENY_RULES, MANAGED_HOOKS, MATCHER, is_managed

# Settings that make the harness run no user hooks at all. The installer can only see the user
# settings file; project, local and managed settings can set these too (a documented limit).
HOOKS_OFF = ("disableAllHooks", "allowManagedHooksOnly")

# (tool_name, command, expect_deny)
GUARD_CASES = [
    ("Bash", "cat .env", True),
    ("Bash", "printenv", True),
    ("PowerShell", "Get-Content .env", True),
    ("PowerShell", "Get-ChildItem env:", True),
    ("Bash", "ls -la", False),
    ("PowerShell", "Get-ChildItem .", False),
    ("Bash", "cat notes.txt && ssh -i deploy.pem host", False),
    ("Bash", "cd sub && cat .env", True),
]


def _token() -> str:
    return "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def run_hook(argv: List[str], payload: dict, timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout
    )


def managed_entries(settings: dict, event: str) -> List[Tuple[str, dict]]:
    """All (matcher, entry) pairs under `event` that run our script for that event."""
    out = []
    for group in settings.get("hooks", {}).get(event, []) or []:
        if not isinstance(group, dict):
            continue
        for entry in group.get("hooks", []) or []:
            if is_managed(entry, MANAGED_HOOKS[event]):
                out.append((group.get("matcher", ""), entry))
    return out


def argv_of(entry: dict) -> List[str]:
    return [entry["command"]] + list(entry.get("args") or [])


def _denied(proc: subprocess.CompletedProcess) -> bool:
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        return False
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def check_guard(argv: List[str]) -> List[str]:
    problems = []
    for tool, command, expect_deny in GUARD_CASES:
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}}
        try:
            proc = run_hook(argv, payload)
        except (OSError, subprocess.SubprocessError) as e:
            return [f"guard hook could not run ({e})"]
        if proc.returncode != 0:
            problems.append(f"guard hook exited {proc.returncode} for {tool} `{command}`: {proc.stderr.strip()}")
        elif _denied(proc) != expect_deny:
            want = "deny" if expect_deny else "allow"
            problems.append(f"guard hook did not {want} {tool} `{command}`")
    return problems


def check_redact(argv: List[str]) -> List[str]:
    problems = []
    secret = _token()
    for tool in ("Bash", "PowerShell"):
        payload = {"hook_event_name": "PostToolUse", "tool_name": tool,
                   "tool_response": {"stdout": f"k={secret}"}}
        try:
            proc = run_hook(argv, payload)
        except (OSError, subprocess.SubprocessError) as e:
            return [f"redact hook could not run ({e})"]
        if proc.returncode != 0 or secret in proc.stdout or "[REDACTED-SECRET]" not in proc.stdout:
            problems.append(f"redact hook did not redact {tool} output (exit {proc.returncode})")
    return problems


def verify_settings(settings: dict) -> List[str]:
    """Check the generated settings: hooks not switched off, every deny rule present, one managed
    entry per event, right matcher, hooks behave. A hook process that works proves nothing if the
    harness is told not to run it, so a switched-off setting is a failure, never a warning."""
    problems = [f"settings set {key}: the harness runs no user hooks"
                for key in HOOKS_OFF if settings.get(key) is True]
    deny = (settings.get("permissions") or {}).get("deny") or []
    missing = [rule for rule in DENY_RULES if rule not in deny]
    if missing:
        problems.append("deny rules missing: " + ", ".join(missing))
    argvs: dict = {}
    for event, script in MANAGED_HOOKS.items():
        entries = managed_entries(settings, event)
        if len(entries) != 1:
            problems.append(f"{event}: expected exactly 1 {script} entry, found {len(entries)}")
            continue
        matcher, entry = entries[0]
        if matcher != MATCHER:
            problems.append(f"{event}: matcher is {matcher!r}, expected {MATCHER!r}")
        if not isinstance(entry.get("command"), str) or not isinstance(entry.get("args"), list):
            problems.append(f"{event}: entry is not exec form (command + args)")
            continue
        argvs[event] = argv_of(entry)
    if "PreToolUse" in argvs:
        problems += check_guard(argvs["PreToolUse"])
    if "PostToolUse" in argvs:
        problems += check_redact(argvs["PostToolUse"])
    return problems

