#!/usr/bin/env python3
"""End-to-end sandbox tests for install.sh's SDD CI pre-push hook block (Task 7, sub-task 7.4).

Covers FR-18 (prompted, idempotent, skippable hook install consistent with the secret-handling
opt-in), FR-18.1 (decline skips cleanly, no error), FR-21 (dogfood: install the hook into this
repo + stage templates under ~/.claude/ for /sdd-init), and NFR-5 (idempotent, non-destructive).

APPROACH — real install.sh, sandboxed (NOT an extracted snippet).
    We drive the *actual* installer end-to-end so the tested bytes are the shipped bytes, but every
    write is redirected away from the real machine:
      * HOME is pointed at a throwaway tempdir, so CLAUDE_HOME=$HOME/.claude is disposable;
      * SCRIPT_DIR is a throwaway copy of the repo files (install.sh, CLAUDE.md, agents/, commands/,
        hooks/, ci-templates/) under a tempdir, git-init'd per scenario so the repo-install path
        resolves inside the sandbox and never touches the real repo;
      * a fake `claude` shim is prepended to PATH so `command -v claude` always succeeds — this
        removes the conditional "Continue anyway?" preflight prompt and makes the prompt order
        deterministic: [secret-handling, pre-push];
      * CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 suppresses the shell-profile prompt;
      * answers are fed on stdin. We always DECLINE the (unrelated) secret-handling prompt so no
        real profile / settings.json is edited, then answer the pre-push prompt per scenario.
    The real ${HOME} is never used: HOME is overridden for every run that could write.

Run:
    python3 -m unittest tests.test_install_pre_push_hook -v
    # or
    python3 tests/test_install_pre_push_hook.py
"""

import filecmp
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

# Resolve the repo root relative to this test so it survives both the worktree layout
#   <root>/tests/test_install_pre_push_hook.py -> <root>/install.sh
# and later consolidation onto feat/github-agent.
ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
HOOK_SRC = ROOT / "ci-templates" / "hooks" / "pre-push"
SCANNER_SRC = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"

SENTINEL = "# >>> sdd-pre-push (managed) >>>"
# The template legitimately contains the sentinel string more than once (the marker line plus a
# quoted reference in its explanatory comment). "No duplication" therefore means the installed hook
# carries the SAME number of sentinels as the template — not that install.sh appended a second block.
TEMPLATE_SENTINEL_COUNT = HOOK_SRC.read_text().count(SENTINEL)

GIT = shutil.which("git")
BASH = shutil.which("bash") or "/bin/bash"
SHELLCHECK = shutil.which("shellcheck")

# What install.sh reads out of SCRIPT_DIR. Copied into each sandbox so the run is faithful.
COPY_DIRS = ("agents", "commands", "hooks", "ci-templates")
COPY_FILES = ("install.sh", "CLAUDE.md")


def is_executable(path: Path) -> bool:
    return bool(os.stat(path).st_mode & 0o111)


class InstallerSandbox:
    """A disposable SCRIPT_DIR + HOME that runs the real install.sh with injected answers."""

    def __init__(self, base: Path, git_repo: bool = True):
        self.base = base
        self.git_repo = git_repo
        self.script_dir = base / "repo"
        self.home = base / "home"
        self.fakebin = base / "fakebin"
        self.script_dir.mkdir(parents=True)
        self.home.mkdir(parents=True)
        self.fakebin.mkdir(parents=True)

        for name in COPY_FILES:
            shutil.copy2(ROOT / name, self.script_dir / name)
        for name in COPY_DIRS:
            src = ROOT / name
            if src.is_dir():
                shutil.copytree(src, self.script_dir / name)

        # Fake `claude` so `command -v claude` succeeds -> deterministic prompt order.
        shim = self.fakebin / "claude"
        shim.write_text("#!/bin/sh\necho 'fake-claude 0.0.0'\n")
        shim.chmod(0o755)

        if git_repo:
            subprocess.run(
                [GIT, "init", "-q", str(self.script_dir)],
                check=True,
                capture_output=True,
            )

    @property
    def hook_dest(self) -> Path:
        # A fresh `git init` resolves --git-path hooks to .git/hooks (relative to SCRIPT_DIR).
        return self.script_dir / ".git" / "hooks" / "pre-push"

    @property
    def staged_hook(self) -> Path:
        return self.home / ".claude" / "ci-templates" / "hooks" / "pre-push"

    @property
    def staged_scanner(self) -> Path:
        return self.home / ".claude" / "ci-templates" / "scripts" / "sdd-secret-scan.py"

    def preexisting_hook(self, content: str):
        """Drop a pre-push hook into the resolved hooks dir before running the installer."""
        dest = self.hook_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        dest.chmod(0o755)

    def run(self, answers: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
        env["PATH"] = str(self.fakebin) + os.pathsep + env.get("PATH", "")
        if not self.git_repo:
            # Prevent git from walking up into any ancestor repo of the tempdir.
            env["GIT_CEILING_DIRECTORIES"] = str(self.base)
        return subprocess.run(
            [BASH, str(self.script_dir / "install.sh")],
            input=answers,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.script_dir),
        )


