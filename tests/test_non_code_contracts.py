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

EXPECTED ON ANY RE-RUN: 5 frozen spans, all matching. A mismatch is a real
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
    ("cls_block.md", ORCHESTRATOR, "CLS — ARTIFACT CLASSIFICATION", "\n```",
     "the artifact classification, its asymmetric PRECEDENCE, the FEATURE-DIRECTORY RULE, and the "
     "CHECK. Attempt 1 shipped a symmetric PRECEDENCE and had to fix it; nothing held it in place"),
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
    """Semantic pins, in addition to the freeze — they survive a deliberate regeneration."""

    @classmethod
    def setUpClass(cls):
        cls.orch = ORCHESTRATOR.read_text(encoding="utf-8")
        cls.cls_block = between(ORCHESTRATOR, "CLS — ARTIFACT CLASSIFICATION", "\n```")

    def test_precedence_is_asymmetric(self):
        """Application code settles unconditionally; non-code needs a passing CHECK."""
        flat = " ".join(self.cls_block.split())
        self.assertIn(
            "is application code UNCONDITIONALLY", flat,
            "the APPLICATION CODE limb is no longer unconditional",
        )
        self.assertIn(
            "ONLY IF the designation CHECK below is run and passes", flat,
            "the NON-CODE limb no longer requires a passing CHECK",
        )

    def test_unrun_check_is_a_failed_check(self):
        """The load-bearing half of the asymmetry. Attempt 1 lost exactly this."""
        flat = " ".join(self.cls_block.split())
        self.assertIn("An UNRUN CHECK is a failed CHECK", flat)
        self.assertIn("There is no fallback to the category tests", flat)
        self.assertIn("A failed CHECK is itself the designation: the file is APPLICATION CODE", flat)

    def test_enumerations_stay_open(self):
        flat = " ".join(self.cls_block.split())
        self.assertIn("for example `agents/*.md` and `commands/*.md`", flat,
                      "'for example' was dropped, converting an illustrative list into a closed one")
        self.assertIn("illustrative, not exhaustive", flat)

    def test_deixis_is_the_worked_project(self):
        """This block installs into other projects, so it must never say 'this repository'."""
        self.assertNotIn("this repository", self.cls_block.lower())
        self.assertIn("the project being worked on", self.cls_block)

    def test_silence_is_not_an_exemption(self):
        """Security review, Medium: steering is usually a set of empty stubs."""
        flat = " ".join(self.cls_block.split())
        self.assertIn("Silence is not an exemption", flat)
        self.assertIn("BY CONVENTION", flat)

    def test_check_refuses_to_follow_an_import_into_a_credential_store(self):
        flat = " ".join(self.cls_block.split())
        self.assertIn("Do not follow an import into a credential store", flat)
        self.assertIn("is a FAILED CHECK, never a skipped one", flat)

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
    """Code review, High 4: the reviewers branched on an undefined term, in the unsafe direction."""

    def test_both_reviewers_define_the_term_and_state_the_fail_safe(self):
        """Matched on whitespace-normalised text: these contracts wrap their prose, so any edit
        that changes where a line breaks would otherwise fail an assertion about meaning."""
        required = (
            "diff of nothing but markdown is **not** automatically a non-code diff",
            "Any file whose designation you cannot settle is application code",
            "Silence is never an exemption.",
        )
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            flat = " ".join(path.read_text(encoding="utf-8").split())
            for phrase in required:
                with self.subTest(contract=path.name, phrase=phrase[:40]):
                    self.assertIn(phrase, flat, f"{path.name} lost: {phrase[:60]!r}")

    def test_the_definition_is_identical_in_both_contracts(self):
        """Same normative content in both. Deliberately prose, not a fifth fence: NFR-12 caps
        replicated fences at exactly four, so adding one would break a stated constraint to fix a
        finding. The divergence from the reviewer's suggested remedy is recorded here on purpose."""
        spans = []
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            spans.append(between(path, "**What counts as a non-code artifact",
                                 "\n**Review scope is not produced output.**"))
        self.assertEqual(spans[0], spans[1],
                         "the two reviewers' definitions of a non-code artifact have diverged")


