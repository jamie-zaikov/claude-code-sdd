#!/usr/bin/env python3
"""Tests for the repo/installed-copy sync classifier (FR-11.8 carve-out).

The carve-out exists so a strict byte-identity assertion cannot pressure anyone into syncing the
live agent fleet early just to get a green suite. That pressure is real and it is dangerous here:
the installed copies are what the reviewer subagents load, so syncing unreviewed agent contracts
would hand the reviewers the very text they are supposed to judge.

The classifier must therefore be permissive about exactly one thing — the repository copy being
ahead of the last merged revision — and strict about everything else.

EXPECTED ON ANY RE-RUN: 8 tests, 8 pass.

Run:
    python3 -m unittest tests.test_sync_state -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_state import classify_sync_state  # noqa: E402

MERGED = "line one\nline two\nGUARD: the invariant\n"
AHEAD = "line one\nline two CHANGED\nline three added\nGUARD: the invariant\n"
HAND_EDITED = "line one\nline two\nGUARD: the invariant\nsomeone edited the install\n"

INVARIANTS = ("GUARD: the invariant",)


class ClassifySyncState(unittest.TestCase):

    def test_identical_copies_are_identical(self):
        self.assertEqual(classify_sync_state(MERGED, MERGED, INVARIANTS, MERGED), "identical")

    def test_repo_ahead_of_last_merged_revision_is_pending(self):
        """The normal window: work committed to a feature branch, not yet installed."""
        self.assertEqual(classify_sync_state(AHEAD, MERGED, INVARIANTS, MERGED), "pending")

    def test_modified_line_is_still_pending_not_drift(self):
        """The case that broke the first attempt at this helper.

        A real edit MODIFIES lines, so the previous wording survives only in the installed copy.
        A content heuristic reads that as divergence. Anchoring on the last merged revision does
        not, and this test is what pins the difference.
        """
        self.assertNotIn("line two CHANGED", MERGED)
        self.assertEqual(classify_sync_state(AHEAD, MERGED, INVARIANTS, MERGED), "pending")

    def test_hand_edited_install_is_drift(self):
        """The installed copy gained content of its own. That is never pending."""
        self.assertEqual(classify_sync_state(MERGED, HAND_EDITED, INVARIANTS, MERGED), "drift")

    def test_repo_losing_an_invariant_is_drift_even_when_pending_shaped(self):
        """`pending` must never become a blanket excuse for a dropped guarantee."""
        without = AHEAD.replace("GUARD: the invariant\n", "")
        self.assertEqual(classify_sync_state(without, MERGED, INVARIANTS, MERGED), "drift")

    def test_repo_losing_an_invariant_is_drift_even_when_copies_are_identical(self):
        """Both copies agreeing on a lost invariant is not agreement worth having."""
        without = MERGED.replace("GUARD: the invariant\n", "")
        self.assertEqual(classify_sync_state(without, without, INVARIANTS, without), "drift")

    def test_without_a_merged_revision_a_difference_is_drift(self):
        """Fail-safe direction: unproven means drift, never a silent pass."""
        self.assertEqual(classify_sync_state(AHEAD, MERGED, INVARIANTS, None), "drift")
        self.assertEqual(classify_sync_state(AHEAD, MERGED, INVARIANTS, ()), "drift")

    def test_installed_copy_one_revision_behind_the_tip_is_pending(self):
        """The post-merge case. This is the bug that made the whole helper too strict.

        Anchoring on the tip alone is right until a merge lands. Then the tip moves, and an
        installed copy that is simply awaiting ./install.sh reads as drift. That fired for real on
        the merge of the feature this helper was written for, and a false drift is corrosive: it
        trains the reader to sync the live fleet reflexively, which is the hazard the helper exists
        to prevent.
        """
        older = MERGED
        tip = AHEAD                      # merged since; the repo is now at the tip
        installed = older                # not yet re-installed
        self.assertEqual(
            classify_sync_state(tip, installed, INVARIANTS, (tip, older)), "pending",
            "an installed copy matching an ANCESTOR of the tip must be pending, not drift",
        )
        # ...and a copy matching no revision at all is still drift.
        self.assertEqual(
            classify_sync_state(tip, HAND_EDITED, INVARIANTS, (tip, older)), "drift")

    def test_no_invariants_supplied_still_discriminates(self):
        """Validity control: the classifier must not collapse to 'everything passes'."""
        self.assertEqual(classify_sync_state(MERGED, HAND_EDITED, (), MERGED), "drift")
        self.assertEqual(classify_sync_state(AHEAD, MERGED, (), MERGED), "pending")


if __name__ == "__main__":
    unittest.main(verbosity=2)
