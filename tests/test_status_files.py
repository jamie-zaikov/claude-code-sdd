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
        record = json.loads(self.path().read_text())
        record["updatedAt"] = "2020-01-01T00:00:00Z"
        self.path().write_text(json.dumps(record))
        code, out = self.run_tool("check", "--feature-dir", str(self.feature), "--stale-seconds", "600")
        self.assertEqual(code, 1)
        self.assertIn("STALE", out)

    def test_old_done_file_is_never_stale(self):
        self.set("--summary-path", "s.md", state="done")
        record = json.loads(self.path().read_text())
        record["updatedAt"] = "2020-01-01T00:00:00Z"
        self.path().write_text(json.dumps(record))
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
                         r"the spec-consistency-checker \(it has no Write tool")


class OrchestratorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = read("agents/orchestrator.md")
        start = text.index("## Specialist Execution Contract")
        cls.contract = text[start:text.index("\n## ", start + 5)]

    def test_completion_notice_is_primary_and_never_polled(self):
        self.assertRegex(self.contract, r"that notice is the \*\*primary signal\*\* — never poll")

    def test_heartbeat_runs_one_status_check_and_acts_on_state(self):
        self.assertIn("python3 ~/.claude/tools/sdd-status.py check --feature-dir", self.contract)
        for state in ("`blocked` — act now on `blockedOn`", "`done` / `failed` with no completion notice",
                      "`STALE` (a live state older than the grace window), or `INVALID`"):
            self.assertIn(state, self.contract)

    def test_empty_return_uses_summary_path(self):
        self.assertRegex(self.contract, r"If the return is empty or cut off, read\s+the status file")

    def test_respawn_gets_a_new_attempt(self):
        self.assertIn("The respawn uses `attempt` + 1 for its status file", self.contract)

    def test_resume_and_status_read_status_files(self):
        self.assertIn("sdd-status.py check", read("commands/sdd-resume.md"))
        self.assertRegex(read("commands/sdd-resume.md"), r"take its result from `summaryPath`, never re-run it")
        self.assertIn("sdd-status.py check", read("commands/sdd-status.md"))

    def test_install_and_uninstall_cover_the_tool(self):
        self.assertIn('for tool_file in "${SCRIPT_DIR}/tools/"*.py; do', read("install.sh"))
        self.assertIn('rm -f "${CLAUDE_HOME}/tools/sdd-status.py"', read("uninstall.sh"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
