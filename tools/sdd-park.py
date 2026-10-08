#!/usr/bin/env python3
"""sdd-park.py — park and unpark a halted task's uncommitted work, safely (github-agent runs it).

    sdd-park.py park   --task N            -> prints the stash SHA, or `none` when nothing to park
    sdd-park.py unpark --task N --ref SHA  -> applies that stash back onto a clean tree

Everything outside `.specs/` counts (tracked edits and untracked, non-ignored files); `.specs/` is
never parked, because the orchestrator's state lives there.

park never returns a stash it did not create: it decides "nothing to park" with the same pathspec
the stash uses, then requires `refs/stash` to have moved and the new entry's message to be
`sdd-task-<N>-parked`. unpark applies only a stash whose message names the same task, only onto a
clean tree, and on a conflict restores the tree to what it was before the apply.

Exit codes: 0 done, 1 unpark conflict (tree restored), 2 refused or git error. Stdlib only.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

PATHSPEC = [":/", ":(top,exclude).specs"]


class Refused(Exception):
    pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise Refused(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc


def message(task: str) -> str:
    return f"sdd-task-{task}-parked"


def dirty(repo: Path) -> List[str]:
    out = git(repo, "status", "--porcelain", "--untracked-files=all", "--", *PATHSPEC).stdout
    return [line for line in out.splitlines() if line.strip()]


def stash_head(repo: Path) -> Optional[str]:
    proc = git(repo, "rev-parse", "-q", "--verify", "refs/stash", check=False)
    return proc.stdout.strip() or None


def subject(repo: Path, ref: str) -> str:
    return git(repo, "log", "-1", "--format=%s", ref).stdout.strip()


def park(repo: Path, task: str) -> str:
    if not dirty(repo):
        return "none"
    before = stash_head(repo)
    git(repo, "stash", "push", "--include-untracked", "-m", message(task), "--", *PATHSPEC)
    after = stash_head(repo)
    if not after or after == before:
        raise Refused("git stash created no entry; nothing was parked")
    if not subject(repo, after).endswith(message(task)):
        raise Refused(f"newest stash is not {message(task)}; refusing to record it")
    if dirty(repo):
        raise Refused("working tree still dirty after park")
    return after


def unpark(repo: Path, task: str, ref: str) -> None:
    if not subject(repo, ref).endswith(message(task)):
        raise Refused(f"{ref} is not a {message(task)} stash")
    if dirty(repo):
        raise Refused("working tree is not clean outside .specs/; refusing to apply over it")
    applied = git(repo, "stash", "apply", ref, check=False)
    if applied.returncode == 0:
        return
    # Restore the clean tree we started from: drop tracked edits and the stash's untracked files.
    git(repo, "reset", "-q", "--", *PATHSPEC, check=False)
    git(repo, "checkout", "-q", "HEAD", "--", *PATHSPEC, check=False)
    untracked = git(repo, "ls-tree", "-r", "--name-only", f"{ref}^3", check=False).stdout.split("\n")
    for rel in filter(None, untracked):
        (repo / rel).unlink(missing_ok=True)
    raise ConflictError(applied.stderr.strip() or "stash apply conflicted")


class ConflictError(Exception):
    pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-park.py", description=__doc__.splitlines()[0])
    parser.add_argument("-C", dest="repo", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("park")
    p.add_argument("--task", required=True)
    u = sub.add_parser("unpark")
    u.add_argument("--task", required=True)
    u.add_argument("--ref", required=True)
    args = parser.parse_args(argv)
    try:
        repo = Path(git(Path(args.repo), "rev-parse", "--show-toplevel").stdout.strip())
        if args.cmd == "park":
            print(park(repo, args.task))
        else:
            unpark(repo, args.task, args.ref)
            print(f"unparked {args.ref}")
        return 0
    except ConflictError as exc:
        print(f"sdd-park: conflict, tree restored: {exc}", file=sys.stderr)
        return 1
    except (Refused, FileNotFoundError) as exc:
        print(f"sdd-park: refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
