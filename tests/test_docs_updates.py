#!/usr/bin/env python3
"""Structural + cross-file consistency lint for the Task 10 documentation updates (sub-task 10.4).

These are markdown docs, not code, so the "test" is a structure + content + consistency check:

  * both CLAUDE.md files (repo-root, resolved relative to this test so it survives consolidation,
    and the GLOBAL ~/.claude/CLAUDE.md read at its absolute path) and README.md are valid markdown;
  * the github-agent ownership bullet, the "only component that runs gh/git push" line, and the
    "No agent modifies another agent's artifact" invariant appear in BOTH CLAUDE.md files;
  * the two CLAUDE.md Agent-Ownership sections are consistent with each other;
  * the README subsection covers the agent, the three CI gates, the pre-push hook, the human merge
    gate, and the ready-to-merge / blocked: label semantics, and the counts / tree entries were
    updated;
  * prose is English (light ASCII/token check).

Covers FR-23, FR-23.1, FR-24, NFR-3, NFR-4, NFR-7.

Stdlib-only. Run:
    python3 -m unittest tests.test_docs_updates -v
    # or
    python3 tests/test_docs_updates.py
"""

import re
import unittest
from pathlib import Path

# Repo-root docs resolve relative to this test:
#   <root>/tests/test_docs_updates.py -> <root>/CLAUDE.md, <root>/README.md
ROOT = Path(__file__).resolve().parent.parent
REPO_CLAUDE = ROOT / "CLAUDE.md"
README = ROOT / "README.md"

# The GLOBAL CLAUDE.md lives outside the worktree; derive it from the invoking user's home so the
# check is portable (FR-11.8). Where the path does not exist — CI, a fresh clone — the existing
# skips fire exactly as they did with the hardcoded absolute path.
GLOBAL_CLAUDE = Path.home() / ".claude" / "CLAUDE.md"


# --- Markdown structural helpers -------------------------------------------


def code_fences_balanced(text):
    """A markdown doc has balanced ``` fences iff the count of fence lines is even."""
    fence_lines = [ln for ln in text.splitlines() if ln.lstrip().startswith("```")]
    return len(fence_lines) % 2 == 0


def headings_well_formed(text):
    """Every ATX heading line outside code fences has a space after the leading #'s.

    Returns a list of offending lines (empty == well-formed).
    """
    offenders = []
    in_fence = False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#+)(.*)$", ln)
        if m and m.group(2) and not m.group(2).startswith(" "):
            offenders.append(ln)
    return offenders


def extract_section(text, heading_regex):
    """Return the body of the section whose heading matches heading_regex (a `### ...` block).

    Captures from the matched heading up to (but not including) the next heading of the same or
    higher level, or EOF.
    """
    lines = text.splitlines()
    start = None
    start_level = None
    for i, ln in enumerate(lines):
        hm = re.match(r"^(#+)\s+(.*)$", ln)
        if hm and re.search(heading_regex, hm.group(2), re.IGNORECASE):
            start = i
            start_level = len(hm.group(1))
            break
    if start is None:
        return None
    body = []
    for ln in lines[start + 1:]:
        hm = re.match(r"^(#+)\s+", ln)
        if hm and len(hm.group(1)) <= start_level:
            break
        body.append(ln)
    return "\n".join(body)


def github_agent_lines(section):
    """The consistency-relevant lines from an Agent-Ownership section.

    Returns the github-agent bullet, the gh/git-push line, and the invariant line, normalised
    (whitespace-collapsed) so wording — not incidental spacing — is compared.
    """
    out = {}
    for ln in section.splitlines():
        norm = re.sub(r"\s+", " ", ln).strip()
        if not norm:
            continue
        if norm.lower().startswith("- github-agent"):
            out["bullet"] = norm
        elif "only component that runs" in norm.lower() and ("gh" in norm or "git push" in norm):
            out["gh_line"] = norm
        elif "no agent modifies another agent" in norm.lower():
            out["invariant"] = norm
    return out


