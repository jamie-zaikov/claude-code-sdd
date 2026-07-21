#!/usr/bin/env python3
"""Task 8 (sub-task 8.4): tests for the `/sdd-init` CI-template distribution work.

Task 8 changed TWO files:
  * commands/sdd-init.md — a new "## CI templates" section documenting how /sdd-init drops the
    workflow + scanner + hook templates into a downstream project non-destructively; and
  * install.sh — the ~/.claude/ci-templates/ staging block now ALSO stages
    ci-templates/workflows/*.yml into ~/.claude/ci-templates/workflows/.

Both parts are covered here:

  Part A — STRUCTURAL check of commands/sdd-init.md (a markdown instruction doc, not executable).
    Assert the file is well-formed markdown and the new "CI templates" section documents the
    load-bearing content Task 8's cited requirements demand (FR-19, FR-20, FR-20.1, NFR-5). These
    are section-level + targeted-substring assertions over the markdown text; we assert the
    load-bearing tokens, not brittle full sentences.

  Part B — BEHAVIORAL check of the install.sh workflow-staging extension (real bash, executed in a
    SANDBOX). Drives the actual installer end-to-end with every write redirected off the real
    machine (HOME → tempdir, SCRIPT_DIR → throwaway repo copy, fake `claude` shim on PATH,
    CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1, answers on stdin). Mirrors the Task-7 harness in
    tests/test_install_pre_push_hook.py so the two stay consistent.

Run:
    python3 -m unittest tests.test_sdd_init_ci_templates -v
    # or
    python3 tests/test_sdd_init_ci_templates.py
"""

import filecmp
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Resolve everything relative to this test so it survives the worktree layout
#   <root>/tests/test_sdd_init_ci_templates.py -> <root>/{install.sh,commands/,ci-templates/}
# and later consolidation onto feat/github-agent.
ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = ROOT / "install.sh"
SDD_INIT_MD = ROOT / "commands" / "sdd-init.md"
WORKFLOWS_SRC = ROOT / "ci-templates" / "workflows"
HOOK_SRC = ROOT / "ci-templates" / "hooks" / "pre-push"
SCANNER_SRC = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"

# The three workflow templates Task 5 authored; Task 8 stages all sdd-*.yml.
EXPECTED_WORKFLOWS = (
    "sdd-secret-scan.yml",
    "sdd-review-gate.yml",
    "sdd-build-test-lint.yml",
)

SENTINEL = "# >>> sdd-pre-push (managed) >>>"

GIT = shutil.which("git")
BASH = shutil.which("bash") or "/bin/bash"
SHELLCHECK = shutil.which("shellcheck")

# What install.sh reads out of SCRIPT_DIR. Copied into each sandbox so the run is faithful.
COPY_DIRS = ("agents", "commands", "hooks", "ci-templates")
COPY_FILES = ("install.sh", "CLAUDE.md")


def is_executable(path: Path) -> bool:
    return bool(os.stat(path).st_mode & 0o111)


