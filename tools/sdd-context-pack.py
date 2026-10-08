#!/usr/bin/env python3
"""sdd-context-pack.py — build one task's context pack: only the spec text the task cites.

    sdd-context-pack.py --feature-dir .specs/features/<f> --task N   -> prints the pack path

Every stage used to read the whole feature folder (thousands of spec lines, megabytes of
spec-memory) for every task. The pack holds exactly:

  * the task block from tasks.md;
  * every requirement the task's `**Requirements:**` line cites — with its sub-requirements —
    from requirements.md;
  * every design section an ID in the `**Design Reference:**` line names (C2, DD-4, I9, ...),
    plus the design lines that cite the task's requirements in a table row;
  * the carry-forward notes that name the task;
  * a NOT FOUND list: any cited ID the extractor could not locate. A non-empty list means the
    reader opens the full document — the pack never hides a gap.

The pack is written to `spec-memory/context/task-<N>.md` with the sha256 of each source, so a
stale pack (a spec amended after it was built) is visible. It is deterministic: the same specs
give the same pack. Exit codes: 0 written, 1 the task is not in tasks.md, 2 usage error. Stdlib only.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

ID = r"[A-Z]{1,4}-?\d+(?:\.\d+)*[a-z]?"
# A block starts at a heading or at a bold lead (`**C1 —`, `- **DD-21 —`).
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_LEAD = re.compile(rf"^\s*(?:[-*]\s+)?\*\*\s*({ID})(?![\w.])")
LEAD_ID = re.compile(rf"^\s*\**\s*({ID})(?!\w|\.\w)")  # `I9.` ends the id; `FR-2.1` does not
# Requirement ids: FR/NFR, and the other prefixes real Requirements lines use (AC-, DOM-, LIM-, ...).
REQ_ID = re.compile(r"\b([A-Z]{2,4}-\d+(?:\.\d+)*)\b")
# Child ranges `FR-9.1–9.3`, `FR-9.1–3`, `FR-9.1–FR-9.3`; parent ranges `FR-15–FR-19`, `FR-15–19`.
RANGE = re.compile(r"\b([A-Z]{2,4}-(\d+))\.(\d+)\s*[–-]\s*(?:[A-Z]{2,4}-)?(?:\d+\.)?(\d+)\b")
PARENT_RANGE = re.compile(r"\b([A-Z]{2,4})-(\d+)\s*[–-]\s*(?:\1-)?(\d+)\b(?!\.)")
DESIGN_ID = re.compile(r"\b((?:[A-Z]{1,3}-\d+|[A-Z]\d+[a-z]?))\b")
# Design ranges `C1–C15`, `C14-C17`, `D1–D5`, `ACC-27–ACC-33`.
DESIGN_RANGE = re.compile(r"\b([A-Z]{1,3}-?)(\d+)\s*[–-]\s*\1?(\d+)\b")
MAX_RANGE = 60  # a longer "range" is a typo or a date, never expanded


def task_block(tasks: str, task: str) -> Optional[str]:
    """The `## Task <N>:` block, up to the next `## Task` heading or a level-1/2 heading."""
    lines = tasks.splitlines(keepends=True)
    start = None
    head = re.compile(rf"^##\s+Task\s+{re.escape(task)}\s*[:.\s—-]")
    in_fence = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
        if in_fence:
            continue
        if start is None and head.match(line):
            start = i
        elif start is not None and re.match(r"^#{1,2}\s", line):
            return "".join(lines[start:i]).rstrip() + "\n"
    return "".join(lines[start:]).rstrip() + "\n" if start is not None else None


def field(block: str, name: str) -> str:
    """The whole `**Name:**` paragraph: the first line and every continuation line, up to the next
    `**Field:**` line, a blank line, a list item, a heading, or a rule."""
    lines = block.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^\*\*{re.escape(name)}:\*\*\s*(.*)$", line)
        if not m:
            continue
        parts = [m.group(1)]
        for nxt in lines[i + 1:]:
            if (not nxt.strip() or re.match(r"^\s*(\*\*[^*]+:\*\*|[-*+]\s|\d+\.\s|#|---)", nxt)):
                break
            parts.append(nxt.strip())
        return " ".join(parts).strip()
    return ""


def _span(lo: str, hi: str):
    lo_n, hi_n = int(lo), int(hi)
    return range(lo_n, hi_n + 1) if 0 <= hi_n - lo_n <= MAX_RANGE else range(0)


def cited_requirements(text: str) -> List[str]:
    ids = set(REQ_ID.findall(text))
    for base, _, lo, hi in RANGE.findall(text):
        ids.update(f"{base}.{n}" for n in _span(lo, hi))
    for prefix, lo, hi in PARENT_RANGE.findall(text):
        ids.update(f"{prefix}-{n}" for n in _span(lo, hi))
    return sorted(ids, key=_id_key)


def cited_design_ids(text: str) -> List[str]:
    ids = {m for m in DESIGN_ID.findall(text)}
    for prefix, lo, hi in DESIGN_RANGE.findall(text):
        ids.update(f"{prefix}{n}" for n in _span(lo, hi))
    return sorted({i for i in ids if not i.startswith(("FR-", "NFR-"))},
                  key=_id_key)


def _id_key(ident: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ident)]


def blocks(doc: str) -> List[Tuple[Optional[str], int, int, int]]:
    """(leading id or None, kind level, start line, end line) for every block. A heading block of
    level L runs to the next heading of level <= L (bold leads and deeper headings stay inside);
    a bold-lead block runs to the next heading or bold lead."""
    lines = doc.splitlines()
    starts = []
    in_fence = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h = HEADING.match(line)
        if h:
            m = LEAD_ID.match(h.group(2))
            starts.append((m.group(1) if m else None, len(h.group(1)), i))
            continue
        b = BOLD_LEAD.match(line)
        if b:
            starts.append((b.group(1), 7, i))  # 7: below every heading level
    out = []
    for n, (ident, level, i) in enumerate(starts):
        end = len(lines)
        for _, lvl, j in starts[n + 1:]:
            if lvl <= level and (level < 7 or lvl <= 7):
                end = j
                break
        out.append((ident, level, i, end))
    return out


def sections_for(doc: str, wanted: List[str], descend: bool) -> Tuple[List[str], List[str]]:
    """Text of every block whose leading id is wanted (or, with descend, a sub-id of one).
    Returns (sections, ids not found). A block already inside a selected block is not repeated."""
    lines = doc.splitlines()
    picked: List[Tuple[int, int]] = []
    found = set()
    for ident, _, start, end in blocks(doc):
        if ident is None:
            continue
        hit = [w for w in wanted if ident == w or (descend and ident.startswith(w + "."))]
        if not hit:
            continue
        found.update(hit)
        if any(s <= start < e for s, e in picked):
            continue
        picked.append((start, end))
    sections = ["\n".join(lines[s:e]).rstrip() for s, e in sorted(picked)]
    # A component defined as a table row (`| C19 | ... |`): the row, under its table header.
    for want in [w for w in wanted if w not in found]:
        row = re.compile(rf"^\|\s*\**{re.escape(want)}\**\s*\|")
        for i, line in enumerate(lines):
            if row.match(line):
                top = i
                while top > 0 and lines[top - 1].lstrip().startswith("|"):
                    top -= 1
                header = lines[top:min(top + 2, i)]
                sections.append("\n".join(header + [line]).rstrip())
                found.add(want)
                break
    return sections, [w for w in wanted if w not in found]


def traceability_rows(doc: str, reqs: List[str]) -> List[str]:
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, reqs)) + r")(?![\w.]|\.\d)") if reqs else None
    rows = []
    for line in doc.splitlines():
        if pattern and line.lstrip().startswith("|") and pattern.search(line):
            rows.append(line.rstrip())
    return rows


def carry_forward(feature: Path, task: str) -> List[str]:
    path = feature / "spec-memory" / "carry-forward.md"
    if not path.is_file():
        return []
    mention = re.compile(rf"\b(?:Task\s+{re.escape(task)}|T{re.escape(task)})(?![\w.])")
    return [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
            if mention.search(line)]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else "absent"


def build(feature: Path, task: str) -> Optional[str]:
    tasks_md = feature / "tasks.md"
    req_md = feature / "requirements.md"
    design_md = feature / "design.md"
    tasks = tasks_md.read_text(encoding="utf-8") if tasks_md.is_file() else ""
    block = task_block(tasks, task)
    if block is None:
        return None
    # The Requirements field, plus every FR/NFR id anywhere in the task block (a sub-task that cites
    # a requirement is a citation too): each one is either packed or listed in NOT FOUND.
    reqs = sorted(set(cited_requirements(field(block, "Requirements")))
                  | {i for i in cited_requirements(block) if i.startswith(("FR-", "NFR-"))},
                  key=_id_key)
    design_ids = cited_design_ids(field(block, "Design Reference"))
    req_doc = req_md.read_text(encoding="utf-8") if req_md.is_file() else ""
    design_doc = design_md.read_text(encoding="utf-8") if design_md.is_file() else ""
    req_sections, req_missing = sections_for(req_doc, reqs, descend=True)
    design_sections, design_missing = sections_for(design_doc, design_ids, descend=False)
    rows = traceability_rows(design_doc, reqs)
    notes = carry_forward(feature, task)
    missing = req_missing + design_missing
    out = [f"# Context pack — Task {task}", "",
           "Built by `sdd-context-pack.py`. Sources (sha256, first 16 hex):",
           f"- tasks.md {sha(tasks_md)}", f"- requirements.md {sha(req_md)}",
           f"- design.md {sha(design_md)}", "",
           "## NOT FOUND — read the full document for these", "",
           ("\n".join(f"- {m}" for m in missing) if missing else "none"), "",
           "## Task", "", block.rstrip(), "",
           f"## Requirements ({', '.join(reqs) or 'none cited'})", ""]
    out += [s + "\n" for s in req_sections] or ["none\n"]
    out += [f"## Design ({', '.join(design_ids) or 'none cited'})", ""]
    out += [s + "\n" for s in design_sections] or ["none\n"]
    out += ["## Design lines that cite these requirements", ""]
    out += rows or ["none"]
    out += ["", "## Carry-forward notes naming this task", ""]
    out += notes or ["none"]
    return "\n".join(out).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sdd-context-pack.py", description=__doc__.splitlines()[0])
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--stdout", action="store_true", help="print the pack instead of writing it")
    args = parser.parse_args(argv)
    feature = Path(args.feature_dir)
    if not feature.is_dir():
        print(f"sdd-context-pack: no feature directory at {feature}", file=sys.stderr)
        return 2
    pack = build(feature, str(args.task))
    if pack is None:
        print(f"sdd-context-pack: Task {args.task} is not in {feature / 'tasks.md'}", file=sys.stderr)
        return 1
    if args.stdout:
        sys.stdout.write(pack)
        return 0
    target = feature / "spec-memory" / "context" / f"task-{args.task}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pack, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
