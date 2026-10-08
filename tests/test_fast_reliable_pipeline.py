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
import subprocess
import tempfile
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
    TREE = r"GIT_INDEX_FILE=\"\$d/index\" git write-tree"

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
        """Every `git add` in an agent or command file runs against a temporary index."""
        files = sorted(AGENTS.glob("*.md")) + sorted((ROOT / "commands").glob("*.md"))
        for path in files:
            for line in path.read_text(encoding="utf-8").splitlines():
                for m in re.finditer(r"git add\b", line):
                    if not re.search(r'GIT_INDEX_FILE="\$d/index" $', line[:m.start()]):
                        self.fail(f"{path.name}: `git add` outside a temporary index: {line.strip()[:90]}")

    def test_tree_hash_excludes_specs_and_never_matches_empty(self):
        self.has(self.impl, r'":/" ":\(top,exclude\)\.specs"', "tree hash excludes .specs")
        self.has(self.impl, r"An empty hash, or a command that exits\s+non-zero, never matches", "empty hash")
        self.has(self.impl, r"rc=\$\?; rm -rf \"\$d\"; \[ \"\$rc\" -eq 0 \]", "exit status kept")
        self.has(self.impl, r"\*\*Limit:\*\* the hash covers tracked and untracked,\s+non-ignored files only", "limit stated")

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
        self.assertEqual(heads, ["Result", "Feature review", "Needs you", "Tasks", "Deferred",
                                "Deferred findings", "Incidents"])

    def test_claude_md_and_readme_list_the_command(self):
        self.has(read("CLAUDE.md"), r"`/sdd-overnight <feature-name>`", "CLAUDE.md key commands")
        self.has(read("README.md"), r"sdd-overnight\.md", "README")


class OvernightReviewFixesTest(Base):
    """Review round 1 (FAIL, 2 High): a halted task left its code for the next task, and the run had
    two possible endings. These pin the single, mechanical rules that replaced them."""

    def test_halted_task_is_parked_and_tree_left_clean(self):
        self.has(self.impl, r"Park, never leave changes behind", "park rule")
        self.has(self.impl, r"\{ action: park, task: N \}", "park action")
        self.has(self.impl, r"Confirm the working\s+tree is clean", "clean tree")
        self.has(self.impl, r"never inherits a parked task's code", "no inheritance")
        gh = read("agents/github-agent.md")
        self.has(gh, r"sdd-park\.py park --task <N>", "github-agent park")
        self.has(gh, r"sdd-park\.py unpark\s+--task <N> --ref <parkedRef>", "github-agent unpark")
        self.has(gh, r"Never drop or clear a stash", "stash kept")

    def test_next_task_is_chosen_by_depends_line(self):
        self.has(self.impl, r"Which task runs next — mechanical, never guessed", "next task")
        self.has(self.impl, r"A task without a `Depends:` line depends\s+on every earlier task", "default dependency")
        tasks = read("agents/tasks-agent.md")
        self.has(tasks, r"^\*\*Depends:\*\* <Task numbers", "tasks template")
        self.has(tasks, r"lists \*\*every\*\* earlier task whose output it needs", "complete deps")

    def test_one_end_of_run_rule_never_publishes(self):
        self.has(self.impl, r"The end of the run — one rule", "end rule")
        self.has(self.impl, r"\*\*never publish\*\* overnight", "no publish")
        gate = section(self.orch, "Feature Review Gate (runs automatically after the last task completes, before `complete`)")
        self.has(gate, r"Overnight: stop here\.\*\* If `overnightAuthorization` is set, do \*\*not\*\* publish", "gate PASS")
        self.has(gate, r"If `overnightAuthorization` is set, do \*\*not\*\* ask", "gate FAIL")
        self.has(self.impl, r"Stopped because: <all tasks complete \| no runnable task \| user \| off>", "template")
        self.has(self.impl, r"^## Feature review$", "template section")

    def test_amendment_is_mechanical_and_always_parks(self):
        self.has(self.impl, r"would change the text of\s+`requirements\.md`, `design\.md`, or `tasks\.md`", "amendment test")
        self.has(self.impl, r"it is never implemented overnight", "amendment parks")

    def test_stale_authorization_is_void(self):
        self.has(self.impl, r"A stale authorization is void", "playbook")
        self.has(read("commands/sdd-resume.md"), r"it is void — only a run started in the current session", "resume")

    def test_deferred_tasks_have_a_way_back(self):
        self.has(self.impl, r"After the run — recover deferred tasks", "recovery")
        self.has(self.impl, r"reset its `retryCount` to 0 only when the\s+user explicitly asks", "retry reset")
        self.has(self.impl, r"cannot run while any task is `deferred`", "feature review waits")
        state = section(self.orch, "State File Management")
        self.has(state, r"`pending`, `in_progress`, `complete`, or `deferred`", "status vocabulary")

    def test_convergence_identity_is_defined(self):
        self.has(self.impl, r"A finding's identity is \*\*`\(stage, file path, requirement id or the reviewer's finding title\)`\*\*", "identity")

    def test_security_count_includes_untracked_files(self):
        self.has(read("agents/security-reviewer.md"), r"git status --porcelain -- <files>", "porcelain count")

    def test_readme_has_no_stale_executor_model_text(self):
        readme = read("README.md")
        self.lacks(readme, r"Sonnet for tasks/execution/validation", "README")
        self.lacks(readme, r"escalates to Opus", "README")


