"""Presentation-tolerant matching for prose-contract tests (steering lesson 5).

A prose pin must go RED when the rule's meaning changes and stay GREEN when only its presentation
changes. `search` removes the presentation layer — Markdown bold/strong markers, runs of spaces,
and line wrapping — from both the document and the pattern, so a test asserts the words of a rule,
not its emphasis or its line breaks. It matches against two views of the text: line breaks kept
(for patterns anchored with `^`/`$`) and lines joined (for a phrase wrapped across lines); either
view matching is a match. Code spans (backticks) are kept: they carry identity (a key, a command,
a path).
"""

import re

_STRONG = re.compile(r"\*\*|__")
_SPACE = re.compile(r"\s+")
_HSPACE = re.compile(r"[ \t]+")


def norm(text):
    """Drop strong-emphasis markers and collapse every whitespace run to one space."""
    return _SPACE.sub(" ", _STRONG.sub("", text))


def norm_lines(text):
    """Drop strong-emphasis markers and collapse spaces, keeping line breaks."""
    return _HSPACE.sub(" ", _STRONG.sub("", text))


def norm_pattern(pat):
    """The same transform for a regex: drop escaped strong markers (`\\*\\*`, `__`)."""
    return pat.replace(r"\*\*", "").replace("__", "")


def search(text, pat, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL):
    pat = norm_pattern(pat)
    return re.search(pat, norm_lines(text), flags) or re.search(pat, norm(text), flags)
