#!/usr/bin/env python3
"""Unit test for the secret-guard.py GitHub-token dump-vector extension (Task 3, sub-task 3.5).

Covers FR-22, FR-22.1, FR-22.2, FR-22.3, FR-22.4, FR-5.2, NFR-2: the guard must DENY commands
that would print a GitHub token (`gh auth token`, echo/printf/printenv of GH_TOKEN/GITHUB_TOKEN)
while leaving sanctioned `gh` *use* (pr create/comment, label, api) untouched, and must route the
denial through the existing shared DENY_REASON ("use, don't read" + SECRET REQUEST guidance).

Stdlib-only (unittest + importlib), no new deps. The target module filename has a hyphen, so it is
loaded via importlib.util from a spec. The file is resolved relative to this test so it works both
in the worktree and after merge:
    <root>/tests/test_secret_guard_gh.py  ->  <root>/hooks/secret-guard.py

Run:
    python3 -m unittest tests.test_secret_guard_gh -v
    # or
    python3 tests/test_secret_guard_gh.py
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD_PATH = ROOT / "hooks" / "secret-guard.py"


def load_guard_module():
    """Load hooks/secret-guard.py as a module despite its hyphenated filename."""
    spec = importlib.util.spec_from_file_location("secret_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = load_guard_module()


class PyCompileTest(unittest.TestCase):
    """Sub-task 3.5: the modified file must still compile."""

    def test_py_compile(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(GUARD_PATH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"py_compile failed: {result.stderr}",
        )


class BlockedGithubTokenVectorsTest(unittest.TestCase):
    """FR-22, FR-22.1, FR-22.2, FR-5.2: dump vectors must be blocked."""

    # --- FR-22.1: `gh auth token` and argument variants ---
    def test_gh_auth_token_blocked(self):
        self.assertTrue(guard.is_blocked("gh auth token"))

    def test_gh_auth_token_with_hostname_arg_blocked(self):
        self.assertTrue(guard.is_blocked("gh auth token --hostname github.com"))

    def test_gh_auth_token_command_substitution_blocked(self):
        self.assertTrue(guard.is_blocked('TOKEN=$(gh auth token)'))

    # --- FR-22.2: echo/printf/printenv of GH_TOKEN / GITHUB_TOKEN ---
    def test_echo_quoted_gh_token_blocked(self):
        self.assertTrue(guard.is_blocked('echo "$GH_TOKEN"'))

    def test_echo_bare_gh_token_blocked(self):
        self.assertTrue(guard.is_blocked("echo $GH_TOKEN"))

    def test_echo_braced_github_token_blocked(self):
        self.assertTrue(guard.is_blocked("echo ${GITHUB_TOKEN}"))

    def test_printf_github_token_blocked(self):
        self.assertTrue(guard.is_blocked("printf '%s' \"$GITHUB_TOKEN\""))

    def test_printenv_github_token_blocked(self):
        self.assertTrue(guard.is_blocked("printenv GITHUB_TOKEN"))


class AllowedGithubUseVectorsTest(unittest.TestCase):
    """FR-22.4: sanctioned `gh` use where the token value never enters context is NOT blocked."""

    def test_gh_pr_create_allowed(self):
        self.assertFalse(guard.is_blocked('gh pr create --title "T" --body "B"'))

    def test_gh_pr_comment_allowed(self):
        self.assertFalse(guard.is_blocked('gh pr comment 42 --body "verdict"'))

    def test_gh_label_add_allowed(self):
        self.assertFalse(guard.is_blocked("gh label add ready-to-merge"))

    def test_gh_label_create_allowed(self):
        self.assertFalse(guard.is_blocked("gh label create blocked:security"))

    def test_gh_api_allowed(self):
        self.assertFalse(guard.is_blocked("gh api repos/o/r/pulls -X POST"))

    def test_gh_auth_status_allowed(self):
        """`gh auth status` reports presence, does not print the token."""
        self.assertFalse(guard.is_blocked("gh auth status"))

    def test_gh_auth_login_allowed(self):
        self.assertFalse(guard.is_blocked("gh auth login"))

    def test_gh_use_vector_referencing_var_allowed(self):
        """A `gh` command that merely references the var (use vector) is not the print vector."""
        self.assertFalse(
            guard.is_blocked('gh pr create --body "$GITHUB_TOKEN note"')
        )


class DenyReasonTest(unittest.TestCase):
    """FR-22.3, NFR-2: the denial routes through the shared DENY_REASON message."""

    def test_deny_reason_has_use_dont_read_and_secret_request_guidance(self):
        reason = guard.DENY_REASON
        # Key phrases (not a brittle full-string copy): the "use, don't read" guidance and the
        # SECRET REQUEST escalation must both be present.
        self.assertIn("SECRET REQUEST", reason)
        self.assertIn("USE it without reading it", reason)
        self.assertIn("env-var name", reason)

    def test_emitted_decision_uses_shared_deny_reason(self):
        """main() must emit a deny decision whose reason IS the shared DENY_REASON."""
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "gh auth token"}}
        )
        result = subprocess.run(
            [sys.executable, str(GUARD_PATH)],
            input=payload,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"guard exited non-zero: {result.stderr}")
        self.assertTrue(result.stdout.strip(), "guard emitted no decision for a blocked command")
        decision = json.loads(result.stdout)
        out = decision["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertEqual(
            out["permissionDecisionReason"],
            guard.DENY_REASON,
            "emitted reason must be the shared DENY_REASON, not a bespoke message",
        )

    def test_allowed_command_emits_no_decision(self):
        """A sanctioned use vector produces no deny output (guard stays silent)."""
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --body b"}}
        )
        result = subprocess.run(
            [sys.executable, str(GUARD_PATH)],
            input=payload,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "", "guard should not emit a decision for allowed use")


class BaseBehaviorRegressionTest(unittest.TestCase):
    """Confirm the pre-existing guard behaviour is unchanged by the extension."""

    def test_bare_printenv_still_blocked(self):
        self.assertTrue(guard.is_blocked("printenv"))

    def test_set_x_still_blocked(self):
        self.assertTrue(guard.is_blocked("set -x"))

    def test_cat_dotenv_still_blocked(self):
        self.assertTrue(guard.is_blocked("cat .env"))

    def test_plain_command_still_allowed(self):
        self.assertFalse(guard.is_blocked("ls -la"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
