#!/usr/bin/env python3
"""
Shared SDD secret scanner — the SINGLE implementation reused by BOTH the CI
secret-scan workflow (`sdd-secret-scan.yml`) and the pre-push git hook, so CI
mirrors the local gate by construction rather than by two copies that can drift
(design DD-2 / FR-16 / NFR-3).

It scans only ADDED/CHANGED content over a git diff range and exits:
  0  clean          — no secret-shaped content in the added lines
  1  secret found   — at least one match; findings printed by TYPE and path:line
  2  usage/git error — bad arguments, git failure, or unreadable diff file

Findings are reported by TYPE and `path:line` ONLY — never the matched value
(NFR-2). The `Finding` record has no value field, and no code path prints the
value on any branch (report, error, or traceback).

Regex family (DD-2): the secret-shaped patterns below are VENDORED verbatim, in
lock-step, from `hooks/secret-redact.py`'s PATTERNS (all 13 families). They are
copied rather than imported because `/sdd-init` ships this scanner standalone
into downstream projects where `hooks/secret-redact.py` does not exist. If the
source family changes, update this list to keep the two byte-identical.

Two NARROW suppression mechanisms keep the gate green over the framework's own
tree without weakening detection (see PRAGMA_MARKER / DEFAULT_EXCLUDED_PATHS):
an inline `pragma: allowlist secret` marker suppresses only its own added line,
and an explicit enumerated path-exclude list covers the framework's own
pattern-definition and dedicated secret-fixture files.

stdlib only (re, subprocess, sys, argparse, typing) — no external dependency
(no gitleaks), per DD-2.
"""
import argparse
import re
import subprocess
import sys
from typing import List, NamedTuple, Optional, Tuple


