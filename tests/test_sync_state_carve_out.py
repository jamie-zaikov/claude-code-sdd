#!/usr/bin/env python3
"""Behavioural tests for the FR-11.8 byte-identity carve-out (Task 1, sub-task 1.7).

Task 1 relaxed the only two live-global byte-identity assertions in the suite —
`test_two_claude_files_byte_identical` (tests/test_docs_updates.py, amendment A1) and
`test_repo_and_global_copies_are_byte_identical` (tests/test_orchestrator_label_lifecycle.py,
amendment A2) — from pass-or-fail byte-identity to a three-state discriminator:
`satisfied` / `pending` / `drift`.

The whole point of the amendment is that the relaxed assertions STILL FAIL on genuine drift
(FR-11.8, NFR-10, AC-8, AC-10). A carve-out that only proved `pending` works would be exactly the
regression FR-11.8 forbids, so this module exercises the discriminator directly against in-test
fixture strings and drives both reworked assertions end-to-end over a fixture "global copy" that
never touches the filesystem:

  * all three states, for both copies of the state machine;
  * genuine drift — a global copy that OMITS an invariant, one that RESTATES/CONTRADICTS it, and
    one carrying a heading of unknown provenance — still classifies as `drift` and still makes the
    reworked assertion FAIL, with the diverging key named;
  * directionality — repository-only headings are `pending`, global-only headings are `drift`;
  * fence-awareness of heading extraction;
  * the invariant extractors are non-vacuous against the real repository files (an extractor that
    silently matched nothing would make the surviving check meaningless — NFR-6);
  * both reworked assertions kept their original names, their skip behaviour, and their
    FR-11.8/NFR-10 rationale docstrings, and no other assertion in either module was removed;
  * NFR-10 negative: running them writes nothing anywhere under `~/.claude/`.

Nothing here writes to `~/.claude/`, and nothing here writes outside the repository at all: every
fixture is an in-test string and every "global copy" is an in-memory stand-in.

Covers FR-11, FR-11.1, FR-11.8, NFR-6, NFR-10 (AC-8, AC-10).

Stdlib-only. Run:
    python3 -m unittest tests.test_sync_state_carve_out -v
    # or
    python3 tests/test_sync_state_carve_out.py
"""

import contextlib
import importlib.util
import re
import unittest
from pathlib import Path
from unittest import mock

# Paths resolve relative to this test file, so the module runs wherever the repo's hooks run
# (FR-11.1): <root>/tests/test_sync_state_carve_out.py -> <root>/...
ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
REPO_CLAUDE = ROOT / "CLAUDE.md"
REPO_ORCH = ROOT / "agents" / "orchestrator.md"

DOCS_MODULE_PATH = TESTS / "test_docs_updates.py"
ORCH_MODULE_PATH = TESTS / "test_orchestrator_label_lifecycle.py"

# The install surface under ~/.claude that `./install.sh` writes and that NFR-10 forbids the
# pipeline from touching. Only names, sizes and mtimes are ever inspected — never contents.
CLAUDE_HOME = Path.home() / ".claude"
INSTALL_SURFACE = ("CLAUDE.md", "settings.json", "agents", "commands", "hooks", "ci-templates")


def _load_test_module(alias, path):
    """Import a sibling test module by file path (runner-independent, no sys.path assumptions)."""
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docs = _load_test_module("_carveout_docs_updates", DOCS_MODULE_PATH)
orch = _load_test_module("_carveout_orch_label_lifecycle", ORCH_MODULE_PATH)


def claude_invariants(text):
    """The extractor the reworked CLAUDE.md assertion passes to the discriminator."""
    return docs.github_agent_lines(docs.extract_section(text, r"Agent Ownership") or "")


# --- In-test fixture documents (no files are created anywhere) ---------------------------------

REPO_DOC = """# CLAUDE.md — Spec-Driven Development

## Agent Ownership

- orchestrator: coordinates lifecycle, never writes content or code
- github-agent: the audited remote choke-point scribe — never merges, never authors content

github-agent is the only component that runs `gh` or `git push`.
No agent modifies another agent's artifact.

## Phase Gates

Requirements -> Design -> Tasks -> Implementation -> Complete.
"""

# The legitimate pending-sync window: the repository copy has grown a new section that
# `./install.sh` has not yet carried into the global copy (NFR-10).
REPO_AHEAD_DOC = REPO_DOC + """
## Feature Classification

The orchestrator records `featureClass` as `"code"` or `"non-code"`.
"""

# Genuine drift (a) — the global copy OMITS an Agent-Ownership invariant the repo copy carries.
GLOBAL_MISSING_INVARIANT = REPO_DOC.replace(
    "No agent modifies another agent's artifact.\n", ""
)

