#!/usr/bin/env python3
"""sdd-findings.py — the feature's one findings index, and the in-attempt repair check.

    .specs/features/<feature>/spec-memory/findings.jsonl     (append-only event log)

One writer: the orchestrator. Specialists keep writing their own reports; the index records each
finding once, with a stable id, and points at the report (`--report`). `.spec-state.json` keeps only
the path and the `counts` output — never the findings themselves.

Subcommands (all take --feature-dir):
  add     --task N --stage S --severity critical|high|medium|low|note --title T
          [--file PATH] [--req ID] [--where PATH:LINE] [--report PATH]
          -> prints the id (F-<task>-<n>). The IDENTITY is (stage, file, req or title) — never a
          line number, which moves. Adding an identity that is already open/routed for the task
          prints the existing id (no duplicate). A closed or invalid identity that reappears is
          REOPENED under its old id.
  route   --id F --to M              the fix site is inside task M's scope; status `routed`
  close   --id F --by EVIDENCE       fixed; EVIDENCE names who verified it (e.g. `7/validator`)
  invalid --id F --by DECISION       the finding itself was wrong, by an independent decision
  list    [--status open,routed,...] [--task N] [--routed-to M] [--min-severity high]
  counts  -> one JSON line: counts by severity and status (for the state file)
  round   --task N --attempt A --ids F-7-1,F-7-3   (empty --ids "" = no blocker left)
          records the blocking set after one check round and prints the repair verdict against the
          previous round of the same task and attempt:
            FIRST     the first round (the starting set)
            CONTINUE  a strict subset, nothing new, every dropped id closed or invalid
            CLEAR     no blocker left (task acceptance still needs every applicable gate)
          A STOP is final for that task and attempt: every later round of it also prints STOP.
            STOP <reason>  not a strict subset, a new or reopened blocker, or a blocker that left
                      without being closed/invalid (deferred, downgraded, or simply missing)
          The comparison never restarts: a new checker invocation or reworded report keeps the ids.

Exit codes: 0 ok (FIRST/CONTINUE/CLEAR), 1 STOP, 2 usage error or unknown id. Stdlib only.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

SEVERITIES = ("critical", "high", "medium", "low", "note")
STATUSES = ("open", "routed", "closed", "invalid")
LOG = "findings.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_path(feature_dir: str) -> Path:
    return Path(feature_dir) / "spec-memory" / LOG


def events(feature_dir: str) -> List[dict]:
    path = log_path(feature_dir)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue  # a torn last line from a crash is skipped, never fatal
    return out


def append(feature_dir: str, event: dict) -> None:
    path = log_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    event["at"] = now()
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def fold(evs: List[dict]) -> Dict[str, dict]:
    """Current view: id -> finding record."""
    view: Dict[str, dict] = {}
    for e in evs:
        kind = e.get("event")
        if kind == "add":
            view[e["id"]] = {k: e.get(k) for k in ("id", "task", "stage", "severity", "title",
                                                     "file", "req", "where", "report")}
            view[e["id"]].update(status="open", routedTo=None, closedBy=None)
        elif e.get("id") in view:
            rec = view[e["id"]]
            if kind == "reopen":
                rec.update(status="open", closedBy=None)
            elif kind == "route":
                rec.update(status="routed", routedTo=e["to"])
            elif kind in ("close", "invalid"):
                rec.update(status="closed" if kind == "close" else "invalid", closedBy=e["by"])
    return view


def identity(task, stage, file, req, title):
    return (str(task), stage, file or "", req or title)


def cmd_add(a, view) -> int:
    ident = identity(a.task, a.stage, a.file, a.req, a.title)
    for rec in view.values():
        if identity(rec["task"], rec["stage"], rec["file"], rec["req"], rec["title"]) == ident:
            if rec["status"] in ("closed", "invalid"):
                append(a.feature_dir, {"event": "reopen", "id": rec["id"]})
                print(f"{rec['id']} REOPENED")
            else:
                print(rec["id"])
            return 0
    n = 1 + sum(1 for rec in view.values() if rec["task"] == str(a.task))
    fid = f"F-{a.task}-{n}"
    append(a.feature_dir, {"event": "add", "id": fid, "task": str(a.task), "stage": a.stage,
                           "severity": a.severity, "title": a.title, "file": a.file,
                           "req": a.req, "where": a.where, "report": a.report})
    print(fid)
    return 0


def cmd_round(a, view, evs) -> int:
    ids = [i for i in (a.ids or "").split(",") if i]
    unknown = [i for i in ids if i not in view]
    if unknown:
        print(f"sdd-findings: unknown id {','.join(unknown)}", file=sys.stderr)
        return 2
    prior = [e for e in evs if e.get("event") == "round" and e.get("task") == str(a.task)
             and e.get("attempt") == a.attempt]
    if any(e.get("verdict") == "STOP" for e in prior):
        print("STOP this attempt already stopped; in-attempt repair never resumes after a STOP")
        return 1
    verdict = verdict_of(set(ids), set(prior[-1]["ids"]) if prior else None, view)
    append(a.feature_dir, {"event": "round", "task": str(a.task), "attempt": a.attempt,
                           "ids": sorted(set(ids)), "verdict": verdict.split()[0]})
    print(verdict)
    return 1 if verdict.startswith("STOP") else 0


def verdict_of(current, previous, view) -> str:
    """The repair verdict for one round against the previous one (None = the first round)."""
    if previous is None:
        return "CLEAR" if not current else "FIRST"
    if not current and not previous:
        return "CLEAR"
    new = sorted(current - previous)
    if new:
        return f"STOP new or reopened blocker(s): {','.join(new)}"
    dropped = previous - current
    unresolved = sorted(i for i in dropped if view[i]["status"] not in ("closed", "invalid"))
    if unresolved:
        return f"STOP blocker(s) left without close/invalid: {','.join(unresolved)}"
    if not dropped:
        return "STOP the blocking set did not shrink"
    return "CLEAR" if not current else "CONTINUE"


def cmd_list(a, view) -> int:
    statuses = set(a.status.split(",")) if a.status else set(STATUSES)
    floor = SEVERITIES.index(a.min_severity) if a.min_severity else len(SEVERITIES) - 1
    for rec in view.values():
        if rec["status"] not in statuses or SEVERITIES.index(rec["severity"]) > floor:
            continue
        if a.task is not None and rec["task"] != str(a.task):
            continue
        if a.routed_to is not None and str(rec["routedTo"]) != str(a.routed_to):
            continue
        where = rec["where"] or rec["file"] or "-"
        extra = f" -> task {rec['routedTo']}" if rec["status"] == "routed" else ""
        print(f"{rec['id']} {rec['severity']} {rec['status']}{extra} {rec['stage']} {where} "
              f"{rec['title']}" + (f" [{rec['report']}]" if rec["report"] else ""))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-findings.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--task", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--severity", required=True, choices=SEVERITIES)
    s.add_argument("--title", required=True)
    for opt in ("--file", "--req", "--where", "--report"):
        s.add_argument(opt)
    s = sub.add_parser("route")
    s.add_argument("--id", required=True)
    s.add_argument("--to", required=True)
    for name in ("close", "invalid"):
        s = sub.add_parser(name)
        s.add_argument("--id", required=True)
        s.add_argument("--by", required=True)
    s = sub.add_parser("list")
    s.add_argument("--status")
    s.add_argument("--task")
    s.add_argument("--routed-to")
    s.add_argument("--min-severity", choices=SEVERITIES)
    sub.add_parser("counts")
    s = sub.add_parser("round")
    s.add_argument("--task", required=True)
    s.add_argument("--attempt", type=int, required=True)
    s.add_argument("--ids", required=True)
    for sp in sub.choices.values():
        sp.add_argument("--feature-dir", required=True)
    a = p.parse_args(argv)
    evs = events(a.feature_dir)
    view = fold(evs)
    if a.cmd == "add":
        return cmd_add(a, view)
    if a.cmd == "round":
        return cmd_round(a, view, evs)
    if a.cmd == "list":
        return cmd_list(a, view)
    if a.cmd == "counts":
        counts: Dict[str, Dict[str, int]] = {"severity": {}, "status": {}}
        for rec in view.values():
            counts["severity"][rec["severity"]] = counts["severity"].get(rec["severity"], 0) + 1
            counts["status"][rec["status"]] = counts["status"].get(rec["status"], 0) + 1
        print(json.dumps(counts, sort_keys=True))
        return 0
    if a.id not in view:
        print(f"sdd-findings: unknown id {a.id}", file=sys.stderr)
        return 2
    if a.cmd == "route":
        append(a.feature_dir, {"event": "route", "id": a.id, "to": str(a.to)})
    else:
        append(a.feature_dir, {"event": a.cmd, "id": a.id, "by": a.by})
    return 0


if __name__ == "__main__":
    sys.exit(main())
