#!/usr/bin/env python3
"""Structural lint for the orchestrator's Feature Classification Gate (non-code-feature-track).

`agents/orchestrator.md` is a markdown/config artifact — an agent-instruction contract, not
executable code — so this "test" is a structure/ordering/semantic lint over the markdown text,
mirroring the existing pattern in `tests/test_orchestrator_label_lifecycle.py` and
`tests/test_orchestrator_github_integration.py` (FR-11, FR-11.1, FR-11.2, NFR-6).

Task 2 covers three design components:

  C0 — the normative non-code artifact allow-list block, whose normative home is this file and
       which Tasks 6/7/8 must be able to replicate **verbatim** into four other agent contracts.
  C1 — the `### Feature Classification Gate ...` section, placed **between** the Consistency Gate
       section and the ``### `implementation` `` section.
  C2 — the `.spec-state.json` schema delta: `featureClass` plus the five-key `classification`
       object, in the initialization block and in the schema prose.

Task 3 extends the module with the A3/A4 corrections to that text and with two more components:

  C3 — the per-task routing inside ``### `implementation` ``: a shared preamble above Stage 1 and
       the stage-specific bullets that forward the two values, with the stage order untouched.
  I1 — the wire contract for those two values: `featureClass` (`"code"` | `"non-code"`, never
       `null`) to Stages 2-5, and `taskProducesApplicationCode` to the task stages (2 & 3) only.

  The A3/A4 corrections asserted here: the OPEN enumeration on both sides of the C0 block with
  `CLAUDE.md` and `README.md` each named with its criterion (A3-3); the `PRECEDENCE` stanza
  subordinating AMB-1…AMB-5 to that enumeration, and the fail-safe section CITING it rather than
  restating it (A4-1); AMB-5, the empty-task-list trigger (A3-4); the C4 reclassification
  subsection in the `null`-consumer list (A3-1); the absence-is-not-by-itself-a-legacy-signal
  qualifier naming `commands/sdd-feature.md` (A3-5); and the legacy branch's one-line report of
  its own determination (A3-2, R10).

Assertions target wording, ORDER and ABSENCE — never mere substring presence where presence alone
would also be satisfied by text saying the opposite. In particular:

  * placement is asserted by character offset (consistency < classification < implementation), not
    by the heading merely existing somewhere in the file;
  * the gate's **entry predicate** is asserted to key on the RECORDED DECISION, with the absent and
    `null` states both pinned as "not yet classified". This is the load-bearing sentence of the
    whole feature: `/sdd-feature` scaffolds without the key and the initialization block writes
    `"featureClass": null`, so a predicate keyed on key *presence* skips the gate for every new
    feature and switches the non-code track off with a green pipeline and no error;
  * the **legacy-state discriminator** is asserted to be TWO conditions (absent `featureClass`
    **and** `phase` at `implementation` or beyond), and the freshly-scaffolded complement is
    asserted positively — a one-condition rule reaches the same silent switch-off from the other
    side;
  * the meaning of a `null` `featureClass` **at every consumer** is asserted in the schema prose,
    so the readers added by Tasks 3/6/7/8 cannot each invent one;
  * the git-diff **disclaimer** is asserted, not just the positive "declared outputs" statement —
    the disclaimer is what discrepancy D1 requires;
  * the fail-safe is asserted to be `"code"` *and* the region is asserted to carry no directive
    classifying `"non-code"`;
  * the override rule's **asymmetry** is asserted in both directions, and each of the three
    branches is asserted to state the value it writes (an honoured override that writes nothing is
    an override that silently does nothing);
  * the C0 block is pinned against its canonical text (design C0 / DD-5), so a future verbatim
    replication has something that cannot silently drift;
  * `ready-to-merge` is asserted **absent** from the classification-gate region, and the whole-file
    singleton invariant (exactly one *set* operation, inside the Feature Review Gate PASS branch)
    is re-asserted here as a regression guard (FR-9.1, AC-7);
  * every routing assertion is scoped to ONE stage's bullet list, so "Stage 3 requests
    artifact-conformance mode" cannot be satisfied by text sitting in Stage 2 — and each scoped
    slice asserts BOTH its anchors (see `slice_between`), so a re-anchoring that no longer matches
    goes red instead of silently widening to the whole section;
  * the `"code"` path is asserted UNCHANGED, not merely un-mentioned: the stage headings are
    asserted to be four, in order, with the reviews still gated on validation, and no region of the
    routing delta may introduce a user prompt (NFR-4).

Covers FR-1, FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-2, FR-2.1, FR-2.3, FR-2.4,
FR-3.3, FR-5.1, FR-9.1, FR-11, FR-11.1, FR-11.2, NFR-4, NFR-5, NFR-6.

Later tasks (4, 5) extend this module by adding further `OrchestratorDocTestCase` subclasses — the
base class, the section/region helpers and the text normalisers below are shared for that purpose.
Nothing here writes anything, anywhere.

Stdlib-only. Run:
    python3 -m unittest tests.test_orchestrator_feature_class -v
    # or
    python3 tests/test_orchestrator_feature_class.py
"""

import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path

# Resolve the orchestrator relative to this test file so the module runs wherever the repo's hooks
# run (FR-11.1): <root>/tests/test_orchestrator_feature_class.py -> <root>/agents/orchestrator.md
ORCH_PATH = Path(__file__).resolve().parent.parent / "agents" / "orchestrator.md"

# --- Exact anchors (design C0 / C1) -------------------------------------------------------------

CONSISTENCY_GATE_HEADING = (
    "Consistency Gate (runs automatically after tasks confirmed, before implementation)"
)
CLASSIFICATION_GATE_HEADING = (
    "Feature Classification Gate "
    "(runs automatically after the consistency gate, before implementation)"
)
IMPLEMENTATION_HEADING = "`implementation`"
ALLOW_LIST_HEADING = (
    "Non-code artifact allow-list (normative — identical in every agent that classifies)"
)

# The C0 allow-list body, verbatim from design.md C0 as amended by A3, A4 and A5 (itself
# unparaphrased from the requirements "Definitions used throughout"): the repository enumeration is
# OPEN on both sides, the application-code side names the repository-root `CLAUDE.md` with its
# criterion and settles it UNCONDITIONALLY, the non-code side names the repository-root `README.md`
# as a CONDITION pointing at the fence's own bounded `PRECEDENCE` CHECK, and that `PRECEDENCE`
# clause is asymmetric: a failed or unrun check is itself the project's designation, so the file is
# application code and does not fall back to the category tests; the FILE-CLASSIFYING triggers
# AMB-2..AMB-4 are subordinate to the enumeration while the FEATURE-LEVEL triggers AMB-1 and AMB-5
# always apply. Tasks 6/7/8 replicate this block into four more agent contracts, so it must not
# drift here: this is its normative home (DD-5). A5-1, A5-2, DD-17.
CANONICAL_ALLOW_LIST = """\
NON-CODE ARTIFACT — exactly one of:
  1. a spec artifact under .specs/features/<feature-name>/
     (requirements.md, design.md, tasks.md, scope.md, .spec-state.json)
  2. a committed prose/documentation file that the project's layout or steering does NOT
     designate as source, agent/prompt contract, template, script, or configuration
     (in this repository these include, but are not limited to, the repository-root
     README.md — WHERE the PRECEDENCE CHECK below passes for it)
  3. a knowledge-vault mutation recorded by vault-writer in
     .specs/features/<feature-name>/vault/.write-log.jsonl

APPLICATION CODE — anything else: executable source, tests, scripts, hooks, CI workflows,
  templates, runtime configuration, and any prose file the project designates as a
  behaviour-bearing contract (in this repository these include, but are not limited to,
  agents/*.md, commands/*.md, and the repository-root CLAUDE.md — a contract the project
  loads into every agent's context at session start).

PRECEDENCE — decided BEFORE the category tests above, and ASYMMETRIC.
  * A file named on the APPLICATION CODE side is settled application code, UNCONDITIONALLY.
  * A file named on the NON-CODE side is settled non-code ONLY IF YOU RUN its CHECK and it
    passes. THE CHECK: read the repository-root CLAUDE.md, the files it imports, and
    .specs/steering/*.md; it FAILS if any of them loads that file into an agent's context or
    designates it a contract (an @-import, a session-start read instruction, or a
    designation of it as a contract or standard, in steering or in CLAUDE.md; a mere mention
    is not a load), and it FAILS if you did not run it.
  * A FAILED OR UNRUN CHECK IS ITSELF THE DESIGNATION: the file is APPLICATION CODE. Do not
    fall back to the category tests for it.
  * AMB-2, AMB-3 and AMB-4 are FILE-CLASSIFYING triggers: they apply only to a file this
    enumeration does not settle and never override one it does. AMB-1 (a task declares no
    outputs) and AMB-5 (tasks.md declares no tasks) are FEATURE-LEVEL triggers about missing
    declarations, name no file, and always apply.
  * Both lists stay open: a file's absence from either list is evidence of nothing.
"""

# Design C4 fixes this anchor verbatim: the reclassification fallback is a `####` subsection at the
# end of ``### `implementation` ``, after the `On **fail**` bullet.
RECLASSIFICATION_HEADING = "Reclassification: non-code → code (fallback, D2)"

# The complete label vocabulary of this pipeline, frozen before this feature and unchanged by it
# (FR-10.1, DD-8). The reclassification subsection introduces no sixth name and applies no label of
# its own: T2 reuses the existing `On **fail**` branch, and T1/T3 are caught before a verdict exists.
FROZEN_LABEL_NAMES = (
    "ready-to-merge",
    "blocked:validation",
    "blocked:code-review",
    "blocked:security-review",
    "blocked:feature-review",
)

CLASSIFICATION_SUBKEYS = (
    "basis",
    "decidedAt",
    "override",
    "tasksValidatedUnderExemption",
    "reclassification",
)

# FR-1.2 / sub-task 4.15: a LOAD-BEARING byte pin, not a convenience. A5 item 1(g) adds a fourth
# input to the very `**Inputs**` list this sentence bounds, and requires the sentence to survive
# **verbatim** — so it is pinned as bytes and pinned as appearing exactly once. A second, reworded
# copy is the NFR-6 drift shape: two normative statements about the same evidence base, one of which
# a later edit can relax while the other keeps every assertion green.
GIT_DIFF_DISCLAIMER = "You **never** inspect a git diff to classify (FR-1.2)."

# DD-5 / sub-task 4.9: the provenance note names the block's normative home and the copy that wins on
# disagreement. It lives OUTSIDE the fence and is deliberately NOT part of what Tasks 6, 7 and 8
# replicate, so it must stay out of `CANONICAL_ALLOW_LIST` as well — see
# `test_provenance_sentence_sits_outside_the_fence_and_is_absent_from_the_pin` for why the inverse
# is a four-file defect rather than a cosmetic one.
PROVENANCE_HOME_PHRASE = "is the **normative home** of this block"
PROVENANCE_TIEBREAK_PHRASE = "`agents/orchestrator.md` wins."

# A5-6 / sub-task 4.14: the exact pre-A5 legacy-report wording, kept only so it can be asserted GONE.
# The corrected template reads "`implementation` or beyond"; the superseded one stopped at
# "`implementation`," and emitted a false condition for a feature resumed at `phase: "review"`.
PRE_A5_LEGACY_TEMPLATE_WORDING = "`implementation`, so this file predates"


# --- Text helpers ------------------------------------------------------------------------------