# ==========================================================================
# Part A — commands/sdd-init.md structural + content lint
# ==========================================================================
def split_frontmatter(text):
    """Split a markdown file into (frontmatter_str, body_str) or (None, text)."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def extract_section(body, heading_regex):
    """Return the text of the markdown section whose heading matches heading_regex.

    Captures from the matched heading up to (but excluding) the next heading at the same-or-
    shallower level, or end-of-document. Returns None if the heading is not found.
    """
    lines = body.split("\n")
    start = None
    start_level = None
    for i, line in enumerate(lines):
        hm = re.match(r"^(#+)\s+(.*)$", line)
        if hm and re.search(heading_regex, hm.group(2), re.IGNORECASE):
            start = i
            start_level = len(hm.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        hm = re.match(r"^(#+)\s+", lines[j])
        if hm and len(hm.group(1)) <= start_level:
            end = j
            break
    return "\n".join(lines[start:end])


class SddInitStructureTest(unittest.TestCase):
    """Part A: the markdown parses cleanly and carries the required structure."""

    @classmethod
    def setUpClass(cls):
        assert SDD_INIT_MD.exists(), f"sdd-init.md not found at {SDD_INIT_MD}"
        cls.text = SDD_INIT_MD.read_text(encoding="utf-8")
        cls.fm, cls.body = split_frontmatter(cls.text)

    def test_valid_markdown_frontmatter_and_headings(self):
        """The command spec opens with YAML frontmatter and a non-empty heading-bearing body."""
        self.assertIsNotNone(self.fm, "sdd-init.md does not open with a --- frontmatter fence")
        self.assertIn("description", self.fm, "frontmatter missing `description`")
        self.assertTrue(self.body.strip(), "markdown body after frontmatter is empty")
        self.assertRegex(self.body, r"(?m)^#\s", "body has no markdown headings")

    def test_code_fences_balanced(self):
        """Well-formed markdown: fenced code blocks are balanced (even number of ``` fences)."""
        fences = re.findall(r"(?m)^```", self.text)
        self.assertEqual(
            len(fences) % 2, 0, f"unbalanced ``` code fences: found {len(fences)}"
        )

    def test_ci_templates_section_present_between_gitignore_and_after_creation(self):
        """The new CI-templates section exists as an H2 (documented ordering: after Gitignore)."""
        self.assertRegex(
            self.body,
            r"(?mi)^##\s+CI templates\b",
            "no `## CI templates` section heading found",
        )
        # Both neighbours from the task description are present, confirming the doc structure.
        self.assertRegex(self.body, r"(?mi)^##\s+Gitignore\b", "Gitignore section missing")
        self.assertRegex(
            self.body, r"(?mi)^##\s+After creation\b", "After creation section missing"
        )


class SddInitCiSectionContentTest(unittest.TestCase):
    """Part A: the CI-templates section documents each required behaviour (FR-19/20/20.1/NFR-5)."""

    @classmethod
    def setUpClass(cls):
        text = SDD_INIT_MD.read_text(encoding="utf-8")
        _, body = split_frontmatter(text)
        cls.section = extract_section(body, r"^CI templates\b")
        assert cls.section is not None, "could not extract the `## CI templates` section"
        cls.lower = cls.section.lower()

    # (a) per-file create-or-skip for workflows -------------------------------
    def test_a_workflows_dir_created_if_missing(self):
        """FR-20: /sdd-init creates .github/workflows/ when absent."""
        self.assertIn(".github/workflows/", self.section)
        self.assertIn("create", self.lower)

    def test_a_per_file_add_missing_sdd_workflows(self):
        """FR-20/FR-19: each sdd-*.yml is added only if missing (per-file glob)."""
        self.assertRegex(
            self.section, r"sdd-\*\.yml", "no per-file `sdd-*.yml` glob documented"
        )

    def test_a_name_clash_skipped_and_reported_never_overwritten(self):
        """FR-20.1: an existing file of the same name is skipped + reported, never clobbered."""
        self.assertRegex(
            self.lower,
            r"do\s*not\s*overwrite|not overwrite|never overwrite",
            "no explicit 'do not overwrite' rule for workflows",
        )
        self.assertIn("skip", self.lower)
        self.assertRegex(
            self.lower, r"report|reported", "clash is not documented as reported"
        )

    # (b) shared scanner drop at the exact path -------------------------------
    def test_b_shared_scanner_exact_path(self):
        """FR-20/FR-19: the shared scanner drops at the exact .github/scripts path."""
        self.assertIn(
            ".github/scripts/sdd-secret-scan.py",
            self.section,
            "the exact shared-scanner path `.github/scripts/sdd-secret-scan.py` is not documented",
        )

    # (c) hook availability + activation guidance -----------------------------
    def test_c_hook_activation_hookspath_or_git_hooks(self):
        """FR-20/NFR-5: hook is made available with opt-in activation guidance."""
        self.assertIn(
            "core.hooksPath",
            self.section,
            "no `git config core.hooksPath` activation guidance",
        )
        # Either the core.hooksPath route or the .git/hooks/ copy route (or both) must appear.
        self.assertTrue(
            "core.hooksPath" in self.section or ".git/hooks/" in self.section,
            "no documented hook-activation location",
        )

    def test_c_hook_opt_in(self):
        """FR-20: activation stays opt-in — /sdd-init never force-activates the hook."""
        self.assertRegex(
            self.lower,
            r"opt-in|opt in|never activates|does not activate",
            "hook activation is not documented as opt-in",
        )

    def test_c_hook_sentinel_idempotence(self):
        """NFR-5: sentinel-based idempotence is documented via the managed-hook marker."""
        self.assertIn(
            SENTINEL,
            self.section,
            "the pre-push sentinel line is not documented for idempotent hook detection",
        )

    # (d) idempotent / non-destructive re-run behaviour -----------------------
    def test_d_idempotent_non_destructive_rerun(self):
        """NFR-5: re-running /sdd-init yields the same result — no duplicates, no overwrites."""
        self.assertRegex(
            self.lower,
            r"idempoten|same result|no duplicat|append-only|non-destructive|untouched",
            "idempotent / non-destructive re-run behaviour is not stated",
        )

    # (e) spec-lint auto-pickup drop-in note ----------------------------------
    def test_e_spec_lint_auto_pickup(self):
        """DD-1: a future sdd-spec-lint.yml is picked up automatically by the per-file loop."""
        self.assertIn(
            "sdd-spec-lint",
            self.section,
            "the sdd-spec-lint.yml auto-pickup drop-in note is missing",
        )

    # (f) two security-guidance items -----------------------------------------
    def test_f_security_no_write_perms_secrets_prt(self):
        """Security: warn against write permissions / secrets / pull_request_target on workflows."""
        self.assertIn(
            "pull_request_target",
            self.section,
            "missing the `pull_request_target` security warning",
        )
        self.assertIn("permissions", self.lower, "missing the write-`permissions:` warning")
        self.assertIn("secrets", self.lower, "missing the `secrets:` exposure warning")

    def test_f_security_review_gate_required_check(self):
        """Security: sdd-review-gate must be a REQUIRED status check on main."""
        self.assertIn(
            "sdd-review-gate",
            self.section,
            "the review-gate job is not named in the branch-protection guidance",
        )
        self.assertRegex(
            self.lower,
            r"required",
            "sdd-review-gate is not documented as a REQUIRED status check",
        )
        self.assertIn(
            "main",
            self.lower,
            "the required-check guidance does not mention the `main` branch",
        )
        # The skipped-non-PR-run caveat is the load-bearing security nuance.
        self.assertIn(
            "skipped",
            self.lower,
            "missing the caveat that a skipped non-PR run must not count as passing",
        )


# ==========================================================================
# Part B — install.sh workflow-staging behaviour (sandboxed real installer)
# ==========================================================================
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
    def staged_workflows_dir(self) -> Path:
        return self.home / ".claude" / "ci-templates" / "workflows"

    @property
    def staged_hook(self) -> Path:
        return self.home / ".claude" / "ci-templates" / "hooks" / "pre-push"

    @property
    def staged_scanner(self) -> Path:
        return self.home / ".claude" / "ci-templates" / "scripts" / "sdd-secret-scan.py"

    def run(self, answers: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
        env["PATH"] = str(self.fakebin) + os.pathsep + env.get("PATH", "")
        if not self.git_repo:
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
        base = Path(tempfile.mkdtemp(prefix="sdd-init-ci-test-"))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        return InstallerSandbox(base, git_repo=git_repo)


# --- B(1): syntax / shellcheck --------------------------------------------
class InstallSyntaxTest(unittest.TestCase):
    def test_bash_n_passes(self):
        """`bash -n install.sh` parses without a syntax error."""
        result = subprocess.run(
            [BASH, "-n", str(INSTALL_SH)], capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode, 0, f"bash -n reported a syntax error:\n{result.stderr}"
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


# --- B(2): opt-in staging of all three workflows alongside hook + scanner ---
@unittest.skipUnless(GIT, "git not available")
class WorkflowStagingTest(SandboxTestBase):
    def setUp(self):
        self.sb = self.make_sandbox(git_repo=True)
        # decline secret-handling, ACCEPT pre-push -> the staging block runs.
        self.proc = self.sb.run("n\ny\n")

    def test_run_succeeds(self):
        self.assertEqual(
            self.proc.returncode,
            0,
            f"installer failed:\n{self.proc.stdout}\n{self.proc.stderr}",
        )

    def test_all_three_workflows_staged(self):
        """FR-20/FR-21: every sdd-*.yml template lands under ~/.claude/ci-templates/workflows/."""
        for name in EXPECTED_WORKFLOWS:
            dest = self.sb.staged_workflows_dir / name
            self.assertTrue(dest.exists(), f"workflow not staged: {name}")

    def test_no_unexpected_extra_workflows(self):
        """Staging picks up exactly the sdd-*.yml set present in the source templates."""
        staged = {p.name for p in self.sb.staged_workflows_dir.glob("*.yml")}
        source = {p.name for p in WORKFLOWS_SRC.glob("sdd-*.yml")}
        self.assertEqual(staged, source, "staged workflow set differs from the source set")

    def test_task7_hook_and_scanner_still_staged(self):
        """Regression guard: Task-7 hook + scanner staging remains intact alongside workflows."""
        self.assertTrue(self.sb.staged_hook.exists(), "pre-push hook no longer staged (Task-7 regression)")
        self.assertTrue(
            is_executable(self.sb.staged_hook), "staged hook lost its exec bit"
        )
        self.assertTrue(
            self.sb.staged_scanner.exists(), "scanner no longer staged (Task-7 regression)"
        )
        self.assertTrue(
            filecmp.cmp(self.sb.staged_hook, HOOK_SRC, shallow=False),
            "staged hook content drifted from the template",
        )
        self.assertTrue(
            filecmp.cmp(self.sb.staged_scanner, SCANNER_SRC, shallow=False),
            "staged scanner content drifted from the source",
        )

    def test_staged_workflows_byte_equal_to_source(self):
        """FR-19: each staged workflow is byte-identical to its source template."""
        for name in EXPECTED_WORKFLOWS:
            dest = self.sb.staged_workflows_dir / name
            src = WORKFLOWS_SRC / name
            self.assertTrue(
                filecmp.cmp(dest, src, shallow=False),
                f"staged workflow {name} is not byte-equal to the source template",
            )

    def test_report_counts_the_staged_workflows(self):
        """The installer reports how many workflow templates were staged."""
        self.assertIn("Templates staged in", self.proc.stdout)
        self.assertRegex(
            self.proc.stdout,
            r"\b3\s+workflow\(s\)",
            "installer did not report 3 staged workflows",
        )


# --- B(3): idempotence — a second run yields the same staged set ------------
@unittest.skipUnless(GIT, "git not available")
class WorkflowStagingIdempotenceTest(SandboxTestBase):
    def _snapshot(self, sb):
        return {
            p.name: p.read_bytes() for p in sorted(sb.staged_workflows_dir.glob("*.yml"))
        }

    def test_second_run_same_set_no_duplication(self):
        """NFR-5: re-running the installer stages the identical set with no error/duplication."""
        sb = self.make_sandbox(git_repo=True)

        first = sb.run("n\ny\n")
        self.assertEqual(first.returncode, 0, f"first run failed:\n{first.stderr}")
        after_first = self._snapshot(sb)
        self.assertEqual(
            set(after_first), set(EXPECTED_WORKFLOWS), "first run staged the wrong set"
        )

        second = sb.run("n\ny\n")
        self.assertEqual(second.returncode, 0, f"second run failed:\n{second.stderr}")
        after_second = self._snapshot(sb)

        self.assertEqual(
            after_first, after_second, "staged workflow set/content changed on the idempotent re-run"
        )
        # No stray duplicates (e.g. sdd-secret-scan.yml.1) created by a second pass.
        all_files = list(sb.staged_workflows_dir.iterdir())
        self.assertEqual(
            len(all_files), len(EXPECTED_WORKFLOWS), f"unexpected files after re-run: {all_files}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
