#!/usr/bin/env python3
"""Structural lint for the non-code feature track (user-declared, two-gate).

The SDD contracts are markdown/config artifacts, so these are structure lints over the contract
text — the same style as tests/test_orchestrator_github_integration.py. They pin the *wiring* that
routes a non-code feature, which is exactly what shipped inert (green suite, dead feature) in two
prior attempts.

For the load-bearing wiring pins we do genuine **mutation verification** in-test: `assert_pin_bites`
asserts the pin matches the real file AND that deleting the pinned line makes the assertion fail —
proving the pin actually bites, not merely that a phrase happens to appear (a phrase can drift into
a doc for unrelated reasons). This mirrors the retired process-lessons rule "prove a pin bites".

Manual mutation checks recorded for the reviewer (each already automated below via `assert_pin_bites`):
  - remove the gate invocation from the consistency-PASS branch  -> test_gate_invoked_on_consistency_pass RED
  - remove the resume checkpoint                                 -> test_resume_checkpoint_present RED
  - remove the taskProducesApplicationCode payload              -> test_per_task_payload_present RED
  - remove the "skip Stage 4" non-code routing                  -> test_non_code_routing_skips_tester_and_code_review RED
  - reword RT-2 to a task failure                                -> test_rt2_is_a_reclassification_not_a_task_failure RED

Run:
    python3 -m pytest tests/test_non_code_track.py -q
    # or
    python3 tests/test_non_code_track.py
"""

import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "agents"
ORCH = AGENTS / "orchestrator.md"
VALIDATOR = AGENTS / "task-validator.md"
TESTER = AGENTS / "task-tester.md"
TASKS = AGENTS / "tasks-agent.md"
CODE_REVIEWER = AGENTS / "code-reviewer.md"
SEC_REVIEWER = AGENTS / "security-reviewer.md"


def read(p):
    return p.read_text(encoding="utf-8")


def region_between(text, start_pat, end_pat):
    """Substring from the first match of start_pat to the next match of end_pat (or EOF)."""
    flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
    ms = re.search(start_pat, text, flags)
    if not ms:
        return None
    rest = text[ms.start():]
    me = re.search(end_pat, rest[1:], flags)
    return rest if not me else rest[: me.start() + 1]


def drop_lines_matching(text, line_substr):
    """Return text with every line containing line_substr removed (the mutation)."""
    return "\n".join(ln for ln in text.splitlines() if line_substr not in ln)


