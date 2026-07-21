#!/usr/bin/env python3
"""Anti-bypass tests for the Task 11 allowlist remediation of the shared secret scanner.

Task 11 adds two NARROW suppression mechanisms to `ci-templates/scripts/sdd-secret-scan.py`
(and its byte-identical `.github/scripts/` dogfood copy) so the scanner runs clean over the
framework's own tree WITHOUT weakening detection anywhere else:

  * an inline `pragma: allowlist secret` marker that suppresses ONLY its own added line, and
  * an EXPLICIT, ENUMERATED path-exclude list (no globs) covering the framework's own
    secret-pattern definitions and dedicated secret-fixture files.

Because an allowlist is a natural bypass vector, this suite is deliberately adversarial: it
PROVES that neither mechanism opens a hole. Every "positive" (suppressed) case is paired with a
"negative" (still-detected) sibling in the SAME diff, so the tests fail loudly if the suppression
ever became broader than one line / one enumerated path.

Covers FR-13 (detection still fires), FR-16 / NFR-3 (CI mirrors the local gate — exit contract),
FR-21 (the dogfood gate goes green over the feature diff), and NFR-2 (no value leak, ever).

Secret hygiene: every secret-shaped fixture is assembled from fragments at RUNTIME
(e.g. "ghp_" + "A"*36) so no whole secret literal is ever committed to this file, and every
no-leak assertion is BOOLEAN so a failure never echoes a fixture value. This file is NOT on the
scanner's exclude list, so a dedicated test verifies the file stays clean under the scanner.

Stdlib only (unittest + importlib + subprocess + tempfile + filecmp + os). The target module
filename is hyphenated, so it is loaded via importlib.util from a path resolved relative to this
test so the suite survives consolidation onto feat/github-agent.

Run:
    python3 -m unittest tests.test_sdd_secret_scan_allowlist -v
    # or
    python3 tests/test_sdd_secret_scan_allowlist.py
"""

import filecmp
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_PATH = ROOT / "ci-templates" / "scripts" / "sdd-secret-scan.py"
DOGFOOD_SCAN_PATH = ROOT / ".github" / "scripts" / "sdd-secret-scan.py"


