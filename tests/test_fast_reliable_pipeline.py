#!/usr/bin/env python3
"""Structural lint for the fast-and-reliable pipeline rules.

Past builds (cellario-scheduler, 10x-e2e, pyhamilton, venus-protocols, arc-lab-automation-platform,
Sep-Oct 2026) lost most of their wall-clock to idle halts and repeated work, not to the gates:
Medium findings opened a fix round on 20 of 24 tasks although the reviewers' own contract says only
Critical/High block; the full suite ran 5-10 times per task; a retry-2 halt waited overnight for an
approval the user always gave; a missing prerequisite (LFS, token scope, deck file) was found at
02:00; and a mixed executor model produced commits whose attribution trailers disagree.

These lints pin the rules that close those gaps without removing a gate. Matches are on meaningful
phrases, so a reworded rule that drops its substance turns the suite red. Stdlib-only.

Run:
    python3 -m unittest tests.test_fast_reliable_pipeline -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def section(text, heading):
    """Return the body of a markdown section from `heading` up to the next heading of equal or
    higher level; None when the heading is absent."""
    m = re.search(rf"^(#+)\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not m:
        return None
    level = len(m.group(1))
    rest = text[m.end():]
    in_fence, offset = False, 0
    for line in rest.splitlines(keepends=True):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and re.match(rf"#{{1,{level}}}\s", line):
            return rest[:offset]
        offset += len(line)
    return rest


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orch = read("agents/orchestrator.md")
        cls.impl = section(cls.orch, "`implementation`")
        cls.rules = section(cls.orch, "Critical Rules")
        assert cls.impl is not None, "orchestrator.md lost its `implementation` section"
        assert cls.rules is not None, "orchestrator.md lost its Critical Rules section"

    def has(self, text, pat, label):
        if not re.search(pat, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            self.fail(f"{label}: missing /{pat}/")

    def lacks(self, text, pat, label):
        if re.search(pat, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            self.fail(f"{label}: forbidden /{pat}/ present")


class SeverityGateTest(Base):
    def test_only_critical_high_block_in_implementation(self):
        self.has(self.impl, r"only\s+Critical/High\s+block", "severity gate")
        self.has(self.impl, r"Medium and Low findings \*\*never\*\*\s+open a fix round", "severity gate")
        self.has(self.impl, r"deferredFindings", "severity gate record")

    def test_critical_rule_forbids_medium_fix_round(self):
        self.has(self.rules, r"NEVER open a fix round for Medium or Low", "critical rule")

    def test_feature_review_receives_deferred_findings(self):
        gate = section(self.orch, "Feature Review Gate (runs automatically after the last task completes, before `complete`)")
        self.assertIsNotNone(gate)
        self.has(gate, r"accumulated `deferredFindings`", "feature review input")

    def test_reviewers_keep_blocking_definition(self):
        for name in ("code-reviewer.md", "security-reviewer.md"):
            self.has(read(f"agents/{name}"), r"Blocking = any Critical or High finding\.\*\* Medium and Low are reported but do not block", name)


class ConvergenceRetryTest(Base):
    def test_attempt_three_requires_strict_decrease_and_no_new_finding(self):
        self.has(self.impl, r"Retry by convergence", "convergence retry")
        self.has(self.impl, r"strictly lower than the previous attempt", "convergence: strict decrease")
        self.has(self.impl, r"no finding in this attempt is new", "convergence: no new finding")
        self.has(self.impl, r"blockingHistory", "convergence record")

    def test_hard_cap_at_three(self):
        self.has(self.impl, r"retryCount >= 3, always halt", "hard cap")
        self.has(self.rules, r"NEVER run a fourth automatic attempt", "critical rule")


class SuiteRecordTest(Base):
    TREE = r"GIT_INDEX_FILE=\"\$t\" git write-tree"

    def test_orchestrator_defines_suite_record_with_temp_index(self):
        self.has(self.impl, r"Suite record \(one full run per tree\)", "suite record")
        self.has(self.impl, self.TREE, "suite record tree hash")
        self.has(self.impl, r"real index is never\s+touched", "suite record read-only")

    def test_tester_runs_full_suite_once_after_final_change(self):
        tester = read("agents/task-tester.md")
        self.has(tester, r"After your \*\*final\*\* change, run the \*\*full suite once\*\*", "tester")
        self.has(tester, self.TREE, "tester tree hash")
        self.has(tester, r"Suite record: tree <hash>", "tester summary")

    def test_validator_reuses_record_and_never_stages(self):
        validator = read("agents/task-validator.md")
        self.has(validator, r"suite record", "validator")
        self.has(validator, self.TREE, "validator tree hash")
        self.has(validator, r"never stage into the real index", "validator read-only")

    def test_no_agent_stages_into_the_real_index(self):
        for path in sorted(AGENTS.glob("*.md")):
            self.lacks(path.read_text(encoding="utf-8"), r"`git add -A && git write-tree`", path.name)

    def test_executor_uses_targeted_tests(self):
        executor = read("agents/task-executor.md")
        self.has(executor, r"run \*\*targeted\*\* tests only", "executor")
        self.has(executor, r"Do \*\*not\*\* run the full suite", "executor")


class PreflightAndOvernightTest(Base):
    def test_preflight_is_read_only_and_never_self_grants(self):
        self.has(self.impl, r"\*\*Preflight", "preflight")
        self.has(self.impl, r"git lfs", "preflight LFS")
        self.has(self.impl, r"\[ -n \"\$VAR\" \]", "preflight credentials by name")
        self.has(self.impl, r"Preflight \*\*never\*\* grants itself a permission", "preflight self-grant")
        self.has(self.impl, r"\*\*never\*\* runs a mutating command against a live", "preflight live")

    def test_overnight_mode_never_asks_and_never_self_confirms(self):
        self.has(self.impl, r"Overnight mode \(implementation only\)", "overnight scope")
        self.has(self.impl, r"Do not call AskUserQuestion", "overnight never asks")
        self.has(self.impl, r"fail-closed, reversible", "overnight default")
        self.has(self.impl, r"Never self-confirm a planning gate", "overnight planning gate")
        self.has(self.impl, r"overnight-summary\.md", "overnight summary")
        self.has(self.rules, r"never self-confirm a planning gate", "critical rule")
        self.has(self.rules, r"NEVER call AskUserQuestion while `overnightAuthorization` is set", "critical rule")


class ModelAndTrailerTest(Base):
    def test_executor_model_is_opus_everywhere(self):
        self.has(read("agents/task-executor.md"), r"^model:\s*opus\s*$", "executor frontmatter")
        self.lacks(self.orch, r"pins `model: sonnet`", "orchestrator executor default")
        self.lacks(self.orch, r"uses Sonnet per frontmatter", "orchestrator executor default")
        self.has(self.impl, r"retry is a \*\*fresh\*\* executor\s+invocation", "fresh retry")

    def test_github_agent_never_edits_trailers_and_returns_sha(self):
        gh = read("agents/github-agent.md")
        self.has(gh, r"never add, remove, or change\s+a trailer line", "github-agent trailer")
        self.has(gh, r"your own model name never goes into a commit", "github-agent trailer")
        self.has(gh, r"^commit: <full SHA", "github-agent return contract")
        self.has(gh, r"Never return an empty report", "github-agent empty report")
        self.has(self.impl, r"github-agent never adds or edits a trailer", "orchestrator trailer")


class StateAndScanHygieneTest(Base):
    def test_state_file_size_limit(self):
        state = section(self.orch, "State File Management")
        self.assertIsNotNone(state)
        self.has(state, r"under \*\*64 KB\*\*", "state size limit")
        self.has(state, r"spec-memory/carry-forward\.md", "state prose moved out")

    def test_security_reviewer_rejects_accidental_empty_input(self):
        sec = read("agents/security-reviewer.md")
        self.has(sec, r"Prove the input is not empty by accident", "security empty input")
        self.has(sec, r"A PASS over an empty input that should not be empty is a false\s+PASS", "security false pass")
        self.has(sec, r"Report the scanned file count", "security file count")


class OvernightCommandTest(Base):
    """`/sdd-overnight` is the one switch, so every unattended run starts, behaves, and ends alike."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cmd = read("commands/sdd-overnight.md")

    def test_command_has_frontmatter_and_three_modes(self):
        self.has(self.cmd, r"\A---\ndescription:", "frontmatter")
        for mode in ("status", "on", "off"):
            self.has(self.cmd, rf"^## `{mode}`$", f"mode {mode}")

    def test_on_runs_phase_check_then_preflight_then_authorize_in_order(self):
        on = section(self.cmd, "`on`")
        self.assertIsNotNone(on)
        steps = [r"1\. \*\*Phase check", r"2\. \*\*Preflight", r"3\. \*\*Authorize",
                 r"5\. \*\*Run", r"6\. \*\*Stop"]
        pos = [re.search(s, on).start() if re.search(s, on) else -1 for s in steps]
        self.assertNotIn(-1, pos, "an `on` step is missing")
        self.assertEqual(pos, sorted(pos), "`on` steps are out of order")

    def test_on_refuses_open_planning_gate_and_open_preflight_gap(self):
        on = section(self.cmd, "`on`")
        self.has(on, r"confirmed \*\*by the user\*\*", "phase check")
        self.has(on, r"never confirms a\s+planning gate", "phase check")
        self.has(on, r"Do not start until the user has fixed them", "preflight gap")

    def test_on_acts_as_orchestrator_and_uses_long_heartbeat(self):
        self.has(self.cmd, r"never spawn it as a nested subagent", "execution model")
        self.has(self.cmd, r"`ScheduleWakeup` fallback of 1800 s or more", "heartbeat")
        self.has(self.cmd, r"never call AskUserQuestion", "never asks")

    def test_stop_writes_the_fixed_template(self):
        self.has(self.cmd, r"Overnight summary template", "summary template")
        self.has(self.cmd, r"clear\s+`overnightAuthorization`", "clear authorization")

    def test_playbook_names_the_command_and_defines_the_template(self):
        self.has(self.impl, r"`/sdd-overnight\s+<feature>`", "playbook entry point")
        self.has(self.impl, r"follow `/sdd-overnight`'s steps exactly", "playbook natural-language trigger")
        tpl = re.search(r"\*\*Overnight summary template\.\*\*.*?```\n(.*?)```", self.impl, re.DOTALL)
        self.assertIsNotNone(tpl, "playbook lost the overnight summary template")
        heads = re.findall(r"^## (.+)$", tpl.group(1), re.MULTILINE)
        self.assertEqual(heads, ["Result", "Needs you", "Tasks", "Deferred", "Deferred findings", "Incidents"])

    def test_claude_md_and_readme_list_the_command(self):
        self.has(read("CLAUDE.md"), r"`/sdd-overnight <feature-name>`", "CLAUDE.md key commands")
        self.has(read("README.md"), r"sdd-overnight\.md", "README")


class ClaudeMdSummaryTest(unittest.TestCase):
    def test_claude_md_summarizes_the_rules(self):
        text = read("CLAUDE.md")
        for pat in (r"Only Critical/High block", r"One full suite run per tree", r"Retry by convergence",
                    r"Preflight before an unattended run", r"Overnight mode covers implementation only"):
            self.assertRegex(text, pat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
