"""Portable helpers for tests that run shell scripts or check exec bits (macOS, Linux, Windows).

* `BASH` — Git Bash on Windows, found from `git --exec-path`. A bare `bash` on a Windows PATH is
  often `C:\\Windows\\System32\\bash.exe`, the WSL launcher, which runs nothing without a distro.
* `fake_claude(bindir)` — a stub `claude` CLI that `command -v` (POSIX) and `shutil.which`
  (Windows, PATHEXT) both find.
* `is_executable(path)` — the exec bit on POSIX. NTFS has no exec bit (git runs hooks through its
  own sh), so on Windows this is True for an existing file.
* `index_mode(rel)` — the mode git records for a tracked repo file: the portable way to check
  that a script is committed executable (100755).
"""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git_bash():
    if os.name != "nt":
        return shutil.which("bash") or "/bin/bash"
    try:
        exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True,
                                   check=True).stdout.strip()
        for up in range(1, 5):  # .../Git/mingw64/libexec/git-core -> .../Git/bin/bash.exe
            candidate = Path(exec_path).parents[up - 1] / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    except (OSError, subprocess.CalledProcessError, IndexError):
        pass
    found = shutil.which("bash")
    return found if found and "system32" not in found.lower() else None


BASH = _git_bash()


def fake_claude(bindir: Path) -> None:
    shim = bindir / "claude"
    shim.write_text("#!/bin/sh\necho 'fake-claude 0.0.0'\n")
    shim.chmod(0o755)
    if os.name == "nt":
        (bindir / "claude.cmd").write_text("@echo fake-claude 0.0.0\r\n")


def is_executable(path: Path) -> bool:
    if os.name == "nt":
        return Path(path).is_file()
    return bool(os.stat(path).st_mode & 0o111)


def index_mode(rel: str) -> str:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", "--", rel],
                         capture_output=True, text=True, check=True).stdout.split()
    return out[0] if out else ""