# Genuine drift (a) — the global copy RESTATES/CONTRADICTS an invariant the repo copy carries.
GLOBAL_RESTATED_INVARIANT = REPO_DOC.replace(
    "No agent modifies another agent's artifact.",
    "No agent modifies another agent's artifact, except the orchestrator.",
)

# Genuine drift (a) — the gh/git-push line is watered down in the global copy.
GLOBAL_RESTATED_GH_LINE = REPO_DOC.replace(
    "github-agent is the only component that runs `gh` or `git push`.",
    "github-agent is the only component that runs `gh`, though agents may `git push` directly.",
)

# Genuine drift (b) — the global copy carries a heading of unknown provenance.
GLOBAL_EXTRA_HEADING = REPO_DOC + """
## Local Hand Edit

Someone edited ~/.claude/CLAUDE.md directly.
"""

# Not drift — the `#` line lives inside a fenced code block, so it is not a heading.
GLOBAL_FENCED_HASH = REPO_DOC + """
Example transcript:

```text
# Local Hand Edit
```
"""

# Not drift — the same heading, differing only in inline formatting / case / trailing hashes.
GLOBAL_HEADING_FORMATTING_ONLY = (
    REPO_DOC.replace("## Phase Gates", "## `PHASE GATES` ##") + "\nA trailing note.\n"
)

# Drift — the repository copy mentions the heading only inside a fence, so the global copy's real
# heading is still of unknown provenance (fence-awareness must apply to both sides).
REPO_FENCED_HEADING = REPO_DOC + """
```text
## Local Hand Edit
```
"""


