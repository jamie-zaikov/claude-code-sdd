#!/usr/bin/env python3
"""install.py / uninstall.py into an isolated destination whose path contains a space.

Portable (macOS, Linux, Windows): every run passes --claude-home into a temp dir, HOME and
USERPROFILE point at a temp dir, and CLAUDE_CONFIG_DIR is removed from the child environment,
so no test can touch the user's real installation. --no-pre-push is always passed (the pre-push
step writes into this checkout's .git/hooks). The hook commands are read back from the generated
settings.json and executed exactly as registered (exec form: argv = command + args, no shell).

Run: python3 -m unittest tests.test_windows_install -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from tests import winsupport
except ImportError:  # run from inside tests/
    import winsupport
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sdd_install import settings as sdd_settings  # noqa: E402
from sdd_install.common import InstallError  # noqa: E402

BASH = winsupport.BASH
OLD_GUARD = {"type": "command", "command": "python3 ~/.claude/hooks/secret-guard.py"}
OLD_REDACT = {"type": "command", "command": "python3 ~/.claude/hooks/secret-redact.py"}
USER_HOOK = {"type": "command", "command": "echo user-hook"}
ENV_FILE = "." + "env"
TOKEN = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class Sandbox:
    def __init__(self, base: Path):
        self.base = base
        self.home = base / "user home"
        self.dest = base / "claude home"  # the space is deliberate
        self.home.mkdir()

    @property
    def settings_path(self) -> Path:
        return self.dest / "settings.json"

    def env(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(HOME=str(self.home), USERPROFILE=str(self.home), NO_COLOR="1")
        return env

    def run(self, script, *args, root=ROOT):
        return subprocess.run(
            [sys.executable, str(root / script), "--claude-home", str(self.dest), *args],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, env=self.env(), timeout=300,
        )

    def install(self, *args, root=ROOT):
        return self.run("install.py", "--yes", "--no-pre-push", *args, root=root)

    def uninstall(self, *args, root=ROOT):
        return self.run("uninstall.py", "--yes", *args, root=root)

    def write_settings(self, data):
        self.dest.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2) + "\n"
        self.settings_path.write_text(text, encoding="utf-8")
        return text

    def settings(self):
        return json.loads(self.settings_path.read_text(encoding="utf-8"))


def managed(settings, event):
    script = sdd_settings.MANAGED_HOOKS[event]
    return [(g.get("matcher"), h) for g in settings.get("hooks", {}).get(event, [])
            for h in g.get("hooks", []) if sdd_settings.is_managed(h, script)]


def run_registered(entry, payload):
    """Execute the hook exactly as the settings entry registers it (exec form: no shell)."""
    argv = [entry["command"], *entry.get("args", [])]
    return subprocess.run(argv, input=json.dumps(payload), capture_output=True, text=True, timeout=60)


class Base(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.mkdtemp(prefix="sdd win test "))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        self.sb = Sandbox(base)

    def assertOk(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class FreshInstallTest(Base):
    def test_install_registers_one_exec_form_entry_per_event(self):
        self.assertOk(self.sb.install())
        s = self.sb.settings()
        for event in ("PreToolUse", "PostToolUse"):
            entries = managed(s, event)
            self.assertEqual(len(entries), 1, event)
            matcher, entry = entries[0]
            self.assertEqual(matcher, "Bash|PowerShell")
            self.assertTrue(os.path.isabs(entry["command"]), entry)
            self.assertTrue(os.path.isabs(entry["args"][0]), entry)
            self.assertTrue(Path(entry["args"][0]).is_file())
            self.assertIn("claude home", entry["args"][0])
        for rule in sdd_settings.DENY_RULES:
            self.assertIn(rule, s["permissions"]["deny"])

    def test_registered_commands_block_and_allow_as_documented(self):
        self.assertOk(self.sb.install())
        s = self.sb.settings()
        (_, guard), = managed(s, "PreToolUse")
        (_, redact), = managed(s, "PostToolUse")
        cases = [("Bash", "cat " + ENV_FILE, True), ("PowerShell", "Get-Content " + ENV_FILE, True),
                 ("PowerShell", "gci env:", True), ("Bash", "ls", False),
                 ("PowerShell", 'curl.exe -H "Authorization: Bearer $env:API_TOKEN" https://x.invalid', False)]  # pragma: allowlist secret (env-var reference)
        for tool, command, deny in cases:
            with self.subTest(tool=tool, command=command):
                proc = run_registered(guard, {"hook_event_name": "PreToolUse", "tool_name": tool,
                                              "tool_input": {"command": command}})
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual('"deny"' in proc.stdout, deny, proc.stdout)
        for tool in ("Bash", "PowerShell"):
            proc = run_registered(redact, {"hook_event_name": "PostToolUse", "tool_name": tool,
                                           "tool_response": {"stdout": f"k={TOKEN}"}})
            self.assertNotIn(TOKEN, proc.stdout)
            self.assertIn("[REDACTED-SECRET]", proc.stdout)

    def test_verify_cli_passes_on_a_fresh_install(self):
        self.assertOk(self.sb.install())
        self.assertOk(self.sb.run("install.py", "--verify"))

    def test_verify_cli_fails_when_a_hook_is_missing(self):
        self.assertOk(self.sb.install())
        s = self.sb.settings()
        del s["hooks"]["PreToolUse"]
        self.sb.write_settings(s)
        proc = self.sb.run("install.py", "--verify")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stdout)

    def test_verify_cli_fails_when_a_deny_rule_is_missing(self):
        self.assertOk(self.sb.install())
        s = self.sb.settings()
        s["permissions"]["deny"].remove("Read(~/.ssh/**)")
        self.sb.write_settings(s)
        proc = self.sb.run("install.py", "--verify")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stdout)
        self.assertIn("Read(~/.ssh/**)", proc.stdout + proc.stderr)

    def test_hooks_switched_off_is_never_reported_protected(self):
        for key in ("disableAllHooks", "allowManagedHooksOnly"):
            with self.subTest(key=key):
                self.sb.write_settings({key: True})
                proc = self.sb.install()
                self.assertNotEqual(proc.returncode, 0, proc.stdout)
                self.assertIn("NOT PROTECTED", proc.stdout)
                self.assertNotIn("ENABLED and verified", proc.stdout)
                self.assertNotEqual(self.sb.run("install.py", "--verify").returncode, 0)
                self.sb.settings_path.unlink()

    def test_no_hooks_means_no_settings(self):
        self.assertOk(self.sb.install("--no-hooks"))
        self.assertFalse(self.sb.settings_path.exists())
        self.assertTrue((self.sb.dest / "agents" / "orchestrator.md").is_file())


class MergeTest(Base):
    def user_settings(self):
        return {
            "model": "opus",
            "env": {"FOO": "1"},
            "permissions": {"allow": ["Bash(ls:*)"], "deny": ["Read(**/secret.txt)", "Read(**/.env)"]},
            "hooks": {
                "PreToolUse": [{"matcher": "Edit", "hooks": [USER_HOOK]},
                               {"matcher": "Bash", "hooks": [OLD_GUARD]}],
                "PostToolUse": [{"matcher": "Bash", "hooks": [USER_HOOK, OLD_REDACT]}],
                "Stop": [{"hooks": [USER_HOOK]}],
            },
        }

    def test_unrelated_settings_and_hooks_are_preserved(self):
        self.sb.write_settings(self.user_settings())
        self.assertOk(self.sb.install())
        s = self.sb.settings()
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["env"], {"FOO": "1"})
        self.assertEqual(s["permissions"]["allow"], ["Bash(ls:*)"])
        self.assertIn("Read(**/secret.txt)", s["permissions"]["deny"])
        self.assertEqual(s["permissions"]["deny"].count("Read(**/.env)"), 1)
        self.assertEqual(s["hooks"]["Stop"], [{"hooks": [USER_HOOK]}])
        self.assertIn({"matcher": "Edit", "hooks": [USER_HOOK]}, s["hooks"]["PreToolUse"])
        self.assertIn({"matcher": "Bash", "hooks": [USER_HOOK]}, s["hooks"]["PostToolUse"])

    def test_old_form_entries_are_replaced_not_duplicated(self):
        self.sb.write_settings(self.user_settings())
        self.assertOk(self.sb.install())
        text = self.sb.settings_path.read_text(encoding="utf-8")
        self.assertNotIn("~/.claude/hooks", text)
        s = self.sb.settings()
        for event in ("PreToolUse", "PostToolUse"):
            self.assertEqual(len(managed(s, event)), 1, event)

    def test_reinstall_is_idempotent(self):
        self.sb.write_settings(self.user_settings())
        self.assertOk(self.sb.install())
        first = self.sb.settings_path.read_bytes()
        backup_first = (self.sb.dest / "settings.json.bak").read_bytes()
        self.assertOk(self.sb.install())
        self.assertEqual(self.sb.settings_path.read_bytes(), first)
        # An unchanged reinstall does not overwrite the backup with the installed state.
        self.assertEqual((self.sb.dest / "settings.json.bak").read_bytes(), backup_first)

    def test_backup_restores_the_pre_install_settings(self):
        original = self.sb.write_settings(self.user_settings())
        self.assertOk(self.sb.install())
        self.assertNotEqual(self.sb.settings_path.read_text(encoding="utf-8"), original)
        for name in ("settings.json.bak", "settings.json.sdd-orig.bak"):
            self.assertEqual((self.sb.dest / name).read_text(encoding="utf-8"), original, name)
        # Controlled recovery: restoring the backup gives back the user's exact settings.
        shutil.copyfile(self.sb.dest / "settings.json.sdd-orig.bak", self.sb.settings_path)
        self.assertEqual(self.sb.settings(), self.user_settings())

    def test_malformed_settings_fail_not_protected_and_unchanged(self):
        self.sb.dest.mkdir(parents=True)
        self.sb.settings_path.write_text('{"model": "opus",', encoding="utf-8")
        proc = self.sb.install()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stdout)
        self.assertNotIn("Setup Complete", proc.stdout)
        self.assertEqual(self.sb.settings_path.read_text(encoding="utf-8"), '{"model": "opus",')
        self.assertFalse((self.sb.dest / "settings.json.bak").exists())

    def test_settings_with_a_bom_are_merged(self):
        path = self.sb.settings_path
        self.sb.dest.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"theme": "dark"}).encode())
        self.assertOk(self.sb.install())
        self.assertEqual(self.sb.settings()["theme"], "dark")

    def test_wrong_shape_settings_fail_unchanged(self):
        text = self.sb.write_settings({"hooks": []})
        proc = self.sb.install()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stdout)
        self.assertEqual(self.sb.settings_path.read_text(encoding="utf-8"), text)

    def test_failed_write_keeps_the_original_and_leaves_no_temp_file(self):
        text = self.sb.write_settings(self.user_settings())
        new, _ = sdd_settings.merge(self.user_settings(), sys.executable, self.sb.dest / "hooks")
        with mock.patch("sdd_install.common.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(InstallError):
                sdd_settings.save(self.sb.settings_path, new, text)
        self.assertEqual(self.sb.settings_path.read_text(encoding="utf-8"), text)
        leftovers = [p.name for p in self.sb.dest.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_broken_hook_script_is_never_registered(self):
        # Fail closed: a guard that allows everything must not land in settings.json.
        repo = self.sb.base / "repo copy"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".specs"))
        (repo / "hooks" / "secret-guard.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        text = self.sb.write_settings({"model": "opus"})
        proc = self.sb.install(root=repo)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stdout)
        self.assertEqual(self.sb.settings_path.read_text(encoding="utf-8"), text)


class UninstallTest(Base):
    def test_uninstall_removes_only_owned_entries(self):
        self.sb.write_settings({"model": "opus", "permissions": {"deny": ["Read(**/.env)", "Read(**/mine)"]},
                                "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [USER_HOOK]}]}})
        self.assertOk(self.sb.install())
        user_file = self.sb.dest / "agents" / "my-own-agent.md"
        user_file.write_text("mine\n", encoding="utf-8")
        edited = self.sb.dest / "agents" / "orchestrator.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nmy local note\n", encoding="utf-8")
        proc = self.sb.uninstall()
        self.assertOk(proc)
        s = self.sb.settings()
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["hooks"], {"PreToolUse": [{"matcher": "Edit", "hooks": [USER_HOOK]}]})
        # Pre-existing deny rules stay (even one the installer also manages); added ones go.
        self.assertEqual(s["permissions"]["deny"], ["Read(**/.env)", "Read(**/mine)"])
        self.assertTrue(user_file.exists())
        self.assertTrue(edited.exists())
        self.assertFalse((self.sb.dest / "agents" / "design-agent.md").exists())
        self.assertFalse((self.sb.dest / "hooks").exists())
        self.assertFalse((self.sb.dest / "tools").exists())
        self.assertTrue((self.sb.dest / "CLAUDE.md").exists())
        self.assertIn("orchestrator.md (changed since install)", proc.stdout)
        self.assertIn("CLAUDE.md", proc.stdout.split("Kept (not removed):")[1])

    def test_uninstall_aborts_on_malformed_settings_without_removing_files(self):
        self.assertOk(self.sb.install())
        self.sb.settings_path.write_text("{oops", encoding="utf-8")
        proc = self.sb.uninstall()
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue((self.sb.dest / "hooks" / "secret-guard.py").exists())
        self.assertTrue((self.sb.dest / "agents" / "orchestrator.md").exists())

    def test_legacy_install_without_manifest(self):
        self.assertOk(self.sb.install())
        (self.sb.dest / ".sdd-install-manifest.json").unlink()
        old = self.sb.dest / "agents" / "task-executor.md"
        old.write_text("an older version\n", encoding="utf-8")
        proc = self.sb.uninstall()
        self.assertOk(proc)
        self.assertTrue(old.exists(), "a file that differs from this checkout must be kept")
        self.assertFalse((self.sb.dest / "agents" / "orchestrator.md").exists())
        self.assertEqual(managed(self.sb.settings(), "PreToolUse"), [])
        self.assertIn("deny rule(s)", proc.stdout)



class PlaybooksTest(Base):
    def repo_copy(self):
        repo = self.sb.base / "repo copy"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".specs"))
        return repo

    def test_playbooks_are_installed_and_uninstalled_like_agents(self):
        repo = self.repo_copy()
        (repo / "playbooks").mkdir(exist_ok=True)
        (repo / "playbooks" / "sdd-test-playbook.md").write_text("# test playbook\n", encoding="utf-8")
        self.assertOk(self.sb.install("--no-hooks", root=repo))
        installed = self.sb.dest / "playbooks" / "sdd-test-playbook.md"
        self.assertEqual(installed.read_text(encoding="utf-8"), "# test playbook\n")
        user_file = self.sb.dest / "playbooks" / "my-notes.md"
        user_file.write_text("mine\n", encoding="utf-8")
        self.assertOk(self.sb.uninstall(root=repo))
        self.assertFalse(installed.exists())
        self.assertTrue(user_file.exists())

    def test_missing_playbooks_folder_is_skipped(self):
        repo = self.repo_copy()
        shutil.rmtree(repo / "playbooks", ignore_errors=True)
        proc = self.sb.install("--no-hooks", root=repo)
        self.assertOk(proc)
        self.assertFalse((self.sb.dest / "playbooks").exists())
        self.assertIn("No playbooks/ folder", proc.stdout)


@unittest.skipUnless(BASH, "bash not on PATH")
class ShimTest(Base):
    def run_shim(self, path_dirs, *args):
        env = self.sb.env()
        env["PATH"] = os.pathsep.join(str(d) for d in path_dirs)
        return subprocess.run([BASH, str(ROOT / "install.sh"), *args], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, env=env, timeout=300)

    def test_shim_installs_through_bash_into_a_spaced_path(self):
        env_path = os.environ.get("PATH", "").split(os.pathsep)
        proc = self.run_shim(env_path, "--yes", "--no-pre-push", "--claude-home", str(self.sb.dest))
        self.assertOk(proc)
        self.assertEqual(len(managed(self.sb.settings(), "PreToolUse")), 1)

    @unittest.skipIf(os.name == "nt", "builds a fake PATH from symlinks")
    def test_shim_reports_not_protected_without_python(self):
        fake = self.sb.base / "fakebin"
        fake.mkdir()
        os.symlink(shutil.which("dirname"), fake / "dirname")
        proc = self.run_shim([fake], "--yes", "--claude-home", str(self.sb.dest))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NOT PROTECTED", proc.stderr)
        self.assertFalse(self.sb.dest.exists())

    @unittest.skipIf(os.name == "nt", "builds a fake PATH from symlinks")
    def test_shim_skips_a_python3_stub_and_falls_back(self):
        fake = self.sb.base / "fakebin"
        fake.mkdir()
        os.symlink(shutil.which("dirname"), fake / "dirname")
        stub = fake / "python3"  # like the Microsoft Store alias: present but unusable
        stub.write_text("#!/bin/sh\nexit 9\n")
        stub.chmod(0o755)
        os.symlink(sys.executable, fake / "python")
        proc = self.run_shim([fake], "--help")
        self.assertOk(proc)
        self.assertIn("--claude-home", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
