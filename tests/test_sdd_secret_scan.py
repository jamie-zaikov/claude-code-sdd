#!/usr/bin/env python3
"""Unit tests for the shared secret scanner (Task 4, sub-task 4.4 + retry regressions).

Covers FR-13, FR-16, NFR-2, NFR-3 for `ci-templates/scripts/sdd-secret-scan.py`:
the single scanner reused by CI and the pre-push hook. It scans ONLY added/changed
content of a unified git diff, exits 0 clean / 1 detected / 2 usage-or-git-error,
and reports findings by TYPE and `path:line` ONLY, never the value (NFR-2).

This suite includes the mandatory regression tests (6-12) that pin the false-negative
class the first attempt shipped: a diff BODY line can be textually identical to a
structural header (`--- x`, `+++ x`), and the count-consuming parser must classify
body lines strictly by first character while inside a counted hunk.

Secret hygiene: every secret-shaped fixture is built by concatenating fragments at
RUNTIME (e.g. "ghp_" + "x"*36) so no whole secret literal is ever committed, and the
no-leak assertions are BOOLEAN so a failure never echoes a fixture value.

Stdlib only (unittest + importlib + subprocess + tempfile + os). The target module
filename is hyphenated, so it is loaded via importlib.util from a path resolved
relative to this test file so the suite survives consolidation onto feat/github-agent:
    <root>/tests/test_sdd_secret_scan.py -> <root>/ci-templates/scripts/sdd-secret-scan.py

Run:
    python3 -m unittest tests.test_sdd_secret_scan -v
    # or
    python3 tests/test_sdd_secret_scan.py
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_PATH = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"


def load_scan_module():
    """Load ci-templates/scripts/sdd-secret-scan.py despite its hyphenated name."""
    spec = importlib.util.spec_from_file_location("sdd_secret_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load_scan_module()


# --- Runtime-built secret-shaped fixtures (NEVER a whole literal in source) ---
# Maps expected Finding.type label -> a value built from fragments. Each value is
# designed to match exactly the vendored pattern for that family.
def _build_secret_fixtures():
    begin = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
    end = "-----END " + "RSA " + "PRIVATE KEY-----"
    body = "MIIB" + "a" * 48
    return {
        "private-key-block": begin + "\n" + body + "\n" + end,
        "aws-access-key-id": "AKIA" + "A" * 16,
        "github-token": "ghp_" + "A" * 36,
        "github-pat": "github_pat_" + "A" * 60,
        "gitlab-pat": "glpat-" + "A" * 20,
        "slack-token": "xoxb-" + "A" * 12,
        "google-api-key": "AIza" + "A" * 35,
        "openai-secret-key": "sk-" + "A" * 20,
        "stripe-live-key": "sk_live_" + "A" * 16,
        "jwt": "eyJ" + "A" * 8 + "." + "B" * 8 + "." + "C" * 8,
        "authorization-header": "Authorization: Bearer " + "A" * 12,
        "x-api-key-header": "x-api-key: " + "A" * 12,
        "secret-assignment": "api_key=" + "A" * 12,
    }


SECRETS = _build_secret_fixtures()

# A single, easily-identified secret used inside diff fixtures (AWS key id shape).
AWS_SECRET = SECRETS["aws-access-key-id"]
GH_SECRET = SECRETS["github-token"]
SLACK_SECRET = SECRETS["slack-token"]

# Private-key block fragments for the multiline diff regression tests.
PK_BEGIN = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
PK_BODY = "MIIB" + "a" * 40
PK_END = "-----END " + "RSA " + "PRIVATE KEY-----"


def run_cli(args, input_bytes=None):
    """Invoke the scanner as the real CLI; return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCAN_PATH)] + args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class PyCompileTest(unittest.TestCase):
    """Sub-task 4.4: the file must compile."""

    def test_py_compile(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SCAN_PATH)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"py_compile failed: {result.stderr}")


