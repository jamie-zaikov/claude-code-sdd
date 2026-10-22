#!/usr/bin/env python3
"""sdd-tree-hash.py — the working tree's identity for suite records and attempt trees.

    sdd-tree-hash.py [-C DIR]   -> prints the tree hash, exit 0

The hash covers every tracked and untracked, non-ignored file outside `.specs/`, read through a
TEMPORARY index (a copy of the real one), so the real index is never touched and a state-file
write under `.specs/` never changes the hash. Run from any directory inside the repository.

Limit: gitignored files and the installed environment are not covered — a change to them voids a
suite record by declaration, not by hash.

Exit codes: 0 hash printed; 2 not a git repository or git error (nothing is printed on stdout, so
an empty hash can never match a recorded one). Stdlib only.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PATHSPEC = [":/", ":(top,exclude).specs"]


def git(cwd: Path, *args: str, env=None) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def tree_hash(cwd: Path) -> str:
    tmp = tempfile.mkdtemp(prefix="sdd-tree-")
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-tree-hash.py", description=__doc__.splitlines()[0])
    parser.add_argument("-C", dest="cwd", default=".", help="directory inside the repository")
    args = parser.parse_args(argv)
    try:
        print(tree_hash(Path(args.cwd)))
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"sdd-tree-hash: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
