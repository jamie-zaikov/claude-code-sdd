"""settings.json merge for the secret-handling safeguards (deny rules + guard/redact hooks).

Managed hook entries are identified by IDENTITY — the hook script filename appearing in the
entry's `command` or `args` — so any older form (e.g. `python3 ~/.claude/hooks/secret-guard.py`)
is replaced by the current exec-form entry instead of coexisting with it.
"""

import copy
import json
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from .common import InstallError, atomic_write_text

MATCHER = "Bash|PowerShell"

GUARD = "secret-guard.py"
REDACT = "secret-redact.py"
# event -> managed hook script filename
MANAGED_HOOKS = {"PreToolUse": GUARD, "PostToolUse": REDACT}

# Read deny rules. Gitignore-style paths; `~/` is home-relative on every platform and the harness
# normalizes Windows paths to forward slashes, so these forms cover Windows too. The one
# Windows-only entry is gcloud's config dir under %APPDATA% (= ~/AppData/Roaming).
DENY_RULES = [
    "Read(**/.env)", "Read(**/.env.*)", "Read(**/*.pem)", "Read(**/*.key)",
    "Read(**/id_rsa*)", "Read(**/id_ed25519*)", "Read(**/*.p12)", "Read(**/*.pfx)",
    "Read(**/credentials)", "Read(**/service-account*.json)", "Read(**/*.tfvars)",
    "Read(**/kubeconfig)", "Read(**/.netrc)",
    "Read(~/.aws/**)", "Read(~/.ssh/**)", "Read(~/.kube/**)", "Read(~/.config/gcloud/**)",
    "Read(~/AppData/Roaming/gcloud/**)",
]


def hook_entry(python: str, hook_path: Path) -> dict:
    """Exec form: no shell, literal args — absolute paths with spaces need no quoting."""
    return {"type": "command", "command": python, "args": [str(hook_path)]}


def _entry_text(entry) -> List[str]:
    if not isinstance(entry, dict):
        return []
    parts = [entry.get("command")]
    args = entry.get("args")
    if isinstance(args, list):
        parts.extend(args)
    return [p for p in parts if isinstance(p, str)]


def is_managed(entry, script: Optional[str] = None) -> bool:
    """True when the hook entry runs one of our scripts (by filename in command or args)."""
    names = [script] if script else list(MANAGED_HOOKS.values())
    return any(name in text for text in _entry_text(entry) for name in names)


def load(path: Path) -> Tuple[dict, Optional[str]]:
    """Return (settings, original_text). Malformed content raises InstallError; the file is untouched."""
    if not path.exists():
        return {}, None
    try:
        text = path.read_text(encoding="utf-8-sig")  # tolerate a BOM (Windows PowerShell 5.1)
    except OSError as e:
        raise InstallError(f"cannot read {path} ({e}).") from e
    if not text.strip():
        return {}, text
    try:
        data = json.loads(text)
    except ValueError as e:
        raise InstallError(
            f"{path} is not valid JSON ({e}). It was NOT modified. "
            "Fix the JSON (or move the file aside) and re-run."
        ) from e
    if not isinstance(data, dict):
        raise InstallError(f"{path} must hold a JSON object; it was NOT modified.")
    _check_shape(data, path)
    return data, text


def _check_shape(data: dict, path: Path) -> None:
    perms = data.get("permissions", {})
    if not isinstance(perms, dict) or not isinstance(perms.get("deny", []), list):
        raise InstallError(f"{path}: `permissions.deny` must be a list; the file was NOT modified.")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallError(f"{path}: `hooks` must be an object; the file was NOT modified.")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise InstallError(f"{path}: `hooks.{event}` must be a list; the file was NOT modified.")


def _strip_managed(groups: list, script: Optional[str]) -> Tuple[list, Optional[int]]:
    """Remove managed entries from groups. Returns (new_groups, index_of_first_emptied_group)."""
    out = []
    slot = None
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            out.append(group)
            continue
        kept = [h for h in group["hooks"] if not is_managed(h, script)]
        if len(kept) == len(group["hooks"]):
            out.append(group)
            continue
        if kept:
            g = dict(group)
            g["hooks"] = kept
            out.append(g)
        elif slot is None:
            slot = len(out)
    return out, slot


def merge(settings: dict, python: str, hooks_dir: Path) -> Tuple[dict, List[str]]:
    """Return (new_settings, deny_rules_added). The input is not mutated."""
    new = copy.deepcopy(settings)
    deny = new.setdefault("permissions", {}).setdefault("deny", [])
    added = [r for r in DENY_RULES if r not in deny]
    deny.extend(added)
    hooks = new.setdefault("hooks", {})
    # Remove every managed entry from every event first (a stray copy under the wrong event is ours).
    slots = {}
    for event in list(hooks):
        hooks[event], slots[event] = _strip_managed(hooks[event], None)
        if not hooks[event] and event not in MANAGED_HOOKS:
            del hooks[event]
    for event, script in MANAGED_HOOKS.items():
        group = {"matcher": MATCHER, "hooks": [hook_entry(python, hooks_dir / script)]}
        current = hooks.setdefault(event, [])
        slot = slots.get(event)
        # Keep the managed group where it was (idempotent position); new installs append.
        if slot is not None:
            current.insert(slot, group)
        else:
            current.append(group)
    return new, added


def unmerge(settings: dict, deny_owned: List[str]) -> dict:
    """Remove managed hook entries (by identity) and the deny rules this installer added."""
    new = copy.deepcopy(settings)
    hooks = new.get("hooks")
    if isinstance(hooks, dict):
        for event in list(hooks):
            groups, _ = _strip_managed(hooks[event], None)
            if groups:
                hooks[event] = groups
            else:
                del hooks[event]
        if not hooks:
            del new["hooks"]
    perms = new.get("permissions")
    if isinstance(perms, dict) and isinstance(perms.get("deny"), list):
        perms["deny"] = [r for r in perms["deny"] if r not in deny_owned]
        if not perms["deny"]:
            del perms["deny"]
        if not perms:
            del new["permissions"]
    return new


def dumps(settings: dict) -> str:
    return json.dumps(settings, indent=2) + "\n"


def save(path: Path, new: dict, original_text: Optional[str], keep_original: bool = True) -> Optional[Path]:
    """Back up then atomically write. Returns the backup path (None if nothing changed/existed).

    `settings.json.bak` holds the content just before this write; `settings.json.sdd-orig.bak`
    holds the content before the FIRST change this installer ever made (never overwritten).
    """
    text = dumps(new)
    if original_text is not None and text == original_text:
        return None
    backup = None
    if original_text is not None:
        backup = path.with_name(path.name + ".bak")
        orig = path.with_name(path.name + ".sdd-orig.bak")
        try:
            if keep_original and not orig.exists():
                shutil.copy2(path, orig)
            shutil.copy2(path, backup)
        except OSError as e:
            raise InstallError(f"cannot write a backup of {path} ({e}); the file was NOT modified.") from e
    try:
        atomic_write_text(path, text)
    except OSError as e:
        raise InstallError(f"cannot write {path} ({e}); the original file is unchanged.") from e
    return backup