class SecretFamilyDetectionTest(unittest.TestCase):
    """(2) Every secret family is detected via scan_content, and the report carries
    TYPE + path:line but NOT the value (FR-13, NFR-2)."""

    def test_every_family_detected_with_type_and_location(self):
        for expected_type, value in SECRETS.items():
            with self.subTest(family=expected_type):
                findings = scan.scan_content(value, "f.txt")
                # Detected at all.
                self.assertTrue(
                    findings, f"no finding produced for family {expected_type}"
                )
                # Detected under the expected type label.
                self.assertTrue(
                    any(f.type == expected_type for f in findings),
                    f"family {expected_type} not detected under its type label",
                )
                report = scan.format_findings(findings)
                # Report carries the type label and a path:line locator.
                self.assertIn(expected_type, report)
                self.assertIn("f.txt:", report)
                self.assertTrue(any(f.path == "f.txt" for f in findings))
                self.assertTrue(all(isinstance(f.line, int) for f in findings))

    def test_report_never_contains_the_secret_value(self):
        """NFR-2 (critical): the rendered report must not contain the fixture value.
        Boolean assertion form so a failure never echoes the value."""
        for expected_type, value in SECRETS.items():
            with self.subTest(family=expected_type):
                findings = scan.scan_content(value, "f.txt")
                report = scan.format_findings(findings)
                self.assertTrue(
                    value not in report,
                    f"report leaked the secret value for family {expected_type}",
                )

    def test_finding_record_has_no_value_field(self):
        """NFR-2: the Finding record structurally cannot carry the value."""
        self.assertEqual(scan.Finding._fields, ("type", "path", "line"))


class CleanContentTest(unittest.TestCase):
    """(3) Clean content produces no findings (FR-13)."""

    def test_clean_content_no_findings(self):
        clean = "def add(a, b):\n    return a + b\n# nothing secret here\n"
        self.assertEqual(scan.scan_content(clean, "f.py"), [])


class ScanDiffAddedVsRemovedTest(unittest.TestCase):
    """(4) scan_diff flags a secret on an ADDED line with correct path:line, and does
    NOT flag one on a removed or context line (FR-13, FR-16)."""

    def _diff(self):
        return (
            "diff --git a/file.txt b/file.txt\n"
            "index 0000000..1111111 100644\n"
            "--- a/file.txt\n"
            "+++ b/file.txt\n"
            "@@ -1,2 +1,2 @@\n"
            " " + SLACK_SECRET + "\n"      # context line -> NOT scanned
            "-" + GH_SECRET + "\n"         # removed line -> NOT scanned
            "+" + AWS_SECRET + "\n"        # added line   -> scanned, new line 2
        )

    def test_added_line_secret_detected_with_location(self):
        findings = scan.scan_diff(self._diff())
        matches = [f for f in findings if f.type == "aws-access-key-id"]
        self.assertEqual(len(matches), 1, "expected exactly one added-line AWS finding")
        self.assertEqual(matches[0].path, "file.txt")
        self.assertEqual(matches[0].line, 2)

    def test_removed_and_context_line_secrets_not_flagged(self):
        findings = scan.scan_diff(self._diff())
        types = {f.type for f in findings}
        self.assertNotIn("github-token", types, "removed-line secret was flagged")
        self.assertNotIn("slack-token", types, "context-line secret was flagged")


class CliEndToEndTest(unittest.TestCase):
    """(5) CLI via --diff-file (path and stdin '-'): exit 1 on secret, 0 on clean."""

    def _write_tmp(self, text):
        fd, path = tempfile.mkstemp(suffix=".diff")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def _secret_diff(self):
        return (
            "diff --git a/s.txt b/s.txt\n"
            "--- a/s.txt\n"
            "+++ b/s.txt\n"
            "@@ -0,0 +1,1 @@\n"
            "+" + AWS_SECRET + "\n"
        )

    def _clean_diff(self):
        return (
            "diff --git a/c.txt b/c.txt\n"
            "--- a/c.txt\n"
            "+++ b/c.txt\n"
            "@@ -0,0 +1,1 @@\n"
            "+just a normal line of code\n"
        )

    def test_diff_file_path_secret_exit_1(self):
        path = self._write_tmp(self._secret_diff())
        proc = run_cli(["--diff-file", path])
        self.assertEqual(proc.returncode, 1)

    def test_diff_file_path_clean_exit_0(self):
        path = self._write_tmp(self._clean_diff())
        proc = run_cli(["--diff-file", path])
        self.assertEqual(proc.returncode, 0)

    def test_stdin_secret_exit_1(self):
        proc = run_cli(["--diff-file", "-"], input_bytes=self._secret_diff().encode())
        self.assertEqual(proc.returncode, 1)

    def test_stdin_clean_exit_0(self):
        proc = run_cli(["--diff-file", "-"], input_bytes=self._clean_diff().encode())
        self.assertEqual(proc.returncode, 0)

    def test_cli_report_does_not_leak_value(self):
        """NFR-2 at the CLI boundary: neither stdout nor stderr contains the value."""
        path = self._write_tmp(self._secret_diff())
        proc = run_cli(["--diff-file", path])
        combined = proc.stdout + proc.stderr
        self.assertTrue(
            AWS_SECRET.encode() not in combined,
            "CLI output leaked the secret value",
        )


