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
    is re-asserted here as a regression guard (FR-9.1, AC-7).

Covers FR-1, FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-9.1, FR-11, FR-11.1,
FR-11.2, NFR-5, NFR-6.

Later tasks (3, 4, 5) extend this module by adding further `OrchestratorDocTestCase` subclasses —
the base class, the section/region helpers and the text normalisers below are shared for that
purpose. Nothing here writes anything, anywhere.

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

# The C0 allow-list body, verbatim from design.md C0 (itself unparaphrased from the requirements
# "Definitions used throughout"). Tasks 6/7/8 replicate this block into four more agent contracts,
# so it must not drift here: this is its normative home (DD-5).
CANONICAL_ALLOW_LIST = """\
NON-CODE ARTIFACT — exactly one of:
  1. a spec artifact under .specs/features/<feature-name>/
     (requirements.md, design.md, tasks.md, scope.md, .spec-state.json)
  2. a committed prose/documentation file that the project's layout or steering does NOT
     designate as source, agent/prompt contract, template, script, or configuration
  3. a knowledge-vault mutation recorded by vault-writer in
     .specs/features/<feature-name>/vault/.write-log.jsonl

APPLICATION CODE — anything else: executable source, tests, scripts, hooks, CI workflows,
  templates, runtime configuration, and any prose file the project designates as a
  behaviour-bearing contract (in this repository: agents/*.md and commands/*.md).
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

    def sub_region(self, start_pat, end_pat, label):
        """The slice of the classification-gate region from `start_pat` up to `end_pat`.

        BOTH anchors are asserted. A missing end anchor must never be tolerated: silently
        extending the slice to the end of the classification gate turns a scoped assertion into a
        whole-gate assertion **while staying green** — every positive pattern would then be
        satisfiable by text belonging to a later paragraph, and every `assertNotRegex` would be
        evaluated over paragraphs it was never meant to police. Fail loudly instead.
        """
        region = self.gate_region()
        ms = re.search(start_pat, region)
        self.assertIsNotNone(ms, f"classification gate has no {label} paragraph")
        rest = region[ms.start():]
        me = re.search(end_pat, rest[1:])
        self.assertIsNotNone(
            me,
            f"the {label} region has no end anchor matching {end_pat!r} after it — the region "
            f"would silently run to the end of the classification gate and every assertion scoped "
            f"to {label} would degrade into a whole-gate assertion without going red. Re-anchor "
            f"this region against the current section structure.",
        )
        return rest[: me.start() + 1]


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

        # Enumerated triggers: at least four, each a distinct list item, each substantive.
        # Any markdown list marker counts — `-`, `*`, `+` or an ordered `1.` / `1)` — so a purely
        # cosmetic re-styling of the enumeration does not turn this assertion red.
        triggers = re.findall(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+.*$", region)
        self.assertGreaterEqual(
            len(triggers), 4,
            f"the fail-safe enumerates only {len(triggers)} ambiguity trigger(s); design C1 lists "
            f"four (no declared outputs / unresolvable output / prose in a designated directory / "
            f"steering silent)",
        )
        flat_triggers = flat("\n".join(triggers))
        for label, pattern, why in (
            ("no declared outputs", r"(?i)declares no outputs", "a task declaring no outputs"),
            ("unresolvable output", r"(?i)cannot be resolved to a concrete path",
             "an output that resolves to no concrete path or category"),
            ("designated directory", r"(?i)steering designates as source",
             "a prose file inside a directory steering designates as source/contract/template"),
            ("steering silent", r"(?i)steering is silent", "steering silent and location unhelpful"),
        ):
            self.assertRegex(
                flat_triggers, pattern,
                f"ambiguity trigger '{label}' is missing — {why} must be enumerated (FR-1.4, R7)",
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
        start, end = self.allow_list_span()
        fence = re.search(r"```[a-zA-Z]*\n(.*?)```", self.body[start:end], re.DOTALL)
        self.assertIsNotNone(fence, "the allow-list section has no fenced block")
        self.assertEqual(
            squash(fence.group(1)), squash(CANONICAL_ALLOW_LIST),
            "the C0 allow-list block has drifted from its canonical text (design C0 / DD-5). This "
            "block is normative and is replicated verbatim into four other agent contracts; change "
            "it in the design first, then in all five copies.",
        )

    def test_allow_list_names_all_three_categories_and_the_code_catch_all(self):
        """FR-1.3 / NFR-6: the substantive content — the three non-code categories and the
        application-code catch-all naming this repository's contract globs."""
        start, end = self.allow_list_span()
        fence = re.search(r"```[a-zA-Z]*\n(.*?)```", self.body[start:end], re.DOTALL)
        self.assertIsNotNone(fence, "the allow-list section has no fenced block")
        block = fence.group(1)

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


# --- (4) Regression: the ready-to-merge singleton invariant ---------------------------------------


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
