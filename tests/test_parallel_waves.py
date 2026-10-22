#!/usr/bin/env python3
"""Prose-contract tests for the parallel-waves feature (scope rev 3).

Each pin names a rule's KEY WORDS and DIRECTION (`prose.near`: terms in order within a short
window), plus checks that the inverted form is absent. So a pin goes RED when the rule's meaning is
removed or inverted, and stays GREEN when the sentence around the key words is reworded, re-wrapped
or re-emphasized (steering lesson 5). Stdlib only. Run:
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
        cls.executor = read("agents/task-executor.md")
        cls.tester = read("agents/task-tester.md")
        cls.tasks = read("agents/tasks-agent.md")
        cls.claude = read("CLAUDE.md")
        cls.pb = read("playbooks/sdd-waves.md")

    def near(self, text, label, *terms, window=160):
        if not prose.near(text, *terms, window=window):
            self.fail(f"{label}: missing {' … '.join(terms)}")

    def lacks(self, text, pat, label):
        if prose.search(text, pat):
            self.fail(f"{label}: forbidden /{pat}/ present")


class HousekeepingTest(Base):
    def test_user_trailer_rule_wins_over_session_attribution(self):
        self.near(self.orch, "trailer", r"user instruction", r"user's rule wins", r"session's attribution")
        self.lacks(self.orch, r"session's attribution wins", "trailer inverted")

    def test_review_order_is_concurrent_everywhere(self):
        for rel in ("CLAUDE.md", "README.md", "agents/code-reviewer.md",
                    "agents/security-reviewer.md"):
            text = read(rel)
            self.lacks(text, r"(after|once) (the |task-)validator pass", rel)
            self.near(text, rel, r"concurrently", window=10)

    def test_steering_lesson_seven_is_local_first(self):
        lessons = read(".specs/steering/process-lessons.md")
        self.lacks(lessons, r"draft PR", "lesson 7")
        self.near(lessons, "lesson 7", r"opened ready", r"only at the whole-feature-review PASS")

    def test_timing_ledger_has_a_writer_and_a_reader(self):
        self.near(self.orch, "writer", r"only writer", r"timing ledger")
        self.near(self.orch, "reader", r"## Timing", r"sdd-status\.py times")


class OutcomeEnvelopeTest(Base):
    def test_paths_and_internal_signatures_are_estimates(self):
        self.near(self.executor, "executor", r"Estimates, not boundaries", r"file paths",
                  r"internal function signatures")
        self.near(self.tasks, "tasks-agent", r"file paths", r"as estimates")
        self.lacks(self.tasks, r"more than 5-6 files, split it", "file-count split")

    def test_local_prerequisite_refactor_stays_inside_the_subsystem(self):
        self.near(self.executor, "refactor", r"prerequisite refactor", r"allowed",
                  r"behaviour-preserving", r"inside the subsystem")
        self.lacks(self.executor, r"refactor anywhere|outside the subsystem is (allowed|fine)", "scope")
        self.lacks(self.executor, r"missing split task, not yours to improvise", "old god-file stop")

    def test_material_change_stops_the_executor_and_has_a_reader(self):
        self.near(self.executor, "executor", r"Material change", r"stop", r"MATERIAL CHANGE:", window=400)
        self.near(self.orch, "reader", r"contains a\s+`MATERIAL CHANGE:` note", r"stop this task's pipeline",
                  r"before Stage 2")
        self.near(self.orch, "no gate", r"Never test or\s+gate a task the executor stopped")
        self.near(self.orch, "overnight", r"MATERIAL CHANGE", r"overnight, record it under `userApprovalNeeded`",
                  r"park the task", window=400)
        self.lacks(self.orch, r"MATERIAL CHANGE[^.]{0,200}continue the pipeline", "material inverted")

    def test_amendment_split_material_vs_internal(self):
        self.near(self.orch, "material", r"Material amendment", r"acceptance", r"user's confirmation",
                  window=500)
        self.near(self.orch, "internal", r"Internal reconciliation", r"owner agent", r"No user gate",
                  window=400)
        self.near(self.orch, "owner rule", r"Never edit the\s+owner's document yourself")
        self.near(self.orch, "fail closed", r"(When in doubt|If (you are )?unsure)", r"treat it as material")
        self.lacks(self.orch, r"treat it as internal", "fail closed inverted")

    def test_permitted_choice_is_decided_without_asking(self):
        self.near(self.orch, "decision", r"already permits is a decision", r"do not ask the\s+user",
                  r"attended or overnight")

    def test_probe_tiers_and_authority(self):
        self.near(self.orch, "tier 1", r"Discovery", r"read-only", r"Always permitted")
        self.near(self.orch, "tier 2", r"Isolated prototype", r"prototype authority", r"grants once",
                  window=400)
        self.near(self.orch, "tier 2 limit", r"never a source of live-system authority")
        self.near(self.orch, "no per-attempt", r"No per-attempt approval")
        self.near(self.orch, "tier 3", r"Live mutation", r"only at the project level",
                  r"never by a prototype authority", window=300)
        self.near(self.orch, "scrub", r"Scrub a capture", r"before", r"written")
        self.near(self.orch, "keep evidence", r"keep\s+the sanitized evidence")
        self.near(self.orch, "user input", r"Never delete user input")

    def test_prototype_has_a_grant_a_builder_and_no_backdated_pass(self):
        self.near(self.orch, "grant", r"ask the user once", r"isolated\s+prototypes")
        self.near(self.orch, "builder", r"outside the checkout", r"task-executor", r"`mode: prototype`",
                  window=400)
        self.near(self.executor, "executor", r"`mode: prototype`", r"outside the checkout")
        self.near(self.orch, "no backdate", r"never recorded as a passed\s+task", r"back-dated")
        self.near(self.executor, "evidence", r"evidence, not a passed task", r"every gate still runs")
        self.near(self.orch, "state key", r"`prototypeAuthority`")
        self.near(self.orch, "which executor", r"pass it to that task's executor")
        self.near(self.orch, "confirmation", r"the tasks gate and the classification gate")
        self.near(self.executor, "apply", r"`patch -p1`", r"never a git command")
        self.lacks(self.executor, r"git apply", "executor applies with git")


class FindingsAndRepairTest(Base):
    def test_one_findings_home_and_one_writer(self):
        self.near(self.orch, "home", r"Every finding", r"`spec-memory/findings\.jsonl`")
        self.near(self.orch, "writer", r"(only|sole) writer|alone write")
        self.near(self.orch, "state file", r"no finding text", r"no ad-hoc note keys")
        self.lacks(self.orch, r"taskStatus\[N\]\.deferredFindings", "old per-task home")

    def test_ids_stay_stable_by_passing_them_back(self):
        self.near(self.orch, "ids", r"ids are\s+kept stable by passing them back", r"closed \| open")
        self.near(self.orch, "new only", r"only a finding it cannot map to\s+a passed id is added as new")
        self.lacks(self.orch, r"every finding is added as new", "id rule inverted")
        for rel in ("agents/task-validator.md", "agents/code-reviewer.md", "agents/security-reviewer.md"):
            text = read(rel)
            self.near(text, rel, r"`<id>: closed`", r"`<id>: open`")
            self.near(text, rel, r"never re-report a listed finding under a new title")

    def test_routed_finding_reaches_its_closers_and_stays_open(self):
        self.near(self.orch, "closers", r"routed-to <M>", r"validator and\s+both reviewers")
        self.near(self.orch, "open", r"routed finding stays", r"open until", r"verifies it is closed")
        self.near(self.orch, "never resolution", r"Routing is never resolution")

    def test_repair_eligibility_and_bound(self):
        self.near(self.orch, "eligibility", r"localized and\s+named", r"no change to\s+acceptance",
                  r"test written to pin behaviour")
        self.near(self.orch, "ineligible", r"test that would have to be weakened is not eligible")
        self.near(self.orch, "bound", r"strict shrink", r"stable blocking set")
        self.near(self.orch, "continue", r"`CONTINUE`", r"strict subset")
        self.lacks(self.orch, r"equal or smaller", "weakened shrink")
        self.near(self.orch, "exit", r"blocker leaves the set only by being fixed", r"invalid")
        self.near(self.orch, "no reset", r"never reset `retryCount`")
        self.near(self.orch, "no laundering", r"deferral", r"severity cut", r"weakened acceptance",
                  r"edited test never empties the set")

    def test_repair_uses_its_own_delta_trees(self):
        self.near(self.orch, "trees", r"repairTrees\[<r>\]\.before", r"repairTrees\[<r>\]\.after")
        self.near(self.orch, "delta", r"`mode: delta`", r"previousTree: repairTrees")
        self.near(self.orch, "exception", r"never selects delta mode", r"except an\s+in-attempt repair")

    def test_executor_repair_mode_is_narrow(self):
        self.near(self.executor, "repair", r"`mode: repair`", r"only", r"localized", r"no test edits",
                  r"no scope\s+growth")

    def test_presentation_rule_with_machine_read_boundary(self):
        for rel in ("CLAUDE.md", "agents/task-validator.md", "agents/code-reviewer.md",
                    "agents/spec-consistency-checker.md"):
            text = read(rel)
            self.near(text, rel, r"Presentation is not a finding")
            self.near(text, rel, r"program or instrument reads", r"never cosmetic")
            self.lacks(text, r"instrument reads[^.]{0,120}may be cosmetic", rel)


class TestSignalTest(Base):
    def test_test_file_size_warns_and_never_blocks(self):
        self.near(self.claude, "CLAUDE.md", r"test file", r"warning only", r"never blocks")
        self.lacks(self.claude, r"test file[^.]{0,60}\b(is High|blocks the task)", "CLAUDE.md inverted")

    def test_one_suite_run_per_accepted_candidate(self):
        self.near(self.orch, "D7", r"once per accepted candidate", r"wave batch")
        self.lacks(self.orch, r"at\s+least once per task", "old per-task wording")
        self.near(self.orch, "feature review reuse", r"equals the suite record's",
                  r"no stage declared a changed gitignored input or environment", r"do not run the suite again",
                  window=300)
        self.near(self.orch, "feature review run", r"launch the task-tester with\s+`mode: suite-only` once")
        self.lacks(self.orch, r"every task's tester", "feature review rerun")


class HygieneAndPermissionTest(Base):
    FORBIDDEN = ("stash", "checkout", "switch", "reset", "restore", "rm --cached", "add", "commit",
                 "worktree", "clean", "merge", "rebase", "cherry-pick")

    def test_executor_and_tester_run_read_only_git(self):
        for rel, text in (("executor", self.executor), ("tester", self.tester)):
            self.near(text, rel, r"read-only git only")
            for verb in self.FORBIDDEN:
                self.near(text, f"{rel}: {verb}", r"Never run", r"`" + verb + r"`", window=300)

    def test_denials_are_never_laundered(self):
        self.near(self.orch, "orchestrator", r"NEVER bypass", r"denial", r"another actor")
        self.near(self.orch, "hook block", r"hook block", r"is\s+a security denial")
        self.near(self.claude, "CLAUDE.md", r"denial is never bypassed")
        self.near(self.claude, "CLAUDE.md hook", r"hook block", r"is\s+a security denial",
                  r"never rephrase")

    def test_commits_name_explicit_paths_only(self):
        self.near(self.orch, "orchestrator", r"explicit paths only", r"never a user-owned file")


class WavePlaybookTest(Base):
    def test_orchestrator_links_the_playbook_and_keeps_the_two_guards(self):
        self.near(self.orch, "link", r"playbooks/sdd-waves\.md", r"on entry to\s+implementation")
        self.near(self.orch, "guards", r"no Level 1 speculation while a wave", r"no wave task is parked")
        self.near(self.orch, "resume", r"sdd-wave\.py status", r"before anything else")
        self.near(self.orch, "state key", r"`wave`")

    def test_opt_in_and_mechanical_eligibility(self):
        self.near(self.pb, "opt-in", r"`Task waves: 2`", r"Absent means off")
        self.near(self.pb, "code track", r"Code track", r"neither task mutates a live system")
        self.near(self.pb, "independent", r"dependency-ready", r"neither\s+depends on the other")
        self.lacks(self.pb, r"either may depend", "dependency inverted")
        self.near(self.pb, "disjoint", r"declared sets are disjoint")
        self.near(self.pb, "env", r"Neither task changes the shared environment")
        self.near(self.pb, "clean", r"main checkout is clean", r"no Level 1 speculation exists")
        self.near(self.pb, "playbook guards", r"While a wave exists", r"no Level 1 speculation starts",
                  r"no wave task is\s+parked")

    def test_per_task_preparation_is_kept(self):
        self.near(self.pb, "prep", r"context pack", r"routed findings", r"`prototype:`",
                  r"MATERIAL CHANGE", window=300)
        self.near(self.pb, "attempt", r"own `retryCount`", r"wave attempt `k` only names refs",
                  window=300)

    def test_freeze_before_land_and_one_candidate(self):
        self.near(self.pb, "freeze", r"Freeze", r"no writer\s+may still run")
        self.near(self.pb, "suite-only", r"`mode: suite-only`", r"writes nothing", r"full suite once",
                  r"before and after")
        self.near(self.pb, "no isolated pass", r"no\s+verdict comes from a worktree")

    def test_commit_is_verified_against_the_gated_tree(self):
        self.near(self.pb, "verify", r"`wave-verify --gated-tree", r"never mark the tasks complete",
                  window=300)

    def test_repairs_are_serial_and_rereview_both_tasks(self):
        self.near(self.pb, "serial", r"one task at a time", r"never two repair executors at once")
        self.lacks(self.pb, r"two repair executors may run", "serial inverted")
        self.near(self.pb, "both", r"all reviewers of\s+both tasks", r"`mode: delta`")
        self.near(self.pb, "snapshot", r"Before each repair write", r"`wave-snapshot`")
        self.near(self.pb, "owned only", r"repair executor writes only paths its task owns", r"strays")

    def test_stop_counts_as_a_failed_attempt_and_falls_back(self):
        self.near(self.pb, "counter", r"attempt counts as failed", r"retryCount \+= 1",
                  r"blockingHistory` kept")
        self.near(self.pb, "re-gate", r"task that passed keeps no verdict", r"re-gates in sequence")
        self.near(self.pb, "fallback", r"Fallback to sequence", r"never a promise of success")
        self.near(self.pb, "user files", r"untracked before\s+the land are never touched")

    def test_agents_know_wave_mode(self):
        self.near(self.executor, "executor", r"write only paths your task owns")
        self.near(self.tester, "tester", r"`mode: suite-only`", r"write nothing")
        self.near(read("agents/github-agent.md"), "github-agent", r"wave-start", r"wave-land",
                  r"wave-adopt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