# ---------------------------------------------------------------------------
# MANDATORY REGRESSION TESTS (6-12) — the false-negative class from attempt 1.
# ---------------------------------------------------------------------------


class RegressionHeaderShapedBodyRemovedTest(unittest.TestCase):
    """(6) A --unified=0 hunk that REMOVES a line reading '-- deprecated setting'
    (rendered '--- deprecated setting') AND adds a secret in the SAME hunk. The
    header-shaped removed body line must NOT terminate the hunk; the secret must be
    detected. This is the exact first-attempt false negative."""

    def _diff(self):
        return (
            "diff --git a/config b/config\n"
            "index aaaaaaa..bbbbbbb 100644\n"
            "--- a/config\n"
            "+++ b/config\n"
            "@@ -10 +10 @@\n"
            "--- deprecated setting\n"    # removed line whose content starts '-- '
            "+" + AWS_SECRET + "\n"       # added secret in the same hunk, new line 10
        )

    def test_secret_after_header_shaped_removed_line_detected(self):
        findings = scan.scan_diff(self._diff())
        matches = [f for f in findings if f.type == "aws-access-key-id"]
        self.assertEqual(len(matches), 1, "secret missed after '--- ' body line")
        self.assertEqual(matches[0].path, "config")
        self.assertEqual(matches[0].line, 10)

    def test_cli_exit_1(self):
        proc = run_cli(["--diff-file", "-"], input_bytes=self._diff().encode())
        self.assertEqual(proc.returncode, 1)


class RegressionHeaderShapedBodyAddedTest(unittest.TestCase):
    """(7) A diff that ADDS a line whose content starts '++ ' (rendered '+++ foo')
    followed by another ADDED line containing a secret in the same hunk. The
    header-shaped added body line must be treated as content, not a '+++' header,
    so the following secret is still detected."""

    def _diff(self):
        return (
            "diff --git a/x b/x\n"
            "index aaaaaaa..bbbbbbb 100644\n"
            "--- a/x\n"
            "+++ b/x\n"
            "@@ -0,0 +1,2 @@\n"
            "+++ foo\n"                    # added line whose content is '++ foo'
            "+" + AWS_SECRET + "\n"        # added secret, new line 2
        )

    def test_secret_after_header_shaped_added_line_detected(self):
        findings = scan.scan_diff(self._diff())
        matches = [f for f in findings if f.type == "aws-access-key-id"]
        self.assertEqual(len(matches), 1, "secret missed after '+++ ' body line")
        self.assertEqual(matches[0].path, "x")
        self.assertEqual(matches[0].line, 2)


class RegressionPrivateKeyBlockAcrossAddedLinesTest(unittest.TestCase):
    """(8) A full BEGIN...END private-key block added as consecutive '+' lines is
    detected as one finding at the BEGIN line."""

    def _diff(self):
        return (
            "diff --git a/key.pem b/key.pem\n"
            "new file mode 100644\n"
            "index 0000000..2222222\n"
            "--- /dev/null\n"
            "+++ b/key.pem\n"
            "@@ -0,0 +1,3 @@\n"
            "+" + PK_BEGIN + "\n"
            "+" + PK_BODY + "\n"
            "+" + PK_END + "\n"
        )

    def test_private_key_block_detected_once_at_begin_line(self):
        findings = scan.scan_diff(self._diff())
        pk = [f for f in findings if f.type == "private-key-block"]
        self.assertEqual(len(pk), 1, "private-key block not detected as a single finding")
        self.assertEqual(pk[0].path, "key.pem")
        self.assertEqual(pk[0].line, 1)


