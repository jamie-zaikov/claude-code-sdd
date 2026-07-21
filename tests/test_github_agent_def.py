#!/usr/bin/env python3
"""Structural + frontmatter lint for the github-agent scribe definition (Task 1, sub-task 1.8).

This is not a unit test: agents/github-agent.md is a markdown/config artifact, so the "test" is a
structure lint. It asserts the frontmatter and required body sections that Task 1's cited
requirements demand. Stdlib-only (no pyyaml dependency) so it runs anywhere the repo's hooks run.

Run:
    python3 -m unittest tests.test_github_agent_def -v
    # or
    python3 tests/test_github_agent_def.py
"""

import re
import unittest
from pathlib import Path

# Locate the agent file relative to this test so it resolves in the worktree and after merge:
#   <root>/tests/test_github_agent_def.py  ->  <root>/agents/github-agent.md
AGENT_PATH = Path(__file__).resolve().parent.parent / "agents" / "github-agent.md"


def split_frontmatter(text):
    """Split a markdown file into (frontmatter_str, body_str).

    Expects the file to open with a `---` fence, a YAML frontmatter block, and a closing `---`
    fence, followed by the markdown body. Returns (None, text) if no valid frontmatter is present.
    """
    if not text.startswith("---"):
        return None, text
    # Match the opening fence, capture up to the next line that is exactly '---'.
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def parse_simple_frontmatter(fm):
    """Parse the restricted `key: value` / block-list subset used by fleet agent frontmatter.

    Supports:
      - `key: value` scalars (folded `>` multi-line values are collapsed to a marker string)
      - `key:` followed by `  - item` list entries

    Returns a dict mapping key -> value (str) or list[str]. Deliberately minimal; the agent
    frontmatter only uses these forms.
    """
    data = {}
    lines = fm.split("\n")
    i = 0
    key_indent_re = re.compile(r"^(\S[^:]*):\s*(.*)$")
    list_item_re = re.compile(r"^\s+-\s+(.*)$")
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        km = key_indent_re.match(line)
        if km:
            key = km.group(1).strip()
            val = km.group(2).strip()
            if val in (">", "|", ">-", "|-", ">+", "|+"):
                # Folded/literal block scalar: consume the more-indented continuation lines.
                block = []
                i += 1
                while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                    block.append(lines[i].strip())
                    i += 1
                data[key] = " ".join(b for b in block if b)
                continue
            if val == "":
                # Possibly a block list on following indented `- ` lines.
                items = []
                j = i + 1
                while j < len(lines) and list_item_re.match(lines[j]):
                    items.append(list_item_re.match(lines[j]).group(1).strip())
                    j += 1
                if items:
                    data[key] = items
                    i = j
                    continue
                data[key] = ""
                i += 1
                continue
            data[key] = val
            i += 1
            continue
        i += 1
    return data


class GithubAgentDefinitionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assertTrueMsg = None
        assert AGENT_PATH.exists(), f"agent definition not found at {AGENT_PATH}"
        cls.text = AGENT_PATH.read_text(encoding="utf-8")
        fm, body = split_frontmatter(cls.text)
        cls.frontmatter_raw = fm
        cls.body = body
        cls.fm = parse_simple_frontmatter(fm) if fm is not None else {}

    # --- Frontmatter structure -------------------------------------------------

    def test_parses_as_frontmatter_plus_body(self):
        """FR-1.1: file is valid YAML frontmatter followed by a non-empty markdown body."""
        self.assertIsNotNone(
            self.frontmatter_raw,
            "file does not open with a --- YAML frontmatter fence",
        )
        self.assertTrue(self.body.strip(), "markdown body after frontmatter is empty")
        # A markdown body should contain at least one heading.
        self.assertRegex(self.body, r"(?m)^#\s", "body has no markdown headings")

    def test_name_and_description_present(self):
        """FR-1.1: name and description keys are present and non-empty."""
        self.assertIn("name", self.fm, "frontmatter missing `name`")
        self.assertTrue(str(self.fm.get("name", "")).strip(), "`name` is empty")
        self.assertEqual(self.fm.get("name"), "github-agent", "`name` should be github-agent")
        self.assertIn("description", self.fm, "frontmatter missing `description`")
        self.assertTrue(
            str(self.fm.get("description", "")).strip(), "`description` is empty"
        )

    def test_model_is_sonnet(self):
        """FR-1.1: model is set to sonnet."""
        self.assertIn("model", self.fm, "frontmatter missing `model`")
        self.assertEqual(self.fm.get("model"), "sonnet", "`model` must be sonnet")

    def test_user_invocable_false(self):
        """FR-1.2: user-invocable is set to false (orchestrator-only agent)."""
        self.assertIn("user-invocable", self.fm, "frontmatter missing `user-invocable`")
        self.assertEqual(
            str(self.fm.get("user-invocable")).strip().lower(),
            "false",
            "`user-invocable` must be false",
        )

    def test_tools_contains_exactly_read_glob_grep_bash(self):
        """FR-1.1, FR-1.3, DD-3: tools == {Read, Glob, Grep, Bash} exactly."""
        self.assertIn("tools", self.fm, "frontmatter missing `tools`")
        tools = self.fm.get("tools")
        self.assertIsInstance(tools, list, "`tools` must be a list")
        self.assertEqual(
            set(tools),
            {"Read", "Glob", "Grep", "Bash"},
            f"`tools` must be exactly Read/Glob/Grep/Bash, got {tools}",
        )

    def test_tools_excludes_write_edit_agent(self):
        """FR-1.3, DD-3: no Write/Edit (remote-only mechanics) and no Agent (leaf, cannot delegate)."""
        tools = set(self.fm.get("tools", []))
        for forbidden in ("Write", "Edit", "Agent"):
            self.assertNotIn(
                forbidden, tools, f"`tools` must exclude `{forbidden}`"
            )

    # --- Required body sections (FR-2..FR-6) -----------------------------------

    def _assert_section(self, patterns, label):
        """Assert that at least one of the given regexes matches a heading/marker in the body."""
        for pat in patterns:
            if re.search(pat, self.body, re.IGNORECASE | re.MULTILINE):
                return
        self.fail(f"required section not found: {label} (tried {patterns})")

    def test_charter_section_present(self):
        """FR-2, FR-2.2: charter / scribe-not-author framing present."""
        self._assert_section(
            [r"scribe,\s*not\s*an?\s*author", r"(?m)^#+.*charter", r"audited choke-point"],
            "Charter / scribe-not-author",
        )

    def test_permitted_operations_section_present(self):
        """FR-3: permitted operations section present."""
        self._assert_section(
            [r"(?m)^#+.*permitted operations"], "Permitted operations"
        )

    def test_prohibited_operations_section_present(self):
        """FR-4: prohibited operations section present."""
        self._assert_section(
            [r"(?m)^#+.*prohibited operations"], "Prohibited operations"
        )

    def test_authentication_section_present(self):
        """FR-5: Authentication ('use, don't read') section present."""
        self._assert_section(
            [r"(?m)^#+.*authentication", r"use,\s*don'?t\s*read"],
            "Authentication (use, don't read)",
        )

    def test_verdict_transcription_section_present(self):
        """FR-6: Verdict transcription section present."""
        self._assert_section(
            [r"(?m)^#+.*verdict transcription", r"transcribe.*verbatim"],
            "Verdict transcription",
        )

    def test_on_invocation_section_present(self):
        """FR-3..FR-6 (D1): On Invocation request-vocabulary section present."""
        self._assert_section([r"(?m)^#+.*on invocation"], "On Invocation")

    def test_return_contract_section_present(self):
        """FR-3..FR-6 (D2): Return Contract section present, with the DONE/BLOCKED verbs."""
        self._assert_section([r"(?m)^#+.*return contract"], "Return Contract")
        self.assertIn("GITHUB DONE", self.body, "Return Contract missing `GITHUB DONE`")
        self.assertIn(
            "GITHUB BLOCKED", self.body, "Return Contract missing `GITHUB BLOCKED`"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
