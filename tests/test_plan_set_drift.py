#!/usr/bin/env python3
"""FR-14: the attribution rule's PLAN SET must not drift behind what `/sdd-feature` scaffolds.

`AT-2(a)` excludes a closed, named set of plan documents from "produced output". That list is
hardcoded in the attribution fence. `/sdd-feature` is what actually creates a feature's scaffold.
If the command ever scaffolds a file the list does not name, that file **COUNTS** as produced
output — and a feature that produced nothing at all then reaches a PASS on the strength of its own
scaffolding.

That is **Residual A**, disclosed in `requirements.md` Appendix A.5 as a bounded false-PASS
requiring plan-set drift. FR-14 is its named mitigation, and it was the last requirement in this
feature with no test at all.

The scaffolded set is **derived from `commands/sdd-feature.md`**, never restated here. A second
hardcoded list would drift in exactly the same way as the first, and would fail together with it —
two copies of the same mistake agreeing with each other is not verification.

Both directions are asserted, because measurement showed the two sets are **exactly equal** today.
They differ in severity, and the failure messages say which is which:
  - scaffolded but NOT in the plan set  -> the hole. That file COUNTS, so a feature that produced
    nothing reaches PASS on its own scaffolding. Residual A widens.
  - in the plan set but NOT scaffolded  -> stale, not dangerous: the rule excludes a file that no
    longer appears. Still drift, and still worth failing on while equality holds.

An earlier draft of this module assumed the plan set was legitimately a superset, on the reasoning
that requirements.md and design.md are authored after scaffolding. That was wrong — `/sdd-feature`
creates all seven as stubs — and asserting the weaker property would have let real drift through
in one direction. The assumption was disproved by printing both sets rather than by reasoning.

EXPECTED ON ANY RE-RUN: 7 files derived from the command, 7 in the plan set, the two sets equal.
A derived set of 0 fails the validity control rather than passing vacuously.

Run:
    python3 -m unittest tests.test_plan_set_drift -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SDD_FEATURE = ROOT / "commands" / "sdd-feature.md"
CODE_REVIEWER = ROOT / "agents" / "code-reviewer.md"


def scaffolded_set():
    """Derive the files `/sdd-feature` creates, from the command's own section headings.

    The command documents each created file as a heading of the form
    `### \\`.specs/features/$ARGUMENTS/<path>\\``. Deriving from those headings means adding a new
    scaffolded file automatically enters this set, which is the whole point: the drift shows up
    without anyone remembering to update a list.
    """
    text = SDD_FEATURE.read_text(encoding="utf-8")
    found = re.findall(r"^###\s+`\.specs/features/\$ARGUMENTS/([^`]+)`", text, re.MULTILINE)
    return sorted(set(found))


def plan_set():
    """Extract AT-2(a)'s named plan documents from the live attribution fence."""
    text = CODE_REVIEWER.read_text(encoding="utf-8")
    i = text.index("(a) PLAN SET")
    body = text[i:text.index("(b) NO TASK TOUCHED IT", i)]
    return sorted(set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|json))`", body)))


class PlanSetDrift(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.scaffolded = scaffolded_set()
        cls.plan = plan_set()

    def test_derivation_is_non_empty(self):
        """Validity control. A derivation returning nothing would make the guard below vacuous."""
        self.assertGreaterEqual(
            len(self.scaffolded), 3,
            f"derived only {self.scaffolded} from {SDD_FEATURE.name}. The heading format it is "
            "parsed from has changed, so this module is no longer checking anything. Fix the "
            "derivation — do not hardcode the list.",
        )
        self.assertGreaterEqual(
            len(self.plan), 5,
            f"extracted only {self.plan} from AT-2(a); the fence format has changed",
        )

    def test_every_scaffolded_file_is_named_in_the_plan_set(self):
        """The one direction that is a hole. A scaffolded file the rule does not name COUNTS."""
        missing = [f for f in self.scaffolded if f not in self.plan]
        self.assertEqual(
            missing, [],
            f"`/sdd-feature` scaffolds {missing}, which AT-2(a)'s PLAN SET does not name. Those "
            "files therefore COUNT as produced output, so a feature that produced nothing reaches "
            "a PASS on the strength of its own scaffolding. This is Residual A widening, and FR-14 "
            f"exists to catch exactly this.\n  scaffolded: {self.scaffolded}\n  plan set:   {self.plan}",
        )

    def test_plan_set_names_nothing_the_command_no_longer_scaffolds(self):
        """The other direction: stale rather than dangerous, but still drift while equality holds."""
        stale = [p for p in self.plan if p not in self.scaffolded]
        self.assertEqual(
            stale, [],
            f"AT-2(a) names {stale}, which `/sdd-feature` no longer scaffolds. Not a hole — the "
            "rule would exclude a file that never appears — but the two lists have drifted apart "
            "and one of them is now wrong.",
        )

    def test_gitignore_scratch_limb_is_present(self):
        """AT-2(a)'s second limb covers the root .gitignore patterns /sdd-feature appends."""
        text = CODE_REVIEWER.read_text(encoding="utf-8")
        i = text.index("(a) PLAN SET")
        body = text[i:text.index("(b) NO TASK TOUCHED IT", i)]
        self.assertIn("`.gitignore`", body, "AT-2(a) no longer covers the root .gitignore")
        self.assertIn("scratch patterns", body)

    def test_the_scratch_patterns_still_exist_in_the_command(self):
        """The limb is only meaningful while /sdd-feature actually appends those patterns."""
        text = SDD_FEATURE.read_text(encoding="utf-8")
        for pattern in ("input-data", "spec-memory"):
            self.assertIn(
                pattern, text,
                f"/sdd-feature no longer mentions the {pattern} scratch pattern, so AT-2(a)'s "
                ".gitignore limb guards nothing",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
