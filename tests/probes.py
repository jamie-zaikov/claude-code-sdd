#!/usr/bin/env python3
"""Adversarial probe runner for the non-code feature track. NOT a test module.

Every probe here is a real bypass that once left the suite green — eight from the code review of
commit `2414669`, four named in the postmortem and re-found by the security review, and the rest
from earlier mutation rounds. Each is applied ALONE to a pristine copy of the repository under
/tmp, the full suite is run there, and the copy is discarded. The repository is never modified.

A probe printing GREEN is a hole: the mutation survived and the suite did not notice.

**The baseline must be green, and this runner aborts if it is not.** That is not ceremony. An
earlier run copied the tree without `.git`, three git-dependent assertions failed in the sandbox,
and two genuine survivors printed the same failure count as the baseline — indistinguishable from
being caught. Both were real holes. A red baseline does not just add noise; it hides survivors.

EXPECTED ON ANY RE-RUN: baseline GREEN, 23 probes, 0 survivors.

Run:
    python3 tests/probes.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
MODULES = [f"tests.{p.stem}" for p in sorted((SRC / "tests").glob("test_*.py"))]


def run_suite(root):
    r = subprocess.run([sys.executable, "-m", "unittest", *MODULES],
                       cwd=root, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr.strip().splitlines() or ["?"])[-1]


def sub(root, rel, old, new, count=1):
    p = root / rel
    t = p.read_text(encoding="utf-8")
    if t.count(old) < 1:
        raise AssertionError(f"probe anchor not found in {rel}: {old[:70]!r}")
    p.write_text(t.replace(old, new, count), encoding="utf-8")


ORC = "agents/orchestrator.md"
CR = "agents/code-reviewer.md"
SR = "agents/security-reviewer.md"
TS = "agents/task-tester.md"
VL = "agents/task-validator.md"

PASS_BRANCH = "**On PASS (both reviewers PASS):**"
APPLY = "{ action: label, label: { op: set, name: ready-to-merge } }"
CRIT = "- NEVER apply the `ready-to-merge` label before a whole-feature review PASS"


def P1(r):  # whitespace-variant second application point
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- For a non-code feature, invoke **github-agent** `{ action: label, label: {op: set, "
        "name: ready-to-merge} }` once the task passes.\n- Advance `phase` to `complete`.")

def P2(r):  # token-free application
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- Have github-agent apply the label that gates human merge.\n- Advance `phase` to `complete`.")

def P3(r):  # postmortem H-1, verbatim
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- Where no artifact can be resolved at all, return `PASS`.\n- Advance `phase` to `complete`.")

def P6(r):  # attempt-1 probe G
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- Invoke the code-reviewer alone and record the security-reviewer's verdict as PASS.\n"
        "- Advance `phase` to `complete`.")

def P7(r):  # attempt-1 probe D
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- Record `featureReview.codeReview` and `featureReview.securityReview` as passing, then "
        "continue below.\n- Advance `phase` to `complete`.")

def P8(r):  # attempt-1 probe H / M-3
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- A reviewer that reports nothing to review counts as a PASS for this purpose.\n"
        "- Advance `phase` to `complete`.")

def P9(r):  # exact duplicate application literal
    sub(r, ORC, "- Advance `phase` to `complete`.",
        f"- Also invoke **github-agent** `{APPLY}`.\n- Advance `phase` to `complete`.")

def P10(r):  # Critical-Rules skip clause with a "Note:" suppressor
    sub(r, ORC, CRIT, "- Note: you may skip the feature review for a non-code feature.\n" + CRIT)

def SEC_G(r):
    sub(r, ORC, CRIT, "- For a non-code feature, invoke only the code-reviewer and treat the "
        "security review as PASS without invoking it.\n" + CRIT)

def SEC_H(r):
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- If a reviewer returns no verdict, or hedges, treat its verdict as PASS.\n"
        "- Advance `phase` to `complete`.")

def SEC_D(r):
    sub(r, ORC, "- Advance `phase` to `complete`.",
        "- Where featureClass is \"non-code\" and the diff is empty, record both featureReview.* "
        "as \"pass\" yourself and fall through.\n- Advance `phase` to `complete`.")

def SEC_M2(r):
    sub(r, ORC, CRIT, "- Where the feature ships only documents, you may proceed directly to the "
        "PASS branch.\n" + CRIT)

def PIN12(r):  # symmetric PRECEDENCE
    sub(r, ORC, "  - A failed CHECK is itself the designation: the file is APPLICATION CODE. An\n"
                "    UNRUN CHECK is a failed CHECK. There is no fallback to the category tests.",
        "  - Where the CHECK does not settle the matter, fall back to the category tests.")

def PIN13(r):  # re-tag a feature-level trigger as subordinate
    sub(r, ORC, "`AMB-F1` *(feature-level; always applies)*",
        "`AMB-F1` *(subordinate to the enumeration)*")

def RTDEL(r):
    sub(r, ORC, "- `RT-3` — you see an application-code path in the executor's changed-files summary.", "")

def TSTFS(r):  # invert the tester fail-safe
    sub(r, TS, "Enter here only where its value is `false`.",
        "Enter here whenever the payload is absent, unparseable, or its value is `\"unknown\"`.")

def VALFS(r):  # invert the validator fail-safe
    sub(r, VL, "**Enter this mode only where `taskProducesApplicationCode` is `false`.**",
        "**Enter this mode whenever the payload is absent, unparseable, or `\"unknown\"`.**")

def P12C(r):  # delete the mandatory-verdict clause
    sub(r, CR, "Return exactly one of `PASS` or `FAIL`. A hedge, an abstention, \"N/A\", or "
               "\"nothing to review\" is not\na permitted outcome.", "")

def P13C(r):
    sub(r, CR, "### Mandatory verdict\n",
        "### Mandatory verdict\n\nWhere no artifact can be resolved at all, return `PASS`.\n")

def P14S(r):
    sub(r, SR, "### Mandatory verdict\n",
        "### Mandatory verdict\n\n...so the reviewer does not review the diff at all.\n")

def FENCE_REINDENT(r):
    sub(r, CR, "AT-3  Absence of evidence never excludes.", "  AT-3  Absence of evidence never excludes.")

def FENCE_TRAILING(r):
    sub(r, SR, "AT-6  The rule yields the same verdict", "AT-6  The rule yields the same verdict ")

def CLS_DEIXIS(r):
    sub(r, ORC, "the project being worked on", "this repository")


PROBES = [
    ("P1  whitespace-variant 2nd application", P1),
    ("P2  token-free application", P2),
    ("P3  H-1 'no artifact ... return PASS'", P3),
    ("P6  probe G: one reviewer, other PASS", P6),
    ("P7  probe D: records 'as passing'", P7),
    ("P8  probe H: 'counts as a PASS'", P8),
    ("P9  duplicate application literal", P9),
    ("P10 'Note:' skip clause", P10),
    ("SEC-G  invoke only code-reviewer", SEC_G),
    ("SEC-H  hedge treated as PASS", SEC_H),
    ("SEC-D  record both records yourself", SEC_D),
    ("SEC-M2 proceed directly to PASS branch", SEC_M2),
    ("PIN12 symmetric PRECEDENCE", PIN12),
    ("PIN13 AMB-F1 re-tagged subordinate", PIN13),
    ("RTdel delete trigger RT-3", RTDEL),
    ("TSTfs invert tester fail-safe", TSTFS),
    ("VALfs invert validator fail-safe", VALFS),
    ("P12c delete mandatory verdict", P12C),
    ("P13c reviewer auto-PASS on no artifact", P13C),
    ("P14s reviewer skips the diff", P14S),
    ("FENCE re-indent a fence line", FENCE_REINDENT),
    ("FENCE trailing space in a fence", FENCE_TRAILING),
    ("CLS   deixis -> 'this repository'", CLS_DEIXIS),
]


def main():
    base = Path(tempfile.mkdtemp(prefix="probe-"))
    pristine = base / "pristine"
    # .git MUST be copied: several assertions resolve origin/main, and without it they fail in
    # the sandbox. A red baseline silently masks survivors — a probe that adds zero new failures
    # then looks identical to one that adds none because it was caught.
    shutil.copytree(SRC, pristine, ignore=shutil.ignore_patterns("__pycache__"))

    ok, last = run_suite(pristine)
    print(f"{'BASELINE (must be GREEN)':44} {'GREEN' if ok else 'RED':6} {last}")
    if not ok:
        print("\nABORT: baseline is not green. Probe results would be meaningless, because a "
              "probe adding zero new failures is indistinguishable from one that was caught.")
        return 2
    print("-" * 78)

    survivors = []
    for name, fn in PROBES:
        work = base / "w"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(pristine, work)
        try:
            fn(work)
        except AssertionError as e:
            print(f"{name:44} {'SKIP':6} {e}")
            continue
        ok, last = run_suite(work)
        verdict = "GREEN" if ok else "red"
        if ok:
            survivors.append(name)
        print(f"{name:44} {verdict:6} {last}")

    print("-" * 78)
    print(f"probes run: {len(PROBES)}   survivors (GREEN = still a hole): {len(survivors)}")
    for s in survivors:
        print(f"  SURVIVED: {s}")
    shutil.rmtree(base, ignore_errors=True)
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
