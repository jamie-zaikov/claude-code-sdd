"""Presentation-tolerant matching for prose-contract tests (steering lesson 5).

A prose pin must go RED when the rule's meaning changes and stay GREEN when only its presentation
changes. `search` removes the presentation layer — Markdown bold/strong markers, runs of spaces,
and line wrapping — from both the document and the pattern, so a test asserts the words of a rule,
not its emphasis or its line breaks. It matches against two views of the text: line breaks kept
(for patterns anchored with `^`/`$`) and lines joined (for a phrase wrapped across lines); either
view matching is a match. Code spans (backticks) are kept: they carry identity (a key, a command,
a path).

`search` is a raw match: use it to forbid a phrase in any form. A positive pin uses `affirms` (or
`near`), which also refuses a match that a negation reverses — "Do not rebuild it on every attempt"
must not satisfy a pin on "Rebuild it on every attempt". A match is negated when one of the three
words right before it, in the same clause, is a negation (not, never, no, without, don't ...); in
`near` each term is checked on its own, so a negation slipped in between two terms is caught too,
and every occurrence of each term is tried, so a negated occurrence never hides a good one.
A pin whose rule really is negative puts the negation inside its pattern.
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


_FLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL
_NEGATION = re.compile(r"^(?:not|never|no|none|nor|neither|without|cannot|\w+n't)$", re.I)
_CLAUSE_END = re.compile(r"[.;:!?,](?=\s|$)|[\n—]")  # a dot inside a path is no end
_WORDS = 3


def search(text, pat, flags=_FLAGS):
    pat = norm_pattern(pat)
    return re.search(pat, norm_lines(text), flags) or re.search(pat, norm(text), flags)


def _negated_at(view, start, floor=0):
    """True when one of the few words right before `start` (same clause, after `floor`) negates."""
    if view.count("`", 0, start) % 2:  # inside a code span: the span is one token, look before it
        start = max(view.rfind("`", 0, start), floor)
    lead = view[floor:start]
    ends = list(_CLAUSE_END.finditer(lead))
    if ends:
        lead = lead[ends[-1].end():]
    return any(_NEGATION.match(w.strip("*_`()[]\"'")) for w in lead.split()[-_WORDS:])


def affirms(text, pat, flags=_FLAGS):
    """A match of `pat` that no negation right before it reverses ("Do not rebuild it" never
    satisfies a pin on "Rebuild it"), or None. In `near`, each term is checked on its own."""
    rx = re.compile(norm_pattern(pat), flags)
    for view in (norm_lines(text), norm(text)):
        m = rx.search(view)
        while m:  # every start position: a negated match must not hide a later, overlapping one
            if not _negated_at(view, m.start()):
                return m
            m = rx.search(view, m.start() + 1)
    return None


def near(text, *terms, window=160):
    """True when every term (a regex) appears in order, each within `window` characters of the
    previous one, in the normalized text, and no term is negated (see `affirms`). Pins the KEY WORDS
    and DIRECTION of a rule (who, never, must, what) while tolerating rewording around them."""
    rxs = [re.compile(norm_pattern(t), _FLAGS) for t in terms]
    return any(_chain(view, rxs, 0, 0, None, window) is not None
               for view in (norm_lines(text), norm(text)))


def _chain(view, rxs, i, pos, prev_end, window):
    """Start positions of an affirmed chain of terms i.. (a list), or None. Every occurrence of term
    i in its window is tried, so a negated or misplaced occurrence never hides a later good one."""
    if i == len(rxs):
        return []
    m = rxs[i].search(view, pos)
    while m and (prev_end is None or m.start() <= prev_end + window):
        if not _negated_at(view, m.start(), prev_end or 0):
            rest = _chain(view, rxs, i + 1, m.end(), m.end(), window)
            if rest is not None:
                return [m.start()] + rest
        m = rxs[i].search(view, m.start() + 1)
    return None
