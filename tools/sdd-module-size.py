#!/usr/bin/env python3
"""sdd-module-size.py — the mechanical "no god files" check (a ratchet, not a purge).

A source file VIOLATES when, after the change, it is over the module size limit AND it has more
lines than it had at the base. So:

  * a new file over the limit                 -> violation
  * a file that crosses the limit             -> violation
  * a file already over the limit that grows  -> violation (legacy god files may not grow)
  * a file over the limit that holds or shrinks -> ok (splitting a god file is always allowed)

The limit and the exemptions come from `.specs/steering/tech.md`:

    Module size limit: 500 lines
    Module size exempt: generated/**, **/*_pb2.py

or from --limit / --exempt. Only source-code suffixes are counted; docs, data, and lockfiles are
never checked. The changed set is every added, modified, or renamed file against the base —
tracked or untracked, non-ignored — read through a temporary index (rename-aware, NUL-delimited), so
a task's new files are covered before they are committed and a moved file keeps its base size.
Feature mode passes `--merge-base` so changes on the base branch are never blamed on the feature.

Exit codes: 0 no violation, 1 violation(s), 2 usage or git error. Output is one line per violation:
    <path>: <base lines> -> <lines now> (limit <N>)
Stdlib only.
"""

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_LIMIT = 500
CODE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".kts", ".scala", ".cs", ".fs", ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".swift", ".rb",
    ".php", ".lua", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".tf", ".sql", ".r", ".jl", ".dart",
    ".vue", ".svelte", ".ex", ".exs", ".erl", ".clj", ".groovy", ".pl",
}
# Tolerates list bullets and markdown bold: `- **Module size limit:** 500 lines`.
LIMIT_LINE = re.compile(r"^\s*[-*]?\s*\**Module size limit:\**\s*(\d+)\s*lines?\b", re.I | re.M)
EXEMPT_LINE = re.compile(r"^\s*[-*]?\s*\**Module size exempt:\**\s*(.+)$", re.I | re.M)


class GitError(Exception):
    pass


def git(repo: Path, *args: str, check: bool = True, env=None) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              env=env)
    except FileNotFoundError as exc:
        raise GitError("git is not installed") from exc
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def steering_config(repo: Path) -> Tuple[Optional[int], List[str]]:
    tech = repo / ".specs" / "steering" / "tech.md"
    if not tech.is_file():
        return None, []
    text = tech.read_text(encoding="utf-8", errors="replace")
    m = LIMIT_LINE.search(text)
    limit = int(m.group(1)) if m else None
    exempt: List[str] = []
    for em in EXEMPT_LINE.finditer(text):
        exempt += [g.strip().strip("`") for g in em.group(1).split(",") if g.strip().strip("`")]
    return limit, exempt


def count_lines(data: str) -> int:
    if not data:
        return 0
    return data.count("\n") + (0 if data.endswith("\n") else 1)


def is_exempt(path: str, globs: List[str]) -> bool:
    for g in globs:
        candidates = [g] + ([g[3:]] if g.startswith("**/") else [])
        if any(fnmatch.fnmatch(path, c) or fnmatch.fnmatch(Path(path).name, c) for c in candidates):
            return True
    return False


def changed_files(repo: Path, base: str) -> List[Tuple[str, str]]:
    """(path now, path at base) for every added, modified, or renamed file — tracked or untracked —
    computed through a temporary index so renames are detected and the real index is untouched.
    NUL-delimited, so unusual and non-ASCII paths are read exactly."""
    tmp = tempfile.mkdtemp(prefix="sdd-msz-")
    try:
        index = Path(tmp) / "index"
        real = Path(git(repo, "rev-parse", "--git-path", "index").strip())
        real = real if real.is_absolute() else repo / real
        if real.is_file():
            shutil.copyfile(real, index)
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        git(repo, "add", "-A", "--", ":/", env=env)
        out = git(repo, "diff", "--cached", "--name-status", "-M", "-z", base, "--", env=env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    fields = out.split("\0")
    changes, i = [], 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status[0] in "RC":
            changes.append((fields[i + 2], fields[i + 1]))
            i += 3
        else:
            if status[0] in "AM":
                changes.append((fields[i + 1], fields[i + 1]))
            i += 2
    return sorted(changes)


def base_lines(repo: Path, base: str, path: str) -> int:
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{base}:{path}"],
                          capture_output=True, text=True, errors="replace")
    return count_lines(proc.stdout) if proc.returncode == 0 else 0


def check(repo: Path, base: str, limit: int, exempt: List[str],
          only: Optional[List[str]] = None) -> List[Tuple[str, int, int]]:
    violations = []
    for path, old_path in changed_files(repo, base):
        if only is not None and path not in only:
            continue
        if Path(path).suffix.lower() not in CODE_SUFFIXES or is_exempt(path, exempt):
            continue
        full = repo / path
        if not full.is_file():
            continue
        now = count_lines(full.read_text(encoding="utf-8", errors="replace"))
        before = base_lines(repo, base, old_path)
        if now > limit and now > before:
            violations.append((path, before, now))
    return violations


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-module-size.py", description=__doc__.splitlines()[0])
    parser.add_argument("-C", dest="repo", default=".", help="repository directory (default: .)")
    parser.add_argument("--base", default="HEAD",
                        help="git ref to compare against (task mode: HEAD; feature mode: main)")
    parser.add_argument("--limit", type=int, help="override the steering limit")
    parser.add_argument("--exempt", action="append", default=[], help="extra exempt glob")
    parser.add_argument("--merge-base", action="store_true",
                        help="compare against merge-base(<base>, HEAD) — feature mode, so changes "
                             "on the base branch since the branch point are not blamed on it")
    parser.add_argument("--waive", action="append", default=[], metavar="PATH",
                        help="a user-granted waiver: report the file as WAIVED, do not fail on it")
    parser.add_argument("paths", nargs="*",
                        help="check only these paths (task mode: the executor's changed files)")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    try:
        repo = Path(git(repo, "rev-parse", "--show-toplevel").strip())
        base = args.base
        git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
        if args.merge_base:
            base = git(repo, "merge-base", base, "HEAD").strip()
        steer_limit, steer_exempt = steering_config(repo)
        limit = next(v for v in (args.limit, steer_limit, DEFAULT_LIMIT) if v is not None)
        found = check(repo, base, limit, steer_exempt + args.exempt, args.paths or None)
    except GitError as exc:
        print(f"sdd-module-size: git error: {exc}", file=sys.stderr)
        return 2
    violations = []
    for path, before, now in found:
        waived = path in args.waive
        print(f"{path}: {before} -> {now} (limit {limit})" + (" WAIVED" if waived else ""))
        if not waived:
            violations.append(path)
    if violations:
        print(f"sdd-module-size: {len(violations)} file(s) over the {limit}-line limit grew. "
              "Put new code in a new module, or split the file first.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
