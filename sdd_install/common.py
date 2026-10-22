"""Output, prompts, destination resolution, atomic writes and the install manifest."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

MANIFEST_NAME = ".sdd-install-manifest.json"
MANIFEST_VERSION = 1

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(msg: str) -> None:
    print(f"{_c('0;34', '[info]')}  {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"{_c('0;32', '[ok]')}    {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{_c('0;33', '[warn]')}  {msg}", flush=True)


def err(msg: str) -> None:
    print(f"{_c('0;31', '[err]')}   {msg}", flush=True)


def line(msg: str = "") -> None:
    print(msg, flush=True)


class InstallError(Exception):
    """A failure the installer must report with a non-zero exit (never a false success)."""


def ask(prompt: str, default: str = "") -> str:
    """Read one answer from stdin. EOF (no answer available) yields `default`."""
    print(prompt, end="", flush=True)
    try:
        answer = sys.stdin.readline()
    except (OSError, ValueError):
        return default
    if answer == "":  # EOF
        print("", flush=True)
        return default
    return answer.strip()


def yes(answer: str) -> bool:
    return answer in ("y", "Y")


def resolve_claude_home(cli_value: Optional[str]) -> Path:
    """`--claude-home`, else `CLAUDE_CONFIG_DIR`, else `~/.claude` (shared by install and uninstall)."""
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env_value = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path.home() / ".claude").resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def files_equal(a: Path, b: Path) -> bool:
    try:
        return a.is_file() and b.is_file() and sha256_file(a) == sha256_file(b)
    except OSError:
        return False


def copy_file(src: Path, dest: Path, executable: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if executable:
        mode = os.stat(dest).st_mode
        os.chmod(dest, mode | 0o111)


def atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` via a temp file in the same directory and os.replace.

    On any failure the temp file is removed and the original file is left unchanged.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            try:
                shutil.copymode(path, tmp)
            except OSError:
                pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_manifest(claude_home: Path) -> Optional[dict]:
    path = claude_home / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise InstallError(
            f"{path} is not valid JSON ({e}). Fix or delete it, then re-run."
        ) from e
    if not isinstance(data, dict):
        raise InstallError(f"{path} is not a JSON object. Fix or delete it, then re-run.")
    data.setdefault("files", {})
    data.setdefault("deny_added", [])
    data.setdefault("repo_hooks", [])
    return data


def new_manifest() -> dict:
    return {"version": MANIFEST_VERSION, "files": {}, "deny_added": [], "repo_hooks": []}


def save_manifest(claude_home: Path, manifest: dict) -> None:
    manifest["version"] = MANIFEST_VERSION
    atomic_write_text(
        claude_home / MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )


def rel(claude_home: Path, path: Path) -> str:
    """Manifest key: a forward-slash path relative to the destination."""
    return path.relative_to(claude_home).as_posix()
