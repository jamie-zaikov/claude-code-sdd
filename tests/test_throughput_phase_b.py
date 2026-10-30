#!/usr/bin/env python3
"""Prose-contract tests for pipeline-throughput Phase B.

Phase B moves the full suite from every task to every candidate (the task that closes an
integration unit), plans integration units, and adds a test-quality rule for the tester. Each pin
names a rule's key words and direction (`prose.near` refuses a negated match), so a pin goes RED
when the rule is removed or inverted and stays GREEN when it is reworded or re-wrapped. Run:
    python3 -m unittest tests.test_throughput_phase_b -v
"""

import unittest
from pathlib import Path

try:
    from tests import prose
except ImportError:  # run from inside tests/
    import prose

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orch = read("agents/orchestrator.md")
        cls.tester = read("agents/task-tester.md")
        cls.validator = read("agents/task-validator.md")
        cls.executor = read("agents/task-executor.md")
        cls.tasks = read("agents/tasks-agent.md")
        cls.checker = read("agents/spec-consistency-checker.md")
        cls.claude = read("CLAUDE.md")

    def near(self, text, label, *terms, window=160):
        if not prose.near(text, *terms, window=window):
            self.fail(f"{label}: missing {' … '.join(terms)}")

    def lacks(self, text, pat, label):
        if prose.search(text, pat):
            self.fail(f"{label}: forbidden /{pat}/ present")


class CandidateRuleTest(Base):
    """The orchestrator decides who runs the full suite, and fails closed."""

    def test_only_the_exact_no_line_skips_the_full_suite(self):
        self.near(self.orch, "marker", r"exact\s+line `\*\*Candidate:\*\* no`", r"focused tests")
        self.near(self.orch, "default", r"any other value, or no line at all", r"is a \*\*candidate\*\*",
                  r"full suite")
        self.near(self.orch, "wave", r"A wave batch is always a candidate", window=40)

    def test_fail_closed_cases_force_the_full_suite(self):
        self.near(self.orch, "fail closed", r"Fail closed", r"`fullSuite: required`")
        for case in (r"last attempt failed", r"last task of the feature", r"`Contract:` interface",
                     r"`Shared:` line", r"test infrastructure", r"gitignored input",
                     r"installed environment", r"cannot list the callers"):
            self.near(self.orch, f"fail-closed case {case}", r"Fail closed", case, window=900)

    def test_a_focused_task_waits_for_its_candidate(self):
        self.near(self.orch, "awaiting", r"set to\s+`awaiting_candidate`, not `complete`",
                  r"not marked `\[x\]`")
        self.near(self.orch, "completion", r"next candidate passes", r"full-suite PASS",
                  r"`awaiting_candidate` task to `complete`")
        self.lacks(self.orch, r"`awaiting_candidate`[^.]{0,40}counts as complete", "awaiting is complete")

    def test_feature_review_waits_for_every_candidate(self):
        self.near(self.orch, "review blocked", r"Feature Review Gate never starts", r"`awaiting_candidate`")
        self.near(self.orch, "review entry", r"Once every task is `complete` \(none `awaiting_candidate`\)")

    def test_a_red_candidate_suite_fails_the_candidate(self):
        self.near(self.orch, "red suite", r"full suite fails fails that attempt", r"failing tests",
                  r"`awaiting_candidate` tasks")
        self.near(self.orch, "retry owner", r"`retryCount` counts on the candidate", window=40)
        self.near(self.orch, "halted", r"halted or parked\s+candidate leaves", r"open")

    def test_status_vocabulary_has_the_new_state(self):
        self.near(self.orch, "vocabulary", r"`in_progress`, `awaiting_candidate`, `complete`")

    def test_the_tester_is_told_which_suite_to_run(self):
        self.near(self.orch, "stage 2", r"`fullSuite: required`", r"`fullSuite: focused`",
                  r"`Candidate: no`")


