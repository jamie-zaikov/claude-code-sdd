#!/usr/bin/env python3
"""secret-guard.py: inert text (quoted cat/tee here-doc bodies, grep/rg search patterns).

The ALLOWED cases are the shapes of real false blocks taken from session logs (2026-10-13 ..
2026-11-05, arc-lab-automation-platform): reviewer summaries written with a quoted here-doc,
security-word searches over a diff, a `--head-sha` option. Each one was blocked before this
change. The BLOCKED cases are real secret-store reads; each must stay blocked, and several
are built to catch a wrong parse (an option that takes a value, a permuted `-e`, a pattern
that runs a command, a here-doc body fed to a shell).

Run:  python3 -m unittest tests.test_secret_guard_inert_text -v
"""

import importlib.util
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().parent.parent / "hooks" / "secret-guard.py"
_spec = importlib.util.spec_from_file_location("secret_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

SUMMARY = (
    "cd /repo && cat > .specs/features/f/spec-memory/status/FR-security-reviewer-a1.md <<'EOF'\n"
    "## Security review\n"
    "The guard stopped a search for words such as credentials, .env, id_rsa and *.pem.\n"
    "No file under ~/.aws or ~/.ssh was read; printenv and set -x were not run.\n"
    "EOF\n"
    "python3 ~/.claude/tools/sdd-status.py set --feature-dir .specs/features/f --agent "
    "security-reviewer --task FR --attempt 1 --state done --step end"
)

ALLOWED = {
    # Block 1 of 2026-11-05: a pattern alternation with `|env|` and `cred` inside quotes.
    "security words over a diff": (
        "cd /repo && git diff ec9eb2b...HEAD -- ':!.specs' | grep -E '^-\\s*def test_' "
        "| grep -iE 'secret|token|cred|auth|env|leak|password|key'"
    ),
    "summary here-doc": SUMMARY,
    "summary here-doc, double-quoted delimiter": 'cat > s.md <<"EOF"\nno .env read\nEOF',
    "summary here-doc, tee": "tee -a s.md > /dev/null <<'EOF'\nthe credentials file\nEOF",
    "summary here-doc after an assignment": (
        "S=spec-memory/status/t-a1.md; cat > \"$S\" <<'EOF'\n"
        "strings (not real credentials) in tests\nEOF"
    ),
    "summary then a status record with variables": (
        "W=.specs/features/f; S=$W/spec-memory/status/9-security-reviewer-a1.md\n"
        "cat > \"$W/spec-memory/status/9-security-reviewer-a1.md\" <<'EOF'\n"
        "the credentials file was not read\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py set --feature-dir $W --agent security-reviewer "
        "--task 9 --attempt 1 --state done --step end --verdict PASS --summary-path \"$S\""
    ),
    "summary then the status record that names it": (
        "cat > st/x-a1.md <<'EOF'\nno credentials file read\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py set --state done --summary-path st/x-a1.md"
    ),
    "pattern with an escape that Bash keeps": 'grep -n "\\.env\\b" .gitignore',
    "pattern names a secret file": 'grep -rn "cd-services.auto.tfvars" scripts/cd.py .github',
    "-e patterns name secret files": (
        "git grep -n -e resolve_image -e image_digest.auto.tfvars -- ':!.specs'"
    ),
    "pattern is an escaped .env": 'grep -n "\\.env" .gitignore',
    "rg pattern word": "rg -n -i 'credentials|kubeconfig' src/",
    "option that contains a tool name": (
        "python3 tools/cd.py route --head-sha abc123 --tfvars-out /tmp/plan.auto.tfvars"
    ),
}

BLOCKED = {
    "cat of a secret store": "cat ~/.aws/credentials",
    "grep in .env": "grep TOKEN .env",
    "grep, secret file after a known option": "grep -i -n TOKEN .env",
    "grep, attached -A value": "grep -A2 TOKEN .env.local",
    "grep, -A value then pattern then file": "grep -A 2 TOKEN ~/.ssh/config",
    "grep, permuted -e makes the first operand a file": "grep .env -e TOKEN",
    "grep, -e then secret file": "grep -e TOKEN -- id_rsa",
    "grep, pattern file": "grep -f patterns.txt .env",
    "grep, -f with a secret file": "grep -f .env notes.txt",
    "grep, unknown option keeps full check (BSD -C arity)": "grep -C TOKEN .env",
    "grep, unknown option keeps full check (GNU -T)": "grep -T TOKEN .env",
    "grep, --include value names a store": "grep -r --include .env TOKEN .",
    "grep, --include= value names a store": "grep -r --include=id_rsa BEGIN .",
    "grep, input redirect": "grep TOKEN < .env",
    "grep, pattern runs a command": 'grep "$(cat .env)" notes.txt',
    "grep, backtick pattern": "grep `cat .env` notes.txt",
    "grep inside bash -c": 'bash -c "grep credentials .env"',
    "grep then a second command": "grep x notes.txt; cat .env",
    "grep, pattern then newline then a dump": "grep credentials notes.txt\ncat ~/.aws/credentials",
    "rg, -E takes a value": "rg -E .env TOKEN ~/.aws/",
    "rg, -r takes a value": "rg -r X TOKEN .env",
    "rg --files lists a store": "rg --files ~/.ssh/",
    "env word outside a pattern": "env | grep TOKEN",
    "here-doc fed to bash": "bash <<'EOF'\ncat ~/.aws/credentials\nEOF",
    "here-doc fed to python": "python3 - <<'EOF'\nprint(open('x').read())  # cat .env\nEOF",
    "cat here-doc piped to bash": "cat <<'EOF' | bash\ncat ~/.aws/credentials\nEOF",
    "cat here-doc inside command substitution": (
        "bash -c \"$(cat <<'EOF'\ncat ~/.aws/credentials\nEOF\n)\""
    ),
    "unquoted here-doc expands": "cat > s.md <<EOF\n$(cat ~/.aws/credentials)\nEOF",
    "here-doc with no terminator": "cat > s.md <<'EOF'\ncat ~/.aws/credentials",
    "secret read on the here-doc line": "cat ~/.aws/credentials - <<'EOF'\nx\nEOF",
    "command after the here-doc": "cat > s.md <<'EOF'\nok\nEOF\ncat .env",
    "two here-docs on one line": "cat <<'A' <<'B'\nx\nA\ncat .env\nB",
    "git cat-file of a committed store": "git cat-file -p HEAD:.env",
    "script here-doc that opens a store, then runs": (
        "cat > /tmp/p.py <<'EOF'\nprint(open('/repo/.env').read())\nEOF\npython3 /tmp/p.py"
    ),
    "script here-doc through a variable": (
        "P=/tmp/p.sh; cat > \"$P\" <<'EOF'\ncat ~/.aws/credentials\nEOF\nbash \"$P\""
    ),
    "here-doc to a file with no extension": "cat > /tmp/run <<'EOF'\ncat .env\nEOF",
    "variable target set twice": (
        "S=a.md; S=b.sh; cat > \"$S\" <<'EOF'\ncat .env\nEOF"
    ),
    "tee to a script": "tee /tmp/x.sh <<'EOF'\ncat ~/.aws/credentials\nEOF",
    "cat here-doc to stdout": "cat <<'EOF'\ncat ~/.aws/credentials\nEOF",
    "printenv after a here-doc": "cat > s.md <<'EOF'\nok\nEOF\nx; printenv",
    # Review round 1 (2026-11-05): each was old True / new False before its fix.
    "escaped quote inside a double-quoted pattern": 'grep "\\"*" ~/.aws/credentials x\\"',
    "POSIXLY_CORRECT: -e after an operand is a file": (
        'export POSIXLY_CORRECT=1; grep "" -e ~/.aws/credentials'
    ),
    "option after the first operand": "grep TOKEN -A 1 .env",
    "here-doc operator inside a string": (
        "echo \"x; cat > a.md <<'EOF'\"\ncat ~/.aws/credentials\nEOF"
    ),
    "here-doc operator inside a comment": (
        "true # ; cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF"
    ),
    "data-named file run by bash": "cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF\nbash a.md",
    "data-named file run directly": (
        "cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF\nchmod +x a.md; ./a.md"
    ),
    "data-named file sourced": "cat > /tmp/a.md <<'EOF'\ncat .env\nEOF\n. /tmp/a.md",
    "variable target run by bash": (
        "S=/tmp/a.md; cat > \"$S\" <<'EOF'\ncat .env\nEOF\nbash \"$S\""
    ),
    "assignment after the here-doc": "cat > \"$S\" <<'EOF'\ncat .env\nEOF\nS=a.md",
    "assignment only inside a string": (
        "echo \"S=a.md\"; cat > \"$S\" <<'EOF'\ncat .env\nEOF"
    ),
    # Review round 2 (2026-11-05): each was old True / new False before its fix.
    "ANSI-C quote shifts the grep words": "grep -v --exclude=$'a\\'b' x\\' ~/.aws/credentials",
    "double quote nested in $( ) before a here-doc": (
        "echo \"$(echo \"; cat > a.md <<'EOF'\")\"\ncat ~/.aws/credentials\nEOF"
    ),
    "run on the operator line": "cat > a.md <<'EOF' && bash a.md\ncat ~/.aws/credentials\nEOF",
    "run through an input redirect": "cat > a.md <<'EOF'\ncat .env\nEOF\nbash < a.md",
    "run through a pipe": "cat > a.md <<'EOF'\ncat .env\nEOF\ncat a.md | bash",
    "run through bash -c": "cat > a.md <<'EOF'\ncat .env\nEOF\nbash -c \"$(cat a.md)\"",
    "variable target run by its value": (
        "S=a.md; cat > \"$S\" <<'EOF'\ncat .env\nEOF\nbash a.md"
    ),
    "variable extended with +=": (
        "S=a.md; S+=.sh; cat > \"$S\" <<'EOF'\ncat .env\nEOF\nbash a.md.sh"
    ),
    "prefix assignment": "S=a.md cat > \"$S\" <<'EOF'\ncat .env\nEOF",
    # Review round 3 (2026-11-05): each was old True / new False before its fix.
    "summary-path argument swallows a run": (
        "cat > a.md <<'EOF'\ncat .env\nEOF\ntrue --summary-path x;sh<a.md"
    ),
    "summary-path is the file sh runs": (
        "cat > a.md <<'EOF'\ncat .env\nEOF\nsh -c '. \"$1\"' --summary-path a.md"
    ),
    "a second variable names the file": (
        "F=a.md; cat > a.md <<'EOF'\ncat .env\nEOF\nbash \"$F\""
    ),
    "braced variable": "S=a.md; cat > \"$S\" <<'EOF'\ncat .env\nEOF\nbash \"${S}\"",
    "glob runs the file": "cat > a.md <<'EOF'\ncat .env\nEOF\nbash ./*.md",
    "quoted letters in the name": "cat > a.md <<'EOF'\ncat .env\nEOF\nbash a.m''d",
    "other letter case": "cat > a.md <<'EOF'\ncat .env\nEOF\nbash A.MD",
    "status command with a substitution": (
        "cat > a.md <<'EOF'\ncat .env\nEOF\npython3 sdd-status.py set --step \"$(bash a.md)\""
    ),
    # Review round 4 (2026-11-05): each was old True / new False before its fix.
    "trap runs the file at exit": (
        "trap 'bash a.md' EXIT; cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF"
    ),
    "background job runs the file": (
        "(sleep 1; bash a.md) & cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py set --state done"
    ),
    "earlier line runs a job": (
        "nohup sh -c 'sleep 1; bash a.md' >/dev/null\ncat > a.md <<'EOF'\ncat .env\nEOF"
    ),
    "status tool of the same name elsewhere": (
        "cat > a.md <<'EOF'\ncat ~/.aws/credentials\nEOF\npython3 /tmp/sdd-status.py a.md"
    ),
    "owner after a pipe": "true | cat > a.md <<'EOF'\ncat .env\nEOF",
    "HOME moves the status tool": (
        "HOME=/tmp/h; cat > a.md <<'EOF'\ncat .env\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py a.md"
    ),
    "PATH picks another python3": (
        "PATH=/tmp/p:/usr/bin; cat > a.md <<'EOF'\ncat .env\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py a.md"
    ),
    # Review round 5 (2026-11-05): non-blocking, fixed anyway.
    "zsh path array": (
        "path=/tmp/x; cat > a.md <<'EOF'\ncat .env\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py set"
    ),
    "status tool in a shared folder": (
        "cat > a.md <<'EOF'\ncat .env\nEOF\npython3 /Users/Shared/.claude/tools/sdd-status.py a.md"
    ),
    "PYTHONPATH changes an import": (
        "PYTHONPATH=/tmp/p; cat > a.md <<'EOF'\ncat .env\nEOF\n"
        "python3 ~/.claude/tools/sdd-status.py a.md"
    ),
    "ANSI-C quote before a here-doc": "echo $'\\''; cat > a.md <<'EOF'\ncat .env\nEOF",
}


class InertTextAllowed(unittest.TestCase):
    def test_false_positive_shapes_are_allowed(self):
        for name, cmd in ALLOWED.items():
            with self.subTest(name):
                self.assertFalse(guard.is_blocked(cmd), cmd)


class SecretReadsStayBlocked(unittest.TestCase):
    def test_real_reads_are_blocked(self):
        for name, cmd in BLOCKED.items():
            with self.subTest(name):
                self.assertTrue(guard.is_blocked(cmd), cmd)


class NoCatastrophicBacktracking(unittest.TestCase):
    """The hook runs before EVERY shell command: a regex that backtracks exponentially on a
    long word would hang the session (2026-11-05: `(?:[...]+|...)+` did on the log corpus)."""

    def test_long_hostile_words_finish_fast(self):
        import time

        word = "a" * 4000 + "$B" + "/c" * 2000 + "!"
        shapes = [
            "cat > a.md <<'EOF'\nx\nEOF\npython3 ~/.claude/tools/sdd-status.py set " + word,
            "cd " + word + " && cat > a.md <<'EOF'\nx\nEOF",
            "S=" + word + "; cat > \"$S\" <<'EOF'\nx\nEOF",
            "grep -e " + word + " notes.txt",
        ]
        for cmd in shapes:
            start = time.monotonic()
            guard.is_blocked(cmd)
            self.assertLess(time.monotonic() - start, 1.0, cmd[:60])


class HelperModuleFailsClosed(unittest.TestCase):
    """The helpers live in hooks/secret_guard_inert.py. A guard installed without them must
    keep the full old check (strict), never crash open."""

    @staticmethod
    def _decision(guard_file, command):
        """Run the guard the way the harness does: a fresh process, JSON on stdin."""
        import json
        import subprocess
        import sys

        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        out = subprocess.run([sys.executable, "-I", str(guard_file)], input=payload,
                             capture_output=True, text=True, check=True).stdout
        return "deny" in out

    def test_guard_without_helper_is_strict(self):
        import shutil
        import tempfile

        self.assertFalse(self._decision(GUARD_PATH, SUMMARY))  # with the helper: inert
        with tempfile.TemporaryDirectory() as tmp:
            lone = Path(tmp) / "secret-guard.py"
            shutil.copy2(GUARD_PATH, lone)
            self.assertTrue(self._decision(lone, SUMMARY))
            self.assertTrue(self._decision(lone, ALLOWED["security words over a diff"]))
            self.assertFalse(self._decision(lone, "ls -la"))
            self.assertFalse((Path(tmp) / "__pycache__").exists())

    def test_helper_crash_checks_the_raw_command(self):
        from unittest import mock

        def boom(_command):
            raise RuntimeError("parser bug")

        with mock.patch.object(guard, "_without_inert_text", boom):
            self.assertTrue(guard.is_blocked(SUMMARY))
            self.assertTrue(guard.is_blocked(BLOCKED["grep in .env"]))
            self.assertFalse(guard.is_blocked("ls -la"))

    def test_installer_copies_the_helper(self):
        import sys
        sys.path.insert(0, str(GUARD_PATH.parent.parent))
        from sdd_install import settings

        self.assertIn("secret_guard_inert.py", settings.HOOK_SUPPORT)
        for name in settings.HOOK_SUPPORT:
            self.assertTrue((GUARD_PATH.parent / name).is_file(), name)
        install = (GUARD_PATH.parent.parent / "install.py").read_text()
        self.assertIn("for name in sdd_settings.HOOK_SUPPORT:", install)


class BriefsPinTheHookBlockRule(unittest.TestCase):
    """Every agent that writes a status summary records a hook block instead of a stale
    `working` state (2026-11-05: a blocked summary write left the record live-looking)."""

    def test_writers_record_a_hook_block(self):
        import sys
        sys.path.insert(0, str(GUARD_PATH.parent.parent / "tests"))
        from prose import near

        agents = sorted((GUARD_PATH.parent.parent / "agents").glob("*.md"))
        writers = [p for p in agents if "(`cat > <summaryPath> <<'EOF'`)" in p.read_text()]
        self.assertGreaterEqual(len(writers), 11)
        for path in writers:
            text = path.read_text()
            with self.subTest(path.name):
                self.assertTrue(near(text, r"summary path ends in `\.md`", r"as data"))
                self.assertTrue(near(text, r"If a hook\s+blocks a command",
                                     r"--state blocked --blocked-on \"hook block\"",
                                     r"possible false positive"))

    def test_security_reviewer_searches_with_a_pattern(self):
        import sys
        sys.path.insert(0, str(GUARD_PATH.parent.parent / "tests"))
        from prose import near

        text = (GUARD_PATH.parent.parent / "agents" / "security-reviewer.md").read_text()
        self.assertTrue(near(text, r"word-list search", r"Search only the diff or tracked files",
                             r"untracked `\.env` files"))
        self.assertTrue(near(text, r"pattern first, before any file",
                             r"checks every file\s+the command reads"))


if __name__ == "__main__":
    unittest.main()
