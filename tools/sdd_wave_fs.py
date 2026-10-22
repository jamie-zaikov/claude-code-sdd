"""sdd_wave_fs.py — the file-system side of sdd-wave.py: every write it makes into a checkout.

Every write goes through `safe_target`, which refuses `..`, absolute paths, and any symlink on a
parent component — checked at write time, so a link an earlier write in the same land created is
caught too — and any path that resolves outside the checkout. Stdlib only.
"""

import os
import stat
import subprocess
from pathlib import Path
from typing import Dict, List


class Failed(Exception):
    pass


def safe_target(repo: Path, path: str) -> Path:
    """The on-disk path for a repo-relative path, refusing any write that could leave the checkout:
    no `..`, no absolute path, and no symlink on any parent component — checked at write time, so a
    link an earlier write in the same land created is caught too."""
    parts = path.split("/")
    if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise Failed(f"unsafe path {path!r}")
    current = repo
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise Failed(f"refused: {path} is under the symlink {current.relative_to(repo).as_posix()}")
    target = repo / path
    root = os.path.realpath(repo)
    if os.path.commonpath([root, os.path.realpath(target.parent)]) != root:
        raise Failed(f"refused: {path} resolves outside the checkout")
    return target


def unsafe_items(items: List[tuple]) -> List[str]:
    """Symlinks are never wave-safe, and two paths that differ only in case (or a file and a
    directory that do) would alias on a case-insensitive filesystem."""
    bad = [f"{path} (symlink)" for _, mode, path in items if mode == "120000"]
    seen: Dict[str, str] = {}
    for _, _, path in items:
        parts = path.casefold().split("/")
        for depth in range(1, len(parts) + 1):
            key = "/".join(parts[:depth])
            real = "/".join(path.split("/")[:depth])
            if seen.setdefault(key, real) != real:
                bad.append(f"{path} (case-collides with {seen[key]})")
                break
    return bad


def write_blob(repo: Path, commit: str, mode: str, path: str) -> None:
    target = safe_target(repo, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", f"{commit}:{path}"],
                          capture_output=True, check=True).stdout
    if target.is_symlink() or target.exists():
        target.unlink()
    if mode == "120000" and os.name != "nt":
        os.symlink(data.decode("utf-8", errors="surrogateescape"), target)
        return
    target.write_bytes(data)  # Windows without symlinks: link text, as git does
    if mode == "100755":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def remove(repo: Path, path: str) -> None:
    target = safe_target(repo, path)
    if target.is_symlink() or target.is_file():
        target.unlink()


def collisions(repo: Path, items: List[tuple]) -> List[str]:
    bad = []
    for status, _, path in items:
        if status == "A":
            target = repo / path
            if target.exists() or target.is_symlink():
                bad.append(f"{path} (already on disk)")
            parent = target.parent
            while parent != repo:
                if parent.exists() and not parent.is_dir():
                    bad.append(f"{path} (under the file {parent.relative_to(repo).as_posix()})")
                parent = parent.parent
    return bad
