#!/usr/bin/env python3
"""Pin for `agents/tasks-agent.md` Task Design Rule 5 (postmortem finding F2).

Rule 5 used to read "No non-coding tasks: ... Only include tasks that produce code or tests."
That sentence categorically forbade the task list a feature which ships no application code
needs, and it sat upstream of the whole lifecycle: tasks-agent could not author such a list at
all. It was unpinned prose -- nothing in tests/ referenced tasks-agent.md -- which is the defect
shape `.specs/steering/process-lessons.md` rule 5 describes: correct logic that nothing holds in
place, or in this case incorrect logic that nothing flagged.

What is pinned here is the *property*, not the sentence (process-lessons rule 5; postmortem
6.2 item 7):

  1. The categorical prohibition is gone, and stays gone. Asserted against the superseded
     wording specifically, so the probe discriminates the dead text from its live successor
     (postmortem 4.8) rather than matching both.
  2. Rule 5 still excludes work no agent can perform -- the fix must not turn into "anything
     goes". "deploy" and "user testing" remain named exclusions.
  3. Rule 5 affirmatively admits a non-code artifact as a valid task output, keyed on the
     artifact nouns rather than on any one phrasing, so a reworded rule that keeps the
     admission still passes and a reworded rule that drops it fails.

EXPECTED ON ANY RE-RUN: 4 tests, 4 pass. A failure here means rule 5's meaning moved, not that
its wording moved -- read the assertion message before changing the test.

Mutation-verified: re-indenting rule 5, restoring the old sentence, or deleting the
non-code admission each turns this module RED. See the commit message for the transcript.

Run:
    python3 -m unittest tests.test_tasks_agent_non_code_tasks -v
    # or
    python3 tests/test_tasks_agent_non_code_tasks.py
"""

import re
import unittest
from pathlib import Path

# <root>/tests/test_tasks_agent_non_code_tasks.py -> <root>/agents/tasks-agent.md
AGENT_PATH = Path(__file__).resolve().parent.parent / "agents" / "tasks-agent.md"

# The exact clauses that made rule 5 a blocker. Neither may return in any casing.
SUPERSEDED_CLAUSES = (
    "No non-coding tasks",
    "Only include tasks that produce code or tests",
)

# Work that genuinely cannot be done by an agent. Rule 5 must keep excluding it.
REQUIRED_EXCLUSIONS = ("deploy", "user testing")

# Artifact nouns that evidence the non-code admission. Rule 5 must name at least two, so a
# rule that mentions one in passing does not satisfy the pin.
NON_CODE_ARTIFACT_NOUNS = (
    "committed document",
    "spec artifact",
    "knowledge-vault entry",
)


def load_agent_text():
    """Read the agent definition, failing with a useful message if it has moved."""
    if not AGENT_PATH.is_file():
        raise AssertionError(f"agent definition not found at {AGENT_PATH}")
    return AGENT_PATH.read_text(encoding="utf-8")


def extract_task_design_rules(text):
    """Return the body of the `### Task Design Rules` section, or None if absent.

    Scoping to the section matters: tasks-agent.md carries more than one numbered list, and an
    earlier one also has an item 5 ("Explore the codebase..."). A file-wide search for `5.`
    finds that one first and every downstream assertion then reasons about the wrong rule.
    """
    m = re.search(
        r"^###[ \t]+Task Design Rules[ \t]*$\n(.*?)(?=^###[ \t]|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    return m.group(1) if m else None


def extract_rule_5(text):
    """Return the body of Task Design Rule 5, or None if it cannot be located.

    Rule 5 runs from its own `5.` list marker to the next top-level numbered marker or the next
    heading, whichever comes first. Tolerant of leading whitespace so a re-indent does not make
    the rule silently unfindable -- an unfindable rule must fail loudly, not vacuously pass.
    """
    section = extract_task_design_rules(text)
    if section is None:
        return None
    m = re.search(
        r"^[ \t]*5\.[ \t]+(.*?)(?=^[ \t]*6\.[ \t]+|^[ \t]*#)",
        section,
        re.DOTALL | re.MULTILINE,
    )
    return m.group(1).strip() if m else None


class TasksAgentRule5(unittest.TestCase):
    """Rule 5 must gate on agent-executability, not on the code/tests dichotomy."""

    @classmethod
    def setUpClass(cls):
        cls.text = load_agent_text()
        cls.rule_5 = extract_rule_5(cls.text)

    def test_rule_5_is_locatable(self):
        """A rule the other assertions cannot find would make them vacuously pass."""
        self.assertIsNotNone(
            self.rule_5,
            "Task Design Rule 5 could not be located in agents/tasks-agent.md. The other "
            "assertions in this module depend on finding it, so an unfindable rule fails here "
            "rather than passing silently elsewhere.",
        )

    def test_categorical_prohibition_is_absent(self):
        """The superseded wording must not come back anywhere in the file."""
        haystack = self.text.lower()
        for clause in SUPERSEDED_CLAUSES:
            self.assertNotIn(
                clause.lower(),
                haystack,
                f"agents/tasks-agent.md has reintroduced the clause {clause!r}. This is "
                "postmortem finding F2: it forbids the task list a non-code feature needs and "
                "sits upstream of the entire lifecycle.",
            )

    def test_human_only_work_is_still_excluded(self):
        """Relaxing rule 5 must not relax it into admitting work no agent can do."""
        rule = (self.rule_5 or "").lower()
        for term in REQUIRED_EXCLUSIONS:
            self.assertIn(
                term,
                rule,
                f"Task Design Rule 5 no longer names {term!r} as excluded. Rule 5 must keep "
                "ruling out work that requires a human to act; the F2 fix removed the "
                "code-or-tests dichotomy, not the agent-executability requirement.",
            )

    def test_non_code_artifacts_are_admitted(self):
        """The admission is keyed on artifact nouns, so a rewording that keeps it still passes."""
        rule = (self.rule_5 or "").lower()
        found = [noun for noun in NON_CODE_ARTIFACT_NOUNS if noun in rule]
        self.assertGreaterEqual(
            len(found),
            2,
            "Task Design Rule 5 must affirmatively admit non-code artifacts as valid task "
            f"output, naming at least two of {list(NON_CODE_ARTIFACT_NOUNS)}; found {found}. "
            "Removing the old prohibition is not sufficient -- silence on the point is what let "
            "tasks-agent read the code/tests dichotomy as exhaustive in the first place.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
