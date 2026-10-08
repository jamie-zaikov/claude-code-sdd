#!/usr/bin/env python3
"""Structural lint for PR 2: context packs, concurrent validation and review, delta re-review,
the acceptance probe, and Level 1 stage overlap.

Matches are on meaningful phrases, so a reworded rule that drops its substance turns the suite red.
Stdlib only. Run:
    python3 -m unittest tests.test_pr2_pipeline -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orch = read("agents/orchestrator.md")
        start = cls.orch.index("### `implementation`")
        cls.impl = cls.orch[start:cls.orch.index("### Feature Review Gate", start)]

    def has(self, text, pat, label):
        if not re.search(pat, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            self.fail(f"{label}: missing /{pat}/")

    def lacks(self, text, pat, label):
        if re.search(pat, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            self.fail(f"{label}: forbidden /{pat}/ present")


class ContextPackTest(Base):
    def test_orchestrator_builds_the_pack_every_attempt(self):
        self.has(self.impl, r"\*\*Context pack \(before Stage 1, every attempt\)\.\*\*", "pack step")
        self.has(self.impl, r"python3 ~/\.claude/tools/sdd-context-pack\.py\s+--feature-dir", "pack command")
        self.has(self.impl, r"Rebuild it on every attempt", "rebuild")
        self.has(self.impl, r"Never pass\s+`spec-memory/` wholesale", "no wholesale spec-memory")
        self.lacks(self.impl, r"All feature spec files", "old whole-folder input")

    def test_specialists_read_the_pack_not_the_folder(self):
        for name in ("task-executor", "task-tester", "task-validator"):
            text = read(f"agents/{name}.md")
            self.has(text, r"Read the \*\*context pack\*\*", name)
            self.has(text, r"Do \*\*not\*\* read\s+the whole feature folder", name)
            self.has(text, r"`Pack misses`", name)
            self.lacks(text, r"Read all files in `\.specs/features/<feature-name>/`", name)

    def test_validator_keeps_the_full_requirements(self):
        self.has(read("agents/task-validator.md"), r"Also read the \*\*full\*\* `requirements\.md`", "validator")
        self.has(self.impl, r"task-validator\s+also reads the full `requirements\.md`", "orchestrator")

    def test_reviewers_read_the_pack(self):
        for name in ("code-reviewer", "security-reviewer"):
            self.has(read(f"agents/{name}.md"), r"Read the \*\*context pack\*\*", name)


class ConcurrentStagesTest(Base):
    def test_validator_and_reviewers_launch_together(self):
        self.has(self.impl, r"Stages 3–5 — Validation and review, concurrently", "concurrent")
        self.has(self.impl, r"launch them \*\*in one message\*\*", "one message")
        self.lacks(self.impl, r"Only run Stages 4–5 if validation passes", "old serial gate")

    def test_combining_rule(self):
        self.has(self.impl, r"discard the reviewers' PASS verdicts", "discard passes")
        self.has(self.impl, r"\*\*keep their blocking findings\*\*", "keep findings")
        self.has(self.impl, r"one\s+combined retry report", "one report")
        self.has(self.impl, r"`RT-2`: handle it as a\s+reclassification", "RT-2 kept")

    def test_delta_re_review(self):
        self.has(self.impl, r"invoke each reviewer with `mode: delta`", "orchestrator delta")
        self.has(self.impl, r"validator always runs in full on a retry", "validator full")
        for name in ("code-reviewer", "security-reviewer"):
            text = read(f"agents/{name}.md")
            self.has(text, r"\*\*`delta` mode\*\*", name)
            self.has(text, r"git diff\s+<previousTree>`? — the fix only", name)
            self.has(text, r"Still run your mechanical checks over the task's full file list", name)


class ProbeTest(Base):
    def test_probe_rules(self):
        self.has(self.impl, r"\*\*Acceptance probe\.\*\*", "orchestrator")
        self.has(self.impl, r"Agents never write or edit the probe command", "never edit")
        self.has(self.impl, r"never\s+run one not marked `sim-only`", "sim-only")
        self.has(self.orch, r"\*\*Acceptance probe:\*\* when `tech\.md` declares one", "preflight")
        self.has(read("agents/task-validator.md"), r"### 2a\. Acceptance probe", "validator")
        self.has(read("agents/code-reviewer.md"), r"### Acceptance probe \(feature mode\)", "reviewer")
        self.has(read("agents/code-reviewer.md"), r"A non-zero exit is a \*\*High\*\* finding", "reviewer severity")

    def test_steering_template(self):
        tech = read("steering-templates/tech.md")
        self.has(tech, r"^## Acceptance Probe$", "probe section")
        self.has(tech, r"Probe scope: sim-only", "scope line")
        self.has(tech, r"Stage overlap: on", "overlap toggle")
        self.has(tech, r"Specialist grace: 1200 s", "grace")


class OverlapTest(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        start = cls.orch.index("#### Stage overlap (Level 1)")
        cls.ovl = cls.orch[start:cls.orch.index("### Feature Review Gate", start)]

    def test_conditions(self):
        self.has(self.ovl, r"on the \*\*code track\*\*", "code track only")
        self.has(self.ovl, r"`Stage overlap: off`", "toggle")
        self.has(self.ovl, r"every task\s+its `Depends:` line names \(other than N\) is `complete`", "depends")
        self.has(self.ovl, r"no speculation is\s+running", "depth one")
        self.has(self.ovl, r"Never start a speculation for a non-code task, a task that mutates a live\s+system", "never")

    def test_lifecycle(self):
        for action in ("overlap-start", "overlap-land", "overlap-discard"):
            self.has(self.ovl, rf"action:\s+{action}", action)
        self.has(self.ovl, r"continue N\+1 at Stage 2", "continue at tester")
        self.has(self.ovl, r"N fails, or land reports stale", "discard path")
        self.has(self.ovl, r"no gate ever sees speculative code", "no gate sees it")

    def test_executor_speculative_mode(self):
        ex = read("agents/task-executor.md")
        self.has(ex, r"\*\*Speculative mode \(Level 1 stage overlap\)\.\*\*", "section")
        self.has(ex, r"write and edit code \*\*only under the worktree path\*\*", "worktree only")
        self.has(ex, r"never touch the main checkout, never commit", "no main checkout")

    def test_github_agent_runs_the_tool(self):
        gh = read("agents/github-agent.md")
        self.has(gh, r"python3 ~/\.claude/tools/sdd-overlap\.py start --task <N> --tree <hash>", "start")
        self.has(gh, r"never retry a land by hand-rolled git", "no hand-rolled")
        for doc in (gh, self.orch):
            self.has(doc, r"overlap-start \| overlap-land \| overlap-discard", "action enum")

    def test_state_key(self):
        self.has(self.orch, r"`invocations`, and `speculation` \(top level\)", "state key")


class DocsTest(unittest.TestCase):
    def test_claude_md_summarises_pr2(self):
        text = read("CLAUDE.md")
        for pat in (r"Context packs, not whole folders", r"Validation and review run concurrently",
                    r"acceptance probe", r"Stage overlap \(Level 1\)"):
            self.assertRegex(text, pat)

    def test_readme_and_uninstall_list_the_tools(self):
        for tool in ("sdd-context-pack.py", "sdd-overlap.py"):
            self.assertIn(tool, read("README.md"))
            self.assertIn(f'rm -f "${{CLAUDE_HOME}}/tools/{tool}"', read("uninstall.sh"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