class NonCodeTrackWiring(unittest.TestCase):
    """The orchestrator wiring that routes a non-code feature. Mutation-verified where load-bearing."""

    @classmethod
    def setUpClass(cls):
        cls.orch = read(ORCH)

    def assert_pin_bites(self, text, present_regex, mutation_line_substr, label):
        """Prove a pin bites: it matches the real text, and deleting the pinned line breaks it."""
        self.assertRegex(text, present_regex, f"{label}: pin not present in the real contract")
        mutated = drop_lines_matching(text, mutation_line_substr)
        self.assertNotRegex(
            mutated, present_regex,
            f"{label}: deleting the pinned line did NOT break the assertion — the pin does not bite",
        )

    def test_gate_invoked_on_consistency_pass(self):
        """The Feature Classification Gate is invoked on the consistency-PASS -> implementation edge."""
        region = region_between(self.orch, r"\*\*On PASS:\*\*", r"\*\*On FAIL:\*\*")
        self.assertIsNotNone(region, "consistency-gate On PASS branch not found")
        self.assert_pin_bites(
            region,
            r"(?i)run the Feature Classification Gate",
            "run the Feature Classification Gate",
            "gate invoked on consistency PASS",
        )
        # And the gate section itself exists as a heading.
        self.assertRegex(
            self.orch, r"(?mi)^#+\s+Feature Classification Gate",
            "Feature Classification Gate section heading missing",
        )

    def test_resume_checkpoint_present(self):
        """A resume that lands past the gate re-runs it (the one path that can skip it)."""
        self.assert_pin_bites(
            self.orch,
            r"(?i)Classification checkpoint on resume",
            "Classification checkpoint on resume",
            "resume checkpoint",
        )

    def test_user_declares_not_inferred(self):
        """The track is a declared human decision, never inferred — no classifier."""
        self.assertRegex(
            self.orch, r"(?i)user declares the track",
            "the gate does not state the user declares the track",
        )
        self.assertRegex(
            self.orch, r"(?i)there is no classifier",
            "the gate does not state there is no classifier",
        )

    def test_per_task_payload_present(self):
        """Stages 2/3/5 carry the featureClass + taskProducesApplicationCode payload."""
        self.assertIn("taskProducesApplicationCode", self.orch, "payload field absent")
        self.assert_pin_bites(
            self.orch,
            r"(?i)Send `false` \*\*only\*\* where `featureClass` is `\"non-code\"`",
            "Send `false`",
            "per-task classification payload",
        )

    def test_non_code_routing_skips_tester_and_code_review(self):
        """A non-code task skips Stage 2 (tester) and Stage 4 (code-review)."""
        # Stage 2 is marked code-track-only / skipped on the non-code track.
        self.assertRegex(
            self.orch,
            r"(?i)Stage 2 — Testing\*\* \*\(code track only",
            "Stage 2 is not marked code-track-only",
        )
        # Stage 4 code-review is explicitly skipped on the non-code track.
        self.assert_pin_bites(
            self.orch,
            r"(?i)skip Stage 4 \(code-review\)",
            "skip Stage 4 (code-review)",
            "non-code skips the per-task code-review",
        )

    def test_rt2_is_a_reclassification_not_a_task_failure(self):
        """RT-2 (validator FAIL citing app code in artifact-conformance) is a reclassification, not a fail."""
        self.assert_pin_bites(
            self.orch,
            r"(?i)This FAIL is a reclassification signal, not a task failure",
            "reclassification signal, not a task failure",
            "RT-2 handled as reclassification",
        )
        # It must NOT enter the per-task fail branch.
        self.assertRegex(
            self.orch, r"(?i)do \*\*not\*\* enter the per-task fail branch",
            "RT-2 does not state it bypasses the fail branch",
        )

    def test_reclassification_is_monotonic_and_scaffolding_exempt(self):
        self.assertRegex(self.orch, r"(?i)reclassification is \*\*monotonic\*\*",
                         "reclassification not stated as monotonic")
        self.assertRegex(
            self.orch,
            r"(?i)never triggers reclassification and never affects classification",
            "scaffolding is not exempted from reclassification",
        )

    def test_state_schema_two_values_never_null(self):
        self.assert_pin_bites(
            self.orch,
            r"(?i)exactly two permitted values, `\"code\"` and `\"non-code\"`",
            "exactly two permitted values",
            "featureClass state schema",
        )
        self.assertRegex(self.orch, r"(?i)`null` is \*\*not\*\*", "null is not forbidden as a value")


class ValidatorArtifactConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = read(VALIDATOR)

    def test_enters_only_on_explicit_false(self):
        flat = " ".join(self.t.split())
        self.assertIn(
            "Enter this mode only where the orchestrator's payload sets `taskProducesApplicationCode: false`",
            flat,
            "artifact-conformance mode entry is not gated on an explicit false",
        )
        self.assertIn("Never select this mode yourself", flat,
                      "validator does not forbid self-selecting the mode")

    def test_checks_acceptance_checklist(self):
        self.assertIn("Check the task's `Acceptance:` checklist item by item", self.t,
                      "validator does not check the Acceptance checklist")
        self.assertRegex(
            self.t, r"(?i)no `Acceptance:` list is underspecified",
            "validator does not FAIL a non-code task lacking an Acceptance list",
        )

    def test_code_path_test_line_untouched_discrimination_control(self):
        """Discrimination control: the code-path test-existence line must survive unchanged."""
        self.assertIn("- [ ] Does at least one test exist for this requirement?", self.t,
                      "the code-path test-existence checklist line was removed or altered")

    def test_mode_verdict_line_and_rt2(self):
        self.assertIn("### Mode: artifact-conformance", self.t, "mode verdict line missing")
        self.assertIn("If the executor modified application code, refuse the exemption.", self.t,
                      "validator does not refuse the exemption on executor-modified app code (RT-2)")