def load_scan_module():
    """Load ci-templates/scripts/sdd-secret-scan.py despite its hyphenated name."""
    spec = importlib.util.spec_from_file_location("sdd_secret_scan_allowlist_tgt", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scan = load_scan_module()

# --- Runtime-built secret-shaped fixtures (NEVER a whole literal in source) ----
# Assembled from fragments so no complete credential literal is committed. Each is
# shaped to match exactly one vendored pattern family.
GH_SECRET = "ghp_" + "A" * 36                       # github-token
AWS_SECRET = "AKIA" + "A" * 16                       # aws-access-key-id
SLACK_SECRET = "xoxb-" + "B" * 12                    # slack-token
# A secret-assignment-shaped line resembling the Task-9 framework false positives
# (a `<word>secret<word> = <8+ chars>` shape). Assembled from fragments at RUNTIME so
# the contiguous shape never appears as a literal in THIS source file.
ASSIGNMENT_FP = "SECRET" + "_SCAN = " + "WORKFLOW" + "_DIR"
# A pre-push-style advisory line (assembled below from fragments) that trips the
# assignment family, resembling ci-templates/hooks/pre-push line 197.
PREPUSH_FP = 'say "  - ' + "secret" + '-scan: potential secret in the pushed range."'

MARKER = scan.PRAGMA_MARKER  # the exact inline allowlist token (not a secret)


def one_file_diff(path, added_lines, new_start=1):
    """Build a minimal one-file, one-hunk unified diff whose body is only added lines."""
    body = "".join("+" + ln + "\n" for ln in added_lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"index 0000000..1111111 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +{new_start},{len(added_lines)} @@\n"
        f"{body}"
    )


def run_cli(args, input_bytes=None):
    """Invoke the scanner as the real CLI; return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCAN_PATH)] + args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# ---------------------------------------------------------------------------
# MANDATORY ANTI-BYPASS TESTS (1-5) — the whole point of Task 11.
# ---------------------------------------------------------------------------


class DetectionStillFiresTest(unittest.TestCase):
    """(1) A real secret on a NON-excluded path with NO pragma is STILL detected — the
    allowlist did not disable the gate (FR-13, FR-16/NFR-3 exit contract)."""

    def test_secret_on_ordinary_path_detected(self):
        diff = one_file_diff("src/app.py", ["token = " + GH_SECRET])
        findings = scan.scan_diff(diff)
        self.assertTrue(findings, "secret on an ordinary path was not detected")
        self.assertTrue(
            any(f.type == "github-token" for f in findings),
            "github-token shape not detected on src/app.py",
        )
        self.assertTrue(any(f.path == "src/app.py" for f in findings))

    def test_cli_exit_1_on_ordinary_path_secret(self):
        diff = one_file_diff("src/app.py", ["token = " + GH_SECRET])
        proc = run_cli(["--diff-file", "-"], input_bytes=diff.encode())
        self.assertEqual(proc.returncode, 1, "exit code is not 1 for a detected secret")


class PragmaIsLineScopedTest(unittest.TestCase):
    """(2) The inline pragma suppresses ONLY its exact added line — not the file, not a
    neighbouring added line in the same hunk."""

    def _diff(self):
        # Line 1 carries the marker (suppressed); line 2 is the SAME secret with NO
        # marker (must still be detected). Same file, same hunk.
        return one_file_diff(
            "src/config.py",
            [
                GH_SECRET + "  # " + MARKER,   # new line 1 -> suppressed
                GH_SECRET,                      # new line 2 -> still detected
            ],
        )

    def test_marker_line_suppressed_neighbor_detected(self):
        findings = scan.scan_diff(self._diff())
        gh = [f for f in findings if f.type == "github-token"]
        self.assertEqual(len(gh), 1, "pragma did not suppress exactly one line")
        self.assertEqual(gh[0].line, 2, "the surviving finding is not the non-marker line")

    def test_marker_line_number_not_reported(self):
        findings = scan.scan_diff(self._diff())
        self.assertFalse(
            any(f.line == 1 for f in findings),
            "the pragma-marked line 1 leaked into findings",
        )

    def test_marker_does_not_suppress_whole_file(self):
        # Three added lines: marker on the middle line only; the two flanking secrets
        # must both survive.
        diff = one_file_diff(
            "src/multi.py",
            [AWS_SECRET, AWS_SECRET + " # " + MARKER, AWS_SECRET],
        )
        findings = scan.scan_diff(diff)
        aws = sorted(f.line for f in findings if f.type == "aws-access-key-id")
        self.assertEqual(aws, [1, 3], "marker suppressed more than its own line")


class PathExcludeIsPerPathTest(unittest.TestCase):
    """(3) A path exclude is per-path, not global: a secret on an excluded path is
    skipped, but a secret on a NON-excluded sibling in the SAME diff is still detected."""

    def _diff(self):
        excluded = "hooks/secret-guard.py"      # on DEFAULT_EXCLUDED_PATHS
        sibling = "hooks/some_other_module.py"   # NOT excluded
        self.assertIn(excluded, scan.DEFAULT_EXCLUDED_PATHS)
        self.assertNotIn(sibling, scan.DEFAULT_EXCLUDED_PATHS)
        return (
            one_file_diff(excluded, ["token = " + GH_SECRET])
            + one_file_diff(sibling, ["token = " + GH_SECRET])
        )

    def test_excluded_path_skipped_sibling_detected(self):
        findings = scan.scan_diff(self._diff())
        paths = {f.path for f in findings}
        self.assertNotIn(
            "hooks/secret-guard.py", paths, "excluded path was still scanned"
        )
        self.assertIn(
            "hooks/some_other_module.py", paths, "non-excluded sibling was skipped"
        )


class ExcludeListIsEnumeratedNotGlobTest(unittest.TestCase):
    """(4) The exclude list is exact/enumerated, not a broad glob: a secret on the
    listed `tests/test_sdd_secret_scan.py` is skipped, but a secret on a DIFFERENT test
    file NOT on the list is still detected. Guards against a `tests/**`-style glob."""

    def _diff(self):
        listed = "tests/test_sdd_secret_scan.py"        # on DEFAULT_EXCLUDED_PATHS
        unlisted = "tests/test_something_else.py"        # a test file NOT on the list
        self.assertIn(listed, scan.DEFAULT_EXCLUDED_PATHS)
        self.assertNotIn(unlisted, scan.DEFAULT_EXCLUDED_PATHS)
        return (
            one_file_diff(listed, ["token = " + GH_SECRET])
            + one_file_diff(unlisted, ["token = " + GH_SECRET])
        )

    def test_listed_test_file_skipped_other_test_file_detected(self):
        findings = scan.scan_diff(self._diff())
        paths = {f.path for f in findings}
        self.assertNotIn(
            "tests/test_sdd_secret_scan.py", paths, "enumerated test file was scanned"
        )
        self.assertIn(
            "tests/test_something_else.py",
            paths,
            "a non-listed test file was skipped — exclude is a glob, not enumerated",
        )


class ExcludeListStructuralGuardTest(unittest.TestCase):
    """(4b) Structural guard: the exclude collection is a tight enumerated set of explicit
    repo-relative strings with NO glob metacharacter — no broad pattern crept in."""

    def test_is_frozenset_of_explicit_strings(self):
        self.assertIsInstance(scan.DEFAULT_EXCLUDED_PATHS, frozenset)
        self.assertTrue(all(isinstance(p, str) for p in scan.DEFAULT_EXCLUDED_PATHS))

    def test_no_glob_metacharacters(self):
        for p in scan.DEFAULT_EXCLUDED_PATHS:
            with self.subTest(path=p):
                for meta in ("*", "?", "[", "]"):
                    self.assertNotIn(
                        meta, p, f"exclude entry {p!r} contains glob metachar {meta!r}"
                    )

    def test_expected_enumerated_membership(self):
        expected = {
            "hooks/secret-redact.py",
            "hooks/secret-guard.py",
            "hooks/README.md",
            "ci-templates/scripts/sdd-secret-scan.py",
            ".github/scripts/sdd-secret-scan.py",
            "tests/test_sdd_secret_scan.py",
            "tests/test_secret_guard_gh.py",
        }
        self.assertEqual(set(scan.DEFAULT_EXCLUDED_PATHS), expected)


class PragmaMarkerBoundaryTest(unittest.TestCase):
    """(5) The pragma marker must be the EXACT token. The impl suppresses a line iff the
    full marker string is a substring of that line. Near-misses and unrelated comments do
    NOT suppress; only the exact token does."""

    def _detected(self, comment):
        diff = one_file_diff("src/edge.py", [GH_SECRET + "  # " + comment])
        return any(f.type == "github-token" for f in scan.scan_diff(diff))

    def test_near_miss_pragma_allow_secret_does_not_suppress(self):
        self.assertTrue(self._detected("pragma: allow secret"),
                        "'pragma: allow secret' wrongly suppressed the finding")

    def test_partial_allowlist_secret_does_not_suppress(self):
        # "allowlist secret" alone lacks the leading "pragma: " of the full marker.
        self.assertTrue(self._detected("allowlist secret"),
                        "'allowlist secret' alone wrongly suppressed the finding")

    def test_random_comment_does_not_suppress(self):
        self.assertTrue(self._detected("just a normal comment"),
                        "an unrelated comment wrongly suppressed the finding")

    def test_exact_marker_does_suppress(self):
        self.assertFalse(self._detected(MARKER),
                         "the exact allowlist marker failed to suppress its own line")


# ---------------------------------------------------------------------------
# REGRESSION / INTENT TESTS (6-10) — the Task-9 false positives, byte-identity,
# no-leak, and the end-to-end dogfood acceptance.
# ---------------------------------------------------------------------------


class FrameworkFalsePositivesSuppressedTest(unittest.TestCase):
    """(6) The known Task-9 framework false positives no longer fire — and each is proven
    to be suppressed by the RIGHT mechanism (path-exclude vs. pragma), never a blanket."""

    def test_secret_assignment_on_excluded_scanner_path_suppressed(self):
        # A secret-assignment-shaped line attributed to an excluded scanner path.
        diff = one_file_diff("ci-templates/scripts/sdd-secret-scan.py", [ASSIGNMENT_FP])
        self.assertEqual(scan.scan_diff(diff), [], "excluded scanner path still flagged")

    def test_secret_guard_pattern_line_on_excluded_path_suppressed(self):
        diff = one_file_diff("hooks/secret-guard.py", ["token = " + GH_SECRET])
        self.assertEqual(scan.scan_diff(diff), [], "excluded guard path still flagged")

    def test_prepush_line_suppressed_by_pragma_not_path(self):
        # pre-push is NOT on the exclude list, so it must rely on the inline pragma.
        path = "ci-templates/hooks/pre-push"
        self.assertNotIn(path, scan.DEFAULT_EXCLUDED_PATHS)
        with_pragma = one_file_diff(path, [PREPUSH_FP + "  # " + MARKER])
        without_pragma = one_file_diff(path, [PREPUSH_FP])
        self.assertEqual(
            scan.scan_diff(with_pragma), [],
            "pragma'd pre-push line still flagged",
        )
        self.assertTrue(
            scan.scan_diff(without_pragma),
            "the pre-push line is not secret-shaped — the fixture is stale, not a real regression proof",
        )

    def test_ci_template_test_line_suppressed_by_pragma_not_path(self):
        # tests/test_ci_workflow_templates.py is NOT on the exclude list -> relies on pragma.
        path = "tests/test_ci_workflow_templates.py"
        self.assertNotIn(path, scan.DEFAULT_EXCLUDED_PATHS)
        with_pragma = one_file_diff(path, [ASSIGNMENT_FP + "  # " + MARKER])
        without_pragma = one_file_diff(path, [ASSIGNMENT_FP])
        self.assertEqual(
            scan.scan_diff(with_pragma), [],
            "pragma'd test_ci_workflow_templates line still flagged",
        )
        self.assertTrue(
            scan.scan_diff(without_pragma),
            "the assignment fixture is not secret-shaped — stale fixture, not a real proof",
        )


class ByteIdentityTest(unittest.TestCase):
    """(7) The two scanner copies remain byte-identical after the Task-11 edits (FR-21)."""

    def test_scanner_copies_byte_identical(self):
        self.assertTrue(DOGFOOD_SCAN_PATH.exists(), f"missing dogfood copy: {DOGFOOD_SCAN_PATH}")
        self.assertTrue(
            filecmp.cmp(SCAN_PATH, DOGFOOD_SCAN_PATH, shallow=False),
            "ci-templates and .github scanner copies diverged after Task 11",
        )


class NoValueLeakTest(unittest.TestCase):
    """(8) NFR-2: suppressed or reported, the scanner never emits a secret value and the
    Finding record structurally cannot carry one."""

    def test_finding_has_no_value_field(self):
        self.assertEqual(scan.Finding._fields, ("type", "path", "line"))

    def test_report_never_contains_value(self):
        diff = one_file_diff("src/app.py", ["token = " + GH_SECRET])
        findings = scan.scan_diff(diff)
        report = scan.format_findings(findings)
        self.assertTrue(GH_SECRET not in report, "report leaked the secret value")

    def test_cli_output_never_contains_value(self):
        diff = one_file_diff("src/app.py", ["token = " + GH_SECRET])
        proc = run_cli(["--diff-file", "-"], input_bytes=diff.encode())
        combined = proc.stdout + proc.stderr
        self.assertTrue(
            GH_SECRET.encode() not in combined, "CLI output leaked the secret value"
        )


class PyCompileBothScannersTest(unittest.TestCase):
    """Both scanner files must byte-compile after the Task-11 edits."""

    def test_py_compile_both(self):
        for path in (SCAN_PATH, DOGFOOD_SCAN_PATH):
            with self.subTest(path=str(path)):
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(path)],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, f"py_compile failed: {result.stderr}")


class ThisTestFileStaysCleanTest(unittest.TestCase):
    """The test file itself must NOT become a new scanner false positive: scanning a diff
    that adds this very file must report ZERO findings (fragment-assembled fixtures)."""

    def test_scanning_this_file_is_clean(self):
        this_rel = "tests/" + Path(__file__).name
        self.assertNotIn(this_rel, scan.DEFAULT_EXCLUDED_PATHS,
                         "this test relies on the file NOT being excluded")
        added = Path(__file__).read_text(encoding="utf-8").split("\n")
        diff = one_file_diff(this_rel, added)
        findings = scan.scan_diff(diff)
        self.assertEqual(
            [f"{f.path}:{f.line} [{f.type}]" for f in findings],
            [],
            "this test file is itself a scanner false positive",
        )


@unittest.skipUnless(shutil.which("git"), "git not on PATH — feature-diff acceptance skipped")
class FeatureDiffAcceptanceTest(unittest.TestCase):
    """(10) End-to-end acceptance (FR-21): the whole feature diff, scanned through the CLI,
    now reports ZERO findings / exit 0 — proving the dogfood secret-scan gate goes green."""

    def _feature_diff(self):
        """Compute the feature diff. Prefer `git diff main` (working tree vs main tip so the
        uncommitted Task-11 edits are included). Fall back to the merge-base, then the empty
        tree, matching how the executor computed it. Returns diff text or None if git can't
        produce one here."""
        for args in (["diff", "main"], ["diff", "HEAD"]):
            proc = subprocess.run(
                ["git", "-C", str(ROOT)] + args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.decode("utf-8", "replace"), args
        return None, None

    def test_feature_diff_scans_clean(self):
        diff_text, args = self._feature_diff()
        if diff_text is None:
            self.skipTest("could not compute a non-empty feature diff in this worktree")
        # Scan via the CLI over a temp diff file (the real gate path).
        fd, path = tempfile.mkstemp(suffix=".diff")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(diff_text)
            proc = run_cli(["--diff-file", path])
            # Never echo the diff; report only counts on failure.
            findings = scan.scan_diff(diff_text)
            self.assertEqual(
                proc.returncode, 0,
                f"feature diff ({' '.join(args)}) is not clean: "
                f"{len(findings)} finding(s) at "
                f"{[f'{f.path}:{f.line}[{f.type}]' for f in findings]}",
            )
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