class NoGodFilesTest(Base):
    """Modularity is enforced by one script, so every review of the same diff reaches one verdict."""
    TOOL = r"python3 ~/\.claude/tools/sdd-module-size\.py"

    def test_steering_template_declares_the_limit(self):
        self.has(read("steering-templates/tech.md"), r"^- Module size limit: 500 lines$", "tech.md template")

    def test_tool_limit_line_matches_the_template(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("sms", ROOT / "tools" / "sdd-module-size.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        m = mod.LIMIT_LINE.search(read("steering-templates/tech.md"))
        self.assertIsNotNone(m, "the tool cannot parse the template's limit line")
        self.assertEqual(int(m.group(1)), mod.DEFAULT_LIMIT)

    def test_code_reviewer_runs_the_tool_and_maps_severity(self):
        cr = read("agents/code-reviewer.md")
        self.has(cr, self.TOOL + r" --base HEAD", "reviewer runs the tool")
        self.has(cr, r"\*\*High\*\* \(blocking\) when `modularity: enforced`", "severity")

    def test_executor_design_and_tasks_agents_carry_the_rule(self):
        self.has(read("agents/task-executor.md"), self.TOOL, "executor self-check")
        self.has(read("agents/design-agent.md"), r"\*\*extraction step\*\*", "design extraction")
        self.has(read("agents/tasks-agent.md"), r"insert a \*\*split task first\*\*", "split task")

    def test_orchestrator_locks_enforcement_and_passes_it(self):
        self.has(self.orch, r"Modularity at the same gate", "gate")
        self.has(self.orch, r"no `modularity` key was planned before the rule: it is \*\*not\*\* enforced", "legacy")
        self.has(self.orch, r"never remove the key once written", "monotonic")
        self.has(self.impl, r"`modularity: enforced` or `modularity: not-enforced`", "payload")

    def test_install_ships_the_tool(self):
        inst = read("install.sh")
        self.has(inst, r'for tool_file in "\$\{SCRIPT_DIR\}/tools/"\*\.py; do', "install loop")
        self.has(inst, r'"\$\{CLAUDE_HOME\}/tools/\$\{name\}"', "install target")


class TreeHashExecutionTest(Base):
    """Run the playbook's tree-hash one-liner itself, extracted from orchestrator.md, in real repos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        m = re.search(r"touched: `(d=\$\(mktemp -d\).*?)`\.", cls.impl, re.DOTALL)
        assert m, "tree-hash command not found in the playbook"
        cls.cmd = m.group(1)
        for name in ("agents/task-tester.md", "agents/task-validator.md"):
            assert cls.cmd in read(name), f"{name} carries a different tree-hash command"

    def sh(self, cwd):
        proc = subprocess.run(["bash", "-c", self.cmd], cwd=cwd, capture_output=True, text=True)
        return proc.returncode, proc.stdout.strip()

    def test_behaviour_in_a_real_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
            git("init", "-q")
            (repo / "sub").mkdir()
            (repo / "top.py").write_text("a\n")
            (repo / "sub" / "s.py").write_text("b\n")
            (repo / ".specs").mkdir()
            (repo / ".specs" / "state.json").write_text("{}\n")
            rc, h1 = self.sh(tmp)  # fresh repo: no index file yet
            self.assertEqual(rc, 0)
            self.assertRegex(h1, r"^[0-9a-f]{40}$")
            self.assertFalse((repo / ".git" / "index").exists(), "the real index was touched")
            (repo / ".specs" / "state.json").write_text('{"x": 1}\n')
            self.assertEqual(self.sh(tmp)[1], h1, ".specs changes must not change the hash")
            (repo / "top.py").write_text("changed\n")
            rc, h2 = self.sh(str(repo / "sub"))  # run from a subdirectory
            self.assertNotEqual(h2, h1, "a top-level change seen from a subdirectory")
        rc, out = self.sh(tempfile.gettempdir())  # outside any repo
        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")


class RoundTwoProseTest(Base):
    def test_github_agent_parks_only_through_the_tool(self):
        gh = read("agents/github-agent.md")
        self.has(gh, r"python3 ~/\.claude/tools/sdd-park\.py park --task <N>", "park via tool")
        self.has(gh, r"Never hand-roll `git stash`", "no hand-rolled stash")
        self.lacks(gh, r"git rev-parse 'stash@\{0\}'", "stash@{0} lookup")

    def test_module_size_modes_and_waivers(self):
        cr = read("agents/code-reviewer.md")
        self.has(cr, r"--base HEAD <each file in the executor's\s+changed-files list>", "task mode")
        self.has(cr, r"--merge-base` — against the branch point", "feature mode")
        self.has(cr, r"`--waive <path>` for each path in the payload's `modularity\.waivers`", "waivers")
        self.has(cr, r"report that at the same severity — High when\s+enforced, Medium otherwise", "missing tool")
        self.has(self.orch, r"A waiver names one file; it is never a\s+glob and never granted by an agent", "waiver rule")
        self.has(self.orch, r"and on \*\*reclassification\*\* to `\"code\"`", "reclassification")

    def test_depends_requires_complete(self):
        self.has(self.impl, r"every task its `Depends:` line names is `complete`", "Depends complete")

    def test_publish_pending_has_a_consumer(self):
        gate = section(self.orch, "Feature Review Gate (runs automatically after the last task completes, before `complete`)")
        self.has(gate, r"Acting on `publishPending`", "consumer")
        self.has(gate, r"If `HEAD` moved, the PASS is stale: re-run this gate", "stale PASS")
        self.has(gate, r"Clear `publishPending` after the\s+publish sequence completes", "clear")
        self.has(read("commands/sdd-resume.md"), r"\*\*Pending publish\.\*\*", "resume")


class ClaudeMdSummaryTest(unittest.TestCase):
    def test_claude_md_summarizes_the_rules(self):
        text = read("CLAUDE.md")
        for pat in (r"Only Critical/High block", r"One full suite run per tree", r"Retry by convergence",
                    r"Preflight before an unattended run", r"Overnight mode covers implementation only"):
            self.assertRegex(text, pat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