def claude_sync_state(repo_text, global_text, extract_invariants, reasons=None):
    """Classify the repository-copy-vs-global-copy relationship of a synced document.

    Returns exactly one of:

      * ``'satisfied'`` — the two copies are identical; nothing to decide.
      * ``'pending'``   — they differ, but only in ways consistent with "the repository copy is
        ahead and ``./install.sh`` has not been run yet". NFR-10 declares that window legitimate.
      * ``'drift'``     — the global copy omits or contradicts something the repository copy
        states, or carries structural content of unknown provenance. NFR-10 calls that a defect.

    ``extract_invariants`` is a callable mapping a document's full text to a
    ``{key: normalised line}`` dict of the invariant lines that must survive the pending-sync
    window. It is a parameter rather than a hardcoded call so that the same state machine serves
    both live-global assertions the FR-11.8 carve-out covers, each with its own invariant set.

    ``reasons``, when a list is passed, collects a human-readable explanation of every drift signal
    found, so the caller can name the diverging invariant key or the global-only heading in its
    failure message rather than reporting a bare "not byte-identical".

    Evaluated in order (design DD-6):

      1. the texts are equal                                          -> ``'satisfied'``
      2. drift, when **either**
         (a) an invariant key extracted from the repository copy is missing from the global copy
             or differs after normalisation, **or**
         (b) an ATX heading (normalised, outside code fences) present in the global copy is absent
             from the repository copy. Containment is deliberately directional: headings that
             exist only in the *repository* copy are the normal signature of a pending sync, while
             a heading only the *global* copy carries is content the installer did not put there.
                                                                      -> ``'drift'``
      3. otherwise                                                    -> ``'pending'``
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


class DocsMarkdownStructureTest(unittest.TestCase):
    """Group 1 — all three files are valid markdown."""

    @classmethod
    def setUpClass(cls):
        cls.repo_claude = REPO_CLAUDE.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")

    def test_repo_claude_exists_and_readable(self):
        self.assertTrue(REPO_CLAUDE.exists(), f"repo-root CLAUDE.md not found at {REPO_CLAUDE}")
        self.assertTrue(self.repo_claude.strip(), "repo-root CLAUDE.md is empty")

    def test_readme_exists_and_readable(self):
        self.assertTrue(README.exists(), f"README.md not found at {README}")
        self.assertTrue(self.readme.strip(), "README.md is empty")

    def test_repo_claude_code_fences_balanced(self):
        self.assertTrue(code_fences_balanced(self.repo_claude), "repo CLAUDE.md has unbalanced ``` fences")

    def test_readme_code_fences_balanced(self):
        self.assertTrue(code_fences_balanced(self.readme), "README.md has unbalanced ``` fences")

    def test_repo_claude_headings_well_formed(self):
        bad = headings_well_formed(self.repo_claude)
        self.assertEqual(bad, [], f"repo CLAUDE.md has malformed headings: {bad}")

    def test_readme_headings_well_formed(self):
        bad = headings_well_formed(self.readme)
        self.assertEqual(bad, [], f"README.md has malformed headings: {bad}")

    def test_docs_have_no_frontmatter(self):
        """These docs are plain markdown (no --- frontmatter); if any is added it must be intact."""
        for name, text in (("repo CLAUDE.md", self.repo_claude), ("README.md", self.readme)):
            if text.startswith("---"):
                # If frontmatter is present, it must have a closing fence.
                self.assertRegex(
                    text, r"^---[ \t]*\n.*?\n---[ \t]*\n", f"{name} opens with --- but frontmatter is not closed"
                )
            else:
                # Otherwise it should open with a top-level heading.
                self.assertTrue(text.lstrip().startswith("#"), f"{name} does not open with a heading")


class ClaudeOwnershipContentTest(unittest.TestCase):
    """Group 2/3 — required lines present in BOTH CLAUDE.md files, and consistent (FR-23, FR-23.1, NFR-4)."""

    @classmethod
    def setUpClass(cls):
        cls.repo_text = REPO_CLAUDE.read_text(encoding="utf-8")
        cls.repo_section = extract_section(cls.repo_text, r"Agent Ownership")
        cls.global_available = False
        cls.global_text = None
        cls.global_section = None
        try:
            cls.global_text = GLOBAL_CLAUDE.read_text(encoding="utf-8")
            cls.global_available = True
            cls.global_section = extract_section(cls.global_text, r"Agent Ownership")
        except OSError:
            cls.global_available = False

    def test_repo_has_agent_ownership_section(self):
        self.assertIsNotNone(self.repo_section, "repo CLAUDE.md missing an Agent Ownership section")

    def test_repo_github_agent_bullet_present(self):
        """FR-23: github-agent ownership bullet in repo CLAUDE.md, framed as choke-point scribe that never merges."""
        self.assertIsNotNone(self.repo_section)
        lines = github_agent_lines(self.repo_section)
        self.assertIn("bullet", lines, "repo CLAUDE.md Agent Ownership missing a `- github-agent` bullet")
        bullet = lines["bullet"].lower()
        self.assertIn("choke-point", bullet, "github-agent bullet should describe the choke-point role")
        self.assertIn("never merges", bullet, "github-agent bullet should state it never merges")

    def test_repo_gh_git_push_line_present(self):
        """FR-23.1: the only-component-that-runs-gh/git-push line in repo CLAUDE.md."""
        self.assertIsNotNone(self.repo_section)
        lines = github_agent_lines(self.repo_section)
        self.assertIn("gh_line", lines, "repo CLAUDE.md missing the 'only component that runs gh/git push' line")

    def test_repo_invariant_preserved(self):
        """NFR-4: the 'No agent modifies another agent's artifact' invariant preserved in repo CLAUDE.md."""
        self.assertIsNotNone(self.repo_section)
        lines = github_agent_lines(self.repo_section)
        self.assertIn("invariant", lines, "repo CLAUDE.md dropped the 'No agent modifies another agent's artifact' invariant")

    def test_global_claude_available_or_skip(self):
        """FR-23: the GLOBAL CLAUDE.md is readable at its absolute path (informational)."""
        if not self.global_available:
            self.skipTest(f"global CLAUDE.md not readable at {GLOBAL_CLAUDE}; cross-file check skipped")
        self.assertTrue(self.global_text.strip(), "global CLAUDE.md is empty")

    def test_global_required_lines_present(self):
        """FR-23/FR-23.1/NFR-4: bullet + gh/git-push line + invariant present in the GLOBAL CLAUDE.md."""
        if not self.global_available:
            self.skipTest(f"global CLAUDE.md not readable at {GLOBAL_CLAUDE}; cross-file check skipped")
        self.assertIsNotNone(self.global_section, "global CLAUDE.md missing an Agent Ownership section")
        lines = github_agent_lines(self.global_section)
        self.assertIn("bullet", lines, "global CLAUDE.md missing the `- github-agent` bullet")
        self.assertIn("gh_line", lines, "global CLAUDE.md missing the 'only component that runs gh/git push' line")
        self.assertIn("invariant", lines, "global CLAUDE.md dropped the invariant line")

    def test_two_claude_ownership_lines_consistent(self):
        """FR-23/NFR-4: the github-agent bullet, gh/git-push line, and invariant match across both files."""
        if not self.global_available:
            self.skipTest(f"global CLAUDE.md not readable at {GLOBAL_CLAUDE}; cross-file consistency skipped")
        repo_lines = github_agent_lines(self.repo_section)
        global_lines = github_agent_lines(self.global_section)
        for key in ("bullet", "gh_line", "invariant"):
            self.assertIn(key, repo_lines, f"repo CLAUDE.md missing `{key}`")
            self.assertIn(key, global_lines, f"global CLAUDE.md missing `{key}`")
            self.assertEqual(
                repo_lines[key], global_lines[key],
                f"CLAUDE.md `{key}` differs between repo-root and global:\n"
                f"  repo:   {repo_lines[key]}\n  global: {global_lines[key]}",
            )

    def test_two_claude_files_byte_identical(self):
        """Sync convention, relaxed to satisfied-or-pending — deliberate carve-out (FR-11.8, NFR-10).

        This assertion used to demand raw byte-identity between the two CLAUDE.md files. FR-11.8
        (amendment A1) deliberately relaxes it, and NFR-10 says why: the **repository copy is
        authoritative** and the `~/.claude` copy is a **derived install artifact**, brought into
        sync by the operator running `./install.sh` *after merge*. While the repository copy has
        moved ahead and the installer has not run, the difference is a legitimate **pending-sync
        window**, not a defect — and it must never be "fixed" by writing to `~/.claude/`, which no
        pipeline stage is permitted to do. Running the installer mid-feature is not an acceptable
        resolution either.

        What is emphatically **not** relaxed is genuine drift: a global copy that omits an
        Agent-Ownership invariant the repository copy carries, states one differently, or carries a
        heading of unknown provenance still FAILs, and the message names what diverged. This is one
        of exactly two assertions in the suite carrying this carve-out (the other is
        `test_repo_and_global_copies_are_byte_identical` in tests/test_orchestrator_label_lifecycle.py,
        amendment A2); a third requires a fresh amendment, not an extension by analogy.

        The invariant set stays the three Agent-Ownership lines `test_two_claude_ownership_lines_consistent`
        already enforces above, and is deliberately *not* extended with new prose (DD-7): new content
        in the repository copy is the very definition of "pending", so promoting it to an invariant
        would make every pending window read as drift and invert the amendment.
        """
        if not self.global_available:
            self.skipTest(f"global CLAUDE.md not readable at {GLOBAL_CLAUDE}; byte-identity skipped")
        reasons = []
        state = claude_sync_state(
            self.repo_text,
            self.global_text,
            lambda text: github_agent_lines(extract_section(text, r"Agent Ownership") or ""),
            reasons,
        )
        self.assertNotEqual(
            state, "drift",
            "repo-root and global CLAUDE.md have genuinely DRIFTED — this is not a pending sync:\n  - "
            + "\n  - ".join(reasons)
            + "\nThe repository copy is authoritative (NFR-10); resolve by running ./install.sh "
              "after merge, never by hand-editing ~/.claude/CLAUDE.md.",
        )
        self.assertIn(
            state, {"satisfied", "pending"},
            f"unhandled CLAUDE.md sync state {state!r} — the discriminator must return "
            f"'satisfied', 'pending' or 'drift'",
        )


