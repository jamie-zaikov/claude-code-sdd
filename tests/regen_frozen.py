#!/usr/bin/env python3
"""Regenerate the frozen span fixtures in tests/frozen/.

`tests/frozen/REGENERATE.md` referenced this script before it existed — a dangling instruction,
which matters because these freezes are now the only pins protecting the shipped behaviour.

A freeze is deliberate friction. Running this makes a RED test green, so it is only correct after
a deliberate contract change. State in the commit message WHICH span moved and WHY; regenerating
without that defeats the mechanism entirely.

Usage:
    python3 tests/regen_frozen.py            # show what would change
    python3 tests/regen_frozen.py --write    # rewrite the fixtures
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_non_code_contracts import SPANS, FROZEN, between  # noqa: E402


def main():
    write = "--write" in sys.argv
    changed = 0
    for name, path, start, end, _why in SPANS:
        current = between(path, start, end)
        target = FROZEN / name
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        if existing == current:
            print(f"  unchanged  {name}")
            continue
        changed += 1
        print(f"  CHANGED    {name}  ({path.name})")
        if write:
            target.write_text(current, encoding="utf-8")
    if changed and not write:
        print(f"\n{changed} span(s) differ. Re-run with --write to accept, and say which and why "
              "in the commit message.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
