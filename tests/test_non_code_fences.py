#!/usr/bin/env python3
"""Fence hub for the non-code feature track: four fences, six replica instances, zero drift.

`requirements.md` is the authoritative copy of all four fences. This module is the **hub**: it
extracts each fence body from that source and asserts every replica equals it byte for byte. No
contract is the winning copy, which is what keeps the identity relation symmetric.

Provenance is recorded HERE and in `design.md` — the two places that are not replicated — and
nowhere inside a contract. Rules R-1..R-6 forbid a provenance sentence inside or immediately
adjacent to any fence body, because a sentence naming one file as the source makes every other
copy derived and breaks the symmetry the identity assertions depend on.

Fences and their replica targets:
  F1  ATTRIBUTION RULE (AT-1..AT-6)   -> code-reviewer, security-reviewer      (2 instances)
  F2  SIGNAL ROLES (attribution)      -> code-reviewer, security-reviewer      (2 instances)
  F3  FEATURE-REVIEW GATE INVARIANT   -> orchestrator                          (1 instance)
  F4  reclassification arming predicate -> orchestrator                        (1 instance)

EXPECTED ON ANY RE-RUN: 4 fences, 6 replica instances, across 3 contract files. Counting
convention: a "fence instance" is one fenced block in one contract whose body equals the
authoritative body exactly. A different total is a real change, not a counting artefact.

Mutation-verified. Each of these turns the module RED:
  - re-indent one line of any replica fence body
  - append one trailing space to any line of any replica fence body
  - append a seventh limb `AT-7` inside a replica fence
  - insert a paragraph between F1 and F2 in either reviewer
  - add "copied from requirements.md" immediately above a replica fence

Run:
    python3 -m unittest tests.test_non_code_fences -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / ".specs/features/non-code-feature-track/requirements.md"

CODE_REVIEWER = ROOT / "agents/code-reviewer.md"
SECURITY_REVIEWER = ROOT / "agents/security-reviewer.md"
ORCHESTRATOR = ROOT / "agents/orchestrator.md"

# First body line of each fence. Each is unique within requirements.md, which is how the
# extraction anchors without depending on line numbers that any edit would move.
F1_ANCHOR = "ATTRIBUTION RULE — what evidences that a feature's tasks produced an artifact"
F2_ANCHOR = "SIGNAL ROLES (attribution)"
F3_ANCHOR = "FEATURE-REVIEW GATE INVARIANT"
F4_ANCHOR = "Triggers. Any one of the following,"

EXPECTED_FENCE_COUNT = 4
EXPECTED_INSTANCE_COUNT = 6


def fenced_bodies(path):
    """Return every fenced-code-block body in a markdown file, in document order."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    bodies, i = [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            bodies.append("\n".join(lines[i + 1:j]))
            i = j + 1
        else:
            i += 1
    return bodies


def authoritative(anchor):
    """Extract one fence body from requirements.md by its unique first body line."""
    matches = [b for b in fenced_bodies(REQUIREMENTS) if b.startswith(anchor)]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly 1 fence in requirements.md starting {anchor!r}, found {len(matches)}. "
            "The hub cannot resolve an authoritative body, so every identity assertion below would "
            "be meaningless. Fix the source before changing any replica."
        )
    return matches[0]