class RegressionCrossHunkFalsePositiveGuardTest(unittest.TestCase):
    """(9) A BEGIN marker added in one hunk and an unrelated END marker added in a
    far-apart hunk must NOT produce a spurious private-key finding spanning the two
    (per-run/per-hunk scanning)."""

    def _diff(self):
        return (
            "diff --git a/mix.txt b/mix.txt\n"
            "index 3333333..4444444 100644\n"
            "--- a/mix.txt\n"
            "+++ b/mix.txt\n"
            "@@ -0,0 +1,2 @@\n"
            "+" + PK_BEGIN + "\n"
            "+some unrelated added content here\n"
            "@@ -50,0 +60,1 @@\n"
            "+" + PK_END + "\n"
        )

    def test_no_spurious_cross_hunk_private_key_finding(self):
        findings = scan.scan_diff(self._diff())
        self.assertFalse(
            any(f.type == "private-key-block" for f in findings),
            "spurious private-key finding spanned two far-apart hunks",
        )


class RegressionMultiHunkMultiFileTest(unittest.TestCase):
    """(10) A single diff spanning two files and two hunks: a secret on an added line
    in the SECOND file/hunk is detected with the correct path and line."""

    def _diff(self):
        return (
            "diff --git a/first.txt b/first.txt\n"
            "index a111111..b111111 100644\n"
            "--- a/first.txt\n"
            "+++ b/first.txt\n"
            "@@ -1,1 +1,2 @@\n"
            " ctx\n"
            "+clean added line\n"
            "diff --git a/second.txt b/second.txt\n"
            "index c111111..d111111 100644\n"
            "--- a/second.txt\n"
            "+++ b/second.txt\n"
            "@@ -5,1 +5,2 @@\n"
            " another ctx\n"
            "+" + AWS_SECRET + "\n"
        )

    def test_secret_in_second_file_second_hunk_located(self):
        findings = scan.scan_diff(self._diff())
        matches = [f for f in findings if f.type == "aws-access-key-id"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].path, "second.txt")
        self.assertEqual(matches[0].line, 6)


class RegressionUtf8RobustnessTest(unittest.TestCase):
    """(11) A --diff-file whose bytes include a non-UTF-8 byte (0xFF) on a clean added
    line must not crash and must scan cleanly (exit 0)."""

    def test_non_utf8_byte_does_not_crash_clean_exit_0(self):
        diff = (
            "diff --git a/f.txt b/f.txt\n"
            "--- a/f.txt\n"
            "+++ b/f.txt\n"
            "@@ -0,0 +1,1 @@\n"
            "+clean XXX line here\n"
        )
        data = diff.encode("utf-8").replace(b"XXX", b"\xff")
        fd, path = tempfile.mkstemp(suffix=".diff")
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        proc = run_cli(["--diff-file", path])
        self.assertEqual(proc.returncode, 0, f"non-UTF-8 diff crashed: {proc.stderr!r}")


class RegressionHeaderPathNotScannedTest(unittest.TestCase):
    """(12) A secret-SHAPED string appearing in a '+++ b/<path>' header path is
    structural, not content, and must NOT be reported as an added-line finding."""

    def test_secret_shaped_header_path_not_reported(self):
        # A secret-assignment-shaped path token, built at runtime (a shape, not a
        # real credential). It sets the current path but is never scanned.
        shaped_path = "api_key=" + "a" * 12
        diff = (
            "diff --git a/x b/x\n"
            "index aaaaaaa..bbbbbbb 100644\n"
            "--- a/x\n"
            "+++ b/" + shaped_path + "\n"
            "@@ -0,0 +1,1 @@\n"
            "+clean content line\n"
        )
        findings = scan.scan_diff(diff)
        self.assertEqual(
            findings, [], "a secret-shaped header path was scanned as content"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
