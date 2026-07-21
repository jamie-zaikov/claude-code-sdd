#!/usr/bin/env python3
"""Structural / workflow lint for the three CI GitHub Actions templates (Task 5, sub-task 5.5).

These are config artifacts (GitHub Actions workflow YAML), so the "test" is a YAML/workflow
structure lint, not a unit test — the Actions runtime cannot be executed here. The suite asserts,
for `ci-templates/workflows/sdd-{secret-scan,review-gate,build-test-lint}.yml`:

  * each file is valid YAML (parsed with PyYAML when importable);
  * the shared trigger block matches the spec (PR on `main`; push branches-ignore [main]);
  * exactly one gate/job per file, with `sdd-`/gate naming;
  * the review-gate requires `ready-to-merge` AND forbids `blocked:*`, gated to pull_request;
  * the secret-scan job invokes the shared `sdd-secret-scan.py` via `--diff-file`;
  * every file declares least-privilege `permissions: contents: read` and none uses
    `pull_request_target`;
  * build-test-lint references `scripts/ci.sh` with both configured / not-configured paths;
  * no untrusted `${{ github.event.* }}` is interpolated directly inside a `run:` block
    (script-injection guard) — such values must be routed through `env:`.

YAML-parse-dependent checks are gated on PyYAML availability (HAVE_YAML). Shape checks that do not
strictly need a parse also have string-level coverage so the injection/scanner guards run anywhere.

Run:
    python3 -m unittest tests.test_ci_workflow_templates -v
    # or
    python3 tests/test_ci_workflow_templates.py
"""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

try:
    import yaml  # PyYAML — used for real YAML validity + structural assertions.

    HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on the runner environment
    yaml = None
    HAVE_YAML = False

# Resolve the workflow dir relative to this test so it survives both the worktree layout
#   <root>/tests/test_ci_workflow_templates.py -> <root>/ci-templates/workflows/
# and consolidation onto feat/github-agent.
WORKFLOW_DIR = Path(__file__).resolve().parent.parent / "ci-templates" / "workflows"

SECRET_SCAN = WORKFLOW_DIR / "sdd-secret-scan.yml"
REVIEW_GATE = WORKFLOW_DIR / "sdd-review-gate.yml"
BUILD_TEST_LINT = WORKFLOW_DIR / "sdd-build-test-lint.yml"

ALL_FILES = (SECRET_SCAN, REVIEW_GATE, BUILD_TEST_LINT)

ACTIONLINT = shutil.which("actionlint")