class FenceHub(unittest.TestCase):
    """Every replica equals the authoritative body byte for byte."""

    @classmethod
    def setUpClass(cls):
        cls.F1 = authoritative(F1_ANCHOR)
        cls.F2 = authoritative(F2_ANCHOR)
        cls.F3 = authoritative(F3_ANCHOR)
        cls.F4 = authoritative(F4_ANCHOR)

    def test_authoritative_bodies_are_not_vacuous(self):
        """Validity control: an empty or trivial body would make identity assertions pass on nothing."""
        for name, body in (("F1", self.F1), ("F2", self.F2), ("F3", self.F3), ("F4", self.F4)):
            self.assertGreaterEqual(
                len(body.strip().splitlines()), 2,
                f"{name}'s authoritative body is shorter than 2 lines. An identity assertion against "
                "a near-empty constant proves nothing.",
            )
        # F1 must actually carry all six limbs, or "byte-identical" is byte-identical to a stub.
        for limb in ("AT-1", "AT-2", "AT-3", "AT-4", "AT-5", "AT-6"):
            self.assertIn(limb, self.F1, f"F1's authoritative body is missing limb {limb}")

    def test_f1_replicated_byte_identical_into_both_reviewers(self):
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            n = sum(1 for b in fenced_bodies(path) if b == self.F1)
            self.assertEqual(
                n, 1,
                f"{path.name} must carry exactly one byte-identical copy of F1 (the attribution "
                f"rule); found {n}. Zero means it drifted from requirements.md; more than one means "
                "a duplicated insert.",
            )

    def test_f2_replicated_byte_identical_into_both_reviewers(self):
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            n = sum(1 for b in fenced_bodies(path) if b == self.F2)
            self.assertEqual(n, 1, f"{path.name} must carry exactly one byte-identical copy of F2; found {n}")

    def test_f3_and_f4_replicated_byte_identical_into_orchestrator(self):
        bodies = fenced_bodies(ORCHESTRATOR)
        self.assertEqual(sum(1 for b in bodies if b == self.F3), 1,
                         "orchestrator.md must carry exactly one byte-identical copy of F3 (the gate invariant)")
        self.assertEqual(sum(1 for b in bodies if b == self.F4), 1,
                         "orchestrator.md must carry exactly one byte-identical copy of F4 (the arming predicate)")

    def test_instance_total_is_six_across_three_files(self):
        """The whole-fleet count, so a fence added to a fifth site is visible immediately."""
        total = 0
        for path in (CODE_REVIEWER, SECURITY_REVIEWER, ORCHESTRATOR):
            for body in fenced_bodies(path):
                if body in (self.F1, self.F2, self.F3, self.F4):
                    total += 1
        self.assertEqual(
            total, EXPECTED_INSTANCE_COUNT,
            f"expected {EXPECTED_INSTANCE_COUNT} replica fence instances across the three contract "
            f"files, found {total}. Counting convention: one fenced block whose body equals an "
            "authoritative body exactly.",
        )

    def test_no_replica_fence_carries_an_appended_limb(self):
        """A near-miss body is worse than a missing one: it reads right and is not the rule."""
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            for body in fenced_bodies(path):
                if body.startswith(F1_ANCHOR):
                    self.assertEqual(
                        body, self.F1,
                        f"{path.name} carries a block that opens with F1's first line but is not "
                        "byte-identical to it. An appended limb or an edited limb changes the rule "
                        "while still looking like it.",
                    )
                if body.startswith(F2_ANCHOR):
                    self.assertEqual(body, self.F2, f"{path.name}: F2 near-miss, not byte-identical")


class FenceAdjacency(unittest.TestCase):
    """F1 and F2 sit adjacent, F1 first, with nothing interposed but one blank line."""

    def test_f1_immediately_precedes_f2_in_both_reviewers(self):
        for path in (CODE_REVIEWER, SECURITY_REVIEWER):
            text = path.read_text(encoding="utf-8")
            f1_close = text.index(F1_ANCHOR)
            f1_end = text.index("\n```", f1_close) + len("\n```")
            between = text[f1_end:text.index(F2_ANCHOR)]
            # Only the closing newline, one blank line, and the opening fence may intervene.
            self.assertEqual(
                between.strip().strip("`"), "",
                f"{path.name}: something is interposed between F1 and F2 — {between!r}. They must be "
                "contiguous so the pin can treat them as one frozen region; an interposed proviso "
                "would otherwise be able to qualify the rule from between its two halves.",
            )