class ClaudeSyncStateThreeStatesTest(unittest.TestCase):
    """FR-11.8 / NFR-10 / DD-6: the CLAUDE.md discriminator returns the right state per fixture."""

    def state(self, repo_text, global_text, reasons=None):
        return docs.claude_sync_state(repo_text, global_text, claude_invariants, reasons)

    # --- satisfied -----------------------------------------------------------

    def test_equal_texts_are_satisfied(self):
        """FR-11.8: identical copies -> 'satisfied'; nothing to decide."""
        self.assertEqual(self.state(REPO_DOC, REPO_DOC), "satisfied")

    def test_satisfied_records_no_reasons(self):
        reasons = []
        self.assertEqual(self.state(REPO_DOC, REPO_DOC, reasons), "satisfied")
        self.assertEqual(reasons, [])

    def test_two_empty_documents_are_satisfied(self):
        """Edge case: equality short-circuits before any extraction, so empty==empty is benign."""
        self.assertEqual(self.state("", ""), "satisfied")

    # --- pending -------------------------------------------------------------

    def test_repo_copy_with_added_section_is_pending(self):
        """NFR-10: repository ahead + installer not yet run is a legitimate pending-sync window."""
        self.assertEqual(self.state(REPO_AHEAD_DOC, REPO_DOC), "pending")

    def test_pending_records_no_reasons(self):
        reasons = []
        self.assertEqual(self.state(REPO_AHEAD_DOC, REPO_DOC, reasons), "pending")
        self.assertEqual(reasons, [])

    def test_repo_only_headings_are_not_drift(self):
        """Directionality: a heading only the REPOSITORY copy has is the signature of a pending sync."""
        repo = REPO_DOC + "\n## Brand New Section\n\nAdded by this feature.\n"
        self.assertEqual(self.state(repo, REPO_DOC), "pending")

    def test_heading_formatting_and_case_differences_are_not_drift(self):
        """Heading comparison is normalised (case, backticks, trailing #), so formatting is tolerated."""
        self.assertEqual(self.state(REPO_DOC, GLOBAL_HEADING_FORMATTING_ONLY), "pending")

    # --- drift ---------------------------------------------------------------

    def test_global_copy_missing_an_invariant_is_drift(self):
        """FR-11.8/NFR-10: a global copy OMITTING an Agent-Ownership invariant is genuine drift."""
        reasons = []
        self.assertEqual(self.state(REPO_DOC, GLOBAL_MISSING_INVARIANT, reasons), "drift")
        self.assertTrue(
            any("invariant" in r and "missing" in r for r in reasons),
            f"drift reasons do not name the missing invariant key: {reasons}",
        )

    def test_global_copy_restating_an_invariant_is_drift(self):
        """FR-11.8/NFR-10: a global copy STATING an invariant differently is genuine drift."""
        reasons = []
        self.assertEqual(self.state(REPO_DOC, GLOBAL_RESTATED_INVARIANT, reasons), "drift")
        self.assertTrue(
            any("stated differently" in r for r in reasons),
            f"drift reasons do not report the contradicted invariant: {reasons}",
        )
        self.assertTrue(
            any("except the orchestrator" in r for r in reasons),
            f"drift reasons do not quote the diverging global value: {reasons}",
        )

    def test_global_copy_contradicting_the_gh_push_line_is_drift(self):
        reasons = []
        self.assertEqual(self.state(REPO_DOC, GLOBAL_RESTATED_GH_LINE, reasons), "drift")
        self.assertTrue(
            any("gh_line" in r for r in reasons),
            f"drift reasons do not name the gh/git-push line: {reasons}",
        )

    def test_global_only_heading_is_drift(self):
        """FR-11.8/NFR-10: structural content only the GLOBAL copy carries is unknown provenance."""
        reasons = []
        self.assertEqual(self.state(REPO_DOC, GLOBAL_EXTRA_HEADING, reasons), "drift")
        self.assertTrue(
            any("local hand edit" in r.lower() for r in reasons),
            f"drift reasons do not name the global-only heading: {reasons}",
        )

    def test_drift_wins_over_pending_when_repo_is_also_ahead(self):
        """A pending-shaped diff does not mask a real invariant divergence."""
        global_text = GLOBAL_MISSING_INVARIANT
        self.assertEqual(self.state(REPO_AHEAD_DOC, global_text), "drift")

    def test_empty_global_copy_is_drift(self):
        """Edge case: an empty/unpopulated global copy omits every invariant -> drift, not pending."""
        self.assertEqual(self.state(REPO_DOC, ""), "drift")

    def test_empty_repo_copy_against_populated_global_is_drift(self):
        """Edge case: with no repo invariants to compare, heading provenance still catches it."""
        self.assertEqual(self.state("", REPO_DOC), "drift")

    # --- fence awareness -----------------------------------------------------

    def test_hash_line_inside_a_code_fence_is_not_a_heading(self):
        """DD-6: heading extraction ignores fenced code, so a `#` line in a fence is not drift."""
        self.assertEqual(self.state(REPO_DOC, GLOBAL_FENCED_HASH), "pending")

    def test_repo_heading_inside_a_fence_does_not_excuse_a_real_global_heading(self):
        """Fence-awareness applies to both sides: a fenced mention is not a real repo heading."""
        self.assertEqual(self.state(REPO_FENCED_HEADING, GLOBAL_EXTRA_HEADING), "drift")

    # --- API shape -----------------------------------------------------------

    def test_reasons_argument_is_optional(self):
        """The helper must be callable without a reasons list (default None)."""
        self.assertEqual(
            docs.claude_sync_state(REPO_DOC, GLOBAL_EXTRA_HEADING, claude_invariants), "drift"
        )

    def test_state_is_always_one_of_the_three(self):
        fixtures = (
            (REPO_DOC, REPO_DOC),
            (REPO_AHEAD_DOC, REPO_DOC),
            (REPO_DOC, GLOBAL_MISSING_INVARIANT),
            (REPO_DOC, GLOBAL_RESTATED_INVARIANT),
            (REPO_DOC, GLOBAL_EXTRA_HEADING),
            (REPO_DOC, GLOBAL_FENCED_HASH),
            ("", REPO_DOC),
        )
        for repo_text, global_text in fixtures:
            with self.subTest(global_text=global_text[:40]):
                self.assertIn(self.state(repo_text, global_text), {"satisfied", "pending", "drift"})


