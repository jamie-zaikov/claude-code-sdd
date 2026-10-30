"""sdd_tree.py — the working tree's IDENTITY for suite records (imported by the SDD tools).

`identity(cwd)` returns a git tree hash over every tracked and untracked, non-ignored file outside
`.specs/`, plus the `.specs/` files the project declares as suite inputs in
`.specs/steering/tech.md`:

    Suite spec inputs: .specs/features/*/design.md, .specs/steering/tech.md

Each entry is a git glob pathspec relative to the repository root, must start with `.specs/`
(everything outside `.specs/` is always covered) and holds no whitespace; each entry
may end in its own `(note)`, which is ignored, and so is a line inside an HTML comment. A malformed entry stops the hash (fail closed). Without the line, `.specs/` is excluded whole, so
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
TECH = ".specs/steering/tech.md"
INPUTS_LINE = re.compile(r"^\s*[-*]?\s*\**Suite spec inputs\**:\**\s*(.+)$", re.I | re.M)
COMMENT = re.compile(r"<!--.*?-->", re.S)
NOTE = re.compile(r"\s*\([^()]*\)\s*$")


class TreeError(RuntimeError):
    pass


def git(cwd: Path, *args: str, env=None) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise TreeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def parse_inputs(text: str) -> List[str]:
    """The `Suite spec inputs:` globs in a tech.md text; each must be a path under `.specs/`."""
    globs: List[str] = []
    for m in INPUTS_LINE.finditer(COMMENT.sub("", text)):
        for entry in m.group(1).split(","):
            entry = NOTE.sub("", entry).strip().strip("`")  # each entry may end in its own "(note)"
            if entry:
                globs.append(entry)
    bad = [g for g in globs if not g.startswith(".specs/") or ".." in Path(g).parts
           or any(c.isspace() for c in g)]
    if bad:
        raise TreeError("Suite spec inputs must be paths under .specs/: " + ", ".join(bad))
    return globs


def spec_inputs(top: Path) -> List[str]:
    """The `Suite spec inputs:` globs from the working tree's steering."""
    tech = top / TECH
    if not tech.is_file():
        return []
    return parse_inputs(tech.read_text(encoding="utf-8", errors="replace"))


def _pathspecs(globs: List[str]) -> List[str]:
    return [f":(top,glob){g}" for g in globs]


def _real_index(top: Path) -> Path:
    return Path(git(top, "rev-parse", "--path-format=absolute", "--git-path", "index").strip())


def snapshot(cwd: Path) -> str:
    """A tree to CHECK OUT (overlap's speculative base): the working tree outside `.specs/`,
    `.specs/` as indexed, and — as they are on disk — the declaration (tech.md) and the spec inputs
    it declares, so the checkout's identity equals the working tree's identity."""
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip())
    globs = spec_inputs(top)
    tmp = tempfile.mkdtemp(prefix="sdd-snap-")
    try:
        index = Path(tmp) / "index"
        real = _real_index(top)
        if real.is_file():
            shutil.copy2(real, index)  # keep mtime: git's racy-clean check needs it
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        git(top, "add", "-A", "--", *OUTSIDE_SPECS, env=env)
        paths = set()
        if (top / TECH).exists() or git(top, "ls-files", "--", f":(top,literal){TECH}", env=env):
            paths.add(TECH)  # the effective declaration, even when its edit is not staged
        if globs:
            found = git(top, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
                        *_pathspecs(globs), env=env)
            paths |= {p for p in found.split("\0") if p}
        if paths:  # -A with a literal path also stages a deletion
            git(top, "add", "-A", "--", *(f":(top,literal){p}" for p in sorted(paths)), env=env)
        return git(top, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _not_ignored(top: Path, paths: List[str]) -> List[str]:
    """Drop paths an ignore rule covers, tracked or not — `identity` never adds them either."""
    if not paths:
        return paths
    proc = subprocess.run(["git", "-C", str(top), "check-ignore", "--no-index", "-z", "--stdin"],
                          input="\0".join(paths) + "\0", capture_output=True, text=True)
    if proc.returncode not in (0, 1):  # 1: none ignored
        raise TreeError(proc.stderr.strip() or "git check-ignore failed")
    ignored = {p for p in proc.stdout.split("\0") if p}
    return [p for p in paths if p not in ignored]


def inputs_at(cwd: Path, rev: str) -> List[str]:
    """The declared spec-input paths of a commit, by that commit's own tech.md."""
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip())
    proc = subprocess.run(["git", "-C", str(top), "show", f"{rev}:.specs/steering/tech.md"],
                          capture_output=True, text=True)
    globs = parse_inputs(proc.stdout) if proc.returncode == 0 else []
    if not globs:
        return []
    tmp = tempfile.mkdtemp(prefix="sdd-inp-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(top, "read-tree", rev, env=env)
        found = git(top, "ls-files", "-z", "--cached", "--", *_pathspecs(globs), env=env)
        return _not_ignored(top, sorted({p for p in found.split("\0") if p}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def identity(cwd: Path) -> str:
    top = Path(git(cwd, "rev-parse", "--show-toplevel").strip())
    globs = spec_inputs(top)
    tmp = tempfile.mkdtemp(prefix="sdd-tree-")
    try:
        index = Path(tmp) / "index"
        real = _real_index(top)
        if real.is_file():
            shutil.copy2(real, index)  # keep mtime: git's racy-clean check needs it
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        # -f: a spec file staged and then edited again must not stop the hash (index-only removal)
        git(top, "rm", "-r", "-f", "--cached", "-q", "--ignore-unmatch", "--", ":(top).specs",
            env=env)
        git(top, "add", "-A", "--", *OUTSIDE_SPECS, env=env)
        if globs:
            # .specs/ is now absent from the index, so every non-ignored file there is "other".
            # Listing first avoids `git add` failing on a glob that matches nothing.
            found = git(top, "ls-files", "-z", "--others", "--exclude-standard", "--",
                        *_pathspecs(globs), env=env)
            paths = [p for p in found.split("\0") if p]
            if paths:
                git(top, "add", "--", *(f":(top,literal){p}" for p in paths), env=env)
        return git(top, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
