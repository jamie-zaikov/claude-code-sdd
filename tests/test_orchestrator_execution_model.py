#!/usr/bin/env python3
"""Structural lint for the stall-safe Orchestration Execution Model.

Fixes the pipeline stall: a specialist goes quiet, the caller is frozen inside a blocking `Agent`
call, and when the caller is itself a subagent the whole chain deadlocks (specialist idle ->
Orchestrator idle -> main session idle). The fix is Option A — the main session *acts as* the
Orchestrator (never a nested subagent), so it keeps the recovery tools and drives every specialist
through a background-launch + heartbeat + kill/respawn-once + idempotent-resume contract.

These are structure lints over markdown/config artifacts (same style as
tests/test_orchestrator_github_integration.py). Matches are on meaningful phrases, not bare
headings, so the lint is not trivially satisfied. Stdlib-only.

Run:
    python3 -m unittest tests.test_orchestrator_execution_model -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORCH_PATH = ROOT / "agents" / "orchestrator.md"
RESUME_PATH = ROOT / "commands" / "sdd-resume.md"
FEATURE_PATH = ROOT / "commands" / "sdd-feature.md"
CLAUDE_PATH = ROOT / "CLAUDE.md"


class OrchestratorExecutionModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert ORCH_PATH.exists(), f"orchestrator definition not found at {ORCH_PATH}"
        cls.orch = ORCH_PATH.read_text(encoding="utf-8")
        cls.resume = RESUME_PATH.read_text(encoding="utf-8")
        cls.feature = FEATURE_PATH.read_text(encoding="utf-8")
        cls.claude = CLAUDE_PATH.read_text(encoding="utf-8")

    def _assert_all(self, text, patterns, label):
        for pat in patterns:
            if not re.search(pat, text, re.IGNORECASE | re.MULTILINE):
                self.fail(f"{label}: missing /{pat}/")

    # --- Orchestrator playbook -------------------------------------------------

    def test_execution_model_section_present(self):
        """The playbook states the main session acts as the Orchestrator, never a nested subagent."""
        self._assert_all(
            self.orch,
            [
                r"##\s+Execution Model",
                r"main session\s+acts as\s+the\s+Orchestrator",
                r"not\s+spawn\b.*nested\s+subagent|never\s+a\s+nested\s+subagent",
            ],
            "orchestrator Execution Model",
        )

    def test_execution_model_names_the_deadlock_and_recovery_tools(self):
        """It names the deadlock (chain of idle layers) and the recovery tools kept in the main loop."""
        self._assert_all(
            self.orch,
            [r"deadlock", r"TaskStop", r"ScheduleWakeup", r"SendMessage"],
            "orchestrator deadlock + recovery tools",
        )

    def test_specialist_execution_contract_present(self):
        """The Specialist Execution Contract covers launch, heartbeat, respawn-once, resume, halt."""
        self._assert_all(
            self.orch,
            [
                r"##\s+Specialist Execution Contract",
                r"background",                        # non-blocking launch
                r"mtime",                             # ledger heartbeat
                r"silence is not death",              # process-lesson 4
                r"process list",                      # liveness by evidence
                r"TaskStop",                          # kill the dead specialist
                r"respawn\b.*once|once\b",            # respawn at most once
                r"resume[s]?\b.*ledger|idempotent",   # idempotent resume
                r"[Hh]alt.*do not loop|Never spin a third",  # bounded, no infinite loop
            ],
            "Specialist Execution Contract",
        )

    def test_critical_rule_forbids_nested_orchestrator(self):
        """Critical Rules forbid spawning the Orchestrator as a nested subagent."""
        self._assert_all(
            self.orch,
            [r"NEVER spawn the Orchestrator as a nested subagent"],
            "orchestrator critical rule (nested subagent)",
        )

    def test_critical_rule_forbids_replacing_quiet_specialist(self):
        """Critical Rules forbid replacing a quiet specialist on a hunch / running two instances."""
        self._assert_all(
            self.orch,
            [
                r"NEVER replace a quiet specialist",
                r"NEVER run two instances",
            ],
            "orchestrator critical rules (quiet/duplicate specialist)",
        )

    # --- Commands route to main-session orchestration --------------------------

    def test_resume_acts_as_orchestrator_not_nested(self):
        """/sdd-resume tells the main session to act as the Orchestrator, not spawn a nested one."""
        self._assert_all(
            self.resume,
            [
                r"act as the Orchestrator",
                r"not\b.*spawn\b.*nested\s+subagent",
            ],
            "sdd-resume act-as-orchestrator",
        )

    def test_feature_acts_as_orchestrator_not_nested(self):
        """/sdd-feature routes both scoping paths to main-session orchestration, no nested subagent."""
        self._assert_all(
            self.feature,
            [
                r"act as the Orchestrator",
                r"not\s+spawn\s+a\s+nested\s+Orchestrator",
            ],
            "sdd-feature act-as-orchestrator",
        )

    # --- Global CLAUDE.md carries the rule (installed downstream) ---------------

    def test_claude_md_has_execution_model_section(self):
        """The installed CLAUDE.md carries the stall-safe execution model for every project."""
        self._assert_all(
            self.claude,
            [
                r"###\s+Orchestration Execution Model",
                r"main session\s+acts as\s+the\s+Orchestrator",
                r"Specialist Execution Contract",
                r"respawn",
            ],
            "CLAUDE.md Orchestration Execution Model",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
