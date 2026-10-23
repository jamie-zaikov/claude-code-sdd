#!/usr/bin/env python3
"""Prose pins for the *Asking the User* rule: every question gives context, then WHAT, WHY, HOW.

Fixes questions that reached the user as bare ids and pipeline slang ("OQ-D2/D3: accept the design
defaults?"), so the user had to answer "elaborate" before they could decide. The rule lives in the
orchestrator playbook, with a Critical Rule and a pointer in the CLAUDE.md Communication Style
section, because the STE rule there said "conversational replies" and an AskUserQuestion call was
not read as one.

Matches use tests/prose.py, so rewording, re-wrapping or dropping emphasis stays GREEN and only a
change of meaning goes RED. Stdlib-only.

Run:
    python3 -m unittest tests.test_asking_the_user -v
"""

import re
import unittest
from pathlib import Path

from tests.prose import near, search

ROOT = Path(__file__).resolve().parent.parent
ORCH = (ROOT / "agents" / "orchestrator.md").read_text(encoding="utf-8")
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}.*?(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert m, f"section '## {heading}' not found"
    return m.group(0)


def step(sec, name):
    """The text of one numbered step ("3. WHY. ..."), up to the next step or blank line."""
    m = re.search(rf"^\s*\d\.\s+\**{name}\.(.*?)(?=^\s*\d\.\s|\n\s*\n)", sec, re.MULTILINE | re.DOTALL)
    assert m, f"step {name} not found"
    return m.group(1)


def critical_rules():
    m = re.search(r"^## Critical Rules\n(.*)", ORCH, re.MULTILINE | re.DOTALL)
    assert m, "Critical Rules section not found"
    return m.group(1)


class AskingTheUserSectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sec = section(ORCH, "Asking the User")

    def test_covers_every_question_and_both_channels(self):
        self.assertTrue(near(self.sec, r"\bevery\b", r"question"))
        self.assertTrue(near(self.sec, r"AskUserQuestion", r"plain text|in text", window=200))

    def test_order_is_context_what_why_how(self):
        self.assertTrue(
            search(self.sec, r"^1\. Context\..*^2\. WHAT\..*^3\. WHY\..*^4\. HOW\."),
            "the four steps must be numbered Context, WHAT, WHY, HOW in that order",
        )

    def test_how_carries_a_recommendation(self):
        self.assertTrue(near(step(self.sec, "HOW"), r"recommendation", r"reason"))

    def test_why_states_the_default(self):
        self.assertTrue(near(step(self.sec, "WHY"), r"\bdefault\b"))

    def test_ask_user_question_is_a_reply_under_ste(self):
        self.assertTrue(near(self.sec, r"AskUserQuestion. call is a reply to the user"))
        self.assertTrue(near(self.sec, r"option description", r"Simplified Technical English"))

    def test_no_bare_ids(self):
        self.assertTrue(near(self.sec, r"No bare ids", r"never stands alone"))
        self.assertTrue(near(self.sec, r"what it means first", r"id may follow"))

    def test_no_acronyms_slang_or_cross_references(self):
        self.assertTrue(near(self.sec, r"acronym", r"first time"))
        self.assertTrue(near(self.sec, r"pipeline", r"explanation|plain words", window=200))
        self.assertTrue(near(self.sec, r"Never send the user to another document"))

    def test_every_option_states_its_effect(self):
        self.assertTrue(near(self.sec, r"Every option states its effect"))
        self.assertTrue(near(self.sec, r"Accept defaults", r"not a valid option"))

    def test_specialist_questions_are_rewritten_not_forwarded(self):
        self.assertTrue(near(self.sec, r"specialist returns", r"rewritten"))
        self.assertTrue(near(self.sec, r"Never paste the specialist"))

    def test_background_is_never_cut_for_room(self):
        self.assertTrue(near(self.sec, r"context, WHAT and WHY", r"text first", r"then make the call"))
        self.assertTrue(near(self.sec, r"never cut"))

    def test_fixed_phase_prompts_are_only_the_last_line(self):
        self.assertTrue(near(self.sec, r"fixed prompts", r"last line", r"never the whole"))

    def test_overnight_entries_follow_the_shape(self):
        self.assertTrue(near(self.sec, r"userApprovalNeeded", r"same shape"))


class AskingTheUserWiringTest(unittest.TestCase):
    def test_section_precedes_phase_routing(self):
        self.assertLess(ORCH.index("## Asking the User"), ORCH.index("## Phase Routing"))

    def test_critical_rule(self):
        rules = critical_rules()
        self.assertTrue(near(rules, r"NEVER ask the user a question without its context",
                             r"WHAT", r"WHY", r"HOW", r"recommendation"))
        self.assertTrue(near(rules, r"specialist", r"rewritten, never forwarded"))

    def test_overnight_needs_you_uses_the_shape(self):
        self.assertTrue(near(ORCH, r"^## Needs you", r"userApprovalNeeded", r"context",
                             r"Asking the User"))

    def test_claude_md_points_to_the_rule(self):
        style = section(CLAUDE, "Communication Style")
        self.assertTrue(near(style, r"AskUserQuestion. call is a reply to the user"))
        self.assertTrue(near(style, r"context first", r"WHAT", r"WHY", r"HOW", r"recommendation"))
        self.assertTrue(near(style, r"Never use a bare id"))
        self.assertTrue(near(style, r"rewritten, never forwarded"))
        self.assertTrue(near(style, r"Asking the User"))


if __name__ == "__main__":
    unittest.main()