# --- Vendored secret-shaped regex family (DD-2, lock-step with secret-redact.py) ---
# Each entry is (type-label, compiled-pattern). The pattern SOURCE and flags are
# byte-identical to hooks/secret-redact.py's PATTERNS; only the human-readable
# type label (used for reporting, never the value) is added here.
VENDORED_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    # Private key blocks (whole block) — the only multiline pattern (re.S).
    ("private-key-block", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    # AWS access key ids.
    ("aws-access-key-id", re.compile(
        r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA)[0-9A-Z]{16}\b")),
    # GitHub / GitLab tokens.
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("gitlab-pat", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    # Slack tokens & webhooks.
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    # Google API keys.
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    # Stripe / OpenAI-style secret keys.
    ("openai-secret-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("stripe-live-key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b")),
    # JWTs.
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    # Authorization / bearer headers.
    ("authorization-header", re.compile(
        r"(?i)(authorization\s*[:=]\s*(?:bearer|basic|token)\s+)\S+")),
    ("x-api-key-header", re.compile(r"(?i)(x-api-key\s*[:=]\s*)\S+")),
    # key=value / key: value where the key is secret-shaped.
    ("secret-assignment", re.compile(
        r"(?i)\b([\w.-]*(?:api[_-]?key|secret|token|passwd|password|pwd|access[_-]?key|private[_-]?key)[\w.-]*\s*[:=]\s*)"
        r"[\"']?[A-Za-z0-9_\-./+=]{8,}[\"']?"
    )),
]

# Split by whether the pattern spans lines (re.DOTALL). Only the private-key
# block is multiline; it is scanned over a contiguous added-run (see below), the
# rest are scanned per single added line.
_MULTILINE_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    (name, pat) for name, pat in VENDORED_PATTERNS if pat.flags & re.DOTALL
]
_SINGLE_LINE_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    (name, pat) for name, pat in VENDORED_PATTERNS if not (pat.flags & re.DOTALL)
]


# --- Targeted suppression (DD-2 dogfood remediation; FR-13/FR-16/FR-21) ---------
# Two NARROW mechanisms let this scanner run clean over the SDD framework's OWN
# tree — which by design carries the secret-regex family and deliberately
# secret-shaped test fixtures — WITHOUT weakening detection anywhere else:
#
#   1. Inline pragma — an added line whose content contains the EXACT marker
#      below is not reported. It suppresses ONLY that one line (the token is
#      detect-secrets-compatible), never a neighbor and never the whole file.
#   2. Path excludes — an EXPLICIT, ENUMERATED list of the framework's own
#      pattern-definition and dedicated secret-fixture files. A finding on a
#      listed path is skipped; a SIBLING non-listed path is still fully scanned.
#      There are NO globs — every entry is one auditable repo-relative path.
#
# Neither mechanism disables the gate: a secret-shaped string on any other path,
# without the pragma on its own line, is still detected and still exits 1.
PRAGMA_MARKER = "pragma: allowlist secret"

# Repo-relative paths (as they appear after the `b/` prefix in a `+++ b/<path>`
# header) whose secret-shaped content is intentional framework material:
#   - the secret-pattern definitions themselves (redactor + guard + this scanner,
#     both copies) and their documentation,
#   - the dedicated test suites that embed secret-shaped fixtures by design.
DEFAULT_EXCLUDED_PATHS = frozenset({
    "hooks/secret-redact.py",
    "hooks/secret-guard.py",
    "hooks/README.md",
    "ci-templates/scripts/sdd-secret-scan.py",
    ".github/scripts/sdd-secret-scan.py",
    "tests/test_sdd_secret_scan.py",
    "tests/test_secret_guard_gh.py",
})


def _normalize_diff_path(path: str) -> str:
    """Normalize a diff path to the repo-relative form used by the exclude list:
    strip a leading `a/`/`b/` (git's diff-side prefixes) and a leading `./`.
    Paths from `_new_path_from_header` are already `b/`-stripped; this keeps the
    match robust for callers that pass a raw path."""
    if path.startswith(("a/", "b/")):
        path = path[2:]
    if path.startswith("./"):
        path = path[2:]
    return path


def _is_excluded(path: str, excluded_paths: "frozenset[str]") -> bool:
    """True when the (normalized) path is on the explicit framework exclude list."""
    return _normalize_diff_path(path) in excluded_paths


def _line_has_pragma(text_lines: List[str], index: int) -> bool:
    """True when the content line at `index` carries the inline allowlist marker.
    Bounds-checked so a finding line that falls outside the scanned block (never
    expected) is simply treated as un-suppressed."""
    return 0 <= index < len(text_lines) and PRAGMA_MARKER in text_lines[index]


class Finding(NamedTuple):
    """A detected secret. Carries the TYPE and location ONLY — never the value
    (NFR-2)."""
    type: str
    path: str
    line: int


class AddedRun(NamedTuple):
    """A contiguous run of added lines from a single hunk, with the new-file
    line number of the first line."""
    path: str
    start_line: int
    lines: List[str]


_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _new_path_from_header(header_body: str) -> str:
    """Extract the path from a `+++ ` header value, stripping the `b/` prefix
    git prepends and ignoring a `/dev/null` (file deletion) target."""
    token = header_body.split("\t", 1)[0].strip()
    if token == "/dev/null":
        return "<removed>"
    if token.startswith("b/"):
        token = token[2:]
    return token


def parse_unified_diff(diff_text: str) -> List[AddedRun]:
    """Parse a unified git diff into contiguous runs of ADDED lines.

    Robustness note (fixes a false-negative class): git-diff BODY content can be
    textually identical to a structural header. A removed source line that reads
    `-- deprecated setting` renders in the diff as `--- deprecated setting`; an
    added line beginning `++ x` renders as `+++ x`. A naive parser that treats
    any `---`/`+++`/`diff `/`index ` prefixed line as structural would leave the
    hunk and skip every remaining added line in it, letting a secret added in the
    same hunk slip through.

    To avoid that, this parser is driven by the hunk header's line counts:
    `@@ -oldStart,oldCount +newStart,newCount @@`. After a hunk header it consumes
    EXACTLY the counted body lines, classifying each STRICTLY by its first
    character (`+` added, `-` removed, ` ` context, `\\` no-newline marker). A
    line whose content merely looks like a header is therefore never mistaken for
    one while inside a hunk body. Structural lines (`+++ b/path`, `diff --git`,
    etc.) are only interpreted OUTSIDE a counted hunk body, so the `+++ b/path`
    header sets the current path but is never scanned as content.

    Omitted counts (`@@ -a +c @@`) default to 1, per git's convention. Multiple
    hunks and multiple files in one diff are handled.
    """
    runs: List[AddedRun] = []
    lines = diff_text.split("\n")
    n = len(lines)
    current_path: Optional[str] = None
    i = 0
    while i < n:
        line = lines[i]

        # Outside any hunk body: interpret structural lines.
        if line.startswith("+++ "):
            current_path = _new_path_from_header(line[4:])
            i += 1
            continue

        m = _HUNK_HEADER.match(line)
        if not m:
            # Any other structural / preamble line (diff --git, index, ---,
            # rename, new file, Binary files, etc.) — not content, skip.
            i += 1
            continue

        # Enter the hunk body: consume exactly the counted lines.
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        new_count = int(m.group(4)) if m.group(4) is not None else 1
        new_line = int(m.group(3))
        remaining_old = old_count
        remaining_new = new_count

        run_start: Optional[int] = None
        run_lines: List[str] = []
        path = current_path or "<unknown>"

        i += 1
        while i < n and (remaining_old > 0 or remaining_new > 0):
            body = lines[i]
            if body == "":
                # A malformed / truncated body line — stop consuming this hunk
                # rather than misclassify. (Blank content lines carry a leading
                # ' ' or '+' prefix, so a truly empty string is not a body line.)
                break
            c = body[0]
            if c == "+":
                if run_start is None:
                    run_start = new_line
                run_lines.append(body[1:])
                new_line += 1
                remaining_new -= 1
            elif c == "-":
                # Removed line: does not advance the new-file counter and breaks
                # any contiguous added-run.
                if run_lines:
                    runs.append(AddedRun(path, run_start or new_line, run_lines))
                    run_start, run_lines = None, []
                remaining_old -= 1
            elif c == " ":
                # Context line: advances new-file counter, breaks the added-run.
                if run_lines:
                    runs.append(AddedRun(path, run_start or new_line, run_lines))
                    run_start, run_lines = None, []
                new_line += 1
                remaining_old -= 1
                remaining_new -= 1
            elif c == "\\":
                # "\ No newline at end of file" — a marker, not counted content.
                pass
            else:
                # First char is none of +/-/space/backslash: not a valid body
                # line (e.g. the next hunk header or file header). Stop the hunk.
                break
            i += 1

        if run_lines:
            runs.append(AddedRun(path, run_start or new_line, run_lines))
        # Loop continues; `i` already points past the consumed body.

    return runs


def scan_content(text: str, path: str, base_line: int = 1) -> List[Finding]:
    """Scan a block of added text. Single-line patterns run per line; multiline
    patterns (private-key block) run over the whole block passed in. Callers
    pass a single contiguous added-run so a multiline match maps to a real,
    contiguous block (see scan_added_lines)."""
    findings: List[Finding] = []

    text_lines = text.split("\n")
    for offset, content_line in enumerate(text_lines):
        for type_label, pat in _SINGLE_LINE_PATTERNS:
            if pat.search(content_line):
                findings.append(Finding(type_label, path, base_line + offset))

    for type_label, pat in _MULTILINE_PATTERNS:
        for match in pat.finditer(text):
            line_no = base_line + text.count("\n", 0, match.start())
            findings.append(Finding(type_label, path, line_no))

    # Inline-pragma suppression: drop any finding whose OWN reported line carries
    # the allowlist marker. Tight by construction — the marker on line N
    # suppresses ONLY line N (single- or multiline match start); neighboring
    # lines and the rest of the block are unaffected.
    findings = [
        f for f in findings if not _line_has_pragma(text_lines, f.line - base_line)
    ]

    return findings


def scan_added_lines(
    runs: List[AddedRun],
    excluded_paths: "frozenset[str]" = DEFAULT_EXCLUDED_PATHS,
) -> List[Finding]:
    """Scan each contiguous added-run independently.

    Scanning per run (rather than joining all added lines of a file across
    hunks) prevents a cross-hunk false positive: a `-----BEGIN ... PRIVATE
    KEY-----` added in one hunk and an unrelated `-----END ... PRIVATE KEY-----`
    added in a far-apart hunk must NOT match as a single block. A real private
    key is a contiguous added block and lands inside one run.

    A run whose path is on `excluded_paths` (the framework's own
    pattern-definition + dedicated secret-fixture files) is skipped entirely; a
    run on any sibling path is still scanned in full."""
    findings: List[Finding] = []
    for run in runs:
        if _is_excluded(run.path, excluded_paths):
            continue
        block = "\n".join(run.lines)
        findings.extend(scan_content(block, run.path, run.start_line))
    return findings


def scan_diff(
    diff_text: str,
    excluded_paths: "frozenset[str]" = DEFAULT_EXCLUDED_PATHS,
) -> List[Finding]:
    """Parse a unified diff and return findings over its added content, honoring
    the inline-pragma and path-exclude suppression mechanisms."""
    return scan_added_lines(parse_unified_diff(diff_text), excluded_paths)


def format_findings(findings: List[Finding]) -> str:
    """Render findings by TYPE and path:line ONLY (never the value, NFR-2)."""
    return "\n".join(
        f"{f.path}:{f.line}: potential secret [{f.type}]" for f in findings
    )


class GitError(Exception):
    """A git invocation failed; maps to exit code 2 (never conflated with the
    exit-1 'secret detected' signal)."""


def _git_diff(diff_args: List[str], repo: Optional[str]) -> str:
    """Run `git [-C repo] diff <args>` and return its stdout decoded with
    errors='replace'. STRICT UTF-8 decoding (subprocess text=True) would raise
    UnicodeDecodeError on a non-UTF-8 byte in the diff, and the interpreter then
    exits 1 — colliding with the 'secret detected' exit code and breaking the
    0/1/2 contract. Capturing bytes and decoding with 'replace' keeps a binary
    byte from ever mapping a git run onto the detection signal."""
    cmd = ["git"]
    if repo:
        cmd += ["-C", repo]
    cmd += ["diff"] + diff_args
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", "replace").strip() or
                       f"git diff exited {proc.returncode}")
    return proc.stdout.decode("utf-8", "replace")


