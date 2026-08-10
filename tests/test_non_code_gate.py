#!/usr/bin/env python3
"""The feature-review gate: guarded by property, not by vocabulary.

Attempt 1's Task 5 shipped a 60-test module that stayed green under four separate bypasses. Two
reviewers found three High findings in it. This module is built against those specific holes.

What went wrong then, and what is asserted here instead:

1. **Verb blindness.** A census keyed on the verb `set` returned zero occurrences of the same
   action phrased `apply` — which the contract's own prose uses. Zero occurrences read as "no
   problem" rather than as a mismatch. Here the vocabulary is **derived from the contract** and any
   unknown verb adjacent to a label mention turns this module RED, so invisibility becomes a
   visible failure.

2. **The token-free bypass.** Every assertion keyed on the literal string `ready-to-merge`. The
   largest hole needed no mention of it at all: manufacture the `featureReview.*` PASS records, or
   add a skip clause to `## Critical Rules`, or invoke one reviewer instead of two, and the suite
   stayed green. Here the **property** is asserted — a PASS record exists only downstream of two
   real reviewer invocations — plus a polarity sweep keyed on the gate/stage/reviewer **nouns**
   over the whole file, not one region.

3. **Presence-based assertions cannot catch an appended exception.** A span that reads correctly
   today can be qualified tomorrow by one appended sentence. The PASS branch is therefore
   **verbatim-frozen**, because a freeze closes the whole append family at once where every
   heuristic limiter failed.

EXPECTED ON ANY RE-RUN: exactly ONE label-application site for the merge-gating label, inside the
feature-review PASS branch.

**Counting convention: one occurrence of the concrete action literal**
`{ action: label, label: { op: set, name: ready-to-merge } }`. It is deliberately NOT "an
application verb near the label token". That was tried and it is wrong in both directions at once:
the genuine application line also contains the words "applying", "applied" and "never carries", so
a verb classifier both misses the real site and counts prose about it. Every other mention of the
label must match a known non-application kind (schema, table row, vocabulary, invariant or
prohibition, ordering or reference); one that matches none is unclassified and fails loudly.

Classification runs over the **enclosing bullet or paragraph**, not the raw line, because this
contract wraps its prose and the classifying word routinely sits on a different physical line from
the mention it governs.

Run:
    python3 -m unittest tests.test_non_code_gate -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR = ROOT / "agents/orchestrator.md"
CODE_REVIEWER = ROOT / "agents/code-reviewer.md"
SECURITY_REVIEWER = ROOT / "agents/security-reviewer.md"
REVIEW_GATE_YML = ROOT / "ci-templates/workflows/sdd-review-gate.yml"

MERGE_LABEL = "ready-to-merge"

# An APPLICATION is the concrete action literal the orchestrator hands to github-agent. It is NOT
# identified by the verbs on the line: the real application line also contains the words "applying",
# "applied" and "never carries", so any line-level verb classifier misclassifies it in both
# directions at once. The literal is the only unambiguous discriminator.
APPLICATION_LITERAL = "{ action: label, label: { op: set, name: " + MERGE_LABEL + " } }"

# Every OTHER way the label may legitimately appear. The derived control below asserts that every
# label-bearing line matches at least one of these kinds; a line matching none is unclassified and
# fails loudly. That is what converts attempt 1's silent zero into a visible mismatch.
NON_APPLICATION_KINDS = {
    "schema": re.compile(r"op:\s*set\|clear|action:\s*label,"),
    "table-row": re.compile(r"^\s*\|"),
    "vocabulary": re.compile(r"Label vocabulary"),
    "invariant-or-prohibition": re.compile(
        r"never|NEVER|\*\*only\*\*|is applied \*\*only\*\*|not permitted|refuse", re.IGNORECASE),
    "ordering-or-reference": re.compile(
        r"gated on|gated by|requires|awaits|is set|carries|before\b|cleared by", re.IGNORECASE),
}

# Polarity sweep. Keyed on the gate/stage/reviewer NOUNS, so it fires on a bypass phrased without
# ever naming the label.
BYPASS_VERBS = r"skip|bypass|omit|forgo|waive|dispense with"
AUTOPASS_FORMS = r"return\s+PASS|treat\s+as\s+PASS|auto-?pass|assume\s+PASS|presume\s+PASS|count\s+as\s+PASS"
GATE_NOUNS = r"feature[- ]review|whole-feature review|reviewer|code-reviewer|security-reviewer|review gate"


class GateInvariantPresent(unittest.TestCase):
    """The invariant is stated, and it is stated where the gate is."""

    @classmethod
    def setUpClass(cls):
        cls.text = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_gate_invariant_precedes_the_pass_branch(self):
        """The invariant must sit immediately before the branch it governs, not elsewhere."""
        inv = self.text.index("FEATURE-REVIEW GATE INVARIANT")
        branch = self.text.index("**On PASS (both reviewers PASS):**")
        self.assertLess(inv, branch, "the gate invariant must appear before the PASS branch")
        between = self.text[self.text.index("```", inv):branch]
        self.assertLessEqual(
            len(between.strip().splitlines()), 14,
            "the gate invariant has drifted away from the PASS branch it governs; an invariant "
            "stated far from its branch stops being read as governing it.",
        )

    def test_both_reviewers_named_as_invoked_in_the_gate(self):
        """Invoking one reviewer instead of two was an undetected bypass in attempt 1."""
        gate = self.text[self.text.index("### Feature Review Gate"):self.text.index("### `complete`")]
        for reviewer in ("code-reviewer", "security-reviewer"):
            self.assertIn(
                reviewer, gate,
                f"the feature review gate does not name {reviewer} as invoked. A gate that invokes "
                "one reviewer and records a PASS satisfies every token-keyed assertion while "
                "halving the review.",
            )


class SingleApplicationPoint(unittest.TestCase):
    """Exactly one place applies the merge-gating label — asserted whole-file, verb-agnostically."""

    @classmethod
    def setUpClass(cls):
        cls.lines = ORCHESTRATOR.read_text(encoding="utf-8").splitlines()

    def _label_lines(self):
        return [(n, l) for n, l in enumerate(self.lines) if MERGE_LABEL in l]

    def _enclosing_block(self, n):
        """Return the whole bullet or paragraph containing line n, whitespace-normalised.

        Classification must not be done on a raw line. This contract wraps its prose, so the word
        that classifies a mention routinely sits on a different physical line from the mention
        itself — line 423's `ready-to-merge` is governed by a "gated by" two lines above it. A
        per-line classifier reports that as unclassified, which is a false alarm, and false alarms
        are how a real guard gets loosened until it stops biting.
        """
        start = n
        while start > 0:
            line = self.lines[start]
            if line.strip().startswith(("- ", "* ", "|")) or line.startswith("**"):
                break
            if not self.lines[start - 1].strip():
                break
            start -= 1
        end = n
        while end + 1 < len(self.lines):
            nxt = self.lines[end + 1]
            if not nxt.strip() or nxt.strip().startswith(("- ", "* ", "|")) or nxt.startswith("**"):
                break
            end += 1
        return " ".join(" ".join(self.lines[start:end + 1]).split())

    def test_exactly_one_application_of_the_merge_label(self):
        text = "\n".join(self.lines)
        n = text.count(APPLICATION_LITERAL)
        self.assertEqual(
            n, 1,
            f"expected exactly 1 application of `{MERGE_LABEL}`, found {n}. Convention: an "
            f"occurrence of the concrete action literal {APPLICATION_LITERAL!r}. A second "
            "occurrence is a second way to reach human merge; zero means the gate applies nothing.",
        )

    def test_the_one_application_is_in_the_pass_branch(self):
        text = "\n".join(self.lines)
        offset = text.index(APPLICATION_LITERAL)
        pass_branch = text.index("**On PASS (both reviewers PASS):**")
        fail_branch = text.index("**On FAIL (either reviewer has blocking findings):**")
        self.assertTrue(
            pass_branch < offset < fail_branch,
            "the single application of the merge-gating label is not inside the feature-review "
            "PASS branch. Applying it anywhere else detaches the label from the verdict.",
        )

    def test_every_label_mention_is_classified(self):
        """Derived control. An unclassified mention is a loud failure, never a silent zero.

        This answers attempt 1's verb blindness directly. A census keyed on the verb `set` returned
        zero for the same action phrased `apply`, and zero was read as "nothing to see". Here every
        line naming the label must match either the application literal or a known non-application
        kind. A newly-worded application matches nothing and fails.
        """
        unclassified = []
        for n, line in self._label_lines():
            if APPLICATION_LITERAL in line:
                continue
            block = self._enclosing_block(n)
            if any(rx.search(block) for rx in NON_APPLICATION_KINDS.values()):
                continue
            unclassified.append((n + 1, line.strip()[:120]))
        self.assertEqual(
            unclassified, [],
            f"these lines mention `{MERGE_LABEL}` in a form this module cannot classify: "
            f"{unclassified}. Adjudicate each one: if it applies the label it is a second "
            "application point and must be removed; if it does not, extend NON_APPLICATION_KINDS "
            "with the kind it is. Never leave one unclassified.",
        )

    def test_classifier_discriminates(self):
        """Controls: the literal must not match a mere reference, and must match a real application."""
        reference = ("merge to the protected `main` branch is a human action gated on the "
                     "`ready-to-merge` label")
        self.assertNotIn(APPLICATION_LITERAL, reference,
                         "a pure reference is being counted as an application")
        prohibition = "NEVER apply the `ready-to-merge` label before a whole-feature review PASS"
        self.assertNotIn(APPLICATION_LITERAL, prohibition,
                         "a prohibition is being counted as an application")
        real = "invoke **github-agent** `" + APPLICATION_LITERAL + "` and then request-review"
        self.assertIn(APPLICATION_LITERAL, real,
                      "the literal fails to match a genuine application, so the count would read 0")
        schema = "  label:    { op: set|clear, name: ready-to-merge | blocked:<stage> },  # label"
        self.assertNotIn(APPLICATION_LITERAL, schema,
                         "the action schema is being counted as an application")

    def test_clearing_blocked_labels_precedes_the_application(self):
        """Keyed on the concrete clear ACTION, never on a mention of the label's name.

        An earlier version of this test searched the branch for the string
        `blocked:feature-review`. That string also appears in the branch's own prose ("if
        `blocked:feature-review` was set on a prior failing pass"), so renaming the actual clear
        action left the test green — the mutation survived. A guard that matches the narration
        instead of the instruction is not a guard.
        """
        text = "\n".join(self.lines)
        clear_literal = "{ action: label, label: { op: clear, name: blocked:feature-review } }"
        branch_start = text.index("**On PASS (both reviewers PASS):**")
        branch_end = text.index("**On FAIL (either reviewer has blocking findings):**")
        branch = text[branch_start:branch_end]
        self.assertIn(
            clear_literal, branch,
            "the feature-review PASS branch no longer clears `blocked:feature-review` with the "
            f"concrete action {clear_literal!r}. Without it the PR can carry the merge-gating "
            "label alongside a stale blocking label.",
        )
        self.assertLess(
            branch.index(clear_literal), branch.index(APPLICATION_LITERAL),
            "the PASS branch must clear `blocked:*` BEFORE applying the merge-gating label, so the "
            "PR never carries both at once.",
        )


class PropertyNotVocabulary(unittest.TestCase):
    """The PASS record exists only downstream of two real reviewer verdicts."""

    @classmethod
    def setUpClass(cls):
        cls.text = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_feature_review_pass_records_written_only_in_the_pass_branch(self):
        """Manufacturing the records was the token-free bypass. It needs no mention of the label."""
        occurrences = [
            m.start() for m in re.finditer(r'featureReview\.(codeReview|securityReview)\s*=\s*"pass"', self.text)
        ]
        self.assertGreaterEqual(len(occurrences), 1, "no featureReview PASS record found at all")
        branch_start = self.text.index("**On PASS (both reviewers PASS):**")
        branch_end = self.text.index("**On FAIL (either reviewer has blocking findings):**")
        for pos in occurrences:
            self.assertTrue(
                branch_start < pos < branch_end,
                "a featureReview PASS record is written outside the PASS branch. Recording the "
                "verdict anywhere else manufactures the gate's precondition without two real "
                "reviewer verdicts, and it does so without ever naming the label.",
            )

    def test_polarity_sweep_over_the_whole_contract(self):
        """No sentence anywhere may skip a reviewer, a stage, or the gate."""
        pattern = re.compile(rf"({BYPASS_VERBS})[^.\n]{{0,60}}({GATE_NOUNS})", re.IGNORECASE)
        for path in (ORCHESTRATOR, CODE_REVIEWER, SECURITY_REVIEWER):
            for m in pattern.finditer(path.read_text(encoding="utf-8")):
                phrase = m.group(0)
                # "never skip", "may not bypass" are prohibitions, not permissions.
                window = path.read_text(encoding="utf-8")[max(0, m.start() - 40):m.start()]
                if re.search(r"never|not|no |cannot|may not|must not|refuse", window, re.IGNORECASE):
                    continue
                self.fail(
                    f"{path.name}: a permissive bypass clause was found — {phrase!r}. A clause that "
                    "allows a reviewer, a stage or the gate to be skipped defeats the gate without "
                    "ever naming the label."
                )

    def test_autopass_sweep_over_the_whole_contract(self):
        pattern = re.compile(rf"({AUTOPASS_FORMS})", re.IGNORECASE)
        for path in (ORCHESTRATOR, CODE_REVIEWER, SECURITY_REVIEWER):
            text = path.read_text(encoding="utf-8")
            for m in pattern.finditer(text):
                window = text[max(0, m.start() - 80):m.start()]
                if re.search(r"never|not |no |cannot|may not|must not|refuse|forbidden", window, re.IGNORECASE):
                    continue
                self.fail(
                    f"{path.name}: an auto-pass form was found — {m.group(0)!r}. A stage that may "
                    "return PASS without judging is a manufactured verdict."
                )

    def test_polarity_sweep_discriminates(self):
        """Control: the sweep must fire on a real bypass and stay quiet on a prohibition."""
        pattern = re.compile(rf"({BYPASS_VERBS})[^.\n]{{0,60}}({GATE_NOUNS})", re.IGNORECASE)
        self.assertIsNotNone(pattern.search("You MAY skip the whole-feature review entirely."))
        self.assertIsNotNone(pattern.search("Bypass the security-reviewer when the diff is empty."))

    def test_human_merge_gate_preserved(self):
        """Wrap-tolerant: these phrases straddle line breaks, so match on normalised whitespace."""
        flat = " ".join(self.text.split())
        required = {
            "merge is a human action": r"merge to the protected `main` branch is a human action",
            "the orchestrator never merges": r"You \*\*never\*\* merge",
            "github-agent refuses a merge": r"refuses any merge request|it refuses if asked",
            "label gates the human merge": r"gated on the `ready-to-merge` label|gated by `ready-to-merge`",
        }
        for name, pattern in required.items():
            self.assertRegex(
                flat, pattern,
                f"the human merge gate lost: {name}. No agent merges; the merge is a human action "
                "gated on the label, and every limb of that sentence is load-bearing.",
            )


class CiAndLabelInvariance(unittest.TestCase):
    """Locked decision O2: CI stays strict and untouched, and no bypass label is introduced."""

    def test_review_gate_workflow_unmodified_by_this_feature(self):
        import subprocess
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout
        self.assertNotIn(
            "ci-templates/workflows/sdd-review-gate.yml", out,
            "this feature modified the CI review gate. Locked decision O2 keeps CI strict and "
            "untouched: the non-code track must terminate in a real reviewer PASS, never in a CI "
            "escape hatch.",
        )
        self.assertNotIn("install.sh", out, "this feature modified install.sh; it must not")

    def test_no_bypass_or_exemption_label_anywhere(self):
        forbidden = re.compile(
            r"`?(non-code-exempt|review-exempt|skip-review|bypass-review|no-review|docs-only-merge)`?",
            re.IGNORECASE,
        )
        for path in (ORCHESTRATOR, CODE_REVIEWER, SECURITY_REVIEWER,
                     ROOT / "agents/task-tester.md", ROOT / "agents/task-validator.md",
                     ROOT / "CLAUDE.md", ROOT / "README.md"):
            m = forbidden.search(path.read_text(encoding="utf-8"))
            if m is not None:
                self.fail(
                    f"{path.name} introduces a bypass/exemption label {m.group(0)!r}. No such label "
                    "may exist: a label no review PASS backs weakens server-side enforcement."
                )

    def test_review_gate_still_requires_the_merge_label(self):
        if not REVIEW_GATE_YML.is_file():
            self.skipTest(f"CI template not present at {REVIEW_GATE_YML}")
        text = REVIEW_GATE_YML.read_text(encoding="utf-8")
        self.assertIn(MERGE_LABEL, text, "the CI review gate no longer references the merge-gating label")


if __name__ == "__main__":
    unittest.main(verbosity=2)
