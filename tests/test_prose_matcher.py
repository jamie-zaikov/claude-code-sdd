#!/usr/bin/env python3
"""The prose matcher itself: a positive pin must go RED when a negation reverses the rule, and stay
GREEN for emphasis, wrapping, and a negation that governs another clause.

Found by the 2026-10-30 test-quality audit: "Do not rebuild it on every attempt — retain the old
pack even after a spec amendment." passed all four context-pack pins, because the pin on "Rebuild
it on every attempt" matched inside the negated sentence.

Run:
    python3 -m unittest tests.test_prose_matcher -v
"""

import unittest

try:
    from tests import prose
except ImportError:  # run from inside tests/
    import prose

PIN = r"Rebuild it on every attempt"


class AffirmsTest(unittest.TestCase):
    def test_the_audited_inversion_is_red(self):
        text = "Do not rebuild it on every attempt — retain the old pack even after a spec amendment."
        self.assertIsNone(prose.affirms(text, PIN))
        self.assertIsNotNone(prose.search(text, PIN), "search stays raw: lacks() must still see it")

    def test_every_negation_word_is_red(self):
        for lead in ("Never", "Don't", "You must not", "Agents cannot", "No agent may", "Without"):
            with self.subTest(lead=lead):
                self.assertIsNone(prose.affirms(f"{lead} rebuild it on every attempt.", PIN))

    def test_a_soft_wrap_after_the_negation_is_still_red(self):
        for text in ("Do not\nrebuild it on every attempt.", "Never\n  rebuild it on every attempt.",
                     "- You must **not**\n  rebuild it on every attempt."):
            with self.subTest(text=text):
                self.assertIsNone(prose.affirms(text, PIN))
                self.assertFalse(prose.near(text, r"rebuild|regenerate", r"(?:every|each) attempt"))

    def test_a_new_item_heading_or_paragraph_ends_the_clause(self):
        for text in ("- Never skip the check\n- rebuild it on every attempt.",
                     "Do not skip it.\n\nRebuild it on every attempt.",
                     "## Not optional\nRebuild it on every attempt.",
                     "1. No cache\n2. Rebuild it on every attempt."):
            with self.subTest(text=text):
                self.assertIsNotNone(prose.affirms(text, PIN))

    def test_presentation_stays_green(self):
        for text in ("Rebuild it on every attempt.", "**Rebuild** it on\n   every attempt.",
                     "- Rebuild it on every\n  attempt, from the specs."):
            with self.subTest(text=text):
                self.assertIsNotNone(prose.affirms(text, PIN))

    def test_a_negation_in_another_clause_stays_green(self):
        for text in ("When no record matches, rebuild it on every attempt.",
                     "Never reuse a pack; rebuild it on every attempt.",
                     "A pack is not shared between tasks or reused: rebuild it on every attempt.",
                     "It runs without asking the user, and agents rebuild it on every attempt."):
            with self.subTest(text=text):
                self.assertIsNotNone(prose.affirms(text, PIN))

    def test_a_negative_rule_carries_its_negation_in_the_pin(self):
        self.assertIsNotNone(prose.affirms("Overnight mode never halts the run.",
                                           r"never halts the run"))
        self.assertIsNone(prose.affirms("Overnight mode halts the run.", r"never halts the run"))

    def test_a_dot_inside_a_path_does_not_end_the_clause(self):
        for text in ("On resume, never run `python3 ~/.claude/tools/sdd-wave.py status` first.",
                     "On resume, never run ~/.claude/tools/sdd-wave.py status first."):
            with self.subTest(text=text):
                self.assertIsNone(prose.affirms(text, r"sdd-wave\.py status"))

    def test_a_negated_match_does_not_hide_an_overlapping_one(self):
        text = "Do not rebuild it from cache; rebuild it on every attempt."
        self.assertIsNotNone(prose.affirms(text, r"rebuild it.{0,40}?attempt"))

    def test_a_negated_match_does_not_hide_a_later_one(self):
        text = "No unexplained acronyms or slang. Expand an acronym the first time it appears."
        self.assertTrue(prose.near(text, r"acronym", r"first time"))


class NearTest(unittest.TestCase):
    RULE = ("`.specs/` is excluded, except the files that `tech.md` lists under "
            "`Suite spec inputs:`, which stay in the hash.")
    TERMS = (r"`\.specs/` is excluded", r"except", r"`Suite spec inputs:`", r"stay in the hash")

    def test_the_rule_is_green(self):
        self.assertTrue(prose.near(self.RULE, *self.TERMS))

    def test_a_negated_occurrence_does_not_hide_a_later_one(self):
        self.assertTrue(prose.near("Use the pack, never the cache, and the cache stays.",
                                   r"pack", r"cache"))
        self.assertFalse(prose.near("Use the pack, never the cache.", r"pack", r"cache"))

    def test_a_negation_before_any_term_is_red(self):
        for inverted in (self.RULE.replace("which stay", "which never stay"),
                         self.RULE.replace("is excluded", "is not excluded"),
                         self.RULE.replace(", except", ", never except")):
            with self.subTest(inverted=inverted):
                self.assertFalse(prose.near(inverted, *self.TERMS))


if __name__ == "__main__":
    unittest.main()