class OrchestratorSyncStateThreeStatesTest(unittest.TestCase):
    """FR-11.8 (A2): the orchestrator copy of the state machine behaves identically."""

    @classmethod
    def setUpClass(cls):
        cls.repo_text = REPO_ORCH.read_text(encoding="utf-8")

    def state(self, repo_text, global_text, reasons=None):
        return orch.orchestrator_sync_state(
            repo_text, global_text, orch.orchestrator_invariant_lines, reasons
        )

    def test_equal_texts_are_satisfied(self):
        self.assertEqual(self.state(self.repo_text, self.repo_text), "satisfied")

    def test_repo_copy_with_added_section_is_pending(self):
        """NFR-10: this feature's orchestrator edits land as new prose -> pending, not drift."""
        repo = self.repo_text + "\n### Feature Classification Gate\n\nRecord `featureClass`.\n"
        self.assertEqual(self.state(repo, self.repo_text), "pending")

    def test_global_copy_missing_an_invariant_is_drift(self):
        """FR-11.8(A2): a global copy that DROPS the never-runs-gh framing is genuine drift."""
        global_text = self.repo_text.replace(
            "**You never run `gh` or `git push` yourself.**",
            "You may occasionally run `gh` yourself.",
        )
        self.assertNotEqual(global_text, self.repo_text, "fixture mutation did not apply")
        reasons = []
        self.assertEqual(self.state(self.repo_text, global_text, reasons), "drift")
        self.assertTrue(
            any("orchestrator_never_runs_gh_or_git_push" in r for r in reasons),
            f"drift reasons do not name the dropped invariant: {reasons}",
        )

    def test_global_copy_contradicting_an_invariant_is_drift(self):
        """FR-11.8(A2): an invariant RESTATED so its meaning inverts is drift, not pending."""
        global_text = self.repo_text.replace(
            "never on resume, so a resumed session does not re-push",
            "and on every resume as well",
        )
        self.assertNotEqual(global_text, self.repo_text, "fixture mutation did not apply")
        reasons = []
        self.assertEqual(self.state(self.repo_text, global_text, reasons), "drift")
        self.assertTrue(
            any("scaffold_push_first_scaffold_only" in r and "stated differently" in r
                for r in reasons),
            f"drift reasons do not report the contradicted scaffold-push scoping: {reasons}",
        )

    def test_global_copy_dropping_ready_to_merge_singleton_is_drift(self):
        """FR-11.8(A2): the ready-to-merge single-application-point rule must survive."""
        global_text = self.repo_text.replace(
            "This is the **only** place `ready-to-merge` is ever applied",
            "This is one of the places `ready-to-merge` may be applied",
        )
        self.assertNotEqual(global_text, self.repo_text, "fixture mutation did not apply")
        reasons = []
        self.assertEqual(self.state(self.repo_text, global_text, reasons), "drift")
        self.assertTrue(
            any("ready_to_merge_single_application_point" in r for r in reasons),
            f"drift reasons do not name the ready-to-merge invariant: {reasons}",
        )

    def test_global_only_heading_is_drift(self):
        global_text = self.repo_text + "\n## Local Hand Edit\n\nEdited in place.\n"
        reasons = []
        self.assertEqual(self.state(self.repo_text, global_text, reasons), "drift")
        self.assertTrue(
            any("local hand edit" in r.lower() for r in reasons),
            f"drift reasons do not name the global-only heading: {reasons}",
        )

    def test_the_two_state_machines_agree(self):
        """A2 keeps a deliberate local copy of the helper; the two must not silently diverge."""
        fixtures = (
            (REPO_DOC, REPO_DOC),
            (REPO_AHEAD_DOC, REPO_DOC),
            (REPO_DOC, GLOBAL_MISSING_INVARIANT),
            (REPO_DOC, GLOBAL_RESTATED_INVARIANT),
            (REPO_DOC, GLOBAL_EXTRA_HEADING),
            (REPO_DOC, GLOBAL_FENCED_HASH),
            (REPO_FENCED_HEADING, GLOBAL_EXTRA_HEADING),
            ("", REPO_DOC),
            (REPO_DOC, ""),
        )
        for repo_text, global_text in fixtures:
            with self.subTest(global_text=global_text[:40]):
                self.assertEqual(
                    docs.claude_sync_state(repo_text, global_text, claude_invariants),
                    orch.orchestrator_sync_state(repo_text, global_text, claude_invariants),
                    "claude_sync_state and orchestrator_sync_state disagree — the deliberate "
                    "local copy (A2) has drifted from the original",
                )


class InvariantExtractorsAreNonVacuousTest(unittest.TestCase):
    """NFR-6/FR-11.8: an extractor that matched nothing would make the surviving check vacuous."""

    def test_claude_extractor_finds_all_three_ownership_keys(self):
        repo_text = REPO_CLAUDE.read_text(encoding="utf-8")
        extracted = claude_invariants(repo_text)
        for key in ("bullet", "gh_line", "invariant"):
            self.assertIn(
                key, extracted,
                f"the repo CLAUDE.md no longer yields the `{key}` invariant — the CLAUDE.md drift "
                f"discriminator would go blind",
            )
            self.assertTrue(extracted[key].strip(), f"invariant `{key}` extracted as blank")

    def test_orchestrator_extractor_finds_every_named_invariant(self):
        repo_text = REPO_ORCH.read_text(encoding="utf-8")
        extracted = orch.orchestrator_invariant_lines(repo_text)
        missing = sorted(set(orch.ORCH_INVARIANT_PATTERNS) - set(extracted))
        self.assertEqual(
            missing, [],
            f"the repo agents/orchestrator.md no longer matches these invariant patterns: {missing}"
            f" — the drift discriminator would go blind",
        )
        for key, value in extracted.items():
            self.assertGreater(
                len(value.strip()), 10,
                f"orchestrator invariant `{key}` matched a suspiciously short span: {value!r}",
            )

    def test_orchestrator_invariant_set_covers_the_four_named_classes(self):
        """FR-11.8(A2) names four invariant classes that must remain checked."""
        keys = set(orch.ORCH_INVARIANT_PATTERNS)
        for expected in (
            "ready_to_merge_single_application_point",
            "clear_blocked_before_ready_to_merge",
            "clear_every_recorded_blocked_label",
            "scaffold_push_first_scaffold_only",
        ):
            self.assertIn(expected, keys, f"FR-11.8 invariant class `{expected}` is not checked")
        self.assertTrue(
            {"orchestrator_never_runs_gh_or_git_push", "github_agent_sole_gh_runner"} <= keys,
            "the never-runs-gh / github-agent-sole-runner framing is not checked",
        )

    def test_claude_invariant_set_is_not_extended_with_new_feature_prose(self):
        """DD-7: promoting this feature's new prose to an invariant would invert the amendment."""
        extracted = claude_invariants(REPO_CLAUDE.read_text(encoding="utf-8"))
        self.assertEqual(
            set(extracted), {"bullet", "gh_line", "invariant"},
            "the CLAUDE.md invariant set grew beyond the three Agent-Ownership lines FR-11.8 names",
        )


