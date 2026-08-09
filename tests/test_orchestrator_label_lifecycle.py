#!/usr/bin/env python3
"""Structural lint for Task 12's orchestrator fixes (label-lifecycle + scaffold-push).

agents/orchestrator.md is a markdown/config artifact — an agent-instruction doc, not executable
code — so this "test" is a structure/ordering lint over the markdown text. It asserts the three
Task-12 fixes and the invariants they must preserve:

  Fix 1 (FR-10/FR-10.1/FR-11.1): in the Feature Review Gate PASS branch, `blocked:feature-review`
         is CLEARED *before* `ready-to-merge` is SET (an ordering assertion, not mere presence).
  Fix 2 (FR-9/FR-11.1): the per-task pass branch clears EVERY recorded `blocked:*` label for the
         task (all-not-singular wording), not merely the last stage's label.
  Fix 3 (FR-7): the scaffold `push` is scoped to the NEW-feature case ("only on first scaffold",
         "never on resume") and the raw scaffold push carries NO `base` field.
  Invariant (NFR-1/NFR-4): the orchestrator never runs `gh`/`git push` itself; github-agent is the
         sole choke-point.

Assertions target load-bearing tokens and their ORDER, extracted from targeted regions of the doc,
rather than brittle full-sentence matches. Stdlib-only (mirrors the Task-2 lint style in
tests/test_orchestrator_github_integration.py) so it runs anywhere the repo's hooks run.

Run:
    python3 -m unittest tests.test_orchestrator_label_lifecycle -v
    # or
    python3 tests/test_orchestrator_label_lifecycle.py
"""

import re
import unittest
from pathlib import Path

# Resolve the orchestrator relative to this test so it survives consolidation / worktree layout:
#   <root>/tests/test_orchestrator_label_lifecycle.py  ->  <root>/agents/orchestrator.md
ORCH_PATH = Path(__file__).resolve().parent.parent / "agents" / "orchestrator.md"

# The reconciled global copy lives at a fixed absolute path (out-of-band, byte-identical target).
GLOBAL_ORCH_PATH = Path("/Users/jamie.zaikov/.claude/agents/orchestrator.md")


def split_frontmatter(text):
    """Split a markdown file into (frontmatter_str, body_str).

    Returns (None, text) if the file does not open with a valid `---` frontmatter fence.
    """
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def region_between(text, start_pat, end_pat):
    """Return the substring from the first match of start_pat to the next match of end_pat.

    If end_pat is not found after start, returns from start_pat to end-of-text. Returns None if
    start_pat is not found. Both patterns are searched case-insensitively / multiline.
    """
    flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
    ms = re.search(start_pat, text, flags)
    if not ms:
        return None
    rest = text[ms.start():]
    me = re.search(end_pat, rest[1:], flags)  # start search past the start match itself
    if not me:
        return rest
    return rest[: me.start() + 1]


class OrchestratorLabelLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert ORCH_PATH.exists(), f"orchestrator definition not found at {ORCH_PATH}"
        cls.text = ORCH_PATH.read_text(encoding="utf-8")
        fm, body = split_frontmatter(cls.text)
        cls.frontmatter_raw = fm
        cls.body = body

    # --- (1) Basic markdown structure -----------------------------------------

    def test_parses_as_valid_markdown(self):
        """(1) The file parses as valid markdown: intact frontmatter (if any), non-empty body with
        headings, and balanced code fences."""
        if self.text.startswith("---"):
            self.assertIsNotNone(
                self.frontmatter_raw,
                "file opens with '---' but has no closing frontmatter fence",
            )
            # Frontmatter should carry the agent identity keys, unbroken by the edits.
            self.assertRegex(self.frontmatter_raw, r"(?m)^name:\s*orchestrator\b",
                             "frontmatter missing name: orchestrator")
        self.assertTrue(self.body.strip(), "markdown body is empty")
        self.assertRegex(self.body, r"(?m)^#\s", "body has no markdown headings")
        fence_lines = re.findall(r"(?m)^```", self.text)
        self.assertEqual(
            len(fence_lines) % 2, 0,
            f"unbalanced ``` code fences (found {len(fence_lines)})",
        )

    # --- (2) Fix 1: feature-review PASS clears blocked:feature-review BEFORE ready-to-merge ---

    def test_feature_review_pass_clears_blocked_before_ready_to_merge(self):
        """(2) Fix 1 / FR-11.1 / FR-10.1: within the Feature Review Gate PASS branch, a
        clear of blocked:feature-review appears and PRECEDES the set of ready-to-merge."""
        # Isolate the Feature Review Gate PASS branch specifically (there is also a Consistency
        # Gate 'On PASS'): anchor on the '(both reviewers PASS)' qualifier, up to its 'On FAIL'.
        region = region_between(
            self.body,
            r"\*\*On PASS \(both reviewers PASS\)",
            r"\*\*On FAIL\b",
        )
        self.assertIsNotNone(region, "could not locate the feature-review 'On PASS' branch region")

        # A clear instruction for blocked:feature-review must exist in the PASS branch.
        clear_m = re.search(
            r"(?is)(op:\s*clear[^}]*blocked:feature-review|clear[^.]*blocked:feature-review)",
            region,
        )
        self.assertIsNotNone(
            clear_m,
            "PASS branch does not clear blocked:feature-review before ready-to-merge",
        )
        # A set of ready-to-merge must exist in the PASS branch.
        set_m = re.search(
            r"(?is)(op:\s*set[^}]*ready-to-merge|set\b[^.]*ready-to-merge)",
            region,
        )
        self.assertIsNotNone(set_m, "PASS branch does not set ready-to-merge")

        # Ordering: the clear must come before the set.
        self.assertLess(
            clear_m.start(), set_m.start(),
            "blocked:feature-review is cleared AFTER ready-to-merge is set — "
            "Fix 1 requires clearing the stale blocked:* label BEFORE applying ready-to-merge",
        )
        # The region should carry the 'before' scoping wording tying the two together.
        self.assertRegex(
            region,
            r"(?is)before\b[^.]*ready-to-merge",
            "PASS branch lacks explicit 'before ... ready-to-merge' ordering language",
        )

    # --- (3) Fix 2: per-task pass clears ALL recorded blocked:* labels ---------

    def test_per_task_pass_clears_all_blocked_labels(self):
        """(3) Fix 2 / FR-9 / FR-11.1: the per-task pass branch clears EVERY recorded blocked:*
        label for the task (all-not-singular), not merely the last stage's label."""
        # Isolate the per-task 'On pass' branch: from 'On **pass**' up to 'On **fail**'.
        region = region_between(
            self.body,
            r"On \*\*pass\*\*",
            r"On \*\*fail\*\*",
        )
        self.assertIsNotNone(region, "could not locate the per-task 'On pass' branch region")

        # All-not-singular wording: clearing every recorded blocked:* label.
        self.assertRegex(
            region,
            r"(?is)(every one of them|clear\s+\*\*every\b|each\b[^.]*blocked:|"
            r"once per (recorded )?label|all\b[^.]*blocked:)",
            "per-task pass branch does not convey clearing EVERY recorded blocked:* label",
        )
        # Explicit disclaimer that it is not merely the last stage's label.
        self.assertRegex(
            region,
            r"(?is)not merely the last stage",
            "per-task pass branch lacks the 'not merely the last stage' all-not-singular clarifier",
        )
        # Enumerates the per-stage blocked:* variants that may need clearing.
        for token in ("blocked:validation", "blocked:code-review", "blocked:security-review"):
            self.assertIn(
                token, region,
                f"per-task pass branch does not enumerate {token} among the labels to clear",
            )
        # No stale blocked:* should be orphaned on the PR after the task passes.
        self.assertRegex(
            region,
            r"(?is)(stale|orphan)",
            "per-task pass branch does not state that no stale/orphaned blocked:* is left behind",
        )
        # It is anchored to FR-11.1 (label-clear) and lives in the FR-9 per-task pass branch.
        self.assertRegex(region, r"FR-11\.1\b", "FR-11.1 not cited in the per-task label-clear")

    # --- (4) Fix 3: scaffold push scoped to new-feature case, no base ---------

    def test_scaffold_push_scoped_to_new_feature_no_base(self):
        """(4) Fix 3 / FR-7 / FR-3.1: the scaffold push is scoped to the NEW-feature case
        ('only on first scaffold' / 'never on resume') and the raw push carries NO base."""
        # Isolate the scaffold-push instruction within the 'On Session Start' new-feature branch:
        # from the FR-7 scaffold marker up to the next numbered top-level step ("3." at line start).
        region = region_between(
            self.body,
            r"GitHub \(scaffold, FR-7\)",
            r"(?m)^\s*3\.",
        )
        self.assertIsNotNone(region, "could not locate the scaffold-push (FR-7) instruction region")

        # New-feature scoping: fires only on first scaffold, never on resume.
        self.assertRegex(
            region,
            r"(?is)(only\b[^.]*first scaffold|first scaffold[^.]*new feature)",
            "scaffold push is not scoped to the first-scaffold / new-feature case",
        )
        self.assertRegex(
            region,
            r"(?is)never\b[^.]*resume",
            "scaffold push does not state it never fires on resume",
        )
        # The push action is present and cites FR-7.
        self.assertRegex(region, r"action:\s*push\b", "scaffold region does not invoke action: push")
        self.assertRegex(region, r"FR-7\b", "FR-7 not cited in the scaffold-push region")

        # The raw scaffold push must NOT carry a base field. The push request object is
        # `{ action: push, feature, branch: ... }` — assert `base` is absent from that object and
        # that the prose explains base does not apply to a raw push.
        push_obj = re.search(r"\{\s*action:\s*push\b[^}]*\}", region, re.IGNORECASE | re.DOTALL)
        self.assertIsNotNone(push_obj, "scaffold push request object not found")
        self.assertNotRegex(
            push_obj.group(0),
            r"(?i)\bbase\b",
            "raw scaffold push request still carries a `base` field — Fix 3 dropped it",
        )
        self.assertRegex(
            region,
            r"(?is)no\s+`?base`?",
            "scaffold region does not explain that no base applies to a raw push",
        )

        # The GitHub Integration table's scaffold row must match: new-feature-only + no base.
        table_row = region_between(
            self.body,
            r"\|\s*\*\*Feature scaffold\*\*",
            r"(?m)^\|",  # up to the next table row
        )
        self.assertIsNotNone(table_row, "scaffold row not found in the GitHub Integration table")
        self.assertRegex(
            table_row,
            r"(?is)new feature only",
            "scaffold table row not scoped to 'new feature only'",
        )
        self.assertRegex(
            table_row,
            r"(?is)no\s+`?base`?",
            "scaffold table row does not state 'no base' for the raw push",
        )

    # --- (5) Invariant preserved: orchestrator never runs gh / git push -------

    def test_orchestrator_never_runs_gh_or_git_push(self):
        """(5) NFR-1 / NFR-4: the file still states the orchestrator never runs gh / git push,
        and github-agent is the sole remote choke-point."""
        # Never-run invariant (mirrors Task-2 lint; must survive the Task-12 edits).
        self.assertRegex(
            self.body,
            r"(?is)(never run[s]?\s+`?gh`?\s*(/|or|and)\s*`?git push`?|"
            r"never\b[^.]*`?git push`?\s+yourself|you never run\s+`?gh`?)",
            "orchestrator no longer states it never runs gh / git push itself",
        )
        self.assertIn("git push", self.body, "'git push' phrase absent")
        # github-agent framed as the single / only choke-point that runs gh or git push.
        self.assertIn("github-agent", self.body, "orchestrator never references github-agent")
        self.assertRegex(
            self.body,
            r"(?is)(only\b[^.]*component[^.]*(gh|git push)|single audited choke-?point|"
            r"only\b[^.]*runs\s+`?gh`?)",
            "github-agent not framed as the sole component that runs gh / git push",
        )

    # --- (6) Consistency: repo copy == reconciled global copy (skips cleanly) --

    def test_repo_and_global_copies_are_byte_identical(self):
        """(6) The repo agents/orchestrator.md and the reconciled global copy are byte-identical.
        If the global copy is unreadable (absent / permission-denied), SKIP cleanly rather than
        fail — the global reconciliation is out-of-band and not always present in every env."""
        if not GLOBAL_ORCH_PATH.exists():
            self.skipTest(f"global orchestrator copy not present at {GLOBAL_ORCH_PATH}")
        try:
            global_bytes = GLOBAL_ORCH_PATH.read_bytes()
        except OSError as exc:
            self.skipTest(f"global orchestrator copy unreadable: {exc}")
        repo_bytes = ORCH_PATH.read_bytes()
        self.assertEqual(
            repo_bytes, global_bytes,
            "repo agents/orchestrator.md and the global copy are NOT byte-identical",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
