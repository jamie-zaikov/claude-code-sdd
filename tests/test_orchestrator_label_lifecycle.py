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

# The reconciled global copy lives outside the worktree; derive it from the invoking user's home so
# the check is portable (FR-11.8). Where the path does not exist — CI, a fresh clone — the existing
# skip fires exactly as it did with the hardcoded absolute path.
GLOBAL_ORCH_PATH = Path.home() / ".claude" / "agents" / "orchestrator.md"


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


# --- Repo-vs-global sync-state discriminator (FR-11.8 carve-out, amendment A2) ----------------
#
# `orchestrator_sync_state` is a deliberate LOCAL COPY of `claude_sync_state` in
# tests/test_docs_updates.py, not an import: FR-11.1 keeps every test module stdlib-only and
# independently runnable, and the carve-out stays confined to the two assertions that need it
# rather than growing a shared importable surface. Same signature, same three states, same order
# of evaluation; only the invariant extractor passed in differs.

ORCH_INVARIANT_PATTERNS = {
    # (a) the `ready-to-merge` single-application-point rule ...
    "ready_to_merge_single_application_point":
        r"This is the \*\*only\*\* place `ready-to-merge` is ever applied[^)]*\)",
    # ... together with the clear-`blocked:*`-before-set ordering.
    "clear_blocked_before_ready_to_merge":
        r"op: clear, name: blocked:feature-review[\s\S]*?alongside a stale `blocked:\*`",
    # (b) the clear-EVERY-recorded-`blocked:*`-label wording.
    "clear_every_recorded_blocked_label":
        r"clear \*\*every one of them\*\*[\s\S]*?not merely the last stage",
    # (c) the scaffold-push-only-on-first-scaffold scoping.
    "scaffold_push_first_scaffold_only":
        r"This fires \*\*only\*\* on first scaffold[^.]*",
    # (d) the "never runs `gh` / `git push` yourself; github-agent is the only component that
    #     does" framing — two spans, because the two halves live in separate paragraphs.
    "orchestrator_never_runs_gh_or_git_push":
        r"\*\*You never run `gh` or `git push` yourself\.\*\*",
    "github_agent_sole_gh_runner":
        r"github-agent is the \*\*only\*\* component in the fleet that runs `gh` or `git push`",
}


def orchestrator_invariant_lines(text):
    """The orchestrator's invariant instruction lines, normalised, as a {key: value} dict.

    These are the invariants FR-11.8 (amendment A2) names as the class of check that must survive
    the byte-identity carve-out. Each pattern is anchored on wording that predates this feature and
    matches exactly one span, so a copy that omits or restates an invariant is detected while new
    content elsewhere — the signature of a pending sync — is ignored by construction.

    Matching runs over the whitespace-normalised whole text rather than per raw line because the
    document is hard-wrapped: two of these invariant sentences straddle a line break, so the line
    is not the meaningful unit. A key whose pattern does not match is simply absent from the dict.
    """
    normalised = re.sub(r"\s+", " ", text)
    out = {}
    for key, pattern in ORCH_INVARIANT_PATTERNS.items():
        m = re.search(pattern, normalised)
        if m:
            out[key] = m.group(0).strip()
    return out


