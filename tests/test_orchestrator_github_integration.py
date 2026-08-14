#!/usr/bin/env python3
"""Structural lint for the orchestrator's GitHub Integration wiring (Task 2, sub-task 2.7).

This is not a unit test: agents/orchestrator.md is a markdown/config artifact, so the "test" is a
structure lint. It asserts that Task 2's cited requirements (FR-7..FR-12, NFR-1, NFR-2, NFR-8) are
wired into the orchestrator — the "GitHub Integration (remote choke-point)" subsection plus each
lifecycle invocation point, the choke-point / human-merge-gate invariants, and the routing of
github-agent halts through the existing Secret-Handling machinery.

Matches are on meaningful phrases / label tokens (e.g. `ready-to-merge`, `blocked:`, `git push`,
`draft`), not just headings, so the lint is not trivially satisfied. Mirrors Task 1's structural
lint (tests/test_github_agent_def.py). Stdlib-only so it runs anywhere the repo's hooks run.

Run:
    python3 -m unittest tests.test_orchestrator_github_integration -v
    # or
    python3 tests/test_orchestrator_github_integration.py
"""

import re
import unittest
from pathlib import Path

# Locate the orchestrator file relative to this test so it resolves in the worktree and after merge:
#   <root>/tests/test_orchestrator_github_integration.py  ->  <root>/agents/orchestrator.md
ORCH_PATH = Path(__file__).resolve().parent.parent / "agents" / "orchestrator.md"


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


class OrchestratorGithubIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert ORCH_PATH.exists(), f"orchestrator definition not found at {ORCH_PATH}"
        cls.text = ORCH_PATH.read_text(encoding="utf-8")
        fm, body = split_frontmatter(cls.text)
        cls.frontmatter_raw = fm
        cls.body = body

    def _assert_any(self, patterns, label):
        """Assert at least one of the given regexes matches somewhere in the body."""
        for pat in patterns:
            if re.search(pat, self.body, re.IGNORECASE | re.MULTILINE):
                return
        self.fail(f"required content not found: {label} (tried {patterns})")

    def _assert_all(self, patterns, label):
        """Assert every given regex matches somewhere in the body."""
        for pat in patterns:
            if not re.search(pat, self.body, re.IGNORECASE | re.MULTILINE):
                self.fail(f"required content not found: {label} — missing /{pat}/")

    # --- Basic markdown structure ---------------------------------------------

    def test_parses_as_valid_markdown(self):
        """2.7(1): the file parses as valid markdown — frontmatter (if any) intact,
        a non-empty body with headings, and balanced code fences."""
        # If the file opens with a frontmatter fence it must be well-formed (closed).
        if self.text.startswith("---"):
            self.assertIsNotNone(
                self.frontmatter_raw,
                "file opens with '---' but has no closing frontmatter fence",
            )
        # Non-empty body with at least one heading.
        self.assertTrue(self.body.strip(), "markdown body is empty")
        self.assertRegex(self.body, r"(?m)^#\s", "body has no markdown headings")
        # Code fences must be balanced (even count of ``` fence lines).
        fence_lines = re.findall(r"(?m)^```", self.text)
        self.assertEqual(
            len(fence_lines) % 2,
            0,
            f"unbalanced ``` code fences (found {len(fence_lines)})",
        )

    def test_github_integration_subsection_present(self):
        """2.7(2), FR-7..FR-12: a 'GitHub Integration (remote choke-point)' subsection heading exists."""
        self.assertRegex(
            self.body,
            r"(?mi)^#+\s+GitHub Integration\b.*choke-?point",
            "missing 'GitHub Integration (remote choke-point)' subsection heading",
        )

    def test_github_agent_is_the_named_choke_point(self):
        """FR-7..FR-12, NFR-1: github-agent is named as the single remote choke-point / sole invoker."""
        self.assertIn("github-agent", self.body, "orchestrator never references github-agent")
        self._assert_any(
            [r"single audited choke-?point", r"one\s+(leaf\s+)?subagent.*github-agent",
             r"only\s+invoker", r"single choke-?point"],
            "github-agent framed as the single choke-point / orchestrator as sole invoker",
        )

    # --- Lifecycle invocation points (2.7(3)) ---------------------------------

    def test_scaffold_does_not_push_branch_stays_local(self):
        """Local-first: the feature scaffold does NOT push; the branch stays local until publish."""
        self._assert_any(
            [r"(?is)branch is created by `/sdd-feature`.*?not pushed",
             r"(?is)local feature branch.*?not pushed",
             r"(?is)branch stays local"],
            "scaffold creates the branch locally and does not push it",
        )
        # The lifecycle table row for scaffold must record no github-agent action.
        self._assert_any(
            [r"(?is)Feature scaffold.*?\bnone\b.*?stays local",
             r"(?is)Feature scaffold.*?nothing is pushed"],
            "the scaffold lifecycle row performs no push",
        )

    def test_planning_confirm_is_local_commit_only_no_pr(self):
        """Local-first: a planning-phase confirm makes a LOCAL commit only — no push, no PR opened."""
        self._assert_any(
            [r"(?is)phase confirmed, local-first.*?action:\s*commit\b.*?local commit only",
             r"(?is)action:\s*commit\b.*?local commit only.*?no PR is opened"],
            "planning confirm -> local commit only, no PR",
        )
        # No draft PR is ever opened — the build never opens a PR, and publish opens it ready.
        self.assertNotRegex(
            self.body, r"draft:\s*true",
            "a draft PR is still opened — local-first opens the PR ready, only at publish",
        )
        self.assertNotIn("commit-push", self.body,
                         "the superseded commit-push action is still referenced")

    def test_per_task_pass_is_local_commit_with_task_trailer_and_local_verdicts(self):
        """Local-first: a per-task pass is a LOCAL commit (SDD-Task trailer), verdicts recorded locally."""
        self._assert_any(
            [r"(?is)per-task pass, local-first.*?action:\s*commit\b.*?local commit only, no push",
             r"(?is)action:\s*commit\b.*?local commit only, no push.*?SDD-Task"],
            "per-task pass -> local commit only, no push",
        )
        self.assertRegex(self.body, r"SDD-Task:\s*<N>",
                         "per-task commit does not carry the SDD-Task:<N> trailer")
        self._assert_any(
            [r"(?is)Record the verdict blocks locally.*?spec-memory",
             r"(?is)verdicts.*?recorded.*?spec-memory",
             r"(?is)accumulated verdicts are transcribed to the PR once, at the publish point"],
            "verdicts recorded locally, transcribed at publish (not per-task PR comments)",
        )

    def test_publish_point_sequence_at_feature_review_pass(self):
        """Local-first: the whole-feature-review PASS is the single publish point — push, ready PR,
        transcribe verdicts, set ready-to-merge, request review."""
        self.assertIn("ready-to-merge", self.body, "'ready-to-merge' label token absent")
        self._assert_any(
            [r"(?is)single publish point.*?push.*?open-pr.*?comment.*?ready-to-merge.*?request-review",
             r"(?is)publish point.*?action:\s*push.*?open-pr.*?ready-to-merge"],
            "publish sequence: push -> open-pr (ready) -> comment -> ready-to-merge -> request-review",
        )
        # The PR is opened READY, not draft.
        self._assert_any(
            [r"(?is)open-pr.*?draft:\s*false", r"(?is)open the PR \*\*ready\*\*, not draft"],
            "the published PR is ready, not draft",
        )
        # ready-to-merge is applied ONLY at the publish point, never earlier.
        self._assert_any(
            [r"(?is)ready-to-merge.*?only.*?publish point",
             r"(?is)only place `ready-to-merge` is ever applied",
             r"(?is)only.*?at the publish point.*?whole-feature review"],
            "ready-to-merge applied only at the publish point (FR-10.1/NFR-1)",
        )
        self._assert_any(
            [r"(?i)request-review", r"(?i)request\s+a human review"],
            "request human review at publish",
        )

    def test_blocking_finding_halts_locally_no_remote_label(self):
        """Local-first: a blocking finding halts locally — there is no PR, so no blocked:* label."""
        self._assert_any(
            [r"(?is)No remote label.*?no PR during the build.*?halts locally",
             r"(?is)blocking finding.*?halts locally",
             r"(?is)no PR.*?so.*?no\b.*?blocked:\*?\*? label"],
            "a blocking finding halts locally with no remote label",
        )
        # The blocked:* family is explicitly framed as legacy / not applied during the build.
        self._assert_any(
            [r"(?is)blocked:\*?\*?.*?legacy of the old draft-PR flow.*?no longer applied",
             r"(?is)no longer applied during the build"],
            "blocked:* framed as legacy, not applied during the local-first build",
        )

    # --- Invariants: choke-point + human merge gate (2.7(4), 2.7(3) complete) --

    def test_orchestrator_never_runs_gh_or_git_push(self):
        """2.7(4), NFR-1, FR-12: the file states the orchestrator itself never runs gh / git push."""
        self._assert_any(
            [r"(?is)never run[s]?\s+`?gh`?\s*(/|or|and)\s*`?git push`?",
             r"(?is)never\b.*?`?git push`?\s+yourself",
             r"(?is)you never run\s+`?gh`?"],
            "orchestrator never runs gh / git push itself (choke-point)",
        )
        self.assertIn("git push", self.body, "'git push' phrase absent")

    def test_human_merge_gate_documented_in_complete(self):
        """FR-12: the complete phase documents the human merge gate (never merge; ready-to-merge required)."""
        self._assert_any(
            [r"(?is)ready for human merge",
             r"(?is)merge (in)?to the protected `?main`?.*?human",
             r"(?is)human action gated on .*ready-to-merge"],
            "human merge gate documented (ready for human merge / gated on ready-to-merge)",
        )
        self._assert_any(
            [r"(?is)never merge", r"(?is)no agent performs it",
             r"(?is)never ask github-agent to merge", r"(?is)you\b.*?\bnever\b.*?merge"],
            "never-merge invariant stated",
        )
        self.assertRegex(self.body, r"FR-12\b", "FR-12 not cited for human merge gate")

    def test_secret_request_and_blocked_halts_routed_via_secret_handling(self):
        """NFR-2: SECRET REQUEST / missing-gh / GITHUB BLOCKED halts routed via Secret-Handling machinery."""
        self._assert_all(
            [r"SECRET REQUEST", r"GITHUB BLOCKED"],
            "github-agent halt vocabulary (SECRET REQUEST / GITHUB BLOCKED)",
        )
        self._assert_any(
            [r"(?i)missing[- ]`?gh`?", r"(?i)`gh` CLI", r"(?i)install(ing)? `?gh`?"],
            "missing-gh handling mentioned",
        )
        self._assert_any(
            [r"(?is)Secret[- ]Handling machinery",
             r"(?is)exactly.*as.*specialist secret request",
             r"(?is)treat these exactly as.*secret request",
             r"(?is)surface.*provision.*re-invoke",
             r"(?is)never read (or paste )?the secret"],
            "halts routed through the existing Secret-Handling machinery (surface/provision/re-invoke)",
        )
        # NFR-2 behaviour (design maps NFR-2 to C1/C6; the orchestrator's obligation is behavioural,
        # not an ID citation): the secret's value is never read into the orchestrator's context.
        self._assert_any(
            [r"(?is)never read (or paste )?the secret",
             r"(?is)value\b.*?\bnever\b.*?(your )?context",
             r"(?is)never your context",
             r"(?is)through the environment.*?never"],
            "NFR-2: secret value never enters the orchestrator's context",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
