#!/usr/bin/env python3
"""Structural lint for the orchestrator's local-first GitHub flow.

agents/orchestrator.md is a markdown/config artifact — an agent-instruction doc, not executable
code — so this "test" is a structure/ordering lint over the markdown text. It asserts the
local-first invariants (the build runs locally; the remote is touched exactly once, at publish):

  (2) Feature Review Gate PASS is the single PUBLISH point: push -> open ready PR -> comment
      verdicts -> set `ready-to-merge` -> request review, in that order.
  (3) A per-task pass is a LOCAL commit only — no push, and no label op (there is no PR yet).
  (4) The feature scaffold does NOT push — the branch stays local until publish.
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

    # --- (2) Feature Review Gate PASS is the single publish point --------------

    def test_feature_review_pass_is_the_publish_point(self):
        """(2) Local-first: within the Feature Review Gate PASS branch, the publish sequence runs
        in order — push, then open the ready PR, then comment verdicts, then set ready-to-merge,
        then request review."""
        region = region_between(
            self.body,
            r"\*\*On PASS \(both reviewers PASS\)",
            r"\*\*On FAIL\b",
        )
        self.assertIsNotNone(region, "could not locate the feature-review 'On PASS' branch region")

        # It must be named the single publish point.
        self.assertRegex(
            region, r"(?is)single publish point",
            "the feature-review PASS branch is not framed as the single publish point",
        )
        # Ordered publish sequence: push -> open-pr -> comment -> ready-to-merge -> request-review.
        push_m = re.search(r"(?is)action:\s*push\b", region)
        openpr_m = re.search(r"(?is)action:\s*open-pr\b", region)
        rtm_m = re.search(r"(?is)(op:\s*set[^}]*ready-to-merge|set[^.]*ready-to-merge)", region)
        review_m = re.search(r"(?is)action:\s*request-review\b", region)
        for m, name in ((push_m, "push"), (openpr_m, "open-pr"), (rtm_m, "ready-to-merge"),
                        (review_m, "request-review")):
            self.assertIsNotNone(m, f"publish sequence missing the {name} step")
        self.assertLess(push_m.start(), openpr_m.start(), "push must precede open-pr")
        self.assertLess(openpr_m.start(), rtm_m.start(), "open-pr must precede ready-to-merge")
        self.assertLess(rtm_m.start(), review_m.start(), "ready-to-merge must precede request-review")
        # The PR is opened ready, not draft.
        self.assertRegex(
            region, r"(?is)draft:\s*false",
            "the published PR is not opened ready (draft: false)",
        )

    # --- (3) A per-task pass is a LOCAL commit only, no label op ---------------

    def test_per_task_pass_is_local_commit_no_label_op(self):
        """(3) Local-first: the per-task pass branch makes a LOCAL commit (action: commit) and
        performs no label op — there is no PR during the build, so nothing to label."""
        region = region_between(
            self.body,
            r"On \*\*pass\*\*",
            r"On \*\*fail\*\*",
        )
        self.assertIsNotNone(region, "could not locate the per-task 'On pass' branch region")

        # Local commit only, carrying the SDD-Task:<N> trailer.
        self.assertRegex(region, r"(?is)action:\s*commit\b", "per-task pass does not use action: commit")
        self.assertRegex(region, r"(?is)local commit only", "per-task pass is not a local commit only")
        self.assertRegex(region, r"SDD-Task:\s*<N>", "per-task commit lacks the SDD-Task:<N> trailer")
        # No label op in the per-task pass branch (no ready-to-merge, no blocked:* set/clear).
        self.assertNotRegex(
            region, r"(?is)action:\s*label\b",
            "per-task pass still performs a label op — local-first has no PR to label during the build",
        )
        self.assertNotIn(
            "ready-to-merge", region,
            "ready-to-merge appears in the per-task pass branch — it belongs only at the publish point",
        )
        # Verdicts are recorded locally rather than posted as a PR comment.
        self.assertRegex(
            region, r"(?is)spec-memory",
            "per-task pass does not record verdicts locally in spec-memory",
        )

    # --- (4) The scaffold does NOT push — the branch stays local --------------

    def test_scaffold_does_not_push_branch_stays_local(self):
        """(4) Local-first: the 'On Session Start' new-feature path does NOT push the branch; it
        stays local until the publish point."""
        # Isolate the On Session Start section (up to the Phase Routing heading).
        region = region_between(
            self.body,
            r"(?mi)^##\s+On Session Start",
            r"(?mi)^##\s+Phase Routing",
        )
        self.assertIsNotNone(region, "could not locate the On Session Start section")
        self.assertRegex(
            region, r"(?is)not pushed",
            "On Session Start does not state the scaffolded branch is not pushed",
        )
        self.assertRegex(
            region, r"(?is)(stays local|local through the whole build)",
            "On Session Start does not state the branch stays local",
        )
        # The GitHub Integration table's scaffold row must record no push action.
        table_row = region_between(
            self.body,
            r"\|\s*\*\*Feature scaffold\*\*",
            r"(?m)^\|",  # up to the next table row
        )
        self.assertIsNotNone(table_row, "scaffold row not found in the GitHub Integration table")
        self.assertRegex(
            table_row,
            r"(?is)(none|stays local|nothing is pushed)",
            "scaffold table row does not record 'no push' for local-first",
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