class GateIsActuallyWired(unittest.TestCase):
    """A section nothing invokes is dead text. Every earlier test here asserted the gate's WORDS.

    A feature-mode review found the gate had never been wired into the phase machine: the string
    "Feature Classification Gate" appeared only as its own heading and one passing mention, while
    the consistency gate right above it IS chained explicitly. `featureClass` was therefore never
    written and every feature fell to the code path — the whole feature was inert, and the entire
    suite was green. These tests assert invocation, not prose.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = ORCHESTRATOR.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_consistency_pass_branch_runs_the_classification_gate_before_advancing(self):
        start = self.text.index("**On PASS:**")
        branch = self.text[start:self.text.index("**On FAIL", start)]
        self.assertIn(
            "Feature Classification Gate", branch,
            "the consistency-gate PASS branch does not invoke the Feature Classification Gate. The "
            "gate then never runs, `featureClass` is never written, and every feature — including "
            "a non-code one — silently takes the code path and deadlocks on the missing test. This "
            "is exactly how the feature shipped inert with a green suite.",
        )
        self.assertLess(
            branch.index("Feature Classification Gate"), branch.index("Update `phase` to `implementation`"),
            "the classification gate is invoked AFTER the phase advances to implementation. It must "
            "run before, or the stages that read `featureClass` run first.",
        )

    def test_gate_is_referenced_somewhere_other_than_its_own_heading(self):
        """Validity control: a heading plus a passing mention is what the broken version had."""
        heading = self.text.count("### Feature Classification Gate")
        total = self.text.count("Feature Classification Gate")
        self.assertGreaterEqual(
            total - heading, 2,
            f"'Feature Classification Gate' appears {total} times, {heading} of them as its own "
            "heading. A section referenced nowhere but its own title is never invoked.",
        )

    def test_legacy_rule_is_restricted_to_pre_existing_features(self):
        """FR-1.7's qualifier. Without it the rule matches the gate's own run/skip state."""
        self.assertIn("started before this change", self.flat,
                      "the legacy-state-file rule dropped FR-1.7's qualifier, so it now also "
                      "matches a feature whose gate merely has not run yet, and a mid-feature "
                      "resume would cement a non-code feature onto the code path")
        self.assertIn("not** a fallback for a feature whose gate simply has not run yet", self.flat)

    def _implementation_section(self):
        i = self.text.index("### `implementation`")
        return self.text[i:self.text.index("### Feature Review Gate", i)]

    def test_resume_path_has_a_classification_checkpoint(self):
        """The gate hangs off the consistency PASS branch, so resume can bypass it entirely.

        Reachable on one path and unreachable on another is the same defect as the gate that was
        never invoked at all — it just needs a different entry point to expose it.
        """
        start = self.text.index("## On Session Start")
        section = self.text[start:self.text.index("## Phase Routing", start)]
        self.assertIn(
            "Classification checkpoint on resume", section,
            "On Session Start has no classification checkpoint. A session resumed at "
            "`implementation` never passes the gate, so `featureClass` is never written and every "
            "stage that reads it falls back to the code path.",
        )
        self.assertIn("classification.decidedAt", section)

    def test_rt1_is_consumed_between_the_tester_and_the_validator(self):
        """RT-1 was defined and never acted on: wiring RT-2 and RT-3 created the asymmetry."""
        impl = self._implementation_section()
        between = impl[impl.index("**Stage 2 — Testing:**"):impl.index("**Stage 3 — Validation:**")]
        self.assertIn(
            "RT-1", between,
            "nothing consumes RT-1. The tester can report that the task produced application code "
            "and the validator is still handed taskProducesApplicationCode: false.",
        )

    def test_rt2_exception_is_stated_INSIDE_the_per_task_fail_branch(self):
        """Sliced, not file-wide. The previous version of this test was the defect it was meant to catch.

        It asserted two substrings existed ANYWHERE in the contract. They did — 76 lines away,
        under a heading for a phase already left — while the fail branch itself still stated the
        general rule unqualified. That is the "asserts the WORDS, not the WIRING" pattern this
        whole class exists to replace, and a reviewer caught it here for the second time.
        """
        impl = self._implementation_section()
        fail_idx = impl.index("On **fail**")
        # The exception must appear in the fail branch's immediate vicinity, before the rule.
        window = impl[max(0, fail_idx - 900):fail_idx]
        self.assertIn(
            "RT-2", window,
            "the per-task fail branch does not reference RT-2. A validator FAIL that is really a "
            "reclassification signal then drives retryCount, blocked:validation and an executor "
            "re-run, whose only way to clear the verdict is deleting legitimate application code.",
        )
        self.assertRegex(window, r"do \*\*not\*\* apply the branch below|not a task failure")

    def test_rt3_is_checked_at_stage_2_where_the_changed_files_summary_exists(self):
        """RT-3 is defined on the executor's changed-files summary; Stage 2 is the only holder."""
        impl = self._implementation_section()
        stage2 = impl[impl.index("**Stage 2 — Testing:**"):impl.index("**Stage 3 — Validation:**")]
        self.assertIn(
            "RT-3", stage2,
            "Stage 2 computes the classification payload from the task's DECLARED outputs without "
            "checking the executor's changed-files summary. A task that in fact produced "
            "application code still receives the exemption.",
        )

    def test_reclassification_is_referenced_from_the_implementation_pipeline(self):
        """A section referenced only from its own heading is never reached in practice."""
        impl = self._implementation_section()
        hits = sum(impl.count(k) for k in ("Reclassif", "RT-1", "RT-2", "RT-3"))
        self.assertGreaterEqual(
            hits, 2,
            f"the implementation pipeline references reclassification {hits} times. The triggers "
            "are defined under a heading scoped to a phase already left, so nothing in the "
            "per-task loop reaches them.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
