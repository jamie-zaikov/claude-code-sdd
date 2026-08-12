#!/usr/bin/env python3
"""Real unit tests for `scripts/classify_feature.py` — inputs in, classification out.

This is the point of moving classification out of prose. Every earlier test of this behaviour
could only grep an agent contract for wording, which proves a paragraph exists and never that it
runs; the classification gate shipped **uninvoked** with a fully green suite. These tests feed the
classifier actual `tasks.md` content and assert the answer.

The safety property under test is the **asymmetry**: application code settles unconditionally,
non-code settles only if the designation check passes, and a failed or unrun check designates
application code. Every uncertain input must come out `"code"`. Attempt 1 shipped a symmetric
version of this rule and had to fix it, and nothing held the fix in place.

EXPECTED ON ANY RE-RUN: 21 tests, 21 pass. Counting convention: one test method each.

Run:
    python3 -m unittest tests.test_classify_feature -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from classify_feature import (  # noqa: E402
    classify_feature, classify_path, parse_declared_outputs,
)

FEATURE = "demo-feature"


def tasks(*blocks):
    """Build a minimal tasks.md from (number, files-line) pairs."""
    out = []
    for n, files in blocks:
        out.append(f"### Task {n}: something")
        if files is not None:
            out.append(f"**Files:** {files}")
        out.append("")
    return "\n".join(out)


class PathClassification(unittest.TestCase):
    """The asymmetry, path by path."""

    def c(self, path, designations=""):
        return classify_path(path, FEATURE, designations)[0]

    def test_agent_contracts_are_application_code(self):
        self.assertEqual(self.c("agents/orchestrator.md"), "code")
        self.assertEqual(self.c("commands/sdd-init.md"), "code")

    def test_executables_and_config_are_application_code(self):
        for p in ("scripts/x.py", "hooks/pre-push.sh", ".github/workflows/ci.yml", "tests/t.py"):
            with self.subTest(path=p):
                self.assertEqual(self.c(p), "code")

    def test_markdown_alone_does_not_make_a_file_non_code(self):
        """The counterintuitive case, and the one a reviewer got wrong in prose."""
        self.assertEqual(self.c("agents/code-reviewer.md"), "code")

    def test_spec_artifacts_settle_without_the_check(self):
        for name in ("requirements.md", "design.md", "tasks.md", "scope.md"):
            with self.subTest(name=name):
                self.assertEqual(self.c(f".specs/features/{FEATURE}/{name}"), "non-code")

    def test_recon_writeup_in_the_feature_directory_is_non_code(self):
        """The feature's headline case. A prose bug once classified this as application code."""
        self.assertEqual(self.c(f".specs/features/{FEATURE}/recon.md"), "non-code")

    def test_vault_changelog_is_non_code(self):
        self.assertEqual(self.c("vault/.write-log.jsonl"), "non-code")

    def test_ordinary_documentation_is_non_code(self):
        self.assertEqual(self.c("docs/how-it-works.md"), "non-code")

    def test_designated_prose_is_application_code(self):
        """The designation check: the project says this file is behaviour-bearing."""
        designations = "Agents must follow docs/house-rules.md at all times."
        self.assertEqual(self.c("docs/house-rules.md", designations), "code")
        self.assertEqual(self.c("docs/house-rules.md", ""), "non-code")  # control

    def test_conventional_instruction_locations_are_code_even_when_undesignated(self):
        """Silence is not an exemption. `.github/copilot-instructions.md` is the live instance."""
        self.assertEqual(self.c(".github/copilot-instructions.md"), "code")
        self.assertEqual(self.c("prompts/system.md"), "code")

    def test_unrun_check_is_a_failed_check(self):
        """The load-bearing half of the asymmetry."""
        self.assertEqual(classify_path("docs/x.md", FEATURE, None)[0], "code")

    def test_check_refuses_to_follow_a_credential_path(self):
        self.assertEqual(self.c("config/.env.example"), "code")
        self.assertEqual(self.c("deploy/secret-notes.md"), "code")

    def test_unknown_extension_resolves_to_code(self):
        """AMB-C1: unresolved by the check means application code, never a guess at non-code."""
        self.assertEqual(self.c("data/blob.bin"), "code")


class FeatureClassification(unittest.TestCase):
    """Whole-feature derivation from declared outputs."""

    def test_all_tasks_non_code_gives_non_code(self):
        md = tasks((1, f"`.specs/features/{FEATURE}/recon.md`"), (2, "`docs/summary.md`"))
        self.assertEqual(classify_feature(md, FEATURE)["featureClass"], "non-code")

    def test_any_task_with_code_makes_the_feature_code(self):
        md = tasks((1, f"`.specs/features/{FEATURE}/recon.md`"), (2, "`scripts/gen.py`"))
        self.assertEqual(classify_feature(md, FEATURE)["featureClass"], "code")

    def test_a_task_declaring_no_outputs_is_amb_f1_and_forces_code(self):
        md = tasks((1, "`docs/a.md`"), (2, None))
        r = classify_feature(md, FEATURE)
        self.assertEqual(r["featureClass"], "code")
        self.assertTrue(any("AMB-F1" in a for a in r["ambiguity"]))

    def test_no_tasks_at_all_is_amb_f2_and_forces_code(self):
        r = classify_feature("# Tasks\n\nnothing here\n", FEATURE)
        self.assertEqual(r["featureClass"], "code")
        self.assertTrue(any("AMB-F2" in a for a in r["ambiguity"]))

    def test_basis_records_every_task_and_its_reason(self):
        """FR-1.5: which tasks drove the decision must be recoverable without re-reading tasks.md."""
        md = tasks((1, "`docs/a.md`"), (2, "`agents/x.md`"))
        basis = classify_feature(md, FEATURE)["basis"]
        self.assertEqual([b["task"] for b in basis], [1, 2])
        self.assertEqual(basis[1]["class"], "code")
        self.assertTrue(any("agents/" in r for r in basis[1]["reasons"]))

    def test_null_is_never_a_permitted_value(self):
        for md in ("", "# no tasks", tasks((1, None))):
            with self.subTest(md=md[:20]):
                self.assertIn(classify_feature(md, FEATURE)["featureClass"], ("code", "non-code"))


class Parsing(unittest.TestCase):

    def test_backticked_and_bare_declarations_both_parse(self):
        self.assertEqual(parse_declared_outputs("### Task 1: x\n**Files:** `a.md`, `b.md`\n"),
                         [(1, ["a.md", "b.md"])])
        self.assertEqual(parse_declared_outputs("### Task 2: x\n**Files:** a.md, b.md\n"),
                         [(2, ["a.md", "b.md"])])

    def test_annotations_after_a_path_do_not_break_parsing(self):
        got = parse_declared_outputs("### Task 1: x\n**Files:** `agents/a.md` (new)\n")
        self.assertEqual(got, [(1, ["agents/a.md"])])


class CommandLine(unittest.TestCase):
    """The contract tells the orchestrator to run this. Prove it runs."""

    def test_runs_against_a_real_feature_and_emits_json(self):
        feats = sorted((ROOT / ".specs" / "features").glob("*/tasks.md"))
        if not feats:
            self.skipTest("no feature with a tasks.md in this repo")
        name = feats[0].parent.name
        r = subprocess.run([sys.executable, "scripts/classify_feature.py", name],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertIn(data["featureClass"], ("code", "non-code"))

    def test_missing_feature_exits_non_zero(self):
        r = subprocess.run([sys.executable, "scripts/classify_feature.py", "no-such-feature"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
