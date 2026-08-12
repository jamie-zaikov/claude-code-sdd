#!/usr/bin/env python3
"""Classify a feature as code-bearing or non-code, from what its tasks declare they produce.

This replaces the `CLS` block, its asymmetric `PRECEDENCE` stanza and its `CHECK` — roughly fifty
lines of prose an agent had to follow correctly, plus a verbatim freeze and eight semantic pins
holding that prose in place.

**Why it is code and not prose.** The prose version was correct and unenforceable. Its tests could
only grep for wording, so they proved the paragraph existed, never that it ran — which is exactly
how the classification gate shipped uninvoked with a green suite. Here the classification is a
function with inputs and outputs: it can be tested with real `tasks.md` content, and "did it run?"
is answered by whether `featureClass` is in the state file, not by reading a contract.

**The asymmetry is preserved, because it is the whole safety property.** Application code settles
unconditionally. Non-code settles only if the designation check runs and passes. A failed check —
or one that could not run — designates application code. Every uncertain path leads to `"code"`,
which is today's behaviour, so the failure direction is always toward more checking.

Usage:
    python3 scripts/classify_feature.py <feature-name>                 # classify a feature
    python3 scripts/classify_feature.py <feature-name> --paths a b c   # classify a reviewer's diff

Emits JSON on stdout:
    {"featureClass": "code"|"non-code", "basis": [...], "ambiguity": [...]}

Exit status is 0 whenever a classification was produced, including `"code"`. A non-zero status
means the classification could not be made at all — never that the answer was `"code"`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- The application-code side. Named here, settles UNCONDITIONALLY. --------------------------
# Illustrative, not exhaustive: a path's absence from this list is evidence of nothing, and the
# designation check below still has to pass before anything is called non-code.
APPLICATION_CODE_SUFFIXES = (
    ".py", ".sh", ".bash", ".js", ".ts", ".rb", ".go", ".rs", ".java", ".c", ".h", ".cpp",
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".sql",
)
APPLICATION_CODE_DIRS = (
    "agents/", "commands/", "hooks/", "scripts/", "tests/", "test/", "ci-templates/",
    ".github/workflows/", "src/", "lib/",
)
# Locations a tool reads as agent instructions BY CONVENTION. Silence is not an exemption here:
# an undesignated file in one of these is application code even though nothing names it.
CONVENTIONAL_INSTRUCTION_DIRS = (
    ".github/", ".cursor/", ".windsurf/", "prompts/", "rules/", ".claude/",
)
# Credential stores. An import into one of these is a FAILED check, never a skipped one.
CREDENTIAL_HINTS = (".env", "credentials", "secret", ".pem", ".key", "tfvars", "kubeconfig")

VAULT_LOG = "vault/.write-log.jsonl"

CODE = "code"
NON_CODE = "non-code"


def _feature_dir(feature: str) -> str:
    return f".specs/features/{feature}/"


def classify_path(path: str, feature: str, designations: str) -> tuple[str, str]:
    """Classify one declared output. Returns (class, reason).

    `designations` is the concatenated text of the worked project's root `CLAUDE.md`, the files it
    imports, and `.specs/steering/*.md` — the corpus the designation check reads.
    """
    p = path.strip().strip("`")
    # Strip a leading "./" as a PREFIX, not as a character set. `lstrip("./")` removes every
    # leading "." and "/", which turned ".github/copilot-instructions.md" into
    # "github/copilot-instructions.md" and slipped it past the conventional-location check below —
    # classifying a live agent-instruction file as non-code.
    if p.startswith("./"):
        p = p[2:]

    # APPLICATION CODE, unconditionally. Checked first: the precedence is asymmetric on purpose.
    if any(p.startswith(d) for d in APPLICATION_CODE_DIRS):
        return CODE, f"under {next(d for d in APPLICATION_CODE_DIRS if p.startswith(d))}"
    if p.endswith(APPLICATION_CODE_SUFFIXES):
        return CODE, f"{Path(p).suffix} is executable/config"

    # FEATURE-DIRECTORY RULE. Anything under the feature's own directory that is not application
    # code settles as a non-code artifact WITHOUT the check. The check cannot be used here: every
    # project loads the feature directory into an agent's context, so it would always fail and
    # would designate the feature's own requirements.md — and its recon write-up — as code.
    if p.startswith(_feature_dir(feature)):
        return NON_CODE, "under the feature directory (settles without the check)"
    if p.endswith(VAULT_LOG):
        return NON_CODE, "knowledge-vault changelog"

    # Conventional instruction locations: application code even when nothing designates them.
    if any(p.startswith(d) for d in CONVENTIONAL_INSTRUCTION_DIRS):
        return CODE, f"in a conventional agent-instruction location ({p.split('/')[0]}/)"

    # THE DESIGNATION CHECK. Fails if the project designates the file a behaviour-bearing contract
    # or loads it into an agent's context. Fails if it names a credential store. A failure — or an
    # inability to run — designates APPLICATION CODE, with no fallback to the category tests.
    if designations is None:
        return CODE, "designation check could not run (unrun check is a failed check)"
    if any(h in p.lower() for h in CREDENTIAL_HINTS):
        return CODE, "path resembles a credential store; check refuses to follow it"
    if p in designations:
        return CODE, "the project designates this file / loads it into agent context"

    if p.endswith((".md", ".rst", ".txt", ".adoc")):
        return NON_CODE, "committed prose the project does not designate as a contract"

    return CODE, "unresolved by the check (AMB-C1)"


def parse_declared_outputs(tasks_md: str) -> list[tuple[int, list[str]]]:
    """Return [(task_number, [declared paths])] from a tasks.md.

    Reads the `**Files:**` declaration under each numbered task heading. A task with a heading and
    no declaration yields an empty list, which is `AMB-F1` and is handled by the caller.
    """
    out: list[tuple[int, list[str]]] = []
    current: int | None = None
    for line in tasks_md.splitlines():
        m = re.match(r"^#+\s*(?:Task\s*)?(\d+)[.:)]?\s", line.strip())
        if m:
            current = int(m.group(1))
            out.append((current, []))
            continue
        if current is not None and line.strip().startswith("**Files:**"):
            paths = re.findall(r"`([^`]+)`", line)
            if not paths:  # declared, but not in backticks
                rest = line.split("**Files:**", 1)[1]
                paths = [x.strip() for x in re.split(r"[,;]", rest) if x.strip()]
            out[-1] = (current, paths)
    return out


def classify_feature(tasks_md: str, feature: str, designations: str = "") -> dict:
    """Classify a whole feature. Every uncertain path resolves to `"code"`."""
    tasks = parse_declared_outputs(tasks_md)
    ambiguity: list[str] = []
    basis: list[dict] = []

    if not tasks:
        return {"featureClass": CODE, "basis": [],
                "ambiguity": ["AMB-F2: tasks.md declares no tasks"]}

    feature_class = NON_CODE
    for number, paths in tasks:
        if not paths:
            ambiguity.append(f"AMB-F1: task {number} declares no outputs")
            feature_class = CODE
            basis.append({"task": number, "declaredOutputs": [], "class": CODE,
                          "reasons": ["no declared outputs"]})
            continue
        classes, reasons = [], []
        for path in paths:
            cls, why = classify_path(path, feature, designations)
            classes.append(cls)
            reasons.append(f"{path.strip().strip('`')}: {cls} — {why}")
        task_class = CODE if CODE in classes else NON_CODE
        if task_class == CODE:
            feature_class = CODE
        basis.append({"task": number, "declaredOutputs": paths, "class": task_class,
                      "reasons": reasons})

    return {"featureClass": feature_class, "basis": basis, "ambiguity": ambiguity}


def classify_paths(paths, feature: str, designations: str) -> dict:
    """Classify an arbitrary set of paths — a reviewer's diff — with the same rules.

    Returns the per-path classification and whether the set as a whole is a non-code diff. A diff
    holding even ONE application-code path is not a non-code diff: the reviewer must run its
    ordinary hunt. That is the fail-safe direction, and it is the same asymmetry `classify_path`
    applies to a single file.
    """
    results = []
    for path in paths:
        cls, why = classify_path(path, feature, designations)
        results.append({"path": path, "class": cls, "reason": why})
    non_code = bool(results) and all(r["class"] == NON_CODE for r in results)
    return {"nonCodeDiff": non_code, "paths": results}


def read_designations(repo: Path) -> str:
    """Concatenate the corpus the designation check reads. Returns None if it cannot be read."""
    parts = []
    claude = repo / "CLAUDE.md"
    if claude.is_file():
        parts.append(claude.read_text(encoding="utf-8"))
    steering = repo / ".specs" / "steering"
    if steering.is_dir():
        for f in sorted(steering.glob("*.md")):
            parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts) if parts else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("feature", nargs="?", help="feature name under .specs/features/")
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    ap.add_argument("--paths", nargs="+", metavar="PATH",
                    help="classify these paths instead of a feature's tasks.md (reviewer mode)")
    args = ap.parse_args(argv)

    if not args.feature:
        ap.error("a feature name is required")

    if args.paths:
        repo = Path(args.repo).resolve()
        print(json.dumps(
            classify_paths(args.paths, args.feature, read_designations(repo)), indent=2))
        return 0

    repo = Path(args.repo).resolve()
    tasks_path = repo / ".specs" / "features" / args.feature / "tasks.md"
    if not tasks_path.is_file():
        print(f"error: no tasks.md at {tasks_path}", file=sys.stderr)
        return 2

    result = classify_feature(
        tasks_path.read_text(encoding="utf-8"), args.feature, read_designations(repo)
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
