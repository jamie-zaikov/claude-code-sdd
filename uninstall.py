#!/usr/bin/env python3
"""SDD Global Uninstaller for Claude Code (stdlib only, Python >= 3.9).

Removes only what the installer owns:
  * files it copied, as recorded in the install manifest — a file the user changed since
    (its hash differs) is KEPT and reported;
  * its settings.json entries — the guard/redact hooks (by identity) and the deny rules it added.
Without a manifest (an install made by the old install.sh) it falls back to removing files whose
content is identical to this checkout's copy, and keeps (and reports) the deny rules.
CLAUDE.md, settings backups and repo pre-push hooks are always kept and reported.

Destination: --claude-home PATH, else $CLAUDE_CONFIG_DIR, else ~/.claude (shared with install).
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sdd_install import MIN_PYTHON  # noqa: E402
from sdd_install import settings as sdd_settings  # noqa: E402
from sdd_install.common import (  # noqa: E402
    MANIFEST_NAME, InstallError, ask, err, files_equal, info, line, load_manifest, ok,
    sha256_file, warn, yes, resolve_claude_home,
)

# Source dirs whose files the installer copies (used for the no-manifest fallback).
SOURCES = (
    ("agents", "agents", "*.md"),
    ("commands", "commands", "*.md"),
    ("playbooks", "playbooks", "*.md"),
    ("tools", "tools", "*.py"),
    ("hooks", "hooks", "secret-*.py"),
)


def parse_args(argv):
    p = argparse.ArgumentParser(description="Uninstall the SDD framework from Claude Code.")
    p.add_argument("--claude-home", help="destination (default: $CLAUDE_CONFIG_DIR or ~/.claude)")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    return p.parse_args(argv)


def planned_files(home: Path, manifest):
    """[(path, expected_sha_or_source_path)] for files the installer owns."""
    if manifest is not None:
        return [(home / relpath, digest) for relpath, digest in sorted(manifest["files"].items())]
    out = []
    for src_sub, dest_sub, pattern in SOURCES:
        for src in sorted((ROOT / src_sub).glob(pattern)):
            out.append((home / dest_sub / src.name, src))
    return out


def owned_now(path: Path, expected) -> bool:
    if isinstance(expected, Path):
        return files_equal(expected, path)
    try:
        return sha256_file(path) == expected
    except OSError:
        return False


def remove_settings(home: Path, manifest) -> list:
    """Remove managed settings entries. Raises InstallError (nothing removed) on bad settings."""
    path = home / "settings.json"
    kept_notes = []
    current, original = sdd_settings.load(path)
    if original is None:
        return kept_notes
    deny_owned = manifest["deny_added"] if manifest is not None else []
    new = sdd_settings.unmerge(current, deny_owned)
    backup = sdd_settings.save(path, new, original, keep_original=False)
    if backup:
        ok(f"Removed SDD hook entries and owned deny rules from {path} (backup: {backup.name}).")
    else:
        info(f"No SDD entries found in {path}.")
    leftover = [r for r in new.get("permissions", {}).get("deny", []) if r in sdd_settings.DENY_RULES]
    if leftover:
        why = ("they existed before the SDD install" if manifest is not None
               else "no install manifest, so ownership is unknown")
        kept_notes.append(f"{len(leftover)} secret-store deny rule(s) in settings.json ({why})")
    return kept_notes


def main(argv=None) -> int:
    if sys.version_info < MIN_PYTHON:
        err(f"Python {'.'.join(map(str, MIN_PYTHON))}+ is required.")
        return 1
    args = parse_args(sys.argv[1:] if argv is None else argv)
    home = resolve_claude_home(args.claude_home)
    line("\nSDD Global Uninstaller\n======================\n")
    try:
        manifest = load_manifest(home)
    except InstallError as e:
        err(str(e))
        return 1
    plan = [(p, exp) for p, exp in planned_files(home, manifest) if p.exists()]
    line(f"This removes SDD files and settings entries from {home}/\n")
    if manifest is None:
        warn("No install manifest found (old install.sh install): only files identical to this "
             "checkout are removed.")
    for path, _ in plan:
        line(f"    - {path.relative_to(home).as_posix()}")
    line()
    if not args.yes and not yes(ask("Continue? (y/N) ", "n")):
        return 0

    # Settings first: if they cannot be updated, delete nothing — removing the hook scripts while
    # settings still reference them would leave hooks pointing at missing files.
    try:
        kept = remove_settings(home, manifest)
    except InstallError as e:
        err(str(e))
        err("Uninstall aborted; no files were removed.")
        return 1

    removed = 0
    for path, expected in plan:
        if owned_now(path, expected):
            path.unlink()
            removed += 1
        else:
            kept.append(f"{path.relative_to(home).as_posix()} (changed since install)")
    for sub in ("ci-templates/workflows", "ci-templates/hooks", "ci-templates/scripts",
                "ci-templates", "hooks", "tools", "playbooks", "commands", "agents"):
        d = home / sub
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass
    manifest_path = home / MANIFEST_NAME
    if manifest_path.exists():
        manifest_path.unlink()
    ok(f"Removed {removed} SDD file(s).")

    if (home / "CLAUDE.md").exists():
        kept.append("CLAUDE.md (remove the SDD instructions manually if you no longer need them)")
    for name in ("settings.json.bak", "settings.json.sdd-orig.bak"):
        if (home / name).exists():
            kept.append(f"{name} (settings backup)")
    for hook in (manifest or {}).get("repo_hooks", []):
        if Path(hook).exists():
            kept.append(f"repo pre-push hook {hook}")
    if kept:
        line("\nKept (not removed):")
        for k in kept:
            line(f"    - {k}")
    line()
    return 0


if __name__ == "__main__":
    sys.exit(main())