def orchestrator_sync_state(repo_text, global_text, extract_invariants, reasons=None):
    """Classify the repository-copy-vs-global-copy relationship: 'satisfied' | 'pending' | 'drift'.

    Local copy of `claude_sync_state` (tests/test_docs_updates.py) — see the note above.

      * ``'satisfied'`` — the two copies are identical; nothing to decide.
      * ``'pending'``   — they differ only in ways consistent with "the repository copy is ahead
        and ``./install.sh`` has not been run yet", the window NFR-10 declares legitimate.
      * ``'drift'``     — the global copy omits or contradicts an invariant the repository copy
        states, or carries a heading of unknown provenance. NFR-10 calls that a defect.

    ``extract_invariants`` maps a document's full text to a ``{key: normalised value}`` dict;
    ``reasons``, when a list is passed, collects a human-readable explanation of every drift signal
    so the caller can name what diverged. Evaluated in order (design DD-6): equal texts first, then
    (a) an invariant key from the repository copy missing from the global copy or differing after
    normalisation, or (b) an ATX heading (normalised, outside code fences) present in the global
    copy and absent from the repository copy — containment is directional, since repository-only
    headings are the normal signature of a pending sync — and 'pending' otherwise.
    """
    if reasons is None:
        reasons = []

    if repo_text == global_text:
        return "satisfied"

    def normalised_headings(text):
        """Normalised ATX heading texts, in document order, ignoring fenced code blocks."""
        found = []
        in_fence = False
        for ln in text.splitlines():
            if ln.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = re.match(r"^#+\s+(.*?)\s*#*\s*$", ln)
            if not m:
                continue
            heading = re.sub(r"\s+", " ", re.sub(r"[`*_]", "", m.group(1))).strip().lower()
            if heading and heading not in found:
                found.append(heading)
        return found

    # (a) invariant divergence — the repository copy is authoritative, so every invariant it
    #     carries must be carried identically by the global copy.
    repo_invariants = extract_invariants(repo_text)
    global_invariants = extract_invariants(global_text)
    for key in sorted(repo_invariants):
        if key not in global_invariants:
            reasons.append(
                f"invariant `{key}` is missing from the global copy\n"
                f"    repo:   {repo_invariants[key]}"
            )
        elif global_invariants[key] != repo_invariants[key]:
            reasons.append(
                f"invariant `{key}` is stated differently in the global copy\n"
                f"    repo:   {repo_invariants[key]}\n"
                f"    global: {global_invariants[key]}"
            )

    # (b) heading provenance — a heading only the global copy has is not a "behind" state.
    repo_headings = set(normalised_headings(repo_text))
    for heading in normalised_headings(global_text):
        if heading not in repo_headings:
            reasons.append(
                f"heading '{heading}' exists only in the global copy — content of unknown "
                f"provenance that running ./install.sh would not explain"
            )

    return "drift" if reasons else "pending"


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
        """(6) Repo-vs-global sync, relaxed to satisfied-or-pending — carve-out (FR-11.8, NFR-10).

        This assertion used to demand raw byte-identity between agents/orchestrator.md and the
        global copy. FR-11.8 (amendment A2) deliberately relaxes it, and NFR-10 says why: the
        **repository copy is authoritative** and the `~/.claude` copy is a **derived install
        artifact**, brought into sync by the operator running `./install.sh` *after merge*. While
        the repository copy has moved ahead and the installer has not run, the difference is a
        legitimate **pending-sync window**, not a defect — and it must never be "fixed" by writing
        to `~/.claude/`, which no pipeline stage is permitted to do. Running the installer
        mid-feature is not an acceptable resolution either.

        What is emphatically **not** relaxed is genuine drift. The discriminator is a real content
        comparison — never a blanket skip taken whenever the two copies differ — over the
        orchestrator's invariant instruction lines: the `ready-to-merge` single-application-point
        rule with its clear-`blocked:*`-before-set ordering, the clear-EVERY-recorded-label
        wording, the scaffold-push-only-on-first-scaffold scoping, and the never-runs-`gh`/`git
        push` framing. A readable global copy that omits or restates any one of them still FAILs,
        and the message names it. This is one of exactly two assertions in the suite carrying this
        carve-out (the other is `test_two_claude_files_byte_identical` in
        tests/test_docs_updates.py, amendment A1); a third requires a fresh amendment.

        The invariant set is anchored on wording that predates the non-code-feature-track change,
        never on prose it adds: new content in the repository copy is the definition of "pending",
        so keying on it would make every pending window read as drift and invert the amendment.

        If the global copy is unreadable (absent / permission-denied), SKIP cleanly rather than
        fail — the global reconciliation is out-of-band and not always present in every env.
        """
        if not GLOBAL_ORCH_PATH.exists():
            self.skipTest(f"global orchestrator copy not present at {GLOBAL_ORCH_PATH}")
        try:
            global_text = GLOBAL_ORCH_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            self.skipTest(f"global orchestrator copy unreadable: {exc}")
        repo_text = ORCH_PATH.read_text(encoding="utf-8")

        # Guard: the discriminator is only as strong as its anchors, so fail loudly rather than
        # silently comparing nothing if the repository copy no longer carries an invariant span.
        extracted = orchestrator_invariant_lines(repo_text)
        missing = sorted(set(ORCH_INVARIANT_PATTERNS) - set(extracted))
        self.assertEqual(
            missing, [],
            f"the repo agents/orchestrator.md no longer matches these invariant patterns: {missing} "
            f"— the drift discriminator would go blind; re-anchor the pattern or restore the invariant",
        )

        reasons = []
        state = orchestrator_sync_state(
            repo_text, global_text, orchestrator_invariant_lines, reasons,
        )
        self.assertNotEqual(
            state, "drift",
            "repo agents/orchestrator.md and the global copy have genuinely DRIFTED — this is not a "
            "pending sync:\n  - "
            + "\n  - ".join(reasons)
            + "\nThe repository copy is authoritative (NFR-10); resolve by running ./install.sh "
              "after merge, never by hand-editing ~/.claude/agents/orchestrator.md.",
        )
        self.assertIn(
            state, {"satisfied", "pending"},
            f"unhandled orchestrator sync state {state!r} — the discriminator must return "
            f"'satisfied', 'pending' or 'drift'",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
