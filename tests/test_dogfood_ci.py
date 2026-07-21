#!/usr/bin/env python3
"""Structural test for the Task 9 dogfood: CI workflows + shared scanner + scripts/ci.sh (FR-21).

Task 9 instantiates the three CI workflow templates and the shared secret scanner into this
repository's OWN `.github/`, and adds a concrete `scripts/ci.sh` for the dogfood build-test-lint
job. These are config / shell artifacts, so the "test" is a YAML/workflow structure lint plus a
`bash -n` syntax check and a clean-tree run of ci.sh — not a unit test (the Actions runtime cannot
be executed here).

The suite asserts, per Task 9 sub-task 9.3 and FR-21 / FR-16.1 / FR-15:

  * each instantiated `.github/workflows/sdd-*.yml` is valid YAML (parsed with PyYAML) with the
    shared trigger block (PR on `main`; push branches-ignore [main]) — FR-16.1;
  * each dogfood workflow is byte-identical to its `ci-templates/workflows/` counterpart, and the
    dogfood `.github/scripts/sdd-secret-scan.py` is byte-identical to the template scanner — FR-21;
  * the seam fix: every workflow (template AND dogfood copy) carries a job-level `name:` equal to
    the documented required-check name (`sdd-secret-scan` / `sdd-review-gate` /
    `sdd-build-test-lint`) so GitHub's emitted check-run context matches branch protection;
  * `scripts/ci.sh` is executable, has the `#!/usr/bin/env bash` shebang, references the framework's
    own checks (py_compile, the scanner path, install.sh, and the guard/redact smoke test), passes
    `bash -n` (and shellcheck when available), and exits 0 on the current clean tree — FR-15.

The known secret-scan false-positive concern (the live secret-scan gate flagging framework source
and test fixtures) is a whole-feature matter routed separately; it is deliberately OUT of scope
here. This suite never runs the secret-scan gate over the repo.

YAML-parse-dependent checks are gated on PyYAML availability (HAVE_YAML). shellcheck / actionlint
checks skip cleanly when those tools are absent.

Run:
    python3 -m unittest tests.test_dogfood_ci -v
    # or
    python3 tests/test_dogfood_ci.py
"""

import filecmp
import os
import shutil
import stat
import subprocess
import unittest
from pathlib import Path

try:
    import yaml  # PyYAML — used for real YAML validity + trigger/name assertions.

    HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on the runner environment
    yaml = None
    HAVE_YAML = False

# Resolve the repo root relative to this test so it survives both the worktree layout
#   <root>/tests/test_dogfood_ci.py -> <root>/
# and consolidation onto feat/github-agent.
ROOT = Path(__file__).resolve().parent.parent

DOGFOOD_WORKFLOWS = ROOT / ".github" / "workflows"
TEMPLATE_WORKFLOWS = ROOT / "ci-templates" / "workflows"
DOGFOOD_SCANNER = ROOT / ".github" / "scripts" / "sdd-secret-scan.py"
TEMPLATE_SCANNER = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"
CI_SH = ROOT / "scripts" / "ci.sh"

# Workflow basename -> documented required-check / job-level name.
WORKFLOW_NAMES = {
    "sdd-secret-scan.yml": "sdd-secret-scan",
    "sdd-review-gate.yml": "sdd-review-gate",
    "sdd-build-test-lint.yml": "sdd-build-test-lint",
}

SHELLCHECK = shutil.which("shellcheck")


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


class DogfoodWorkflowsExistTests(unittest.TestCase):
    """The three workflows and the shared scanner must be instantiated into `.github/` (FR-21)."""

    def test_dogfood_workflows_present(self):
        for name in WORKFLOW_NAMES:
            path = DOGFOOD_WORKFLOWS / name
            self.assertTrue(path.exists(), f"dogfood workflow not instantiated: {path}")

    def test_dogfood_scanner_present(self):
        self.assertTrue(
            DOGFOOD_SCANNER.exists(),
            f"dogfood scanner not placed at referenced path: {DOGFOOD_SCANNER}",
        )


@unittest.skipUnless(HAVE_YAML, "PyYAML not importable — YAML-parse checks skipped")
class DogfoodWorkflowYamlTests(unittest.TestCase):
    """Each instantiated workflow is valid YAML with the shared trigger block (FR-16.1)."""

    def test_workflows_are_valid_yaml(self):
        for name in WORKFLOW_NAMES:
            with self.subTest(workflow=name):
                data = load_yaml(DOGFOOD_WORKFLOWS / name)
                self.assertIsInstance(data, dict, f"{name}: did not parse to a mapping")

    def test_pull_request_trigger_targets_main(self):
        for name in WORKFLOW_NAMES:
            with self.subTest(workflow=name):
                on = get_on_block(load_yaml(DOGFOOD_WORKFLOWS / name))
                self.assertIsInstance(on, dict, f"{name}: no `on:` mapping")
                self.assertIn("pull_request", on, f"{name}: no pull_request trigger")
                self.assertEqual(
                    on["pull_request"].get("branches"),
                    ["main"],
                    f"{name}: on.pull_request.branches must be [main]",
                )

    def test_push_trigger_ignores_main(self):
        for name in WORKFLOW_NAMES:
            with self.subTest(workflow=name):
                on = get_on_block(load_yaml(DOGFOOD_WORKFLOWS / name))
                self.assertIn("push", on, f"{name}: no push trigger")
                self.assertEqual(
                    on["push"].get("branches-ignore"),
                    ["main"],
                    f"{name}: on.push.branches-ignore must be [main]",
                )