class TesterTest(Base):
    def test_focused_mode_runs_neighbours_and_writes_a_focused_record(self):
        self.near(self.tester, "focused", r"`fullSuite: focused`", r"focused tests once",
                  r"direct importers", r"focused record")
        self.near(self.tester, "escape", r"cannot list the importers", r"run the full suite instead")
        self.near(self.tester, "record format", r"Focused record: tree <hash>", r"scope:")
        self.near(self.tester, "default full", r"`fullSuite: required`, or no value",
                  r"full suite once")

    def test_each_new_test_names_the_wrong_result_it_rejects(self):
        self.near(self.tester, "rejects", r"Each new test names the wrong result it rejects")
        self.near(self.tester, "summary", r"rejects: <the wrong result>", r"expected from:")

    def test_expected_values_come_from_outside_the_code(self):
        self.near(self.tester, "oracle", r"Expected values come from outside the code under test",
                  r"contract", r"calculation")
        self.near(self.tester, "no echo", r"Never from\s+a second call to the same production path")

    def test_important_guards_are_proved_on_a_scratch_copy(self):
        self.near(self.tester, "guard", r"important guard proves itself", r"scratch copy",
                  r"never the checkout", r"turn red")

    def test_prose_checks_accept_rewording(self):
        self.near(self.tester, "prose", r"checks prose", r"accepts an equivalent\s+rewording",
                  r"fails\s+on a change of meaning")

    def test_reuse_counts_only_for_the_same_wrong_result(self):
        self.near(self.tester, "reuse", r"existing test that\s+already rejects the same wrong result")
        self.lacks(self.tester, r"Each cited requirement should have at least one test that verifies it",
                   "old one-test-per-requirement incentive")


class ValidatorTest(Base):
    def test_focused_record_is_valid_only_on_a_marked_task(self):
        self.near(self.validator, "focused valid", r"focused record", r"valid only when",
                  r"exact line `\*\*Candidate:\*\* no`", r"`fullSuite: focused`")
        self.near(self.validator, "else fail", r"In any other case a missing\s+suite record is a FAIL")

    def test_validator_checks_test_quality(self):
        self.near(self.validator, "quality", r"name the wrong result it rejects",
                  r"not from a second\s+call to the same production path")
        self.near(self.validator, "fail", r"protects nothing", r"FAIL with the test name")


class ExecutorTest(Base):
    def test_candidate_retry_may_fix_the_unit(self):
        self.near(self.executor, "unit fix", r"full-suite failure", r"may fix any file of the",
                  r"`awaiting_candidate` tasks")


class TasksAgentTest(Base):
    def test_integration_units_keep_producer_and_consumer_together(self):
        self.near(self.tasks, "units", r"Integration units", r"producer and the consumer it needs",
                  r"one task")
        self.near(self.tasks, "why", r"leave the suite\s+red or the path unusable")

    def test_candidate_marks_are_narrow_and_default_to_candidate(self):
        self.near(self.tasks, "mark", r"Every task is a candidate unless its block has the line",
                  r"`\*\*Candidate:\*\* no`")
        for cond in (r"lists it on its `Depends:` line", r"no `Contract:` interface",
                     r"no file on a `Shared:` line", r"no test infrastructure",
                     r"not the last task of the feature"):
            self.near(self.tasks, f"condition {cond}", r"Write `no` only when all of these hold", cond,
                      window=700)
        self.near(self.tasks, "unsure", r"When unsure, omit the line", r"candidate")
        self.near(self.tasks, "user", r"user approves the marks")


class CheckerTest(Base):
    def test_checker_flags_an_uncovered_focused_task(self):
        self.near(self.checker, "marks", r"Candidate marks", r"last\s+task", r"`Depends:` line",
                  r"`Contract:` or `Shared:` line")


class ClaudeMdTest(Base):
    def test_global_rule_states_the_candidate_policy(self):
        self.near(self.claude, "bullet", r"One full suite per candidate", r"`Candidate: no`",
                  r"focused tests", r"`awaiting_candidate`")
        self.near(self.claude, "always", r"always run the full suite")
        self.near(self.claude, "quality", r"names the wrong\s+result it rejects")


if __name__ == "__main__":
    unittest.main(verbosity=2)