class FakeGlobalCopy:
    """An in-memory stand-in for a path under ~/.claude.

    Nothing is written and nothing is read from disk: the reworked assertions are driven over
    fixture text so that "what happens on genuine drift" can be observed without hand-editing the
    operator's live global configuration (NFR-10 forbids any write under ~/.claude/).
    """

    def __init__(self, text=None, error=None, present=True):
        self._text = text
        self._error = error
        self._present = present

    def exists(self):
        return self._present

    def read_text(self, encoding="utf-8"):
        if self._error is not None:
            raise self._error
        return self._text

    def __str__(self):
        return "<in-memory fixture global copy — no filesystem access>"


class DummyRepoDoc:
    """Read-only stand-in for an in-repo path, serving fixture text instead of the real file.

    Used only to simulate "the repository copy has moved ahead of the global copy" without editing
    the real file — the state NFR-10 declares a legitimate pending-sync window.
    """

    def __init__(self, text, real_path=None):
        self._text = text
        self._real = real_path

    def exists(self):
        return True

    def read_text(self, encoding="utf-8"):
        return self._text

    def __str__(self):
        return str(self._real) if self._real is not None else "<in-memory fixture repo copy>"


def run_claude_identity_assertion(fake_global, repo_text=None):
    """Drive the reworked CLAUDE.md assertion over fixture copies, then restore the real state."""
    cls = docs.ClaudeOwnershipContentTest
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(docs, "GLOBAL_CLAUDE", fake_global))
            if repo_text is not None:
                stack.enter_context(
                    mock.patch.object(
                        docs, "REPO_CLAUDE", DummyRepoDoc(repo_text, docs.REPO_CLAUDE)
                    )
                )
            cls.setUpClass()
            case = cls("test_two_claude_files_byte_identical")
            case.test_two_claude_files_byte_identical()
    finally:
        cls.setUpClass()  # restore real class state for any later run in this process


def run_orchestrator_identity_assertion(fake_global, repo_text=None):
    """Drive the reworked orchestrator assertion over fixture copies."""
    cls = orch.OrchestratorLabelLifecycleTest
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(orch, "GLOBAL_ORCH_PATH", fake_global))
            if repo_text is not None:
                stack.enter_context(
                    mock.patch.object(orch, "ORCH_PATH", DummyRepoDoc(repo_text, orch.ORCH_PATH))
                )
            cls.setUpClass()
            case = cls("test_repo_and_global_copies_are_byte_identical")
            case.test_repo_and_global_copies_are_byte_identical()
    finally:
        cls.setUpClass()


def run_real_identity_assertions():
    """Run both reworked assertions exactly as the suite does — real paths, no patching.

    Skips and failures are swallowed: this exists to observe side effects, not verdicts.
    """
    for cls, name in (
        (docs.ClaudeOwnershipContentTest, "test_two_claude_files_byte_identical"),
        (orch.OrchestratorLabelLifecycleTest, "test_repo_and_global_copies_are_byte_identical"),
    ):
        cls.setUpClass()
        try:
            getattr(cls(name), name)()
        except (unittest.SkipTest, AssertionError):
            pass


