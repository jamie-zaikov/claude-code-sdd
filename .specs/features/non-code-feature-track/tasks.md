# Tasks: non-code-feature-track

<!-- This file is owned by the tasks-agent. Do not edit manually during SDD workflow. -->

## Overview

11 top-level tasks implement the first-class non-code track: the byte-identity carve-out that makes
intermediate commits viable at all (A1/A2), four orchestrator contract edits (classification gate +
state schema, per-task routing, reclassification fallback, feature-review gate wiring), the
task-tester no-code behaviour, the task-validator artifact-conformance mode, the shared non-code
review scope in both reviewers, a CI-template lock test, the documentation updates, and the F3
remediation of the non-blocking findings the Task 1 reviews left against the carve-out.

The deliverable is mostly markdown, because in this repository behaviour-bearing prose **is** the
implementation: `agents/*.md` and `commands/*.md` are classified as application code by the very
allow-list this feature installs. This feature is therefore itself `featureClass: "code"` and runs
the unchanged five-stage pipeline while building the non-code path (design Flow E).

### Amendment status and progress

- **Tasks 1, 2, 3 and 4 are complete and committed** (`8de970c`, `baf7245`, `562c6d5`, `c73de3f`);
  all four passed all five pipeline stages. Their checkboxes below are ticked. **Tasks 5–11 have
  not run** and are unticked.
- **Design amendments A3 and A4 are absorbed into this list.** A3 items 1–7 and A4's authoritative
  propagation block (*design.md → Amendment A4 → What A3 and A4 together require of `tasks.md`*) are
  applied: the C0/C1/C2 contract corrections land in **Task 3**, which grows materially as a result;
  Task 4 keeps C4 consistent with the `null`-is-unclassified reading rule; and the six requirement
  rows A4 names (FR-1.1, FR-1.3, FR-1.4, FR-1.5, FR-1.7, NFR-5) gain Task 3 in the coverage table.
  **A3's item 8 is superseded in full by A4** and is not followed.
- **Design amendment A5 is absorbed into this list.** Its authoritative propagation block is
  *design.md → Amendment A5 → What A5 requires of `tasks.md`*, and every item in it is applied.
  Because **Task 3 already shipped the A3/A4 form** of C0's fence, A5's corrections to that text are
  **re-edits of committed work whose owner is Task 4** — seven new sub-tasks **4.9–4.15** (A5 item
  1(a)–(g)), with sub-tasks **4.4** and **4.8** amended in place; **Task 8** carries the rewritten
  FR-6.4 attribution rule (sub-tasks 8.5, 8.6 and 8.10, A5 item 3); Tasks **6** and **7** now
  replicate C0 as it stands after **Task 4**, not after Task 3 (A5 item 4); and the **eight**
  requirement rows A5 item 5 names (FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.7, FR-2, FR-2.1, NFR-4)
  gain Task 4 in the coverage table. **No completed task is re-executed and no tick is reversed.**
- **Numbering under Task 4, stated so it does not read as an error.** Sub-tasks **4.9–4.15 are
  inserted physically above 4.8**, which keeps its number and remains the task's **last** sub-task.
  A5 item 1 left that choice to this agent, and **nothing is renumbered**: `design.md`,
  `.spec-state.json`, this feature's PR thread and its audit chain all cite specific sub-task
  numbers, so renumbering would invalidate live citations. The document's own invariant — the final
  sub-task of every task is its test sub-task — is preserved **by position, not by ordinal**.
- **Sub-task 2.1's original C0 wording and sub-task 2.2's original entry-predicate wording are
  superseded.** Both are annotated in place under Task 2 and corrected in Task 3. No completed work
  is re-executed.
- **Sub-tasks 3.1, 3.4, 3.7, 3.9, 3.12 and 3.13 are superseded by A5** wherever they state C0's
  fence, its precedence pointer, the routing preamble's scope, the exemption record's append point,
  the legacy report's condition, or the assertions pinning any of those. Task 3 executed them as
  written and its output is correct for A3/A4; the corrections land in Task 4. Annotated in place
  under Task 3.
- **Task 11 is new**: the F3 remediation of Task 1's non-blocking code- and security-review findings.
  It must land before the whole-feature review.

### How to read this list

Each top-level task is one coherent design component (or a tight pair), sized for a single
Execute → Test → Validate → Code Review → Security Review pass. Every task cites the requirement IDs
it satisfies, names its design component, and lists every file it touches. The final sub-task of
each task is always its test sub-task — **by position, not by ordinal**: in Task 4 that sub-task
keeps the number **4.8** while the seven A5 sub-tasks **4.9–4.15** sit above it (see the numbering
note above). A traceability table at the end confirms every FR-1…FR-13 and NFR-1…NFR-11 is covered.

### Execution environment (context, not a task)

The task-executor works in the **shared feature-branch checkout** on `feat/non-code-feature-track` —
not an isolated worktree. Tasks run sequentially, so each task inherits the committed output of every
prior task. Task N may rely on Task N-1's files existing on disk; it must not re-create them.

### The `**Files:**` field is load-bearing here

Design component C1 makes each task's `**Files:**` field the primary input to feature classification.
The fields below are exhaustive and path-precise for that reason: a task that touches a file not
listed is a task the classifier would mis-read. If an executor finds it must touch an unlisted file,
that is a signal to stop and report, not to widen silently.

### Global constraints — apply to every task without exception

1. **No task writes anywhere under `~/.claude/`, runs `./install.sh`, or modifies `install.sh`**
   (FR-12.1, NFR-10, amendment A1). The global copies are derived install artifacts; the operator
   syncs them by running `./install.sh` **after merge**. A repository copy ahead of an unsynced
   global copy is a legitimate pending-sync window, never a defect to "fix".
2. **No task modifies `ci-templates/workflows/sdd-review-gate.yml`**, any other CI workflow or
   template, or any hook (FR-10, NFR-2). Task 9 reads that file; it does not write it.
3. **No task modifies `agents/tasks-agent.md`.** Risk R9 records that its rule 5 reads as excluding
   non-code task lists; no requirement authorises changing it. It is a flagged follow-up, not scope.
4. **No task deletes or weakens any existing assertion in `tests/`**, with exactly the two carve-outs
   Task 1 implements (FR-11.8). Task 11 hardens those two reworked assertions without widening the
   carve-out, which stays closed at two. `tests/test_install_pre_push_hook.py` and
   `tests/test_sdd_init_ci_templates.py` are **not** modified — they point `HOME` at a throwaway
   tempdir and are unaffected by the pending-sync window.
5. **No new agent, no new tool grant, no new write target, no new label** (NFR-3, FR-10.1). Every
   change is confined to the text of existing agent contracts, tests under `tests/`, and the two
   documentation files.
6. Every new test module is **stdlib-only `unittest`**, resolves paths with
   `Path(__file__).resolve().parent.parent`, and carries its own local helper copies — no new shared
   importable module (FR-11.1, C12 precedent).

### Sequencing (why the order is what it is)

- **Task 1 is first and is not negotiable.** `agents/orchestrator.md` and `CLAUDE.md` are
  byte-identical to their global copies today, so `test_repo_and_global_copies_are_byte_identical`
  (`tests/test_orchestrator_label_lifecycle.py`) and `test_two_claude_files_byte_identical`
  (`tests/test_docs_updates.py`) turn red on the **first** edit to either file and block the pipeline
  on its own suite. The rework must land before — never after — the edits it covers.
- Tasks 2–5 edit `agents/orchestrator.md` and are unblocked only once Task 1 has landed.
- Every agent-contract edit lands **in the same task as** the assertions covering it, so no committed
  test asserts text that does not yet exist.
- **The C0 fence's final form, and its pinned constant, must land before Task 6** (A3 item 1;
  A4 item 1(a); A5 item 1(a) and sequencing constraint 5). Task 3 landed the A3/A4 form of the fence
  and its `CANONICAL_ALLOW_LIST` pin; **A5 corrects that committed text, so the final form lands in
  Task 4 sub-task 4.9**, which still precedes Task 6. Tasks 6, 7 and 8 replicate the block and Task 8
  asserts all five copies are normalised-identical. If the correction landed after Task 6, four
  copies of the superseded wording would ship and the identity assertion would lock the wrong text
  in place.
- Task 8 carries `test_allow_list_blocks_identical` because it is the first point at which all five
  copies of the C0 allow-list block exist (orchestrator → Task 2, corrected in Task 3 and finalised
  in Task 4; tester → Task 6, validator → Task 7, both reviewers → Task 8).
- Task 10 edits `CLAUDE.md`, which Task 1 has already made safe.
- **Task 11 is sequenced last but is not optional.** It edits only Task 1's artifacts, so it is
  unblocked from the moment Task 1 lands; it is placed last because its findings were raised against
  Task 1 as non-blocking. It **must land before the whole-feature review**.

---

## Task 1: Byte-identity carve-out — rework the two live-global assertions (A1/A2)
- [x] 1. Rework `test_two_claude_files_byte_identical` and `test_repo_and_global_copies_are_byte_identical` to satisfied-or-pending, so intermediate commits stop failing on a legitimate pending-sync window.

**Description:** Implement the A1 resolution and the A2 extension in the design. Both assertions
currently demand byte-identity with a live `~/.claude` copy and skip only when that copy is
unreadable, so both fail the instant this feature edits `CLAUDE.md` or `agents/orchestrator.md`.
Replace raw byte-identity with a three-state discriminator — `satisfied` / `pending` / `drift` —
that still FAILs on genuine drift. This is the **only** authorised carve-out in the suite and is
closed at exactly two assertions; nothing else in either module changes. **This task must land
before Tasks 2–5 (orchestrator edits) and before Task 10 (`CLAUDE.md` edit).**

**Sub-tasks:**
- [x] 1.1. In `tests/test_docs_updates.py`, derive the global path from `Path.home()`:
  `GLOBAL_CLAUDE = Path.home() / ".claude" / "CLAUDE.md"`, replacing the hardcoded absolute. No
  environment-variable override is added — FR-11.8 permits `Path.home()` and nothing more. CI
  behaviour is unchanged (the path does not exist there, so the existing skip fires). (FR-11.8)
- [x] 1.2. Add a module-level `claude_sync_state(repo_text, global_text, extract_invariants)` helper
  to `tests/test_docs_updates.py` returning `'satisfied' | 'pending' | 'drift'`, evaluated in order:
  (1) `satisfied` when the texts are equal; (2) `drift` when **either** (a) any invariant key
  extracted from the repository copy is missing from the global copy or differs after normalisation,
  **or** (b) any ATX heading (normalised, outside code fences) present in the global copy is absent
  from the repository copy — containment is directional, repository-only headings are the normal
  signature of a pending sync; (3) `pending` otherwise. The invariant extractor is a **parameter**,
  so the same state machine serves both assertions. (FR-11.8, NFR-10, DD-6)
- [x] 1.3. Rework `test_two_claude_files_byte_identical` in place — same name, same
  unreadable-global skip — to call the helper with the existing `github_agent_lines()` extractor
  (keys `bullet`, `gh_line`, `invariant`) and assert
  `assertNotEqual(state, "drift", <message naming the diverging key or global-only heading>)` plus
  `assertIn(state, {"satisfied", "pending"})`, so an unhandled state can never pass silently. Do
  **not** extend the invariant set with this feature's new classification prose (DD-7). Its
  docstring must state the carve-out rationale, citing **FR-11.8** and **NFR-10**: the repository
  copy is authoritative, the global copy is a derived install artifact synced post-merge by
  `./install.sh`, the pending window is legitimate and must never be resolved by writing to
  `~/.claude/`, and genuine drift still fails. (FR-11.8, NFR-10, AC-8, AC-10)
- [x] 1.4. In `tests/test_orchestrator_label_lifecycle.py`, derive `GLOBAL_ORCH_PATH` from
  `Path.home()` and add a local copy of the same sync-state helper (local copy, not an import —
  no new shared module). (FR-11.8, FR-11.1)