@unittest.skipUnless(HAVE_YAML, "PyYAML not importable — YAML-parse checks skipped")
class JobNameSeamFixTests(unittest.TestCase):
    """Every job carries the documented job-level `name:` so the check-run context matches
    branch protection's required-check name — in BOTH the template and the dogfood copy."""

    def _assert_job_name(self, path, expected):
        data = load_yaml(path)
        jobs = data.get("jobs")
        self.assertIsInstance(jobs, dict, f"{path}: no jobs mapping")
        self.assertEqual(len(jobs), 1, f"{path}: expected exactly one job")
        (job_body,) = jobs.values()
        self.assertEqual(
            job_body.get("name"),
            expected,
            f"{path}: job-level name must be {expected!r} (got {job_body.get('name')!r})",
        )

    def test_dogfood_job_names(self):
        for name, expected in WORKFLOW_NAMES.items():
            with self.subTest(workflow=name, where="dogfood"):
                self._assert_job_name(DOGFOOD_WORKFLOWS / name, expected)

    def test_template_job_names(self):
        for name, expected in WORKFLOW_NAMES.items():
            with self.subTest(workflow=name, where="template"):
                self._assert_job_name(TEMPLATE_WORKFLOWS / name, expected)

    def test_review_gate_job_name_is_sdd_review_gate(self):
        # Explicit per the task: the review-gate job name must be `sdd-review-gate`.
        self._assert_job_name(DOGFOOD_WORKFLOWS / "sdd-review-gate.yml", "sdd-review-gate")
        self._assert_job_name(TEMPLATE_WORKFLOWS / "sdd-review-gate.yml", "sdd-review-gate")


class ByteIdentityTests(unittest.TestCase):
    """Dogfood copies must be byte-identical to their templates (FR-21)."""

    def test_workflows_byte_identical_to_templates(self):
        for name in WORKFLOW_NAMES:
            with self.subTest(workflow=name):
                dogfood = DOGFOOD_WORKFLOWS / name
                template = TEMPLATE_WORKFLOWS / name
                self.assertTrue(
                    filecmp.cmp(dogfood, template, shallow=False),
                    f"{name}: dogfood copy is not byte-identical to ci-templates counterpart",
                )

    def test_scanner_byte_identical_to_template(self):
        self.assertTrue(
            filecmp.cmp(DOGFOOD_SCANNER, TEMPLATE_SCANNER, shallow=False),
            "dogfood sdd-secret-scan.py is not byte-identical to ci-templates scanner",
        )


class CiShStructureTests(unittest.TestCase):
    """scripts/ci.sh is a concrete, executable dogfood build/test/lint entrypoint (FR-15)."""

    @classmethod
    def setUpClass(cls):
        cls.text = CI_SH.read_text(encoding="utf-8") if CI_SH.exists() else ""

    def test_ci_sh_exists(self):
        self.assertTrue(CI_SH.exists(), f"scripts/ci.sh not created: {CI_SH}")

    def test_ci_sh_is_executable(self):
        mode = os.stat(CI_SH).st_mode
        self.assertTrue(mode & 0o111, "scripts/ci.sh is not executable (no exec bit set)")

    def test_ci_sh_has_bash_shebang(self):
        first_line = self.text.splitlines()[0] if self.text else ""
        self.assertEqual(
            first_line,
            "#!/usr/bin/env bash",
            f"scripts/ci.sh must start with the bash shebang (got {first_line!r})",
        )

    def test_ci_sh_references_py_compile(self):
        self.assertIn("py_compile", self.text, "ci.sh must run python3 -m py_compile")

    def test_ci_sh_references_scanner_path(self):
        self.assertIn(
            ".github/scripts/sdd-secret-scan.py",
            self.text,
            "ci.sh must byte-compile the shared scanner at its referenced path",
        )

    def test_ci_sh_references_install_sh(self):
        self.assertIn("install.sh", self.text, "ci.sh must lint install.sh")

    def test_ci_sh_runs_guard_redact_smoke(self):
        self.assertIn("secret-guard.py", self.text, "ci.sh must smoke-test secret-guard.py")
        self.assertIn("secret-redact.py", self.text, "ci.sh must smoke-test secret-redact.py")


class CiShSyntaxTests(unittest.TestCase):
    """scripts/ci.sh passes `bash -n` (and shellcheck when available)."""

    def test_bash_n_syntax_ok(self):
        result = subprocess.run(
            ["bash", "-n", str(CI_SH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"`bash -n scripts/ci.sh` failed:\n{result.stderr}",
        )

    @unittest.skipUnless(SHELLCHECK, "shellcheck not on PATH — external-tool check skipped")
    def test_shellcheck_clean(self):
        result = subprocess.run(
            [SHELLCHECK, str(CI_SH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"shellcheck reported findings in scripts/ci.sh:\n{result.stdout}\n{result.stderr}",
        )


class CiShRunTests(unittest.TestCase):
    """scripts/ci.sh exits 0 when run on the current clean tree (FR-15)."""

    def test_ci_sh_exits_zero_on_clean_tree(self):
        # ci.sh resolves REPO_ROOT from its own location and cd's there itself, so the caller's
        # cwd does not matter; run from the repo root anyway for clarity. It performs no network
        # or gh calls and writes nothing outside the tree.
        result = subprocess.run(
            ["bash", str(CI_SH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"scripts/ci.sh did not exit 0 on the clean tree:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