class ReworkedAssertionsStillFailOnDriftTest(unittest.TestCase):
    """AC-10: each reworked assertion tolerates the pending window yet FAILs on genuine drift."""

    @classmethod
    def setUpClass(cls):
        cls.repo_claude = REPO_CLAUDE.read_text(encoding="utf-8")
        cls.repo_orch = REPO_ORCH.read_text(encoding="utf-8")

    # --- CLAUDE.md (A1) ------------------------------------------------------

    def test_claude_assertion_passes_when_copies_are_identical(self):
        run_claude_identity_assertion(FakeGlobalCopy(text=self.repo_claude))

    def test_claude_assertion_passes_while_repo_copy_is_ahead(self):
        """NFR-10: the pending-sync window must not fail the assertion."""
        ahead = self.repo_claude + "\n## Feature Classification\n\nA new section.\n"
        run_claude_identity_assertion(FakeGlobalCopy(text=self.repo_claude), repo_text=ahead)

    def test_claude_assertion_fails_when_global_omits_an_invariant(self):
        """AC-10: a readable global copy omitting an Agent-Ownership invariant still FAILs."""
        drifted = self.repo_claude.replace(
            "No agent modifies another agent's artifact.", "", 1
        )
        self.assertNotEqual(drifted, self.repo_claude, "fixture mutation did not apply")
        with self.assertRaises(AssertionError) as ctx:
            run_claude_identity_assertion(FakeGlobalCopy(text=drifted))
        message = str(ctx.exception)
        self.assertIn("DRIFTED", message)
        self.assertIn("invariant", message)

    def test_claude_assertion_fails_when_global_restates_an_invariant(self):
        drifted = self.repo_claude.replace(
            "No agent modifies another agent's artifact.",
            "No agent modifies another agent's artifact, except the orchestrator.",
            1,
        )
        self.assertNotEqual(drifted, self.repo_claude, "fixture mutation did not apply")
        with self.assertRaises(AssertionError) as ctx:
            run_claude_identity_assertion(FakeGlobalCopy(text=drifted))
        self.assertIn("stated differently", str(ctx.exception))

    def test_claude_assertion_fails_on_a_global_only_heading(self):
        drifted = self.repo_claude + "\n## Local Hand Edit\n\nEdited in place.\n"
        with self.assertRaises(AssertionError) as ctx:
            run_claude_identity_assertion(FakeGlobalCopy(text=drifted))
        self.assertIn("local hand edit", str(ctx.exception).lower())

    def test_claude_assertion_skips_when_global_copy_is_unreadable(self):
        """The original skip behaviour survives the rework (CI has no global copy)."""
        with self.assertRaises(unittest.SkipTest):
            run_claude_identity_assertion(FakeGlobalCopy(error=OSError("no such file")))

    # --- agents/orchestrator.md (A2) ----------------------------------------

    def test_orchestrator_assertion_passes_when_copies_are_identical(self):
        run_orchestrator_identity_assertion(FakeGlobalCopy(text=self.repo_orch))

    def test_orchestrator_assertion_passes_while_repo_copy_is_ahead(self):
        """NFR-10: this feature's orchestrator edits are a pending sync, not a failure."""
        ahead = self.repo_orch + "\n### Feature Classification Gate\n\nRecord `featureClass`.\n"
        run_orchestrator_identity_assertion(
            FakeGlobalCopy(text=self.repo_orch), repo_text=ahead
        )

    def test_orchestrator_assertion_fails_when_global_omits_an_invariant(self):
        """AC-10: a readable global copy omitting an orchestrator invariant still FAILs."""
        drifted = self.repo_orch.replace(
            "**You never run `gh` or `git push` yourself.**",
            "You may occasionally run `gh` yourself.",
            1,
        )
        self.assertNotEqual(drifted, self.repo_orch, "fixture mutation did not apply")
        with self.assertRaises(AssertionError) as ctx:
            run_orchestrator_identity_assertion(FakeGlobalCopy(text=drifted))
        message = str(ctx.exception)
        self.assertIn("DRIFTED", message)
        self.assertIn("orchestrator_never_runs_gh_or_git_push", message)

    def test_orchestrator_assertion_fails_when_global_contradicts_an_invariant(self):
        drifted = self.repo_orch.replace(
            "never on resume, so a resumed session does not re-push",
            "and on every resume as well",
            1,
        )
        self.assertNotEqual(drifted, self.repo_orch, "fixture mutation did not apply")
        with self.assertRaises(AssertionError) as ctx:
            run_orchestrator_identity_assertion(FakeGlobalCopy(text=drifted))
        self.assertIn("scaffold_push_first_scaffold_only", str(ctx.exception))

    def test_orchestrator_assertion_fails_on_a_global_only_heading(self):
        drifted = self.repo_orch + "\n## Local Hand Edit\n\nEdited in place.\n"
        with self.assertRaises(AssertionError) as ctx:
            run_orchestrator_identity_assertion(FakeGlobalCopy(text=drifted))
        self.assertIn("local hand edit", str(ctx.exception).lower())

    def test_orchestrator_assertion_skips_when_global_copy_is_absent(self):
        with self.assertRaises(unittest.SkipTest):
            run_orchestrator_identity_assertion(FakeGlobalCopy(present=False))

    def test_orchestrator_assertion_skips_when_global_copy_is_unreadable(self):
        with self.assertRaises(unittest.SkipTest):
            run_orchestrator_identity_assertion(
                FakeGlobalCopy(error=OSError("permission denied"))
            )


