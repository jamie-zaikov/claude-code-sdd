#!/usr/bin/env python3
"""sdd-tree-hash.py — the working tree's identity for suite records and attempt trees.

    sdd-tree-hash.py [-C DIR]   -> prints the tree hash, exit 0

The hash covers every tracked and untracked, non-ignored file outside `.specs/`, plus the `.specs/`
files that `tech.md` lists under `Suite spec inputs:` (see `sdd_tree.py`). It is read through a
TEMPORARY index with every `.specs/` entry removed, so the real index is never touched and a spec or
state commit never changes the hash unless a listed file changed. Run from any directory inside the
repository.

Limit: gitignored files and the installed environment are not covered — a change to them voids a
suite record by declaration, not by hash.

Exit codes: 0 hash printed; 2 not a git repository, git error, or a `Suite spec inputs:` entry
outside `.specs/` (nothing is printed on stdout, so an empty hash can never match a recorded one).
Stdlib only.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sdd_tree import TreeError, identity  # noqa: E402


def tree_hash(cwd: Path) -> str:
    return identity(cwd)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-tree-hash.py", description=__doc__.splitlines()[0])
    parser.add_argument("-C", dest="cwd", default=".", help="directory inside the repository")
    args = parser.parse_args(argv)
    try:
        print(tree_hash(Path(args.cwd)))
    except (TreeError, FileNotFoundError) as exc:
        print(f"sdd-tree-hash: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
