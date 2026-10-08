#!/usr/bin/env python3
"""sdd-status.py — the specialist status files: one writer per file, one reader (the orchestrator).

Every specialist keeps one small JSON status file for its current invocation:

    .specs/features/<feature>/spec-memory/status/<task>-<agent>-a<attempt>.json

with exactly these keys (see STATES / REQUIRED):

    {"agent": "task-executor", "task": "7", "attempt": 1, "state": "working",
     "step": "7.2 parser", "updatedAt": "2026-10-08T01:14:37Z",
     "verdict": null, "summaryPath": null, "blockedOn": null}

`task` is the task number, or the phase name for a planning agent (`requirements`, `design`, ...).

Subcommands:
  set    write (atomically) a status file — for agents that have Bash. Agents without Bash write
         the same JSON with their Write tool.
  check  validate every status file of a feature and print one line each:
             <file> <state> <step> age=<seconds>s [STALE] [INVALID: reason]
         With --stale-seconds N, a `started`/`working` file older than N seconds is STALE.

Exit codes (check): 0 all valid and none stale, 1 an invalid or stale file, 2 usage error.
Stdlib only.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

STATES = ("started", "working", "blocked", "done", "failed")
LIVE_STATES = ("started", "working")
REQUIRED = ("agent", "task", "attempt", "state", "step", "updatedAt", "verdict", "summaryPath",
            "blockedOn")
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def status_dir(feature_dir: Path) -> Path:
    return feature_dir / "spec-memory" / "status"


def file_name(task: str, agent: str, attempt: int) -> str:
    return f"{task}-{agent}-a{attempt}.json"


def validate(path: Path, record) -> Optional[str]:
    """Return None when the record is valid, else a one-line reason."""
    if not isinstance(record, dict):
        return "not a JSON object"
    missing = [k for k in REQUIRED if k not in record]
    if missing:
        return "missing " + ",".join(missing)
    extra = sorted(set(record) - set(REQUIRED))
    if extra:
        return "unknown key " + ",".join(extra)
    if record["state"] not in STATES:
        return f"state {record['state']!r} not in {'|'.join(STATES)}"
    if not isinstance(record["attempt"], int) or record["attempt"] < 1:
        return "attempt must be an integer >= 1"
    try:
        datetime.strptime(record["updatedAt"], STAMP)
    except (TypeError, ValueError):
        return "updatedAt must be UTC like 2026-10-08T01:14:37Z"
    expected = file_name(str(record["task"]), str(record["agent"]), record["attempt"])
    if path.name != expected:
        return f"file name must be {expected}"
    if record["state"] == "done" and not record["summaryPath"]:
        return "state done needs summaryPath"
    if record["state"] == "blocked" and not record["blockedOn"]:
        return "state blocked needs blockedOn"
    return None


def cmd_set(args) -> int:
    record = {
        "agent": args.agent, "task": str(args.task), "attempt": args.attempt, "state": args.state,
        "step": args.step, "updatedAt": now_utc().strftime(STAMP), "verdict": args.verdict,
        "summaryPath": args.summary_path, "blockedOn": args.blocked_on,
    }
    target_dir = status_dir(Path(args.feature_dir))
    target = target_dir / file_name(record["task"], record["agent"], record["attempt"])
    reason = validate(target, record)
    if reason:
        print(f"sdd-status: refused: {reason}", file=sys.stderr)
        return 2
    target_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=1)
        handle.write("\n")
    os.replace(tmp, target)  # atomic: a reader never sees a half-written file
    print(target)
    return 0


def cmd_check(args) -> int:
    root = status_dir(Path(args.feature_dir))
    if not root.is_dir():
        print(f"sdd-status: no status directory at {root}")
        return 0
    bad = False
    current = now_utc()
    for path in sorted(root.glob("*.json")):
        if args.task is not None and not path.name.startswith(f"{args.task}-"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{path.name} ? ? age=?s INVALID: unreadable ({exc.__class__.__name__})")
            bad = True
            continue
        reason = validate(path, record)
        if reason:
            print(f"{path.name} ? ? age=?s INVALID: {reason}")
            bad = True
            continue
        updated = datetime.strptime(record["updatedAt"], STAMP).replace(tzinfo=timezone.utc)
        age = int((current - updated).total_seconds())
        stale = (args.stale_seconds is not None and record["state"] in LIVE_STATES
                 and age > args.stale_seconds)
        bad = bad or stale
        print(f"{path.name} {record['state']} {record['step']!r} age={age}s"
              + (" STALE" if stale else ""))
    return 1 if bad else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-status.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set", help="write a status file atomically")
    s.add_argument("--feature-dir", required=True)
    s.add_argument("--agent", required=True)
    s.add_argument("--task", required=True)
    s.add_argument("--attempt", type=int, required=True)
    s.add_argument("--state", required=True, choices=STATES)
    s.add_argument("--step", required=True)
    s.add_argument("--verdict")
    s.add_argument("--summary-path")
    s.add_argument("--blocked-on")
    c = sub.add_parser("check", help="validate and list a feature's status files")
    c.add_argument("--feature-dir", required=True)
    c.add_argument("--task")
    c.add_argument("--stale-seconds", type=int)
    args = parser.parse_args(argv)
    return cmd_set(args) if args.cmd == "set" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
