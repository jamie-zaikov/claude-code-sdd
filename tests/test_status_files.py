#!/usr/bin/env python3
"""Specialist status files: the orchestrator reads a state, it never guesses liveness from silence.

Before this, the contract said "every agent writes its report incrementally", but no specialist
definition told it to — ledgers existed only where an orchestrator prompt asked for one — and
liveness was judged from file mtimes plus a polling heartbeat. These tests pin:

  * tools/sdd-status.py — atomic `set`, schema and staleness `check`, exit codes;
  * the shared *Status File* section in every specialist that can write a file;
  * the orchestrator contract that acts on `state`, and the resume/status commands that read it.

Stdlib only. Run:
    python3 -m unittest tests.test_status_files -v
"""

import importlib.util
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "sdd-status.py"
WRITERS = ("requirements-agent", "design-agent", "tasks-agent", "task-executor", "task-tester",
           "task-validator", "code-reviewer", "security-reviewer", "github-agent", "vault-reader",
           "vault-writer")


def load_tool():
    spec = importlib.util.spec_from_file_location("sdd_status", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = load_tool()


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class ToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = tool.main(list(argv))
        return code, out.getvalue()

    def set(self, *extra, state="working", task="7", attempt="1"):
        return self.run_tool("set", "--feature-dir", str(self.feature), "--agent", "task-executor",
                             "--task", task, "--attempt", attempt, "--state", state,
                             "--step", "7.2", *extra)

    @staticmethod
    def age(path, seconds):
        import os
        import time
        t = time.time() - seconds
        os.utime(path, (t, t))

    def path(self, task="7", attempt=1):
        return self.feature / "spec-memory" / "status" / f"{task}-task-executor-a{attempt}.json"

    def test_set_writes_exactly_the_schema(self):
        code, _ = self.set()
        self.assertEqual(code, 0)
        record = json.loads(self.path().read_text())
        self.assertEqual(tuple(record), tool.REQUIRED)
        self.assertEqual(record["state"], "working")
        self.assertRegex(record["updatedAt"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_set_leaves_no_temp_file(self):
        self.set()
        self.assertEqual([p.name for p in self.path().parent.iterdir()], [self.path().name])

    def test_done_needs_summary_and_blocked_needs_reason(self):
        self.assertEqual(self.set(state="done")[0], 2)
        self.assertEqual(self.set(state="blocked")[0], 2)
        self.assertEqual(self.set("--summary-path", "s.md", state="done")[0], 0)
        self.assertEqual(self.set("--blocked-on", "SECRET REQUEST: X", state="blocked")[0], 0)

    def test_check_passes_fresh_and_flags_stale(self):
        self.set()
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature),
                                       "--stale-seconds", "600")[0], 0)
        self.age(self.path(), 3600)
        code, out = self.run_tool("check", "--feature-dir", str(self.feature), "--stale-seconds", "600")
        self.assertEqual(code, 1)
        self.assertIn("STALE", out)

    def test_old_done_file_is_never_stale(self):
        self.set("--summary-path", "s.md", state="done")
        self.age(self.path(), 3600)
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature),
                                       "--stale-seconds", "600")[0], 0)

    def test_check_flags_invalid_and_unreadable(self):
        self.set()
        bad = self.path().parent / "8-task-tester-a1.json"
        bad.write_text('{"agent": "task-tester"}')
        code, out = self.run_tool("check", "--feature-dir", str(self.feature))
        self.assertEqual(code, 1)
        self.assertIn("INVALID: missing", out)
        bad.write_text("{not json")
        self.assertIn("unreadable", self.run_tool("check", "--feature-dir", str(self.feature))[1])

    def test_check_rejects_unknown_state_extra_key_and_wrong_name(self):
        self.set()
        record = json.loads(self.path().read_text())
        for mutate, reason in ((lambda r: r.update(state="sleeping"), "state"),
                               (lambda r: r.update(extra=1), "unknown key"),
                               (lambda r: r.update(task="9"), "file name must be")):
            r = dict(record)
            mutate(r)
            self.path().write_text(json.dumps(r))
            code, out = self.run_tool("check", "--feature-dir", str(self.feature))
            self.assertEqual(code, 1, reason)
            self.assertIn(reason, out)

    def test_check_task_filter(self):
        self.set(task="7")
        self.set(task="8")
        _, out = self.run_tool("check", "--feature-dir", str(self.feature), "--task", "8")
        self.assertIn("8-task-executor-a1.json", out)
        self.assertNotIn("7-task-executor-a1.json", out)

    # --- review round 3 ---
    def test_dead_older_attempt_never_makes_a_fresh_respawn_stale(self):
        self.set(attempt="1")
        self.age(self.path(attempt=1), 3600)  # a1 died mid-step
        self.set(attempt="2")
        code, out = self.run_tool("check", "--feature-dir", str(self.feature), "--task", "7",
                                  "--stale-seconds", "600")
        self.assertEqual(code, 0, out)
        self.assertIn("a2.json", out)
        self.assertNotIn("a1.json", out)
        _, history = self.run_tool("check", "--feature-dir", str(self.feature), "--all")
        self.assertIn("a1.json", history)

    def test_exact_check_reports_missing_before_the_first_write(self):
        self.set("--summary-path", "s.md", state="done", attempt="1")  # an OLD done result
        code, out = self.run_tool("check", "--feature-dir", str(self.feature), "--task", "7",
                                  "--agent", "task-executor", "--attempt", "2")
        self.assertEqual(code, 3)
        self.assertIn("a2.json MISSING", out)

    def test_staleness_uses_mtime_not_the_self_reported_clock(self):
        self.set()
        record = json.loads(self.path().read_text())
        record["updatedAt"] = "2030-01-01T00:00:00Z"  # an agent without a clock guessed the future
        self.path().write_text(json.dumps(record))
        self.age(self.path(), 3600)
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature),
                                       "--stale-seconds", "600")[0], 1)
        record["updatedAt"] = "2000-01-01T00:00:00Z"  # ...or the distant past
        self.path().write_text(json.dumps(record))  # fresh mtime
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature),
                                       "--stale-seconds", "600")[0], 0)

    # --- review round 4 ---
    def write_record(self, task, agent, attempt=1):
        d = self.feature / "spec-memory" / "status"
        d.mkdir(parents=True, exist_ok=True)
        rec = {"agent": agent, "task": task, "attempt": attempt, "state": "working", "step": "s",
               "updatedAt": "2026-10-08T00:00:00Z", "verdict": None, "summaryPath": None,
               "blockedOn": None}
        (d / f"{task}-{agent}-a{attempt}.json").write_text(json.dumps(rec))

    def test_agent_and_task_filters_are_exact(self):
        self.write_record("3", "code-reviewer")
        self.write_record("3", "reviewer")
        self.write_record("fix-a1-x", "task-tester")
        _, out = self.run_tool("check", "--feature-dir", str(self.feature), "--agent", "reviewer")
        self.assertIn("3-reviewer-a1.json", out)
        self.assertNotIn("code-reviewer", out)
        _, out = self.run_tool("check", "--feature-dir", str(self.feature), "--task", "fix")
        self.assertNotIn("fix-a1-x", out)

    def test_attempt_alone_is_a_usage_error(self):
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature),
                                       "--task", "3", "--attempt", "9")[0], 2)

    def test_check_without_status_dir_is_clean(self):
        self.assertEqual(self.run_tool("check", "--feature-dir", str(self.feature))[0], 0)


