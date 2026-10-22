#!/usr/bin/env python3
"""Prose-contract tests for the parallel-waves feature (scope rev 3).

Pins are presentation-tolerant (tests/prose.py, steering lesson 5): each one goes RED when the
rule's meaning is removed or inverted, and stays GREEN when only bold, wrapping or spacing change.
Stdlib only. Run:
    python3 -m unittest tests.test_parallel_waves -v
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

    def has(self, text, pat, label):
        if not prose.search(text, pat):
            self.fail(f"{label}: missing /{pat}/")

    def lacks(self, text, pat, label):
        if prose.search(text, pat):
            self.fail(f"{label}: forbidden /{pat}/ present")


class HousekeepingTest(Base):
    def test_user_trailer_rule_wins_over_session_attribution(self):
        self.has(self.orch, r"unless a user instruction \(CLAUDE\.md, memory, or the user's own words\)"
                 r" removes or changes it: the user's rule wins over the session's attribution",
                 "trailer precedence")

    def test_review_order_is_concurrent_everywhere(self):
        for rel in ("CLAUDE.md", "README.md", "agents/code-reviewer.md",
                    "agents/security-reviewer.md"):
            text = read(rel)
            self.lacks(text, r"after (the |task-)validator pass", rel)
            self.has(text, r"concurrently with (it|the task-validator)|validator and the two reviews"
                     r" run concurrently", rel)

    def test_steering_lesson_seven_is_local_first(self):
        lessons = read(".specs/steering/process-lessons.md")
        self.lacks(lessons, r"under a single draft PR", "lesson 7")
        self.has(lessons, r"opened ready, carrying `ready-to-merge`, only at the whole-feature-review"
                 r" PASS", "lesson 7")


class OutcomeEnvelopeTest(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.executor = read("agents/task-executor.md")
        cls.tasks = read("agents/tasks-agent.md")

    def test_paths_and_internal_signatures_are_estimates(self):
        self.has(self.executor, r"Estimates, not boundaries: the expected file paths, internal module"
                 r" names, helper names and internal function signatures", "executor")
        self.has(self.tasks, r"Name file paths, function signatures and component names from the"
                 r" design as estimates", "tasks-agent")
        self.lacks(self.tasks, r"more than 5-6 files, split it", "tasks-agent file-count split")

    def test_local_prerequisite_refactor_is_allowed_inside_the_subsystem(self):
        self.has(self.executor, r"Local prerequisite refactor — allowed\. When the outcome needs it, a"
                 r" behaviour-preserving refactor inside the subsystem the task touches is part of the"
                 r" task", "executor")
        self.lacks(self.executor, r"missing split task, not yours to improvise", "old god-file stop")

    def test_material_change_stops_the_executor(self):
        self.has(self.executor, r"MATERIAL CHANGE: <what and why>", "executor")
        self.has(self.executor, r"Material change — stop and report", "executor")

    def test_amendment_split_material_vs_internal(self):
        self.has(self.orch, r"Material amendment — it changes acceptance [^—]{0,500}? get the user's"
                 r" confirmation", "material")
        self.has(self.orch, r"Internal reconciliation — [^—]{0,300}? Route it through its owner agent"
                 r" [^—]{0,300}? No user gate", "internal")
        self.has(self.orch, r"Never edit the\s+owner's document yourself", "owner rule kept")
        self.has(self.orch, r"When in doubt whether a change is material, treat it as material", "fail closed")

    def test_permitted_choice_is_decided_without_asking(self):
        self.has(self.orch, r"A choice the confirmed text already permits is a decision, not an"
                 r" amendment: decide it, record it in `spec-memory/decisions\.md`, and do not ask the"
                 r" user — attended or overnight", "decision")

    def test_probe_tiers_and_authority(self):
        self.has(self.orch, r"Discovery — read-only", "tier 1")
        self.has(self.orch, r"Isolated prototype — [^—]{0,400}? prototype authority the user grants once", "tier 2")
        self.has(self.orch, r"never a source of live-system authority", "tier 2 limit")
        self.has(self.orch, r"Live mutation — [^—]{0,200}? Authorized only at the project level", "tier 3")
        self.has(self.orch, r"Scrub a capture before it is written anywhere", "scrub first")
        self.has(self.orch, r"keep\s+the sanitized evidence", "keep sanitized evidence")
        self.has(self.orch, r"Never delete user input", "user input kept")

    def test_retained_prototype_never_backdates_a_pass(self):
        self.has(self.orch, r"A prototype is never recorded as a passed\s+task, and no confirmation or"
                 r" verdict is ever back-dated", "no backdated pass")
        self.has(self.executor, r"It is evidence, not a passed task: every gate still runs", "executor")


class FindingsAndRepairTest(Base):
    def test_one_findings_home_and_one_writer(self):
        self.has(self.orch, r"Every finding \(blocking or deferred\) and every\s+cross-task note goes"
                 r" into `spec-memory/findings\.jsonl`", "one home")
        self.has(self.orch, r"You are its only writer", "one writer")
        self.has(self.orch, r"no finding text, no per-task finding lists, no ad-hoc note keys", "state file")
        self.lacks(self.orch, r"taskStatus\[N\]\.deferredFindings", "old per-task home")

    def test_routed_finding_stays_open_until_verified(self):
        self.has(self.orch, r"A routed finding stays\s+open until task M's validator or a reviewer"
                 r" verifies it is closed", "route")
        self.has(self.orch, r"Routing is never resolution", "route")

    def test_repair_is_bounded_by_strict_shrink_and_never_resets_retry(self):
        self.has(self.orch, r"bounded by a strict shrink of a\s+stable blocking set", "bound")
        self.has(self.orch, r"A blocker leaves the set only by being fixed, or by an independent"
                 r" decision that it was invalid", "exit rule")
        self.has(self.orch, r"Repairs never reset `retryCount` and never erase\s+earlier failure"
                 r" evidence", "no reset")
        self.has(self.orch, r"deferral, a severity cut, a weakened acceptance, or an\s+edited test"
                 r" never empties the set", "no laundering")

    def test_repair_reruns_invalidated_evidence(self):
        self.has(self.orch, r"Re-run the failed stage and every stage whose evidence the correction"
                 r" invalidated", "rerun")

    def test_executor_repair_mode_is_narrow(self):
        ex = read("agents/task-executor.md")
        self.has(ex, r"`mode: repair`\) the blocking findings of an in-attempt repair: make only the"
                 r" localized\s+correction each one names — no other change, no test edits, no scope"
                 r" growth", "executor")

    def test_presentation_rule_with_machine_read_boundary(self):
        for rel in ("CLAUDE.md", "agents/task-validator.md", "agents/code-reviewer.md",
                    "agents/spec-consistency-checker.md"):
            text = read(rel)
            self.has(text, r"Presentation is not a finding", rel)
            self.has(text, r"A string\s+a program or instrument reads .{0,120}? is never cosmetic", rel)


class HygieneAndPermissionTest(Base):
    FORBIDDEN = ("stash", "checkout", "reset", "restore", "rm --cached", "add", "commit", "worktree",
                 "clean")

    def test_executor_and_tester_run_read_only_git(self):
        for rel in ("agents/task-executor.md", "agents/task-tester.md"):
            text = read(rel)
            self.has(text, r"Run\s+read-only git only", rel)
            for verb in self.FORBIDDEN:
                self.has(text, r"Never run [^.]*`" + verb + r"`", f"{rel}: {verb}")

    def test_denials_are_never_laundered(self):
        self.has(self.orch, r"NEVER bypass a real permission or security denial through another actor"
                 r" or an equivalent tool", "orchestrator")
        self.has(self.orch, r"a missing tool or a transient error is not a denial", "orchestrator")
        self.has(read("CLAUDE.md"), r"A real permission or security denial is never bypassed", "CLAUDE.md")

    def test_commits_name_explicit_paths_only(self):
        self.has(self.orch, r"commits name explicit paths only, never a user-owned file", "orchestrator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