def strip_frontmatter(text):
    """Return the markdown body, dropping a leading `---` frontmatter block if present."""
    if not text.startswith("---"):
        return text
    m = re.match(r"^---[ \t]*\n.*?\n---[ \t]*\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def squash(text):
    """Collapse every run of whitespace to a single space (wrapping-insensitive comparison)."""
    return re.sub(r"\s+", " ", text).strip()


def flat(text):
    """`squash` plus markdown emphasis/backtick removal.

    Lets an assertion target the *wording* of a hard-wrapped, bold-sprinkled sentence without
    encoding where the author happened to put `**` or a line break. Note this also eats the `*` in
    globs like `agents/*.md`, so raw text is used wherever a glob is the thing being asserted.
    """
    return squash(re.sub(r"[`*_]", "", text))


def headings(text):
    """[(offset, level, title)] for every ATX heading outside fenced code blocks, in order."""
    out = []
    in_fence = False
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if m:
                out.append((offset, len(m.group(1)), m.group(2)))
        offset += len(line)
    return out


def section_span(text, title):
    """(start, end) offsets of the section opened by the heading whose title is exactly `title`.

    The section ends at the next heading of the same or a higher level (or end of text). Returns
    None when no heading carries that exact title — so "the heading exists, spelled exactly so" and
    "here is its extent" are the same assertion.
    """
    hs = headings(text)
    for i, (offset, level, heading_title) in enumerate(hs):
        if heading_title != title:
            continue
        end = len(text)
        for next_offset, next_level, _ in hs[i + 1:]:
            if next_level <= level:
                end = next_offset
                break
        return offset, end
    return None


def strip_fences(text):
    """Drop fenced code blocks, keeping prose only (so an example inside a fence is not evidence)."""
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def load_frozen_span_extractor():
    """Task 1's frozen-span extractor, imported by path — READ-ONLY.

    `tests/test_orchestrator_label_lifecycle.py` owns `ORCH_INVARIANT_PATTERNS` and
    `orchestrator_invariant_lines`, and Tasks 5 and 10 are held to that same extractor. Re-deriving
    the six patterns here would defeat the point: a second copy could be relaxed independently, and
    then two modules would disagree about what "frozen" means. So the extractor is borrowed, never
    reimplemented and never edited.

    Loaded by explicit file path rather than by module name so the import does not depend on how the
    suite happened to be invoked (`unittest discover -s tests`, a bare `python3 tests/...`, or the
    repo's pre-push hook).
    """
    path = Path(__file__).resolve().parent / "test_orchestrator_label_lifecycle.py"
    spec = importlib.util.spec_from_file_location("_task1_frozen_span_extractor", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load the frozen-span extractor from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def label_set_invocations(text):
    """[(offset, label_name)] for every concrete github-agent label *set* request in `text`.

    Matches the invocation shape `{ action: label, label: { op: set, name: <name> } }` only. The
    request-schema line in *GitHub Integration* spells the op as `set|clear`, which is a grammar,
    not an operation, and is deliberately not matched.
    """
    pattern = re.compile(
        r"\{\s*action:\s*label\s*,\s*label:\s*\{\s*op:\s*set\s*,\s*name:\s*([^}\s]+)\s*\}\s*\}"
    )
    return [(m.start(), m.group(1)) for m in pattern.finditer(text)]


class OrchestratorDocTestCase(unittest.TestCase):
    """Base: loads `agents/orchestrator.md` once and exposes its body plus the Task-2 regions."""

    @classmethod
    def setUpClass(cls):
        assert ORCH_PATH.exists(), f"orchestrator definition not found at {ORCH_PATH}"
        cls.text = ORCH_PATH.read_text(encoding="utf-8")
        cls.body = strip_frontmatter(cls.text)

    def gate_span(self):
        span = section_span(self.body, CLASSIFICATION_GATE_HEADING)
        self.assertIsNotNone(
            span,
            "no heading with the exact title "
            f"{CLASSIFICATION_GATE_HEADING!r} — design C1 fixes this anchor verbatim",
        )
        return span

    def gate_region(self):
        start, end = self.gate_span()
        return self.body[start:end]

    def slice_between(self, text, start_pat, end_pat, label, container="classification gate"):
        """The slice of `text` from `start_pat` up to `end_pat`, with BOTH anchors asserted.

        A missing end anchor must never be tolerated: silently extending the slice to the end of
        the containing section turns a scoped assertion into a whole-section assertion **while
        staying green** — every positive pattern would then be satisfiable by text belonging to a
        later paragraph, and every `assertNotRegex` would be evaluated over paragraphs it was never
        meant to police. Fail loudly instead.
        """
        ms = re.search(start_pat, text)
        self.assertIsNotNone(ms, f"the {container} has no {label} paragraph")
        rest = text[ms.start():]
        me = re.search(end_pat, rest[1:])
        self.assertIsNotNone(
            me,
            f"the {label} region has no end anchor matching {end_pat!r} after it — the region "
            f"would silently run to the end of the {container} and every assertion scoped "
            f"to {label} would degrade into a whole-section assertion without going red. Re-anchor "
            f"this region against the current section structure.",
        )
        return rest[: me.start() + 1]

    def sub_region(self, start_pat, end_pat, label):
        """`slice_between` scoped to the Feature Classification Gate section."""
        return self.slice_between(self.gate_region(), start_pat, end_pat, label)

    def impl_span(self):
        span = section_span(self.body, IMPLEMENTATION_HEADING)
        self.assertIsNotNone(
            span,
            f"no heading with the exact title {IMPLEMENTATION_HEADING!r} — design C3 places the "
            f"per-task routing inside that section",
        )
        return span

    def impl_region(self):
        start, end = self.impl_span()
        return self.body[start:end]

    def stage_region(self, start_pat, end_pat, label):
        """`slice_between` scoped to the ``### `implementation` `` section (design C3)."""
        return self.slice_between(
            self.impl_region(), start_pat, end_pat, label,
            container="`implementation` section",
        )


# --- (1) C1: placement, ordering, and the gate's procedural content ------------------------------


class ClassificationGatePlacementTest(OrchestratorDocTestCase):
    def test_gate_heading_is_exact_and_appears_once(self):
        """FR-1 / NFR-6: the gate exists under the exact C1 anchor, spelled once."""
        self.assertIsNotNone(section_span(self.body, CLASSIFICATION_GATE_HEADING))
        titles = [t for _, _, t in headings(self.body)]
        self.assertEqual(
            titles.count(CLASSIFICATION_GATE_HEADING), 1,
            "the classification-gate heading must appear exactly once",
        )
        level = next(lvl for _, lvl, t in headings(self.body) if t == CLASSIFICATION_GATE_HEADING)
        self.assertEqual(level, 3, "the classification gate must be a `###` section (design C1)")

    def test_gate_sits_between_consistency_gate_and_implementation(self):
        """FR-1 / design C1: ORDERING by character offset, not mere presence.

        A gate that exists but sits after ``### `implementation` `` would never run before
        implementation, which is the whole content of FR-1.
        """
        consistency = section_span(self.body, CONSISTENCY_GATE_HEADING)
        classification = section_span(self.body, CLASSIFICATION_GATE_HEADING)
        implementation = section_span(self.body, IMPLEMENTATION_HEADING)
        for name, span in (
            ("Consistency Gate", consistency),
            ("Feature Classification Gate", classification),
            ("`implementation`", implementation),
        ):
            self.assertIsNotNone(span, f"section {name!r} not found")

        self.assertLess(
            consistency[0], classification[0],
            "the classification gate is placed BEFORE the consistency gate — FR-1 requires it to "
            "run after the task list is confirmed and the consistency gate has resolved",
        )
        self.assertLess(
            classification[0], implementation[0],
            "the classification gate is placed AFTER the `implementation` section — FR-1 requires "
            "it to run before implementation begins",
        )
        # The consistency gate must not swallow the new section, and the new section must not
        # swallow `implementation`: sibling `###` sections, in that order.
        self.assertLessEqual(consistency[1], classification[0])
        self.assertLessEqual(classification[1], implementation[0])

    def test_gate_runs_once_after_consistency_pass_including_override_path(self):
        """FR-1 / DD-1: when it runs — after the consistency PASS (incl. `(d) override and
        proceed`), in the same state-file write that sets `phase = "implementation"`, exactly once,
        and skipped on resume only once a classification has actually been RECORDED."""
        region = flat(self.sub_region(r"\*\*When it runs", r"\*\*Inputs", "'When it runs'"))
        self.assertRegex(
            region, r"(?i)after the consistency gate resolves PASS",
            "the gate does not state it runs after the consistency gate resolves PASS",
        )
        self.assertRegex(
            region, r"(?i)\(d\) override and proceed",
            "the gate does not cover the consistency gate's `(d) override and proceed` path",
        )
        self.assertRegex(
            region, r'(?i)same state-file write that sets phase = "implementation"',
            "the gate is not tied to the same state-file write that sets phase = implementation",
        )
        self.assertRegex(
            region, r"(?i)exactly once per feature",
            "the gate does not state it runs exactly once per feature",
        )
        self.assertRegex(
            region,
            r'(?i)on resume,? skip the gate only when featureClass already holds '
            r'"code" or "non-code"',
            "the gate does not state the resume rule in terms of the RECORDED decision — the "
            "skip condition must be `featureClass` already holding \"code\" or \"non-code\", "
            "never the mere presence of the key (FR-1, FR-1.7)",
        )

    def test_gate_entry_predicate_keys_on_recorded_decision_not_key_presence(self):
        """FR-1 / FR-1.1 / FR-1.7: the run/skip predicate is the load-bearing sentence of the whole
        feature — get it wrong and the gate never fires.

        `/sdd-feature` scaffolds a state file whose `featureClass` is absent, and the initialization
        block in *State File Management* initialises it to `null`. A predicate keyed on **key
        presence** therefore skips the gate for every new feature, leaving `featureClass`
        unwritten and the non-code track silently switched off with a green pipeline. The contract
        must key on the recorded decision and must say so about BOTH unrecorded states — absent and
        `null` alike.
        """
        region = flat(self.sub_region(r"\*\*When it runs", r"\*\*Inputs", "'When it runs'"))

        self.assertRegex(
            region,
            r"(?i)run/skip predicate keys on the recorded decision, never on the presence of "
            r"the key",
            "the gate does not state that its run/skip predicate keys on the RECORDED DECISION "
            "rather than on the presence of the `featureClass` key (FR-1)",
        )
        self.assertRegex(
            region,
            r'(?i)run this gate unless featureClass is already set to "code" or "non-code"',
            "the gate does not state the positive entry condition (run unless a classification of "
            '"code" or "non-code" has already been recorded)',
        )
        # The complement: `null` is not a decision, and neither is absence.
        self.assertRegex(
            region,
            r"(?i)featureClass that is absent and a featureClass that is null both mean "
            r"no classification has been recorded yet",
            "the gate does not state that an ABSENT and a NULL `featureClass` both mean no "
            "classification has been recorded yet — a `null` read as 'decided' turns the gate off "
            "for every freshly scaffolded feature (FR-1, FR-1.1)",
        )
        self.assertRegex(
            region, r"(?i)in either state the gate runs",
            "the gate does not state that it RUNS in both the absent and the null state",
        )
        self.assertRegex(
            region, r"(?i)never skip it merely because the key exists",
            "the closing clause forbidding a key-presence skip is missing — without it the "
            "defective predicate can be restored without any assertion going red (FR-1)",
        )
        # Regression guard against the exact defective phrasing this retry removed.
        self.assertNotRegex(
            region, r"(?i)featureClass is already present",
            "the run/skip predicate has been restored to key on the PRESENCE of `featureClass`. "
            "The initialization block writes `\"featureClass\": null`, so a presence-keyed "
            "predicate skips the classification gate for every new feature (FR-1, FR-1.1).",
        )

    def test_classification_derives_from_declared_outputs(self):
        """FR-1.2 (positive half): the inputs are the confirmed task list's declared outputs, read
        primarily from each task's `**Files:**` field, with design.md and steering as tie-breakers."""
        region = self.sub_region(r"\*\*Inputs\.\*\*", r"\*\*Per-output rule", "'Inputs'")
        flat_region = flat(region)
        self.assertRegex(
            flat_region, r"(?i)confirmed tasks\.md",
            "the gate does not name the confirmed tasks.md as its primary input",
        )
        self.assertRegex(
            flat_region, r"(?i)declared outputs",
            "the gate does not say it classifies from the tasks' DECLARED OUTPUTS",
        )
        self.assertIn(
            "**Files:**", region,
            "the gate does not name the task template's `**Files:**` field as the source of the "
            "declared outputs (design C1 input (a))",
        )
        self.assertRegex(
            flat_region, r"(?i)design\.md",
            "the gate does not name design.md as the component-name fallback input",
        )
        self.assertRegex(
            flat_region, r"(?i)\.specs/steering/(structure|tech)\.md",
            "the gate does not name the steering files that designate source/contract/template",
        )

    def test_inputs_name_the_designation_only_claude_md_input(self):
        """FR-1.2 / FR-1.3 / FR-1.4 / DD-17 / A5-2: the gate's `**Inputs**` list must name the fourth,
        designation-only input that C0's `PRECEDENCE` CHECK requires.

        The fence's non-code naming is conditional on a bounded check over the repository-root
        `CLAUDE.md`, the files it imports and `.specs/steering/*.md`, and it declares an **unrun**
        check **failed**. A contract that names that evidence while its Inputs list grants the
        classifier authority over steering only states a criterion the classifier may not evaluate —
        so every check is unrun, so every non-code naming settles as application code, so AC-2 /
        Flow B becomes unreachable in the very repository A4-1 made it reachable in.

        The input is deliberately narrow, and its narrowness is asserted alongside its presence: it
        is the same KIND of input as (c) — a source of the project's **designation**, which is what a
        declared output is classified *against* — and it widens nothing about what the classification
        is derived *from*, which remains the declared task outputs (FR-1.2).
        """
        region = self.sub_region(r"\*\*Inputs\.\*\*", r"\*\*Per-output rule", "'Inputs'")
        flat_region = flat(region)

        self.assertRegex(
            flat_region,
            r"(?i)\(d\) the repository-root CLAUDE\.md and any file it imports",
            "the gate's `**Inputs**` list has no fourth input naming the repository-root "
            "`CLAUDE.md` and the files it imports. C0's `PRECEDENCE` CHECK reads exactly that "
            "surface, and an unrun check is declared FAILED — without the input every check is "
            "unrun by construction (FR-1.3, FR-1.4, DD-17, A5-2)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)read only to run the allow-list block's PRECEDENCE CHECK",
            "input (d) is not scoped to running C0's `PRECEDENCE` CHECK and nothing else — an "
            "unscoped read of `CLAUDE.md` widens the classification's evidence base, which FR-1.2 "
            "fixes at the declared task outputs (FR-1.2, DD-17, A5-2)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)same kind of input as \(c\)",
            "input (d) is not tied to input (c) as the same KIND of input — a source of the "
            "project's DESIGNATION. Stated without that, it reads as a second thing the "
            "classification is derived from (FR-1.2, DD-17, A5-2)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)designation.{0,120}what a declared output is classified against — never what the "
            r"classification is derived from",
            "input (d) does not distinguish what an output is classified AGAINST from what the "
            "classification is derived FROM. That distinction is the whole of FR-1.2's survival "
            "here (FR-1.2, DD-17, A5-2)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)widens no other part of the classification|it widens no other part",
            "input (d) does not state that it widens no other part of the classification (A5-2)",
        )

    def test_classification_explicitly_disclaims_the_git_diff(self):
        """FR-1.2 / D1 (the load-bearing half): the contract must explicitly DISCLAIM deriving the
        classification from a git diff. The positive statement alone does not discharge D1 — the
        whole point of the discrepancy is that an empty diff must never be read as evidence."""
        gate = flat(self.gate_region())
        self.assertRegex(
            gate, r"(?i)never\s+inspect\s+a\s+git\s+diff",
            "the classification gate does not explicitly state it NEVER inspects a git diff "
            "(FR-1.2, D1)",
        )
        self.assertRegex(
            gate, r"(?i)nothing has been implemented",
            "the gate does not give the structural reason the no-diff rule holds (nothing has "
            "been implemented yet at this point in the lifecycle)",
        )
        self.assertRegex(
            gate, r'(?i)never from whether a diff happens to be empty',
            "the gate does not disclaim the 'empty diff means non-code' inference (D1)",
        )
        self.assertRegex(gate, r"FR-1\.2", "the no-diff rule is not anchored to FR-1.2")

    def test_git_diff_disclaimer_survives_verbatim_and_exactly_once(self):
        """FR-1.2 / sub-task 4.15: the disclaimer must survive A5's `**Inputs**` edit **verbatim**,
        exactly once, and must still stand *after* the input list it bounds.

        `test_classification_explicitly_disclaims_the_git_diff` asserts the rule is *present*, via a
        whitespace-insensitive pattern over the flattened gate. That is the right shape for a
        rationale sentence and the wrong shape for this one. Sub-task 4.15 edits the very list this
        sentence qualifies and says in terms: do not touch it, it must survive verbatim. A pattern
        cannot discharge a verbatim requirement — `never inspects a git diff *for the class of the
        feature*` would satisfy it while narrowing the rule from all classification to one of its
        uses. So the pin here is BYTES, and it is deliberately load-bearing rather than incidental.

        Exactly-once matters for the same reason it matters for the NFR-4 guard sentence: input (d)
        newly grants a read of `CLAUDE.md`, and the one thing keeping that from widening the evidence
        base is a single unambiguous statement of what the classification is *never* derived from.
        Two copies are two things to relax, and the suite would notice neither.

        Ordering matters because (d) is a *grant* and this is its *bound*. The sentence sitting after
        the list is what makes it read as qualifying all four inputs; moved above them, input (d)
        would be the last word on the subject.
        """
        self.assertIn(
            GIT_DIFF_DISCLAIMER, self.body,
            "the FR-1.2 git-diff disclaimer is no longer present VERBATIM. Sub-task 4.15 edits the "
            "`**Inputs**` list this sentence bounds and requires the sentence itself to survive "
            "unchanged; expected exactly:\n"
            f"  {GIT_DIFF_DISCLAIMER!r}\n"
            "A reworded variant may still satisfy the looser presence check in "
            "`test_classification_explicitly_disclaims_the_git_diff` while narrowing the rule "
            "(FR-1.2, D1, A5-2)",
        )
        self.assertEqual(
            self.body.count(GIT_DIFF_DISCLAIMER), 1,
            f"the FR-1.2 git-diff disclaimer appears "
            f"{self.body.count(GIT_DIFF_DISCLAIMER)} times; it must be stated exactly ONCE. Input "
            f"(d) grants a designation-only read of `CLAUDE.md`, and one unambiguous statement of "
            f"what the classification is never derived from is what keeps that grant bounded — two "
            f"copies are two places a later edit can relax independently (FR-1.2, NFR-6)",
        )
        # No second, reworded statement of the same rule anywhere in the gate.
        gate = self.gate_region()
        restatements = re.findall(r"(?i)never\s+inspects?\s+a\s+git\s+diff", flat(gate))
        self.assertEqual(
            len(restatements), 1,
            f"the classification gate states the no-git-diff rule {len(restatements)} times. It is "
            f"one rule with one normative home; a second phrasing in the same section is the NFR-6 "
            f"drift shape (FR-1.2, NFR-6)",
        )
        # ...and it stands AFTER the input list it bounds, including A5's new input (d).
        input_d = gate.find("(d) The repository-root `CLAUDE.md`")
        self.assertNotEqual(
            input_d, -1,
            "the gate's `**Inputs**` list has no input (d) — sub-task 4.15 adds it (A5 item 1(g))",
        )
        disclaimer_at = gate.find(GIT_DIFF_DISCLAIMER)
        self.assertNotEqual(
            disclaimer_at, -1,
            "the FR-1.2 disclaimer is not inside the Feature Classification Gate section at all — "
            "it bounds that gate's inputs and must live with them (FR-1.2)",
        )
        self.assertGreater(
            disclaimer_at, input_d,
            "the FR-1.2 disclaimer now sits ABOVE the `**Inputs**` list. It is the bound on what the "
            "classification may be derived from, and input (d) is a newly granted read of "
            "`CLAUDE.md`; stated before the grant it no longer reads as qualifying it (FR-1.2, "
            "DD-17, A5-2)",
        )

    def test_per_output_and_per_feature_rules(self):
        """FR-1.3: an output is non-code iff it matches the allow-list; a FEATURE is non-code iff
        every task declares at least one output and every declared output is non-code."""
        per_output = flat(
            self.sub_region(r"\*\*Per-output rule", r"\*\*Per-feature rule", "'Per-output rule'")
        )
        self.assertRegex(
            per_output, r"(?i)non-code iff it matches one of the three allow-list categories",
            "the per-output rule is not stated as an iff over the three allow-list categories",
        )
        self.assertRegex(
            per_output, r"(?i)otherwise it is application code",
            "the per-output rule lacks the application-code catch-all",
        )

        per_feature = flat(
            self.sub_region(r"\*\*Per-feature rule", r"\*\*Fail-safe", "'Per-feature rule'")
        )
        self.assertRegex(
            per_feature,
            r'(?i)featureClass = "non-code".{0,40}iff.{0,80}every task declares at least one output',
            "the per-feature rule does not require EVERY task to declare at least one output",
        )
        self.assertRegex(
            per_feature, r"(?i)every declared output of every task classifies non-code",
            "the per-feature rule does not require EVERY declared output to classify non-code",
        )
        self.assertRegex(
            per_feature, r'(?i)otherwise set featureClass = "code"',
            "the per-feature rule lacks the 'otherwise code' branch",
        )
        self.assertRegex(
            per_feature, r'(?i)one task declaring application code is enough',
            "the per-feature rule does not state that a single code-declaring task forces 'code'",
        )

    def test_fail_safe_is_code_with_enumerated_ambiguity_triggers(self):
        """FR-1.4 / R7: the fail-safe DIRECTION is `"code"`, the triggers are enumerated so the
        rule is checkable, and the region carries no directive pointing the other way."""
        region = self.sub_region(r"\*\*Fail-safe", r"\*\*Record and report", "'Fail-safe'")
        flat_region = flat(region)

        self.assertRegex(
            flat_region, r'(?i)classify "code" whenever the answer is not unambiguous',
            "the fail-safe does not state that an ambiguous answer classifies 'code' (FR-1.4)",
        )
        self.assertRegex(
            flat_region, r'(?i)"code" is the fail-safe direction because it preserves '
                         r"today's behaviour",
            "the fail-safe does not state WHY 'code' is the safe direction (preserves today's "
            "behaviour exactly)",
        )
        # Negative: nothing in the fail-safe region may direct a classification toward "non-code".
        self.assertNotRegex(
            flat_region, r'(?i)(classify|set|default[s]? to)[^.]{0,60}"non-code"',
            "the fail-safe region contains a directive classifying \"non-code\" — the fail-safe "
            "direction must be \"code\" and only \"code\" (FR-1.4)",
        )

        # Enumerated triggers: FIVE, each a distinct list item, each substantive. Any markdown list
        # marker counts — `-`, `*`, `+` or an ordered `1.` / `1)` — so a purely cosmetic re-styling
        # of the enumeration does not turn this assertion red.
        triggers = re.findall(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+.*$", region)
        self.assertGreaterEqual(
            len(triggers), 5,
            f"the fail-safe enumerates only {len(triggers)} ambiguity trigger(s); design C1 lists "
            f"five (no declared outputs / unresolvable output / prose in a designated directory / "
            f"steering silent / an empty task list)",
        )
        flat_triggers = flat("\n".join(triggers))
        # The labels themselves, pinned exactly: AMB-1 … AMB-5, once each, in order. Tests, reviews
        # and the contract's own precedence pointer cite these labels by name, so a dropped or
        # renumbered trigger must go red rather than merely thin the enumeration out.
        self.assertEqual(
            re.findall(r"\bAMB-\d+\b", flat_triggers),
            ["AMB-1", "AMB-2", "AMB-3", "AMB-4", "AMB-5"],
            "the ambiguity triggers are not labelled AMB-1 … AMB-5, exactly once each and in "
            "order (FR-1.4, A3-4)",
        )
        for label, pattern, why in (
            ("no declared outputs", r"(?i)declares no outputs", "a task declaring no outputs"),
            ("unresolvable output", r"(?i)cannot be resolved to a concrete path",
             "an output that resolves to no concrete path or category"),
            ("designated directory", r"(?i)steering designates as source",
             "a prose file inside a directory steering designates as source/contract/template"),
            ("steering silent", r"(?i)steering is silent", "steering silent and location unhelpful"),
            # AMB-5 (A3-4): the per-feature rule is a conjunction of two universals and is
            # VACUOUSLY TRUE over zero tasks — an empty task list is the single input on which the
            # rule would otherwise invert its own fail-safe direction. AMB-1 covers "a task
            # declares no outputs" and says nothing about "there are no tasks".
            ("empty task list", r"(?i)tasks\.md declares no tasks",
             "a tasks.md that declares no tasks at all, which no other trigger catches"),
        ):
            self.assertRegex(
                flat_triggers, pattern,
                f"ambiguity trigger '{label}' is missing — {why} must be enumerated (FR-1.4, R7)",
            )

    def test_ambiguity_triggers_are_declared_subordinate_to_the_allow_list_enumeration(self):
        """FR-1.4 / NFR-6 / A4-1: the fail-safe section must SUBORDINATE AMB-1…AMB-5 to C0's
        enumeration, by citing the fenced `PRECEDENCE` clause rather than restating it.

        Without the pointer the two rules are peers, and the repository-root `CLAUDE.md` (prose,
        but a behaviour-bearing contract) and `README.md` (prose in a directory full of contracts)
        are each simultaneously settled by the enumeration and caught by AMB-3/AMB-4 — an
        ambiguity trigger firing over a file the enumeration already named would classify by
        fail-safe instead of by enumeration, which is exactly the drift A4-1 closes.

        The pointer must be a CITATION, not a copy: a second normative statement of the precedence
        rule can drift out of step with the one Tasks 6/7/8 replicate into four other contracts.
        """
        region = flat(self.sub_region(r"\*\*Fail-safe", r"\*\*Record and report", "'Fail-safe'"))

        self.assertRegex(
            region, r"(?i)these triggers are subordinate to the allow-list enumeration",
            "the fail-safe section does not declare the ambiguity triggers SUBORDINATE to C0's "
            "allow-list enumeration (FR-1.4, A4-1)",
        )
        self.assertRegex(
            region,
            r"(?i)apply only to a file the fenced block above does not already settle by name",
            "the fail-safe section does not restrict the triggers to files the fenced block does "
            "not already settle by name (A4-1)",
        )
        self.assertRegex(
            region, r"(?i)stated normatively once, in that block's PRECEDENCE clause",
            "the fail-safe section does not CITE the fenced `PRECEDENCE` clause as the one "
            "normative statement of the precedence rule (NFR-6, A4-1)",
        )
        self.assertRegex(
            region, r"(?i)deliberately not restated here",
            "the fail-safe section does not say the precedence rule is deliberately NOT restated "
            "here — the reason a reader may not add a second copy (NFR-6)",
        )
        # A restatement, not a citation, is the failure mode: the normative sentence itself must
        # live only in the fenced block that Tasks 6/7/8 replicate.
        self.assertNotIn(
            "settles every file it names", region,
            "the fail-safe section RESTATES the `PRECEDENCE` rule instead of citing it. The "
            "normative wording belongs in the fenced C0 block alone — Tasks 6/7/8 replicate that "
            "block into four other contracts, and a second copy here would drift out of step "
            "(NFR-6, A4-1, DD-5).",
        )
        # The concrete consequence, spelled out for the two files the enumeration now names.
        self.assertRegex(
            region,
            r"(?i)the repository-root CLAUDE\.md is application code and the repository-root "
            r"README\.md is a category-2 non-code artifact by enumeration",
            "the fail-safe section does not state the concrete consequence of the precedence rule "
            "for the repository-root CLAUDE.md and README.md (A4-1)",
        )
        self.assertRegex(
            region, r"(?i)AMB-3 and AMB-4 never fire over either",
            "the fail-safe section does not state that AMB-3 and AMB-4 never fire over the two "
            "files the enumeration settles by name (FR-1.4, A4-1)",
        )

    def test_fail_safe_pointer_rescopes_the_triggers_and_conditions_the_readme_consequence(self):
        """FR-1.4 / NFR-6 / A5-1 / A5-2 — sub-task 4.10, A5 item 1(b): the POINTER, not the fence,
        must carry A5's rescoping.

        A5 rewrote the precedence rule inside the fenced C0 block, and the fence is pinned
        byte-for-byte. The fail-safe **pointer** is a second, *unpinned* paragraph about the same
        rule, and A5's own item-2 test inventory names no assertion for it: every feature-level,
        always-apply and conditionality assertion in this module targets the fenced block
        (`flat_block`). The pointer could therefore have been left in its pre-A5 shape —
        subordinating all five triggers and settling the repository-root `README.md` non-code
        *unconditionally* — with the entire suite green. That is exactly the NFR-6 drift the pointer
        exists to prevent, and it is the worse half of it: a reader who stops at the prose gets the
        superseded rule, while the fence the four replicas carry says something else.

        Everything below is asserted as a PROPERTY of the pointer's own sentences rather than as a
        sentence pin, so a rewording that preserves the rule stays green while an inversion goes red:

          * the subordination claim names the FILE-CLASSIFYING triggers (AMB-2…AMB-4) and does not
            reach AMB-1 or AMB-5;
          * the always-apply claim names AMB-1 and AMB-5 and does NOT reach AMB-2…AMB-4 — the
            inversion guard, since "always apply" said of a file-classifying trigger re-opens the
            override the fence just closed;
          * the `README.md` consequence is CONDITIONAL on the fence's bounded check while the
            `CLAUDE.md` consequence stays unconditional, and the failed-or-unrun branch settles the
            file as application code;
          * and the paragraph remains a CITATION — it refers to the check without restating its
            operative definition, which is what keeps one normative copy in the replicated fence.
        """
        raw = self.sub_region(r"\*\*Fail-safe", r"\*\*Record and report", "'Fail-safe'")

        # Scope guard, asserted rather than assumed. Every assertion below is meant to police the
        # pointer PROSE; the pinned fence sits above `**Fail-safe` and so is outside this region
        # today. If a fenced block ever moved in here, the pinned C0 text would satisfy these
        # assertions on the fence's behalf and the pointer could drift unobserved — the precise
        # failure this test was added to close.
        self.assertNotIn(
            "```", raw,
            "the fail-safe region now contains a fenced block, so every assertion in this test can "
            "be satisfied by pinned C0 text instead of by the pointer prose it is meant to police "
            "(NFR-6, A5-1)",
        )

        region = flat(raw)
        # Sentence granularity: split on sentence-final periods only. `flat()` has already removed
        # backticks and emphasis, and intra-word dots (`tasks.md`, `README.md`) are not followed by
        # whitespace, so they do not split. Colons deliberately do NOT split — the subordination
        # sentence carries its scope after a colon, and splitting there would separate the claim
        # from the very list this test checks.
        sentences = [s for s in re.split(r"(?<=\.)\s+", region) if s.strip()]

        # (i) The subordination claim is scoped to the file-classifying triggers.
        subordinating = [
            s for s in sentences
            if re.search(r"(?i)subordinate to the allow-list enumeration", s)
        ]
        self.assertTrue(
            subordinating,
            "the fail-safe pointer no longer subordinates the ambiguity triggers to C0's allow-list "
            "enumeration at all (FR-1.4, A4-1, A5-1)",
        )
        for sentence in subordinating:
            self.assertRegex(
                sentence, r"(?i)file-classifying",
                "the pointer subordinates the triggers without saying WHICH ones — A5 makes the "
                "subordination apply to the FILE-CLASSIFYING triggers only, because a trigger that "
                "names no file cannot be overridden by a file enumeration (FR-1.4, A5-1)\n"
                f"  offending sentence: {sentence!r}",
            )
            for trigger in ("AMB-2", "AMB-3", "AMB-4"):
                self.assertIn(
                    trigger, sentence,
                    f"the pointer's subordination claim does not name {trigger} — the three "
                    f"file-classifying triggers are named individually so a dropped one goes red "
                    f"rather than silently escaping the enumeration's precedence (FR-1.4, A5-1)\n"
                    f"  offending sentence: {sentence!r}",
                )
            self.assertNotRegex(
                sentence, r"AMB-1|AMB-5",
                "the pointer still subordinates AMB-1 or AMB-5 to the file enumeration. A5-1 makes "
                "both FEATURE-LEVEL: they are about missing declarations and name no file, so a "
                "file enumeration has nothing to settle them with. Subordinated, AMB-5 could not "
                "fire over a `tasks.md` with no tasks — the one input on which the per-feature rule "
                "inverts its own fail-safe direction (FR-1.4, A5-1, A5-2)\n"
                f"  offending sentence: {sentence!r}",
            )

        # (ii) The always-apply claim is scoped to the feature-level triggers — and the inversion
        # guard: it must not be claimed of the file-classifying ones.
        always_apply = [s for s in sentences if re.search(r"(?i)always apply", s)]
        self.assertTrue(
            always_apply,
            "the fail-safe pointer does not state that any trigger ALWAYS APPLIES. A5-1 requires "
            "AMB-1 and AMB-5 to be declared feature-level and always applying; without it the "
            "subordination sentence reads as covering all five (FR-1.4, A5-1)",
        )
        for sentence in always_apply:
            self.assertRegex(
                sentence, r"(?i)feature-level",
                "the pointer's always-apply claim does not tie itself to the FEATURE-LEVEL triggers "
                "— the reason they always apply is that they name no file (FR-1.4, A5-1)\n"
                f"  offending sentence: {sentence!r}",
            )
            for trigger in ("AMB-1", "AMB-5"):
                self.assertIn(
                    trigger, sentence,
                    f"the pointer's always-apply claim does not name {trigger} (FR-1.4, A5-1)\n"
                    f"  offending sentence: {sentence!r}",
                )
            self.assertNotRegex(
                sentence, r"AMB-2|AMB-3|AMB-4",
                "the pointer claims a FILE-CLASSIFYING trigger always applies. That inverts A5-1: "
                "AMB-2…AMB-4 apply only to a file the fenced enumeration does not settle, and a "
                "trigger that always applies overrides the enumeration for the two files it names "
                "by hand — reinstating exactly the drift A4-1 closed (FR-1.4, A5-1)\n"
                f"  offending sentence: {sentence!r}",
            )

        # The stated REASON, not merely the conclusion: they name no file, so there is no unsettled
        # file for the enumeration to leave open. Without the reason the two claims read as an
        # arbitrary carve-out that a later editor may "tidy up" into symmetry.
        self.assertRegex(
            region, r"(?i)name no file",
            "the pointer does not give the reason AMB-1 and AMB-5 always apply — they name no file, "
            "which is what puts them outside a FILE enumeration's reach (FR-1.4, A5-1)",
        )
        self.assertRegex(
            region, r"(?i)no unsettled file",
            "the pointer does not state the case that makes the carve-out load-bearing: a `tasks.md` "
            "with no tasks leaves no unsettled file at all, so a subordinated AMB-5 would never "
            "fire (FR-1.4, A5-1, A5-2)",
        )

        # (iii) The `README.md` consequence is conditional; the `CLAUDE.md` one is not.
        readme_sentences = [s for s in sentences if "README.md" in s]
        self.assertTrue(
            readme_sentences,
            "the fail-safe pointer no longer states the concrete consequence for the "
            "repository-root README.md (A4-1, A5-2)",
        )
        for sentence in readme_sentences:
            self.assertRegex(
                sentence, r"(?i)\bunconditionally\b",
                "the pointer states the two consequences symmetrically. A5-2 makes them asymmetric: "
                "the repository-root CLAUDE.md is settled application code UNCONDITIONALLY, and "
                "only the README.md side is conditional (FR-1.4, A5-2)\n"
                f"  offending sentence: {sentence!r}",
            )
            self.assertRegex(
                sentence, r"(?i)has been run and passes",
                "the pointer settles the repository-root README.md non-code without conditioning it "
                "on the fence's bounded CHECK having been RUN and PASSED. This fence ships to "
                "consumer projects through `install.sh`, where \"in this repository\" rebinds: a "
                "consumer whose CLAUDE.md carries `@README.md` has a behaviour-bearing README, and "
                "an unconditional pointer hands it the tester's no-code behaviour and the "
                "validator's artifact-conformance mode on a criterion that is false (FR-1.4, A5-2, "
                "DD-17)\n"
                f"  offending sentence: {sentence!r}",
            )
            self.assertRegex(
                sentence, r"(?i)\bCHECK\b",
                "the pointer's conditionality does not name the fence's CHECK as the thing it is "
                "conditional on, so the condition has no stated criterion to be evaluated against "
                "(NFR-6, A5-2)\n"
                f"  offending sentence: {sentence!r}",
            )

        # (iv) The failed-or-unrun branch: the contrapositive must be here too, or a reader of the
        # prose learns the condition without learning what happens when it does not hold.
        unrun_sentences = [s for s in sentences if re.search(r"(?i)never run|was not run", s)]
        self.assertTrue(
            unrun_sentences,
            "the pointer states the README.md condition without its failure branch. The fence "
            "declares an UNRUN check failed and a failed check itself the designation; the pointer "
            "must carry that consequence or the conditionality reads as \"non-code until someone "
            "checks\" (FR-1.4, A5-2, DD-17)",
        )
        for sentence in unrun_sentences:
            self.assertRegex(
                sentence, r"(?i)application code",
                "the pointer's failed-or-unrun branch does not settle the file as APPLICATION CODE "
                "— the fail-safe direction. Any other resolution turns an unrun check into a "
                "non-code classification, which is the inversion DD-17 exists to block (FR-1.4, "
                "A5-2, DD-17)\n"
                f"  offending sentence: {sentence!r}",
            )

        # (v) Still a CITATION. The existing test asserts the citation wording is present; this is
        # the other half — the check's OPERATIVE definition must not be re-stated here, because a
        # second copy of it drifts out of step with the one Tasks 6/7/8 replicate into four files.
        for token, what in (
            ("@-import", "the @-import load criterion"),
            ("session-start read instruction", "the session-start read criterion"),
            ("mere mention", "the mere-mention exclusion"),
            ("FAILS if", "the check's failure conditions"),
            (".specs/steering/*.md", "the check's read surface"),
        ):
            self.assertNotIn(
                token, raw,
                f"the fail-safe pointer restates {what} instead of citing the fenced PRECEDENCE "
                f"clause. That clause is the single normative statement of the rule and is "
                f"replicated verbatim into four other agent contracts by Tasks 6/7/8; a second copy "
                f"here can be relaxed without any of the five replicas going red (NFR-6, A5-1, "
                f"DD-5)",
            )

    def test_record_and_report_value_and_per_task_basis(self):
        """FR-1.5 / NFR-5: the gate writes `featureClass` + the `classification` object and reports
        both the value AND its basis, one line per task naming that task's declared outputs."""
        region = flat(self.sub_region(r"\*\*Record and report", r"\*\*Override", "'Record'"))
        self.assertRegex(
            region, r"(?i)write featureClass and the classification object",
            "the gate does not state that it writes featureClass and the classification object",
        )
        self.assertRegex(
            region, r"(?i)\.spec-state\.json",
            "the gate does not name .spec-state.json as the record target (NFR-5)",
        )
        self.assertRegex(
            region, r"(?i)classification\.basis",
            "the gate does not record the basis in classification.basis (FR-1.5)",
        )
        self.assertRegex(
            region, r"(?i)report to the user the recorded value",
            "the gate does not report the recorded value to the user (FR-1.5)",
        )
        self.assertRegex(
            region, r"(?i)one line per task, naming that task's declared outputs",
            "the gate does not require a per-task basis line naming that task's declared outputs",
        )

    def test_override_rule_is_asymmetric(self):
        """FR-1.6: an override toward `"code"` is ALWAYS honoured; one toward `"non-code"` is
        honoured ONLY when the per-feature rule already holds — and both outcomes are recorded."""
        region = flat(self.sub_region(r"\*\*Override", r"\*\*Legacy state", "'Override'"))
        self.assertRegex(
            region, r'(?i)override toward "code" is always honoured',
            "an override toward \"code\" is not stated as always honoured (FR-1.6)",
        )
        self.assertRegex(
            region, r'(?i)override toward "non-code" is honoured only when',
            "an override toward \"non-code\" is not conditioned on the FR-1.3 test (FR-1.6)",
        )
        self.assertNotRegex(
            region, r'(?i)override toward "non-code" is (always|unconditionally) honoured',
            "an override toward \"non-code\" is stated as unconditional — FR-1.6 makes the rule "
            "ASYMMETRIC: only the override toward \"code\" is unconditional",
        )
        self.assertRegex(
            region, r"(?i)FR-1\.3", "the conditional override does not cite the FR-1.3 test",
        )
        self.assertRegex(
            region, r"(?i)refuse it.{0,120}name the offending task",
            "a refused override does not have to name the offending task and its code output",
        )
        self.assertRegex(
            region, r'(?i)keep featureClass = "code"',
            "a refused override does not state that featureClass stays \"code\"",
        )
        self.assertRegex(
            region, r"(?i)accepted (or|and) refused.{0,60}recorded in classification\.override",
            "the gate does not record BOTH accepted and refused overrides (FR-1.6, NFR-5)",
        )

    def test_override_branches_each_state_the_value_written(self):
        """FR-1.6 / NFR-5: all three override branches say what `featureClass` ends up as.

        The refusal branch has always spelled out its outcome (`keep featureClass = "code"`). The
        two acceptance branches must be symmetric with it: an override the orchestrator honours but
        never writes is an override that silently does nothing, and `classification.override` would
        then record an acceptance that `featureClass` contradicts.
        """
        region = flat(self.sub_region(r"\*\*Override", r"\*\*Legacy state", "'Override'"))
        self.assertRegex(
            region, r'(?i)always honoured: write featureClass = "code"',
            'the accepted override toward "code" does not say the value is WRITTEN — an honoured '
            "override must state its effect on `featureClass` (FR-1.6, NFR-5)",
        )
        self.assertRegex(
            region, r'(?i)when it does, write featureClass = "non-code"',
            'the accepted override toward "non-code" does not say the value is WRITTEN, leaving '
            "the honoured branch with no stated effect while the refused branch has one "
            "(FR-1.6, NFR-5)",
        )
        self.assertRegex(
            region, r'(?i)keep featureClass = "code"',
            "the refused-override branch no longer states that `featureClass` stays \"code\" "
            "(FR-1.6)",
        )

    def test_legacy_state_absent_feature_class_is_code(self):
        """FR-1.7 / R4: an absent `featureClass` is read as `"code"` on the unchanged code path,
        with no retro-classification of an already-confirmed task list."""
        region = flat(self.sub_region(r"\*\*Legacy state", r"\*\*What this gate never does",
                                      "'Legacy state'"))
        self.assertRegex(
            region, r"(?i)if featureClass is absent from an existing state file",
            "the legacy-state rule does not describe an absent featureClass",
        )
        self.assertRegex(
            region, r'(?i)treat the feature as "code"',
            "an absent featureClass is not treated as \"code\" (FR-1.7)",
        )
        self.assertRegex(
            region, r"(?i)unchanged code path",
            "the legacy-state rule does not keep the feature on the UNCHANGED code path (NFR-4)",
        )
        self.assertRegex(
            region, r"(?i)do not retro-classify",
            "the legacy-state rule does not forbid retro-classification",
        )

    def test_legacy_discriminator_requires_absence_and_phase_at_implementation_or_beyond(self):
        """FR-1.7 / R4: the legacy escape hatch is guarded by TWO conditions, not one.

        FR-1.7 addresses "a feature started before this change". Absence of `featureClass` does not
        identify such a feature: `/sdd-feature` scaffolds every NEW feature without the key too.
        A one-condition discriminator therefore routes every new feature down the legacy path and
        the classification gate never runs — the same silent switch-off as a presence-keyed entry
        predicate, reached from the other side. The second condition (`phase` already at
        `implementation` or beyond) is what makes the rule sound: only a run that had already
        passed the point where this gate now sits could have written such a file.
        """
        region = flat(self.sub_region(r"\*\*Legacy state", r"\*\*What this gate never does",
                                      "'Legacy state'"))
        self.assertRegex(
            region,
            r"(?i)pre-change state file is identified by two conditions holding together,? "
            r"never by one alone",
            "the legacy-state rule does not declare its discriminator to be TWO conditions "
            "holding together (FR-1.7, R4)",
        )
        self.assertRegex(
            region,
            r"(?i)featureClass is absent from an existing state file and phase is already "
            r"implementation or beyond",
            "the legacy discriminator does not conjoin an absent `featureClass` WITH `phase` "
            "already at `implementation` or beyond — absence alone would capture every freshly "
            "scaffolded feature and skip the gate for all of them (FR-1.7)",
        )

    def test_legacy_state_does_not_capture_a_freshly_scaffolded_feature(self):
        """FR-1.7 / FR-1.1 / R4: the complement of the legacy rule is stated positively.

        The rule must not merely omit the wrong reading; it must forbid it by name, and it must say
        what the absent/`null` key means at `requirements` / `design` / `tasks` — a NEW feature the
        gate is obliged to run over.
        """
        region = flat(self.sub_region(r"\*\*Legacy state", r"\*\*What this gate never does",
                                      "'Legacy state'"))
        self.assertRegex(
            region, r"(?i)absence on its own is not the discriminator",
            "the legacy-state rule does not state that absence ALONE is not the discriminator — "
            "without that sentence the one-condition misreading is a permitted reading (FR-1.7)",
        )
        self.assertRegex(
            region,
            r"(?i)every freshly scaffolded feature begins with no featureClass key at all",
            "the legacy-state rule does not name the freshly-scaffolded case, which is exactly "
            "the case a one-condition discriminator misclassifies (FR-1.7)",
        )
        self.assertRegex(
            region, r"(?i)/sdd-feature writes a state file that does not contain it",
            "the legacy-state rule does not cite `/sdd-feature` as the reason a new feature's "
            "state file lacks the key (FR-1.7)",
        )
        self.assertRegex(
            region,
            r"(?i)featureClass is absent or null while phase is still requirements, design or "
            r"tasks is a new feature, not a legacy one",
            "the legacy-state rule does not classify an absent-or-null `featureClass` at the "
            "planning phases as a NEW feature (FR-1.1, FR-1.7)",
        )
        self.assertRegex(
            region, r"(?i)this gate must run over it",
            "the legacy-state rule does not oblige the gate to RUN over a freshly scaffolded "
            "feature — the positive duty is what stops the silent switch-off (FR-1, FR-1.7)",
        )

    def test_legacy_branch_reports_its_determination(self):
        """FR-1.5 / FR-1.7 / NFR-5 / NFR-4 / R10: the legacy branch is the one path through this
        gate that records no classification — so it must still REPORT.

        Every other exit from the gate writes `featureClass` plus `classification.basis` and reports
        the value and its basis to the user (FR-1.5). The legacy branch writes nothing, so without
        an explicit report it is a silent path: the user cannot tell "this feature was read as
        pre-change and left unclassified" apart from "the gate never ran". The report must name the
        two conditions it fired on, and it must remain a REPORT — a prompt here would break NFR-4's
        "no additional user prompt on the code path".
        """
        region = self.sub_region(
            r"\*\*Report the legacy determination", r"\*\*What this gate never does",
            "'Report the legacy determination'",
        )
        flat_region = flat(region)

        self.assertRegex(
            flat_region, r"(?i)when the legacy branch fires, report it to the user in one line",
            "the legacy branch does not report its determination to the user — the one branch of "
            "this gate that records no classification would leave no audit trail at all "
            "(FR-1.5, NFR-5, R10)",
        )
        self.assertRegex(
            flat_region, r"(?i)read as genuinely pre-change",
            "the legacy report does not state WHAT was determined (that the state file was read "
            "as genuinely pre-change) (FR-1.7)",
        )
        self.assertRegex(
            flat_region, r"(?i)on which two conditions it was so read",
            "the legacy report does not have to state the TWO conditions it fired on — a report "
            "that omits its own grounds is not the audit trail FR-1.5 requires (FR-1.7, NFR-5)",
        )
        self.assertRegex(
            flat_region, r'(?i)proceeds as "code", unclassified',
            "the legacy report does not state the consequence: the feature proceeds as \"code\", "
            "unclassified (FR-1.7)",
        )
        # The two conditions are not merely promised in the abstract — the report shape names them,
        # and it names the SECOND one in full (A5-6, Task 3 code review Medium). The pre-A5 template
        # hardcoded "`phase` already `implementation`" with no placeholder while the rule paragraph
        # and the C2 schema clause both say "`implementation` **or beyond**". A genuinely pre-change
        # feature resumed at `phase: "review"` or `"complete"` satisfies the rule and fires the
        # branch, then emits an audit line asserting a condition that did not hold for that file —
        # on the one branch of this gate that writes NOTHING to `.spec-state.json`, so that line is
        # the entire audit record (NFR-5) and it must not be false. The assertion is tightened to the
        # full condition so it agrees with its own failure message, which already claimed it.
        self.assertRegex(
            flat_region,
            r"(?i)featureClass absent AND phase already implementation or beyond",
            "the legacy report shape does not name the two conditions concretely (an absent "
            "`featureClass` AND a `phase` already at `implementation` or beyond) (FR-1.7, NFR-5, "
            "A5-6)",
        )
        # It stays FULLY LITERAL: no interpolated phase, path or username. The interpolated-phase
        # alternative the review suggested is rejected in design C1 item 10 — it would make this the
        # only interpolated value in a template that is literal by construction, and it buys nothing,
        # because "implementation or beyond" is true whenever the branch fires.
        template = re.search(r"```\n(.*?)```", region, re.DOTALL)
        self.assertIsNotNone(
            template,
            "the legacy determination has no fenced report template — the audit line's exact shape "
            "is what FR-1.5 and NFR-5 pin here",
        )
        self.assertNotRegex(
            template.group(1),
            r"<[^>]+>|\{[^}]+\}",
            "the legacy report template carries an interpolated placeholder. Design C1 item 10 "
            "keeps this line FULLY LITERAL — it names the two conditions and the resulting "
            "`\"code\"` treatment and nothing else: no path, no username, no observed state value "
            "(NFR-4, NFR-5, A5-6)",
        )
        # NFR-4: a report, never a prompt.
        self.assertRegex(
            flat_region, r"(?i)this is a report, not a prompt",
            "the legacy determination is not declared a REPORT rather than a prompt — NFR-4 "
            "forbids any additional user prompt on the code path (NFR-4)",
        )
        self.assertRegex(
            flat_region, r"(?i)it asks the user nothing",
            "the legacy report does not state that it asks the user nothing (NFR-4)",
        )
        self.assertRegex(
            flat_region, r"(?i)no additional user prompt on the code path.{0,20}is untouched",
            "the legacy report does not tie itself back to NFR-4's 'no additional user prompt on "
            "the code path' guarantee (NFR-4)",
        )
        self.assertNotRegex(
            flat_region,
            r"(?i)(ask the user|prompt the user|await (the user's )?(confirmation|response)|"
            r"wait for the user)",
            "the legacy determination has been turned into a user PROMPT. It must be a one-line "
            "report: NFR-4 guarantees the code path gains no additional user prompt, and a legacy "
            "state file is on the code path by definition (NFR-4, FR-1.7).",
        )

    def test_legacy_report_template_retired_the_pre_a5_condition_wording(self):
        """FR-1.5 / FR-1.7 / NFR-5 / A5-6 — sub-task 4.14: the corrected condition is asserted on the
        TEMPLATE itself, and the superseded wording is asserted GONE.

        `test_legacy_branch_reports_its_determination` now requires *"featureClass absent AND phase
        already implementation or beyond"* — but over `flat(region)`, which spans the prose *and* the
        fenced template. The rule paragraph above the fence already said "or beyond" before A5, so
        that assertion is satisfiable by the prose alone: the fenced audit line could keep its
        pre-A5 wording and stay green. The audit line is the one thing this branch writes anywhere —
        it writes nothing to `.spec-state.json` — so a false condition in it is the whole of the NFR-5
        defect, and the assertion has to bite on the template, not near it.

        The negative half is what makes this a regression guard rather than a restatement: A5-6 exists
        because the template asserted `phase` already `implementation` for a feature resumed at
        `phase: "review"` or `"complete"`, which fires the branch and does not satisfy that claim.
        Pinning the retired string keeps a future re-wrap from quietly reintroducing it.
        """
        region = self.sub_region(
            r"\*\*Report the legacy determination", r"\*\*What this gate never does",
            "'Report the legacy determination'",
        )
        template = re.search(r"```\n(.*?)```", region, re.DOTALL)
        self.assertIsNotNone(
            template,
            "the legacy determination has no fenced report template — the audit line's exact shape "
            "is what FR-1.5 and NFR-5 pin here",
        )
        # Wrapping-insensitive: the template hard-wraps mid-condition, and where the line break falls
        # is not the assertion.
        line = squash(template.group(1))

        self.assertIn(
            "`implementation` or beyond", line,
            "the fenced legacy-report template does not state the second condition in full. The "
            "rule paragraph and the C2 schema clause both say `implementation` **or beyond**, and "
            "this line is the entire audit record for the one branch of this gate that writes "
            "nothing to `.spec-state.json` — so it must not assert a condition that did not hold "
            f"(FR-1.7, NFR-5, A5-6). Template line: {line!r}",
        )
        self.assertNotIn(
            PRE_A5_LEGACY_TEMPLATE_WORDING, line,
            "the fenced legacy-report template still carries the pre-A5 wording "
            f"{PRE_A5_LEGACY_TEMPLATE_WORDING!r}. A feature genuinely predating this gate and "
            "resumed at `phase: \"review\"` or `\"complete\"` fires this branch and does NOT satisfy "
            "\"`phase` already `implementation`\", so the line emits a false condition on the one "
            "path that leaves no other trace (FR-1.7, NFR-5, A5-6)",
        )
        # The condition is a conjunction of two: correcting the second must not have dropped the
        # first, which is the discriminator's other half.
        self.assertIn(
            "`featureClass` absent AND", line,
            "the legacy-report template no longer names the FIRST condition (an absent "
            "`featureClass`) alongside the phase condition. Either alone is not the legacy "
            "discriminator: a freshly scaffolded feature has an absent `featureClass` too, and it is "
            "the phase that separates them (FR-1.7, NFR-5)",
        )

    def test_gate_region_carries_no_label_github_or_ci_operation(self):
        """FR-9.1 / FR-10.1 / design C1 'explicitly absent': the classification gate performs no
        remote action. No `ready-to-merge`, no label op, no github-agent call, no CI reference."""
        region = self.gate_region()
        prose = strip_fences(region)  # `CI workflows` legitimately appears inside the C0 fence

        self.assertNotIn(
            "ready-to-merge", region,
            "the classification-gate region mentions `ready-to-merge` — FR-9.1 forbids the "
            "non-code track introducing any second application point or exemption",
        )
        for token in ("blocked:", "action: label", "op: set", "op: clear", "github-agent",
                      "request-review", "sdd-review-gate", "ci-templates"):
            self.assertNotIn(
                token, region,
                f"the classification-gate region contains {token!r} — the gate writes no label "
                f"and makes no GitHub or CI call",
            )
        self.assertNotRegex(
            prose, r"\bCI\b",
            "the classification-gate region references CI outside the allow-list block (FR-10, NFR-2)",
        )
        self.assertRegex(
            flat(region), r"(?i)classification gate performs no GitHub action",
            "the gate does not state outright that it performs no GitHub action (design C1)",
        )


# --- (2) C0: the normative allow-list block ------------------------------------------------------


class AllowListBlockTest(OrchestratorDocTestCase):
    def allow_list_span(self):
        span = section_span(self.body, ALLOW_LIST_HEADING)
        self.assertIsNotNone(
            span,
            f"no heading with the exact title {ALLOW_LIST_HEADING!r} — design C0 fixes this "
            f"anchor verbatim in all five agents that classify",
        )
        return span

    def allow_list_block(self):
        """The fenced body of the C0 block, read from the LIVE file (never from the pin)."""
        start, end = self.allow_list_span()
        fence = re.search(r"```[a-zA-Z]*\n(.*?)```", self.body[start:end], re.DOTALL)
        self.assertIsNotNone(fence, "the allow-list section has no fenced block")
        return fence.group(1)

    def test_allow_list_heading_is_exact_and_inside_the_gate(self):
        """FR-1.3 / DD-5: the C0 heading is spelled exactly, is a `####` subsection, and lives
        inside the classification-gate section rather than floating elsewhere in the file."""
        start, _ = self.allow_list_span()
        level = next(lvl for _, lvl, t in headings(self.body) if t == ALLOW_LIST_HEADING)
        self.assertEqual(level, 4, "the allow-list must be a `####` subsection (design C0)")

        gate_start, gate_end = self.gate_span()
        self.assertTrue(
            gate_start < start < gate_end,
            "the allow-list block sits outside the Feature Classification Gate section",
        )

    def test_allow_list_heading_is_immediately_followed_by_its_fenced_body(self):
        """DD-5: heading then fence, with no intervening prose — so a downstream agent can lift the
        block verbatim by anchoring on the heading."""
        start, end = self.allow_list_span()
        section = self.body[start:end]
        lines = section.splitlines()[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        self.assertTrue(lines, "the allow-list heading is followed by nothing at all")
        self.assertTrue(
            lines[0].lstrip().startswith("```"),
            "the allow-list heading is not immediately followed by a fenced block — found "
            f"{lines[0]!r} in between",
        )

    def test_allow_list_body_matches_the_canonical_block(self):
        """FR-1.3 / DD-5 / A5-1 (A5 item 2.1): the fenced body is the canonical C0 text,
        **byte-for-byte**.

        A5 item 2.1 says byte-for-byte, and it means it. This comparison used `squash()`, which
        collapses every whitespace run — so it could not distinguish the fence from a copy with
        different indentation, different wrapping, or a blank line moved between the three blocks.
        That is not a cosmetic tolerance here. `CANONICAL_ALLOW_LIST` is the constant Tasks 6, 7 and 8
        replicate *against*, and Task 8 asserts all five copies are identical: a whitespace-insensitive
        pin cannot catch an indentation divergence in a replica, and indentation is load-bearing in
        this block, which uses two-space continuation to bind each criterion to the category it
        qualifies. Re-indented, `WHERE the PRECEDENCE CHECK below passes for it` can read as
        qualifying category 3.

        So the pin is exact, and the diagnostics fall back to `squash()` only to tell the reader
        *which kind* of drift happened — whitespace-only, or substantive.
        """
        live = self.allow_list_block()
        if live != CANONICAL_ALLOW_LIST:
            whitespace_only = squash(live) == squash(CANONICAL_ALLOW_LIST)
            kind = (
                "WHITESPACE-ONLY drift (indentation, wrapping or blank lines). This still fails: "
                "indentation binds each criterion to the category it qualifies, and Task 8 asserts "
                "the five copies identical, so a tolerance here becomes a tolerance in four replicas"
                if whitespace_only else
                "SUBSTANTIVE drift — the wording itself differs"
            )
            diff = "\n".join(
                f"    {marker} {line!r}"
                for marker, line in (
                    [("pin  ", pin_line) for pin_line in CANONICAL_ALLOW_LIST.splitlines()
                     if pin_line not in live.splitlines()]
                    + [("live ", live_line) for live_line in live.splitlines()
                       if live_line not in CANONICAL_ALLOW_LIST.splitlines()]
                )
            )
            self.fail(
                "the C0 allow-list block has drifted from its canonical text (design C0, DD-5, "
                f"A5-1).\n  {kind}.\n  Lines present in only one of the two:\n{diff}\n"
                "  This block is normative and is replicated verbatim into four other agent "
                "contracts; change it in design C0 first, then re-pin `CANONICAL_ALLOW_LIST`, then "
                "all five copies."
            )

    def test_provenance_sentence_sits_outside_the_fence_and_is_absent_from_the_pin(self):
        """DD-5 / sub-task 4.9: the provenance note is OUTSIDE the closing fence and OUT of the pin.

        This is the DD-5 **inversion guard**, and nothing else in the suite is it.
        `test_allow_list_declares_this_file_the_normative_home` asserts the sentence exists and is
        deixis-free, but it searches the whole flattened gate — so it is equally satisfied whether the
        sentence sits above the fence, below it, or *inside* it. Sub-task 4.9 says the sentence stays
        in place and is **not** part of what Tasks 6, 7 and 8 replicate. Those tasks lift "the heading
        and its fenced body"; the only mechanical fact that keeps the sentence out of the four
        replicas is that it is not in the fenced body, and the only fact that keeps it out of what
        Task 8's identity assertion locks down is that it is not in `CANONICAL_ALLOW_LIST`.

        Invert either and the damage is specific, not stylistic: four agent contracts would each
        declare, of themselves, that `agents/orchestrator.md` is the normative home *of the block the
        replica is currently stating* — and Task 8 would then assert that inversion is byte-identical
        across all five copies, freezing it. A tie-breaker that ships inside the thing it breaks ties
        for is the one arrangement DD-5 cannot survive.
        """
        start, end = self.allow_list_span()
        section = self.body[start:end]
        fence = re.search(r"```[a-zA-Z]*\n(.*?)```", section, re.DOTALL)
        self.assertIsNotNone(fence, "the allow-list section has no fenced block")
        body_of_fence = fence.group(1)

        home_at = section.find(PROVENANCE_HOME_PHRASE)
        self.assertNotEqual(
            home_at, -1,
            "the allow-list section carries no provenance note naming its normative home — DD-5's "
            f"tie-breaker for a divergent replica. Expected the phrase {PROVENANCE_HOME_PHRASE!r}",
        )
        self.assertGreater(
            home_at, fence.end(),
            "the provenance note sits at or before the CLOSING fence of the C0 block. Tasks 6/7/8 "
            "replicate the heading and the fenced body; a note inside that body ships into four "
            "other agent contracts, where each replica would assert of itself that the *orchestrator* "
            "is the normative home of the block it is stating — and Task 8's identity assertion would "
            "then freeze that inversion in all five copies (DD-5, sub-task 4.9)",
        )
        for phrase, what in (
            (PROVENANCE_HOME_PHRASE, "the normative-home declaration"),
            (PROVENANCE_TIEBREAK_PHRASE, "the which-copy-wins tie-breaker"),
        ):
            self.assertNotIn(
                phrase, body_of_fence,
                f"{what} appears INSIDE the fenced C0 body. It must live in the prose that follows "
                f"the fence: the fenced body is what Tasks 6/7/8 lift verbatim into four other "
                f"contracts (DD-5, sub-task 4.9)",
            )

        # And out of the pin, in both directions — the pin is what the replicas are compared against,
        # so a sentence smuggled in here would make its own replication the "correct" outcome.
        for token, why in (
            ("normative home", "the normative-home declaration"),
            ("wins", "the which-copy-wins tie-breaker"),
            ("verbatim replica", "the replica list"),
            ("agents/orchestrator.md", "the normative home's own filename"),
            ("agents/task-tester.md", "a replica filename"),
            ("agents/task-validator.md", "a replica filename"),
            ("agents/code-reviewer.md", "a replica filename"),
            ("agents/security-reviewer.md", "a replica filename"),
        ):
            self.assertNotIn(
                token, CANONICAL_ALLOW_LIST,
                f"`CANONICAL_ALLOW_LIST` contains {token!r} — {why} has leaked into the pin. The pin "
                f"is the text Tasks 6/7/8 replicate against and Task 8 asserts identical across five "
                f"copies, so anything in it becomes required in every replica. The provenance note is "
                f"deliberately outside it (DD-5, sub-task 4.9)",
            )
        # The `agents/*.md` glob on the application-code side is a classification criterion and is
        # expected in the pin; the specific per-agent filenames above are not. Guard the distinction
        # so the loop above cannot be "fixed" by deleting the glob.
        self.assertIn(
            "agents/*.md", CANONICAL_ALLOW_LIST,
            "the pin lost the `agents/*.md` glob. It is a classification CRITERION (this project's "
            "agent contracts are application code) and belongs in the replicated fence — unlike the "
            "provenance note's per-file replica list, which does not (FR-1.3, DD-5)",
        )

    def test_allow_list_names_all_three_categories_and_the_code_catch_all(self):
        """FR-1.3 / NFR-6: the substantive content — the three non-code categories and the
        application-code catch-all naming this repository's contract globs."""
        block = self.allow_list_block()

        self.assertIn("NON-CODE ARTIFACT", block)
        self.assertIn("exactly one of", block,
                      "the three categories are not stated as mutually exclusive alternatives")
        # (1) spec artifacts
        self.assertIn(".specs/features/<feature-name>/", block)
        for spec_file in ("requirements.md", "design.md", "tasks.md", "scope.md",
                          ".spec-state.json"):
            self.assertIn(spec_file, block,
                          f"spec artifact {spec_file} missing from allow-list category 1")
        # (2) prose/documentation, with the steering-designation exclusion
        self.assertRegex(block, r"(?i)prose/documentation file")
        self.assertRegex(
            block, r"(?i)does NOT\s+designate as source, agent/prompt contract, template, "
                   r"script, or configuration",
            "allow-list category 2 lacks the steering-designation exclusion",
        )
        # (3) vault mutation, by its in-repo changelog path
        self.assertIn(".specs/features/<feature-name>/vault/.write-log.jsonl", block,
                      "allow-list category 3 does not name the vault changelog path")
        self.assertIn("vault-writer", block)
        # Catch-all
        self.assertIn("APPLICATION CODE", block)
        self.assertIn("anything else", block,
                      "APPLICATION CODE is not defined as the catch-all complement")
        for token in ("executable source", "tests", "scripts", "hooks", "CI workflows",
                      "templates", "runtime configuration"):
            self.assertIn(token, block, f"application-code enumeration omits {token!r}")
        self.assertIn("agents/*.md", block,
                      "the allow-list does not designate agents/*.md as application code")
        self.assertIn("commands/*.md", block,
                      "the allow-list does not designate commands/*.md as application code")

    def test_allow_list_enumeration_is_open_on_both_sides_and_names_claude_md_and_readme_md(self):
        """FR-1.3 / A3-3 / A4-1: the repository enumeration is OPEN on both sides, and each side
        names its worked example WITH the criterion that puts it there.

        A closed enumeration would make "not listed" mean "not application code", so any prose file
        the project later designates as a contract would classify non-code by omission. And the two
        hard cases must be settled by name: the repository-root `CLAUDE.md` is prose the project
        loads into every agent's context (application code), while the repository-root `README.md`
        is prose nothing loads (category-2 non-code). Naming them without the criterion would
        settle two files; naming the criterion generalises to the next file like them.

        **A5-2: the two namings are not symmetric, and the fence must say so.** `CLAUDE.md` is
        settled application code unconditionally — the error direction there costs extra review.
        `README.md` is named as a **condition**, pointing at the fence's own bounded `PRECEDENCE`
        CHECK, because this fence ships to consumer projects through `install.sh` and "in this
        repository" rebinds there: a consumer whose `CLAUDE.md` carries `@README.md` has a
        behaviour-bearing README, and settling it non-code *by name* would hand it the tester's
        no-code behaviour and the validator's artifact-conformance mode on a criterion that is
        false. So the non-code naming must read as a gate, not as an apposition justifying itself,
        and the contrapositive — check fails or was never run → application code — must be present
        in the fence rather than left to the reader (A5-2, DD-17).
        """
        block = self.allow_list_block()
        flat_block = flat(block)

        self.assertEqual(
            len(re.findall(r"(?i)include, but are not limited to", block)), 2,
            "the repository enumeration is not stated as OPEN on BOTH sides — the phrase "
            "'include, but are not limited to' must appear once in the non-code category 2 and "
            "once in the application-code catch-all (FR-1.3, A3-3)",
        )
        self.assertNotRegex(
            flat_block, r"(?i)(exhaustive|only the following|and nothing else)",
            "the repository enumeration is closed — absence from either list must be evidence of "
            "nothing (A3-3, A4-1)",
        )

        # The application-code side: CLAUDE.md, with the criterion that puts it there.
        self.assertIn(
            "CLAUDE.md", block,
            "the allow-list does not name the repository-root CLAUDE.md at all (A3-3)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)the repository-root CLAUDE\.md .{0,20}a contract the project loads into every "
            r"agent's context at session start",
            "the repository-root CLAUDE.md is not designated application code WITH its criterion "
            "(the project loads it into every agent's context as a behaviour-bearing contract) "
            "(FR-1.3, A3-3)",
        )
        claude_at = flat_block.index("CLAUDE.md")
        self.assertGreater(
            claude_at, flat_block.index("APPLICATION CODE"),
            "the repository-root CLAUDE.md is named on the NON-CODE side of the enumeration — it "
            "is a behaviour-bearing contract and belongs to APPLICATION CODE (FR-1.3, A3-3)",
        )

        # The non-code side: README.md, named as a CONDITION rather than with an apposition that
        # merely justifies the naming (A5-2). The gloss must point at the fence's own bounded check.
        self.assertIn(
            "README.md", block,
            "the allow-list does not name the repository-root README.md at all (A3-3)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)the repository-root README\.md .{0,20}WHERE the PRECEDENCE CHECK below passes "
            r"for it",
            "the repository-root README.md is not named on the non-code side as a CONDITION "
            "pointing at the fence's own bounded PRECEDENCE CHECK. A4's apposition gloss "
            "(\"descriptive documentation that nothing loads into an agent's context\") reads as a "
            "justification for the naming rather than a gate on it, and `PRECEDENCE` then settled "
            "the file regardless — in a consumer project whose `CLAUDE.md` imports its README, that "
            "hands a behaviour-bearing contract the tester's no-code behaviour and the validator's "
            "artifact-conformance mode on a false criterion (FR-1.3, A5-2, DD-17)",
        )
        # The A4 apposition must be gone, not merely joined by the condition: two glosses on the
        # same naming is the NFR-6 drift shape, and the weaker one is the one a reader will apply.
        self.assertNotRegex(
            flat_block,
            r"(?i)README\.md .{0,20}descriptive documentation that nothing loads into an agent's "
            r"context",
            "the fence still carries A4's unconditional apposition gloss on the README.md naming "
            "alongside A5's condition. The naming is conditional or it is not; leaving both lets a "
            "classifier settle the file non-code without running the check (A5-2)",
        )
        readme_at = flat_block.index("README.md")
        self.assertLess(
            readme_at, flat_block.index("APPLICATION CODE"),
            "the repository-root README.md is named on the APPLICATION CODE side of the "
            "enumeration — nothing loads it into an agent's context, so it is a category-2 "
            "non-code artifact (FR-1.3, A3-3)",
        )
        # A5-2: the condition is only a condition if its FAILING branch is stated. A criterion with
        # no contrapositive is a negative existential satisfied by not looking — the fall-through
        # would land a behaviour-bearing README back in category 2 by the very category tests
        # `PRECEDENCE` decides ahead of.
        self.assertRegex(
            flat_block,
            r"(?i)a FAILED OR UNRUN CHECK IS ITSELF THE DESIGNATION: the file is APPLICATION CODE",
            "the fence states the README.md naming as a condition but omits its contrapositive — a "
            "failed or unrun check must itself be the project's designation, settling the file as "
            "APPLICATION CODE (FR-1.3, FR-1.4, A5-2, DD-17)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)do not fall back to the category tests for it",
            "the fence does not forbid falling back to the category tests after a failed or unrun "
            "check — the fall-through is what puts a behaviour-bearing README back in category 2 "
            "(A5-2, DD-17)",
        )

    def test_allow_list_precedence_clause_subordinates_the_ambiguity_triggers(self):
        """FR-1.3 / FR-1.4 / A4-1 / A5-1 / A5-2: the fenced block carries the `PRECEDENCE` stanza,
        and it is the stanza that is replicated — so the ordering rule travels with the enumeration.

        The enumeration and the AMB triggers are two rules over the same files. Without an explicit
        ordering, `CLAUDE.md` is both "application code by enumeration" and "prose in a directory
        steering designates as contract" (AMB-3), and a reader may take either. The `PRECEDENCE`
        stanza must live INSIDE the fence: Tasks 6/7/8 replicate only the fenced block into four
        other agent contracts, so a precedence rule stated outside it would not reach them.

        **A5 rescopes it in two directions, and both are asserted here.**

        *Asymmetry (A5-2).* A4's clause settled every named file unconditionally, on both sides.
        That is right for the application-code side (an error there costs extra testing) and wrong
        for the non-code side (an error there costs the test gate), so the stanza must settle the
        application-code side unconditionally and the non-code side only where its bounded check has
        been **run** and passes, with a failed or unrun check settling the file as application code.

        *Trigger scope (A5-1).* A4 subordinated AMB-1 **through** AMB-5 to what is a **file**
        enumeration. AMB-1 ("a task declares no outputs") and AMB-5 ("`tasks.md` declares no tasks")
        are feature-level triggers about missing declarations and name no file, so read literally
        that clause disabled AMB-5: a zero-task feature has no *file* the enumeration fails to
        settle, so AMB-5 never fires, so the per-feature rule's two vacuously-true universals stand
        and the feature classifies `"non-code"` — the same amendment that added AMB-5 to close the
        vacuous-truth hole reopening it. Only AMB-2…AMB-4 may be subordinated.
        """
        block = self.allow_list_block()
        flat_block = flat(block)

        self.assertIn(
            "PRECEDENCE", block,
            "the fenced C0 block carries no `PRECEDENCE` stanza — Tasks 6/7/8 replicate this fence "
            "and only this fence, so the subordination rule would not reach the four replicas "
            "(A4-1, DD-5)",
        )
        # (i) Decided ahead of the category tests, and declared asymmetric in the fence itself, so
        #     the asymmetry travels into the four replicas rather than staying design-side rationale.
        self.assertRegex(
            flat_block,
            r"(?i)PRECEDENCE — decided BEFORE the category tests above, and ASYMMETRIC",
            "the `PRECEDENCE` stanza does not state that it is decided BEFORE the category tests "
            "and that it is ASYMMETRIC between the two sides (A5-2)",
        )
        # (ii) The application-code side: unconditional.
        self.assertRegex(
            flat_block,
            r"(?i)a file named on the APPLICATION CODE side is settled application code, "
            r"UNCONDITIONALLY",
            "the `PRECEDENCE` stanza does not settle the application-code side UNCONDITIONALLY — "
            "the safe direction must stay unconditional (FR-1.3, A5-2)",
        )
        # (iii) The non-code side: conditional on the check having been RUN and passing.
        self.assertRegex(
            flat_block,
            r"(?i)a file named on the NON-CODE side is settled non-code ONLY IF YOU RUN its CHECK "
            r"and it passes",
            "the `PRECEDENCE` stanza settles the non-code side without requiring its bounded check "
            "to have been RUN and passed — an unrun check is a criterion satisfied by not looking "
            "(FR-1.3, FR-1.4, A5-2, DD-17)",
        )
        # (iv) The check is bounded: it names the surface to read and what counts as a hit, and it
        #      excludes a mere mention (that exclusion is load-bearing in THIS repository, whose
        #      CLAUDE.md mentions README.md once without loading it — AC-2 / Flow B depend on it).
        for pattern, why in (
            (r"(?i)read the repository-root CLAUDE\.md, the files it imports, and \.specs/steering",
             "name the surface the check reads (the repository-root CLAUDE.md, the files it "
             "imports, and .specs/steering/*.md)"),
            (r"(?i)an @-import, a session-start read instruction, or a designation of it as a "
             r"contract or standard",
             "name what counts as a hit (an @-import, a session-start read instruction, or a "
             "designation as a contract or standard)"),
            (r"(?i)a mere mention is not a load",
             "exclude a mere mention of the filename from counting as a load — without it the "
             "check fails in this very repository and AC-2 / Flow B become unreachable here"),
            (r"(?i)it FAILS if you did not run it",
             "declare an UNRUN check FAILED — otherwise the criterion is a negative existential "
             "satisfied by never looking"),
        ):
            self.assertRegex(
                flat_block, pattern,
                f"the `PRECEDENCE` CHECK is not bounded: it does not {why} (A5-2, DD-17)",
            )
        # (v) The contrapositive, and no fall-through to the category tests.
        self.assertRegex(
            flat_block,
            r"(?i)a FAILED OR UNRUN CHECK IS ITSELF THE DESIGNATION: the file is APPLICATION CODE\. "
            r"Do not fall back to the category tests for it",
            "the `PRECEDENCE` stanza does not state that a failed or unrun check is itself the "
            "project's designation, settling the file as APPLICATION CODE with no fall-back to the "
            "category tests (FR-1.4, A5-2, DD-17)",
        )
        # (vi) A5-1: only the FILE-CLASSIFYING triggers are subordinated, and they are named.
        self.assertRegex(
            flat_block,
            r"(?i)AMB-2, AMB-3 and AMB-4 are FILE-CLASSIFYING triggers: they apply only to a file "
            r"this enumeration does not settle",
            "the `PRECEDENCE` stanza does not subordinate exactly the FILE-CLASSIFYING triggers "
            "AMB-2…AMB-4 to the enumeration by name (FR-1.4, A5-1)",
        )
        self.assertRegex(
            flat_block, r"(?i)and never override one it does",
            "the `PRECEDENCE` stanza does not forbid a file-classifying trigger OVERRIDING a file "
            "the enumeration settles — subordination without that clause is advisory (FR-1.4, "
            "A4-1, A5-1)",
        )
        # (vii) A5-1: AMB-1 and AMB-5 are declared feature-level and UNAFFECTED. Both halves matter:
        #       naming them without "always apply" leaves their status open, and "always apply"
        #       without the reason (they name no file) invites a later reader to re-subordinate them.
        self.assertRegex(
            flat_block,
            r"(?i)AMB-1 \(a task declares no outputs\) and AMB-5 \(tasks\.md declares no tasks\) "
            r"are FEATURE-LEVEL triggers about missing declarations, name no file, and always apply",
            "the `PRECEDENCE` stanza does not declare AMB-1 and AMB-5 FEATURE-LEVEL triggers that "
            "name no file and ALWAYS apply. A4 subordinated all five to a FILE enumeration, which "
            "read literally disabled AMB-5: a zero-task feature has no unsettled file, so the "
            "trigger added to close the vacuous-truth hole would never fire and a task-less feature "
            "would classify \"non-code\" (FR-1.4, A5-1)",
        )
        # The A4 over-broad form must be GONE, not merely supplemented.
        self.assertNotRegex(
            flat_block,
            r"(?i)AMB-1 through AMB-5 apply only to a file this enumeration does not already settle",
            "the fence still subordinates AMB-1 THROUGH AMB-5 to the enumeration. AMB-1 and AMB-5 "
            "are feature-level and name no file, so subordinating them to a file enumeration "
            "disables AMB-5 over the one input it exists for (A5-1)",
        )
        self.assertNotRegex(
            flat_block,
            r"(?i)this enumeration settles every file it names, on the side it names it",
            "the fence still carries A4's symmetric 'settles every file it names' wording, which "
            "settles the non-code side unconditionally — the very naming A5-2 made conditional",
        )
        self.assertRegex(
            flat_block,
            r"(?i)both lists stay open: a file's absence from either list is evidence of nothing",
            "the `PRECEDENCE` stanza does not keep both lists open — without it, omission from "
            "the enumeration becomes an argument (A3-3, A4-1)",
        )
        # The inversion: the ordering must never be stated the other way round.
        self.assertNotRegex(
            flat_block,
            r"(?i)(this )?enumeration[^.]{0,60}(is subordinate to|yields to|defers to|"
            r"gives way to)",
            "the fenced block subordinates the ENUMERATION to the ambiguity triggers — A4-1 "
            "requires the opposite ordering: the enumeration settles, the triggers only fill the "
            "gaps it leaves (FR-1.3, FR-1.4)",
        )

    def test_allow_list_declares_this_file_the_normative_home(self):
        """DD-5 / R1: the block states where it is normative and which copies are replicas, so a
        divergence has a documented tie-breaker."""
        gate = flat(self.gate_region())
        self.assertRegex(
            gate, r"(?i)agents/orchestrator\.md is the normative home",
            "the allow-list does not declare agents/orchestrator.md its normative home (DD-5)",
        )
        for replica in ("agents/task-tester.md", "agents/task-validator.md",
                        "agents/code-reviewer.md", "agents/security-reviewer.md"):
            self.assertIn(
                replica, gate,
                f"the provenance note does not name {replica} as a verbatim replica (DD-5, R1)",
            )
        self.assertRegex(
            gate,
            r"(?i)verbatim replicas.{0,160}agents/orchestrator\.md wins",
            "the provenance note does not name `agents/orchestrator.md` as the copy that wins on "
            "disagreement (DD-5, R1)",
        )
        # The tie-breaker must be DEIXIS-FREE. Tasks 6/7/8 replicate this sentence verbatim into
        # four other agent contracts; a self-referential "this one wins" would then assert, inside
        # each replica, that the replica beats the normative home — inverting DD-5 in four files.
        self.assertNotRegex(
            gate, r"(?i)verbatim replicas.{0,160}this (one|copy|file) wins",
            "the provenance tie-breaker is deictic (\"this one wins\"). It is replicated verbatim "
            "into four other agent contracts by Tasks 6/7/8, where \"this\" would resolve to the "
            "replica and invert DD-5. Name `agents/orchestrator.md` explicitly.",
        )


# --- (3) C2: the `.spec-state.json` schema delta -------------------------------------------------


class StateSchemaTest(OrchestratorDocTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        start = cls.body.index("## State File Management")
        end = cls.body.index("## Critical Rules", start)
        m = re.search(
            r"Initialize new features with:\s*```json\n(.*?)```", cls.body, re.DOTALL,
        )
        assert m, "the State File Management initialization JSON block was not found"
        # The JSON block is searched over the whole body while the section bounds are computed
        # independently, so pin the match INSIDE `## State File Management`. Were an earlier
        # "Initialize new features with:" block ever to appear, `schema_prose` would silently span
        # unrelated text (or invert) and every assertion below would be measuring the wrong slice.
        assert m.start() > start, (
            "the 'Initialize new features with:' JSON block matched at offset "
            f"{m.start()}, BEFORE '## State File Management' at {start} — the schema-prose slice "
            "would cover unrelated text"
        )
        assert m.end() < end, (
            "the 'Initialize new features with:' JSON block ends at offset "
            f"{m.end()}, at or after '## Critical Rules' at {end} — the schema-prose slice would "
            "be empty or inverted"
        )
        cls.init_json_raw = m.group(1)
        cls.schema_prose = cls.body[m.end():end]

    def test_init_block_still_parses_as_json(self):
        """NFR-6: the initialization block is a real JSON document — the schema delta must not have
        broken it (a trailing comma here would ship a state file nobody can write)."""
        try:
            parsed = json.loads(self.init_json_raw)
        except json.JSONDecodeError as exc:
            self.fail(f"the initialization block no longer parses as JSON: {exc}")
        self.assertIsInstance(parsed, dict)

    def test_init_block_declares_feature_class_and_classification(self):
        """FR-1.1 / C2: `featureClass` (null-initialised) and the five-key `classification` object
        are present as sibling top-level keys, and every pre-existing key survived."""
        parsed = json.loads(self.init_json_raw)

        self.assertIn("featureClass", parsed,
                      "`featureClass` is missing from the state-file initialization block (FR-1.1)")
        self.assertIsNone(parsed["featureClass"],
                          "`featureClass` must initialise to null (before the gate has run)")

        self.assertIn("classification", parsed, "the `classification` object is missing (C2)")
        self.assertIsInstance(parsed["classification"], dict)
        self.assertEqual(
            sorted(parsed["classification"]), sorted(CLASSIFICATION_SUBKEYS),
            "the `classification` object does not carry exactly the five C2 sub-keys",
        )
        self.assertEqual(
            parsed["classification"]["tasksValidatedUnderExemption"], [],
            "`tasksValidatedUnderExemption` must initialise to an empty array (FR-3.3)",
        )
        for key in ("basis", "decidedAt", "override", "reclassification"):
            self.assertIsNone(parsed["classification"][key],
                              f"`classification.{key}` must initialise to null")

        # Regression: the delta is additive — nothing pre-existing was dropped.
        for key in ("feature", "phase", "lastModified", "confirmed", "implementationProgress",
                    "taskStatus", "featureReview", "escalations"):
            self.assertIn(key, parsed,
                          f"pre-existing state key {key!r} was dropped by the schema delta")

    def test_new_keys_are_siblings_placed_after_task_status(self):
        """C2: `featureClass` and `classification` are added as sibling top-level keys AFTER
        `taskStatus`, not nested inside it."""
        parsed = json.loads(self.init_json_raw)
        self.assertNotIn("featureClass", parsed.get("taskStatus", {}),
                         "`featureClass` was nested inside taskStatus instead of being a sibling")
        order = {k: self.init_json_raw.index(f'"{k}"') for k in
                 ("taskStatus", "featureClass", "classification", "featureReview")}
        self.assertLess(order["taskStatus"], order["featureClass"])
        self.assertLess(order["featureClass"], order["classification"])
        self.assertLess(order["classification"], order["featureReview"])

    def test_schema_prose_names_both_permitted_values_and_the_absent_states(self):
        """FR-1.1 / FR-1.7: the schema prose names exactly two permitted values, and documents the
        `null`-before-gate and absent-in-legacy-file states with their `"code"` default."""
        prose = flat(self.schema_prose)
        self.assertRegex(
            prose, r"(?i)featureClass is the feature classification",
            "the schema prose does not document `featureClass` at all (FR-1.1)",
        )
        self.assertRegex(
            prose, r'(?i)permitted values are exactly two: "code" or "non-code"',
            "the schema prose does not name both permitted values \"code\" and \"non-code\" "
            "(FR-1.1)",
        )
        self.assertRegex(
            prose, r"(?i)no other value is valid",
            "the schema prose does not close the value set (a third value must be invalid)",
        )
        self.assertRegex(
            prose, r"(?i)null before the classification gate has run",
            "the schema prose does not document the null-before-gate state",
        )
        self.assertRegex(
            prose, r"(?i)absent from a state file written before this key existed",
            "the schema prose does not document the absent-in-legacy-file state (FR-1.7)",
        )
        self.assertRegex(
            prose, r'(?i)read an absent featureClass with a default of "code"',
            "the schema prose does not give the \"code\" default for an absent key (FR-1.7)",
        )
        self.assertRegex(
            prose, r"(?i)featureClass is the single source of truth",
            "the schema prose does not name `featureClass` the single source of truth (C2)",
        )
        self.assertRegex(
            prose, r"(?i)classification object carries only provenance",
            "the schema prose does not confine `classification` to provenance (C2)",
        )

    def test_schema_prose_defines_null_feature_class_at_every_consumer(self):
        """FR-1.1 / FR-1.7 / NFR-5: `null` is defined for the CONSUMERS, not just for the writer.

        The initialization block ships `"featureClass": null`, so `null` is the value every
        downstream reader added by Tasks 3/6/7/8 will meet first. Left undefined, each of them
        would have to invent a reading, and "not code" is the tempting one — which would run the
        artifact-conformance path over an unclassified feature. The schema must fix `null` as an
        exact synonym for absent, defaulting to `"code"`, and must forbid it being treated as a
        third classification or forwarded as one.
        """
        prose = flat(self.schema_prose)
        self.assertRegex(
            prose, r"(?i)a null featureClass reaching any consumer",
            "the schema prose does not say what a `null` `featureClass` means when it reaches a "
            "consumer — Tasks 3/6/7/8 would each inherit an undefined value (FR-1.1)",
        )
        for consumer, why in (
            (r"per-task routing", "the Stage 2-5 routing preamble (FR-2)"),
            (r"task-tester", "the tester (FR-4)"),
            (r"task-validator", "the validator (FR-3)"),
            (r"either reviewer", "the code and security reviewers (FR-5, FR-6)"),
            (r"feature-review gate", "the whole-feature review gate (FR-8)"),
        ):
            self.assertRegex(
                prose, rf"(?i)a null featureClass reaching any consumer.{{0,200}}{consumer}",
                f"the `null` rule does not enumerate {consumer!r} as a consumer — {why} would be "
                f"left without a defined reading (FR-1.1, NFR-5)",
            )
        self.assertRegex(
            prose, r"(?i)the feature is unclassified",
            "the schema prose does not state that a `null` `featureClass` means the feature is "
            "UNCLASSIFIED (the gate has not run)",
        )
        self.assertRegex(
            prose, r'(?i)read null exactly as you read an absent value and treat it as "code"',
            "the schema prose does not equate `null` with absent and default it to \"code\" — "
            "this is the rule that keeps a pre-gate state file on the unchanged code path "
            "(FR-1.1, FR-1.7)",
        )
        self.assertRegex(
            prose, r"(?i)null is never a third classification",
            "the schema prose does not close the value set against `null` becoming a third "
            "classification alongside \"code\" and \"non-code\" (FR-1.1)",
        )
        self.assertRegex(
            prose, r"(?i)never forwarded to a consumer as if it were one",
            "the schema prose does not forbid forwarding `null` to a consumer as a "
            "classification (FR-1.1, FR-2)",
        )

    def test_null_consumer_list_names_the_reclassification_subsection(self):
        """FR-1.1 / A3-1 / A4-1: the `null`-is-unclassified consumer list must also name the C4
        reclassification subsection.

        C4 reads `featureClass` to decide whether a feature is already `"code"` (and so whether the
        monotonic non-code → code transition applies at all). Left out of this list, it is the one
        consumer with no defined reading of `null` — and the tempting reading, "not yet code", is
        the one that would let a reclassification fire over a feature that was never classified.
        The whole point of A3-1 is that no consumer invents its own reading, so the list must be
        complete, not merely non-empty.
        """
        prose = flat(self.schema_prose)
        consumers = re.search(
            r"(?i)a null featureClass reaching any consumer(.*?)means the classification gate has "
            r"not run",
            prose,
        )
        self.assertIsNotNone(
            consumers,
            "the `null`-reaching-a-consumer sentence has no 'means the classification gate has not "
            "run' tail — the consumer enumeration could not be scoped, and asserting over the "
            "whole schema prose would let any later paragraph satisfy it (FR-1.1)",
        )
        listed = consumers.group(1)
        for consumer, why in (
            ("per-task routing", "the Stage 2-5 routing preamble (C3, FR-2)"),
            ("task-tester", "the tester (C6, FR-4)"),
            ("task-validator", "the validator (C7, FR-3)"),
            ("either reviewer", "the code and security reviewers (C8/C9, FR-5, FR-6)"),
            ("feature-review gate", "the whole-feature review gate (C5, FR-8)"),
            ("reclassification subsection", "the non-code → code fallback (C4, FR-3)"),
        ):
            self.assertIn(
                consumer, listed,
                f"the `null` consumer enumeration omits {consumer!r} — {why} would be left to "
                f"invent its own reading of `null` (FR-1.1, A3-1, A4-1)",
            )

    def test_schema_prose_states_that_absence_is_not_by_itself_a_legacy_signal(self):
        """FR-1.1 / FR-1.7 / A3-5: the `"code"`-for-absent default is a READER's default, and must
        be fenced off from the legacy discriminator.

        Two true statements sit next to each other here — "read an absent `featureClass` as
        `"code"`" and "an absent `featureClass` means a pre-change state file" — and only the first
        is unconditionally true. Read together they license skipping the classification gate for
        every freshly scaffolded feature, because `/sdd-feature` writes a state file with no
        `featureClass` key at all. The schema prose must therefore say, in the same breath as the
        default, that absence alone decides nothing about the gate.
        """
        region = self.slice_between(
            self.schema_prose,
            r"\*\*Absence is not, by itself, a legacy signal",
            r"single source of truth",
            "'Absence is not, by itself, a legacy signal'",
            container="`## State File Management` schema prose",
        )
        flat_region = flat(region)

        self.assertRegex(
            flat_region, r"(?i)absence is not, by itself, a legacy signal",
            "the schema prose does not qualify the absent-key default with the "
            "'absence is not, by itself, a legacy signal' clause (FR-1.7, A3-5)",
        )
        self.assertRegex(
            flat_region, r"(?i)default above is a reader's default",
            "the schema prose does not scope the \"code\" default as a READER's default — the "
            "distinction between how a consumer reads the key and what its absence proves is the "
            "whole content of A3-5 (FR-1.1, FR-1.7)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)absence also means the classification gate has not yet run",
            "the schema prose does not state the second, weaker meaning of absence (the gate has "
            "not yet run over this feature) (FR-1.1, A3-5)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)only the Feature Classification Gate's two-condition rule .{0,120}"
            r"decides whether absence is a genuinely pre-change state file",
            "the schema prose does not defer to the Feature Classification Gate's TWO-condition "
            "rule as the only thing that decides whether absence means 'pre-change' (FR-1.7)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)featureClass absent and phase already implementation or beyond",
            "the schema prose cites the two-condition rule without naming its two conditions "
            "(FR-1.7, A3-5)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)never be cited to justify skipping the gate for a freshly scaffolded feature",
            "the schema prose does not forbid citing the absent-key default to justify SKIPPING "
            "the gate for a freshly scaffolded feature — that misuse is exactly the silent "
            "switch-off A3-5 closes (FR-1.1, FR-1.7)",
        )
        self.assertIn(
            "commands/sdd-feature.md", region,
            "the schema prose does not name `commands/sdd-feature.md` as the command that writes "
            "a state file with no `featureClass` key at all — the evidence that bare absence is "
            "the ordinary state of every new feature (FR-1.7, A3-5)",
        )

    def test_schema_prose_documents_all_five_classification_subkeys(self):
        """FR-1.5 / FR-1.6 / FR-3.1 / FR-3.3 / NFR-5: each sub-key is documented with substantive
        content, not merely listed."""
        prose = flat(self.schema_prose)
        for key in CLASSIFICATION_SUBKEYS:
            self.assertRegex(
                prose, rf"(?i)classification\.{key}\b",
                f"`classification.{key}` is not documented in the schema prose",
            )
        self.assertRegex(
            prose, r"(?i)classification\.basis.{0,120}which tasks' declared outputs drove the value",
            "`classification.basis` does not record WHICH tasks' declared outputs drove the value "
            "(FR-1.5, NFR-5)",
        )
        self.assertRegex(
            prose, r"(?i)classification\.decidedAt.{0,80}(ISO-8601|timestamp)",
            "`classification.decidedAt` is not documented as a timestamp",
        )
        override = re.search(r"(?i)classification\.override(.{0,320})", prose)
        self.assertIsNotNone(override, "`classification.override` is undocumented")
        for field in ('"by"', '"requested"', '"accepted"', '"reason"'):
            self.assertIn(
                field.strip('"'), override.group(1),
                f"the `classification.override` object shape omits {field} (FR-1.6)",
            )
        self.assertRegex(
            override.group(1), r"(?i)whether the override was accepted or refused",
            "`classification.override` does not record refused overrides (FR-1.6, NFR-5)",
        )
        self.assertRegex(
            prose,
            r"(?i)classification\.tasksValidatedUnderExemption.{0,160}"
            r"artifact-conformance mode",
            "`classification.tasksValidatedUnderExemption` does not record the tasks validated "
            "under the non-code exemption (FR-3.3, NFR-5)",
        )
        reclass = re.search(r"(?i)classification\.reclassification(.{0,320})", prose)
        self.assertIsNotNone(reclass, "`classification.reclassification` is undocumented")
        for field in ("from", "to", "task", "paths", "trigger"):
            self.assertIn(
                field, reclass.group(1),
                f"the `classification.reclassification` object shape omits {field!r} (FR-3.1)",
            )


# --- (4) C3 / I1: per-task routing of the two forwarded values -----------------------------------


class PerTaskRoutingTest(OrchestratorDocTestCase):
    """C3 / I1 (FR-2, FR-2.1, FR-2.3, FR-2.4, FR-3.3, FR-5.1, NFR-4).

    The routing delta is additive by design: two values are added to prompts the stages already
    receive, and every condition that consumes them tests `featureClass == "non-code"` explicitly.
    So the assertions here are of two kinds — the routing must actually be STATED at each stage
    (a value nobody is told to pass is not forwarded), and the code path must be provably
    untouched (same stages, same order, same gate, no new prompt).
    """

    def preamble_region(self):
        return self.stage_region(
            r"\*\*Forwarded to the stages of this pipeline",
            r"\*\*Stage 1", "'Forwarded to the stages' preamble",
        )

    def stage_two_region(self):
        return self.stage_region(r"\*\*Stage 2 — Testing", r"\*\*Stage 3", "'Stage 2'")

    def stage_three_region(self):
        return self.stage_region(r"\*\*Stage 3 — Validation", r"\*\*Stages 4 & 5", "'Stage 3'")

    def stages_four_five_region(self):
        return self.stage_region(
            r"\*\*Stages 4 & 5 — Review", r"\*\*Review model tiering", "'Stages 4 & 5'",
        )

    def test_preamble_declares_both_forwarded_values_above_stage_one(self):
        """FR-2 / I1 / C3: one shared preamble, placed above Stage 1, defining both values.

        Defining them once above the stages is what makes the per-stage bullets short enough to
        stay correct; defining them inside a stage would leave the later stages reading a name
        nothing in the contract binds. `taskProducesApplicationCode` in particular is derived
        per TASK, not per feature, and the derivation has to be stated somewhere.
        """
        impl = self.impl_region()
        self.assertLess(
            impl.index("**Forwarded to the stages of this pipeline"),
            impl.index("**Stage 1"),
            "the forwarded-values preamble sits BELOW Stage 1 — C3 places it immediately above "
            "the stage list, so every stage bullet below can refer to values already defined",
        )

        region = flat(self.preamble_region())
        self.assertRegex(
            region, r"(?i)featureClass\b.{0,4}the current value from \.spec-state\.json",
            "the preamble does not define `featureClass` as the current value read from "
            "`.spec-state.json` (FR-2, I1)",
        )
        self.assertRegex(
            region,
            r"(?i)taskProducesApplicationCode\b.{0,80}derived for this task alone from the "
            r"outputs it declares",
            "the preamble does not define `taskProducesApplicationCode` as derived for THIS TASK "
            "from the outputs it declares — a feature-level reading of it would exempt every task "
            "in a non-code feature, including one that produces code (FR-2, I1)",
        )
        self.assertRegex(
            region, r"(?i)using the allow-list above",
            "the preamble does not tie the derivation of `taskProducesApplicationCode` to the C0 "
            "allow-list, leaving each task's outputs classified by an unstated rule (FR-1.3, I1)",
        )
        # A5-3 / DD-18: the derivation must be TOTAL as well as fail-safe. Anchored on the two
        # properties, not on the sentence: (i) the exemption-eligible value `false` requires BOTH a
        # non-empty set of declared outputs AND every one of them classifying non-code, and (ii) the
        # no-output case derives `true` explicitly. Without the first conjunct the universal is
        # vacuously true over zero declared outputs, so the one input on which nobody has said what
        # the task produces would derive the exemption-eligible value — the identical inference
        # AMB-5 was added to block one level up, and the per-feature rule (C1 item 6) already
        # carries the matching conjunct. Reachable after the gate, which runs once per feature while
        # `tasks.md` stays mutable.
        self.assertRegex(
            region,
            r"(?i)it is false only when this task declares at least one output and every output it "
            r"declares classifies non-code",
            "the preamble does not carry the AT-LEAST-ONE-OUTPUT conjunct in the derivation of "
            "`taskProducesApplicationCode`. Stated as \"`false` only when every output this task "
            "declares classifies non-code\", the universal is VACUOUSLY TRUE over zero declared "
            "outputs, so a task declaring nothing derives the exemption-eligible value "
            "(FR-2.1, FR-1.4, A5-3, DD-18)",
        )
        self.assertRegex(
            region,
            r"(?i)a task that declares no outputs derives true",
            "the preamble does not state the no-output direction explicitly — a task that declares "
            "no outputs must derive `true`, the per-task counterpart of AMB-1 (FR-2.1, FR-1.4, "
            "A5-3, DD-18)",
        )
        self.assertRegex(
            region,
            r"(?i)fail-safe",
            "the preamble states the derivation as arithmetic without naming the FAIL-SAFE "
            "direction it encodes — FR-1.4's direction is what makes the missing-declaration case "
            "resolve toward more review, not less (FR-1.4, A5-3)",
        )
        self.assertRegex(
            region,
            r"(?i)counterpart of AMB-1",
            "the preamble does not tie the per-task rule to AMB-1, its per-feature counterpart — "
            "the two rules close the same vacuous-truth hole one level apart and a later reader "
            "must be able to see that they travel together (A5-3, DD-18)",
        )
        # A3 / I1: `null` is never on the wire.
        self.assertRegex(
            region, r'(?i)forward it as "code"; null itself is never forwarded',
            "the preamble does not state that an unclassified feature is forwarded as \"code\" "
            "and that `null` itself never reaches a stage — I1 fixes the wire values at exactly "
            "the two permitted classifications (FR-1.1, A3-1)",
        )
        self.assertRegex(
            region, r"(?i)nothing existing is removed or renamed",
            "the preamble does not state that the delta is ADDITIVE to the existing payloads "
            "(I1, NFR-4)",
        )

    def test_preamble_scopes_each_forwarded_value_to_the_stages_that_receive_it(self):
        """FR-2 / FR-2.3 / NFR-4 / NFR-6 / I1 / A5-4: the preamble states WHICH stage receives WHICH
        value, and agrees with I1 and the stage bullets directly beneath it.

        The pre-A5 preamble said the two values ride along with the payloads *"each stage"* already
        receives, while I1 and the four stage bullets immediately below it say Stage 1 receives
        neither and Stages 4 & 5 receive `featureClass` only. Two normative statements in one
        section disagreeing about the same wire contract is the NFR-6 drift shape, and the suite
        pinned **both** sides green — the positive half here and the negative half in
        `test_stages_four_and_five_receive_feature_class_only`, which still passes unchanged as the
        other side of this same fact. The harm was bounded while the field is inert in the executor
        and reviewer contracts, but four more contracts read this text after Tasks 6/7/8.
        """
        region = flat(self.preamble_region())

        # `featureClass` — Stages 2, 3, 4 and 5.
        self.assertRegex(
            region,
            r"(?i)featureClass\b.{0,80}forwarded to Stages 2, 3, 4 and 5",
            "the preamble does not scope `featureClass` to Stages 2, 3, 4 and 5 — I1 and the stage "
            "bullets below fix exactly those four (FR-2, NFR-6, I1, A5-4)",
        )
        # `taskProducesApplicationCode` — the task stages only, Stages 2 and 3.
        self.assertRegex(
            region,
            r"(?i)forwarded to the task stages only — Stages 2 and 3",
            "the preamble does not scope `taskProducesApplicationCode` to the TASK STAGES ONLY "
            "(Stages 2 and 3) — I1 confines it there and the reviewers scope on the feature "
            "classification, not on one task's declared outputs (FR-2, NFR-6, I1, A5-4)",
        )
        # Stage 1 — neither value, and unchanged.
        self.assertRegex(
            region,
            r"(?i)the task-executor \(Stage 1\) receives neither value",
            "the preamble does not state that Stage 1 receives NEITHER value — FR-2.4 and NFR-4 "
            "keep the executor invocation untouched, and I1 says so (FR-2.4, NFR-4, I1, A5-4)",
        )
        self.assertRegex(
            region,
            r"(?i)its invocation is unchanged — no new field and no new prompt",
            "the preamble does not state that the executor invocation is unchanged (no new field, "
            "no new prompt) (FR-2.4, NFR-4, A5-4)",
        )
        # The defective A5-4 wording: the values must NOT be said to ride with "each stage".
        self.assertNotRegex(
            region,
            r"(?i)ride along with the payloads each stage already receives",
            "the preamble still says the two values ride along with the payloads EACH STAGE already "
            "receives. That contradicts I1 and the four stage bullets directly beneath it — Stage 1 "
            "receives neither and Stages 4 & 5 receive `featureClass` only — and two normative "
            "statements in one section disagreeing about the wire contract is the NFR-6 drift shape "
            "(FR-2, NFR-6, I1, A5-4)",
        )
        # Stated once, here: the per-stage bullets repeat the scope rather than extend it.
        self.assertRegex(
            region,
            r"(?i)which stage receives which is fixed here, once",
            "the preamble does not declare itself the single place the per-stage scope is fixed — "
            "without that, a later stage bullet widening its own inputs reads as an extension "
            "rather than a contradiction (NFR-6, A5-4)",
        )

    def test_preamble_carries_the_nfr4_guard_sentence_once(self):
        """FR-2.3 / NFR-4: the guard sentence is present, complete, and stated exactly once.

        "Changes nothing" has to be spelled out as the list of things that do not change, or it is
        an aspiration rather than a checkable contract. Stating it once, in the shared preamble,
        is also what keeps it from drifting into five per-stage variants that disagree.
        """
        region = flat(self.preamble_region())
        self.assertRegex(
            region, r'(?i)where featureClass is "code", these two values change nothing',
            "the preamble carries no NFR-4 guard sentence for the `\"code\"` path (FR-2.3, NFR-4)",
        )
        self.assertRegex(
            region,
            r"(?i)same stages, same order, same verdict formats, same labels, and no additional "
            r"user prompt",
            "the NFR-4 guard sentence does not enumerate what stays the same (same stages, same "
            "order, same verdict formats, same labels, no additional user prompt) — an unqualified "
            "'nothing changes' is not checkable (FR-2.3, NFR-4)",
        )
        self.assertEqual(
            len(re.findall(
                r"(?i)same stages, same order, same verdict formats, same labels", flat(self.body),
            )),
            1,
            "the NFR-4 guard sentence appears more than once in `agents/orchestrator.md`; C3 "
            "states it once, in the shared preamble, so the copies cannot drift apart",
        )
        # The count above only sees a VERBATIM second copy of the enumeration. A shorter
        # restatement ("There is no additional user prompt on the code path.") is a second
        # normative home for the same NFR-4 promise — independently relaxable, and invisible to
        # every assertion here. Quotations of NFR-4's own wording are legitimate and are exempted
        # by their opening double quote (the classification gate's legacy report is one).
        flat_body = flat(self.body)
        normative = [
            m for m in re.finditer(r"(?i)no additional user prompt", flat_body)
            if flat_body[m.start() - 1:m.start()] != '"'
        ]
        self.assertEqual(
            len(normative), 1,
            f"the NFR-4 'no additional user prompt' guarantee is stated normatively "
            f"{len(normative)} times in `agents/orchestrator.md`; sub-task 4.12 requires it "
            f"exactly ONCE, in this preamble. Two normative copies of one guarantee are two "
            f"places a later edit can relax independently — the NFR-6 drift shape "
            f"(FR-2.3, NFR-4, NFR-6)",
        )
        self.assertRegex(
            region, r'(?i)every condition below tests featureClass against "non-code" explicitly',
            "the preamble does not state that every routing condition tests `featureClass` "
            "against `\"non-code\"` EXPLICITLY — that is what makes an unclassified feature take "
            "the unchanged code path by construction rather than by luck (FR-2.3, NFR-4, A3-1)",
        )

    def test_stage_two_receives_both_values_and_the_conditional_no_code_instruction(self):
        """FR-2 / FR-2.1: the tester is passed both values, and the no-code behaviour is requested
        only on the conjunction — non-code feature AND a task producing no application code."""
        region = flat(self.stage_two_region())

        self.assertIn(
            "featureClass", region,
            "Stage 2 does not pass `featureClass` to the task-tester (FR-2)",
        )
        self.assertIn(
            "taskProducesApplicationCode", region,
            "Stage 2 does not pass `taskProducesApplicationCode` to the task-tester — without it "
            "the tester cannot tell a prose task from a code task inside a non-code feature "
            "(FR-2, I1)",
        )
        self.assertRegex(
            region,
            r'(?i)where featureClass is "non-code" and taskProducesApplicationCode is false, '
            r"instruct the tester to apply its no-code behaviour",
            "Stage 2 does not instruct the tester to apply its no-code behaviour on the "
            "conjunction FR-2.1 defines (a `\"non-code\"` feature AND a task that produces no "
            "application code)",
        )
        self.assertRegex(
            region, r"(?i)in every other combination the tester is invoked exactly as today",
            "Stage 2 does not state that every other combination leaves the tester invocation "
            "unchanged — without it the no-code instruction has no stated complement (NFR-4)",
        )

    def test_stage_three_requests_artifact_conformance_and_records_the_exemption(self):
        """FR-2.1 / FR-5.1 / FR-3.3 / DD-2: the validator is passed both values; artifact-
        conformance mode is entered ONLY on the orchestrator's instruction; and issuing that
        instruction is recorded in `classification.tasksValidatedUnderExemption`.

        The mode is an exemption from "missing tests are a FAIL", so its entry point has to be
        single and its use has to be auditable — a validator that could select the mode itself
        would be able to exempt a code task, and an exemption nobody records cannot be re-reviewed
        under the code path when the feature is later reclassified (FR-3.3).
        """
        region = flat(self.stage_three_region())

        self.assertIn(
            "featureClass", region,
            "Stage 3 does not pass `featureClass` to the task-validator (FR-2)",
        )
        self.assertIn(
            "taskProducesApplicationCode", region,
            "Stage 3 does not pass `taskProducesApplicationCode` to the task-validator (FR-2, I1)",
        )
        self.assertRegex(
            region,
            r'(?i)where featureClass is "non-code" and taskProducesApplicationCode is false, '
            r"instruct the validator to run in artifact-conformance mode",
            "Stage 3 does not instruct the validator to run in artifact-conformance mode on the "
            "conjunction FR-2.1 defines",
        )
        self.assertRegex(
            region, r"(?i)the validator never selects that mode itself",
            "Stage 3 does not state that the validator NEVER selects artifact-conformance mode "
            "itself — FR-5.1 makes the orchestrator's instruction the only entry point",
        )
        self.assertRegex(
            region, r"(?i)your instruction is its only entry point",
            "Stage 3 does not name the orchestrator's instruction as the ONLY entry point into "
            "artifact-conformance mode (FR-5.1, DD-2)",
        )
        # A5-5: the record is WRITE-AHEAD and SET-VALUED. Re-anchored on those two properties rather
        # than on the old "append …" sentence, which stated neither.
        #
        # (i) Write-ahead. "When you issue it, append" reads naturally as append-AFTER, and an
        #     interruption in that window leaves an exemption GRANTED BUT UNRECORDED — the audit
        #     record failing in the one direction that hides an exemption rather than over-declaring
        #     one. NFR-5 makes this array *the* audit surface for the exemption.
        # (ii) Set-valued. Stage 3 re-runs on both retry paths — the ordinary `On **fail**` branch
        #      and C4 action 3 — so a plain append makes a twice-retried task record `[4, 4, 4]`,
        #      misstating how many tasks were exempted to any human or CI job reading the file.
        self.assertRegex(
            region,
            r"(?i)before you issue that instruction, add this task's number to "
            r"classification\.tasksValidatedUnderExemption",
            "Stage 3 does not record the exemption WRITE-AHEAD — the task's number must be added to "
            "`classification.tasksValidatedUnderExemption` BEFORE the artifact-conformance "
            "instruction is issued. An add stated after the instruction leaves an interruption "
            "window in which the exemption is granted but unrecorded, which is the one direction "
            "that HIDES an exemption from the NFR-5 audit surface (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            region,
            r"(?i)if it is not already present",
            "Stage 3's add is not conditional on the number being absent. Stage 3 re-runs on both "
            "retry paths — the `On **fail**` branch and the reclassification subsection's action 3 "
            "— so an unconditional add records a twice-retried task three times and misstates how "
            "many tasks were exempted (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            region,
            r"(?i)the key is a duplicate-free set of task numbers",
            "Stage 3 does not declare `classification.tasksValidatedUnderExemption` a "
            "DUPLICATE-FREE SET — the conditional add and the set semantics must both be stated, or "
            "a later reader restores the append (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            region,
            r"(?i)entries are never removed or cleared",
            "Stage 3 does not state that entries are NEVER removed or cleared — FR-3.3's re-review "
            "reads this key after reclassification, so a cleared entry is a task whose exemption "
            "nothing re-covers (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            region,
            r"(?i)keyed on issuing the instruction, never on the validation verdict",
            "Stage 3 does not keep the record keyed on ISSUING THE INSTRUCTION rather than on the "
            "verdict. The instruction-issue keying is deliberately preserved: it OVER-records, and "
            "over-recording is the direction FR-3.3's re-review requires (FR-3.3, NFR-5, A5-5)",
        )
        # The pre-A5 wording must be GONE: it stated neither property.
        self.assertNotRegex(
            region,
            r"(?i)when you issue it, append this task's number",
            "Stage 3 still carries the pre-A5 append-on-issue wording. It reads as append-AFTER "
            "(leaving a granted-but-unrecorded window) and it is unconditional (recording a "
            "retried task once per attempt) — the two defects A5-5 exists to fix (A5-5)",
        )
        self.assertRegex(
            region, r"(?i)in every other combination the validator is invoked exactly as today",
            "Stage 3 does not state that every other combination leaves the validator in its "
            "unchanged code mode (FR-2.3, NFR-4)",
        )
        # The inversion FR-5.1 exists to forbid.
        self.assertNotRegex(
            region,
            r"(?i)the validator (may|can|should|will) (select|choose|enter|decide)",
            "Stage 3 lets the validator select artifact-conformance mode for itself — FR-5.1 "
            "requires the orchestrator's instruction to be the single entry point",
        )

    def test_stages_four_and_five_receive_feature_class_only(self):
        """FR-2 / I1: both reviewers are passed `featureClass` and nothing else changes.

        `taskProducesApplicationCode` is a task-stage value (I1: "task stages only (Stages 2 & 3)")
        — the reviewers scope on the feature classification and the diff, not on one task's
        declared outputs.
        """
        region_raw = self.stages_four_five_region()
        region = flat(region_raw)

        self.assertIn(
            "featureClass", region,
            "Stages 4 & 5 do not pass `featureClass` to the reviewers (FR-2)",
        )
        self.assertNotIn(
            "taskProducesApplicationCode", region_raw,
            "Stages 4 & 5 pass `taskProducesApplicationCode` to the reviewers — I1 scopes that "
            "field to the task stages (Stages 2 & 3) only",
        )
        self.assertRegex(
            region,
            r"(?i)everything else about the invocation is unchanged: mode: task, both reviewers "
            r"concurrent, both on Opus",
            "Stages 4 & 5 do not state that the rest of the invocation is unchanged (`mode: task`, "
            "both reviewers concurrent, both on Opus) — the reviewer invocation is exactly what "
            "NFR-4 and FR-2.4 forbid this feature from perturbing",
        )

    def test_stage_order_and_the_post_validation_review_gate_are_unchanged(self):
        """FR-2.4: execute → test → validate → code review → security review, in that order, with
        the reviews still gated on validation passing.

        The routing delta adds fields to existing prompts. If it ever reorders or inserts a stage,
        every downstream contract's assumptions about what a stage has already seen break — and
        for a `"code"` feature that is a behavioural change NFR-4 forbids outright.
        """
        impl = self.impl_region()
        offsets = []
        for anchor, label in (
            (r"\*\*Stage 1 — Execution", "Stage 1 — Execution"),
            (r"\*\*Stage 2 — Testing", "Stage 2 — Testing"),
            (r"\*\*Stage 3 — Validation", "Stage 3 — Validation"),
            (r"\*\*Stages 4 & 5 — Review", "Stages 4 & 5 — Review"),
        ):
            found = [m.start() for m in re.finditer(anchor, impl)]
            self.assertEqual(
                len(found), 1,
                f"the ``### `implementation` `` section declares the {label!r} heading "
                f"{len(found)} time(s); exactly one is expected (FR-2.4)",
            )
            offsets.append((label, found[0]))

        for (earlier, a), (later, b) in zip(offsets, offsets[1:]):
            self.assertLess(
                a, b,
                f"{later!r} is declared BEFORE {earlier!r} — FR-2.4 fixes the stage order as "
                f"execute → test → validate → code review → security review for both classes",
            )

        self.assertRegex(
            flat(impl), r"(?i)Stages 4 & 5 — Review \(run only after validation passes\)",
            "the review stages are no longer labelled as running only after validation passes "
            "(FR-2.4)",
        )
        self.assertRegex(
            flat(impl), r"(?i)only run stages 4.5 if validation passes",
            "the ``### `implementation` `` section no longer gates Stages 4-5 on validation "
            "passing — FR-2.4 keeps that gate for both classes",
        )
        # The reviewers are one concurrent pair, not two more sequential stages.
        self.assertRegex(
            flat(impl), r"(?i)invoke them concurrently",
            "the code and security reviewers are no longer invoked concurrently (FR-2.4, NFR-4)",
        )

    def test_routing_adds_no_stage_and_no_user_prompt_to_the_code_path(self):
        """FR-2.3 / FR-2.4 / NFR-4: the delta introduces no sixth stage and no new user prompt.

        A new stage or a new question is the most likely way this feature would leak into the code
        path, and neither would be caught by the per-stage assertions above — they check what the
        existing stages say, not whether something new was appended.
        """
        impl = self.impl_region()
        stage_headings = re.findall(r"\*\*Stages? [\d &]+ —", impl)
        self.assertEqual(
            len(stage_headings), 4,
            f"the ``### `implementation` `` section declares {len(stage_headings)} stage "
            f"heading(s) ({stage_headings}); the pipeline has exactly four (Stage 1, Stage 2, "
            f"Stage 3, and the paired Stages 4 & 5) and FR-2.4 forbids adding one",
        )

        for region_name, region in (
            ("the forwarded-values preamble", self.preamble_region()),
            ("Stage 2", self.stage_two_region()),
            ("Stage 3", self.stage_three_region()),
            ("Stages 4 & 5", self.stages_four_five_region()),
        ):
            self.assertNotRegex(
                flat(region),
                r"(?i)(ask the user|prompt the user|ask:\s|await (the user's )?"
                r"(confirmation|approval))",
                f"{region_name} introduces a user prompt into the per-task pipeline — NFR-4 and "
                f"FR-2.3 guarantee the classification adds no additional user prompt",
            )


# --- (5) C4: the reclassification fallback, non-code → code --------------------------------------


class ReclassificationFallbackTest(OrchestratorDocTestCase):
    """C4 / D2 (FR-3, FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-4.5, FR-5.6, FR-10.1, NFR-5).

    A `"non-code"` classification is a claim about what the tasks *declared*, decided once, before
    any of them ran. This subsection is the only thing standing between that claim being wrong and a
    feature shipping application code with the test gate switched off — so locked decision D2's
    "tests optional" must not survive contact with an application-code path. The assertions here are
    therefore of three kinds: the fallback must be REACHABLE (it exists, at its anchor, in the right
    section), it must be COMPLETE (all three triggers, all five actions), and it must be
    MONOTONIC AND CHEAP (it never travels back toward `"non-code"`, and it does not silently spend a
    retry or invent a label).
    """

    def reclassification_span(self):
        span = section_span(self.body, RECLASSIFICATION_HEADING)
        self.assertIsNotNone(
            span,
            f"no heading with the exact title {RECLASSIFICATION_HEADING!r} — design C4 fixes this "
            f"anchor verbatim, and the tester, the validator and this orchestrator all cite it",
        )
        return span

    def reclassification_region(self):
        start, end = self.reclassification_span()
        return self.body[start:end]

    def test_subsection_exists_inside_implementation_after_the_fail_branch(self):
        """C4 placement: a `####` subsection at the END of ``### `implementation` ``, after the
        `On **fail**` bullet.

        Placement is substantive, not cosmetic. The fallback fires from inside the per-task
        pipeline — its triggers are the tester's report, the validator's verdict and the executor's
        changed-files summary — and its retry accounting is stated as a delta against the
        `On **fail**` branch, which must therefore already have been read.
        """
        start, _ = self.reclassification_span()
        level = next(lvl for _, lvl, t in headings(self.body) if t == RECLASSIFICATION_HEADING)
        self.assertEqual(
            level, 4,
            "the reclassification fallback must be a `####` subsection of "
            "``### `implementation` `` (design C4) — a `###` heading would close that section and "
            "orphan the per-task pipeline's own trailing branches",
        )

        impl_start, impl_end = self.impl_span()
        self.assertTrue(
            impl_start < start < impl_end,
            "the reclassification subsection sits OUTSIDE the ``### `implementation` `` section. "
            "Its triggers all arise inside the per-task pipeline and its retry accounting is stated "
            "as a delta against that section's `On **fail**` branch (design C4)",
        )
        fail_branch = re.search(r"On \*\*fail\*\*", self.body[impl_start:impl_end])
        self.assertIsNotNone(
            fail_branch, "the ``### `implementation` `` section has no `On **fail**` branch"
        )
        self.assertGreater(
            start, impl_start + fail_branch.start(),
            "the reclassification subsection is placed BEFORE the `On **fail**` bullet. C4 places "
            "it at the end of the section, after that branch, because its retry accounting is "
            "stated as a delta against it (design C4, DD-8)",
        )

    def test_all_three_triggers_are_named(self):
        """FR-3 / FR-4.5 / FR-5.6: T1, T2 and T3, each labelled and each substantive.

        Three independent detectors, because each sees something the others cannot: the tester sees
        what the code actually is, the validator sees the mode it was judged under, and the
        orchestrator sees the changed-files summary even when both downstream stages are silent.
        """
        region = self.reclassification_region()
        flat_region = flat(region)

        self.assertEqual(
            re.findall(r"\bT[123]\b", flat_region)[:3], ["T1", "T2", "T3"],
            "the reclassification triggers are not labelled T1, T2 and T3 in order — the labels are "
            "cited by number in design C4, in this task's retry accounting and in review (FR-3)",
        )
        for label, pattern, why in (
            ("T1",
             r"(?i)task-tester reports that the task in fact produced application code",
             "the task-tester reporting that the task in fact produced application code (FR-4.5)"),
            ("T2",
             r"(?i)task-validator returns FAIL citing application-code modification under "
             r"artifact-conformance mode",
             "the task-validator returning FAIL over an application-code modification it was asked "
             "to judge in artifact-conformance mode (FR-5.6)"),
            ("T3",
             r"(?i)application-code path in the executor's changed-files summary",
             "the orchestrator itself seeing an application-code path in the executor's "
             "changed-files summary — the detector that still fires when both downstream stages are "
             "silent"),
        ):
            self.assertRegex(
                flat_region, pattern,
                f"reclassification trigger {label} is missing or reworded — {why} must be one of "
                f"the enumerated triggers (FR-3)",
            )

    def test_triggers_are_scoped_to_a_recorded_non_code_classification(self):
        """FR-2.3 / FR-3 / FR-3.4 / sub-task 4.7: the mechanical guard behind the triggers' ARMING
        condition.

        `test_all_three_triggers_are_named` pins each trigger's own wording. Nothing pins the clause
        that decides *which features the triggers are live over* — and that clause is this one-way
        valve's arming condition. It is silently invertible in four directions, every one of which
        leaves the rest of this class green:

        - Scoped to `"code"` instead. A feature classified `"non-code"` at the gate has a task that
          writes `hooks/pre-push`; no trigger is in scope, so nothing fires, `featureClass` stays
          `"non-code"`, and the task completes on the artifact-conformance PASS it earned — the mode
          in which **missing tests are explicitly not a failure** (D2). The feature ships
          application code with the test gate switched off, which is the single outcome this
          subsection exists to prevent.
        - Scoped away entirely, or keyed on the mere PRESENCE or ABSENCE of the `featureClass` key.
          The triggers go live over `"code"` and unclassified features too. `/sdd-feature` plus the
          initialization block in *State File Management* leave `featureClass: null` **present**, so
          a presence-keyed predicate arms the fallback for every freshly scaffolded feature:
          action 1 then writes a fabricated `classification.reclassification` for a feature never
          `"non-code"`, breaking FR-2.3's "no behavioural change whatsoever" on the code path and
          inverting this subsection's own "no trigger reclassifies it".

        So the predicate is pinned the way the gate's entry predicate is pinned by
        `test_gate_entry_predicate_keys_on_recorded_decision_not_key_presence`: positively on the
        **recorded decision** being `"non-code"`, and negatively against any key-presence
        formulation. This clause is also absent from design C4, so no later task re-syncing C4's
        contract text can drop it and stay green.
        """
        preamble = self.slice_between(
            self.reclassification_region(), r"\*\*Triggers\.\*\*", r"\*\*T1\*\*",
            "trigger preamble", container="reclassification subsection",
        )
        flat_preamble = flat(preamble)

        self.assertRegex(
            flat_preamble, r'(?i)whose recorded featureClass is "non-code"',
            "the trigger preamble does not scope the triggers to a feature whose RECORDED "
            "`featureClass` is `\"non-code\"`. That clause is the fallback's arming condition: "
            "without it the triggers are live over `\"code\"` and unclassified features (which "
            "carry `featureClass: null`), and action 1 fabricates a reclassification record for a "
            "feature that was never `\"non-code\"` (FR-2.3, FR-3, FR-3.4)",
        )
        # The inversion is the dangerous half: it disarms the valve rather than over-arming it.
        self.assertNotRegex(
            flat_preamble, r'(?i)recorded featureClass is "code"',
            "the triggers have been scoped to features whose recorded `featureClass` is `\"code\"` "
            "— exactly backwards. A `\"non-code\"` feature whose task writes application code "
            "would then have NO trigger in scope: nothing reclassifies it, and it completes on an "
            "artifact-conformance PASS in the mode where missing tests are not a failure. The "
            "feature ships application code with the test gate off (FR-3, FR-3.2, D2)",
        )
        # ...and neither half may be restated in terms of the KEY instead of the recorded value.
        for pattern, why in (
            (r"(?i)featureClass key",
             "keys on the `featureClass` KEY rather than on the decision recorded in it"),
            (r"(?i)featureClass is (present|absent)",
             "keys on the PRESENCE or ABSENCE of `featureClass` rather than on the recorded "
             "decision"),
        ):
            self.assertNotRegex(
                flat_preamble, pattern,
                f"the trigger preamble {why}. `featureClass: null` is written by the "
                f"initialization block and is therefore PRESENT on every freshly scaffolded "
                f"feature, so a key-keyed predicate arms this fallback for features that were "
                f"never classified `\"non-code\"` — the same defect shape the gate's own entry "
                f"predicate was corrected for (FR-1.1, FR-2.3, FR-3.4)",
            )

    def test_actions_set_code_record_provenance_and_report(self):
        """FR-3.1 / NFR-5: set `featureClass = "code"`, populate `classification.reclassification`
        with the four provenance fields, and report to the user naming the file(s) and the task.

        The record is the audit surface: a reclassification that happens without provenance leaves a
        feature whose `featureClass` contradicts its own `classification.basis` with nothing
        explaining the difference.
        """
        flat_region = flat(self.reclassification_region())

        self.assertRegex(
            flat_region, r'(?i)set featureClass = "code" in \.spec-state\.json',
            "the reclassification does not write `featureClass = \"code\"` to `.spec-state.json` "
            "(FR-3.1)",
        )
        self.assertRegex(
            flat_region, r"(?i)populate classification\.reclassification",
            "the reclassification does not populate `classification.reclassification` — the "
            "transition would leave no provenance at all (FR-3.1, NFR-5)",
        )
        for field, why in (
            (r"(?i)triggering path", "which path forced the transition"),
            (r"(?i)the task number", "which task it was seen in"),
            (r"(?i)the trigger source", "which of T1/T2/T3 saw it"),
            (r"(?i)the timestamp", "when it happened"),
        ):
            self.assertRegex(
                flat_region, field,
                f"`classification.reclassification` is populated without recording {why} "
                f"(FR-3.1, NFR-5)",
            )
        self.assertRegex(
            flat_region,
            r"(?i)report the reclassification to the user, naming the file\(s\) and the task",
            "the reclassification is not reported to the user naming the file(s) and the task — a "
            "silent class change is exactly the audit gap NFR-5 forbids (FR-3.1, NFR-5)",
        )

    def test_stages_two_and_three_rerun_under_the_code_path_with_tests_required(self):
        """FR-3.2: the current task's test and validation stages re-run under the code path — tests
        required — before the task may be marked complete.

        Without this the transition is retroactive in name only: the task that produced the
        application code would keep the PASS it earned in artifact-conformance mode, where missing
        tests are explicitly not a failure (locked decision D2 must not become a loophole).
        """
        flat_region = flat(self.reclassification_region())

        self.assertRegex(
            flat_region,
            r"(?i)re-run the current task's Stage 2 \(test\) and Stage 3 \(validation\) under the "
            r"code path",
            "the reclassification does not re-run the current task's Stage 2 (test) and Stage 3 "
            "(validation) under the code path (FR-3.2)",
        )
        self.assertRegex(
            flat_region, r"(?i)tests required",
            "the re-run does not state that TESTS ARE REQUIRED — a re-run that inherits the "
            "no-code behaviour re-reaches the same verdict and D2's tests-optional becomes a "
            "loophole (FR-3.2)",
        )
        self.assertRegex(
            flat_region, r"(?i)before the task may be marked complete",
            "the re-run is not gated BEFORE the task may be marked complete — a task completed on "
            "its exempted verdict and re-tested afterwards has already passed the gate (FR-3.2)",
        )

    def test_exemption_record_semantics_are_documented_in_full(self):
        """FR-3.3 / NFR-5 / A5-5: `classification.tasksValidatedUnderExemption` is kept as written,
        and its semantics — not merely its shape — are documented here.

        NFR-5 makes this array *the* audit surface for the exemption, and FR-3.3 makes it the input
        to the post-reclassification re-review. Four properties therefore have to be stated, because
        each has a plausible wrong reading: it is **write-ahead** (an add stated after the
        instruction leaves a window in which the exemption is granted but unrecorded — the one
        direction that HIDES an exemption); it is a **duplicate-free set** (Stage 3 re-runs on both
        retry paths, so a plain append records `[4, 4, 4]` and misstates how many tasks were
        exempted); it is keyed on **instruction-issue** rather than on the verdict, which
        over-records deliberately; and entries are **never removed or cleared**, including here on
        reclassification, which is the moment a reader would most expect a withdrawal.
        """
        flat_region = flat(self.reclassification_region())

        self.assertRegex(
            flat_region,
            r"(?i)keep classification\.tasksValidatedUnderExemption as written",
            "the reclassification does not state that `classification.tasksValidatedUnderExemption` "
            "is KEPT AS WRITTEN (FR-3.3)",
        )
        self.assertRegex(
            flat_region, r"(?i)permanent record, not a live flag",
            "the key is not declared a PERMANENT RECORD rather than a live flag — read as a live "
            "flag it would be cleared the moment the exemption stops applying, destroying the input "
            "FR-3.3's re-review needs (FR-3.3, NFR-5)",
        )
        # (i) What it records.
        self.assertRegex(
            flat_region,
            r"(?i)the numbers of the tasks whose Stage 3 ran in artifact-conformance mode",
            "the subsection documents the key's shape without saying WHAT it records — the numbers "
            "of the tasks whose Stage 3 ran in artifact-conformance mode (FR-3.3, NFR-5, A5-5)",
        )
        # (ii) The write-ahead add point, in both halves: BEFORE, and only IF ABSENT.
        self.assertRegex(
            flat_region,
            r"(?i)added, if it is not already present, immediately before you issue the "
            r"artifact-conformance instruction",
            "the subsection does not document the key's WRITE-AHEAD add point: the task's number is "
            "added, IF NOT ALREADY PRESENT, immediately BEFORE the artifact-conformance instruction "
            "is issued. An add stated after the instruction leaves an interruption window in which "
            "the exemption is granted but unrecorded (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)write-ahead, so no interruption in that window can leave an exemption granted but "
            r"unrecorded",
            "the subsection does not say WHY the write is write-ahead — the interruption window is "
            "the whole reason the ordering is normative rather than stylistic (NFR-5, A5-5)",
        )
        # (iii) Duplicate-free set, with the reason it matters: Stage 3 re-runs on both paths.
        self.assertRegex(
            flat_region, r"(?i)duplicate-free set",
            "the subsection does not declare the key a DUPLICATE-FREE SET (FR-3.3, NFR-5, A5-5)",
        )
        self.assertRegex(
            flat_region, r"(?i)appears exactly once in this key, not once per attempt",
            "the subsection does not state that a task whose Stage 3 re-runs under the exemption "
            "appears EXACTLY ONCE. Stage 3 re-runs on both retry paths — the `On **fail**` branch "
            "and action 3 here — so an append records a twice-retried task three times and "
            "misstates how many tasks were exempted (FR-3.3, NFR-5, A5-5)",
        )
        # (iv) Instruction-issue keying, and the over-recording it is chosen for.
        self.assertRegex(
            flat_region, r"(?i)keyed on issuing the instruction, never on the verdict",
            "the subsection does not state that the key is keyed on ISSUING THE INSTRUCTION rather "
            "than on the verdict (FR-3.3, A5-5)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)a task that fails validation under the exemption stays recorded",
            "the subsection does not state the over-recording the instruction-issue keying buys — a "
            "task that FAILS validation under the exemption stays recorded, which is the direction "
            "FR-3.3's re-review requires (FR-3.3, A5-5)",
        )
        # (v) Never removed or cleared — including HERE, the moment a reader expects a withdrawal.
        self.assertRegex(
            flat_region,
            r"(?i)entries are never removed or cleared — not here on reclassification, and not at "
            r"feature completion",
            "the subsection does not state that entries are NEVER removed or cleared, naming both "
            "moments a reader would expect a withdrawal: here on reclassification, and at feature "
            "completion (FR-3.3, NFR-5, A5-5)",
        )
        # The Feature Review Gate consequence: those tasks are re-reviewed under the code path.
        self.assertRegex(
            flat_region,
            r"(?i)non-empty and the feature has been reclassified, the Feature Review Gate "
            r"invocation must state that those tasks' outputs are to be reviewed under the code path",
            "the subsection does not require the Feature Review Gate invocation to state that the "
            "exempted tasks' outputs are reviewed UNDER THE CODE PATH once the feature has been "
            "reclassified — that re-review is the whole purpose of recording the exemption (FR-3.3)",
        )

    def test_monotonicity_is_stated_and_covers_the_user_override(self):
        """FR-3.4 / FR-1.6: once `"code"`, never back to `"non-code"` — not by a later artifact-only
        task, and not by a user override.

        Both exclusions are needed. Without the first, a non-code feature that reclassified at task
        3 would drift back at task 4 whose declared outputs happen to be prose. Without the second,
        FR-1.6's honoured-toward-`"non-code"` override becomes the withdrawal FR-3.4 forbids.
        """
        flat_region = flat(self.reclassification_region())

        self.assertRegex(
            flat_region,
            r'(?i)once featureClass is "code" it is never set back to "non-code" for the remainder '
            r"of the feature",
            "the subsection does not state MONOTONICITY: once `featureClass` is `\"code\"` it is "
            "never set back to `\"non-code\"` for the remainder of the feature (FR-3.4)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)not by a later task that declares only artifacts",
            "monotonicity does not exclude the later artifact-only task — the most likely route "
            "back, since a non-code feature's remaining tasks typically declare prose (FR-3.4)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)and not by a user override",
            "monotonicity does not exclude the USER OVERRIDE — FR-1.6 honours an override toward "
            "`\"non-code\"` when the FR-1.3 test holds, and after a reclassification it does not "
            "(FR-3.4, FR-1.6)",
        )

    def test_null_is_read_as_unclassified_and_non_code_is_never_written(self):
        """FR-3 / FR-3.1 / FR-3.4 / A3-1 / A4-1: this subsection is a CONSUMER of `featureClass` and
        obeys the schema prose's reading rule, with both consequences stated so it cannot be
        inverted here.

        `null` has one tempting local reading — "not yet code" — and it is the reading that would let
        a trigger fire over a feature that was never classified, "withdrawing" an exemption that was
        never granted. The second consequence is the mirror image: a subsection that may write
        `featureClass` at all could be read as free to write the other permitted value, which would
        make the fallback a bidirectional classifier and FR-3.4 unenforceable.
        """
        flat_region = flat(self.reclassification_region())

        self.assertRegex(
            flat_region, r"(?i)this subsection is a consumer of featureClass",
            "the subsection does not declare itself a CONSUMER of `featureClass` — the schema "
            "prose's `null` reading rule binds consumers, and a subsection outside that set would "
            "be free to invent its own reading (FR-1.1, A3-1, A4-1)",
        )
        self.assertRegex(
            flat_region,
            r'(?i)a null or absent featureClass means the feature is unclassified and is read '
            r'exactly as an absent value — that is, as "code"',
            "the subsection does not state the `null`/absent-is-unclassified reading: both are read "
            "EXACTLY AS an absent value, i.e. as `\"code\"` (FR-1.1, A3-1)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)there is no exemption to withdraw",
            "the subsection does not state the first consequence — an unclassified feature was "
            "never granted an exemption, so there is nothing to withdraw and no trigger "
            "reclassifies it (FR-3, A3-1)",
        )
        self.assertRegex(
            flat_region, r"(?i)no trigger reclassifies it",
            "the subsection does not state that no trigger fires over an unclassified feature "
            "(FR-3, A3-1)",
        )
        self.assertRegex(
            flat_region, r'(?i)this subsection never writes "non-code"',
            "the subsection does not state that it NEVER writes `\"non-code\"` — the second "
            "consequence of the reading rule, and what keeps FR-3.4's monotonicity enforceable "
            "(FR-3.4, A3-1)",
        )
        self.assertRegex(
            flat_region,
            r'(?i)only ever moves a value to "code" — never from null to "non-code", and never back',
            "the subsection does not state the direction of travel exactly: only ever TO `\"code\"`, "
            "never from `null` to `\"non-code\"`, and never back (FR-3.1, FR-3.4, A3-1)",
        )

    def test_retry_accounting_is_settled_and_introduces_no_label(self):
        """FR-3.2 / FR-10.1 / DD-8: T2 spends an attempt through the existing `On **fail**` branch;
        T1 and T3 do not, and no path introduces a label.

        Left unsettled, an implementer reading "re-run stages 2–3" would plausibly increment
        `retryCount` for all three, and two `retryCount` increments halt the task at the user
        (`retryCount >= 2`) — so a feature that merely mis-declared its outputs would present as a
        double failure. The opposite default is just as wrong for T2, which IS a validator FAIL and
        must be accounted as one.
        """
        region = self.reclassification_region()
        flat_region = flat(region)

        # T2: the EXISTING branch, unchanged, with all three of its effects named.
        self.assertRegex(
            flat_region,
            r"(?i)T2 is a genuine validator FAIL",
            "the retry accounting does not identify T2 as a GENUINE validator FAIL — it arrives as "
            "a FAIL verdict and must be accounted as one (FR-3.2, DD-8)",
        )
        self.assertRegex(
            flat_region,
            # `flat()` eats the `**` emphasis, so the anchor is `On fail`, not `On **fail**`.
            r"(?i)flows through the existing On fail branch above, unchanged",
            "the retry accounting does not route T2 through the EXISTING `On **fail**` branch "
            "unchanged — a parallel failure path would duplicate the label and retry logic "
            "(FR-10.1, DD-8, NFR-6)",
        )
        for effect in (r"retryCount \+= 1", r"blocked:validation set", r"the executor re-run"):
            self.assertRegex(
                flat_region, f"(?i){effect}",
                f"the retry accounting does not name {effect!r} among T2's effects — the point of "
                f"stating the branch is that all of its effects apply (FR-10.1, DD-8)",
            )
        # T1 / T3: same attempt, no increment, no label.
        self.assertRegex(
            flat_region,
            r"(?i)T1 and T3 are caught before a validation verdict exists",
            "the retry accounting does not state that T1 and T3 are caught BEFORE a validation "
            "verdict exists — which is why there is no failure to account (FR-3.2, DD-8)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)re-run stages 2.3 within the same attempt",
            "the retry accounting does not state that T1 and T3 re-run stages 2–3 WITHIN THE SAME "
            "ATTEMPT (FR-3.2, DD-8)",
        )
        self.assertRegex(
            flat_region,
            r"(?i)do not increment retryCount and they do not set a label",
            "the retry accounting does not state that T1 and T3 neither increment `retryCount` nor "
            "set a label. Two increments halt the task at the user (`retryCount >= 2`), so charging "
            "a mis-declared output as a double failure is a behavioural change, not a nit "
            "(FR-3.2, FR-10.1, DD-8)",
        )
        self.assertRegex(
            flat_region, r"(?i)no new label is introduced on any path",
            "the retry accounting does not state that NO NEW LABEL is introduced on any path "
            "(FR-10.1, DD-8)",
        )

    def test_region_writes_only_code_and_never_directs_a_write_of_non_code(self):
        """FR-3.1 / FR-3.4 / sub-task 4.7: the mechanical guard behind the *stated* rule.

        `test_null_is_read_as_unclassified_and_non_code_is_never_written` asserts the subsection
        *says* it never writes `"non-code"`. A contract can say that and then do it two paragraphs
        later — the promise and the instructions are different text, and only the promise was pinned.
        This test checks the instructions: every `featureClass` assignment in the region assigns
        `"code"`, and no assignment of `"non-code"` occurs in any form.

        The direction of travel is the whole of FR-3.4. A single reachable write of `"non-code"` here
        makes the fallback a bidirectional classifier: monotonicity becomes unenforceable, and an
        exemption already recorded in `tasksValidatedUnderExemption` is silently re-granted for the
        rest of the feature.
        """
        region = self.reclassification_region()
        flat_region = flat(region)

        assigned = re.findall(r'(?i)set featureClass = "(non-code|code)"', flat_region)
        self.assertIn(
            "code", assigned,
            "the reclassification subsection contains no instruction setting `featureClass = "
            "\"code\"` at all — that assignment is the action the whole subsection exists to perform "
            "(FR-3.1)",
        )
        self.assertEqual(
            [value for value in assigned if value != "code"], [],
            f"the reclassification subsection instructs a write of `featureClass` other than "
            f"`\"code\"` (found {sorted(set(assigned))}). It may only ever move a value TO `\"code\"`; "
            f"a write of `\"non-code\"` here makes the fallback bidirectional and FR-3.4's "
            f"monotonicity unenforceable (FR-3.1, FR-3.4)",
        )
        # No assignment shape at all, however spelled — this catches `featureClass = "non-code"`
        # written without the leading verb the loop above keys on.
        self.assertNotRegex(
            flat_region, r'(?i)featureClass\s*=\s*"non-code"',
            "the reclassification subsection contains a `featureClass = \"non-code\"` assignment. "
            "The subsection is a one-way valve: every mention of `\"non-code\"` here must be the "
            "value being moved AWAY from or a negation, never a value being written (FR-3.1, FR-3.4)",
        )
        # Nor may it undo the audit record on the way through: FR-3.3's re-review reads that key
        # after the reclassification, so a clear here empties its only input.
        self.assertNotRegex(
            flat_region,
            r"(?i)(clear|empty|reset|delete|remove) (the )?classification\.tasksValidatedUnderExemption",
            "the reclassification subsection instructs a clear of "
            "`classification.tasksValidatedUnderExemption`. Reclassification is the moment a reader "
            "most expects a withdrawal, and it is exactly the moment FR-3.3 needs the record: the "
            "post-reclassification re-review reads that key to find which tasks were validated under "
            "the exemption (FR-3.3, NFR-5, A5-5)",
        )

    def test_the_retry_increment_is_charged_to_t2_only(self):
        """FR-3.2 / FR-10.1 / DD-8: the mechanical guard behind the retry-accounting prose.

        `test_retry_accounting_is_settled_and_introduces_no_label` asserts the three effects are
        *named* for T2 and *negated* for T1/T3. Both halves are satisfiable by a region that also
        charges an increment somewhere else — the prose would still read correctly and the assertion
        would still pass. So the placement is checked directly: exactly one `retryCount += 1` exists
        in the region, it falls inside T2's clause, and nothing after the T1/T3 clause begins spends
        an attempt or names a label.

        Why it is worth a test of its own: two increments halt the task at the user
        (`retryCount >= 2`), so charging T1 or T3 an attempt turns a mis-declared output into a
        double failure requiring human intervention — a behavioural change on the non-code path, not
        a nit. And T1/T3 fire *before* a verdict exists, so there is no FAIL to label.
        """
        region = self.reclassification_region()

        increments = list(re.finditer(r"retryCount`?\s*\+=\s*1", region))
        self.assertEqual(
            len(increments), 1,
            f"the reclassification subsection contains {len(increments)} `retryCount += 1` "
            f"instruction(s); exactly one is correct — T2's, which is a genuine validator FAIL "
            f"flowing through the existing `On **fail**` branch. T1 and T3 are caught before a "
            f"verdict exists and must spend no attempt (FR-3.2, FR-10.1, DD-8)",
        )
        t2 = re.search(r"(?i)T2 is a genuine validator FAIL", region)
        t1_t3 = re.search(r"(?i)T1 and T3 are caught before", region)
        self.assertIsNotNone(
            t2, "the retry accounting no longer identifies T2's clause (FR-3.2, DD-8)"
        )
        self.assertIsNotNone(
            t1_t3, "the retry accounting no longer identifies T1 and T3's clause (FR-3.2, DD-8)"
        )
        self.assertLess(
            t2.start(), increments[0].start(),
            "the single `retryCount += 1` is stated BEFORE T2's clause, so it is not attributable to "
            "T2 — an increment stated unattributed reads as applying to every trigger (FR-3.2, DD-8)",
        )
        self.assertLess(
            increments[0].start(), t1_t3.start(),
            "the single `retryCount += 1` falls at or after the T1/T3 clause, which must spend no "
            "attempt. Two increments halt the task at the user (`retryCount >= 2`), so a "
            "mis-declared output would present as a double failure (FR-3.2, FR-10.1, DD-8)",
        )
        # From the T1/T3 clause onward: no label name, and no second increment.
        tail = region[t1_t3.start():]
        self.assertNotRegex(
            tail, r"blocked:[a-z-]+",
            "the region names a `blocked:*` label at or after the T1/T3 clause. T1 and T3 are caught "
            "before a validation verdict exists, so there is no failure to label; T2's label comes "
            "from the existing `On **fail**` branch stated above it (FR-10.1, DD-8)",
        )

    def test_region_introduces_no_label_name_outside_the_frozen_vocabulary(self):
        """FR-10.1 / DD-8 / FR-9.1: every `blocked:` name in the new region is one of the five frozen
        label names, and the subsection applies no label of its own.

        The label vocabulary is frozen before this feature and the CI review-gate keys on it
        server-side, so a sixth name invented in prose is a label CI will never clear. `ready-to-merge`
        is additionally forbidden here outright: FR-9.1 fixes its single application point in the
        Feature Review Gate PASS branch, and a reclassification path that touched it would be a
        second one.
        """
        region = self.reclassification_region()

        found = set(re.findall(r"blocked:[a-z-]+", region))
        allowed = {name for name in FROZEN_LABEL_NAMES if name.startswith("blocked:")}
        self.assertFalse(
            found - allowed,
            f"the reclassification subsection names blocked:* label(s) outside the frozen "
            f"vocabulary: {sorted(found - allowed)}. The five names are fixed before this feature "
            f"and the CI review-gate keys on them, so an invented name is a label nothing clears "
            f"(FR-10.1, DD-8)",
        )
        self.assertNotIn(
            "ready-to-merge", region,
            "the reclassification subsection mentions `ready-to-merge`. FR-9.1 fixes its single "
            "application point in the Feature Review Gate PASS branch; a reclassification path that "
            "touches it is a second one (FR-9.1, FR-10.1, NFR-1)",
        )
        # It applies no label of its own: no concrete github-agent label invocation lives here.
        self.assertNotIn(
            "action: label", region,
            "the reclassification subsection issues a github-agent label operation of its own. T2 "
            "reuses the existing `On **fail**` branch and T1/T3 set no label at all (FR-10.1, DD-8)",
        )
        # And it adds no stage: the pipeline still has exactly four stage headings (FR-2.4).
        self.assertNotRegex(
            region, r"\*\*Stages? [\d &]+ —",
            "the reclassification subsection declares a stage heading of its own. It re-runs the "
            "EXISTING Stages 2 and 3; FR-2.4 forbids adding a stage for either class",
        )


# --- (6) Regression: the ready-to-merge singleton invariant ---------------------------------------


class ReadyToMergeSingletonRegressionTest(OrchestratorDocTestCase):
    """FR-9.1 / AC-7. Task 2 must not have created a second application point for the label.

    This is the load-bearing invariant of the whole feature, so it is guarded here at the first
    orchestrator edit as well as by the dedicated module a later task adds.
    """

    def test_ready_to_merge_set_exactly_once_in_the_feature_review_pass_branch(self):
        sets = label_set_invocations(self.body)
        r2m = [offset for offset, name in sets if name == "ready-to-merge"]
        self.assertEqual(
            len(r2m), 1,
            f"`ready-to-merge` is SET in {len(r2m)} place(s) in agents/orchestrator.md; FR-9.1 and "
            f"AC-7 require exactly one. Offsets: {r2m}",
        )

        pass_branch = re.search(r"\*\*On PASS \(both reviewers PASS\)", self.body)
        self.assertIsNotNone(pass_branch, "the Feature Review Gate PASS branch was not found")
        fail_branch = re.search(r"\*\*On FAIL \(either reviewer", self.body[pass_branch.start():])
        self.assertIsNotNone(fail_branch, "the Feature Review Gate FAIL branch was not found")
        pass_start = pass_branch.start()
        pass_end = pass_start + fail_branch.start()
        self.assertTrue(
            pass_start < r2m[0] < pass_end,
            "the single `ready-to-merge` set operation has moved OUT of the Feature Review Gate "
            "PASS branch — it may only be applied after both reviewers PASS (FR-9.1, NFR-1)",
        )

    def test_only_place_sentence_survives(self):
        """The prose that makes the singleton auditable must still be there."""
        self.assertRegex(
            flat(self.body),
            r"(?i)This is the only place ready-to-merge is ever applied",
            "the 'only place ready-to-merge is ever applied' sentence was lost",
        )
        self.assertRegex(
            flat(self.body),
            r"(?i)never before a whole-feature review PASS",
            "the 'never before a whole-feature review PASS' qualifier was lost (NFR-1)",
        )


# --- (7) Regression: the six frozen invariant spans, HEAD vs the working tree ---------------------


class FrozenSpanHeadToTreeTest(unittest.TestCase):
    """FR-11.2 / NFR-6 / A5 item 6: the six frozen invariant spans survive this feature's edits
    byte-identically.

    Every task that touches `agents/orchestrator.md` is required to verify this before and after, and
    every task so far has done it with a throwaway script. A throwaway script verifies the commit it
    was run for and nothing afterwards. This is the same check, resident in the suite, so the next
    edit to this file — by this feature's remaining tasks or by anything after it — cannot quietly
    reword an invariant while every requirement-anchored assertion stays green.

    The comparison is HEAD versus the working tree, which is the contracted form of the check. Note
    what that does and does not buy: once these edits are committed, HEAD *is* the tree and the
    comparison is trivially true for them. Its value is prospective — it goes red on the next
    uncommitted edit that disturbs a span, which is exactly when it is cheap to fix.
    """

    def setUp(self):
        self.extractor = load_frozen_span_extractor()

    def head_copy(self):
        """`agents/orchestrator.md` as of HEAD, or a skip when git cannot answer."""
        repo_root = ORCH_PATH.resolve().parent.parent
        try:
            result = subprocess.run(
                ["git", "show", "HEAD:agents/orchestrator.md"],
                cwd=str(repo_root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError as exc:
            self.skipTest(f"git not available, cannot read the HEAD copy: {exc}")
        if result.returncode != 0:
            self.skipTest(
                "cannot read agents/orchestrator.md from HEAD (not a git checkout, or the file is "
                f"not in HEAD): {result.stderr.decode('utf-8', 'replace').strip()}"
            )
        return result.stdout.decode("utf-8")

    def test_the_extractor_still_carries_exactly_six_patterns(self):
        """The count is itself part of the contract: A5 item 6 names six spans.

        Without this, deleting a pattern from Task 1's extractor would make the comparison below pass
        over five spans, then four — a check that gets weaker without ever going red. Tasks 5 and 10
        are held to this same extractor, so its size is not an implementation detail.
        """
        patterns = self.extractor.ORCH_INVARIANT_PATTERNS
        self.assertEqual(
            len(patterns), 6,
            f"Task 1's `ORCH_INVARIANT_PATTERNS` carries {len(patterns)} pattern(s); A5 item 6 names "
            f"SIX frozen spans. Keys present: {sorted(patterns)}",
        )

    def test_six_frozen_spans_are_byte_identical_between_head_and_the_tree(self):
        """FR-11.2 / A5 item 6: all six spans extract from both copies, and all six match."""
        patterns = self.extractor.ORCH_INVARIANT_PATTERNS
        extract = self.extractor.orchestrator_invariant_lines

        tree_spans = extract(ORCH_PATH.read_text(encoding="utf-8"))
        head_spans = extract(self.head_copy())

        # (i) Every span is still FINDABLE in the working tree. A pattern that stops matching makes
        # the identity comparison below vacuous for that span — silently, since a dict comparison over
        # two empty dicts is equal. This is the failure mode the check must not have.
        self.assertEqual(
            sorted(tree_spans), sorted(patterns),
            f"these frozen spans no longer match in the working-tree `agents/orchestrator.md`: "
            f"{sorted(set(patterns) - set(tree_spans))}. Either the invariant was reworded or the "
            f"pattern needs re-anchoring — and until it is resolved the byte-identity check below is "
            f"blind to that span (FR-11.2, A5 item 6)",
        )
        self.assertEqual(
            sorted(head_spans), sorted(patterns),
            f"these frozen spans do not match in the HEAD copy of `agents/orchestrator.md`: "
            f"{sorted(set(patterns) - set(head_spans))}. The baseline itself is unreadable, so "
            f"'unchanged since HEAD' cannot be established for those spans (FR-11.2, A5 item 6)",
        )

        # (ii) And every one is byte-identical. Reported per span: which invariant moved is the whole
        # of the diagnosis.
        for key in sorted(patterns):
            self.assertEqual(
                head_spans[key], tree_spans[key],
                f"the frozen invariant span {key!r} is NOT byte-identical between HEAD and the "
                f"working tree.\n"
                f"  HEAD: {head_spans[key]!r}\n"
                f"  tree: {tree_spans[key]!r}\n"
                f"These spans are frozen for the duration of this feature: the `ready-to-merge` "
                f"single-application-point rule, the clear-before-set ordering, the clear-every-"
                f"recorded-label wording, the scaffold-push scoping, and the two sole-gh-runner "
                f"sentences. They are the invariants the A2 byte-identity carve-out is defined "
                f"against — a reworded invariant is `drift`, not a `pending` sync (FR-11.2, NFR-6, "
                f"A5 item 6)",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
