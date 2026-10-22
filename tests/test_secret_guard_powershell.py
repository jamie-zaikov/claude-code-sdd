#!/usr/bin/env python3
"""secret-guard.py / secret-redact.py on the PowerShell tool and Windows paths (portable).

Every case runs the real hook script as a process with a JSON payload on stdin — the same
contract the harness uses — and checks the decision, not the regex spelling. Secret-shaped
fixtures are assembled from fragments so no secret-shaped literal is stored in this file.

Run: python3 -m unittest tests.test_secret_guard_powershell -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "hooks" / "secret-guard.py"
REDACT = ROOT / "hooks" / "secret-redact.py"

ENV = "." + "env"  # keeps a literal `cat .env` out of this file's own command lines


def run_hook(script, payload):
    return subprocess.run([sys.executable, str(script)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)


def decision(tool, command):
    proc = run_hook(GUARD, {"hook_event_name": "PreToolUse", "tool_name": tool,
                            "tool_input": {"command": command}})
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return "allow"
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]


DENY_POWERSHELL = [
    f"Get-Content {ENV}",
    f"gc C:\\work\\app\\{ENV}",
    f"type C:\\proj\\{ENV}.local",
    "cat ~\\.ssh\\id_rsa",
    "Get-Content C:\\Users\\me\\.aws\\credentials",
    "Get-Content $HOME\\.kube\\config",
    "gc $env:APPDATA\\gcloud\\x.json",
    "Get-Content C:\\Users\\me\\AppData\\Roaming\\gcloud\\credentials.db",
    f"Select-String -Path {ENV} -Pattern KEY",
    f"[IO.File]::ReadAllText('C:\\p\\{ENV}')",
    "Get-ChildItem env:",
    "gci Env:\\GH_TOKEN",
    "dir env:",
    "ls env:",
    "Get-ChildItem -Path Env:",
    "Get-Item env:API_KEY",
    "Write-Output $env:GH_TOKEN",
    "echo $env:API_KEY",
    'Write-Host "value=$env:MY_SECRET"',
    "$env:GITHUB_TOKEN",
    '"${env:DB_PASSWORD}"',
    "$env:AWS_ACCESS_KEY_ID; $env:API_TOKEN",
    "$env:API_TOKEN | Out-Host",
    "[Environment]::GetEnvironmentVariable('API_TOKEN')",
    "[System.Environment]::GetEnvironmentVariables()",
    "Set-PSDebug -Trace 1",
    "set-psdebug -trace 2",
    "gh auth token",
]

ALLOW_POWERSHELL = [
    'curl.exe -H "Authorization: Bearer $env:API_TOKEN" https://example.invalid',  # pragma: allowlist secret (env-var reference)
    "ssh -i C:\\keys\\id_ed25519 deploy@host",
    "Write-Host $env:PATH",
    "$env:GH_TOKEN.Length",
    '$env:API_TOKEN = "placeholder"',  # pragma: allowlist secret (placeholder)
    "echo done; curl.exe -H \"X-Key: $env:API_KEY\" https://example.invalid",
    "Set-PSDebug -Trace 0",
    "Get-ChildItem .",
    "Get-Content README.md",
    "Get-Content $env:USERPROFILE\\notes.txt",
    "git log --oneline -5",
    "gh pr list",
]


class PowerShellGuardTest(unittest.TestCase):
    def test_dump_vectors_are_denied(self):
        for command in DENY_POWERSHELL:
            with self.subTest(command=command):
                self.assertEqual(decision("PowerShell", command), "deny")

    def test_use_vectors_are_allowed(self):
        for command in ALLOW_POWERSHELL:
            with self.subTest(command=command):
                self.assertEqual(decision("PowerShell", command), "allow")

    def test_case_and_spacing_variants_keep_the_decision(self):
        # Equivalent reformats: PowerShell is case-insensitive and tolerant of spacing.
        for command in ("GET-CONTENT " + ENV, "get-content   " + ENV, "Gci   ENV:", "WRITE-OUTPUT $ENV:GH_TOKEN"):
            with self.subTest(command=command):
                self.assertEqual(decision("PowerShell", command), "deny")

    def test_powershell_vectors_also_apply_to_bash(self):
        # A Bash command can start PowerShell, so the rule set is shared.
        self.assertEqual(decision("Bash", 'pwsh -c "Get-ChildItem env:"'), "deny")

    def test_bash_rules_still_apply_to_both_tools(self):
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                self.assertEqual(decision(tool, "cat " + ENV), "deny")
                self.assertEqual(decision(tool, "printenv"), "deny")
                self.assertEqual(decision(tool, "ls -la"), "allow")

    def test_windows_paths_under_bash(self):
        # Git Bash accepts backslash and drive-letter paths too.
        self.assertEqual(decision("Bash", "cat C:\\Users\\me\\.ssh\\id_rsa"), "deny")
        self.assertEqual(decision("Bash", "cat /c/Users/me/.aws/credentials"), "deny")

    def test_other_tools_are_ignored(self):
        proc = run_hook(GUARD, {"tool_name": "Read", "tool_input": {"command": "Get-ChildItem env:"}})
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))


class PowerShellRedactTest(unittest.TestCase):
    def test_powershell_output_is_redacted(self):
        secret = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                proc = run_hook(REDACT, {"tool_name": tool, "tool_response": {"stdout": f"k={secret}"}})
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn(secret, proc.stdout)
                self.assertIn("[REDACTED-SECRET]", json.loads(proc.stdout)["hookSpecificOutput"]["updatedToolOutput"])

    def test_other_tools_pass_through(self):
        secret = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        proc = run_hook(REDACT, {"tool_name": "Read", "tool_response": {"stdout": f"k={secret}"}})
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