- [x] 1.5. Add an orchestrator invariant extractor to that module pulling the file's **invariant
  instruction lines**: the `ready-to-merge` single-application-point sentence, the
  clear-`blocked:*`-before-set ordering, the clear-**every**-recorded-label wording, the
  scaffold-push-only-on-first-scaffold scoping, and the "never runs `gh` / `git push` yourself"
  framing. Rework `test_repo_and_global_copies_are_byte_identical` in place — same name, same
  absent/unreadable skip — to the same satisfied-or-pending assertion shape, with the same
  rationale docstring citing FR-11.8 and NFR-10. The drift discriminator must be a genuine content
  comparison, **never** a blanket skip taken whenever the two copies differ. (FR-11.8, NFR-10, AC-8)
- [x] 1.6. Confirm nothing else changes: `test_two_claude_ownership_lines_consistent`,
  `test_global_required_lines_present`, and every other assertion in both modules are untouched, and
  no other test module is edited. (FR-11.8, AC-8)
- [x] 1.7. Test: run `python3 -m unittest discover -s tests -v` and assert the full suite passes with
  the working tree as-is; then verify the discriminator by exercising the sync-state helper directly
  (in-test fixture strings, no file writes outside the repo) for all three states — equal texts →
  `satisfied`; repository copy with an added section → `pending`; a global copy missing or restating
  an invariant line, and a global copy carrying a heading the repository copy lacks → `drift`. Assert
  no write occurred anywhere under `~/.claude/`. (FR-11.8, FR-11.1, NFR-10, AC-8)

**Requirements:** FR-11, FR-11.1, FR-11.8, NFR-10, NFR-6
**Design Reference:** *A1 resolution*; *Conflict C-1* / amendment **A2**; DD-6, DD-7, DD-9; C12 (the
reworked-module row); risks R3, R6
**Files:** `tests/test_docs_updates.py` (modify — exactly three edits: the `GLOBAL_CLAUDE` constant,
the new `claude_sync_state()` helper, the reworked `test_two_claude_files_byte_identical`),
`tests/test_orchestrator_label_lifecycle.py` (modify — exactly the `GLOBAL_ORCH_PATH` constant, the
local helper + orchestrator invariant extractor, and the reworked
`test_repo_and_global_copies_are_byte_identical`)

---

## Task 2: Orchestrator — C0 allow-list + Feature Classification Gate + state schema (C0, C1, C2)
- [x] 2. Add the normative non-code artifact allow-list, the Feature Classification Gate, and the `.spec-state.json` schema delta to `agents/orchestrator.md`.

**Description:** Insert the classification gate as a new `###` section **between** the existing
`### Consistency Gate (runs automatically after tasks confirmed, before implementation)` section and
the existing ``### `implementation` `` section, carrying the C0 allow-list block verbatim
(`agents/orchestrator.md` is its normative home), and extend the `## State File Management`
initialization block and its schema prose with `featureClass` and the `classification` object.
Depends on Task 1. Writes no label and makes no GitHub call — the gate performs no remote action.

**Sub-tasks:**
- [x] 2.1. Add the C0 block under the exact heading
  `#### Non-code artifact allow-list (normative — identical in every agent that classifies)`, as a
  single fenced block reproducing the requirements definition unparaphrased (three NON-CODE ARTIFACT
  categories; APPLICATION CODE as everything else, naming `agents/*.md` and `commands/*.md` for this
  repository). Byte-for-byte reusable — Tasks 6, 7 and 8 replicate it verbatim. (FR-1.3, NFR-6, DD-5)
  **[Wording superseded by A3-3 / A4-1 — see the supersession note after sub-task 2.10. Executed as
  written; the landed block is corrected in Task 3 sub-task 3.7 and finalised in Task 4 sub-task
  4.9 per A5.]**
- [x] 2.2. Add the section headed
  `### Feature Classification Gate (runs automatically after the consistency gate, before implementation)`
  in the placement above, specifying: it runs immediately after the consistency gate resolves PASS
  (including the `(d) override and proceed` path), in the **same state-file write** that sets
  `phase = "implementation"`; exactly once per feature; not re-run on resume when `featureClass` is
  already present. (FR-1, DD-1)
  **[The final clause — "not re-run on resume when `featureClass` is already present" — is the
  defective key-presence entry predicate. Superseded by A3-1; see the supersession note after
  sub-task 2.10. Already repaired in the landed contract (`baf7245`).]**
- [x] 2.3. Specify the inputs: (a) the confirmed `tasks.md`, taken primarily from each task's
  **`**Files:**` field** (defined by the task template at `agents/tasks-agent.md:62`) and secondarily
  from the task body and sub-tasks where that field is absent or incomplete; (b) `design.md`, only to
  resolve outputs named by component rather than path; (c) `.specs/steering/structure.md` and
  `tech.md` for the project's designation of source/contract/template/script/configuration. State
  explicitly that the gate **never** inspects a git diff to classify, and why: at this point nothing
  has been implemented. (FR-1.2, D1)
  **[Three inputs only. A5 item 1(g) adds a fourth, designation-only input (d) — the repository-root
  `CLAUDE.md` and the files it imports, read solely to run C0's `PRECEDENCE` CHECK — in Task 4
  sub-task 4.15. The never-inspects-a-git-diff sentence survives verbatim.]**
- [x] 2.4. Specify the per-output rule (an output is non-code iff it matches one of the three
  allow-list categories, otherwise application code) and the per-feature rule
  (`featureClass = "non-code"` iff every task declares at least one output **and** every declared
  output of every task classifies non-code; otherwise `"code"`). (FR-1.3)
- [x] 2.5. Specify the fail-safe with enumerated ambiguity triggers so the rule is checkable: a task
  declares no outputs; an output cannot be resolved to a concrete path or to one of the three
  categories; a prose file sits inside a directory steering designates as source/contract/template;
  steering is silent and the location does not settle it. State plainly that `"code"` is the
  fail-safe direction because it preserves today's behaviour exactly. (FR-1.4, R7)
  **[Four triggers only. Superseded by A3-4 (AMB-5) and A4-1 (the `PRECEDENCE` subordination); both
  land in Task 3 sub-tasks 3.8 and 3.9. A5-1 then rescopes that subordination to the
  file-classifying triggers AMB-2…AMB-4 in Task 4 sub-tasks 4.9 and 4.10.]**
- [x] 2.6. Specify record-and-report: write `featureClass` and the `classification` object, and
  report to the user the recorded value **and** the basis — one line per task naming its declared
  outputs and their classification. (FR-1.5, NFR-5)
- [x] 2.7. Specify the override rule (an override toward `"code"` is always honoured; toward
  `"non-code"` only when the FR-1.3 test already holds, otherwise refuse, name the offending task's
  application-code output, and keep `"code"`; every override, accepted or refused, is recorded) and
  the legacy-state rule (absent `featureClass` → treat as `"code"`, proceed on the unchanged code
  path, no retro-classification). (FR-1.6, FR-1.7, R4)
  **[The legacy-state clause states bare absence. Superseded by A3-2's two-condition rule, already
  repaired in the landed contract (`baf7245`); the missing legacy-branch report lands in Task 3
  sub-task 3.12, and its reported condition is corrected to "`implementation` or beyond" in Task 4
  sub-task 4.14 per A5-6.]**
- [x] 2.8. In `## State File Management`, add `"featureClass": null` and the `classification` object
  (`basis`, `decidedAt`, `override`, `tasksValidatedUnderExemption`, `reclassification`) as sibling
  top-level keys after `taskStatus`, and add the schema prose documenting `featureClass`'s two
  permitted values `"code"`/`"non-code"`, its `null`-before-gate and absent-in-legacy-files states,
  and each `classification` sub-key including the `override` and `reclassification` object shapes.
  State that `featureClass` is the single source of truth and `classification` carries only
  provenance. (FR-1.1, FR-1.5, FR-1.6, FR-3.1, FR-3.3, NFR-5)
- [x] 2.9. Confirm the section mentions no `ready-to-merge`, no label operation, and no CI reference.
  (FR-9.1, FR-10.1)
- [x] 2.10. Test: create `tests/test_orchestrator_feature_class.py` (stdlib-only `unittest`, paths
  resolved relative to the test file) asserting: the classification-gate heading exists and its
  offset lies **between** the consistency-gate section and the `implementation` section (ordering,
  not mere presence); `featureClass` appears in the state-file JSON block; both permitted values are
  named in the schema prose; the five `classification` sub-keys are documented; the fail-safe default
  is stated with its ambiguity triggers; the text states classification derives from declared task
  outputs and explicitly disclaims deriving it from a git diff; the C0 block is present under its
  exact heading; and no `ready-to-merge` token appears anywhere in the classification-gate region.
  Run the full suite. (FR-11, FR-11.1, FR-11.2, NFR-6)

**Superseded wording (A3/A4) — do not restate these sub-tasks anywhere.** Task 2 is complete and is
**not** re-executed; every correction below lands in Task 3.

- **Sub-task 2.1** told the executor to name "`agents/*.md` and `commands/*.md` for this repository",
  reproducing the design's **closed** enumeration. The correct form (A3-3 + A4-1) is an **open**
  enumeration on both sides, naming the repository-root `CLAUDE.md` on the application-code side and
  the repository-root `README.md` on the non-code side, each with the criterion that decides it, plus
  a `PRECEDENCE` stanza. Any future restatement of C0 uses the A3+A4 form, never this one — and, per
  **A5**, the A5 form once Task 4 sub-task 4.9 has landed it.