class SandboxTestBase(unittest.TestCase):
    def make_sandbox(self, git_repo: bool = True) -> InstallerSandbox:
        base = Path(tempfile.mkdtemp(prefix="sdd-install-test-"))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        return InstallerSandbox(base, git_repo=git_repo)


# --------------------------------------------------------------------------
# 7.4(1): syntax / shellcheck
# --------------------------------------------------------------------------
class SyntaxTest(unittest.TestCase):
    def test_bash_n_passes(self):
        """`bash -n install.sh` parses without error."""
        result = subprocess.run(
            [BASH, "-n", str(INSTALL_SH)], capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode,
            0,
            f"bash -n reported a syntax error:\n{result.stderr}",
        )

    @unittest.skipUnless(SHELLCHECK, "shellcheck not on PATH — external-tool check skipped")
    def test_shellcheck_clean(self):
        """If shellcheck is available, install.sh lints with no errors; otherwise SKIP."""
        result = subprocess.run(
            [SHELLCHECK, "-S", "error", str(INSTALL_SH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"shellcheck reported errors:\n{result.stdout}\n{result.stderr}",
        )


# --------------------------------------------------------------------------
# Fresh install + ~/.claude staging (FR-18, FR-21)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class FreshInstallTest(SandboxTestBase):
    def setUp(self):
        self.sb = self.make_sandbox(git_repo=True)
        # decline secret-handling, accept pre-push.
        self.proc = self.sb.run("n\ny\n")

    def test_run_succeeds(self):
        self.assertEqual(
            self.proc.returncode, 0, f"installer failed:\n{self.proc.stdout}\n{self.proc.stderr}"
        )

    def test_hook_installed_into_repo(self):
        self.assertTrue(self.sb.hook_dest.exists(), "pre-push hook was not installed into the repo")
        self.assertIn("Pre-push hook installed", self.proc.stdout)

    def test_installed_hook_matches_template(self):
        self.assertTrue(
            filecmp.cmp(self.sb.hook_dest, HOOK_SRC, shallow=False),
            "installed hook content does not match the template",
        )

    def test_installed_hook_is_executable(self):
        self.assertTrue(
            is_executable(self.sb.hook_dest),
            "installed hook is not executable (exec bit not preserved)",
        )

    def test_staged_hook_under_claude_home(self):
        self.assertTrue(self.sb.staged_hook.exists(), "hook not staged under ~/.claude/ci-templates")
        self.assertTrue(
            filecmp.cmp(self.sb.staged_hook, HOOK_SRC, shallow=False),
            "staged hook content does not match the template",
        )
        self.assertTrue(
            is_executable(self.sb.staged_hook),
            "staged hook is not executable (exec bit not preserved)",
        )

    def test_staged_scanner_under_claude_home(self):
        self.assertTrue(
            self.sb.staged_scanner.exists(), "scanner not staged under ~/.claude/ci-templates/scripts"
        )
        self.assertTrue(
            filecmp.cmp(self.sb.staged_scanner, SCANNER_SRC, shallow=False),
            "staged scanner content does not match the source",
        )
        self.assertIn("Templates staged in", self.proc.stdout)


# --------------------------------------------------------------------------
# 7.4(2): idempotence (NFR-5)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class IdempotenceTest(SandboxTestBase):
    def test_second_run_unchanged_no_duplication(self):
        sb = self.make_sandbox(git_repo=True)

        first = sb.run("n\ny\n")
        self.assertEqual(first.returncode, 0, f"first run failed:\n{first.stderr}")
        self.assertIn("Pre-push hook installed", first.stdout)
        after_first = sb.hook_dest.read_text()

        second = sb.run("n\ny\n")
        self.assertEqual(second.returncode, 0, f"second run failed:\n{second.stderr}")
        # Second run detects its own sentinel + identical content -> reports unchanged.
        self.assertIn("unchanged", second.stdout.lower())
        self.assertNotIn("Pre-push hook installed", second.stdout)

        after_second = sb.hook_dest.read_text()
        self.assertEqual(after_first, after_second, "hook content changed on the idempotent re-run")
        # No duplication: the installer did not append a second managed block.
        self.assertEqual(
            after_second.count(SENTINEL),
            TEMPLATE_SENTINEL_COUNT,
            "managed block duplicated after re-run",
        )
        self.assertTrue(
            filecmp.cmp(sb.hook_dest, HOOK_SRC, shallow=False),
            "hook drifted from the template after re-run",
        )


# --------------------------------------------------------------------------
# 7.4(3): decline path skips cleanly (FR-18.1)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class DeclinePathTest(SandboxTestBase):
    def setUp(self):
        self.sb = self.make_sandbox(git_repo=True)
        # decline secret-handling AND decline pre-push.
        self.proc = self.sb.run("n\nn\n")

    def test_run_succeeds(self):
        self.assertEqual(
            self.proc.returncode, 0, f"installer errored on decline:\n{self.proc.stderr}"
        )

    def test_no_hook_installed(self):
        self.assertFalse(self.sb.hook_dest.exists(), "hook installed despite declining")

    def test_reports_skip(self):
        self.assertIn("Pre-push hook skipped", self.proc.stdout)

    def test_nothing_staged_on_decline(self):
        # Staging happens only on opt-in; declining must not create the global templates.
        self.assertFalse(
            self.sb.staged_hook.exists(), "templates staged under ~/.claude despite declining"
        )


# --------------------------------------------------------------------------
# 7.4(4): pre-existing non-sentinel user hook is NOT overwritten (FR-18, NFR-5)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class NonSentinelHookPreservedTest(SandboxTestBase):
    USER_HOOK = "#!/bin/sh\n# my very own hook, do not touch\necho custom-user-hook\nexit 0\n"

    def setUp(self):
        self.sb = self.make_sandbox(git_repo=True)
        self.sb.preexisting_hook(self.USER_HOOK)
        self.proc = self.sb.run("n\ny\n")

    def test_run_succeeds(self):
        self.assertEqual(
            self.proc.returncode, 0, f"installer errored:\n{self.proc.stderr}"
        )

    def test_user_hook_content_preserved(self):
        self.assertEqual(
            self.sb.hook_dest.read_text(),
            self.USER_HOOK,
            "a pre-existing non-SDD user hook was overwritten",
        )
        self.assertNotIn(SENTINEL, self.sb.hook_dest.read_text())

    def test_warning_emitted(self):
        self.assertIn("not overwriting", self.proc.stdout.lower())

    def test_templates_still_staged(self):
        # Even when the repo hook is left alone, the global templates are still staged on opt-in.
        self.assertTrue(
            self.sb.staged_hook.exists(),
            "templates should still stage under ~/.claude even when the repo hook is preserved",
        )


# --------------------------------------------------------------------------
# Bonus: SDD-sentinel hook that has drifted is updated back to the template (NFR-5)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class SentinelDriftUpdatedTest(SandboxTestBase):
    DRIFTED = (
        "#!/bin/sh\n"
        f"{SENTINEL}\n"
        "# an older, drifted SDD-managed hook\n"
        "exit 0\n"
        "# <<< sdd-pre-push (managed) <<<\n"
    )

    def setUp(self):
        self.sb = self.make_sandbox(git_repo=True)
        self.sb.preexisting_hook(self.DRIFTED)
        self.proc = self.sb.run("n\ny\n")

    def test_run_succeeds(self):
        self.assertEqual(self.proc.returncode, 0, f"installer errored:\n{self.proc.stderr}")

    def test_hook_updated_to_template(self):
        self.assertIn("updated", self.proc.stdout.lower())
        self.assertTrue(
            filecmp.cmp(self.sb.hook_dest, HOOK_SRC, shallow=False),
            "drifted SDD hook was not updated back to the template",
        )
        self.assertEqual(
            self.sb.hook_dest.read_text().count(SENTINEL),
            TEMPLATE_SENTINEL_COUNT,
            "managed block duplicated after drift update",
        )


# --------------------------------------------------------------------------
# Bonus: not-a-git-repo warns and skips the repo install without aborting (NFR-5)
# --------------------------------------------------------------------------
@unittest.skipUnless(GIT, "git not available")
class NotAGitRepoTest(SandboxTestBase):
    def setUp(self):
        self.sb = self.make_sandbox(git_repo=False)
        self.proc = self.sb.run("n\ny\n")

    def test_run_succeeds(self):
        self.assertEqual(
            self.proc.returncode,
            0,
            f"installer aborted in a non-git dir (set -e leak?):\n{self.proc.stderr}",
        )

    def test_warns_not_a_git_repo(self):
        self.assertIn("not a git repository", self.proc.stdout.lower())

    def test_no_repo_hook_but_templates_still_staged(self):
        self.assertFalse(self.sb.hook_dest.exists(), "hook installed despite not being a git repo")
        # (b) staging into ~/.claude runs on opt-in even when the repo install is skipped.
        self.assertTrue(
            self.sb.staged_hook.exists(),
            "global templates should still stage even when the repo is not a git repo",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