class AgentSectionTest(unittest.TestCase):
    def test_every_writer_carries_the_status_section(self):
        for name in WRITERS:
            text = read(f"agents/{name}.md")
            self.assertIn("## Status File (liveness and result)", text, name)
            self.assertIn("spec-memory/status/<task>-<agent>-a<attempt>.json", text, name)
            self.assertIn("python3 ~/.claude/tools/sdd-status.py set", text, name)
            self.assertRegex(text, r"Before the last write, put your full return summary in `summaryPath`", name)
            self.assertIn("Never write another agent's status file", text, name)

    def test_section_round_three_rules(self):
        for name in WRITERS:
            text = read(f"agents/{name}.md")
            self.assertIn("skip\nthe status file", text, name)
            self.assertIn("staleness is judged from the file's real\nmodification time", text, name)
            self.assertIn("(`cat > <summaryPath> <<'EOF'`)", text, name)
            self.assertNotIn("it is the one file you write", text, name)

    def test_vault_agents_allow_their_status_file(self):
        self.assertRegex(read("agents/vault-reader.md"),
                         r"NEVER write anywhere except the single `output_path` — and your status\s+file")
        self.assertRegex(read("agents/vault-writer.md"),
                         r"NEVER write outside `vault_path` \(except the changelog under the feature directory, and your status")

    def test_section_lists_the_tools_schema_keys(self):
        text = read("agents/task-executor.md")
        block = re.search(r"```json\n(.*?)```", text[text.index("## Status File"):], re.S)
        self.assertIsNotNone(block)
        for key in tool.REQUIRED:
            self.assertIn(f'"{key}"', block.group(1), key)

    def test_section_states_match_the_tool(self):
        text = read("agents/task-executor.md")
        section = text[text.index("## Status File"):]
        for state in tool.STATES:
            self.assertIn(f"`{state}`", section, state)

    def test_checker_is_the_named_exception(self):
        self.assertNotIn("## Status File", read("agents/spec-consistency-checker.md"))
        self.assertRegex(read("agents/orchestrator.md"),
                         r"The spec-consistency-checker has no Write tool and keeps no status file")


class OrchestratorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = read("agents/orchestrator.md")
        start = text.index("## Specialist Execution Contract")
        cls.contract = text[start:text.index("\n## ", start + 5)]

    def test_completion_notice_is_primary_and_never_polled(self):
        self.assertRegex(self.contract, r"that notice is the \*\*primary signal\*\* — never poll")

    def test_heartbeat_runs_one_status_check_and_acts_on_state(self):
        self.assertRegex(self.contract, r"python3\s+~/\.claude/tools/sdd-status\.py check --feature-dir")
        for state in ("`blocked` — act now on `blockedOn`", "`done` / `failed` with no completion notice",
                      "`STALE` (a live state with no file write for the grace window), or `INVALID`"):
            self.assertIn(state, self.contract)

    def test_empty_return_uses_summary_path(self):
        self.assertRegex(self.contract, r"If the return is empty or cut off, read\s+the status file")

    def test_respawn_gets_a_new_attempt(self):
        self.assertRegex(self.contract, r"The respawn uses `attempt` \+ 1 \(recorded in\s+`invocations` before launch\)")

    def test_resume_and_status_read_status_files(self):
        self.assertIn("sdd-status.py check", read("commands/sdd-resume.md"))
        self.assertRegex(read("commands/sdd-resume.md"), r"take its result from `summaryPath`, never re-run it")
        self.assertIn("sdd-status.py check", read("commands/sdd-status.md"))

    # --- review round 3 ---
    def test_heartbeat_checks_the_exact_invocation(self):
        self.assertRegex(self.contract, r"--task <task>\s+--agent <agent> --attempt <n> --stale-seconds <grace>")
        self.assertIn("can never be read as this one", self.contract)

    def test_grace_window_is_numeric(self):
        self.assertIn("**1200 s** by default, **2400 s** for a vault-reader", self.contract)

    def test_missing_first_write_is_handled(self):
        self.assertIn("`MISSING` (exit 3)", self.contract)

    def test_attempt_counter_is_persisted_before_launch(self):
        self.assertRegex(self.contract, r"\*\*Before\*\* each launch, record it\s+in `\.spec-state\.json` under `invocations")
        self.assertIn("Continue numbering from `invocations`", read("commands/sdd-resume.md"))

    def test_checker_liveness_uses_the_harness_not_the_os_process_list(self):
        self.assertIn("the harness's task list (`TaskOutput`)", self.contract)

    def test_install_and_uninstall_cover_the_tool(self):
        self.assertIn('for tool_file in "${SCRIPT_DIR}/tools/"*.py; do', read("install.sh"))
        self.assertIn('rm -f "${CLAUDE_HOME}/tools/sdd-status.py"', read("uninstall.sh"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