- **Sub-task 2.2** carried the defective **entry-predicate** formulation. "Not re-run on resume when
  `featureClass` is already present" keys on **key presence**, and C2 ships `"featureClass": null`, so
  a feature resumed in a later session would skip the gate and enter implementation with a value the
  schema prose itself declares invalid (Task 2 code review, High #2). The correct rule (A3-1), already
  implemented in `baf7245`: run the gate **unless** `featureClass` is already set to `"code"` or
  `"non-code"` — absent and `null` both mean unclassified and both make the gate run.
- **Sub-task 2.5** enumerates **four** ambiguity triggers. The set is now **five** — AMB-5,
  "`tasks.md` declares no tasks at all" (A3-4) — and the triggers are subordinate to C0's
  `PRECEDENCE` clause (A4-1), which **A5-1** rescopes: only the **file-classifying** triggers
  AMB-2…AMB-4 are subordinate to the enumeration, while AMB-1 and AMB-5 are feature-level and always
  apply.
- **Sub-task 2.7** states the legacy rule as bare absence. The correct rule (A3-2), already
  implemented in `baf7245`, is **two conditions together**: `featureClass` absent **and** `phase`
  already `implementation` or beyond. The legacy branch must additionally **report** its
  determination, which is not yet implemented.

**Requirements:** FR-1, FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-11.1, FR-11.2,
NFR-5, NFR-6
**Design Reference:** C0, C1, C2; DD-1, DD-5; risks R4, R7
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (new)

---

## Task 3: Orchestrator — A3/A4 corrections to C0/C1/C2 + per-task routing of `featureClass` (C0, C1, C2, C3, I1)
- [x] 3. Land the A3/A4 corrections to the text Task 2 committed, and forward `featureClass` and `taskProducesApplicationCode` to Stages 2, 3, 4 and 5 without changing the stage order or the code path.

**Description:** Two bodies of work in one file. **(i) The A3/A4 corrections** to what Task 2 landed:
C0's fenced allow-list block and its `CANONICAL_ALLOW_LIST` pin, AMB-5 and the precedence pointer in
the fail-safe list, the two `## State File Management` schema clauses, and the legacy-branch report.
These follow the authoritative propagation block in *design.md → Amendment A4 → What A3 and A4
together require of `tasks.md`*, item 1(a)–(f); follow it literally. **(ii) The routing work:** the
shared preamble and the stage-specific bullets inside ``### `implementation` `` — no new stage, no
reordering, no new user prompt. Depends on Tasks 1 and 2 (`featureClass` must be defined and recorded
before it can be routed).

**This task is materially larger than it was before A3/A4.** Six contract edits plus five routing
edits in `agents/orchestrator.md`, and a test sub-task carrying an eight-item assertion inventory
(three verify-and-keep, five new or changed) on top of the routing assertions. Size it as such rather
than discovering it mid-execution. **Hard ordering constraint: sub-task 3.7 must land before Task 6**,
because Tasks 6, 7 and 8 replicate C0's block and Task 8 asserts all five copies are
normalised-identical.

Sub-tasks 3.1–3.6 are the routing work, unchanged from the pre-amendment list; 3.7–3.12 are the
A3/A4 corrections; 3.13 is the test sub-task (formerly numbered 3.7, now grown per A4 item 3). The
two bodies of work are independent within the file and may be executed in either order.

**Sub-tasks:**
- [x] 3.1. Add a short preamble immediately above **Stage 1** naming the two forwarded values:
  `featureClass` (current value from `.spec-state.json`) and `taskProducesApplicationCode`
  (`true`/`false`, derived for *this task* from its declared outputs using the C0 allow-list).
  (FR-2, I1)
- [x] 3.2. Add the NFR-4 guard sentence once, in that preamble: where `featureClass` is `"code"`
  these two values change nothing — same stages, same order, same verdict formats, same labels, no
  additional user prompt. (FR-2.3, NFR-4)
- [x] 3.3. Extend the **Stage 2 (task-tester)** input bullets: pass both values; where `featureClass`
  is `"non-code"` **and** `taskProducesApplicationCode` is `false`, instruct the tester to apply its
  **no-code behaviour**. (FR-2.1)
- [x] 3.4. Extend the **Stage 3 (task-validator)** input bullets: pass both values; under the same
  condition instruct the validator to run in **artifact-conformance mode**, stating that the
  validator never selects the mode itself and the instruction is the only entry point; and append the
  task number to `classification.tasksValidatedUnderExemption` when the instruction is issued.
  (FR-2.1, FR-5.1, FR-3.3, DD-2)
- [x] 3.5. Extend the **Stages 4 & 5 (reviewers)** input bullets: pass `featureClass`; everything else
  about the invocation is unchanged — `mode: task`, both concurrent, both Opus. (FR-2)
- [x] 3.6. Confirm the stage order and the "reviews run only after validation passes" gate are
  untouched. (FR-2.4)
- [x] 3.7. **(A4 item 1(a) — the C0 correction.)** Replace C0's fenced block in
  `agents/orchestrator.md` with the A3/A4-corrected wording exactly as design C0 gives it: an **open**
  enumeration on **both** sides ("include, but are not limited to"); the application-code side naming
  the repository-root `CLAUDE.md` **with its criterion** (the project loads it into every agent's
  context as a behaviour-bearing contract); the non-code side naming the repository-root `README.md`
  **with its criterion** (nothing loads it into an agent's context — descriptive documentation); and a
  `PRECEDENCE` stanza stating that the enumeration settles every file it names on the side it names
  it, that AMB-1…AMB-5 apply only to a file the enumeration does not already settle and never
  override it, and that both lists stay open (absence from either list is evidence of nothing). Then
  update `CANONICAL_ALLOW_LIST` in `tests/test_orchestrator_feature_class.py` to match
  **byte-for-byte**. Leave the provenance sentence that follows the fence — `agents/orchestrator.md`
  is the normative home, the other four copies are verbatim replicas, and if a copy disagrees
  `agents/orchestrator.md` wins — in place and unchanged **here**; it belongs to the normative home
  only and is **not** part of what Tasks 6, 7 and 8 replicate. (FR-1.3, NFR-6, DD-5, A3-3, A4-1)
- [x] 3.8. **(A4 item 1(b).)** Add **AMB-5** — "`tasks.md` declares no tasks at all" → `"code"` — to
  the fail-safe trigger list, labelled `AMB-5` so tests and reviews can cite it, with the reason
  stated in the contract: the per-feature rule is a conjunction of two universals and is **vacuously
  true over zero tasks**, so an empty task list is the single input on which the rule would invert its
  own fail-safe direction; AMB-1 covers "a task declares no outputs" and says nothing about "there are
  no tasks". (FR-1.4, A3-4, R7)
- [x] 3.9. **(A4 item 1(c).)** Add the precedence pointer to the fail-safe section: the ambiguity
  triggers are **subordinate** to C0's enumeration and apply only to a file the fenced block does not
  already settle by name — **citing** the fenced `PRECEDENCE` clause rather than restating it, so no
  second normative copy can drift out of step with the replicated one. State the concrete
  consequence: the repository-root `CLAUDE.md` is application code and the repository-root `README.md`
  is a category-2 non-code artifact **by enumeration**, and AMB-3/AMB-4 never fire over either.
  (FR-1.4, NFR-6, A4-1)
- [x] 3.10. **(A4 item 1(d).)** Extend the `null`-is-unclassified consumer sentence in
  `## State File Management` so its consumer list also names the **C4 reclassification subsection**,
  alongside the per-task routing (C3), the task-tester, the task-validator, both reviewers and the
  feature-review gate (C5). The rule itself is unchanged: `null` is read exactly as an absent value
  and treated as `"code"`; it is never a third classification and is never forwarded to a consumer as
  if it were one. (FR-1.1, A3-1)
- [x] 3.11. **(A4 item 1(e).)** Add the absence-is-not-by-itself-a-legacy-signal clause to the same
  schema prose: the `"code"` default for an absent `featureClass` is a *reader's* default and is
  correct as such, but absence **also** means the classification gate has not yet run, and only the
  Feature Classification Gate's two-condition rule — absent **and** `phase` already `implementation`
  or beyond — decides whether absence is a genuinely pre-change state file. State explicitly that this
  sentence must never be cited to justify **skipping the gate** for a freshly scaffolded feature, and
  name `commands/sdd-feature.md` as the command that writes a state file with no `featureClass` key at
  all. (FR-1.1, FR-1.7, A3-5)
- [x] 3.12. **(A4 item 1(f).)** Add the legacy-branch **report** to the Feature Classification Gate:
  when the legacy branch fires, the orchestrator reports it to the user in one line — that the state
  file was read as genuinely pre-change, on **which two conditions**, and that the feature proceeds as
  `"code"`, unclassified. It is a **report, not a prompt**, so NFR-4's "no additional user prompt on
  the code path" is untouched; its purpose (R10) is to convert the one silent path through this gate
  into an audited one, the same audit surface a normal classification already has. (FR-1.5, FR-1.7,
  NFR-5, NFR-4, A3-2)
- [x] 3.13. Test (formerly sub-task 3.7; grown per A4 item 3): extend
  `tests/test_orchestrator_feature_class.py` so that at the end of this task it carries **all eight**
  of the following. Three already exist from Task 2 and are *verify-and-keep*; the rest are new or
  changed.
  1. **All five ambiguity triggers AMB-1…AMB-5**, AMB-5 by name. *Changed* — the existing assertion at
     `tests/test_orchestrator_feature_class.py:478–500` requires **at least four** triggers and lists
     four labels; tighten it to five.
  2. **The entry predicate keys on the recorded decision**, absent and `null` both unclassified.
     *Exists* (`test_gate_entry_predicate_keys_on_recorded_decision_not_key_presence`) — keep.
  3. **The legacy rule states both conditions.** *Exists*
     (`test_legacy_discriminator_requires_absence_and_phase_at_implementation_or_beyond`) — keep.
  4. **`/sdd-feature` named as the evidence** that absence alone is insufficient. *Exists*
     (`test_legacy_state_does_not_capture_a_freshly_scaffolded_feature`) — keep.
  5. **The legacy branch reports its determination.** *New.*
  6. **`CANONICAL_ALLOW_LIST` matches the corrected block.** *Changed* — the constant must now carry
     `CLAUDE.md` **and** `README.md`, each with its criterion, the open phrasing on both sides, and
     the `PRECEDENCE` clause.
  7. **The `PRECEDENCE` clause is present** and the ambiguity triggers are declared subordinate to
     the enumeration. *New (A4).*
  8. **The two schema-prose clauses** from sub-tasks 3.10 and 3.11 — the C4 entry in the
     `null`-consumer list, and the absence-is-not-a-legacy-signal qualifier. *New.*

  Plus the routing assertions this task already required: routing bullets naming `featureClass` inside
  the Stage 2, Stage 3 and Stages 4 & 5 regions; `taskProducesApplicationCode` inside the Stage 2 and
  Stage 3 regions; the artifact-conformance instruction and the `tasksValidatedUnderExemption` append
  stated in the Stage 3 region; the NFR-4 guard sentence present; and the stage sequence
  execute → test → validate → review still appearing in order. Run the full suite. (FR-11.2, FR-1.1,
  FR-1.3, FR-1.4, FR-1.5, FR-1.7, NFR-4, NFR-5, NFR-6)

**Superseded wording (A5) — do not restate these sub-tasks anywhere.** Task 3 is complete, passed all
five pipeline stages on the first attempt, and is **not** re-executed. Six of the twelve non-blocking
findings its code and security reviews raised are defects in *design* text Task 3 transcribed
faithfully, and **both reviewers said so explicitly** and recommended a design amendment rather than
an executor retry. Every correction below therefore lands in **Task 4**, which already declares both
of the files involved and still precedes Task 6, so the before-Task-6 ordering that A3, A4 and A5 all
rely on is preserved (sequencing constraint 5).

- **Sub-task 3.7** told the executor to write the A3/A4 fence: `README.md` named on the non-code side
  with its criterion stated as an **apposition**, and a `PRECEDENCE` clause subordinating
  **AMB-1…AMB-5** to the enumeration. Both are defective. The apposition **justifies** the naming
  rather than **gating** it (A5-2), so in a consumer project whose `CLAUDE.md` carries `@README.md` —
  and the fence ships to consumer projects through `install.sh`, where *"in this repository"*
  rebinds — a behaviour-bearing README is settled category 2 *by enumeration* and receives the
  tester's no-code behaviour and the validator's artifact-conformance mode on a criterion that is
  false. And subordinating the **feature-level** triggers AMB-1 and AMB-5 to a **file** enumeration
  disables AMB-5 (A5-1): a zero-task feature has no *file* the enumeration fails to settle, so the
  same amendment that added AMB-5 to close the vacuous-truth hole disabled it. The final form is a
  **bounded check** stated as a condition, plus an **asymmetric, rescoped** `PRECEDENCE` clause; it
  lands in **sub-task 4.9** with the byte-for-byte `CANONICAL_ALLOW_LIST` re-pin.
- **Sub-task 3.9's** concrete-consequence sentence states the `README.md` outcome
  **unconditionally**. It becomes conditional on the fence's own criterion, and the pointer is
  rescoped to the **file-classifying** triggers AMB-2…AMB-4 with AMB-1 and AMB-5 declared always
  applicable, in **sub-task 4.10**. The shipped pointer's "AMB-3 and AMB-4 never fire over either of
  them" was already correctly scoped and needs only the conditionality. (A5-1, A5-2)
- **Sub-task 3.4** stated that the task number is **appended** to
  `classification.tasksValidatedUnderExemption` **when** the artifact-conformance instruction is
  issued. A5-5 makes that a **write-ahead, duplicate-free set** — added *before* the instruction is
  issued, and only if not already present — in **sub-task 4.13**, because Stage 3 re-runs on both
  retry paths (so a twice-retried task recorded `[4, 4, 4]`) and append-*after* leaves a
  granted-but-unrecorded exemption if the window is interrupted. Sub-task 4.4's documentation and
  sub-task 4.8's assertion move with it.
- **Sub-task 3.1's** preamble names both forwarded values without scoping them per stage, which
  contradicts interface I1 and the stage bullets directly beneath it. A5-4 corrects the scoping in
  **sub-task 4.12**; the NFR-4 guard sentence from sub-task 3.2 is untouched and must remain present
  exactly once.
- **Sub-task 3.12's** legacy report states the condition without *"or beyond"*, so a feature resumed
  at `phase: "review"` or `"complete"` fires the branch correctly and then emits an audit line
  asserting a condition that did not hold — on the one branch of the gate that writes nothing to
  `.spec-state.json`, so that line is the whole audit record. A5-6 corrects it in **sub-task 4.14**;
  the line stays a **report, not a prompt** and stays fully literal.
- **Sub-task 3.13's** assertion inventory pins the A3/A4 text. Items 6 and 7 — `CANONICAL_ALLOW_LIST`
  matching the corrected block, and the `PRECEDENCE` clause subordinating the ambiguity triggers —
  both assert the over-broad A4 form and **will fail** against the final fence unless they move with
  it. They are re-pinned in **sub-task 4.8**, items 1–3, alongside the routing, exemption and
  legacy-report pins that items 4, 6 and 7 of that inventory re-anchor. Nothing Task 3 landed is
  deleted or weakened: every pin is **re-anchored, never dropped**.

**Requirements:** FR-1.1, FR-1.3, FR-1.4, FR-1.5, FR-1.7, FR-2, FR-2.1, FR-2.3, FR-2.4, FR-3.3,
FR-5.1, FR-11.2, NFR-4, NFR-5, NFR-6
**Design Reference:** C0; C1 items 1, 2, 7 and 10; C2; C3; interface I1; DD-2, DD-5; amendments
**A3** (changes A3-1…A3-5) and **A4** (change A4-1 and propagation items 1(a)–(f), 2, 3); risks R10,
R11
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (modify)

---

## Task 4: Orchestrator — reclassification fallback, non-code → code (C4) + the A5 contract corrections (C0, C1, C3)
- [x] 4. Add the monotonic reclassification subsection with its three triggers and its retry accounting, and land the A5 corrections to C0's fence, its fail-safe pointer, the per-task derivation, the routing preamble, the exemption record, the legacy-branch report and the gate's `**Inputs**` list.

**Description:** Add a new `####`-level subsection at the end of ``### `implementation` ``, after the
`On **fail**` bullet, headed `#### Reclassification: non-code → code (fallback, D2)`. Depends on
Tasks 1, 2 and 3 (it updates the state keys from Task 2 and reacts to the stages wired in Task 3).
Per A3 item 7 / A4 item 5, this subsection is a **consumer** of `featureClass` and must be written
consistently with the `null`-is-unclassified reading rule Task 3 extends to it (sub-task 4.7).

**This task grew materially with A5, and now carries two bodies of work.** **(i) C4**, the
reclassification subsection — sub-tasks 4.1–4.7, unchanged from the pre-A5 list. **(ii) The A5
contract re-edits** — sub-tasks 4.9–4.15, following the authoritative propagation block in
*design.md → Amendment A5 → What A5 requires of `tasks.md`*, item 1(a)–(g); follow it literally.
Because Task 3 shipped the A3/A4 form of the text A5 corrects, these are **re-edits of committed
text, not new work**, and their owner is this task. Sub-task **4.4 is amended** to match A5-5's
write-ahead set semantics, and sub-task **4.8 grows** by the eight-item assertion inventory of A5
item 2 on top of everything it already carried. Sub-tasks 4.1, 4.2, 4.3, 4.5, 4.6 and 4.7 are
**unaffected**. Size the task as seven contract re-edits plus the C4 subsection plus a substantially
larger test sub-task, rather than discovering it mid-execution.

**Every A5 edit here lands in one of six regions of `agents/orchestrator.md`** — the C0 fence, its
fail-safe precedence pointer, the legacy-branch report, the routing preamble, the Stage 3 bullet, and
the Feature Classification Gate's `**Inputs**` list — and **no frozen span lies in any of them**. The
six frozen spans (the `ready-to-merge` single-application-point sentence **together with its trailing
`(FR-10.1, NFR-1, NFR-8)` parenthetical**, the clear-`blocked:*`-before-set ordering, the
clear-**every**-recorded-label wording, the scaffold-push-only-on-first-scaffold scoping, *"You never
run `gh` or `git push` yourself"*, and *"github-agent is the only component in the fleet that runs
`gh` or `git push`"*) must be verified byte-identical to `HEAD` before and after, exactly as Task 3
did (A5 item 6). This task's edits move the repository copy of `agents/orchestrator.md` further ahead
of the unsynced `~/.claude` copy, which is the **`pending`** state the A2 carve-out exists for — not
`drift`, because no invariant instruction line changes and no heading is added. It **must not modify**
`tests/test_orchestrator_label_lifecycle.py` or `tests/test_sync_state_carve_out.py`, which belong to
Tasks 1 and 11 and must stay green (A5 item 7).

**Sub-task numbering.** 4.9–4.15 are inserted **above** 4.8, which keeps its number and stays this
task's last sub-task. Nothing is renumbered — `design.md`, `.spec-state.json` and this feature's PR
thread cite these numbers — so the ordinals here are deliberately non-monotonic while the test
sub-task remains last by position. A5 item 1 explicitly left the choice to the tasks-agent.

**Sub-tasks:**
- [x] 4.1. Specify the three triggers: **T1** the task-tester reports the task in fact produced
  application code; **T2** the task-validator returns FAIL citing application-code modification under
  artifact-conformance mode; **T3** the orchestrator itself sees an application-code path in the
  executor's changed-files summary. (FR-3, FR-4.5, FR-5.6)
- [x] 4.2. Specify the actions on any trigger: set `featureClass = "code"` and populate
  `classification.reclassification` with the triggering path(s), task number, trigger source and
  timestamp; report the reclassification to the user naming the file(s) and the task. (FR-3.1, NFR-5)
- [x] 4.3. Specify that the current task's **Stage 2 (test)** and **Stage 3 (validation)** re-run
  under the code path — tests required — before the task may be marked complete. (FR-3.2)
- [x] 4.4. Specify that `classification.tasksValidatedUnderExemption` is kept as written — a
  permanent record, not a live flag — and that when it is non-empty and the feature has been
  reclassified, the Feature Review Gate invocation must state that those tasks' outputs are reviewed
  under the code path. **Document the key's semantics, not merely its shape** (Task 2 security review,
  Low): what it records (the numbers of the tasks whose Stage 3 ran in artifact-conformance mode);
  **when** an entry is added — the task's number is **added, if not already present, immediately
  before** the orchestrator issues the artifact-conformance instruction (C3, sub-task 4.13), so the
  record is **write-ahead** and no interruption in that window can leave a granted-but-unrecorded
  exemption; that the key is a **duplicate-free set**, so a task whose Stage 3 re-runs on either
  retry path appears exactly **once** rather than repeatedly; that the keying stays on
  **instruction-issue**, which over-records deliberately — a task that *fails* validation under the
  exemption stays recorded, the direction FR-3.3's re-review requires; and that entries are **never
  removed or cleared**, not on reclassification and not at feature completion. (FR-3.3, NFR-5, A5-5)
- [x] 4.5. State monotonicity explicitly: once `featureClass` is `"code"` it is never set back to
  `"non-code"` for the remainder of the feature — not by a later artifact-only task, and not by a
  user override. (FR-3.4, FR-1.6)
- [x] 4.6. Settle retry accounting explicitly: T2 is a genuine validator FAIL and flows through the
  **existing** `On **fail**` branch unchanged (`retryCount += 1`, `blocked:validation`, executor
  re-run); T1 and T3 are caught before a validation verdict exists, re-run stages 2–3 within the same
  attempt, and do **not** increment `retryCount` and do **not** set a label. No new label is
  introduced on any path. (FR-3.2, FR-10.1, DD-8)
- [x] 4.7. **(A3 item 7 / A4 item 5.)** Keep C4 consistent with the `null`-is-unclassified reading
  rule: state in the subsection that it is a **consumer** of `featureClass` and obeys the schema
  prose's rule — a `null` or absent value means the feature is **unclassified** and is read exactly as
  an absent value, i.e. as `"code"`. State the two consequences plainly, so the rule cannot be
  inverted here: there is **no exemption to withdraw** from an unclassified feature, so no trigger
  reclassifies it; and this subsection **never writes `"non-code"`** — it only ever moves a value
  **to** `"code"`, never from `null` to `"non-code"` and never back. (FR-3, FR-3.1, FR-3.4)
- [x] 4.9. **(A5 item 1(a) — the fence's final form.)** Replace C0's fenced block in
  `agents/orchestrator.md` with its final form exactly as design C0 gives it after A5: category 2's
  `README.md` parenthetical stated as a **condition** pointing at the fence's own bounded check
  (`WHERE the PRECEDENCE CHECK below passes for it`), with the failure consequence named inside
  `PRECEDENCE`; the application-code side **unchanged**; and the `PRECEDENCE` clause replaced by its
  asymmetric, rescoped form — decided **before** the category tests, with a file named on the
  **application-code** side settled application code **unconditionally**; a file named on the
  **non-code** side settled non-code **only if** its CHECK is run and passes (the CHECK reads the
  repository-root `CLAUDE.md`, the files it imports and `.specs/steering/*.md`, and fails on an
  `@`-import, a session-start read instruction, or a designation of the file as a contract or
  standard — a mere mention is **not** a load — and fails if it was not run); a **failed or unrun
  check declared itself the project's designation**, so the file is **application code** and does
  **not** fall back to the category tests; **AMB-2, AMB-3 and AMB-4** declared **file-classifying**
  triggers, subordinate to the enumeration and never overriding a file it settles; **AMB-1 and
  AMB-5** declared **feature-level** triggers about missing declarations that name no file and
  **always apply**; and **both lists still open** (a file's absence from either list is evidence of
  nothing). Then **re-pin `CANONICAL_ALLOW_LIST`** in `tests/test_orchestrator_feature_class.py` to
  match **byte-for-byte**. Leave the provenance sentence that follows the fence in place and
  unchanged; it is **not** part of what Tasks 6, 7 and 8 replicate (DD-5). (FR-1.3, FR-1.4, NFR-6,
  DD-5, DD-17, A5-1, A5-2)
  **Hard ordering constraint: this sub-task must land before Task 6.** Tasks 6, 7 and 8 replicate the
  fence and Task 8 asserts all five copies are normalised-identical, so the fence's **final** form
  and its pinned constant must be in place first, or four copies of superseded wording ship and the
  identity assertion locks the wrong text in place (sequencing constraint 5).
- [x] 4.10. **(A5 item 1(b).)** Rescope the fail-safe precedence pointer in the Feature
  Classification Gate to the **file-classifying** triggers AMB-2…AMB-4; state that **AMB-1 and AMB-5
  are feature-level and always apply**, which is what keeps AMB-5 able to fire over a `tasks.md` with
  no tasks and therefore no unsettled file; and make the `README.md` consequence **conditional** on
  the fence's criterion. Keep it a **citation** of the fenced `PRECEDENCE` clause, never a
  restatement, so no second normative copy can drift out of step with the replicated one (NFR-6) —
  the shipped pointer's "AMB-3 and AMB-4 never fire over either of them" is already correctly scoped
  and needs only the conditionality. (FR-1.4, NFR-6, A5-1, A5-2)
- [x] 4.11. **(A5 item 1(c).)** Add the **at-least-one-output conjunct** to the per-task derivation of
  `taskProducesApplicationCode`: it is `false` **only when the task declares at least one output
  and** every declared output classifies non-code; a task declaring **no** outputs derives
  **`true`**. This is the per-task counterpart of AMB-1, closing one level down the same
  vacuous-truth hole AMB-5 closes at feature level — the per-feature rule carries the explicit
  *"every task declares at least one output"* conjunct and the per-task rule carried neither it nor
  AMB-1. State the fail-safe direction, not merely the arithmetic. (FR-2.1, FR-1.4, DD-18, A5-3)
- [x] 4.12. **(A5 item 1(d).)** Correct the routing preamble's scoping so it agrees with interface I1
  and the stage bullets beneath it: `featureClass` is forwarded to **Stages 2, 3, 4 and 5**;
  `taskProducesApplicationCode` to **Stages 2 and 3 only**; **Stage 1 receives neither** and is
  unchanged. Do **not** touch the NFR-4 guard sentence, which must remain present **exactly once**.
  (FR-2, FR-2.3, NFR-4, NFR-6, I1, A5-4)
- [x] 4.13. **(A5 item 1(e).)** Make the exemption record **write-ahead and set-valued** in the
  Stage 3 region: **before** issuing the artifact-conformance instruction, add this task's number to
  `classification.tasksValidatedUnderExemption` **if it is not already present**; the key is a
  **duplicate-free set**; entries are **never removed or cleared**; and the keying stays on
  **instruction-issue**. (FR-3.3, NFR-5, A5-5)
- [x] 4.14. **(A5 item 1(f).)** Correct the legacy-branch report template so the reported condition
  reads `phase` already `implementation` **or beyond**, matching the rule paragraph and the C2 schema
  clause it currently contradicts. Keep the line a **report, not a prompt** (NFR-4) and keep it
  **fully literal** — no interpolated path, username or state value; full literalness is a verified
  property worth keeping, and *"implementation or beyond"* is true whenever the branch fires.
  (FR-1.5, FR-1.7, NFR-4, NFR-5, A5-6)
- [x] 4.15. **(A5 item 1(g).)** Add the designation input C0's check requires to the Feature
  Classification Gate's `**Inputs**` list, as a fourth input: *(d) the repository-root `CLAUDE.md`
  and any file it imports, read **only** to run C0's `PRECEDENCE` **CHECK** — whether this project
  loads a file the enumeration names on its non-code side into an agent's context, or designates it a
  contract or standard.* State that it is the **same kind of input as (c)** — a source of the
  project's **designation**, which is what a declared output is classified *against*, never what the
  classification is derived *from* — and that it widens no other part of the classification. **Do not
  touch the *"never inspects a git diff"* sentence (FR-1.2); it must survive verbatim.** Without this
  input the fence names evidence the contract gives the classifier no authority to read. (FR-1.2,
  FR-1.3, FR-1.4, DD-17, A5-2)
- [x] 4.8. Test — **physically last, and deliberately still numbered 4.8** (4.9–4.15 were inserted
  above it rather than renumbering anything). Extend `tests/test_orchestrator_feature_class.py` with
  assertions that the reclassification subsection exists under its exact heading and sits inside the
  `implementation` section after the `On **fail**` bullet; that all three triggers are named; that
  monotonicity is stated; that re-running test + validation under the code path is stated; that
  `classification.reclassification` and `tasksValidatedUnderExemption` are referenced and the
  latter's **write-ahead add point** — the number is added **before** the artifact-conformance
  instruction is issued, and only **if it is not already present** — together with its
  **duplicate-free set** and never-cleared semantics are documented; that the
  T1/T3-do-not-increment-`retryCount` rule is stated; that the subsection states the `null`/absent-is-unclassified
  reading and that it never writes `"non-code"`; and that every `blocked:` label name appearing in the
  new region is drawn from the frozen five-name vocabulary.

  **Plus the eight-item inventory A5 item 2 adds** for the contract re-edits in sub-tasks 4.9–4.15.
  By the end of this task the module must assert:
  1. **`CANONICAL_ALLOW_LIST` matches the A5 fence** byte-for-byte. *Changed pin* —
     `test_allow_list_body_matches_the_canonical_block`.
  2. **The `PRECEDENCE` clause is asymmetric and correctly scoped**: the application-code side
     settles unconditionally, the non-code side only where its bounded check has been run and passes,
     with a failed or unrun check settling the file as application code, AMB-2…AMB-4 are subordinate,
     and AMB-1 and AMB-5 are declared unaffected. *Changed* —
     `test_allow_list_precedence_clause_subordinates_the_ambiguity_triggers` currently asserts the
     over-broad A4 form and **will fail** against the corrected fence unless it moves with it.
  3. **The non-code naming is conditional**, with the contrapositive present. *Changed* —
     `test_allow_list_enumeration_is_open_on_both_sides_and_names_claude_md_and_readme_md` pins the
     A4 apposition phrasing today.
  4. **The per-task derivation states the at-least-one-output conjunct** and the no-output → `true`
     direction. *Changed pin* — the regex at `tests/test_orchestrator_feature_class.py:1533–1539`,
     inside `test_preamble_declares_both_forwarded_values_above_stage_one`, pins the current sentence
     verbatim. Re-anchor it on the **property** (fail-safe direction plus the precondition), not on
     the sentence.
  5. **The preamble scopes forwarding per stage** — and the existing
     `test_stages_four_and_five_receive_feature_class_only` still passes, unchanged, as the negative
     half of the same fact.
  6. **The Stage 3 region states write-ahead ordering and set semantics.** *Changed — **rewritten**,
     not extended.* `test_stage_three_requests_artifact_conformance_and_records_the_exemption`
     (`:1617`) currently pins the literal `append this task's number to
     classification\.tasksValidatedUnderExemption` in a regex at `:1656`. That regex **will fail**
     against the corrected wording, so it must be **rewritten** — re-anchored on the two properties
     (the add happens *before* the instruction is issued, and the add is conditional on absence),
     not on the old sentence. This task goes red if it is merely extended.
  7. **The legacy report states `implementation` or beyond.** *Changed* — the regex inside
     `test_legacy_branch_reports_its_determination` (`:806`, assertion at `:846–851`) requires only
     `phase already implementation` while its own failure message claims the requirement is
     "`implementation` **or beyond**". Tighten the assertion to the full condition so assertion and
     message agree.
  8. **The gate's `**Inputs**` list names the designation-only input** required by C0's check, and
     the *"never inspects a git diff"* sentence is still present. *New assertion.* The existing
     input-list assertions in `tests/test_orchestrator_feature_class.py:430–448` remain green:
     sub-task 4.15 only adds an input.

  Every other assertion in the module is **verify-and-keep**: this task **deletes and weakens
  nothing**. Then verify the **six frozen spans** in `agents/orchestrator.md` are byte-identical to
  `HEAD` before and after, exactly as Task 3 did (`orchestrator_invariant_lines` /
  `ORCH_INVARIANT_PATTERNS`), and confirm `tests/test_orchestrator_label_lifecycle.py` and
  `tests/test_sync_state_carve_out.py` are still green and **not modified** by this task. Run the
  full suite; the pass count is monotonic across this feature. (FR-11.2, FR-10.1, FR-1.2, FR-1.3,
  FR-1.4, FR-1.5, FR-1.7, FR-2, FR-2.1, FR-3.3, FR-3.4, NFR-4, NFR-5, NFR-6)

**Requirements:** FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.7, FR-2, FR-2.1, FR-3, FR-3.1, FR-3.2,
FR-3.3, FR-3.4, FR-4.5, FR-5.6, FR-10.1, FR-11.2, NFR-4, NFR-5, NFR-6
**Design Reference:** C4; DD-8; risk R4; Flow C; amendment **A3** item 7 / **A4** item 5. Plus, per
**A5**: C0; C1 items 3, 7 and 10; C3; interface I1; DD-5, DD-17, DD-18; amendment **A5** (changes
A5-1…A5-6 and propagation items 1(a)–(g), 2, 5, 6, 7); sequencing constraint 5; risks R7, R11
**Files:** `agents/orchestrator.md` (modify), `tests/test_orchestrator_feature_class.py` (modify)

---

## Task 5: Orchestrator — Feature Review Gate wiring + `ready-to-merge` singleton regression (C5)
- [ ] 5. Pass `featureClass` and the non-code scope instruction to the feature-review invocation, add the Critical Rules line, and lock the single `ready-to-merge` application point with a test.

**Description:** Add exactly one bullet to the Feature Review Gate's "Pass each:" list and one line
to `## Critical Rules`, leaving the `**On PASS (both reviewers PASS)**` branch edited **in no way**.
Then add the regression module that makes any future second application point a test failure.
Depends on Tasks 1–4. This is the task where the FR-9 invariant is at greatest risk; treat the PASS
branch as read-only.

**Sub-tasks:**
- [ ] 5.1. Add one bullet to the Feature Review Gate "Pass each:" list: pass `featureClass`; where it
  is `"non-code"`, add the **non-code review scope** instruction (the `feature`-mode diff will be
  empty or contain only non-code artifacts, so the reviewer resolves and reviews the non-code review
  scope defined in its own contract and must return exactly one of `PASS`/`FAIL`); and where
  `classification.tasksValidatedUnderExemption` is non-empty **and** the feature was reclassified,
  additionally state that those tasks' outputs are reviewed under the code path. (FR-2.2, FR-3.3)
- [ ] 5.2. Confirm the invocation stays concurrent and Opus-pinned, and that the `On PASS` branch
  retains, unedited: the `blocked:feature-review` clear preceding the single
  `label set ready-to-merge`, the "This is the **only** place `ready-to-merge` is ever applied"
  sentence, the draft-on-blocking-finding rule, and the human merge gate. Add no class-conditional
  wording anywhere in that branch. (FR-2.2, FR-9, FR-9.1, FR-9.2, FR-9.3, FR-9.4, NFR-1)
- [ ] 5.3. Add one line to `## Critical Rules`, adjacent to the existing `ready-to-merge` rule:
  never treat `featureClass: "non-code"` as an exemption from any gate — it changes which artifacts
  the tester, validator and reviewers examine, never whether they run, and never what a PASS
  requires. (FR-9.1, NFR-1, DD-10)
- [ ] 5.4. Test: create `tests/test_orchestrator_ready_to_merge_singleton.py` asserting: exactly
  **one** `ready-to-merge` *set* operation in the whole body (regex over
  `op:\s*set[^}]*ready-to-merge` plus prose `set … ready-to-merge` forms, de-duplicated by offset);
  its offset lies inside the Feature Review Gate `On PASS (both reviewers PASS)` region; the "only
  place `ready-to-merge` is ever applied" sentence survives; **no** `ready-to-merge` token appears
  anywhere in the classification-gate or reclassification regions; and every `blocked:` label name in
  the file is drawn from the frozen five-name vocabulary (`blocked:validation`,
  `blocked:code-review`, `blocked:security-review`, `blocked:feature-review`, alongside
  `ready-to-merge`). Additionally extend `tests/test_orchestrator_feature_class.py` with an assertion
  that the Feature Review Gate region names `featureClass` and the non-code review scope instruction.
  Run the full suite, including `tests/test_orchestrator_label_lifecycle.py`, and confirm every
  pre-existing assertion in it still passes. (FR-11.1, FR-11.2, FR-11.6, FR-9.1, FR-10.1, AC-7)

**Requirements:** FR-2, FR-2.2, FR-3.3, FR-9, FR-9.1, FR-9.2, FR-9.3, FR-9.4, FR-10.1, FR-11.1,
FR-11.2, FR-11.6, NFR-1, NFR-6
**Design Reference:** C5; C12 (`test_orchestrator_ready_to_merge_singleton`); DD-10; Flows A and D
**Files:** `agents/orchestrator.md` (modify),
`tests/test_orchestrator_ready_to_merge_singleton.py` (new),
`tests/test_orchestrator_feature_class.py` (modify)

---

## Task 6: `agents/task-tester.md` — no-code behaviour (C6, I2)
- [ ] 6. Define what the task-tester does when a task produces no application code, and forbid vacuous tests.

**Description:** Add a new `##`-level section between `## Testing Rules` and `## Completion Summary`
headed `## No-Code Behaviour (tasks that produce no application code)`, carrying the C0 allow-list
block verbatim, plus one added line in `## Rules`. Independent of Task 5, but the C0 block must be
copied byte-for-byte from `agents/orchestrator.md` **as it stands after Task 4** — the fence's final,
A5-corrected form — so run it after **Task 4**, never after Task 2 or Task 3 alone (A5 item 4).

**Sub-tasks:**
- [ ] 6.1. Specify entry: the behaviour applies when the orchestrator states
  `featureClass: non-code` and `taskProducesApplicationCode: false`. Replicate the C0 block verbatim
  under its exact heading, copying it from `agents/orchestrator.md` **after Task 4**. Replicate the
  **heading and the fenced body only**: do **not** copy the provenance sentence that follows the
  fence in `agents/orchestrator.md` (naming that file the normative home and the winning copy when
  copies disagree) or any of the surrounding prose — a replica that claims to be the winning copy
  inverts DD-5. (FR-4, FR-2.1, DD-5)
- [ ] 6.2. Specify the prohibition with its forms enumerated: no vacuous or placeholder tests written
  to satisfy a tests-exist expectation — an assertion that cannot fail; a test asserting only that a
  file exists when the requirement is about its content; a test asserting a constant; a test with no
  assertion. State the reason: a vacuous test is worse than no test, because it converts a known gap
  into a false signal. (FR-4.1)
- [ ] 6.3. Specify the preferred path: where a produced artifact is machine-checkable, **write the
  check** in the project's conventional test directory following the project's existing test
  patterns, with the enumerated examples — a structural or content lint over a markdown contract; a
  schema or frontmatter check; a link/path-resolution check; a cross-file consistency check between
  two copies of a document. This must appear **before** the fallback in the section. (FR-4.2)
- [ ] 6.4. Specify the fallback: only if no meaningful machine check is feasible, emit the
  **"no applicable tests" completion block** in the I2 shape — retaining the existing
  `## Tester Summary: Task <N>` header, with `### Result: no applicable tests`,
  `### Artifacts Produced` (each artifact, the requirement it satisfies, and why no automated check
  is feasible), `### Machine Checks Written`, `### Existing Tests Run`, and `### Issues Found`. State
  that an empty or improvised summary is not an acceptable substitute. (FR-4.3, I2)
- [ ] 6.5. Specify that in **all** cases the tester runs the project's existing tests in the affected
  area and reports regressions, exactly as today. (FR-4.4)
- [ ] 6.6. Specify escalation: if the task in fact produced application code, report that fact to the
  orchestrator naming the path(s) — which triggers reclassification — and write tests for that code
  normally; do not apply the no-code behaviour to it. (FR-4.5)
- [ ] 6.7. Add the `## Rules` line: never write a placeholder or vacuous test to satisfy a
  tests-exist expectation; emit the "no applicable tests" block instead. Confirm the tester's
  never-modify-implementation rule is unchanged. (FR-4.1, NFR-9)
- [ ] 6.8. Test: create `tests/test_tester_no_code_behaviour.py` asserting: the section heading is
  present with the specified placement; the vacuous/placeholder prohibition appears with its
  enumerated forms; the machine-checkable preference precedes the fallback (offset ordering); the
  "no applicable tests" block is specified and names artifact + requirement + why-no-check; the
  run-existing-tests-in-all-cases rule survives; the FR-4.5 escalation is present; the new `## Rules`
  line is present; and the frontmatter `tools:` list is unchanged from the pre-change set. Run the
  full suite. (FR-11.1, FR-11.4, NFR-3, NFR-6)

**Requirements:** FR-4, FR-4.1, FR-4.2, FR-4.3, FR-4.4, FR-4.5, FR-2.1, FR-11.1, FR-11.4, NFR-3,
NFR-6, NFR-9
**Design Reference:** C6; interface I2; DD-5; amendment **A5** propagation item 4
**Files:** `agents/task-tester.md` (modify), `tests/test_tester_no_code_behaviour.py` (new)

---

## Task 7: `agents/task-validator.md` — artifact-conformance mode (C7, I3)
- [ ] 7. Add artifact-conformance mode, entered only on the orchestrator's instruction, with its verdict block — deleting no existing check.

**Description:** Three edits to `agents/task-validator.md`: qualify `### 2. Test Coverage` as
*(code mode)* with a conditional lead-in and add a sibling `### 2A. Artifact Conformance`; add a new
`## Artifact-Conformance Mode` section between `## Validation Checklist` and `## Verdict`, carrying
the C0 block verbatim; and add the I3 verdict variant to `## Verdict`. The three existing
`### 2. Test Coverage` checkboxes are **not deleted**, so the code path reads identically to today.
Run after **Task 4**, which is the source of the C0 fence's final, A5-corrected form; the
instruction that enters the mode comes from Task 3 (sub-task 3.4), with its write-ahead correction
in Task 4 (sub-task 4.13).

**Sub-tasks:**
- [ ] 7.1. Rename the heading to `### 2. Test Coverage  *(code mode)*` and add the lead-in sentence:
  in artifact-conformance mode this section is replaced by §2A below; in all other cases it applies
  unchanged. Leave all three existing checkboxes in place. (FR-5.4, NFR-4)
- [ ] 7.2. Add the sibling subsection
  `### 2A. Artifact Conformance  *(artifact-conformance mode only)*` in the checklist. (FR-5, FR-5.4)
- [ ] 7.3. Add the `## Artifact-Conformance Mode` section stating instruction-only entry in as many
  words — *never self-selected by the validator because a diff looked empty* — and carrying the C0
  block verbatim, copied from `agents/orchestrator.md` **after Task 4**. Replicate the **heading and
  the fenced body only**: do **not** copy the provenance sentence naming `agents/orchestrator.md` as
  the normative home and winning copy, which belongs to that file alone (copying it into a replica
  inverts DD-5). (FR-5.1, DD-2, DD-5)
- [ ] 7.4. Specify mapping: map every cited requirement to at least one **named produced artifact** —
  a file path, or an entry in `.specs/features/<feature-name>/vault/.write-log.jsonl` identified by
  its `operation` + `target` (and `section` where present) — and **read** it. A requirement with no
  mapped artifact is a FAIL. (FR-5.2, I4)
- [ ] 7.5. Specify substance: each mapped artifact exists, is non-empty, and substantively states or
  delivers what the cited requirement demands; a placeholder, stub, TODO-only or heading-only
  artifact is a **FAIL**. For a changelog-mapped requirement, `target`, `operation` and `intent` must
  be consistent with the requirement — and the validator reads the changelog, never the vault note.
  (FR-5.3, NFR-8)
- [ ] 7.6. Specify that in this mode the absence of unit tests is **not** a failure, replacing the
  unconditional "at least one test exists for this requirement" check **for this mode only**; and
  that machine checks written under FR-4.2 are run with Bash, with any failure a FAIL. (FR-5.4,
  FR-5.5)
- [ ] 7.7. Specify code detection: if any file modified by this task is application code per the
  allow-list, **refuse the exemption**, return `FAIL`, and report the offending path(s) so the
  orchestrator reclassifies — never a silent switch to code-mode validation, because the orchestrator
  owns the classification. (FR-5.6, FR-3)
- [ ] 7.8. Specify the retained checks (§3 Scope Check and §4 Quality Check remain fully active: no
  scope creep, `.specs/steering/tech.md` conventions respected, no leftover TODOs) and cite the
  existing all-or-nothing "NEVER partially pass" rule, leaving that rule's own text untouched.
  (FR-5.7, FR-5.9)
- [ ] 7.9. Add the I3 verdict variant to `## Verdict` as an additional labelled block: the
  `## Validator Verdict: Task <N>` header and `### Result:` line keep their exact existing shape; a
  `### Mode: artifact-conformance` line is emitted **only** in this mode; per-requirement lines carry
  artifact + substantive + tests-n/a (or the machine check run); plus `### Artifacts Reviewed` and
  `### Notes`, with the FAIL variant in the same shape. The existing PASS and FAIL blocks are
  unchanged, and no `### Mode:` line is added to the code path. (FR-5.8, NFR-4, DD-4)
- [ ] 7.10. Test: create `tests/test_validator_artifact_conformance.py` asserting: the
  `## Artifact-Conformance Mode` heading is present; instruction-only entry is asserted both by the
  "never self-selected" phrasing **and** by the absence of any self-entry condition; the
  tests-absence-is-not-a-failure statement is scoped to the mode; placeholder/stub/TODO artifact →
  FAIL; application-code detection → FAIL plus reported path; the literal `.write-log.jsonl` path is
  present; the scope and quality checks are still referenced as active; the all-or-nothing rule is
  still present; the original `### 2. Test Coverage` checkboxes are still present (nothing deleted);
  the `### Mode: artifact-conformance` line appears only in the artifact-conformance verdict variant;
  and the frontmatter `tools:` list is unchanged. Run the full suite. (FR-11.1, FR-11.3, NFR-3,
  NFR-4, NFR-6)

**Requirements:** FR-5, FR-5.1, FR-5.2, FR-5.3, FR-5.4, FR-5.5, FR-5.6, FR-5.7, FR-5.8, FR-5.9,
FR-11.1, FR-11.3, NFR-3, NFR-4, NFR-6, NFR-7, NFR-8, NFR-9
**Design Reference:** C7; interfaces I3, I4; DD-2, DD-4, DD-5; amendment **A5** propagation item 4
**Files:** `agents/task-validator.md` (modify), `tests/test_validator_artifact_conformance.py` (new)

---

## Task 8: Both reviewers — shared non-code review scope + finding classes (C8, C9, I5)
- [ ] 8. Give `code-reviewer` and `security-reviewer` a verbatim-identical non-code review scope section and their own finding-class lists, so an empty or docs-only diff yields a real PASS or FAIL.

**Description:** Insert the same `## Non-Code Review Scope (empty or non-code diff)` section into
both reviewer files, immediately after `## On Invocation` and before `## What to Hunt For`, with
verbatim-identical text (asserted by test) and the C0 block verbatim; add a
`### Non-code scope (FR-7)` subsection to the code-reviewer's `## What to Hunt For` and a
`### Non-code scope (FR-8)` subsection to the security-reviewer's; add one `## Rules` bullet to each;
and extend the PASS/FAIL blocks with the I5 additions. Run after Tasks 4, 6 and 7 — this task's test
module also asserts that all five copies of the C0 block are identical **in the fence's final,
A5-corrected form**, which is only possible once they all exist and once Task 4 sub-task 4.9 has
landed that form. This task also writes the **A5 form of the FR-6.4 attribution rule** into both
contracts and pins it in its test module, so the rule must be settled in `design.md` first — it is
(A5-7, sequencing constraint 6). Neither reviewer gains a tool or a write target.

**Sub-tasks:**
- [ ] 8.1. In both files, add the shared section with identical text specifying the resolution order:
  establish the existing diff first (`git diff` for `task` mode, `git diff <base>...HEAD` for
  `feature` mode); partition the changed paths with the C0 allow-list; if the diff contains **one or
  more application-code paths**, review it exactly as today and stop — the non-code scope does not
  apply; if the diff is empty **or** contains only non-code artifacts, resolve and review the
  non-code review scope. State that the orchestrator's prompt may confirm the situation but the
  reviewer does not wait for it. (FR-6, FR-6.2, DD-2)
- [ ] 8.2. Define the scope as the union of (a) the feature's spec artifacts (`requirements.md`,
  `design.md`, `tasks.md`, and `scope.md` where present, under `.specs/features/<feature-name>/`),
  (b) every non-code file in the diff for the reviewer's mode, and (c) the vault changelog entries at
  `.specs/features/<feature-name>/vault/.write-log.jsonl`. (FR-6.1)
- [ ] 8.3. Specify changelog reading: read the JSON-lines changelog itself with `Read` (`operation`,
  `target`, `intent`, optional `section`/`bytes`); **never** open the vault note named by `target`;
  the in-repo changelog is the entire reviewable surface; a needed vault fact means halting with
  `VAULT REQUEST: <need>` for the orchestrator to fulfil through vault-reader. (FR-6.8, NFR-8)
- [ ] 8.4. Specify the mandatory verdict: exactly one of `PASS` or `FAIL`; a hedge, an abstention, an
  "N/A", a "nothing to review", or a verdict with no result line is **not a permitted outcome** —
  forbidden by name. (FR-6.3, AC-5)
- [ ] 8.5. Specify the empty-scope FAIL as a single **Critical** finding ("the feature produced no
  reviewable output"), reusing the existing severity rule and FAIL block rather than a new verdict
  kind; and state, in its **A5** form, the attribution rule that makes the emptiness test able to
  fire at all — **structurally, by location**: everything under the feature's own
  `.specs/features/<feature-name>/` directory is the plan and is never counted as output,
  **neither when read from disk under scope item (a) nor when it appears as a changed file
  under scope item (b)** — with exactly **two** exceptions. **Exception 1:** the vault changelog at
  `.../vault/.write-log.jsonl`, which is scope item (c) and **is** counted. **Exception 2:** a file
  inside that directory that a task **both declared and produced** — it is a changed file in the
  diff for the reviewer's mode **and** some task in `tasks.md` declares it in that task's
  `**Files:**` field **as a file that task creates or modifies** (a file the field names only as
  one the task *reads* is not a declaration); or, in `task` mode, the executor reported writing
  it; both limbs are required, and both
  are evaluable in either mode because `tasks.md` is scope item (a) and is always read. Any
  **other** artifact counts as output **only** when it appears as a changed file in the diff for
  the reviewer's mode or the executor reported writing it; a `**Files:**` declaration alone does
  **not** promote an artifact to output outside the feature's directory. Item (a) is review
  context; items (b) and (c) less the plan, so defined, are the counted output. **State it by
  location, not as a list of file names** — a list is wrong the next time the scaffold changes, and
  this text is pinned in two contracts and one test module. Replicate the rule bullets only; the
  *why-by-location*, *Authority* and *`**Files:**`* paragraphs in design C8/C9 §5 are design-side
  rationale and are not part of the contract text, and neither is the *What Task 8 replicates*
  paragraph itself. (FR-6.4, AC-4, DD-3, A5-7)
- [ ] 8.6. Specify that the `Scope Reviewed` section enumerates what was actually inspected, listing
  each vault changelog entry **by target and operation**; that the severity model is unchanged
  (Critical/High block, Medium/Low report only); and that resolving the scope uses only the existing
  `Read`/`Glob`/`Grep`/`Bash` tools, both reviewers remaining read-only with no new tool and no new
  write target. Replicate the C0 block verbatim from `agents/orchestrator.md` **after Task 4** —
  **heading and fenced body only**, never the provenance sentence naming `agents/orchestrator.md` as
  the normative home and winning copy, whose replication would invert DD-5. (FR-6.5, FR-6.6, FR-6.7,
  NFR-3, NFR-9, DD-5)
- [ ] 8.7. Extend both verdict blocks per I5: a
  `### Scope Resolution: non-code (diff empty or non-code artifacts only)` line emitted **only** when
  the non-code scope was resolved, plus the enumerated `Scope Reviewed`. The existing headers,
  `— PASS`/`— FAIL` suffixes and severity sections are unchanged, and no scope-resolution line is
  added to the code path. (FR-6.3, FR-6.5, NFR-4, DD-4)
- [ ] 8.8. Add `### Non-code scope (FR-7)` to `agents/code-reviewer.md`'s `## What to Hunt For`:
  internal contradiction / unfollowable instruction; stale or dangling references (broken paths, dead
  links, non-existent requirement or task IDs, renamed or removed artifacts); duplication, divergence
  and incompleteness — including two synchronised copies of a document where both are in scope,
  subject to the NFR-10 pending-sync allowance (a repository copy legitimately ahead of an unsynced
  installed copy is **not** a finding; an installed copy that *contradicts* the authoritative
  repository copy is) — plus placeholders and unresolved TODOs; vault-update coherence (each recorded
  write traceable to a requirement, `target`/`operation`/`intent` consistent with the stated intent).
  Add the `## Rules` bullet requiring a concrete failure scenario for every blocking non-code
  finding — the reader or downstream consumer misled and the wrong outcome that follows — and leave
  the existing "do not re-litigate requirement conformance" rule intact, citing it from the new
  section. (FR-7, FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.5, NFR-10, R8)
- [ ] 8.9. Add `### Non-code scope (FR-8)` to `agents/security-reviewer.md`'s `## What to Hunt For`:
  committed credential material in prose, reported as **type + `path:line` with the value redacted**,
  never reproduced (for a changelog entry, the entry's `target` plus its line number in the
  changelog); sensitive disclosure (internal hostnames, endpoints, account identifiers, PII,
  infrastructure detail); unsafe documented instructions, with a documented unsafe default a finding
  in its own right; vault-write exposure (changelog entries placing sensitive material into the
  vault, or whose `target` resolves outside the declared vault path). Add the `## Rules` bullet
  requiring a concrete attack or exposure scenario for every blocking finding. (FR-8, FR-8.1, FR-8.2,
  FR-8.3, FR-8.4, FR-8.5, NFR-7)
- [ ] 8.10. Test: create `tests/test_reviewers_non_code_scope.py`, parameterised over both reviewer
  paths, asserting for each file: the `## Non-Code Review Scope` heading with the specified
  placement; all three scope components; the literal path
  `.specs/features/<feature-name>/vault/.write-log.jsonl`; the diff-first-then-fallback resolution
  order; the mandatory `PASS`/`FAIL` with hedge / N-A / nothing-to-review explicitly forbidden; the
  empty-scope FAIL and the attribution rule **in its A5 form** — the exclusion stated
  **structurally, by location** (everything under `.specs/features/<feature-name>/`, both when read
  from disk under (a) and when it appears as a changed file under (b)), with exactly the **two**
  exceptions (the vault changelog; and a file a task **both** declared in its `**Files:**` field as
  one it creates or modifies **and** produced), and with a `**Files:**` declaration alone asserted
  **not** to promote any artifact to output outside the feature's directory; a "never read the vault
  note" statement plus the `VAULT REQUEST` escalation; the severity model restated unchanged; and the
  frontmatter `tools:` list unchanged from the pre-change set. **Assert the A5 form, never the pre-A5
  one** — pinning the pre-A5 wording would put the defective rule into two agent contracts plus a
  green test guarding a rule that cannot fire. Plus a cross-file assertion that the shared section is
  normalised-identical in both reviewers, each reviewer's own finding-class subsection asserted
  separately, and `test_allow_list_blocks_identical` asserting the C0 block — in its **final
  A5-corrected form, as it stands in `agents/orchestrator.md` after Task 4** — is
  normalised-identical across all five agent files (`orchestrator`, `task-tester`, `task-validator`,
  `code-reviewer`, `security-reviewer`). Run the full suite. (FR-11.1, FR-11.5, NFR-3, NFR-6, NFR-8,
  R1)

**Requirements:** FR-6, FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5, FR-6.6, FR-6.7, FR-6.8, FR-7,
FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.5, FR-8, FR-8.1, FR-8.2, FR-8.3, FR-8.4, FR-8.5, FR-9.2,
FR-11.1, FR-11.5, NFR-3, NFR-4, NFR-6, NFR-7, NFR-8, NFR-9, NFR-10
**Design Reference:** C8, C9; interfaces I4, I5; DD-2, DD-3, DD-4, DD-5; risks R1, R5, R8; Flows A,
B, D; amendment **A5** (change A5-7, propagation items 3 and 4, sequencing constraint 6)
**Files:** `agents/code-reviewer.md` (modify), `agents/security-reviewer.md` (modify),
`tests/test_reviewers_non_code_scope.py` (new)

---

## Task 9: CI review-gate lock test (C12 / FR-10, NFR-2)
- [ ] 9. Add a read-only regression module asserting `ci-templates/workflows/sdd-review-gate.yml` still enforces the gate and carries no bypass.

**Description:** Create `tests/test_review_gate_untouched.py`, which reads the CI template and locks
its semantics so no future change to this track can weaken server-side enforcement. The workflow file
itself is **not modified by this task or any other** — the module only reads it. Independent of Tasks
1–8; sequenced here because the invariant it locks is the one the whole feature must preserve.

**Sub-tasks:**
- [ ] 9.1. Assert the gate conditions survive: `"ready-to-merge" in labels` is present;
  `startswith("blocked:")` is present; both `sys.exit(1)` failure branches are present; the
  `github.event_name == 'pull_request'` guard is present; and `permissions:` / `contents: read` are
  unchanged. (FR-11.7, NFR-2)
- [ ] 9.2. Assert **no** token matching
  `(?i)(bypass|exempt|escape[- ]?hatch|override|skip[-_ ]?gate|non-?code|featureclass)` appears
  anywhere in the file, and that every label-shaped literal in it is drawn from the frozen five-name
  vocabulary. (FR-10, FR-10.1, FR-10.2)
- [ ] 9.3. Test: run the new module, run the full suite, and confirm
  `git diff main...HEAD -- ci-templates/ .github/ hooks/ install.sh` is empty — no CI template, no
  workflow, no hook and no installer change anywhere in this feature's diff. (FR-11.7, FR-12.1,
  NFR-2, AC-6)

**Requirements:** FR-10, FR-10.1, FR-10.2, FR-11, FR-11.1, FR-11.7, NFR-1, NFR-2, NFR-6
**Design Reference:** C12 (`test_review_gate_untouched`); AC-6
**Files:** `tests/test_review_gate_untouched.py` (new). Reads, and does **not** modify,
`ci-templates/workflows/sdd-review-gate.yml`.

---

## Task 10: Documentation — repository `CLAUDE.md` + `README.md` (C11)
- [ ] 10. Describe the classification step and the non-code track in the repository-root `CLAUDE.md` and the README, and assert the new content.

**Description:** Update the repository-root `CLAUDE.md` phase-gates section and the README's
pipeline description. **The repository copy only** — no pipeline stage writes to
`~/.claude/CLAUDE.md` or to any other path under `~/.claude/`; the operator syncs the global copy by
running `./install.sh` after merge. Done last, after the behaviour it describes exists. Depends on
Task 1 (the byte-identity carve-out) and on Tasks 2–8 for accuracy. All prose in English (NFR-11).

**Sub-tasks:**
- [ ] 10.1. In `CLAUDE.md` `### Phase Gates`, change the phase line to
  `Requirements → Design → Tasks → [Consistency Check] → [Classification] → Implementation → [Feature Review] → Complete`
  and add a paragraph stating: classification is explicit and recorded in `.spec-state.json` under
  `featureClass`; a `non-code` feature runs the same five stages, with the validator in
  artifact-conformance mode (tests optional, a placeholder artifact still FAILs) and both reviewers
  reviewing the spec artifacts, the committed docs and the vault changelog; **`ready-to-merge` still
  requires a real whole-feature review PASS and there is no bypass**. (FR-12)
- [ ] 10.2. State in that paragraph that a non-code feature which turns out to touch application code
  falls back to the full code path, with the exemption withdrawn. (FR-12.2)
- [ ] 10.3. Hold the load-bearing constraint: the edit must **not** alter the three lines
  `github_agent_lines()` extracts from `### Agent Ownership` — the `- github-agent` bullet, the "only
  component that runs `gh`/`git push`" line, and the "No agent modifies another agent's artifact"
  invariant — because `test_two_claude_ownership_lines_consistent` compares them strictly across both
  copies and is **not** carved out. Rename no existing heading (a rename false-FAILs the Task-1
  discriminator, limit L2). Write nothing under `~/.claude/`. (FR-12.1, NFR-10, DD-7)
- [ ] 10.4. In `README.md` `### Review the workflow`, insert a classification step between the
  current items 4 (consistency check) and 5 (implementation), renumbering the list, and extend the
  implementation item to note that for a `non-code` feature the validator runs artifact-conformance
  and the reviewers review the resolved non-code scope. (FR-13)
- [ ] 10.5. Add one sentence to the README stating that a non-code feature reaches `ready-to-merge`
  through the same audited path as a code feature and that no bypass label exists. Leave the
  `## GitHub integration & CI enforcement` label vocabulary untouched. (FR-13.1, FR-10.1)
- [ ] 10.6. Test: create `tests/test_docs_non_code_track.py` asserting — **reading only the
  repository copies, never anything under `~/.claude/`** — that repo `CLAUDE.md` names
  `featureClass`, carries the classification step in the phase-gate line, describes the
  artifact-conformance/tests-optional behaviour and the reviewers' non-code scope, restates that
  `ready-to-merge` still requires a real whole-feature review PASS, and states the
  fallback-to-code-path rule; and that the README describes the classification step and the non-code
  track in its pipeline description and states that no bypass label exists. Then run the full suite —
  including `tests/test_docs_updates.py` — and confirm it passes with the repository copy ahead of
  the unsynced global copy, and that `git diff` contains no write under `~/.claude/`. (FR-11.1,
  FR-12, FR-12.1, FR-12.2, FR-13, FR-13.1, NFR-10, NFR-11, AC-10)

**Requirements:** FR-12, FR-12.1, FR-12.2, FR-13, FR-13.1, FR-10.1, FR-11.1, NFR-6, NFR-10, NFR-11
**Design Reference:** C11(a), C11(b); DD-7, DD-9; A1-resolution limits L1–L4
**Files:** `CLAUDE.md` (repository root, modify), `README.md` (modify),
`tests/test_docs_non_code_track.py` (new)

---

## Task 11: F3 remediation — bound the drift message, harden the sync-state discriminator
- [ ] 11. Close the four non-blocking findings the Task 1 code and security reviews left against the byte-identity carve-out, without weakening its drift detection.

**Description:** Task 1 passed all five stages, and both reviewers returned **PASS** with
non-blocking findings. Four of those were promoted to follow-up **F3** and are remediated here. The
primary one is a **security** finding (Medium): the drift failure message quotes every global-only ATX
heading **verbatim and unbounded**, and `install.sh`'s append mode preserves an operator's personal
sections in their global `CLAUDE.md` — so a private section title would be enumerated into text this
pipeline transcribes **verbatim into public PR comments**. The other three are correctness hardening
of the same helper. This task edits **only Task 1's artifacts** and adds no new assertion class;
FR-11.8's "no change beyond that to either module's scope" still binds, so every edit stays inside the
sync-state helper, the two reworked assertions, and the discriminator's own test module. The carve-out
stays **closed at two**. Depends on Task 1 only, and **must land before the whole-feature review**.

**Sub-tasks:**
- [ ] 11.1. **Bound the quotation of global-only headings (security, Medium — the primary fix).** In
  `claude_sync_state()` (`tests/test_docs_updates.py`) and `orchestrator_sync_state()`
  (`tests/test_orchestrator_label_lifecycle.py`), stop reproducing private section titles in the drift
  output: report the **count** of global-only headings and cap how many, if any, are named, eliding or
  summarising the remainder rather than enumerating them all. The message must remain
  **diagnostically useful** — it must still say which drift rule fired (invariant divergence vs
  heading provenance), how many headings are implicated, and how the operator resolves it
  (`./install.sh`, post-merge) — so a genuine drift report stays actionable without disclosing the
  operator's personal section titles. Invariant-divergence reasons, which quote text the *repository*
  copy itself carries, are unaffected and keep naming the diverging key. (FR-11.8, NFR-10, and NFR-7
  by the same "report the fact, not the content" principle it states for secrets in reviewed
  documents, applied here to test-failure text this pipeline transcribes into public PR comments.)
- [ ] 11.2. **Derive the verdict from a locally-collected list (code review, Medium).** Both helpers
  currently end `return "drift" if reasons else "pending"`, where `reasons` is the **caller's**
  optional out-param — so a caller passing a reused, already non-empty list gets a spurious `drift`.
  Collect drift signals into a list local to the helper, decide the verdict from that local list, and
  extend the caller's `reasons` from it when one is passed. The `reasons=None` default, the parameter
  order and the message content contract are all preserved. (FR-11.8, FR-11.1)
- [ ] 11.3. **Pin `ORCH_INVARIANT_PATTERNS` with `assertEqual` (code review, Medium).** In
  `tests/test_sync_state_carve_out.py`,
  `test_orchestrator_invariant_set_covers_the_four_named_classes` asserts only that the four named
  classes are a **subset** of the pattern keys, so the orchestrator invariant set can silently grow —
  which would make every pending window read as drift and invert amendment A2, with the whole suite
  still green. Add an `assertEqual` over the full key set of `ORCH_INVARIANT_PATTERNS`, mirroring the
  existing `test_claude_invariant_set_is_not_extended_with_new_feature_prose`, so **DD-7 is
  mechanically enforced for A2 exactly as it already is for A1**. Keep the existing subset assertion,
  which carries FR-11.8(A2)'s four-named-classes requirement. (FR-11.8, NFR-10, DD-7)
- [ ] 11.4. **Widen the global-copy read's exception clause (code review, Low).** Both reworked
  assertions read the global copy with `read_text(encoding="utf-8")` guarded by `except OSError`, so a
  non-UTF-8 global copy raises `UnicodeDecodeError` and **errors** instead of taking the documented
  skip. Catch `(OSError, UnicodeDecodeError)` so an unreadable-or-undecodable global copy skips, as
  FR-11.8 intends. Do not broaden the clause any further — a bare `except Exception` would hide the
  drift signal this carve-out exists to preserve. (FR-11.8, FR-11.1)
- [ ] 11.5. Confirm nothing is widened: the carve-out stays closed at exactly the two assertions
  FR-11.8 names; no other assertion in either module or in any other module is deleted or weakened;
  the three-state discriminator still returns `drift` on every drift input Task 1 established (missing
  invariant, restated invariant, global-only heading); and nothing is written anywhere under
  `~/.claude/`. (FR-11.8, NFR-10, FR-12.1)
- [ ] 11.6. Test: extend `tests/test_sync_state_carve_out.py` with assertions driven over fixture
  strings only — no file writes, and no read of the operator's live global copy — that: (a) a global
  copy carrying several headings the repository copy lacks still yields `drift`, while the emitted
  message does **not** reproduce every heading verbatim (the count is reported and the quotation is
  bounded by the cap); (b) passing a **pre-populated** `reasons` list to either helper still yields
  `satisfied` over two identical texts and `pending` over a pending-shaped pair; (c) a global copy
  whose bytes are not valid UTF-8 makes the reworked assertion **skip** rather than error; and (d) the
  `ORCH_INVARIANT_PATTERNS` key set equals the pinned set. Then run
  `python3 -m unittest discover -s tests -v` and confirm the full suite passes. (FR-11, FR-11.1,
  FR-11.8, NFR-6, NFR-10)

**Requirements:** FR-11, FR-11.1, FR-11.8, FR-12.1, NFR-6, NFR-7, NFR-10
**Design Reference:** *A1 resolution* (the `claude_sync_state()` discriminator and its failure
message); *Conflict C-1* / amendment **A2**; DD-6, DD-7; the discriminator's honest limits L1–L4;
risks R3, R6. The finding record this task discharges is follow-up **F3** in
`.spec-state.json → followUps`, sourced from the Task 1 code review and security review (both PASS,
both non-blocking).
**Files:** `tests/test_docs_updates.py` (modify — `claude_sync_state()` and the reworked
`test_two_claude_files_byte_identical` only), `tests/test_orchestrator_label_lifecycle.py` (modify —
`orchestrator_sync_state()` and the reworked `test_repo_and_global_copies_are_byte_identical` only),
`tests/test_sync_state_carve_out.py` (modify — the discriminator's own test module, added by Task 1)

---

## Requirement Coverage

| Requirement | Task(s) |
|-------------|---------|
| FR-1        | Task 2 |
| FR-1.1      | Task 2, Task 3 |
| FR-1.2      | Task 2, Task 4 |
| FR-1.3      | Task 2, Task 3, Task 4 |
| FR-1.4      | Task 2, Task 3, Task 4 |
| FR-1.5      | Task 2, Task 3, Task 4 |
| FR-1.6      | Task 2, Task 4 |
| FR-1.7      | Task 2, Task 3, Task 4 |
| FR-2        | Task 3, Task 4, Task 5 |
| FR-2.1      | Task 3, Task 4, Task 6 |
| FR-2.2      | Task 5 |
| FR-2.3      | Task 3 |
| FR-2.4      | Task 3 |
| FR-3        | Task 4, Task 7 |
| FR-3.1      | Task 2, Task 4 |
| FR-3.2      | Task 4 |
| FR-3.3      | Task 2, Task 3, Task 4, Task 5 |
| FR-3.4      | Task 4 |
| FR-4        | Task 6 |
| FR-4.1      | Task 6 |
| FR-4.2      | Task 6 |
| FR-4.3      | Task 6 |
| FR-4.4      | Task 6 |
| FR-4.5      | Task 4, Task 6 |
| FR-5        | Task 7 |
| FR-5.1      | Task 3, Task 7 |
| FR-5.2      | Task 7 |
| FR-5.3      | Task 7 |
| FR-5.4      | Task 7 |
| FR-5.5      | Task 7 |
| FR-5.6      | Task 4, Task 7 |
| FR-5.7      | Task 7 |
| FR-5.8      | Task 7 |
| FR-5.9      | Task 7 |
| FR-6        | Task 8 |
| FR-6.1      | Task 8 |
| FR-6.2      | Task 8 |
| FR-6.3      | Task 8 |
| FR-6.4      | Task 8 |
| FR-6.5      | Task 8 |
| FR-6.6      | Task 8 |
| FR-6.7      | Task 8 |
| FR-6.8      | Task 8 |
| FR-7        | Task 8 |
| FR-7.1      | Task 8 |
| FR-7.2      | Task 8 |
| FR-7.3      | Task 8 |
| FR-7.4      | Task 8 |
| FR-7.5      | Task 8 |
| FR-8        | Task 8 |
| FR-8.1      | Task 8 |
| FR-8.2      | Task 8 |
| FR-8.3      | Task 8 |
| FR-8.4      | Task 8 |
| FR-8.5      | Task 8 |
| FR-9        | Task 5 |
| FR-9.1      | Task 2, Task 5 |
| FR-9.2      | Task 5, Task 8 |
| FR-9.3      | Task 5 |
| FR-9.4      | Task 5 |
| FR-10       | Task 9 |
| FR-10.1     | Task 2, Task 4, Task 5, Task 9, Task 10 |
| FR-10.2     | Task 9 |
| FR-11       | Tasks 1–11 (every task's final test sub-task) |
| FR-11.1     | Tasks 1, 2, 5, 6, 7, 8, 9, 10, 11 |
| FR-11.2     | Task 2, Task 3, Task 4, Task 5 |
| FR-11.3     | Task 7 |
| FR-11.4     | Task 6 |
| FR-11.5     | Task 8 |
| FR-11.6     | Task 5 |
| FR-11.7     | Task 9 |
| FR-11.8     | Task 1, Task 11 |
| FR-12       | Task 10 |
| FR-12.1     | Task 10 (+ global constraint 1 on every task; asserted by sub-tasks 9.3, 10.6 and 11.5) |
| FR-12.2     | Task 10 |
| FR-13       | Task 10 |
| FR-13.1     | Task 10 |
| NFR-1       | Task 5, Task 9 |
| NFR-2       | Task 9 (+ global constraint 2 on every task) |
| NFR-3       | Task 6, Task 7, Task 8 (+ global constraint 5 on every task) |
| NFR-4       | Task 3, Task 4, Task 7, Task 8 |
| NFR-5       | Task 2, Task 3, Task 4 |
| NFR-6       | Tasks 1–11 |
| NFR-7       | Task 7, Task 8, Task 11 |
| NFR-8       | Task 7, Task 8 |
| NFR-9       | Task 6, Task 7, Task 8 |
| NFR-10      | Task 1, Task 8, Task 10, Task 11 |
| NFR-11      | Task 10 (all prose authored in English; the spec artifacts keep EARS `FR-N`/`NFR-N` numbering) |

Every FR-1…FR-13 and NFR-1…NFR-11 is covered by at least one task, and every task cites at least one
requirement. No orphan tasks; no orphan requirements.

**Rows moved by amendments A3/A4** (A4 → *What A3 and A4 together require of `tasks.md`*, item 2 —
exactly six, all gaining Task 3): FR-1.1, FR-1.3, FR-1.4, FR-1.5, FR-1.7 and NFR-5. FR-11.2 and NFR-6
already listed Task 3 and did not move. **Rows moved by the addition of Task 11:** FR-11, FR-11.1,
FR-11.8, FR-12.1, NFR-6, NFR-7 and NFR-10.

**Rows moved by A5** (A5 → *What A5 requires of `tasks.md`*, item 5 — exactly **eight**, all gaining
**Task 4**): FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.7, FR-2, FR-2.1, NFR-4. Nothing else moves, and
the rows that do *not* move are stated here so no one has to re-derive them: FR-3.3, NFR-5 and
FR-11.2 already listed Task 4; FR-6.4 and FR-11.5 already list Task 8, so **no row moves for Task 8**
even though sub-tasks 8.5, 8.6 and 8.10 change; FR-1.1 does **not** gain Task 4, because A5 touches
neither C2 schema clause; and no row moves for Tasks 1, 2, 3, 5, 6, 7, 9, 10 or 11.

### Deliberately not tasked

- **`ci-templates/workflows/sdd-review-gate.yml`** — locked by Task 9's read-only assertions and
  modified by nothing (FR-10, NFR-2, AC-6).
- **`install.sh`, `~/.claude/`, and the post-merge global sync** — out of scope by A1; the operator
  runs `./install.sh` after merge (FR-12.1, NFR-10).
- **`agents/tasks-agent.md` rule 5** — risk R9 records that its wording reads as excluding non-code
  task lists. No requirement authorises the change, so no task edits it; it is flagged for a separate
  follow-up requirement.
- **`agents/vault-writer.md`** — C10 consumes its existing changelog contract unchanged; adding a
  field or a path would be a new write target (NFR-3).
- **AC-1, AC-2, AC-3, AC-5 and AC-9** are behavioural end-to-end scenarios over *future* features
  (design Flows A, B, C and E). They are discharged by the contract text plus the structural-lint
  assertions above, not by a runnable test of their own — no task can execute a future feature's
  pipeline. AC-4 is asserted within sub-task 8.10, and AC-6, AC-7, AC-8 and AC-10 are asserted
  directly by Tasks 9, 5, 1 and 10 respectively.
