#!/usr/bin/env python3
"""sdd-overlap.py — Level 1 stage overlap: task N+1's executor works while task N is reviewed.

    sdd-overlap.py start   --task M [--tree T]   -> prints `<worktree path> <base commit>`
    sdd-overlap.py land    --task M --base B     -> moves M's work into the main checkout
    sdd-overlap.py discard --task M              -> removes M's worktree; nothing else changes

`start` snapshots the main checkout's tree (task N's finished but not yet committed work; pass the
suite record's tree hash as --tree, or it is computed through a temporary index) as a detached base
commit, and adds a worktree for task M on it under `<git-common-dir>/sdd-overlap/task-M`. Only one
speculation exists at a time.

`land` runs only when task N was committed with exactly the snapshot's content (HEAD has no
difference from the base outside `.specs/`) and the main checkout is clean outside `.specs/`. It
commits M's worktree changes onto the base (a commit no branch points to), applies them to the main
checkout with `cherry-pick --no-commit`, unstages them, and removes the worktree — M then continues
its pipeline in the main checkout like any task. If N changed after the snapshot (a fix round),
`land` refuses with exit 1 and the caller discards: M restarts on the real tree.

Exit codes: 0 done, 1 stale (N changed since the snapshot), 2 refused or git error. Stdlib only.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

PATHSPEC = [":/", ":(top,exclude).specs"]


class Refused(Exception):
    pass


class Stale(Exception):
    pass


def git(cwd: Path, *args: str, check: bool = True, env=None) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    if check and proc.returncode != 0:
        raise Refused(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def tree_of(cwd: Path) -> str:
    """The working tree's tree hash outside `.specs/`, through a temporary index."""
    tmp = tempfile.mkdtemp(prefix="sdd-ovl-")
    try:
        index = Path(tmp) / "index"
        real = Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-path", "index").strip())
        if real.is_file():
            shutil.copyfile(real, index)
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        git(cwd, "add", "-A", "--", *PATHSPEC, env=env)
        return git(cwd, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def worktree_path(repo: Path, task: str) -> Path:
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    return common / "sdd-overlap" / f"task-{task}"


def existing(repo: Path) -> List[Path]:
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    root = common / "sdd-overlap"
    return sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []


def dirty(cwd: Path) -> List[str]:
    out = git(cwd, "status", "--porcelain", "--untracked-files=all", "--", *PATHSPEC)
    return [line for line in out.splitlines() if line.strip()]


def start(repo: Path, task: str, tree: Optional[str]) -> str:
    if existing(repo):
        raise Refused("a speculation already exists: " + ", ".join(p.name for p in existing(repo)))
    tree = tree or tree_of(repo)
    if git(repo, "cat-file", "-t", tree, check=False).strip() != "tree":
        raise Refused(f"{tree} is not a tree object")
    base = git(repo, "commit-tree", tree, "-p", "HEAD", "-m",
               f"sdd-speculative-base for task {task}").strip()
    path = worktree_path(repo, task)
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "--detach", str(path), base)
    return f"{path} {base}"


def land(repo: Path, task: str, base: str) -> None:
    path = worktree_path(repo, task)
    if not path.is_dir():
        raise Refused(f"no speculation for task {task}")
    if dirty(repo):
        raise Refused("the main checkout is not clean outside .specs/; commit the base task first")
    if git(repo, "diff", "--name-only", base, "HEAD", "--", *PATHSPEC).strip():
        raise Stale("the base task changed after the snapshot; discard and restart this task")
    wip_tree = tree_of(path)
    wip = git(repo, "commit-tree", wip_tree, "-p", base, "-m", f"sdd-speculative work for task {task}").strip()
    git(repo, "cherry-pick", "--no-commit", wip)
    git(repo, "reset", "-q")  # leave M's work as plain working-tree changes, like any executor's
    discard(repo, task)


def discard(repo: Path, task: str) -> None:
    path = worktree_path(repo, task)
    if path.is_dir():
        git(repo, "worktree", "remove", "--force", str(path))
    git(repo, "worktree", "prune")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-overlap.py", description=__doc__.splitlines()[0])
    parser.add_argument("-C", dest="repo", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--task", required=True)
    s.add_argument("--tree")
    l = sub.add_parser("land")
    l.add_argument("--task", required=True)
    l.add_argument("--base", required=True)
    d = sub.add_parser("discard")
    d.add_argument("--task", required=True)
    args = parser.parse_args(argv)
    try:
        repo = Path(git(Path(args.repo), "rev-parse", "--show-toplevel").strip())
        if args.cmd == "start":
            print(start(repo, args.task, args.tree))
        elif args.cmd == "land":
            land(repo, args.task, args.base)
            print(f"landed task {args.task}")
        else:
            discard(repo, args.task)
            print(f"discarded task {args.task}")
        return 0
    except Stale as exc:
        print(f"sdd-overlap: stale: {exc}", file=sys.stderr)
        return 1
    except (Refused, FileNotFoundError) as exc:
        print(f"sdd-overlap: refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
