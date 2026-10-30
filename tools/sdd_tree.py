"""sdd_tree.py — the working tree's IDENTITY for suite records (imported by the SDD tools).

`identity(cwd)` returns a git tree hash over every tracked and untracked, non-ignored file outside
`.specs/`, plus the `.specs/` files the project declares as suite inputs in
`.specs/steering/tech.md`:

    Suite spec inputs: .specs/features/*/design.md, .specs/steering/tech.md

Each entry is a git glob pathspec relative to the repository root and must start with `.specs/`
(everything outside `.specs/` is always covered). Without the line, `.specs/` is excluded whole, so
a spec or state commit never changes the identity. A test that reads a spec file must have that file
listed, or a spec edit can leave a stale suite record.

The hash is read through a TEMPORARY index (a copy of the real one, mtime kept for git's racy-clean
check) from which every `.specs/` entry is removed first: the real index is never touched, and an
already-committed spec file cannot leak into the identity.

Limit: gitignored files (including a listed one) and the installed environment are not covered — a
change to them voids a suite record by declaration, not by hash. Stdlib only.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

OUTSIDE_SPECS = [":/", ":(top,exclude).specs"]
INPUTS_LINE = re.compile(r"^\s*[-*]?\s*\**Suite spec inputs:\**\s*(.+)$", re.I | re.M)


class TreeError(RuntimeError):
    pass


def git(cwd: Path, *args: str, env=None) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise TreeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def spec_inputs(top: Path) -> List[str]:
    """The `Suite spec inputs:` globs from the working tree's steering; each must be under `.specs/`."""
    tech = top / ".specs" / "steering" / "tech.md"
    if not tech.is_file():
        return []
    globs: List[str] = []
    for m in INPUTS_LINE.finditer(tech.read_text(encoding="utf-8", errors="replace")):
        globs += [g.strip().strip("`") for g in m.group(1).split(",") if g.strip().strip("`")]
    bad = [g for g in globs if not g.startswith(".specs/") or ".." in Path(g).parts]
    if bad:
        raise TreeError("Suite spec inputs must be paths under .specs/: " + ", ".join(bad))
    return globs


def identity(cwd: Path) -> str:
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip())
    globs = spec_inputs(top)
    tmp = tempfile.mkdtemp(prefix="sdd-tree-")
    try:
        index = Path(tmp) / "index"
        real = Path(git(top, "rev-parse", "--path-format=absolute", "--git-path", "index").strip())
        if real.is_file():
            shutil.copy2(real, index)  # keep mtime: git's racy-clean check needs it
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        git(top, "rm", "-r", "--cached", "-q", "--ignore-unmatch", "--", ":(top).specs", env=env)
        git(top, "add", "-A", "--", *OUTSIDE_SPECS, env=env)
        if globs:
            # .specs/ is now absent from the index, so every non-ignored file there is "other".
            # Listing first avoids `git add` failing on a glob that matches nothing.
            found = git(top, "ls-files", "-z", "--others", "--exclude-standard", "--",
                        *(f":(top,glob){g}" for g in globs), env=env)
            paths = [p for p in found.split("\0") if p]
            if paths:
                git(top, "add", "--", *(f":(top,literal){p}" for p in paths), env=env)
        return git(top, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
