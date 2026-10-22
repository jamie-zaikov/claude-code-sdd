#!/usr/bin/env python3
"""Behaviour tests for tools/sdd-findings.py — the findings index and the in-attempt repair check."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sdd_findings", ROOT / "tools" / "sdd-findings.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class FindingsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fd = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tool.main([argv[0], "--feature-dir", self.fd, *argv[1:]])
        return code, out.getvalue().strip()

    def add(self, title, severity="high", task="7", stage="validator", file="a.py", req=None):
        extra = ["--req", req] if req else []
        return self.run_tool("add", "--task", task, "--stage", stage, "--severity", severity,
                             "--title", title, "--file", file, *extra)[1]

    def round(self, *ids, attempt="1", task="7"):
        return self.run_tool("round", "--task", task, "--attempt", attempt, "--ids", ",".join(ids))

    # --- the index ---
    def test_ids_are_stable_and_identity_ignores_line_and_wording_of_where(self):
        a = self.add("off-by-one")
        self.assertEqual(a, "F-7-1")
        again = self.run_tool("add", "--task", "7", "--stage", "validator", "--severity", "high",
                              "--title", "off-by-one", "--file", "a.py", "--where", "a.py:99")[1]
        self.assertEqual(again, a, "same identity, new line number: no duplicate")
        self.assertEqual(self.add("other"), "F-7-2")

    def test_requirement_id_is_the_identity_for_a_validator_finding(self):
        a = self.add("FR-3 not met", req="FR-3")
        self.assertEqual(self.add("FR-3 reworded by a new run", req="FR-3"), a)

    def test_closed_identity_that_reappears_is_reopened(self):
        a = self.add("leak")
        self.run_tool("close", "--id", a, "--by", "7/validator")
        self.assertEqual(self.add("leak"), f"{a} REOPENED")
        self.assertIn(f"{a} high open", self.run_tool("list")[1])

    def test_route_and_list_by_destination(self):
        a = self.add("cheap medium", severity="medium")
        self.run_tool("route", "--id", a, "--to", "9")
        out = self.run_tool("list", "--routed-to", "9")[1]
        self.assertIn(f"{a} medium routed -> task 9", out)
        self.assertEqual(self.run_tool("list", "--status", "open")[1], "")

    def test_counts_and_unknown_id(self):
        self.add("x", severity="low")
        self.assertEqual(json.loads(self.run_tool("counts")[1]),
                         {"severity": {"low": 1}, "status": {"open": 1}})
        self.assertEqual(self.run_tool("close", "--id", "F-9-9", "--by", "x")[0], 2)

    def test_min_severity_filter(self):
        self.add("big", severity="critical")
        self.add("small", severity="low")
        out = self.run_tool("list", "--min-severity", "high")[1]
        self.assertIn("big", out)
        self.assertNotIn("small", out)

    # --- the repair check (strict shrink of a stable blocking set) ---
    def test_strict_shrink_with_closed_blocker_continues_then_clears(self):
        a, b = self.add("A"), self.add("B")
        self.assertEqual(self.round(a, b), (0, "FIRST"))
        self.run_tool("close", "--id", a, "--by", "7/validator")
        self.assertEqual(self.round(b), (0, "CONTINUE"))
        self.run_tool("close", "--id", b, "--by", "7/validator")
        self.assertEqual(self.round(), (0, "CLEAR"))

    def test_unchanged_set_stops(self):
        a = self.add("A")
        self.round(a)
        code, out = self.round(a)
        self.assertEqual(code, 1)
        self.assertIn("did not shrink", out)

    def test_new_blocker_stops(self):
        a, b = self.add("A"), self.add("B")
        self.round(a)
        code, out = self.round(b)
        self.assertEqual(code, 1)
        self.assertIn("new or reopened", out)

    def test_blocker_dropped_without_close_stops(self):
        """Deferral, downgrade or a checker that stopped reporting it never empties the set."""
        a, b = self.add("A"), self.add("B")
        self.round(a, b)
        code, out = self.round(b)
        self.assertEqual(code, 1)
        self.assertIn(a, out)

    def test_invalid_by_decision_may_leave_the_set(self):
        a, b = self.add("A"), self.add("B")
        self.round(a, b)
        self.run_tool("invalid", "--id", a, "--by", "user decision D-4")
        self.assertEqual(self.round(b), (0, "CONTINUE"))

    def test_stop_is_final_for_the_attempt(self):
        """{A} FIRST -> {A,B} STOP -> close B -> {A} must stay STOP: no cycle back to CONTINUE."""
        a, b = self.add("A"), self.add("B")
        self.round(a)
        self.assertEqual(self.round(a, b)[0], 1)
        self.run_tool("close", "--id", b, "--by", "7/validator")
        code, out = self.round(a)
        self.assertEqual(code, 1)
        self.assertIn("already stopped", out)

    def test_rounds_are_per_task_and_attempt(self):
        a = self.add("A")
        self.round(a, attempt="1")
        self.assertEqual(self.round(a, attempt="2"), (0, "FIRST"), "a new attempt starts again")

    def test_torn_last_line_is_ignored(self):
        self.add("A")
        with open(Path(self.fd) / "spec-memory" / "findings.jsonl", "a") as handle:
            handle.write('{"event": "add", "id": ')
        self.assertEqual(self.add("B"), "F-7-2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
