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

import json
import re
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

# The C0 allow-list body, verbatim from design.md C0 as amended by A3 and A4 (itself unparaphrased
# from the requirements "Definitions used throughout"): the repository enumeration is OPEN on both
# sides, the application-code side names the repository-root `CLAUDE.md` with its criterion, the
# non-code side names the repository-root `README.md` with its criterion, and a `PRECEDENCE` clause
# subordinates the AMB-1..AMB-5 ambiguity triggers to the enumeration. Tasks 6/7/8 replicate this
# block into four more agent contracts, so it must not drift here: this is its normative home (DD-5).
CANONICAL_ALLOW_LIST = """\
NON-CODE ARTIFACT — exactly one of:
  1. a spec artifact under .specs/features/<feature-name>/
     (requirements.md, design.md, tasks.md, scope.md, .spec-state.json)
  2. a committed prose/documentation file that the project's layout or steering does NOT
     designate as source, agent/prompt contract, template, script, or configuration
     (in this repository these include, but are not limited to, the repository-root
     README.md — descriptive documentation that nothing loads into an agent's context)
  3. a knowledge-vault mutation recorded by vault-writer in
     .specs/features/<feature-name>/vault/.write-log.jsonl

APPLICATION CODE — anything else: executable source, tests, scripts, hooks, CI workflows,
  templates, runtime configuration, and any prose file the project designates as a
  behaviour-bearing contract (in this repository these include, but are not limited to,
  agents/*.md, commands/*.md, and the repository-root CLAUDE.md — a contract the project
  loads into every agent's context at session start).

PRECEDENCE — this enumeration settles every file it names, on the side it names it. The
  ambiguity triggers AMB-1 through AMB-5 apply only to a file this enumeration does not
  already settle, and never override it. Both lists stay open: a file's absence from
  either list is evidence of nothing.
"""

CLASSIFICATION_SUBKEYS = (
    "basis",
    "decidedAt",
    "override",
    "tasksValidatedUnderExemption",
    "reclassification",
)


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
        # The two conditions are not merely promised in the abstract — the report shape names them.
        self.assertRegex(
            flat_region,
            r"(?i)featureClass absent AND phase already implementation",
            "the legacy report shape does not name the two conditions concretely (an absent "
            "`featureClass` AND a `phase` already at `implementation` or beyond) (FR-1.7, NFR-5)",
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
        """FR-1.3 / DD-5: the fenced body is the canonical C0 text, normalised for whitespace only.

        Tasks 6/7/8 replicate this block verbatim into four other agent contracts and a later test
        asserts all five copies are normalised-identical. Pinning the normative home here is what
        makes that replication meaningful — a silent edit here would propagate as "correct".
        """
        self.assertEqual(
            squash(self.allow_list_block()), squash(CANONICAL_ALLOW_LIST),
            "the C0 allow-list block has drifted from its canonical text (design C0 / DD-5). This "
            "block is normative and is replicated verbatim into four other agent contracts; change "
            "it in the design first, then in all five copies.",
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

        # The non-code side: README.md, with the criterion that puts it there.
        self.assertIn(
            "README.md", block,
            "the allow-list does not name the repository-root README.md at all (A3-3)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)the repository-root README\.md .{0,20}descriptive documentation that nothing "
            r"loads into an agent's context",
            "the repository-root README.md is not designated a category-2 non-code artifact WITH "
            "its criterion (nothing loads it into an agent's context) (FR-1.3, A3-3)",
        )
        readme_at = flat_block.index("README.md")
        self.assertLess(
            readme_at, flat_block.index("APPLICATION CODE"),
            "the repository-root README.md is named on the APPLICATION CODE side of the "
            "enumeration — nothing loads it into an agent's context, so it is a category-2 "
            "non-code artifact (FR-1.3, A3-3)",
        )

    def test_allow_list_precedence_clause_subordinates_the_ambiguity_triggers(self):
        """FR-1.3 / FR-1.4 / A4-1: the fenced block carries the `PRECEDENCE` stanza, and it is the
        stanza that is replicated — so the subordination rule travels with the enumeration.

        The enumeration and the AMB triggers are two rules over the same files. Without an explicit
        ordering, `CLAUDE.md` is both "application code by enumeration" and "prose in a directory
        steering designates as contract" (AMB-3), and a reader may take either. The `PRECEDENCE`
        stanza must live INSIDE the fence: Tasks 6/7/8 replicate only the fenced block into four
        other agent contracts, so a precedence rule stated outside it would not reach them.
        """
        block = self.allow_list_block()
        flat_block = flat(block)

        self.assertIn(
            "PRECEDENCE", block,
            "the fenced C0 block carries no `PRECEDENCE` stanza — Tasks 6/7/8 replicate this fence "
            "and only this fence, so the subordination rule would not reach the four replicas "
            "(A4-1, DD-5)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)this enumeration settles every file it names, on the side it names it",
            "the `PRECEDENCE` stanza does not state that the enumeration settles every file it "
            "names, on the side it names it (A4-1)",
        )
        self.assertRegex(
            flat_block,
            r"(?i)the ambiguity triggers AMB-1 through AMB-5 apply only to a file this enumeration "
            r"does not already settle",
            "the `PRECEDENCE` stanza does not subordinate AMB-1…AMB-5 to the enumeration by name "
            "(FR-1.4, A4-1)",
        )
        self.assertRegex(
            flat_block, r"(?i)and never override it",
            "the `PRECEDENCE` stanza does not forbid an ambiguity trigger OVERRIDING the "
            "enumeration — subordination without that clause is advisory (FR-1.4, A4-1)",
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
        self.assertRegex(
            region,
            r"(?i)it is false only when every output this task declares classifies non-code",
            "the preamble does not state the fail-safe direction of "
            "`taskProducesApplicationCode` — it must be `false` only when EVERY declared output "
            "is non-code (FR-1.4, FR-2)",
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
        self.assertRegex(
            region,
            r"(?i)append this task's number to classification\.tasksValidatedUnderExemption",
            "Stage 3 does not append the task number to "
            "`classification.tasksValidatedUnderExemption` when it issues the artifact-conformance "
            "instruction — the exemption would then be unauditable and FR-3.3's reclassification "
            "re-review would have nothing to re-cover",
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


# --- (5) Regression: the ready-to-merge singleton invariant ---------------------------------------


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
