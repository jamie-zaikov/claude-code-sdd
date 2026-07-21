#!/usr/bin/env python3
"""Structural + behavioral tests for the pre-push git hook template (Task 6, sub-task 6.4).

The hook (`ci-templates/hooks/pre-push`) is a POSIX-sh artifact, so the required "test" is a
shell-structure lint (syntax check + sentinel/reference asserts). It is also feasible to drive the
hook end-to-end here: a throwaway git repo is created in a tempdir and fed the real pre-push stdin
protocol, exercising the detection / clean / deletion / new-branch / ci.sh / fail-open paths that a
purely structural check cannot reach.

Coverage map (requirements from tasks.md Task 6: FR-17, FR-17.1, FR-16, FR-19, NFR-3):

  Structural (sub-task 6.4 items 1,2,4):
    * `bash -n`, `sh -n`, and (when present) `dash -n` parse the hook cleanly; shellcheck run when
      installed, skipped cleanly otherwise.                                    (FR-17, NFR-3)
    * the `# >>> sdd-pre-push (managed) >>>` sentinel (and its closing marker) is present. (FR-19)
    * the hook references `sdd-secret-scan.py` (the SHARED scanner CI also runs). (FR-16, NFR-3)

  Behavioral (sub-task 6.4 item 3 + strongly-recommended scenarios):
    * a simulated failing check (detected secret / failing scripts/ci.sh) exits non-zero and names
      the failing check.                                                       (FR-17.1)
    * a clean push exits 0.                                                     (FR-17)
    * a branch-deletion push (local sha all-zeros) scans nothing and exits 0.   (FR-17)
    * a new-branch push (remote sha all-zeros) with a secret in the unique commits blocks. (FR-17.1)
    * a failing `scripts/ci.sh` blocks and names build-test-lint; a passing one exits 0. (FR-17, FR-17.1)
    * a missing scanner is fail-open (warn + exit 0) — advisory layer; CI still enforces. (FR-16, NFR-3)
    * a ref name carrying shell metacharacters does not break parsing or inject a command. (FR-17)

Secret fixtures are assembled from runtime-concatenated fragments (never a real secret literal) and
their values are never printed.

Run:
    python3 -m unittest tests.test_pre_push_hook -v
    # or
    python3 tests/test_pre_push_hook.py
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Resolve the hook + shared scanner relative to this test so the suite survives both the worktree
# layout (<root>/tests/... -> <root>/ci-templates/...) and consolidation onto feat/github-agent.
ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "ci-templates" / "hooks" / "pre-push"
SCANNER_SRC = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"

SENTINEL_OPEN = "# >>> sdd-pre-push (managed) >>>"
SENTINEL_CLOSE = "# <<< sdd-pre-push (managed) <<<"

ZERO_SHA = "0" * 40

BASH = shutil.which("bash")
SH = shutil.which("sh")
DASH = shutil.which("dash")
SHELLCHECK = shutil.which("shellcheck")
GIT = shutil.which("git")


def _secret_line():
    """Build a github-token-shaped fixture line from fragments (never a real secret literal).

    Matches the scanner's `\\bgh[pousr]_[A-Za-z0-9]{36,}\\b` family. The value is only ever written
    into a file on disk; it is never printed or returned to the test report."""
    token = "ghp_" + ("A" * 36)
    return "API_TOKEN = " + token + "\n"


class HookStructureTest(unittest.TestCase):
    """Sub-task 6.4 items 1, 2, 4 — shell-structure lint, no git required."""

    @classmethod
    def setUpClass(cls):
        cls.text = HOOK.read_text(encoding="utf-8")

    def test_hook_file_exists_and_executable(self):
        # FR-19: the hook is a real, installable template file.
        self.assertTrue(HOOK.is_file(), f"hook template missing at {HOOK}")
        mode = HOOK.stat().st_mode
        self.assertTrue(mode & 0o111, "hook should be executable (a git hook must be runnable)")

    def test_bash_syntax_check(self):
        # 6.4(1): `bash -n` must parse the hook cleanly.
        if not BASH:
            self.skipTest("bash not on PATH")
        proc = subprocess.run([BASH, "-n", str(HOOK)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"bash -n reported syntax errors:\n{proc.stderr}")

    def test_sh_syntax_check(self):
        # 6.4(1): the hook is `#!/bin/sh`, so `sh -n` must also parse it cleanly.
        if not SH:
            self.skipTest("sh not on PATH")
        proc = subprocess.run([SH, "-n", str(HOOK)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"sh -n reported syntax errors:\n{proc.stderr}")

    def test_dash_syntax_check(self):
        # 6.4(1): dash is the strict POSIX sh; parsing under it guards against bashisms.
        if not DASH:
            self.skipTest("dash not on PATH")
        proc = subprocess.run([DASH, "-n", str(HOOK)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"dash -n reported syntax errors:\n{proc.stderr}")

    def test_shellcheck_clean_when_available(self):
        # 6.4(1): run shellcheck if installed; SKIP cleanly otherwise (no external-tool failure).
        if not SHELLCHECK:
            self.skipTest("shellcheck not installed")
        proc = subprocess.run(
            [SHELLCHECK, "-s", "sh", str(HOOK)], capture_output=True, text=True
        )
        self.assertEqual(
            proc.returncode, 0, f"shellcheck reported issues:\n{proc.stdout}\n{proc.stderr}"
        )

    def test_sentinel_present(self):
        # 6.4(2) / FR-19: the managed-sentinel line (and its closing marker) enable idempotent
        # install detection.
        self.assertIn(SENTINEL_OPEN, self.text, "opening managed sentinel line missing")
        self.assertIn(SENTINEL_CLOSE, self.text, "closing managed sentinel line missing")

    def test_references_shared_scanner(self):
        # 6.4(4) / FR-16 / NFR-3: the hook must run the SHARED sdd-secret-scan.py so local and CI
        # cannot drift.
        self.assertIn("sdd-secret-scan.py", self.text, "hook must reference the shared scanner")


@unittest.skipUnless(GIT, "git not available")
class HookBehaviorTest(unittest.TestCase):
    """Drive the hook through the real pre-push stdin protocol against throwaway repos."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sdd-prepush-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    # --- git helpers -------------------------------------------------------
    def _git(self, repo, *args, check=True):
        proc = subprocess.run(
            [GIT, "-C", str(repo), *args], capture_output=True, text=True
        )
        if check and proc.returncode != 0:
            self.fail(f"git {' '.join(args)} failed:\n{proc.stderr}")
        return proc

    def _init_repo(self, name):
        repo = self.tmp / name
        repo.mkdir()
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "test@example.com")
        self._git(repo, "config", "user.name", "SDD Test")
        self._git(repo, "config", "commit.gpgsign", "false")
        return repo

    def _commit_file(self, repo, relpath, content, msg):
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._git(repo, "add", relpath)
        self._git(repo, "commit", "-q", "-m", msg)
        return self._git(repo, "rev-parse", "HEAD").stdout.strip()

    def _install_scanner(self, repo):
        """Place the SHARED scanner where the hook looks first (.github/scripts/)."""
        dest = repo / ".github" / "scripts" / "sdd-secret-scan.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCANNER_SRC, dest)
        return dest

    def _write_ci_sh(self, repo, exit_code):
        ci = repo / "scripts" / "ci.sh"
        ci.parent.mkdir(parents=True, exist_ok=True)
        ci.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
        ci.chmod(0o755)
        return ci

    def _run_hook(self, repo, stdin_lines):
        """Invoke the hook exactly as git would: argv = <remote-name> <remote-url>, refs on stdin."""
        stdin = "".join(line + "\n" for line in stdin_lines)
        proc = subprocess.run(
            [SH, str(HOOK), "origin", "https://example.invalid/repo.git"],
            cwd=str(repo),
            input=stdin,
            capture_output=True,
            text=True,
        )
        return proc

    # --- FR-17.1: detected secret blocks and names the check --------------
    def test_detected_secret_blocks_normal_update(self):
        repo = self._init_repo("detect")
        self._install_scanner(repo)
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "config.env", _secret_line(), "add secret")
        # Normal update: scan the pushed range remote_sha..local_sha.
        proc = self._run_hook(
            repo, [f"refs/heads/main {head} refs/heads/main {base}"]
        )
        self.assertNotEqual(proc.returncode, 0, "a detected secret must block the push")
        self.assertIn("PUSH BLOCKED", proc.stderr)
        self.assertIn("secret-scan", proc.stderr, "the blocking message must name the failing check")

    # --- FR-17: clean push passes -----------------------------------------
    def test_clean_normal_update_passes(self):
        repo = self._init_repo("clean")
        self._install_scanner(repo)
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "notes.txt", "just some ordinary text\n", "add notes")
        proc = self._run_hook(
            repo, [f"refs/heads/main {head} refs/heads/main {base}"]
        )
        self.assertEqual(
            proc.returncode, 0, f"a clean push must pass; stderr:\n{proc.stderr}"
        )
        self.assertNotIn("PUSH BLOCKED", proc.stderr)

    # --- FR-17: branch deletion scans nothing -----------------------------
    def test_branch_deletion_skips_scan(self):
        repo = self._init_repo("delete")
        self._install_scanner(repo)
        # History deliberately contains a secret; a deletion must still not scan / block.
        self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "config.env", _secret_line(), "add secret")
        proc = self._run_hook(
            repo, [f"(delete) {ZERO_SHA} refs/heads/main {head}"]
        )
        self.assertEqual(
            proc.returncode, 0,
            f"a branch deletion (local sha all-zeros) must scan nothing and pass; stderr:\n{proc.stderr}",
        )

    # --- FR-17.1: new branch scans its unique commits and blocks ----------
    def test_new_branch_with_secret_blocks(self):
        repo = self._init_repo("newbranch")
        self._install_scanner(repo)
        self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "config.env", _secret_line(), "add secret")
        # New branch: remote sha all-zeros. No remotes configured -> empty-tree base -> full scan.
        proc = self._run_hook(
            repo, [f"refs/heads/feature {head} refs/heads/feature {ZERO_SHA}"]
        )
        self.assertNotEqual(
            proc.returncode, 0, "a new branch whose unique commits add a secret must block"
        )
        self.assertIn("secret-scan", proc.stderr)

    # --- FR-17 / FR-17.1: scripts/ci.sh failure blocks and names it -------
    def test_failing_ci_sh_blocks_and_names_build_test_lint(self):
        repo = self._init_repo("cifail")
        self._install_scanner(repo)
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "notes.txt", "clean content\n", "add notes")
        self._write_ci_sh(repo, exit_code=1)
        proc = self._run_hook(
            repo, [f"refs/heads/main {head} refs/heads/main {base}"]
        )
        self.assertNotEqual(proc.returncode, 0, "a failing scripts/ci.sh must block the push")
        self.assertIn("PUSH BLOCKED", proc.stderr)
        self.assertIn("build-test-lint", proc.stderr, "the message must name the failing check")

    def test_passing_ci_sh_allows_clean_push(self):
        repo = self._init_repo("cipass")
        self._install_scanner(repo)
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "notes.txt", "clean content\n", "add notes")
        self._write_ci_sh(repo, exit_code=0)
        proc = self._run_hook(
            repo, [f"refs/heads/main {head} refs/heads/main {base}"]
        )
        self.assertEqual(
            proc.returncode, 0, f"a passing ci.sh + clean diff must pass; stderr:\n{proc.stderr}"
        )

    # --- FR-16 / NFR-3: missing scanner is fail-open (advisory layer) -----
    def test_missing_scanner_is_fail_open(self):
        repo = self._init_repo("noscanner")
        # Deliberately DO NOT install the scanner anywhere the hook looks.
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "config.env", _secret_line(), "add secret")
        proc = self._run_hook(
            repo, [f"refs/heads/main {head} refs/heads/main {base}"]
        )
        # Advisory fail-open: warn and do NOT block (CI still enforces server-side).
        self.assertEqual(
            proc.returncode, 0,
            f"a missing local scanner must warn-and-skip, not block; stderr:\n{proc.stderr}",
        )
        self.assertIn("sdd-secret-scan.py not found", proc.stderr)
        self.assertNotIn("PUSH BLOCKED", proc.stderr)

    # --- FR-17: robustness — a hostile ref name must not inject or crash --
    def test_ref_name_with_metacharacters_is_safe(self):
        repo = self._init_repo("weirdref")
        self._install_scanner(repo)
        base = self._commit_file(repo, "README.md", "hello\n", "init")
        head = self._commit_file(repo, "notes.txt", "clean content\n", "add notes")
        marker = repo / "PWNED"
        # The ref-name fields are never used except as read-into variables; a command substitution
        # in a ref name must not execute.
        hostile = 'refs/heads/$(touch PWNED) ' + head + ' refs/heads/x ' + base
        proc = self._run_hook(repo, [hostile])
        self.assertFalse(marker.exists(), "a ref name must never be evaluated as a command")
        # Parsing must not crash; a clean diff should still pass.
        self.assertEqual(
            proc.returncode, 0, f"hostile ref name broke parsing; stderr:\n{proc.stderr}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