class CarveOutIsConfinedTest(unittest.TestCase):
    """FR-11.8/AC-8: the carve-out keeps its shape — same names, same skips, nothing else lost."""

    @classmethod
    def setUpClass(cls):
        cls.docs_source = DOCS_MODULE_PATH.read_text(encoding="utf-8")
        cls.orch_source = ORCH_MODULE_PATH.read_text(encoding="utf-8")

    def test_reworked_assertions_kept_their_names(self):
        self.assertTrue(
            hasattr(docs.ClaudeOwnershipContentTest, "test_two_claude_files_byte_identical"),
            "test_two_claude_files_byte_identical was renamed or deleted",
        )
        self.assertTrue(
            hasattr(
                orch.OrchestratorLabelLifecycleTest,
                "test_repo_and_global_copies_are_byte_identical",
            ),
            "test_repo_and_global_copies_are_byte_identical was renamed or deleted",
        )

    def test_other_assertions_in_both_modules_survive(self):
        """FR-11.8: only two assertions are carved out; every other one remains."""
        for name in (
            "test_repo_has_agent_ownership_section",
            "test_repo_github_agent_bullet_present",
            "test_repo_gh_git_push_line_present",
            "test_repo_invariant_preserved",
            "test_global_claude_available_or_skip",
            "test_global_required_lines_present",
            "test_two_claude_ownership_lines_consistent",
        ):
            self.assertTrue(
                hasattr(docs.ClaudeOwnershipContentTest, name),
                f"{name} disappeared from tests/test_docs_updates.py",
            )
        for name in (
            "test_parses_as_valid_markdown",
            "test_feature_review_pass_clears_blocked_before_ready_to_merge",
            "test_per_task_pass_clears_all_blocked_labels",
            "test_scaffold_push_scoped_to_new_feature_no_base",
            "test_orchestrator_never_runs_gh_or_git_push",
        ):
            self.assertTrue(
                hasattr(orch.OrchestratorLabelLifecycleTest, name),
                f"{name} disappeared from tests/test_orchestrator_label_lifecycle.py",
            )

    def test_reworked_assertions_document_the_carve_out(self):
        """FR-11.8: the rationale lives in each reworked assertion itself."""
        pairs = (
            (docs.ClaudeOwnershipContentTest.test_two_claude_files_byte_identical, "CLAUDE.md"),
            (
                orch.OrchestratorLabelLifecycleTest.test_repo_and_global_copies_are_byte_identical,
                "orchestrator",
            ),
        )
        for func, label in pairs:
            doc = func.__doc__ or ""
            self.assertIn("FR-11.8", doc, f"{label} assertion docstring does not cite FR-11.8")
            self.assertIn("NFR-10", doc, f"{label} assertion docstring does not cite NFR-10")
            self.assertIn(
                "install.sh", doc,
                f"{label} assertion docstring does not name the post-merge installer sync",
            )

    def test_global_paths_derive_from_home_not_a_hardcoded_absolute(self):
        """FR-11.8/FR-11.1: the one permitted portability fix, and nothing beyond it."""
        self.assertEqual(docs.GLOBAL_CLAUDE, Path.home() / ".claude" / "CLAUDE.md")
        self.assertEqual(
            orch.GLOBAL_ORCH_PATH, Path.home() / ".claude" / "agents" / "orchestrator.md"
        )
        for name, source in (
            ("tests/test_docs_updates.py", self.docs_source),
            ("tests/test_orchestrator_label_lifecycle.py", self.orch_source),
        ):
            self.assertNotIn(
                "/Users/", source, f"{name} still hardcodes an absolute home-directory path"
            )

    def test_in_repo_paths_still_resolve_relative_to_the_test_file(self):
        """FR-11.1: the modules run wherever the repo's hooks run."""
        self.assertEqual(docs.ROOT, ROOT)
        self.assertEqual(orch.ORCH_PATH, REPO_ORCH)

    def test_no_third_live_global_assertion_was_introduced(self):
        """FR-11.8: the carve-out is closed at exactly two live-global readers."""
        live_global_readers = []
        for path in sorted(TESTS.glob("test_*.py")):
            source = path.read_text(encoding="utf-8")
            # Constants bound to a path under the real ~/.claude ...
            constants = re.findall(
                r"(?m)^([A-Z_][A-Z0-9_]*)\s*=\s*Path\.home\(\)\s*/\s*[\"']\.claude[\"']", source
            )
            # ... that the module then READS are the live-global checks FR-11.8 counts.
            if any(re.search(rf"\b{const}\b[^\n]*\.read_text\(", source) for const in constants):
                live_global_readers.append(path.name)
        self.assertEqual(
            sorted(live_global_readers),
            ["test_docs_updates.py", "test_orchestrator_label_lifecycle.py"],
            "the set of test modules reading a live copy under ~/.claude changed — FR-11.8 closes "
            "the carve-out at two and requires a fresh amendment for any third",
        )


