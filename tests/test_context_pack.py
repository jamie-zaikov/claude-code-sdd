#!/usr/bin/env python3
"""Unit tests for tools/sdd-context-pack.py — one task's cited spec text, never a silent gap.

The fixture copies the three spec styles found in real features (Sep-Oct 2026): requirement
headings (`### FR-2:` / `#### FR-2.1:`), design components as headings (`#### C2 —`), bold leads
(`**C1 —`), bullets (`- **DD-21 —`), and table rows (`| C19 | ... |`). Stdlib only.

Run:
    python3 -m unittest tests.test_context_pack -v
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sdd_context_pack", ROOT / "tools" / "sdd-context-pack.py")
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

TASKS = """# Tasks

## Task 1: Binding functions
- [ ] 1. Binding functions

**Requirements:** FR-2.1, FR-3, NFR-1
**Design Reference:** C2, DD-4, C19 (`tools/`), I9
**Files:** `src/bind.py`
**Depends:** none

---

## Task 2: Later task
**Requirements:** FR-9.1–9.3
**Design Reference:** C1, DD-99

## Task 3: Wrapped fields
- [ ] 3.1. Also honour FR-4 here (cited only in a sub-task).

```sh
## a shell comment inside a fence is not a heading
```

**Requirements:** FR-2.1,
  FR-2.2, NFR-1
**Design Reference:** C2,
  DD-4
**Files:** `x.py`

## Task 4: Ranges and prefixes
**Requirements:** FR-2–FR-4, AC-7
**Design Reference:** C19–C21

## Task 12: Not task 1
**Requirements:** FR-4
"""

REQS = """# Requirements

## Functional Requirements

### FR-2: Binding
Parent text of FR-2.

#### FR-2.1: Apply overrides
WHEN overrides exist THE SYSTEM SHALL apply them.

#### FR-2.2: Null removes
Not cited.

### FR-3: Tokens
Parent FR-3.

#### FR-3.1: Token grammar
Child of FR-3, included because FR-3 is cited.

### FR-4: Other
Task 12 only.

### FR-9: Ranges
#### FR-9.1: one
#### FR-9.2: two
#### FR-9.3: three
#### FR-9.4: four, not in the range

## Non-Functional Requirements

### NFR-1: Speed
Fast.

### NFR-10: Not NFR-1
Must not be picked for NFR-1.

## Amendments (rev 2)

### FR-3.2: Added in an amendment
An amended child of FR-3, far from its parent.
"""

DESIGN = """# Design

## Architecture

### Components
| ID | Name | Path |
|---|---|---|
| C19 | Repo tooling | `tools/` |
| C20 | Other | `x/` |
| **DD-30** (OQ-1) | Decision in a table row with more text in the first cell | x |
| C200 | Must not match C20 | y |

**C1 — Construction (FR-9)**
Bold-lead component C1.

**C2 — Binding resolution (FR-2)**
Bold-lead component C2 body.

#### I9. Repo layout (C14-C17, C19)
Heading with a period after the id.

##### Layout detail
Sub-heading body without an id, still part of I9.

## Requirement Traceability
| FR-2.1 | C2 | binding |
| FR-2.10 | C7 | a longer id must not match |

## Design Decisions
- **DD-4 — When-lists**: bullet decision.
- **DD-5 — Other**: not cited.