def load_yaml(path):
    """Parse a workflow file with PyYAML. Only call when HAVE_YAML is True."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_on_block(data):
    """Return the `on:` mapping.

    PyYAML follows the YAML 1.1 core schema, where the bare key `on` is parsed as the boolean
    True. GitHub Actions treats it as the string "on". Accept either so the assertions are robust
    to the parser's interpretation.
    """
    if True in data:
        return data[True]
    return data.get("on")


def iter_run_blocks(text):
    """Yield the raw text of every `run:` block scalar in a workflow file.

    Handles both `run: |` / `run: >` block scalars (consuming the more-indented continuation
    lines) and single-line `run: <cmd>` forms. String-level so it needs no YAML parser and is
    used for the script-injection guard.
    """
    lines = text.split("\n")
    i = 0
    run_re = re.compile(r"^(\s*)run:\s*(\S.*)?$")
    while i < len(lines):
        m = run_re.match(lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        rest = (m.group(2) or "").strip()
        if rest and rest[0] in "|>":
            # Block scalar: gather more-indented (or blank) lines.
            block = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                if ln.strip() and (len(ln) - len(ln.lstrip())) <= indent:
                    break
                block.append(ln)
                i += 1
            yield "\n".join(block)
        else:
            # Single-line run value.
            yield rest
            i += 1


class WorkflowFilesExistTest(unittest.TestCase):
    def test_all_three_workflow_files_exist(self):
        for path in ALL_FILES:
            self.assertTrue(path.exists(), f"workflow template not found: {path}")


@unittest.skipUnless(HAVE_YAML, "PyYAML not importable — YAML-parse checks skipped")
class ValidYamlTest(unittest.TestCase):
    """5.5(1): each file is valid YAML. Uses real PyYAML parsing."""

    def test_each_file_is_valid_yaml(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                try:
                    data = load_yaml(path)
                except yaml.YAMLError as exc:  # pragma: no cover
                    self.fail(f"{path.name} is not valid YAML: {exc}")
                self.assertIsInstance(
                    data, dict, f"{path.name} did not parse to a mapping"
                )


@unittest.skipUnless(ACTIONLINT, "actionlint not on PATH — external-tool check skipped")
class ActionlintTest(unittest.TestCase):
    """5.5(2): if actionlint is available, each workflow lints clean; otherwise SKIP."""

    def test_actionlint_clean(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                result = subprocess.run(
                    [ACTIONLINT, str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"actionlint reported issues for {path.name}:\n"
                    f"{result.stdout}\n{result.stderr}",
                )


@unittest.skipUnless(HAVE_YAML, "PyYAML not importable — trigger-block parse checks skipped")
class TriggerBlockTest(unittest.TestCase):
    """5.5(3): the shared trigger block matches the spec in all three files (FR-16.1, FR-19)."""

    def test_pull_request_targets_main(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                on = get_on_block(load_yaml(path))
                self.assertIsInstance(on, dict, f"{path.name}: no `on:` mapping")
                self.assertIn("pull_request", on, f"{path.name}: no pull_request trigger")
                self.assertEqual(
                    on["pull_request"].get("branches"),
                    ["main"],
                    f"{path.name}: on.pull_request.branches must be [main]",
                )

    def test_push_ignores_main(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                on = get_on_block(load_yaml(path))
                self.assertIn("push", on, f"{path.name}: no push trigger")
                self.assertEqual(
                    on["push"].get("branches-ignore"),
                    ["main"],
                    f"{path.name}: on.push.branches-ignore must be [main]",
                )


@unittest.skipUnless(HAVE_YAML, "PyYAML not importable — job-count parse checks skipped")
class SingleGatePerFileTest(unittest.TestCase):
    """5.5(4): exactly one gate/job per file, with sdd-/gate naming (DD-1, FR-19)."""

    EXPECTED_JOB = {
        SECRET_SCAN.name: "secret-scan",
        REVIEW_GATE.name: "review-gate",
        BUILD_TEST_LINT.name: "build-test-lint",
    }

    def test_exactly_one_job_per_file(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                jobs = load_yaml(path).get("jobs")
                self.assertIsInstance(jobs, dict, f"{path.name}: no jobs mapping")
                self.assertEqual(
                    len(jobs),
                    1,
                    f"{path.name}: expected exactly one job, got {list(jobs)}",
                )
                self.assertIn(
                    self.EXPECTED_JOB[path.name],
                    jobs,
                    f"{path.name}: expected job {self.EXPECTED_JOB[path.name]!r}, got {list(jobs)}",
                )

    def test_workflow_name_carries_sdd_prefix(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                data = load_yaml(path)
                name = str(data.get("name", ""))
                self.assertTrue(
                    name.startswith("sdd-"),
                    f"{path.name}: workflow `name` must carry the sdd- prefix, got {name!r}",
                )
                # The filename itself is the sdd-<gate>.yml naming that lets a future
                # sdd-spec-lint.yml drop in (DD-1).
                self.assertTrue(
                    path.name.startswith("sdd-"),
                    f"{path.name}: filename must carry the sdd- prefix",
                )


class LeastPrivilegeTest(unittest.TestCase):
    """5.5(7): least-privilege permissions (contents: read) and no pull_request_target (NFR-1)."""

    @unittest.skipUnless(HAVE_YAML, "PyYAML not importable")
    def test_permissions_contents_read(self):
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                perms = load_yaml(path).get("permissions")
                self.assertIsInstance(
                    perms, dict, f"{path.name}: missing top-level permissions block"
                )
                self.assertEqual(
                    perms.get("contents"),
                    "read",
                    f"{path.name}: permissions.contents must be 'read'",
                )
                # Least privilege: contents:read should be the only scope granted.
                self.assertEqual(
                    set(perms),
                    {"contents"},
                    f"{path.name}: only `contents: read` should be granted, got {perms}",
                )

    def test_no_pull_request_target(self):
        # String-level so it runs even without PyYAML — pull_request_target is the dangerous
        # trigger that would grant a write token to untrusted PR code.
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "pull_request_target",
                    text,
                    f"{path.name}: must not use the pull_request_target trigger",
                )


class ReviewGateLogicTest(unittest.TestCase):
    """5.5(5): review-gate requires ready-to-merge AND forbids blocked:*, PR-gated (FR-14, FR-12)."""

    @classmethod
    def setUpClass(cls):
        cls.text = REVIEW_GATE.read_text(encoding="utf-8")

    def test_references_ready_to_merge(self):
        self.assertIn(
            "ready-to-merge",
            self.text,
            "review-gate must reference the ready-to-merge label",
        )

    def test_references_blocked_label(self):
        self.assertIn(
            "blocked:",
            self.text,
            "review-gate must reference the blocked:* label prefix",
        )

    def test_gated_to_pull_request_events(self):
        # The job must be conditioned on pull_request events (no-op on push-to-feature-branch).
        self.assertRegex(
            self.text,
            r"github\.event_name\s*==\s*'pull_request'",
            "review-gate job must be gated to pull_request events",
        )

    @unittest.skipUnless(HAVE_YAML, "PyYAML not importable")
    def test_job_if_condition_present(self):
        job = load_yaml(REVIEW_GATE)["jobs"]["review-gate"]
        cond = str(job.get("if", ""))
        self.assertIn(
            "pull_request",
            cond,
            "review-gate job `if:` must restrict to pull_request events",
        )

    def test_fails_on_blocked_and_requires_ready(self):
        # The enforcement logic must contain both a failure path keyed to blocked labels and a
        # failure path when ready-to-merge is absent (both exit non-zero).
        self.assertRegex(
            self.text,
            r"blocked",
            "review-gate must key a failure on blocked labels",
        )
        # A ready-to-merge membership test drives the required-label check.
        self.assertRegex(
            self.text,
            r'"ready-to-merge"\s+in\s+labels|ready-to-merge.*in\s+labels|not\s+ready',
            "review-gate must check membership of ready-to-merge",
        )


class SecretScanScannerTest(unittest.TestCase):
    """5.5(6): secret-scan references the shared scanner and passes the diff via --diff-file."""

    @classmethod
    def setUpClass(cls):
        cls.text = SECRET_SCAN.read_text(encoding="utf-8")

    def test_references_shared_scanner(self):
        self.assertIn(
            "sdd-secret-scan.py",
            self.text,
            "secret-scan must invoke the shared sdd-secret-scan.py scanner",
        )

    def test_passes_diff_via_diff_file(self):
        self.assertIn(
            "--diff-file",
            self.text,
            "secret-scan must hand the pre-computed diff to the scanner via --diff-file",
        )

    def test_scanner_invoked_with_diff_file_argument(self):
        # The scanner call must be `... sdd-secret-scan.py --diff-file <path>` — the diff-file
        # approach that closes the Task-4 argument-injection caveat (no refs after a bare `--`).
        self.assertRegex(
            self.text,
            r"sdd-secret-scan\.py\s+--diff-file",
            "scanner must be invoked as `sdd-secret-scan.py --diff-file <path>`",
        )

    def test_no_bare_double_dash_remainder_with_refs(self):
        # Guard the Task-4 REMAINDER caveat: the scanner must NOT be called with refs after a bare
        # `--` (which argparse would treat as positional remainder). The --diff-file form is used
        # instead, so no `sdd-secret-scan.py -- <ref>` pattern should appear.
        self.assertNotRegex(
            self.text,
            r"sdd-secret-scan\.py\s+--\s",
            "scanner must not be invoked with a bare `--` remainder of refs",
        )


class ScriptInjectionGuardTest(unittest.TestCase):
    """Bonus: no untrusted ${{ github.event.* }} interpolated directly inside a run: block."""

    def test_no_github_event_interpolation_in_run_blocks(self):
        pat = re.compile(r"\$\{\{\s*github\.event[.\[]")
        for path in ALL_FILES:
            with self.subTest(workflow=path.name):
                for block in iter_run_blocks(path.read_text(encoding="utf-8")):
                    self.assertNotRegex(
                        block,
                        pat,
                        f"{path.name}: untrusted github.event.* interpolated directly into a "
                        f"run: block — route it through env: instead. Offending run:\n{block}",
                    )


class BuildTestLintTest(unittest.TestCase):
    """Bonus: build-test-lint references scripts/ci.sh with configured + not-configured paths."""

    @classmethod
    def setUpClass(cls):
        cls.text = BUILD_TEST_LINT.read_text(encoding="utf-8")

    def test_references_ci_sh(self):
        self.assertIn(
            "scripts/ci.sh",
            self.text,
            "build-test-lint must reference the conventional scripts/ci.sh entrypoint",
        )

    def test_has_present_path(self):
        # Runs ci.sh when it exists.
        self.assertRegex(
            self.text,
            r"-f\s+scripts/ci\.sh",
            "build-test-lint must test for scripts/ci.sh presence",
        )
        self.assertRegex(
            self.text,
            r"bash\s+scripts/ci\.sh",
            "build-test-lint must run scripts/ci.sh when present",
        )

    def test_has_not_configured_path(self):
        # Prints a notice and exits 0 when ci.sh is absent.
        self.assertRegex(
            self.text,
            r"::notice::",
            "build-test-lint must emit a `not configured` notice when ci.sh is absent",
        )
        self.assertRegex(
            self.text,
            r"exit 0",
            "build-test-lint must exit 0 on the not-configured path",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
