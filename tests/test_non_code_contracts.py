#!/usr/bin/env python3
"""Verbatim freezes over every span this feature's safety rests on.

Both the code review and the security review of commit `2414669` returned FAIL, and both reached
the same conclusion by different routes: **stop enumerating verbs, freeze the span**.

Between them, eleven mutations left a 262-test suite bit-identically green — including four probes
the postmortem had already named and written down (§3.6 probes D, G, H, and M-2/M-3). Every one of
them was a *reworded* instruction, and every guard that missed them was keyed on vocabulary: a
closed set of bypass verbs, a regex requiring the literal `= "pass"`, a check that two reviewer
names merely *appear*. As the postmortem puts it, those guards check that the text says certain
things, never that it says nothing else.

A verbatim freeze inverts that. It does not care how a bypass is worded, because any added,
removed, or reworded sentence inside a frozen span turns the assertion RED. It is also the
technique that finally closed attempt 1's `C12` hole after every heuristic limiter had failed.

Each frozen span lives in `tests/frozen/`. To change a frozen span deliberately: make the contract
edit, re-run `tests/frozen/REGENERATE.md`'s command, and say in the commit message which span moved
and why. Regenerating without saying so defeats the entire mechanism.

EXPECTED ON ANY RE-RUN: 4 frozen spans, all matching. A mismatch is a real
change to a safety-bearing span, never a formatting artefact — the comparison is byte-exact.

Run:
    python3 -m unittest tests.test_non_code_contracts -v
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN = Path(__file__).resolve().parent / "frozen"

ORCHESTRATOR = ROOT / "agents/orchestrator.md"
CODE_REVIEWER = ROOT / "agents/code-reviewer.md"
SECURITY_REVIEWER = ROOT / "agents/security-reviewer.md"
TESTER = ROOT / "agents/task-tester.md"
VALIDATOR = ROOT / "agents/task-validator.md"


def between(path, start, end):
    """Extract the span from `start` up to the next `end`, or raise with a useful message."""
    t = path.read_text(encoding="utf-8")
    try:
        i = t.index(start)
        # "\x00" is the end-of-file sentinel, for a section that runs to the end of the document.
        j = len(t) if end == "\x00" else t.index(end, i)
    except ValueError:
        raise AssertionError(
            f"{path.name}: could not locate the frozen span bounded by {start[:50]!r} .. "
            f"{end[:40]!r}. The span was renamed, moved, or deleted. That is itself the finding — "
            "do not adjust these bounds to make the test pass."
        )
    return t[i:j]


def frozen(name):
    p = FROZEN / name
    if not p.is_file():
        raise AssertionError(f"frozen fixture missing: {p}")
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        raise AssertionError(f"frozen fixture {name} is empty; comparing against it proves nothing")
    return text


# (fixture, path, start bound, end bound, why it is frozen)
SPANS = [
    ("tester_failsafe.md", TESTER, "\n## When the Task Produces No Application Code\n",
     "\n## Completion Summary",
     "the WHOLE no-code section, not just the entry condition. The narrow version froze 5 lines "
     "and stopped immediately before the prohibitions, leaving FR-4.1 (no vacuous tests), FR-4.2 "
     "(write the machine check), FR-4.4 (still run existing tests) and FR-4.5 (report application "
     "code) pinned by nothing at all"),
    ("validator_failsafe.md", VALIDATOR, "\n## Artifact-Conformance Mode\n", "\n## Verdict",
     "the WHOLE mode section. The narrow version stopped at 'In this mode:', so the entry "
     "condition was frozen but FR-5.2 through FR-5.9 - the artifact mapping, the placeholder "
     "rule, the machine-check run, and the exemption refusal - were not"),
    ("code_reviewer_noncode.md", CODE_REVIEWER, "\n## Non-Code and Empty Scope\n", "\n## Severity",
     "the WHOLE non-code section, not the paragraph a probe last hit. A re-review defeated a "
     "narrower freeze by planting an auto-PASS one line above it -- 'conclude the review with a "
     "PASS verdict' -- which no verb list matched. Freezing the section closes that family"),
    ("security_reviewer_noncode.md", SECURITY_REVIEWER, "\n## Non-Code and Empty Scope\n",
     "\n## Severity", "as above, for the security reviewer"),
]


class FrozenSpans(unittest.TestCase):
    """Every safety-bearing span matches its recorded text byte for byte."""

    def test_all_spans_match(self):
        for name, path, start, end, why in SPANS:
            with self.subTest(span=name):
                self.assertEqual(
                    between(path, start, end), frozen(name),
                    f"\n\nFROZEN SPAN CHANGED: {name} in {path.name}\n"
                    f"Why it is frozen: {why}.\n"
                    "Any added, removed or reworded sentence inside this span turns this RED, "
                    "by design — that is the point of a freeze, and it is what a verb-keyed guard "
                    "could not do. If the change is deliberate, regenerate the fixture and say in "
                    "the commit message which span moved and why.",
                )

    def test_every_span_bound_resolves_unambiguously(self):
        """A bound occurring twice would silently re-point the span at the wrong text."""
        for name, path, start, end, _why in SPANS:
            with self.subTest(span=name):
                body = path.read_text(encoding="utf-8")
                self.assertEqual(
                    body.count(start), 1,
                    f"{name}: its start bound {start[:50]!r} occurs {body.count(start)} times in "
                    f"{path.name}. The span would resolve to the first one, which may not be the "
                    "text you meant to freeze.",
                )

    def test_fixture_count_matches_the_span_list(self):
        # REGENERATE.md documents the mechanism; it is not itself a frozen span.
        found = sorted(p.name for p in FROZEN.glob("*.md") if p.name != "REGENERATE.md")
        self.assertEqual(
            len(found), len(SPANS),
            f"expected {len(SPANS)} frozen fixtures, found {len(found)}: {found}. An unused fixture "
            "means a span stopped being checked.",
        )

class ClassificationProperties(unittest.TestCase):
    """What remains prose after the classifier moved into scripts/classify_feature.py.

    The artifact categories, the asymmetric precedence, the designation check and the
    feature-directory rule are no longer asserted here: they are executable now, and
    tests/test_classify_feature.py exercises them with real tasks.md content instead of grepping
    for wording. What stays here is the wiring — that the orchestrator actually runs the script,
    and that the triggers around it are present.
    """

    @classmethod
    def setUpClass(cls):
        cls.orch = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_the_contract_runs_the_classifier_rather_than_restating_the_rules(self):
        """The rules are executable now; the contract must invoke them, not paraphrase them."""
        self.assertIn("scripts/classify_feature.py", self.orch,
                      "the contract no longer invokes the classifier, so nothing classifies")
        self.assertNotIn("CLS — ARTIFACT CLASSIFICATION", self.orch,
                         "the superseded prose rules have returned alongside the script; two "
                         "copies of a classification rule is the drift surface this removed")

    def test_classifier_unavailable_falls_back_to_code(self):
        """The fail-safe direction survives the move to code."""
        flat = " ".join(self.orch.split())
        self.assertIn("classifier-unavailable", flat)
        self.assertIn("treat the feature as `\"code\"`", flat)

    def test_feature_level_ambiguity_triggers_are_not_subordinate(self):
        for trigger in ("`AMB-F1` *(feature-level; always applies)*",
                        "`AMB-F2` *(feature-level; always applies)*"):
            self.assertIn(trigger, self.orch,
                          f"{trigger} lost its feature-level scope. A symmetric rule disables the "
                          "feature-level triggers, which is the defect attempt 1's A4 shipped.")
        self.assertIn("`AMB-C1` *(file-classifying; subordinate to the enumeration)*", self.orch)

    def test_all_three_reclassification_triggers_present(self):
        for rt in ("`RT-1`", "`RT-2`", "`RT-3`"):
            self.assertIn(rt, self.orch, f"reclassification trigger {rt} is missing")
        self.assertIn("**monotonic**", self.orch, "reclassification is no longer stated as monotonic")

    def test_scaffolding_never_triggers_reclassification(self):
        self.assertIn("never triggers reclassification and never affects classification", self.orch)


class ReceiverFailSafes(unittest.TestCase):
    """Both receivers must fail toward MORE checking, never toward an exemption."""

    def test_tester_enters_only_on_an_explicit_false(self):
        t = TESTER.read_text(encoding="utf-8")
        self.assertIn("Enter here only where its value is `false`", t)
        self.assertIn("Never select this behaviour", " ".join(t.split()))

    def test_validator_enters_only_on_an_explicit_false(self):
        t = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("**Enter this mode only where `taskProducesApplicationCode` is `false`.**", t)
        self.assertIn("Never select this mode yourself", t)

    def test_exemption_refusal_judges_the_executor_not_the_task(self):
        """One word, and it decides whether a legitimate non-code feature survives.

        The tester's own FR-4.2 machine check lands in the project's test directory, which the
        transmitted CLS block calls application code. If the validator refuses the exemption
        whenever "the task" modified application code, the tester's legitimate output triggers a
        reclassification of the very feature it was validating — and reclassification is monotonic,
        so nothing undoes it. Judging the EXECUTOR's output is what keeps that closed.
        """
        flat = " ".join(VALIDATOR.read_text(encoding="utf-8").split())
        self.assertIn(
            "If the executor modified application code, refuse the exemption.", flat,
            "the exemption-refusal bullet no longer names the executor. Worded as 'the task', the "
            "tester's own machine check spuriously reclassifies a legitimate non-code feature.",
        )
        self.assertNotIn(
            "If the task modified application code", flat,
            "the superseded 'the task' wording has returned",
        )

    def test_code_path_test_coverage_line_is_untouched(self):
        """Discrimination control: removing it would make the mode assertions prove nothing."""
        t = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("- [ ] Does at least one test exist for this requirement?", t)


class ReviewerScopeDefinition(unittest.TestCase):
    """Both reviewers must INVOKE the classifier, not carry a second copy of its rules.

    They used to hold a prose definition of a non-code artifact. It was correct, and it was a
    second source of truth: a prose copy alongside the script can disagree with it, and only one
    of the two is tested. Those assertions are replaced, not deleted — the risk changed direction
    rather than disappearing.
    """

    def test_both_reviewers_run_the_classifier_over_their_diff(self):
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            with self.subTest(contract=path.name):
                t = path.read_text(encoding="utf-8")
                self.assertIn(
                    "scripts/classify_feature.py", t,
                    f"{path.name} does not invoke the classifier, so it decides by eye whether its "
                    "diff is non-code — and an all-markdown diff of agent contracts reads as prose.",
                )
                self.assertIn("--paths", t, f"{path.name} does not use the reviewer mode")

    def test_neither_reviewer_restates_the_classification_rules(self):
        """A second copy of the rules is the drift surface this change removes."""
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            with self.subTest(contract=path.name):
                flat = " ".join(path.read_text(encoding="utf-8").split())
                for superseded in ("A non-code artifact is exactly one of",
                                   "CLS — ARTIFACT CLASSIFICATION"):
                    self.assertNotIn(
                        superseded, flat,
                        f"{path.name} has reintroduced the classification rules in prose alongside "
                        "the script that owns them",
                    )

    def test_both_reviewers_state_the_fail_safe_direction(self):
        """If the classifier cannot run, review it as code. Never self-classify."""
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            with self.subTest(contract=path.name):
                flat = " ".join(path.read_text(encoding="utf-8").split())
                self.assertIn("If the classifier cannot run, treat the diff as application code", flat)
                self.assertIn("Never fall back to classifying it yourself.", flat)

    def test_the_instruction_is_identical_in_both_contracts(self):
        spans = [between(p, "**Deciding whether your diff is a non-code diff",
                         "\n**Review scope is not produced output.**")
                 for p in (CODE_REVIEWER, SECURITY_REVIEWER)]
        self.assertEqual(spans[0], spans[1],
                         "the two reviewers' classifier instructions have diverged")


if __name__ == "__main__":
    unittest.main(verbosity=2)