def _read_diff_file(path: str) -> str:
    """Read a pre-computed unified diff from a file (or stdin when '-'), decoding
    with errors='replace' to match _git_diff and stay non-UTF-8 safe."""
    if path == "-":
        return sys.stdin.buffer.read().decode("utf-8", "replace")
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8", "replace")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sdd-secret-scan.py",
        description="Scan added/changed content of a git diff range for "
                    "secret-shaped material. Exit 0 clean, 1 secret found, "
                    "2 usage/git error.",
    )
    parser.add_argument(
        "-C", dest="repo", metavar="REPO",
        help="run git in the given repository directory",
    )
    parser.add_argument(
        "--diff-file", dest="diff_file", metavar="PATH",
        help="read a pre-computed unified diff from PATH ('-' for stdin) "
             "instead of running git diff",
    )
    parser.add_argument(
        "diff_args", nargs=argparse.REMAINDER,
        help="arguments passed through to `git diff` (e.g. a range like "
             "BASE...HEAD, or '--unified=0'). Place after any scanner options.",
    )
    # argparse exits 2 on its own usage errors, matching the contract.
    args = parser.parse_args(argv)

    try:
        if args.diff_file is not None:
            diff_text = _read_diff_file(args.diff_file)
        else:
            diff_text = _git_diff(args.diff_args, args.repo)
    except GitError as exc:
        print(f"sdd-secret-scan: git error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        # Unreadable --diff-file, missing stdin, etc. Report the error text
        # (never any diff content) and map to the usage/error exit code.
        print(f"sdd-secret-scan: cannot read diff: {exc}", file=sys.stderr)
        return 2

    findings = scan_diff(diff_text)
    if findings:
        # Report to stderr by type and path:line only — never the value.
        print(format_findings(findings), file=sys.stderr)
        print(
            f"sdd-secret-scan: {len(findings)} potential secret(s) detected in "
            f"added content.", file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