class TesterSkipped(unittest.TestCase):
    def test_tester_not_invoked_for_non_code(self):
        flat = " ".join(read(TESTER).split())
        self.assertRegex(flat, r"(?i)Non-code tasks skip this stage",
                         "tester does not state it is skipped for non-code tasks")
        self.assertRegex(flat, r"(?i)does \*\*not\*\* invoke\b[\s>]*you",
                         "tester does not state the orchestrator will not invoke it")


class TasksAgentAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = read(TASKS)

    def test_non_code_section_and_acceptance_block(self):
        self.assertRegex(self.t, r"(?mi)^#+\s+Non-Code Features",
                         "tasks-agent has no Non-Code Features section")
        self.assertIn("**Acceptance:**", self.t, "tasks-agent does not author an Acceptance block")

    def test_acceptance_items_are_checkable_not_subjective(self):
        self.assertRegex(
            self.t, r"(?i)Finite and checkable",
            "tasks-agent does not require Acceptance items to be finite and checkable",
        )
        self.assertRegex(
            self.t, r"(?i)renders with no error",
            "tasks-agent does not require a render item for diagram tasks",
        )

    def test_testing_subtask_carve_out(self):
        flat = " ".join(self.t.split())
        self.assertRegex(
            flat, r"(?i)except\b.*non-code.*Acceptance",
            "the 'every task ends with a testing sub-task' rule has no non-code carve-out",
        )


class ReviewersNonCodeMode(unittest.TestCase):
    def test_code_reviewer_closed_rubric_and_failsafe(self):
        t = read(CODE_REVIEWER)
        self.assertRegex(t, r"(?mi)^#+\s+Non-Code and Empty Scope",
                         "code-reviewer has no Non-Code and Empty Scope section")
        self.assertRegex(t, r"(?i)closed rubric", "code-reviewer non-code rubric is not closed")
        self.assertRegex(t, r"(?i)Return exactly one of `PASS` or `FAIL`",
                         "code-reviewer non-code mode permits a hedge")
        self.assertRegex(t, r"(?i)any application-code path.*ordinary hunt|ordinary hunt",
                         "code-reviewer non-code mode has no fail-safe to the ordinary hunt")

    def test_security_reviewer_mechanical_checklist(self):
        t = read(SEC_REVIEWER)
        self.assertRegex(t, r"(?mi)^#+\s+Non-Code and Empty Scope",
                         "security-reviewer has no Non-Code and Empty Scope section")
        self.assertRegex(t, r"(?i)closed, mechanical checklist",
                         "security-reviewer non-code mode is not a closed mechanical checklist")
        for cls_name in ("Secret committed in prose", "Sensitive disclosure",
                         "Unsafe documented instruction", "Vault-changelog exposure"):
            self.assertIn(cls_name, t, f"security-reviewer non-code checklist missing: {cls_name}")


class CodePathUnchanged(unittest.TestCase):
    """The non-code track ADDS a path; the code path must be byte-unchanged in spirit."""

    def test_code_feature_still_runs_five_stages(self):
        orch = read(ORCH)
        self.assertRegex(orch, r"(?i)code track runs five stages",
                         "the orchestrator no longer states the code track runs five stages")

    def test_code_feature_needs_no_extra_prompt(self):
        orch = read(ORCH)
        self.assertRegex(
            orch, r"(?i)routed exactly as today, with no behavioural change and no extra prompt",
            "a code feature is no longer guaranteed the unchanged, no-extra-prompt path",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
