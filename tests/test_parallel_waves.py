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


if __name__ == "__main__":
    unittest.main(verbosity=2)
