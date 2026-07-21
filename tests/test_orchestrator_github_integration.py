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

    def test_scaffold_pushes_branch(self):
        """FR-7, FR-3.1: feature scaffold invokes github-agent to push the feature branch + upstream."""
        self._assert_any(
            [r"(?is)scaffold.*?\bpush\b.*?(branch|upstream)",
             r"(?is)branch already created locally.*?push",
             r"(?is)push.*?feature branch.*?upstream"],
            "feature-scaffold -> push branch / set upstream invocation",
        )
        self.assertRegex(self.body, r"FR-7\b", "FR-7 not cited for scaffold trigger")

    def test_planning_confirm_commit_push_and_first_draft_pr(self):
        """FR-8, FR-3.2: planning-phase confirm commit-pushes, and the first confirm opens a DRAFT PR."""
        self.assertIn("commit-push", self.body, "no commit-push invocation documented")
        self._assert_any(
            [r"(?is)first\b.*?confirmation.*?open-pr",
             r"(?is)open-pr.*?draft:\s*true",
             r"(?is)first\b.*?confirm.*?draft"],
            "first planning confirm -> open-pr as draft",
        )
        self.assertRegex(self.body, r"(?i)draft", "draft PR not mentioned for first confirm")
        self.assertRegex(self.body, r"FR-8\b", "FR-8 not cited for planning-confirm trigger")

    def test_per_task_pass_commit_push_and_verdict_comment(self):
        """FR-9, FR-6, FR-6.1, NFR-8: per-task pass commit-pushes changes and comments the verdict blocks."""
        self._assert_any(
            [r"(?is)per-task.*?pass.*?commit-push.*?comment",
             r"(?is)validator PASS.*?both reviewers PASS.*?commit-push",
             r"(?is)commit-push.*?task'?s changes.*?comment"],
            "per-task pass -> commit-push + comment verdicts",
        )
        # The three verdict blocks must be transcribed verbatim and stage-attributed.
        self._assert_any(
            [r"(?is)three verbatim.*?verdict", r"(?is)verbatim.*?verdict",
             r"(?is)transcribed.*?verdict", r"(?is)stage-attributed verdict"],
            "verbatim / stage-attributed verdict transcription",
        )
        self.assertRegex(self.body, r"FR-9\b", "FR-9 not cited for per-task trigger")

    def test_feature_review_pass_sets_ready_to_merge_and_requests_review(self):
        """FR-10, FR-10.1, NFR-1: feature-review PASS sets ready-to-merge and requests human review."""
        self.assertIn("ready-to-merge", self.body, "'ready-to-merge' label token absent")
        self._assert_any(
            [r"(?i)request-review", r"(?i)request\s+review\s+from a human",
             r"(?i)human[- ]review request"],
            "request human review on feature-review PASS",
        )
        # FR-10.1 / NFR-1: ready-to-merge is set ONLY at feature-review PASS, never earlier.
        self._assert_any(
            [r"(?is)only\b.*?ready-to-merge.*?never (earlier|before)",
             r"(?is)ready-to-merge.*?\bonly\b.*?feature[- ]?review",
             r"(?is)only\b.*?feature[- ]?review.*?ready-to-merge",
             r"(?is)never\b.*?ready-to-merge.*?before",
             r"(?is)ready-to-merge.*?never\b.*?(earlier|before)"],
            "ready-to-merge set only at feature-review PASS, never earlier (FR-10.1/NFR-1)",
        )
        self._assert_all([r"FR-10\b", r"FR-10\.1\b"], "FR-10 / FR-10.1 citations")

    def test_blocking_finding_sets_blocked_label_and_keeps_draft(self):
        """FR-11: any blocking finding sets a blocked:<stage> label and keeps the PR in draft."""
        self.assertRegex(self.body, r"blocked:", "'blocked:' label family token absent")
        self._assert_any(
            [r"(?is)blocked:.*?keep.*?draft", r"(?is)keep.*?draft.*?blocked:",
             r"(?is)stays draft", r"(?is)keep the PR (in )?\*?\*?draft",
             r"(?is)keep PR \*?\*?draft"],
            "blocking finding keeps PR in draft",
        )
        # The blocked family should name at least the per-stage variants.
        self._assert_any(
            [r"blocked:validation", r"blocked:code-review",
             r"blocked:security-review", r"blocked:feature-review"],
            "blocked:<stage> family naming the failing stage",
        )
        self.assertRegex(self.body, r"FR-11\b", "FR-11 not cited for blocking-finding trigger")

    def test_blocked_label_cleared_on_resolution(self):
        """FR-11.1: on resolution the orchestrator clears the blocked:<stage> label."""
        self._assert_any(
            [r"(?i)label clear blocked:", r"(?is)clear.*?blocked:",
             r"(?is)op:\s*clear,\s*name:\s*blocked:", r"(?is)blocked:.*?cleared"],
            "blocked:<stage> label cleared on resolution",
        )
        self.assertRegex(self.body, r"FR-11\.1\b", "FR-11.1 not cited for label-clear")

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
