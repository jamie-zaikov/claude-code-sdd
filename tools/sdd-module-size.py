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
never checked. The changed set is `git diff --name-only <base>` plus untracked, non-ignored files,
so a task's new files are covered before they are committed.

Exit codes: 0 no violation, 1 violation(s), 2 usage or git error. Output is one line per violation:
    <path>: <base lines> -> <lines now> (limit <N>)
Stdlib only.
"""

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_LIMIT = 500
CODE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".kts", ".scala", ".cs", ".fs", ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".swift", ".rb",
    ".php", ".lua", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".tf", ".sql", ".r", ".jl", ".dart",
    ".vue", ".svelte", ".ex", ".exs", ".erl", ".clj", ".groovy", ".pl",
}
LIMIT_LINE = re.compile(r"^\s*[-*]?\s*Module size limit:\s*(\d+)\s*lines?\b", re.I | re.M)
EXEMPT_LINE = re.compile(r"^\s*[-*]?\s*Module size exempt:\s*(.+)$", re.I | re.M)


class GitError(Exception):
    pass


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
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
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(Path(path).name, g) for g in globs)


def changed_files(repo: Path, base: str) -> List[str]:
    tracked = git(repo, "diff", "--name-only", "--diff-filter=AMR", base, "--").splitlines()
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in tracked + untracked if p})


def base_lines(repo: Path, base: str, path: str) -> int:
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{base}:{path}"],
                          capture_output=True, text=True, errors="replace")
    return count_lines(proc.stdout) if proc.returncode == 0 else 0


def check(repo: Path, base: str, limit: int, exempt: List[str]) -> List[Tuple[str, int, int]]:
    violations = []
    for path in changed_files(repo, base):
        if Path(path).suffix.lower() not in CODE_SUFFIXES or is_exempt(path, exempt):
            continue
        full = repo / path
        if not full.is_file():
            continue
        now = count_lines(full.read_text(encoding="utf-8", errors="replace"))
        before = base_lines(repo, base, path)
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
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    try:
        repo = Path(git(repo, "rev-parse", "--show-toplevel").strip())
        git(repo, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
        steer_limit, steer_exempt = steering_config(repo)
        limit = args.limit or steer_limit or DEFAULT_LIMIT
        violations = check(repo, args.base, limit, steer_exempt + args.exempt)
    except GitError as exc:
        print(f"sdd-module-size: git error: {exc}", file=sys.stderr)
        return 2
    for path, before, now in violations:
        print(f"{path}: {before} -> {now} (limit {limit})")
    if violations:
        print(f"sdd-module-size: {len(violations)} file(s) over the {limit}-line limit grew. "
              "Put new code in a new module, or split the file first.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