class ClaudeHomeIsNeverWrittenTest(unittest.TestCase):
    """NFR-10: the pipeline never resolves the pending-sync window by writing to ~/.claude/.

    Only names, sizes and mtimes of the install surface are inspected — no file under ~/.claude is
    ever read, and none is ever written.
    """

    @staticmethod
    def install_surface_snapshot():
        snapshot = {}
        for name in INSTALL_SURFACE:
            target = CLAUDE_HOME / name
            if not target.exists():
                snapshot[name] = None
                continue
            if target.is_dir():
                snapshot[name] = "dir"
                for child in sorted(target.rglob("*")):
                    try:
                        stat = child.lstat()
                    except OSError:
                        snapshot[str(child)] = "unstatable"
                        continue
                    snapshot[str(child)] = (stat.st_size, stat.st_mtime_ns)
            else:
                stat = target.lstat()
                snapshot[name] = (stat.st_size, stat.st_mtime_ns)
        return snapshot

    def test_running_the_reworked_assertions_writes_nothing_under_claude_home(self):
        if not CLAUDE_HOME.exists():
            self.skipTest(f"{CLAUDE_HOME} does not exist (CI); nothing could be written there")
        before = self.install_surface_snapshot()
        if not any(isinstance(v, tuple) for v in before.values()):
            self.skipTest(f"{CLAUDE_HOME} carries no install surface; snapshot would be vacuous")

        run_real_identity_assertions()

        after = self.install_surface_snapshot()
        self.assertEqual(
            before, after,
            "something under ~/.claude/ changed while the reworked assertions ran — NFR-10 forbids "
            "the pipeline writing to the global copy; the operator runs ./install.sh after merge",
        )

    def test_reworked_modules_contain_no_write_operation(self):
        """NFR-10, statically: neither reworked module can write anywhere, let alone ~/.claude/."""
        write_patterns = (
            r"\.write_text\s*\(",
            r"\.write_bytes\s*\(",
            r"\.mkdir\s*\(",
            r"\.unlink\s*\(",
            r"\bshutil\.",
            r"\bsubprocess\b",
            r"\bos\.(remove|rename|makedirs|system)\b",
            r"\bopen\s*\([^)]*['\"][wax]",
            r"\btempfile\b",
        )
        for name, path in (
            ("tests/test_docs_updates.py", DOCS_MODULE_PATH),
            ("tests/test_orchestrator_label_lifecycle.py", ORCH_MODULE_PATH),
        ):
            source = path.read_text(encoding="utf-8")
            for pattern in write_patterns:
                self.assertIsNone(
                    re.search(pattern, source),
                    f"{name} contains a write-shaped operation matching {pattern!r}",
                )

    def test_global_paths_are_only_ever_read(self):
        """NFR-10: the two global constants are touched only by read_text()/exists()."""
        for name, path, const in (
            ("tests/test_docs_updates.py", DOCS_MODULE_PATH, "GLOBAL_CLAUDE"),
            ("tests/test_orchestrator_label_lifecycle.py", ORCH_MODULE_PATH, "GLOBAL_ORCH_PATH"),
        ):
            source = path.read_text(encoding="utf-8")
            attributes = set(re.findall(rf"\b{const}\.(\w+)", source))
            self.assertTrue(
                attributes <= {"read_text", "exists"},
                f"{name} performs {sorted(attributes - {'read_text', 'exists'})} on {const}; "
                f"only read_text/exists are permitted (NFR-10)",
            )

    def test_any_module_running_the_installer_sandboxes_home(self):
        """NFR-10/A1: no test may run ./install.sh against the operator's real ~/.claude.

        FR-11.8 records that the only modules executing the installer point `HOME` at a throwaway
        temporary directory, which is why they are not live-global checks and are unaffected by the
        pending-sync window. Any new installer-running module must do the same.
        """
        for path in sorted(TESTS.glob("test_*.py")):
            source = path.read_text(encoding="utf-8")
            if not re.search(r"subprocess\.[a-z_]+\([^)]*install\.sh", source, re.DOTALL):
                continue
            self.assertRegex(
                source, r"env\[[\"']HOME[\"']\]",
                f"{path.name} executes install.sh without overriding HOME",
            )
            self.assertTrue(
                "mkdtemp" in source or "TemporaryDirectory" in source,
                f"{path.name} executes install.sh without a throwaway temporary HOME",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