```
#### C2 — inside a code fence, never a section
```
"""


class PackTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.feature = Path(self._tmp.name)
        (self.feature / "tasks.md").write_text(TASKS)
        (self.feature / "requirements.md").write_text(REQS)
        (self.feature / "design.md").write_text(DESIGN)
        self.pack = cp.build(self.feature, "1")

    def tearDown(self):
        self._tmp.cleanup()

    def test_task_block_is_exact(self):
        self.assertIn("## Task 1: Binding functions", self.pack)
        self.assertNotIn("## Task 2", self.pack)
        self.assertNotIn("Task 12 only", self.pack)

    def test_cited_requirements_and_children(self):
        self.assertIn("WHEN overrides exist", self.pack)
        self.assertIn("Child of FR-3, included", self.pack)
        self.assertNotIn("Null removes", self.pack)
        self.assertIn("### NFR-1: Speed", self.pack)
        self.assertNotIn("Must not be picked for NFR-1", self.pack)

    def test_design_in_every_style(self):
        self.assertIn("Bold-lead component C2 body.", self.pack)  # bold lead
        self.assertIn("bullet decision", self.pack)  # bullet
        self.assertIn("| C19 | Repo tooling", self.pack)  # table row
        self.assertIn("| ID | Name | Path |", self.pack)  # ...under its header
        self.assertIn("Heading with a period after the id.", self.pack)  # `I9.`
        self.assertNotIn("Bold-lead component C1.", self.pack)
        self.assertNotIn("not cited", self.pack)

    def test_amended_child_far_from_its_parent_is_included(self):
        self.assertIn("An amended child of FR-3, far from its parent.", self.pack)

    def test_a_deeper_sub_heading_stays_inside_its_section(self):
        self.assertIn("Sub-heading body without an id, still part of I9.", self.pack)

    def test_wrapped_fields_are_read_whole(self):
        pack = cp.build(self.feature, "3")
        self.assertIn("Null removes", pack)  # FR-2.2 on the continuation line
        self.assertIn("bullet decision", pack)  # DD-4 on the continuation line
        self.assertIn("### NFR-1: Speed", pack)

    def test_an_id_cited_only_in_a_sub_task_is_packed(self):
        self.assertIn("Task 12 only.", cp.build(self.feature, "3"))  # FR-4's body

    def test_a_fenced_heading_never_ends_the_task_block(self):
        self.assertIn("**Files:** `x.py`", cp.build(self.feature, "3"))

    def test_parent_ranges_design_ranges_and_other_prefixes(self):
        pack = cp.build(self.feature, "4")
        self.assertIn("### FR-3: Tokens", pack)  # the middle of FR-2–FR-4
        self.assertIn("| C20 | Other", pack)  # the middle of C19–C21
        nf = pack[pack.index("## NOT FOUND"):pack.index("## Task")]
        self.assertIn("- AC-7", nf)  # an unknown prefix is never silently dropped
        self.assertIn("- C21", nf)
        self.assertEqual(cp.cited_requirements("FR-1–FR-999"), ["FR-1", "FR-999"])  # no runaway range

    def test_table_row_whose_first_cell_starts_with_the_id(self):
        self.assertEqual(cp.sections_for(DESIGN, ["DD-30"], False)[1], [])
        sections, _ = cp.sections_for(DESIGN, ["C20"], False)
        self.assertNotIn("Must not match C20", "\n".join(sections))

    def test_an_exact_first_cell_wins_over_a_shared_row(self):
        doc = "| ID | x |\n|---|---|\n| C2 / C3 | shared |\n| C2-legacy | old |\n| C2 | the real one |\n"
        sections, missing = cp.sections_for(doc, ["C2"], False)
        self.assertEqual(missing, [])
        self.assertIn("the real one", sections[0])
        self.assertNotIn("shared", sections[0])

    def test_cross_parent_range_is_never_guessed(self):
        self.assertEqual(cp.cited_requirements("FR-1.2–FR-2.3"), ["FR-1.2", "FR-2.3"])

    def test_body_only_foreign_id_is_listed_apart(self):
        (self.feature / "tasks.md").write_text(TASKS.replace(
            "## Task 12: Not task 1", "## Task 5: Cross-feature\n- [ ] 5.1. Keep FR-77.1 of the old feature.\n"
            "```\nFR-88 inside a fence\n```\n**Requirements:** FR-2.1, FR-66\n\n## Task 12: Not task 1"))
        pack = cp.build(self.feature, "5")
        nf = pack[pack.index("## NOT FOUND"):pack.index("## Cited from another feature")]
        other = pack[pack.index("## Cited from another feature"):pack.index("## Task")]
        self.assertIn("- FR-66", nf)  # in the Requirements field: a real gap
        self.assertNotIn("FR-77.1", nf)
        self.assertIn("- FR-77.1", other)  # body-only and undefined here: another feature's id
        self.assertNotIn("FR-88", pack[:pack.index("## Task")])  # fenced code is never a citation

    def test_code_fence_is_never_a_section(self):
        self.assertEqual(self.pack.count("#### C2 — inside a code fence"), 0)

    def test_traceability_rows_match_exact_ids(self):
        self.assertIn("| FR-2.1 | C2 | binding |", self.pack)
        self.assertNotIn("a longer id must not match", self.pack)

    def test_not_found_lists_every_gap(self):
        pack2 = cp.build(self.feature, "2")
        nf = pack2[pack2.index("## NOT FOUND"):pack2.index("## Task")]
        self.assertIn("- DD-99", nf)
        self.assertNotIn("C1", nf)
        nf1 = self.pack[self.pack.index("## NOT FOUND"):self.pack.index("## Task")]
        self.assertIn("none", nf1)

    def test_ranges_expand(self):
        pack2 = cp.build(self.feature, "2")
        for n in (1, 2, 3):
            self.assertIn(f"#### FR-9.{n}:", pack2)
        self.assertNotIn("FR-9.4", pack2)
        for form in ("FR-9.1–9.3", "FR-9.1-3", "FR-9.1–FR-9.3"):
            self.assertEqual(cp.cited_requirements(form), ["FR-9.1", "FR-9.2", "FR-9.3"], form)

    def test_carry_forward_notes(self):
        (self.feature / "spec-memory").mkdir()
        (self.feature / "spec-memory" / "carry-forward.md").write_text(
            "- Task 1: keep the seam\n- Task 12: unrelated\n- T1 also counts\n")
        pack = cp.build(self.feature, "1")
        self.assertIn("keep the seam", pack)
        self.assertIn("T1 also counts", pack)
        self.assertNotIn("unrelated", pack)

    def test_sources_are_hashed(self):
        self.assertRegex(self.pack, r"- requirements\.md [0-9a-f]{16}")

    def test_deterministic(self):
        self.assertEqual(cp.build(self.feature, "1"), self.pack)

    def test_cli(self):
        self.assertEqual(cp.main(["--feature-dir", str(self.feature), "--task", "1"]), 0)
        self.assertTrue((self.feature / "spec-memory" / "context" / "task-1.md").is_file())
        self.assertEqual(cp.main(["--feature-dir", str(self.feature), "--task", "77"]), 1)
        self.assertEqual(cp.main(["--feature-dir", str(self.feature / "nope"), "--task", "1"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