class ProvenanceProhibition(unittest.TestCase):
    """R-1..R-6: no contract may name a source for a fence, inside it or immediately adjacent."""

    # Words that would make a replica derived rather than a peer.
    PROVENANCE = re.compile(
        r"copied from|replicated from|verbatim from|source of truth|authoritative copy|"
        r"canonical copy|see `?requirements\.md|as defined in `?requirements\.md",
        re.IGNORECASE,
    )
    # A replica must not name another contract file next to the fence either.
    OTHER_CONTRACT = re.compile(r"agents/[a-z-]+\.md")

    def _regions(self, path, anchors):
        """Yield (anchor, region) where region is the fence plus the paragraph either side."""
        lines = path.read_text(encoding="utf-8").splitlines()
        for anchor in anchors:
            for n, line in enumerate(lines):
                if line.startswith(anchor):
                    o = n
                    while o > 0 and not lines[o].startswith("```"):
                        o -= 1
                    c = n
                    while c < len(lines) - 1 and not lines[c].startswith("```"):
                        c += 1
                    if not lines[o].startswith("```") or not lines[c].startswith("```"):
                        self.fail(
                            f"{path.name}: the anchor {anchor[:40]!r} is not inside a fenced "
                            "block; an unbounded walk would run off the file."
                        )
                    yield anchor, "\n".join(lines[max(0, o - 4):min(len(lines), c + 5)])

    def test_no_provenance_sentence_inside_or_adjacent_to_any_fence(self):
        targets = [
            (CODE_REVIEWER, (F1_ANCHOR, F2_ANCHOR)),
            (SECURITY_REVIEWER, (F1_ANCHOR, F2_ANCHOR)),
            (ORCHESTRATOR, (F3_ANCHOR, F4_ANCHOR)),
        ]
        for path, anchors in targets:
            for anchor, region in self._regions(path, anchors):
                hit = self.PROVENANCE.search(region)
                if hit is not None:
                    self.fail(
                        f"{path.name}: a provenance phrase {hit.group(0)!r} appears inside or "
                        f"adjacent to the fence starting {anchor[:40]!r}. Naming a source makes this "
                        "copy derived and inverts the no-winning-copy decision. Provenance belongs "
                        "in design.md and in this test module, which are the two places that are "
                        "not replicated."
                    )
                other = self.OTHER_CONTRACT.search(region)
                if other is not None:
                    self.fail(
                        f"{path.name}: another contract file {other.group(0)!r} is named adjacent to "
                        f"the fence starting {anchor[:40]!r}. A replica must not point at a peer."
                    )

    def test_provenance_detector_discriminates(self):
        """Control: the detector must fire on a real provenance sentence, or it proves nothing."""
        self.assertIsNotNone(self.PROVENANCE.search("This block is copied from requirements.md."))
        self.assertIsNotNone(self.PROVENANCE.search("requirements.md is the authoritative copy."))
        # ...and must NOT fire on the legitimate operational prose that does sit next to the fences.
        self.assertIsNone(self.PROVENANCE.search(
            "The task marker is the fixed trailer line `SDD-Task: <N>`, one per line."))
        self.assertIsNone(self.PROVENANCE.search(
            "`AT-2(b)` reads commit provenance through your existing `git` access under `Bash`."))


class SingleSiteBlocks(unittest.TestCase):
    """CLS and NCT are single-site: exactly one copy, in exactly one contract."""

    def test_cls_block_exists_once_and_only_in_the_orchestrator(self):
        for path in (CODE_REVIEWER, SECURITY_REVIEWER, ROOT / "agents/task-tester.md",
                     ROOT / "agents/task-validator.md"):
            self.assertEqual(
                sum(1 for b in fenced_bodies(path) if b.startswith("CLS — ARTIFACT CLASSIFICATION")), 0,
                f"{path.name} carries a copy of the CLS block. CLS is single-site: the orchestrator "
                "transmits it in the invocation payload, so no other contract replicates it.",
            )
        self.assertEqual(
            sum(1 for b in fenced_bodies(ORCHESTRATOR) if b.startswith("CLS — ARTIFACT CLASSIFICATION")), 1,
            "orchestrator.md must carry exactly one CLS block",
        )

    def test_nct_block_exists_once_and_only_in_the_tester(self):
        tester = ROOT / "agents/task-tester.md"
        self.assertEqual(
            sum(1 for b in fenced_bodies(tester) if b.startswith("NO APPLICABLE TESTS")), 1,
            "task-tester.md must carry exactly one NO APPLICABLE TESTS block",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