class ReadmeContentTest(unittest.TestCase):
    """Group 4/5 — README covers the agent + CI layer, updated counts/tree (FR-24, NFR-3, NFR-7)."""

    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def test_github_agent_md_listed(self):
        """FR-24: github-agent.md appears in the README."""
        self.assertIn("github-agent.md", self.text, "README does not list github-agent.md")

    def test_agent_count_bumped(self):
        """FR-24/NFR-3: agent count bumped to 13; no stale '12 agents' remains."""
        self.assertNotRegex(self.text, r"\b12\s+agents\b", "README still says '12 agents'")
        self.assertRegex(self.text, r"\b13\s+agents\b", "README does not state '13 agents'")

    def test_ci_templates_tree_entry(self):
        """FR-24: ci-templates/ appears in the 'What's Included' tree."""
        self.assertIn("ci-templates/", self.text, "README missing ci-templates/ tree entry")

    def test_three_gates_named(self):
        """FR-24/NFR-3: each of the three CI workflow gates is named."""
        for gate in ("sdd-secret-scan", "sdd-review-gate", "sdd-build-test-lint"):
            self.assertIn(gate, self.text, f"README does not mention the {gate} gate")

    def test_pre_push_hook_covered(self):
        """FR-24/NFR-3: the pre-push hook is described."""
        self.assertRegex(self.text, r"pre-push", "README does not mention the pre-push hook")

    def test_human_merge_gate_covered(self):
        """FR-24/NFR-1: the human merge gate is described."""
        low = self.text.lower()
        self.assertIn("human", low, "README does not describe the human merge gate")
        self.assertIn("merge", low, "README does not describe the merge gate")
        self.assertTrue(
            "never merges" in low or "no agent merges" in low,
            "README should state that no agent merges",
        )

    def test_label_semantics_covered(self):
        """FR-24: ready-to-merge and blocked: label semantics are described."""
        self.assertIn("ready-to-merge", self.text, "README missing the ready-to-merge label")
        self.assertRegex(self.text, r"blocked:", "README missing the blocked:* label semantics")

    def test_ci_mirrors_never_replaces(self):
        """NFR-3: README states CI mirrors — never replaces — the local gates."""
        low = self.text.lower()
        self.assertTrue(
            "mirrors" in low and "never replaces" in low,
            "README does not state that CI mirrors — never replaces — the local gates",
        )

    def test_review_gate_required_check_and_branch_protection(self):
        """FR-24/NFR-3: README ties sdd-review-gate to a required check + branch protection."""
        low = self.text.lower()
        self.assertIn("branch protection", low, "README does not mention branch protection")
        self.assertTrue(
            "required" in low and "sdd-review-gate" in self.text,
            "README does not describe sdd-review-gate as a required check",
        )

    def test_allowlist_pragma_mentioned(self):
        """FR-24: README documents the `pragma: allowlist secret` suppression."""
        self.assertIn("pragma: allowlist secret", self.text, "README missing the allowlist pragma")

    def test_sdd_init_distribution_and_dogfood(self):
        """FR-24: README covers /sdd-init distribution and the this-repo dogfood."""
        low = self.text.lower()
        self.assertIn("/sdd-init", self.text, "README does not mention /sdd-init distribution")
        self.assertIn("dogfood", low, "README does not mention the this-repo dogfood")

    def test_prose_is_english_ascii(self):
        """NFR-7: prose is English — the required tokens are present and the doc is ASCII-clean.

        Light check: allow the handful of non-ASCII punctuation the docs use intentionally
        (em dash, en dash, smart quotes, arrows, box-drawing for trees) but assert the doc is not
        otherwise dominated by non-Latin script.
        """
        allowed_non_ascii = set("—–‘’“”→←↔│├└─•")
        stray = [ch for ch in self.text if ord(ch) > 127 and ch not in allowed_non_ascii]
        self.assertEqual(
            stray[:20], [], f"README contains unexpected non-ASCII (non-English?) characters: {stray[:20]}"
        )
        # And the required English tokens are present.
        for token in ("GitHub", "audited", "choke-point", "label"):
            self.assertIn(token, self.text, f"README missing expected English token '{token}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
