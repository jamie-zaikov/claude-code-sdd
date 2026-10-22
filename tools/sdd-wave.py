#!/usr/bin/env python3
"""sdd-wave.py — a two-task wave: two tasks in isolated worktrees, one combined candidate.

    start    --feature F --tasks A,B --attempt K --own A=p1,p2 --own B=p3
    extend   --task A --paths p               (an unowned path joins A's ownership)
    check    --task A                         (read-only; exit 1 on a path outside A's ownership)
    freeze   --task A                         (A's worktree -> a commit under a namespaced ref)
    land                                      (combined candidate -> main checkout, uncommitted)
    snapshot                                  (record the landed checkout before a repair writes)
    unland                                    (main checkout back to base; nothing else touched)
    strays                                    (read-only: changed paths neither task owns)
    verify   --gated-tree T                   (after the commits: HEAD holds what the gates judged)
    adopt    --task A [--patch-out FILE]      (fallback: apply A's frozen work onto the checkout)
    discard  [--drop-refs]   |   prune --feature F   |   status   |   spec-rev --feature-dir D

The base is HEAD at `start`. Worktrees live under `<git-common-dir>/sdd-wave/task-<N>`; the state
file is `<git-common-dir>/sdd-wave/wave.json`. Frozen work, the candidate and every landed snapshot
are commits on the base kept under `refs/sdd-wave/<feature>/w<A>-<B>-a<K>/`, so a fallback never
loses a patch; `freeze` never overwrites a ref; `prune` drops a feature's refs at completion.

`land` builds the candidate with a three-way `read-tree` of base, A and B in a TEMPORARY index (no
integration worktree; the sets are disjoint, so any unmerged path is a conflict) and writes the
changed paths straight into the main checkout from git objects — the real index is never touched.
It refuses when the checkout moved or holds tracked changes outside `.specs/`, and when a path the
candidate adds already exists on disk (tracked, untracked or IGNORED) or sits under a file. The
untracked files present before the land are recorded; `unland` and `verify` never count them.
`unland` restores the union of the candidate's paths and every path a later snapshot shows, so a
repair made after the land is undone too (its work stays in the snapshot ref).

Exit codes: 0 ok; 1 conflict, stale checkout, collision, or ownership/verify failure; 2 refused or
git error. Stdlib only.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

SPEC = [":/", ":(top,exclude).specs"]
ZERO = "0" * 40
ENV_FILES = re.compile(r"(^|/)(pyproject\.toml|setup\.(py|cfg)|requirements[^/]*\.txt|Pipfile(\.lock)?|"
                       r"[^/]*\.lock|package(-lock)?\.json|pnpm-lock\.yaml|go\.(mod|sum)|"
                       r"Cargo\.toml|Gemfile|environment\.ya?ml)$")


class Refused(Exception):
    pass


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sdd_wave_fs import (Failed, collisions, owned, remove, safe_target,  # noqa: E402
                         spec_rev, unsafe_items, unwritable, valid_owned, write_blob)


def git(cwd: Path, *args: str, env=None, check: bool = True, data: Optional[bytes] = None) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, env=env, input=data)
    if check and proc.returncode != 0:
        raise Refused(proc.stderr.decode(errors="replace").strip() or f"git {args[0]} failed")
    return proc.stdout.decode("utf-8", errors="surrogateescape")


def common(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())


def state_path(repo: Path) -> Path:
    return common(repo) / "sdd-wave" / "wave.json"


def load(repo: Path) -> dict:
    path = state_path(repo)
    if not path.is_file():
        raise Refused("no wave exists")
    return json.loads(path.read_text(encoding="utf-8"))


def save(repo: Path, wave: dict) -> None:
    path = state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(wave, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def tree_of(cwd: Path) -> str:
    """Working-tree hash outside `.specs/`, through a temporary index (as sdd-tree-hash.py)."""
    tmp = tempfile.mkdtemp(prefix="sdd-wave-")
    try:
        index = Path(tmp) / "index"
        real = Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-path", "index").strip())
        if real.is_file():
            shutil.copy2(real, index)  # keep mtime: git's racy-clean check needs it
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        git(cwd, "add", "-A", "--", *SPEC, env=env)
        return git(cwd, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def changes(repo: Path, a: str, b: str) -> List[tuple]:
    """(status, mode_b, path) for every path that differs between two tree-ish, renames split."""
    out = git(repo, "diff", "--raw", "--no-renames", "-z", a, b, "--", *SPEC)
    items, fields = [], out.split("\0")
    for i in range(0, len(fields) - 1, 2):
        meta = fields[i].lstrip(":").split()
        if len(meta) >= 5:
            items.append((meta[4], meta[1], fields[i + 1]))
    return items


def tracked_dirty(repo: Path) -> List[str]:
    out = git(repo, "status", "--porcelain", "--untracked-files=no", "--", *SPEC)
    return [line for line in out.splitlines() if line.strip()]


def untracked(repo: Path) -> List[str]:
    out = git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *SPEC)
    return sorted(p for p in out.split("\0") if p)


def prefix(wave: dict) -> str:
    a, b = wave["tasks"]
    return f"refs/sdd-wave/{wave['feature']}/w{a}-{b}-a{wave['attempt']}"


def new_ref(repo: Path, ref: str, commit: str) -> None:
    git(repo, "update-ref", ref, commit, ZERO)  # ZERO old value: refuses to overwrite




SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


# --- commands ---------------------------------------------------------------------------------

def cmd_start(repo: Path, a) -> str:
    if state_path(repo).exists():
        raise Refused("a wave already exists")
    ovl = common(repo) / "sdd-overlap"
    if ovl.is_dir() and any(ovl.iterdir()):
        raise Refused("a Level 1 speculation exists; never run both")
    if tracked_dirty(repo):
        raise Refused("tracked files have uncommitted changes outside .specs/")
    tasks = a.tasks.split(",")
    if len(tasks) != 2 or tasks[0] == tasks[1]:
        raise Refused("a wave has exactly two different tasks")
    if not all(SAFE_ID.match(x) for x in [a.feature, *tasks]):
        raise Refused("feature and task ids must match [A-Za-z0-9][A-Za-z0-9._-]*")
    own: Dict[str, List[str]] = {t: [] for t in tasks}
    for spec in a.own:
        task, _, paths = spec.partition("=")
        if task not in own:
            raise Refused(f"--own names {task}, not a wave task")
        own[task] += [p.strip() for p in paths.split(",") if p.strip()]
    bad = [p for t in own for p in own[t] if not valid_owned(p)]
    if bad:
        raise Refused("invalid ownership entries (plain repo-relative paths only): " + ", ".join(bad))
    casefold = git(repo, "config", "--bool", "core.ignorecase", check=False).strip() == "true"
    wave = {"feature": a.feature, "tasks": tasks, "attempt": a.attempt, "own": own,
            "casefold": casefold, "base": git(repo, "rev-parse", "HEAD").strip(),
            "frozen": {}, "phase": "started", "snapshots": []}
    for path in own[tasks[0]]:  # either side may be a prefix of the other
        if owned(wave, tasks[1], path) or any(owned({**wave, "own": {"x": [path]}}, "x", q)
                                              for q in own[tasks[1]]):
            raise Refused(f"ownership overlaps on {path}")
    for task in tasks:
        wt = common(repo) / "sdd-wave" / f"task-{task}"
        git(repo, "worktree", "add", "--detach", str(wt), wave["base"])
    save(repo, wave)
    return "\n".join(f"{t} {common(repo) / 'sdd-wave' / f'task-{t}'}" for t in tasks) + \
        f"\nbase {wave['base']}"


def cmd_check(repo: Path, wave: dict, task: str) -> List[str]:
    if task not in wave["tasks"]:
        raise Refused(f"task {task} is not in the wave")
    other = [t for t in wave["tasks"] if t != task][0]
    wt = common(repo) / "sdd-wave" / f"task-{task}"
    bad = []
    for status, mode, path in changes(repo, wave["base"], tree_of(wt)):
        if mode == "160000":
            bad.append(f"{path}: submodule change (never wave-safe)")
        elif mode == "120000":
            bad.append(f"{path}: symlink (never wave-safe)")
        elif owned(wave, other, path):
            bad.append(f"{path}: owned by task {other}")
        elif not owned(wave, task, path):
            bad.append(f"{path}: outside task {task}'s ownership"
                       + (" (manifest/lockfile: env-changing, not wave-safe)"
                          if ENV_FILES.search(path) else ""))
    return bad


def cmd_freeze(repo: Path, wave: dict, task: str) -> str:
    if task in wave["frozen"]:
        raise Refused(f"task {task} is already frozen")
    bad = cmd_check(repo, wave, task)
    if bad:
        raise Failed("not frozen; paths outside ownership:\n" + "\n".join(bad))
    wt = common(repo) / "sdd-wave" / f"task-{task}"
    commit = git(repo, "commit-tree", tree_of(wt), "-p", wave["base"], "-m",
                 f"sdd-wave frozen work for task {task}").strip()
    ref = f"{prefix(wave)}/task-{task}"
    new_ref(repo, ref, commit)
    wave["frozen"][task] = ref
    save(repo, wave)
    return f"{ref} {commit}"


def candidate(repo: Path, wave: dict) -> str:
    a, b = (wave["frozen"][t] for t in wave["tasks"])
    tmp = tempfile.mkdtemp(prefix="sdd-wave-idx-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(repo, "read-tree", "-m", "-i", "--aggressive", wave["base"], a, b, env=env)
        unmerged = git(repo, "ls-files", "-u", env=env).strip()
        if unmerged:
            raise Failed("the two tasks conflict:\n" + unmerged)
        tree = git(repo, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    commit = git(repo, "commit-tree", tree, "-p", wave["base"], "-m", "sdd-wave candidate").strip()
    new_ref(repo, f"{prefix(wave)}/candidate", commit)
    return commit


def cmd_land(repo: Path, wave: dict) -> str:
    if wave["phase"] != "started" or len(wave["frozen"]) != 2:
        raise Refused("land needs both tasks frozen and nothing landed")
    if git(repo, "rev-parse", "HEAD").strip() != wave["base"] or tracked_dirty(repo):
        raise Failed("stale: the main checkout moved or has tracked changes outside .specs/")
    cand = candidate(repo, wave)
    items = changes(repo, wave["base"], cand)
    bad = unsafe_items(items) + collisions(repo, items) + unwritable(repo, items)
    if bad:
        raise Failed("not landed (nothing written):\n" + "\n".join(bad))
    wave["preLandUntracked"] = untracked(repo)
    wave["candidate"] = cand
    wave["phase"] = "landing"
    save(repo, wave)  # recorded first: a crash mid-write is recoverable with unland
    for status, mode, path in items:
        remove(repo, path) if status == "D" else write_blob(repo, cand, mode, path)
    wave["phase"] = "landed"
    save(repo, wave)
    return f"candidate {cand}"


def owned_tree(repo: Path, wave: dict) -> str:
    """The base tree with only the wave's OWNED paths taken from disk. User files outside the two
    tasks' ownership are never hashed, so they never land in a long-lived ref. Built entry by entry
    from lists that may be empty (ls-tree, ls-files -o) — never from a pathspec that git can refuse
    (an empty or wholly ignored owned directory must not wedge a snapshot or an unland)."""
    owns = lambda path: any(owned(wave, t, path) for t in wave["tasks"])  # noqa: E731
    paths = {b for b in git(repo, "ls-tree", "-r", "--name-only", "-z", wave["base"]).split("\0")
             if b and owns(b)}
    magic = ":(literal,icase)" if wave.get("casefold") else ":(literal)"
    specs = [magic + o.rstrip("/") for t in wave["tasks"] for o in wave["own"][t]]
    paths |= {u for u in git(repo, "ls-files", "-o", "--exclude-standard", "-z", "--", *specs)
              .split("\0") if u and owns(u)}
    lines = []
    for path in sorted(paths):
        try:
            target = safe_target(repo, path)
        except Failed:
            target = None  # beyond a symlink: git sees no file there
        if target is None or not (target.exists() or target.is_symlink()) or target.is_dir():
            lines.append(f"0 {ZERO}\t{path}")
            continue
        if target.is_symlink():
            data, mode = os.readlink(target).encode("utf-8", "surrogateescape"), "120000"
        else:
            data = target.read_bytes()
            mode = "100755" if os.access(target, os.X_OK) and os.name != "nt" else "100644"
        blob = subprocess.run(["git", "-C", str(repo), "hash-object", "-w", "--stdin"], input=data,
                              capture_output=True, check=True).stdout.decode().strip()
        lines.append(f"{mode} {blob}\t{path}")
    tmp = tempfile.mkdtemp(prefix="sdd-wave-own-")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(repo, "read-tree", wave["base"], env=env)
        if lines:
            git(repo, "update-index", "--index-info", env=env,
                data=("\n".join(lines) + "\n").encode("utf-8", "surrogateescape"))
        return git(repo, "write-tree", env=env).strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_snapshot(repo: Path, wave: dict) -> str:
    if wave["phase"] not in ("landed", "landing"):
        raise Refused("nothing is landed")
    commit = git(repo, "commit-tree", owned_tree(repo, wave), "-p", wave["base"], "-m",
                 "sdd-wave landed snapshot (owned paths only)").strip()
    ref = f"{prefix(wave)}/landed-{len(wave['snapshots']) + 1}"
    new_ref(repo, ref, commit)
    wave["snapshots"].append(ref)
    save(repo, wave)
    return f"{ref} {commit}"


def cmd_unland(repo: Path, wave: dict) -> str:
    snap = cmd_snapshot(repo, wave).split()[1]  # keeps any post-land repair work in a ref
    keep: Set[str] = set(wave.get("preLandUntracked", []))
    paths = {p for _, _, p in changes(repo, wave["base"], wave["candidate"])}
    paths |= {p for _, _, p in changes(repo, wave["base"], snap)}
    base_modes = {}
    for line in git(repo, "ls-tree", "-r", "-z", wave["base"]).split("\0"):
        if line:
            meta, path = line.split("\t", 1)
            base_modes[path] = meta.split()[0]
    skipped: Dict[str, str] = {}
    for path in sorted(paths - keep):
        try:
            safe_target(repo, path)
        except Failed as exc:  # never written through: leave it, report it, never count it below
            skipped[path] = str(exc)
            continue
        if path in base_modes:
            write_blob(repo, wave["base"], base_modes[path], path)
        else:
            remove(repo, path)
    left = {p for _, _, p in changes(repo, wave["base"], owned_tree(repo, wave))} - keep - set(skipped)
    if left:
        raise Failed("unland left changes behind:\n" + "\n".join(sorted(left)))
    wave["phase"] = "started"
    save(repo, wave)
    return f"unlanded; work kept in {wave['snapshots'][-1]}" + \
        ("\nskipped (refused, never written):\n" + "\n".join(skipped.values()) if skipped else "")


def cmd_strays(repo: Path, wave: dict) -> List[str]:
    """Paths changed since the base that NEITHER task owns (and were not untracked before the
    land): a repair out of scope, or a file a user or test run left. Read-only; landed only."""
    if wave["phase"] not in ("landed", "landing"):
        raise Refused("strays is meaningful only while the wave is landed")
    keep = set(wave.get("preLandUntracked", []))
    return sorted(p for _, _, p in changes(repo, wave["base"], tree_of(repo))
                  if p not in keep and not any(owned(wave, t, p) for t in wave["tasks"]))


def cmd_verify(repo: Path, wave: dict, gated: str) -> List[str]:
    keep = set(wave.get("preLandUntracked", []))
    diff = git(repo, "diff", "--name-only", "--no-renames", "-z", gated, "HEAD", "--", *SPEC)
    return sorted(p for p in diff.split("\0") if p and p not in keep)


def cmd_adopt(repo: Path, wave: dict, task: str, patch_out: Optional[str]) -> str:
    ref = wave["frozen"].get(task)
    if not ref:
        raise Refused(f"task {task} has no frozen work")
    if patch_out:
        patch = subprocess.run(["git", "-C", str(repo), "diff", "--binary", wave["base"], ref,
                                "--", *SPEC], capture_output=True, check=True).stdout
        Path(patch_out).write_bytes(patch)  # bytes: no newline translation on Windows
    items = changes(repo, wave["base"], ref)
    if unsafe_items(items) or unwritable(repo, items):
        raise Failed("not adopted:\n" + "\n".join(unsafe_items(items) + unwritable(repo, items)))
    moved = {p for _, _, p in changes(repo, wave["base"], tree_of(repo))}  # HEAD or disk
    bad = sorted({p for _, _, p in items if p in moved} |
                 {c for c in collisions(repo, items) if c.split(" ")[0] not in moved})
    if bad:
        raise Failed("not adopted; these paths changed since the base (use the patch file):\n"
                     + "\n".join(bad))
    commit = git(repo, "rev-parse", ref).strip()
    for status, mode, path in items:
        remove(repo, path) if status == "D" else write_blob(repo, commit, mode, path)
    return f"adopted {ref}"


def cmd_discard(repo: Path, wave: Optional[dict], drop_refs: bool) -> str:
    leftovers = []
    root = common(repo) / "sdd-wave"
    for wt in sorted(root.glob("task-*")) if root.is_dir() else []:
        ok = False
        for _ in range(2):  # Windows: a locked file can fail the first removal
            if subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)],
                              capture_output=True).returncode == 0:
                ok = True
                break
        if not ok:
            leftovers.append(str(wt))
    git(repo, "worktree", "prune", check=False)
    if drop_refs and wave:
        cmd_prune(repo, prefix(wave))
    if state_path(repo).exists():
        state_path(repo).unlink()
    return "discarded" + ("; leftover worktree(s): " + ", ".join(leftovers) if leftovers else "")


def cmd_prune(repo: Path, ref_prefix: str) -> str:
    refs = git(repo, "for-each-ref", "--format=%(refname)", ref_prefix).split()
    for ref in refs:
        git(repo, "update-ref", "-d", ref)
    return f"dropped {len(refs)} ref(s)"




def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-wave.py", description=__doc__.splitlines()[0])
    p.add_argument("-C", dest="repo", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--feature", required=True)
    s.add_argument("--tasks", required=True)
    s.add_argument("--attempt", type=int, required=True)
    s.add_argument("--own", action="append", default=[])
    s = sub.add_parser("extend")
    s.add_argument("--task", required=True)
    s.add_argument("--paths", required=True)
    for name in ("check", "freeze"):
        sub.add_parser(name).add_argument("--task", required=True)
    for name in ("land", "snapshot", "unland", "status", "strays"):
        sub.add_parser(name)
    sub.add_parser("verify").add_argument("--gated-tree", required=True)
    s = sub.add_parser("adopt")
    s.add_argument("--task", required=True)
    s.add_argument("--patch-out")
    sub.add_parser("discard").add_argument("--drop-refs", action="store_true")
    sub.add_parser("prune").add_argument("--feature", required=True)
    sub.add_parser("spec-rev").add_argument("--feature-dir", required=True)
    a = p.parse_args(argv)
    try:
        if a.cmd == "spec-rev":
            print(spec_rev(Path(a.feature_dir)))
            return 0
        repo = Path(git(Path(a.repo), "rev-parse", "--show-toplevel").strip())
        if a.cmd == "start":
            print(cmd_start(repo, a))
        elif a.cmd == "prune":
            if not SAFE_ID.match(a.feature):
                raise Refused("feature id must match [A-Za-z0-9][A-Za-z0-9._-]*")
            print(cmd_prune(repo, f"refs/sdd-wave/{a.feature}/"))
        elif a.cmd == "discard":
            current = load(repo) if state_path(repo).exists() else None
            if current and current["phase"] in ("landed", "landing"):
                raise Refused("the wave is landed; unland first (discard would lose the record)")
            print(cmd_discard(repo, current, a.drop_refs))
        else:
            wave = load(repo)
            if a.cmd == "status":
                print(json.dumps(wave, indent=1, sort_keys=True))
            elif a.cmd == "extend":
                if a.task not in wave["tasks"]:
                    raise Refused(f"task {a.task} is not in the wave")
                other = [t for t in wave["tasks"] if t != a.task][0]
                for path in [x.strip() for x in a.paths.split(",") if x.strip()]:
                    probe = {**wave, "own": {"x": [path]}}
                    if owned(wave, other, path) or any(owned(probe, "x", q)
                                                       for q in wave["own"][other]):
                        raise Refused(f"{path} overlaps task {other}'s ownership; serialize instead")
                    if not valid_owned(path):
                        raise Refused(f"invalid ownership entry {path!r}")
                    wave["own"][a.task].append(path)
                save(repo, wave)
            elif a.cmd in ("check", "verify", "strays"):
                bad = cmd_check(repo, wave, a.task) if a.cmd == "check" else \
                    cmd_verify(repo, wave, a.gated_tree) if a.cmd == "verify" else \
                    cmd_strays(repo, wave)
                print("\n".join(bad) if bad else "ok")
                return 1 if bad else 0
            elif a.cmd == "freeze":
                print(cmd_freeze(repo, wave, a.task))
            elif a.cmd == "land":
                print(cmd_land(repo, wave))
            elif a.cmd == "snapshot":
                print(cmd_snapshot(repo, wave))
            elif a.cmd == "unland":
                if wave["phase"] not in ("landed", "landing"):
                    raise Refused("nothing is landed")
                print(cmd_unland(repo, wave))
            elif a.cmd == "adopt":
                print(cmd_adopt(repo, wave, a.task, a.patch_out))
    except Failed as exc:
        print(f"sdd-wave: {exc}", file=sys.stderr)
        return 1
    except (Refused, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"sdd-wave: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
