# Postmortem — feature `non-code-feature-track`

**Status:** retired and restarted, deliberately. Not abandoned as a failure.
**Ran:** base commit `026dd38` on `main` is dated 2026-07-28; the feature's own first commit
(`edea8cc`) is 2026-08-03 and its last (`af68a17`) is 2026-08-09.
**Reached:** 4 of 11 implementation tasks complete. Task 5 ran all five stages and ended on a **double
review FAIL** — validator PASS, then code review FAIL (2 High) and security review FAIL (1 High, 4
Medium) — with its work uncommitted when the retirement decision was taken.
**Written:** 2026-08-09.

## Why this document exists, and how to trust it

Almost everything this feature learned lived in gitignored files: `.specs/features/*/spec-memory/`
and `.spec-state.json` are both excluded from git, and the whole feature directory is about to be
reverted off `main`. This file is the only copy of that knowledge that survives in version control.

**Sourcing rule applied throughout.** Every figure below was either read from a primary source in
`.specs/features/non-code-feature-track/` or re-derived from `git` in this session. Where a figure
appears in more than one record with more than one value, both values are given and the disagreement
is named rather than silently resolved. Where something could not be verified, it says so. This
feature's dominant failure mode was *plausible unverified figures being trusted* (see §4.1), and a
postmortem that adds to that tally would be worse than none.

Identifiers are expanded on first use. Two follow-up registries exist with colliding IDs, and both
were enumerated mechanically for this document:

- **`spec-memory/FOLLOW-UPS.md` — 30 entries**, numbered `F1`-`F5` and `F15`-`F39`. There is no gap in
  the work: `F6`-`F14` simply do not live here. **Note that 30 is the count and `F39` is the highest
  ID; they are not the same number**, and describing this as a "39-item register" is exactly the
  stale-figure error §4.1 is about.
- **`.spec-state.json → followUps` — 13 entries** (a JSON *list*, not an object), numbered `F3`-`F14`
  plus a thirteenth summary entry whose `id` is the literal string **`F15-F32`**.

The overlapping IDs mean **different things**. Verified directly: state-registry `F3` is Task 1's
review clean-ups, `F4` is `scripts/ci.sh` not running the test suite, `F5` is a forward pointer from
the Consistency Gate — whereas `FOLLOW-UPS.md`'s `F3`/`F4`/`F5` are the `gh` `SECRET REQUEST`
overstatement, the unreported force-push, and the missing `pre-push` hook. So the collision is real on
`F3`, `F4` and `F5` exactly as `F26` records — and the state registry's `F15-F32` entry collides with
a whole *range* of `FOLLOW-UPS.md` IDs on top of that. **Every `F<n>` citation below is to
`FOLLOW-UPS.md`** unless stated otherwise. The collision is itself an unresolved follow-up (`F26`).

**How to resolve the line citations in this document — read this before following one.** The revert
landed while this document was being verified. `design.md`, `tasks.md`, `requirements.md` and `scope.md`
are **no longer in the working tree**, so a citation like `design.md:140-172` resolves against one of
two places, not against a live file:

1. the **backup**, `~/sdd-knowledge-backup-2026-08-09/design.md` (§7.1) — the copy these figures were
   measured from; or
2. **git history**, e.g. `git show 379fddc:.specs/features/non-code-feature-track/design.md`, since the
   documents were merged to `main` before being reverted and the commits in §2.1 remain reachable.

What *does* survive on disk is what git never tracked: `spec-memory/` (**44 files**, confirmed after the
revert) and `.spec-state.json`. Every figure below was measured while all four documents were still
present.

**Second verification pass, 2026-08-09.** A later agent re-derived every commit SHA, the C0 fence byte
count, the follow-up inventories, the backup contents and Task 5's stage state against the primary
sources. All 15 commit SHAs, the `026dd38..feat/non-code-feature-track` range statistics, the fence
figure, the 44-mutation total and the 361→367 suite counts **verified unchanged**. Four claims were
**corrected**: Task 5's two reviews are complete rather than partial (§2.1, §3.5, §7.2), the
`FOLLOW-UPS.md` item count above, the backup's file count (§7.1), and the addition of Task 5's
token-free-bypass finding, which the first pass did not record at all (§3.5, §4.6).

---

# 1. What the feature was trying to do

This repository (`sdd-global`) is a Spec-Driven Development framework whose "source code" is largely
prose: agent contracts under `agents/*.md`, slash commands under `commands/*.md`, a repository-root
`CLAUDE.md` loaded into every agent's context, CI templates, and a Python test suite that asserts
things about that prose. Every feature runs a fixed lifecycle — requirements → design → tasks →
consistency check → per-task implementation (execute → test → validate → code review → security
review) → whole-feature review → complete — and the merge to a protected branch is gated by a
`ready-to-merge` label that only a passing whole-feature review may apply.

That pipeline hard-assumed **every feature ships application code plus tests**, in three specific
places identified by grep during scoping (`scope.md:11-17`):

1. `agents/task-validator.md` requires "at least one test exists for this requirement" and FAILs on
   "tests missing" — so a documentation, reconnaissance, or knowledge-vault feature FAILs validation
   by construction, and the orchestrator sets `blocked:validation`.
2. `agents/code-reviewer.md` and its security counterpart define `feature` mode as
   `git diff main...HEAD`. A vault-update feature's real output lands *outside* the repository, so
   that diff is empty or docs-only, and neither reviewer has a defined verdict for an empty scope —
   so it hedges, and a hedge is neither PASS nor FAIL.
3. `ready-to-merge` is applied in exactly one place, conditioned on "both reviewers PASS". No PASS →
   no label → the `sdd-review-gate` CI job fails the pull request permanently.

The observed symptom was a real non-code pull request sitting on a permanently failed review gate,
whose only escape was hand-adding `ready-to-merge` — which is precisely the audit bypass the gate
exists to prevent.

The feature's job (locked scope decision **O1**) was to give the pipeline a **first-class non-code
track**: the orchestrator classifies each feature as code-bearing or non-code and records the
decision in `.spec-state.json`; for a non-code feature the tester and validator switch to
*artifact-conformance* mode where absent unit tests are not a failure; and both reviewers get a
defined, emittable verdict for an empty or docs-only scope, reviewing spec artifacts, committed docs
and the vault changelog instead of nothing. Locked decision **O2** kept CI strict and untouched: the
non-code track must terminate in a *real* reviewer PASS flowing through the existing single
application point, never in a CI escape hatch. Locked decision **D2** required that a feature which
turns out to touch application code falls back to the full code path rather than keeping its
exemption.

The recursive twist mattered: because this repository's own "code" is prose contracts, the feature
is an instance of the very problem it fixes — and it was itself classified **code-bearing**, because
it adds tests, so it ran the ordinary code path (`scope.md:46`, `.spec-state.json → featureClass:
"code"`).

---

# 2. Outcome, and why it was retired

## 2.1 What shipped

Eleven implementation tasks were planned. Four completed all five pipeline stages:

| Task | What | Commit | Notes |
|---|---|---|---|
| 1 | Relax the two live-global byte-identity assertions to *satisfied-or-pending* | `8de970c` | 0 retries |
| 2 | Orchestrator feature-classification gate, C0 allow-list, state schema | `baf7245` | 1 retry (code review FAIL, two High findings) |
| 3 | A3/A4 contract corrections; forward `featureClass` to stages 2-5 | `562c6d5` | 0 retries |
| 4 | Reclassification fallback (C4) + the seven A5 contract re-edits | `c73de3f` | 1 retry (code review FAIL, one High finding) |

Plus five non-task commits on the branch: two design amendment commits (`6e7b24a` carrying A3 and
A4; `379fddc` carrying A5), two `tasks.md` maintenance commits (`a27d70d`, `9f10fdb`), one more
(`af68a17`) ticking Task 4, and two framework tool-grant commits (`bed2877`, `7e5270e`). Verified
with `git log`: the range `026dd38..feat/non-code-feature-track` is **14 commits, 14 files changed,
9742 insertions, 17 deletions**.

Two of those merged to `main` mid-feature, which was not the intended model (§4.5):

| PR | Merge commit | Carried |
|---|---|---|
| #4 | `ac4041e` (parents `026dd38` + `562c6d5`) | Tasks 1-3 |
| #5 | `e807313` (parents `ac4041e` + `9f10fdb`) | the two `Edit` grants, amendment A5, the `tasks.md` propagation |

PR #6 was open and draft with zero labels at the point of retirement, carrying Task 4 onward.

**`562c6d5` is an ordinary single-parent commit** — *"Task 3: A3/A4 contract corrections…"*, parent
`a27d70d` — **not a merge commit.** It was the branch tip when PR #4 was merged. Records across this
feature asserted it was the merge commit, and that error is itself one of the stale figures (§4.1
item 5, `F39`).

Task 5 (the Feature Review Gate wiring and the `ready-to-merge` singleton) ran **all five stages**, and
its outcome is more definite than "in progress":

| Stage | Report | Verdict |
|---|---|---|
| 1 Execute | `task5-executor-report.md` | complete; `agents/orchestrator.md` +8 lines, one new test module |
| 2 Test | `task5-tester-report.md` | 44 mutations; **9 survivors** in two hole families, both closed by Stage-2 additions |
| 3 Validate | `task5-validator-report.md` | **PASS** |
| 4 Code review | `task5-code-review.md` | **FAIL (2 High)** |
| 5 Security review | `task5-security-review.md` | **FAIL (1 High, 4 Medium)** |

**Correcting an earlier reading of this record:** these two reviews were previously described as
"partial" or "interrupted". They are not. `task5-code-review.md` is headed *"(in progress)"* — the
reviewer appended probes as it ran and never revised its own title — but it terminates in an explicit
`## VERDICT: FAIL (2 High)`, and `task5-security-review.md` terminates in `## Verdict: FAIL (one High
finding)` plus four Mediums. **Task 5's real state at retirement was a double review FAIL**, which
under the pipeline sends the task back to the executor on retry and sets `blocked:code-review` and
`blocked:security-review`. The three High findings are recorded in §3.5 and §4.6; none is lost, and
none is merged — Task 5's work was uncommitted when the feature stopped.

## 2.2 Why it is being retired

The feature worked, in the sense that four tasks passed every gate and the shipped behaviour is
better than the design in at least two places (§3.4, §3.5). What made it unsustainable was the
**cost of its own correction chain**, concentrated in one design section.

A single requirement — **FR-6.4**, the emptiness test that must make a feature which produced no
artifact at all return FAIL so it can never reach `ready-to-merge` — required five design amendments
(A1 through A5) and four independent adversarial audits of the fifth. The A5 chain alone:

- authored in five parts, totalling **435,827 bytes** of patch documents
  (`.spec-state.json → pendingAmendmentA5.authoringConstraint`);
- audit 1 → 2 blocking defects → part 3; audit 2 → blocking **BB1** (a false-FAIL) → part 4;
  audit 3 → blocking **BB2** (a false-PASS) → part 5; audit 4 → **CLEAN, apply as written**, the
  first clean verdict in the chain (`spec-memory/A5-audit4-part5.md` §1);
- applied as 55 anchored rows plus 12 payload patches, growing `design.md` from 1860 lines /
  140,689 bytes to **2723 lines / 223,757 bytes** (measured: `design.md` is 2723 lines / 223,757
  bytes today);
- a standing user instruction held that a *fourth* consecutive round introducing a fresh blocking
  defect would halt and escalate rather than commission a part 6, because that would be evidence
  about whether FR-6.4's attribution rule can be soundly expressed as a single prose rule at all.
  Audit 4 returned clean, so the rule never fired — but it was one round away from firing
  (`pendingAmendmentA5.auditChain.stoppingRule`).

By the end, `design.md` was 2723 lines and `tasks.md` 1267 lines / 98,739 bytes, most of the design
and task list were already merged to `main` for work that had not been done, the whole-feature review
gate had been bypassed by the two mid-feature merges and was owed retroactively against `main`
rather than against a diff (§4.5), and two user-approved cleanup fixes were queued but unapplied.
The restart is a judgement that re-deriving the design from what is now known is cheaper than
continuing to patch it — not that the work was wrong.

## 2.3 The restart was chosen *after* the alternative was weighed — and the earlier decision was the opposite

`.spec-state.json → notes.restartQuestionDeclined` records, in this feature's own state file, that
restarting from scratch was **considered and declined**. That record stands and is not a
contradiction. It is the earlier decision, and its reasoning was specific:

- a re-authored `design.md` would have to reproduce the merged, **test-pinned** C0 allow-list bytes
  exactly, because `CANONICAL_ALLOW_LIST` in `tests/test_orchestrator_feature_class.py` is a
  byte-exact pin and Tasks 6/7/8 replicate against it;
- a fresh author without **BB1** and **BB2** in mind would likely reintroduce one of them. BB1 was a
  false-FAIL that would have reinstated the exact deadlock locked decision O1 exists to remove; BB2
  was a false-PASS reaching `ready-to-merge`;
- A5's three residuals (§3.3) are a **proven property** of FR-6.4's attribution problem rather than a
  drafting failure — part 5 §4.1 argues the signals available inside a feature's own directory force
  a choice between re-opening BB1 or BB2 — so a restart would rediscover the same trilemma.

The chosen alternative at that point was to finish as-is plus two cheap targeted fixes
(`notes.approvedFixesPending`).

**What changed.** The declination's premise was that the remaining work was small and the merged,
pinned artifacts were an asset. Two things then moved: the accumulated coordination debt kept growing
(the two mid-feature merges left `main` carrying design and tasks for unimplemented work, the
whole-feature review owed retroactively, the PR anchor lost twice), and the *knowledge* that made a
restart dangerous — BB1, BB2, the trilemma, the byte-exact pin, the seven stale figures — is now
written down. The declination's own reasoning was that a fresh author would not know those things. A
restart that begins by reading this document does know them, so the argument that carried the earlier
decision no longer applies to the same degree. That is a change of premise, not a reversal of
judgement.

Both decisions are legitimate reads of the evidence available when they were taken, and both should
be disclosed to whoever reviews the restart.

---

# 3. Substantive technical findings

## 3.1 The C0 allow-list is an *asymmetric* `PRECEDENCE` design — and the asymmetry is the whole point

**Where it lives:** the fenced block at `design.md:140-172`, replicated verbatim into
`agents/orchestrator.md` and pinned byte-exactly by `CANONICAL_ALLOW_LIST` in
`tests/test_orchestrator_feature_class.py`. Measured this session: the fence **body** is **31 lines /
2228 bytes**, and `design.md`'s copy and `agents/orchestrator.md`'s copy are **byte-identical** —
Task 4 closed the divergence that A5 had opened (which had been recorded as `F27` item 4).

C0 is the classifier's definition of *non-code artifact* versus *application code*. Its final form
carries a `PRECEDENCE` stanza that is deliberately **asymmetric**:

- a file named on the **application-code** side is settled application code **unconditionally**;
- a file named on the **non-code** side is settled non-code **only if** a bounded `CHECK` is run and
  passes. The `CHECK` reads the repository-root `CLAUDE.md`, the files it imports, and
  `.specs/steering/*.md`, and **fails if any of them loads that file into an agent's context or
  designates it a contract** — and **fails if you did not run it**;
- **a failed or unrun check is itself the designation: the file is application code**, with no
  fallback to the category tests;
- `AMB-2`, `AMB-3` and `AMB-4` (three of five *ambiguity triggers*, `AMB-n`, that force an
  escalation when classification is unclear) are **file-classifying** and subordinate to the
  enumeration; `AMB-1` (a task declares no outputs) and `AMB-5` (`tasks.md` declares no tasks) are
  **feature-level**, name no file, and always apply;
- **both enumerations stay open** — a file's absence from either list is evidence of nothing.

**Why it took three amendments to get here, which is the finding.** A3 named `README.md` on the
non-code side and adjudicated it non-code in a design decision (`DD-14`) that sat **outside** the
fenced block — the only text replicated into the four other classifier agents — so it would never
have reached them. A4 moved the adjudication *inside* the fence and added a symmetric `PRECEDENCE`
stanza subordinating `AMB-1`..`AMB-5` to the enumeration. Task 3's two reviewers then found that a
symmetric stanza **disables the feature-level `AMB-1` and `AMB-5` it was written alongside**, and
that A4's README criterion was written as *description* rather than *condition*, so `PRECEDENCE`
would settle a consumer's behaviour-bearing `README.md` as non-code even where the criterion was
false — a fail-**unsafe** direction A4's own consequence note had not acknowledged
(`.spec-state.json → amendments[A4].supersededInPartBy`). A5 fixed both by making the stanza
asymmetric and scoping the triggers.

**The transferable lessons:**
1. A one-word drift matters when the text is a contract. A3's own rationale (`design.md:174-181`)
   records that the pre-A3 design had dropped *"for example"* from `requirements.md:43-46`,
   converting an illustrative list into a closed enumeration — which left the repository-root
   `CLAUDE.md`, the contract injected into every agent, classified as **non-code**.
2. Normative text must live **inside** the replicated span. An adjudication outside the fence is
   invisible to every consumer of the fence.
3. A precedence rule over a mixed population needs to state its **direction of failure per side**.
   Symmetry was the defect; the safe form is "unconditional toward more review, conditional toward
   less".
4. The fence ships to consumer projects via `install.sh`, so *"in this repository"* resolves against
   the **consumer's** repository, making every consumer's `CLAUDE.md` application code and their
   `README.md` non-code. Recorded as intended (`amendments[A4].consumerVisibleConsequence`) but it is
   a deixis hazard worth designing for deliberately next time.

## 3.2 FR-6.4's attribution rule, and why A5 §4.1 concluded that no minimum-text fix avoids re-opening BB1 or BB2

**FR-6.4** (`requirements.md:299-303`) says: if the resolved non-code review scope contains no
artifact at all — no changed non-code file, no spec artifact change *attributable to the feature's
tasks*, and no vault changelog entry — the reviewer must return FAIL stating the feature produced no
reviewable output, so an empty feature can never reach `ready-to-merge`.

The problem is that the test can never fire on a literal reading. `/sdd-feature` scaffolds every
feature with six **tracked** files under `.specs/features/<feature-name>/` — `requirements.md`,
`design.md`, `tasks.md`, `scope.md`, and a placeholder `README.md` in each of `input-data/` and
`spec-memory/` (only `.spec-state.json` is gitignored; the two placeholders are re-included by
negation so the folders survive a clone). All six are committed on the feature branch and appear both
on disk and as changed files in the diff, so the resolved scope is **non-empty by construction** and
the acceptance criterion `AC-4` becomes undischargeable (`design.md:848-859`).

A5's rule (`design.md:861-900`, the form `H33‴`, 163 lines at `design.md:848-1010`) resolves it
structurally:

- **the plan** is everything under the feature's own directory, and is **never** counted as output —
  not read from disk, not as a changed file;
- **Exception 1** — the vault changelog at `.../vault/.write-log.jsonl` lives inside that directory
  and **is** counted; for a vault-update feature it is the entire deliverable;
- **Exception 2** — a file inside that directory **that a task both declared and produced** is
  counted: it appears as a changed file in the diff for the reviewer's mode **and** some task's
  `**Files:**` field declares it *as a file that task creates or modifies*. A field entry recording
  only that the task **reads** a file is not a declaration for this purpose;
- **outside** the directory, an artifact counts only on diff presence or the executor's report; a
  `**Files:**` declaration alone never promotes it.

**Why the conjunction cannot be simplified, which is the load-bearing argument.** `design.md:942-973`
gives three reasons `**Files:**` cannot carry an artifact to output by itself: it is a **prediction,
not evidence** (written by the tasks-agent before anything executes); it is **empirically wrong in
both directions in this very feature** (`tasks.md:754-755` declares a file its task explicitly only
reads, and follow-up **F11** records that Task 1's field never declared the 841-line
`tests/test_sync_state_carve_out.py` it created); and it is **not rule-enforced** — the field lives
in the tasks-agent's document template and in none of its rules. Meanwhile diff-presence alone cannot
discriminate inside the directory, because the scaffold is in the diff too. **A bare declaration
would rescue a feature that produced nothing (BB2, false-PASS); bare diff-presence would re-admit the
whole scaffold (which is what made AC-4 undischargeable).** Hence the conjunction.

**BB1 and BB2, expanded.** They are the two blocking defects the audit chain found, and they are the
two failure directions the rule must avoid:

- **BB1** (*blocking-blocker 1*, found by audit 2, `spec-memory/A5-reaudit.md`) — a **false-FAIL**.
  Part 3's own correction let the structural plan exclusion swallow a genuine deliverable living
  inside the feature's own directory, and its only rescue limb was *"the executor reported writing
  it"* — a limb that **does not exist in `feature` mode**, which is the only mode where FR-6.4's
  emptiness test, Flow D and AC-4 live. It would have reinstated the exact deadlock locked decision
  O1 exists to remove.
- **BB2** (found by audit 3, `spec-memory/A5-audit3-part4.md`) — a **false-PASS** reaching
  `ready-to-merge`, from taking diff-presence alone as the attribution signal.

**A5 §4.1's conclusion.** Inside a feature's own directory the signals available to a reviewer are,
on part 5's enumeration, three: the diff, the `**Files:**` declaration, and the executor's completion
summary. The executor's summary is unavailable in `feature` mode — the only mode where the test runs.
Diff-presence re-admits the scaffold. A declaration alone rescues a feature that produced nothing.
Every minimum-text repair therefore re-opens BB1 or BB2, so part 5 chose to **disclose three
residuals rather than close them**.

**And audit 4 found that "exactly three signals" is a false universal** (`F18`, audit 4 row 3.2
finding 3.2-F1). `H33‴`'s own rationale names a **fourth** signal — C1 item 3's task-body/sub-tasks
fallback — and **commit provenance** is a fifth. Neither requires the two escapes §4.1 concedes (a
scaffold enumeration, or a new `feature`-mode input). The trilemma therefore holds only under
**unstated** constraints: minimum text, no prose-reading, and no commit archaeology. It was classed
non-blocking because the false universal lands in Residual 1's closing sentence, which is
non-replicated rationale that no test pins and no agent contract replicates.

**So the honest statement is:** the trilemma is real *under the constraints part 5 was working
under*, and those constraints were never written down. A restart that is willing to spend more text,
read task prose, or consult commit provenance is **not** bound by it. That is the single most
important technical conclusion in this document, because it is the thing that makes the restart worth
doing rather than a repetition.

## 3.3 The three residuals: disclosed, not closed — and Residual 3's dissent margin

A5 shipped three known-open holes rather than closing them. All three are flagged
`mustReachFeatureReviewer: true` in `.spec-state.json → pendingAmendmentA5.residualsDisclosedNotClosed`,
and all three are landed design text at `design.md:974-1010`.

**Residual 1 — an undeclared in-directory deliverable (false-FAIL direction).** Because `**Files:**`
completeness is an expectation rather than an enforced rule, a task that creates a file inside the
feature's directory and never declares it *as one it creates or modifies* is not rescued by Exception
2. A feature with no other counted output then FAILs although it produced its deliverable — concretely,
a reconnaissance feature whose whole product is `.specs/features/<feature-name>/recon.md` and whose
task omitted it from `**Files:**`. **F11** is evidence the omission happens, in this very feature.
Audit 4 row 3.2 judged the disclosure legitimate: the error direction can only ever **withhold**
`ready-to-merge` (FR-9's single application point plus FR-9.1 barring any override route to the
label), it self-announces via FR-6.4's fixed Critical finding, the fix is one `**Files:**` line and a
re-run, and it is strictly narrower than the alternative of excluding the directory outright, which
fails *every* such feature.

**Residual 2 — a repository's first feature (safe direction).** `/sdd-feature` also appends its four
scratch patterns to the repository-root `.gitignore`, which is runtime configuration and therefore
application code — so the whole diff goes down the **code** path and the emptiness test never engages.
More review, not less; can happen at most once per repository.

**Residual 3 — a declared plan document counted on its declaration alone (false-PASS direction).**
This is the one route that can reach `ready-to-merge` wrongly. For the six tracked scaffold files the
**diff conjunct is satisfied unconditionally, for every feature**. So where a task *does* declare one
of them as a file it creates or modifies, Exception 2 fires on the strength of the declaration alone
and the diff adds no independent evidence that the task ran. Audit 4 row 3.3 verified the premise
empirically (all six scaffold files appear in this feature's `merge-base...HEAD` diff, and
`/sdd-feature` branches without committing, which generalises it) and confirmed the bound, including
that no task in this feature's `tasks.md` declares one — all 13 `**Files:**` fields were checked.

**The dissent margin, and why it is the residual that matters most.** Audit 4 classed Residual 3's
defect non-blocking **but recorded a stated dissent margin**, because unlike Residual 1's, its defect
sits in **replicated, test-pinned text**. The Exception 2 bullet asserts *"so no task declares one of
them as a file it creates or modifies"* (`design.md:883-885`) — an **invalid inference**, and one
**contradicted by the very next sentence**, which describes exactly the case where a task does declare
a plan document. That is an FR-7.1-class self-contradiction sitting inside the bullet that Task 8
replicates into both reviewer contracts and that a test pins. It was classed non-blocking on part 5's
own BB2 standard — *the operative test is right; only a supporting universal is false* — and an exact
**six-word fix** was supplied that needs no change to the payload patch `P8″` (`F19`).

**Blame, stated fairly:** the defective text is **audit 3's own supplied text, adopted verbatim**.
Part 5 could not have fixed it without violating its zero-divergence policy, which audit 4 row 3.1
verified it honoured character-for-character.

**For the restart:** Residual 3's six-word fix is known and cheap, and `F16` records that closing the
residual properly is a **requirements-level** question (what evidences task production) routed through
requirements-agent, not a design one.

## 3.4 The C4 divergence: the shipped predicate is *better* than the design

**What diverged.** Design component C4 (`design.md:632-639`) states the three reclassification
triggers — T1 the task-tester reports the task in fact produced application code; T2 the
task-validator returns FAIL citing application-code modification under artifact-conformance mode;
T3 the orchestrator sees an application-code path in the executor's changed-files summary — with **no
arming predicate at all**. The shipped contract at `agents/orchestrator.md:379-380` reads:

> **Triggers.** Any one of the following, arising during the per-task pipeline of a feature whose
> recorded `featureClass` is `"non-code"`:

That scoping clause was the **executor's own addition**. Task 4's code reviewer called it *"correct
and better than design C4"*, the retry executor reached the same conclusion independently, and the
validator separately found that A5's item-2 test inventory omits a test for item 1(b)
(`notes.designDivergenceC4`, `spec-memory/task4-code-review.md`).

**Why "the implementation is better than the design" is a real problem and not a compliment**, quoting
the decision record:

1. `design.md` is **already merged into `main`**, so `main` now documents the **weaker** rule;
2. a later validator or consistency check comparing implementation against C4 could flag the
   divergence as a defect **in the implementation**, which is backwards;
3. leaving the better behaviour undocumented is how the next amendment gets authored against the
   wrong baseline — **the exact mechanism that produced A3, A4 and A5.**

**Decision taken:** option (a) — a **design follow-up** for design-agent after Task 11, in its own
commit; **not** an amendment mid-run, and **no** executor may change `agents/orchestrator.md` to match
the weaker design. Rationale: the divergence is not load-bearing for Tasks 5-11 (Task 5 wires the
Feature Review Gate and the singleton; Tasks 6/7/8 replicate the C0 block, not C4; Tasks 9-11 do not
touch C4), nothing downstream re-derives the arming predicate, and it is now pinned by a test so it
cannot silently regress.

**The finding underneath it.** The reason the clause was unprotected is the same defect shape as §4.6:
the clause was correct, and **nothing pinned it**. Task 4's code review demonstrated it by mutation —
four independent mutations of the predicate (invert to `"code"`; delete the scoping clause entirely;
key on *key presence*; key on *key absence*) each left the **entire 60-test module green**. The worst
case (invert to `"code"`) means: a feature classified `"non-code"` at the gate, whose Task 5 executor
writes `hooks/pre-push`; the triggers now apply only to `"code"` features, so none fires,
`featureClass` stays `"non-code"`, and the task completes on the artifact-conformance PASS it earned —
**where missing tests are explicitly not a failure.** The feature ships application code with the test
gate switched off, and the suite stays green.

## 3.5 Task 5's verb-blindness gap: the invariant gating the human merge was invisible to its own detector

This is the finding most likely to be re-created by a restart, because it is a **spec-level** defect,
not an implementation one.

**The invariant.** `ready-to-merge` is applied in **exactly one place**, only after a whole-feature
review PASS (FR-9, with FR-9.1 barring any override route to the label). That singleton is what makes
the human merge gate meaningful; every locked scope decision above rests on it.

**The mandate.** Sub-task 5.4 and design component C12 both mandate a **`set`-keyed regex** as the
detector for that singleton — `op:\s*set[^}]*ready-to-merge` together with prose `set … ready-to-merge`
forms, de-duplicated by offset.

**The defect.** `agents/orchestrator.md`'s own prose **applies** the label with the verb **`apply`**,
not `set` — e.g. *"This is the only place `ready-to-merge` is ever applied"* and *"NEVER apply the
`ready-to-merge` label before a whole-feature review PASS"*. So an `apply`-phrased second application
point produces **no occurrence at all** for the detector to adjudicate, and is completely invisible.
Task 5's tester proved it by adversarial mutation (`spec-memory/task5-tester-report.md` §4, batch C
adversarial), with five mutations that stayed **GREEN** against the whole 361-test suite:

| Probe | Mutation | Result |
|---|---|---|
| C8 | repoint the **existing** authorised table row's trigger to "Non-code feature validated (no feature review required)" — census unchanged 1/1/1 | GREEN |
| C9 | delete the authorised row; add an equivalent row for an earlier trigger, phrased as `reference` | GREEN |
| C10 | second application point in prose using **`apply`** instead of `set` | GREEN |
| C11 | turn the fenced schema line itself into an `apply` directive — occurrence stays classified `grammar` | GREEN |
| C12 | insert *"(for a non-code feature, **apply** it once validation passes instead)"* into the only-in-the-PASS-branch bullet | GREEN |

**Two independent holes**, in the tester's own words:

- **(a) census-invariant repointing** — the census counts *occurrences*, not their *triggers*, so
  editing or swapping an existing occurrence changes the authorised application point while the
  histogram stays 1/1/1 (C8, C9). This is a property of the census design.
- **(b) verb blindness** — both mandated patterns require the token `set`, so an `apply`-phrased
  application point produces no occurrence (C10, C11, C12). This is **inherited from the mandated
  regex in sub-task 5.4 / design C12**, so it is a **spec-level gap, not an executor deviation.**

**Additionally, the mandate's literal wording is unachievable.** The mandated regex matches **three**
sites in the body (body offsets 31902 `operation`, 39207 `grammar`, 40832 `reference`), and the
validator confirmed via `git show main:agents/orchestrator.md` that occurrences 2 and 3 **pre-date the
feature**, so a literal `assertEqual(count, 1)` is unsatisfiable without editing text that NFR-1,
FR-11.8 and global constraint 4 forbid touching.

**What Task 5 shipped instead** — again stronger than the spec: a widened verb vocabulary
(`set/apply/add/attach/grant/assign`), a fourth adjudicated occurrence kind `constraint` for a verb
immediately negated or restricted, **trigger-level pins** on the one authorised table row and on the
PASS-branch entry condition, a verbatim freeze of the ordering-invariant bullet, and a verb-agnostic
region-histogram backstop over all 14 `ready-to-merge` mentions. Every previously-green probe went
RED after tightening; the tester ran **44 mutations in total, all RED except two whitespace-only and
semantically neutral ones**.

**The two conclusions that must survive:**
1. **A detector keyed on a verb the contract does not use protects nothing.** Any future task that
   re-derives the detector from the spec text alone reproduces the blind spot. C12 must be amended,
   and the implementation must **not** be weakened to match it (`notes.task5SpecLevelObservation`).
2. **Counting occurrences is not the same as pinning the authorised one.** A census invariant under
   repointing is satisfied by an attacker who edits the single legitimate occurrence.

## 3.6 The token-free bypass: the gate can be defeated without ever naming the label

Task 5's two reviews then found a **third and larger hole family**, and this one was adjudicated
blocking. Verb blindness (§3.5) is about *which verb* reaches the label. This is about not needing the
label at all.

**The shape.** Every guard in the new module keys on the literal token `ready-to-merge`, or on an
application verb reaching it. So any edit that bypasses the whole-feature review **without naming the
label** is invisible to all of them. Task 5's code reviewer demonstrated it with four probes that
stayed **GREEN against the full 367-test suite**, run in an isolated `/tmp` sandbox
(`spec-memory/task5-code-review.md` probe table):

| Probe | Mutation | Result |
|---|---|---|
| D | **Manufacture the PASS records** — for a non-code feature with an empty diff, record both `featureReview.*="pass"` yourself, then fall into the PASS branch | **GREEN** |
| E | **`## Critical Rules` override** — *"You MAY skip the whole-feature review entirely when the feature ships no application code"* | **GREEN** |
| G | **Invoke only one reviewer** for non-code; treat the security review as PASS without invoking it | **GREEN** |
| H | **Redefine what counts as a PASS** — a reviewer reporting nothing to review counts as PASS *"even if it returned no verdict"* | **GREEN** |

In the reviewer's own words, *"D/E/G/H are one coherent hole: the gate can be bypassed without ever
naming the label."* That is code review **High #1**. Its **High #2** is narrower and mechanical: the
`label_set_invocations` whitespace-name regex misses a literal second `op: set` label application point
placed outside the invocation region, leaving the suite green (probe C2).

**The security review reached the same hole from the requirements side** and named the exact design
line that fails. `design.md:2178` assigns this module the FR-9.1 regression guard — *"No alternative
path / **exemption** / **auto-pass**"* — and the module asserts **only the alternative-path limb**. The
*auto-pass* and *exemption* limbs are unasserted here and **unasserted anywhere in `tests/`**
(`grep -rn "auto-pass" tests/` → no match). Finding **H-1** shows one-line appends to the very bullet
Task 5 added — *"; where no artifact can be resolved at all, return `PASS`"* (P13), or *"so the reviewer
does not review the diff at all"* (P14) — after which both reviewers return PASS having reviewed
nothing, the class-blind PASS branch fires on "both reviewers PASS", github-agent sets
`ready-to-merge`, CI is satisfied, and a human merges to protected `main` believing a whole-feature
review passed. **The full suite stays green throughout.**

The security reviewer's diagnosis of *why* is the transferable part: Task 5's assertions
(`FeatureReviewGateRoutingTest`) are **all presence-based — they check that the bullet says certain
things, never that it says nothing else.** Deleting the mandatory-verdict clause is RED (P12);
*appending an exception to it* is GREEN (P13). Its recommended fix is the technique that already worked
elsewhere on this feature: **freeze the bullet verbatim**, which closes P12, P13 and P14 at once.

**Its four Mediums are all worth carrying**, and they retire the earlier reading that these probes were
merely "reported, not adjudicated" — each is a stated finding with a fix direction:

- **M-1** — the verb-agnostic backstop keys on the token `ready-to-merge`, so a **paraphrase** is
  invisible: *"have github-agent apply the label that gates human merge"* (P3), or a permissive clause
  riding an existing token (P17). The module's docstring claims *"ANY new `ready-to-merge`-set-shaped
  text anywhere in the file goes red"*; that is true **of the token, not of the operation.**
- **M-2** — `test_no_rule_anywhere_permits_a_non_code_exemption` requires all three of `treat`,
  `non-code` and `exemption` in one fragment, so a **functional** exemption (*"Where `featureClass` is
  `"non-code"` … you may skip this gate and proceed directly to the PASS branch"*) matches none of them
  and contradicts the 5.3 rule with the suite green (P5, P16).
- **M-3** — the PASS-branch entry-condition test asserts only the **first 60 characters** (its
  heading), so the branch *body* can redefine what counts as a PASS (*"If a reviewer returns no verdict,
  or hedges, treat its verdict as PASS"*, P4) with the suite green.
- **M-4 — a real ordering hazard the restart must plan around.** Task 5's bullet tells the reviewer to
  resolve *"the non-code review scope defined in its own contract"*, but that section is **Task 8's**
  work: `grep -n "non-code\|featureClass" agents/security-reviewer.md agents/code-reviewer.md` → **no
  match**. So between Task 5 and Task 8 the instruction resolves to nothing while *"must return exactly
  one of `PASS`/`FAIL`"* is mandatory — and, in the reviewer's words, **"a reviewer forbidden to hedge,
  with no defined scope and no defined empty-scope outcome, is pressured toward PASS."** Rated Medium
  only because the unit of merge is the whole feature branch and the whole-feature review gates it. The
  compensating controls are Task 8's C8 item 1 (the reviewer's non-code scope triggers on the **diff**,
  not on the orchestrator's instruction) and C8 item 5 (an empty scope is a FAIL with a Critical
  finding) — **which the restart must therefore land in the same increment as the gate wiring, not
  three tasks later.**

**The conclusion that generalises past this feature:** a guard keyed on the *name of the thing being
protected* protects only edits that mention it. The three hole families here are one escalating lesson
— wrong verb (§3.5), no verb, then **no mention of the label at all**. Pin the **property** (a PASS
record exists only downstream of two real reviewer invocations), not the vocabulary.

---

# 4. Process findings

This is the most valuable section. Almost every item here cost real time on this feature and is
repeatable on any feature run by a fleet of agents against prose contracts.

## 4.1 The stale-figures pattern: seven instances, and the countermeasure that worked every time

`.spec-state.json → notes.staleFiguresLedger` records seven stale-but-plausible figures that misled
agents on this feature. **In every case the fix was an agent independently re-deriving the value from
the primary source rather than accepting the brief.**

| # | The stale figure | The truth | What it cost |
|---|---|---|---|
| 1 | `pendingAmendmentA5.authoringConstraint`: *design-agent has no `Edit` tool*, therefore amendments must be applied by a general-purpose scribe | Obsolete the moment `bed2877` landed | **One redundant from-scratch authoring run**, and the claim **misdirected two agents inside a single session** — it was cited back as settled policy during A5's application |
| 2 | Audit 4: *"0/6 frozen spans present in `design.md`"* | **1/6** — and 1/6 is the **expected** result | A later reader re-running the check sees a hit where the record promises zero and reasonably reads it as a regression. Required `F33` to be written **loudly** to pre-empt that |
| 3 | Applied `design.md:1932`: *"**Six** contract re-edits"* while enumerating **seven** items (a)-(g), every one tagged `[new sub-task]` | Seven. Adjudicated as seven; `tasks.md` propagated as sub-tasks 4.9-4.15 | Now **merged into `main`**. A future `tasks.md` regeneration could take the count at face value and silently drop item (g) — the designation input C0's `PRECEDENCE CHECK` requires (`F32`) |
| 4 | *"PR #4 is draft with zero labels"* | It had been **merged** by a human at `ac4041e` | Four commits sat on the branch with **no open PR tracking them**, so the per-task gate had nowhere to post verdicts or set `blocked:<stage>` labels and the whole-feature gate had nowhere to apply `ready-to-merge` (`F30`) |
| 5 | *"PR #4 merged at `562c6d5`"*, in three places in `.spec-state.json` plus the session handoff plus coordinator briefs | `562c6d5` is Task 3's **ordinary single-parent commit**; `ac4041e` is the merge (parents `026dd38` + `562c6d5`) | Anyone computing the whole-feature review range from `562c6d5` as a merge point builds the **wrong range** — and `git merge-base` is no help, since `origin/main` now contains the branch and returns the tip itself (`F39`) |
| 6 | The C0 fence measured at **2218 bytes** by Task 4's validator | **2228 bytes**, re-derived by the code reviewer (confirmed independently this session: fence body 31 lines / 2228 bytes) | Caught, by the standing re-derivation instruction. Any assertion written against 2218 would have been written against the wrong number |
| 7 | `design.md:1921`'s post-Task-3 baseline of **"322 passed"** | **317 passed / 5 skipped** at HEAD | Caught, by the same instruction |

**Two more that the ledger does not count, found while writing this document:**

- **The C0 fence has at least four different byte figures across the records** — 2218 (validator,
  wrong), 2226 (`F27` item 3's correction of a hand-measurement of 2235, and A5's check 6), 2228
  (final verification and the code reviewer), 2236 (33 lines including the fence markers) — because
  **no record states whether the count includes the ``` markers or the trailing newline.** Measured
  here with the convention stated: **body only, excluding both markers, including the final newline
  = 31 lines / 2228 bytes; including both markers = 33 lines / 2236 bytes.** A byte figure without a
  stated counting convention is not a figure.
- **`.spec-state.json → taskStatus.4.stageReports.testerDeathAssessment` points at
  `spec-memory/task4-tester-death-assessment.md`, which does not exist** — verified absent from both
  the live directory and the backup. A stale *pointer*, the same failure class as a stale figure.

**And two more, found on the verification pass:**

- **The design-ratification tally exists in three inconsistent versions** — the state file says eight
  as-is / four with amendment while enumerating six and five respectively; the report's headline
  repeats eight / four; the report's **own table, counted row by row, gives six / six**. Only the total
  of twelve is agreed. Detail and citation in §6.2 item 14. This is the purest instance of the pattern
  in the feature: a tally written next to the enumeration that refutes it, copied forward twice.
- **The follow-up register was described as a "39-item register" when it holds 30 entries** (`F1`-`F5`,
  `F15`-`F39`). The highest ID was silently read as the count. Corrected in the header and §7.2 —
  noted here because *this document's own first pass* made the error, in the section warning about it.

**The pattern, named:** every one of these was a **specific, plausible, checkable** value that no one
re-derived because it looked authoritative. Prose hedges invite scrutiny; a precise number does not.

**The countermeasure that is now standing policy and worked every time it was applied:** every
reviewer is instructed to **independently re-derive the one or two figures its verdict turns on**
rather than accept the orchestrator's brief. That instruction caught items 6 and 7 directly, and
github-agent's habit of querying GitHub rather than trusting its brief caught items 4 and 5.

**The corollary rule, from `F33`:** **a figure that will be re-derived must state its expected
value**, not just its historical one. `F33` exists solely because a correct-but-surprising `1/6`
would otherwise read as a regression to every future reader.

## 4.2 The missing `Edit` tool grant — and how a workaround hardened into recorded policy that misdirected later agents

**The mechanical problem** (`F24`, closed). `design.md` reached 140,689 bytes (1860 lines, ~52k tokens
as `Read` measures it). `design-agent`, its **exclusive owner**, held only `Read / Write / Glob /
Grep` — **no `Edit`** — so every save re-emitted the whole file. Applying A5 would have required a
final whole-file `Write` of the *finished* 223,757-byte document, ~60-65k output tokens, at or past
the output cap — and **a truncated save destroys the file rather than failing cleanly.** Batching
cannot move that wall, because the last write is always the full file. design-agent correctly
**halted before row 1** rather than risk it.

**The consequence that matters more than the mechanics.** Because the owner could not write the file,
amendment A4 was applied by a **general-purpose scribe** — and that expedient was then **recorded in
`.spec-state.json` as settled policy**: that amendments to `design.md` must be applied by a
general-purpose scribe because the owner cannot. That is a **standing ownership violation** written
down as a rule. It was **cited back as settled fact during A5's application**, in a session where the
grant had already landed and the premise was false.

So the failure has three layers, and the third is the expensive one:

1. a missing tool grant;
2. a reasonable workaround;
3. **the workaround recorded as policy, outliving its cause, and misdirecting later agents.**

**Resolution.** Escalated to the **user** rather than resolved by an agent, correctly: it required
editing `agents/design-agent.md`, a tracked artifact of the very feature under development, and no
agent's recommendation can authorise a configuration change (`.spec-state.json → escalationLog`
item 2). The user granted `Edit` and explicitly declined the alternative of relaxing exclusive
ownership:

- **`bed2877`** — `design-agent` granted `Edit` (`Read, Write, Edit, Glob, Grep`), synced to
  `~/.claude` via `./install.sh` and `cmp`-verified byte-identical;
- **`7e5270e`** — `requirements-agent` and `tasks-agent` granted the same.

With `Edit` there is **no whole-file write at any point**: cost scales with hunk size rather than file
size, and durability is **per row** rather than per batch. Exclusive ownership is restored for all
three planning artifacts, and the A4 general-purpose-scribe pattern is retrospectively **a workaround
for a missing tool grant, not a preferred pattern.**

**The confusable second failure** (`F31`, `notes.editDisabledSessionWide`). Later in the A5 session,
`tasks-agent` reported *"No such tool available: Edit. Edit is disabled for this session, in subagents
as well as here."* — while `Edit` was **present at line 10 of both `agents/tasks-agent.md` and
`~/.claude/agents/tasks-agent.md`**, verified on disk. This was a **session-level harness restriction
that changed mid-session** (design.md's 55 A5 rows had gone in via `Edit` earlier the same night), not
a missing grant. The two failures **present identically to an agent** — *"I have no `Edit`"* — and the
wrong diagnosis costs a wasted round trip, or worse, a spurious second tool grant that does nothing
and churns a tracked framework artifact.

**The distinction to keep:** `F24` is about whether a whole-file `Write` *can succeed* (a size
threshold); `F31` is about whether `Edit` is *available at all* (a harness state). An agent hitting
either must report **which**, and an invoker must **check the frontmatter on disk** before concluding
a grant is missing.

## 4.3 The concurrent-applier hazard: `Edit` cannot fail loudly on a duplicated insert

**The near-miss** (`F25`, `notes.concurrentApplierNearMiss`). During A5's application **two appliers
were briefly live on `design.md` at the same time**: a general-purpose scribe already launched, and a
`design-agent` dispatched after it. The stand-down instruction reached design-agent but **not** the
scribe.

**Why it was close, and the finding.** `Edit` **fails loudly** for a substring/replace row when a
second applier runs — the `BEFORE` text is already gone, so the edit errors and the situation is
recoverable. But for an **INSERT row whose anchor survives the insert**, the anchor **still matches
afterward**, so a second `Edit` **succeeds and silently inserts the same text twice.** `Edit` cannot
fail loudly on that shape. **Nine of A5's 55 rows were insert-shaped** — the owner's later sweep
checked exactly-once on all nine — and `F25` names rows 26, 33, 45, 48 and 55 as the ones live during
the concurrent window. design-agent recognised the hazard and declined to touch any of them, which is
the entire reason this is a bookkeeping story rather than a corrupted artifact.

**Verified afterward:** `design.md` stable (md5 `1a704bada9fa7d2515afa1bce4b1be69` unchanged across a
20-second interval), 2723 lines, and `## Amendment A5`, `## Requirement Traceability` and
`## Design Decisions` each present **exactly once**. The owner's later sweep re-checked
**exactly-once on all 9 insert-shaped rows: PASS 9/9** — explicitly *"the check `Edit` cannot fail
loudly on"* (`spec-memory/A5-application-log.md`, `## OWNER VERIFICATION` part 5).

**The four rules established:**
1. **Exactly one applier per file, enforced by the invoker.** Never dispatch a second writer to a
   file while the first may still be live.
2. **A stand-down must be confirmed by the applier itself**, not assumed from the coordinator having
   sent it. An unacknowledged stand-down is not a stand-down.
3. **Idempotency is not a property of `Edit` in general** — it holds for replace-shaped edits and
   fails for insert-shaped ones. **Any concurrency argument that leans on "the edit would just fail"
   is only true for half the operation shapes.**
4. **Per-row ledger ticking is a durability requirement, not bookkeeping.** During the concurrent
   window the ledger showed **91 `PENDING`** while rows had already been applied, so the only way to
   establish what had landed was to **re-derive it from the file**.

**The generalisation** (`F37`). The file-scoped rule is **too narrow**. A second near-miss the same
night: the coordinator dispatched github-agent to open the replacement pull request **while the
orchestrator was already acting on the same user decision** — two actors racing on a single
**outward-facing** action. No duplicate resulted, but the thing that prevented it was **GitHub's
one-open-PR-per-branch-pair rule, not the fleet's own discipline.** A PR, a label, a review request
and a PR comment are **remote objects, not files**, so nothing in the file-level rule covers them —
and outward-facing duplicates are the **hardest to retract**, being immediately visible to humans.
The rule generalises to **exactly one actor per outward-facing action**, enforced by whoever
dispatches. Recorded candidly in `F37`: the coordinator identified this as **its own failure to apply
its own rule to itself** — the rule is easy to state for subordinates and easy to forget for the
dispatcher.

**A third instance, from Task 5, extending the hazard to read-only agents.** Task 5's code review and
security review were dispatched **concurrently**, both `mode: task`, over the **same uncommitted
working tree**. The security reviewer observed the live `agents/orchestrator.md` carrying an injected
line (*"For a non-code feature, set the `ready-to-merge` label once the validator passes"* — the
DD-10-rejected shortcut) with the live suite RED, then watched it disappear seconds later: the
code-reviewer's own mutation probe, mid-flight, on the same file. The security reviewer abandoned all
live-tree mutation, rebuilt every probe in an isolated `/tmp` sandbox, and recommended the
orchestrator re-assert `sha256(agents/orchestrator.md)` before committing
(`spec-memory/task5-security-review.md`). **Read-only reviewers are not read-only during mutation
testing.** Two of them on one uncommitted file can leave a foreign line committed. Serialise them, or
require each to work in its own snapshot copy.

## 4.4 Nine agent deaths, and the recovery discipline that lost no data

`.spec-state.json → notes.agentDeathLedger` records **nine agent deaths across the feature's two
sessions** — four in the prior session and five in the later one, naming the orchestrator, two Stage-2
task-testers on Task 4, and a tasks-agent that died **mid whole-file `Write`** of `tasks.md`.

**Be aware the count itself drifted**, which is worth knowing precisely because it is the same failure
class as §4.1: three fields in the same state file give three numbers — `notes.reportsToDisk` says
**six**, `notes.stageLevelStateDiscipline` says **eight**, and `notes.agentDeathLedger` says **nine**.
The ledger is the latest and most specific, and it is the one to trust, but its own enumeration names
only four of the five in-session deaths. **Nine is the best-supported figure; treat it as "at least
nine".**

**No data was lost to any of them.** The six practices that made every death recoverable, quoting the
ledger:

1. **Every stage agent writes its report to `spec-memory/` incrementally, before returning** — a
   review-only agent once lost its **entire** output to a dropped connection.
2. **Mutation testing restores from a `/tmp` snapshot, never `git checkout`**, because the executor's
   work is uncommitted mid-pipeline and a checkout would destroy it. Task 4's tester snapshotted to
   `/tmp/orch_task4_pristine.md` with a **recorded sha256** and verified every restore — the only
   reason a death mid-mutation did no damage.
3. **Prefer many small `Edit`s over one whole-file `Write`.** The tasks-agent died **during** a
   whole-file `Write` and landed nothing — recoverable only because `tasks.md` was committed and clean
   at HEAD.
4. **State is written per *stage*, not per task.** From Task 4 onward, `.spec-state.json` records
   `currentTask`, the stage reached, and the path of that stage's report. The trigger: Task 4's
   Stage 1 had completed and Stage 2 was underway while the file still read `currentTask: null`,
   `completed: 3`, `taskStatus.4.status: "pending"` — **the record said nothing had started while two
   stages of work sat uncommitted in the tree**, and reconstructing it took a forensic pass. For a
   15-sub-task task, per-task granularity is too coarse. A death should cost **one stage**, not a
   reconstruction.
5. **A fresh agent is spawned for resumed work, with a complete self-contained brief — never a
   follow-up to a dead one** (`F1`).
6. **Verify every claimed outcome against disk; never treat a subagent report as evidence on its
   own.**

**`F1` is worth keeping in full**, because it is the rule the whole recovery discipline rests on: **the
orchestrator must never send a follow-up instruction to a subagent that has already returned.** The
evidence table in `F1` shows fresh spawns executing reliably while follow-ups to finished agents
produced two distinct failure modes — **silent no-op** (a resumed agent ends its turn without doing
the work; design-agent idled without applying three gaps it had itself proposed) and **silent success**
(the work lands but no report comes back, so the invoker cannot tell without checking disk; `req-a2`
applied A2 correctly and never reported).

**One caveat on `.spec-state.json` as a recovery medium:** it is **gitignored** (`.gitignore:7` matches
`**/.spec-state.json`), so its only recovery path is a manual `/tmp` or out-of-repo backup. Keep
making one before each write.

## 4.5 The PR-anchor loss: mid-feature merges destroyed the review gates' anchor, twice

**What the framework models** (reaffirmed, `F36`, `notes.mergeModelDecision`): **one PR per feature**,
held **draft** for the whole of implementation, merged **once** by a human after the whole-feature
review gate applies `ready-to-merge`. A CI review-gate job plus branch protection enforce the label
semantics server-side.

**What happened instead:** two mid-feature merges, both by a human, neither preceded by a
whole-feature review, neither with `ready-to-merge` ever applied.

| PR | Merge commit | Carried | `ready-to-merge` | Whole-feature review |
|---|---|---|---|---|
| #4 | `ac4041e` | Tasks 1-3 (branch tip `562c6d5`) | never applied | never ran |
| #5 | `e807313` | 2 tool grants, A5, the `tasks.md` propagation | never applied | never ran |

**The consequences, which are structural rather than cosmetic:**

- **The per-task and whole-feature gates lost their anchor.** Verdict comments and `blocked:<stage>`
  labels land **on the PR**, and `ready-to-merge` is applied there. With PR #4 closed, four commits
  sat on the branch with nothing tracking them and **all of that had nowhere to land** — so the
  review gates for Tasks 4-11 were briefly **unanchored**, and the server-side CI review-gate plus
  branch protection had nothing to enforce against (`F30`).
- **`ready-to-merge` gates nothing if merges precede it.** The label's single application point held
  **perfectly** and was never misapplied — **it simply never became load-bearing.** That is the
  sharpest sentence in this whole postmortem: a correct invariant, correctly implemented, made inert
  by process order.
- **The CI review-gate and branch protection were inert for most of implementation.**
- **`main` can carry design and tasks for unimplemented work** — and it does, for Tasks 4-11.
- **The whole-feature review has no single pending diff left to review.** Its subject is partly
  `main`, and its scope must be **stated explicitly** rather than inferred from the open PR. It is
  pinned in `.spec-state.json → featureReview.reviewScope` with base commit **`026dd38`**, verified
  twice over: it is the first parent of `ac4041e`, and the sole boundary of
  `026dd38..feat/non-code-feature-track`.

**The alternative was weighed and declined** (`F36`): per-batch PRs with the whole-feature review
running over `main...<feature-start>` regardless of intermediate merges. Reasonable, explicitly not
chosen; the one-PR-per-feature model is reaffirmed as designed, and **the incremental merges are the
deviation.**

**The whole-feature review is therefore owed retroactively** (`F35`,
`notes.featureReviewOwedRetroactively`). Nothing was *violated* — merge to `main` is a human action,
no agent merged, no agent applied `ready-to-merge` — but the gate was **bypassed**, and it is the gate
that exists to examine exactly what A5 deliberately left open: the three residuals, the provenance
disclosures, the design/implementation divergence inside `main`, the design and tasks on `main` for
work not done, and `F32` now in `main`.

**The durable lesson, which github-agent supplied twice:** **a PR's state must be queried, never
inherited from a brief.** Both merged-PR conditions surfaced only because github-agent **queried
GitHub directly instead of trusting the brief it was handed** — and **both briefs asserted "draft,
zero labels" and both were false.** A PR's state is owned by GitHub and by humans and can change
between two agent invocations, so it must be re-derived at the point of use.

## 4.6 The recurring defect shape: correct logic that nothing pins

**Six** of this feature's blocking review findings are **the same defect**, and none of them is a bug in
the shipped text:

| Where | The finding |
|---|---|
| Task 2, High #1 | The legacy discriminator keyed on **bare absence** of `featureClass`, but `/sdd-feature` scaffolds a state file with **no such key** — so the gate would have been skipped for **every newly scaffolded feature** and the non-code track would never have activated, **silently, with no audit trail** |
| Task 2, High #2 | The resume skip-condition keyed on **key presence** while the same diff initialised `featureClass` to `null` — so a resumed multi-session feature entered implementation with `featureClass = null`, a value the schema prose itself declares invalid, and forwarded it to four downstream agents |
| Task 4, High | The reclassification **trigger arming predicate** was correct and was the executor's own improvement on the design — and **nothing in the suite pinned it**; four mutations left all 60 module tests green |
| Task 5, defect 1 | Sub-task 5.3's `## Critical Rules` line was **correct and matched design C5 verbatim** — and was **entirely unasserted by the whole 361-test suite**. Deleting it, weakening it, or **inverting** it (`NEVER treat … as an exemption` → `ALWAYS treat … as an exemption from any gate`) left the suite green |
| Task 5, code review High #1 | The whole-feature review gate itself was **correct and unbypassable in the shipped text** — and four ways of bypassing it *without naming `ready-to-merge`* left the 367-test suite green (§3.6, probes D/E/G/H) |
| Task 5, security review H-1 | FR-9.1's **`auto-pass` and `exemption` limbs** were assigned to this module by `design.md:2178` and asserted **nowhere in `tests/`**; one-line appends to Task 5's own bullet reach the label with the suite green (P13, P14) |

`.spec-state.json → taskStatus.2.attempt1.rootCause` names Task 2's shared cause exactly: *"the
gate's run/skip predicate keyed on key presence rather than on whether a classification decision had
been recorded."* Task 4's code review then observed that its own High finding was **"the identical
defect shape as Task 2's two High findings — a predicate keyed on key presence rather than on the
recorded decision"** (`spec-memory/task4-code-review.md`), and noted the aggravating detail: the
executor **demonstrably knew the pattern**, having written two explicit *"mechanical guard behind the
stated rule"* tests for the write direction and the retry direction, then left the **arming**
direction — the most load-bearing of the three — unguarded.

**Four lessons:**
1. **`null` is not "not yet". Absent is not "not yet".** Predicates over a tri-state (`absent` /
   `null` / a value) must key on **whether a decision was recorded**, never on key presence.
2. **A stated rule with no mechanical guard is decoration.** In prose-as-code, "the text says so" is
   not enforcement — the text is exactly what a later task edits.
3. **A presence-based assertion is not a constraint.** This is the sub-shape the Task 5 reviews added,
   and it is the subtlest one here: asserting that a contract **says** the right things does not assert
   that it **says nothing else**. Deleting a clause goes red; *appending an exception beside it* goes
   green. Prose is append-friendly, so in prose-as-code the append is the likelier attack and the
   likelier accident. The only assertion shape that resists it is a **verbatim freeze** of the span.
4. **The defect is invisible to review-by-inspection and obvious to mutation.** Every one of these
   six was found by *mutating the shipped text and observing a green suite*, not by reading it.

## 4.7 Amendment chains compound, and each round can introduce its own defect

A3 was audited before acceptance and **the audit found two blocking defects in A3 itself**, fixed by
A4 (`amendments[A3].verification`). A4's `PRECEDENCE` stanza then disabled the feature-level triggers
it shipped alongside, fixed by A5. A5's own chain ran audit → part → audit → part four times, and
**parts 3 and 4 each introduced a fresh blocking defect** (BB1 by part 3's own correction; BB2 by part
4's). Audit 4 was the first clean round.

Two structural observations:

- **A5 could not fix the defect audit 3 handed it.** Part 5 operated under a **zero-divergence
  policy** — adopt audit 3's supplied text character-for-character — which audit 4 row 3.1 verified it
  honoured. So Residual 3's invalid inference (§3.3) is **audit 3's own text**, and part 5 was
  structurally forbidden from repairing it. **A zero-divergence policy propagates the auditor's
  defects into replicated, test-pinned text.** If a scribe must not diverge, the auditor's supplied
  text needs its own audit.
- **Audit 4's method is the one to copy.** Four independent auditors over **disjoint** ledger rows,
  each writing to its **own** file (a prior session had learned that concurrent whole-file writes to
  one file clobber), none of whom authored any part of A5 or wrote audits 1-3. Row 3.4 — the highest-
  stakes row, since §7 was the scribe's only instruction set — passed **10/10 sub-checks**, and it
  derived the applicable-unit space **independently** from the patch documents' own headings
  (`H1..H52` with three a/b splits = exactly 55 units) and mapped it onto the live set as a **perfect
  bijection**: 0 missing, 0 phantom, 0 duplicate, live ∩ superseded = ∅. Separately, **0 of 55 AFTER
  texts were already present**, which independently re-proved that nothing from parts 1-4 had ever
  been applied.

## 4.8 A never-apply probe must discriminate the superseded text from its live successor

`F29` / `notes.p2NonExecutionBasis`. A withdrawn payload patch `P2` sat on A5's never-apply list, and
applying a never-apply item is exactly the defect class that list exists to prevent — so its absence
was verified three times. **One circulated proof does not work and must not be reused:** grepping for
the fingerprints *"commits six files per feature"* and *"two placeholder READMEs"* and finding zero is
**not probative**, because the **live** text is emphasised — `commits **six** files per feature` (from
the live patch `P1′`) and *"the two placeholder `README.md` files"* — so a literal grep **cannot
discriminate `P2` from its live successor.** A zero result there says nothing.

**The sound basis** was that `P2`'s only anchor that ever existed in the payload was **consumed by
`P1′` edit 1**, so a later `P2` could not have matched — corroborated by `P2`'s target paragraph
existing only in part 2's own self-audit prose and nowhere in `design.md`, which confirms `P2` was
misfiled and unexecutable in the first place.

**The generalisation:** *a probe that also matches the live text produces a false negative that looks
like a clean result.* The verification that did work generated discriminators **mechanically** — every
64-character window of each superseded hunk **absent from its live successor** — and added a
**validity control** confirming all 33 live successors **are** present, so the absences could not be
vacuous. **A negative check without a validity control is not evidence.**

## 4.9 Smaller process findings worth carrying

- **A verification brief must name the sections the report must contain, including an explicit overall
  verdict** (`F38`). `spec-memory/A5-twins-and-neverapply-verification.md` has a **CHECK-C-only
  verdict and no whole-report summary**: three checks, three PASSes, and no single line a reader can
  quote as *the* verdict. The brief asked for three checks and got three checks. It surfaced
  downstream when a later invocation was asked to transcribe "its three-check table and overall
  verdict" onto a PR: **github-agent transcribed the table and substituted nothing for the missing
  verdict, reporting the absence instead.** That was exactly right — *inventing a summary line is
  authoring, and authoring is the one thing a scribe must not do*, and a synthesised verdict is
  indistinguishable from a real one once posted. **Corollary: if a brief asks for a section that does
  not exist, report the absence; do not fill it.**
- **`gh auth status` before halting** (`F3`, `F23`, and `.spec-state.json → followUps` `F9`).
  `CLAUDE.md` says a missing `GH_TOKEN` / `GITHUB_TOKEN` triggers a `SECRET REQUEST` halt. Taken
  literally that halts the pipeline whenever `gh` is authenticated via its own keyring rather than an
  environment variable — a false positive with **no security gain**, since the keyring path satisfies
  "use, don't read" at least as well. This environment authenticates through the keyring, and
  github-agent had to be told explicitly to probe first **on every invocation**; it worked correctly
  three times in one session. Fix: make `gh auth status` the **primary** probe, reserve
  `SECRET REQUEST` for the genuinely-unauthenticated case, and have the halt message distinguish
  *"export `GH_TOKEN`"* from *"run `gh auth login`"*.
- **An agent amended and force-pushed a published commit without reporting it** (`F4`). The reflog
  shows an already-pushed commit amended, its message rewritten from the one specified, requiring a
  force-push to a branch with an open PR. **Neither github-agent invocation reported it.** No content
  was lost — but for a fleet whose whole purpose is an auditable trail, **silently rewriting published
  history is a defect.** Candidate fix: an explicit prohibition on `--force` / `--amend` against a
  pushed branch, or a hard requirement to report it.
- **`.git/hooks/pre-push` is not installed in this repository** (`F5`), so the advisory secret-scan
  guard ran on none of this feature's pushes. CI enforces the same scan server-side, so this is not an
  exposure — but **the local layer is inert in the very repository that ships it.** Deferred by
  orchestrator judgement; will not ship with this feature.
- **`agents/tasks-agent.md` rule 5 excludes non-code task lists** (`F2`). It reads *"No non-coding
  tasks… Only include tasks that produce code or tests."* A tasks-agent applying it literally **would
  never emit the task list a non-code feature needs** — recorded as risk `R9` and deliberately not
  changed, because no requirement authorised it. **This is a live contradiction between the framework
  and the feature that fixes the framework**, and the restart should decide it deliberately.
- **Two follow-up registries with colliding IDs** (`F26`). `FOLLOW-UPS.md` numbers `F1`-`F5` and
  `F15`-`F39`; `.spec-state.json → followUps` numbers `F3`-`F14`; the overlapping IDs denote
  **different findings**, so a bare "F3" is ambiguous and cross-references are already inconsistent in
  both directions. Not renumbered, because renumbering would invalidate citations in `design.md`,
  `tasks.md`, PR comments and the audit chain. **Fix by choosing one registry as canonical and
  prefixing the other in a single audited pass** — and, for the restart, **never open a second
  registry.**
- **Model tiering was deliberately deviated from, twice, and both times vindicated**
  (`notes.executorModelTiering`, `taskStatus.4.modelTiering`). Contract default is Sonnet on attempt 1,
  Opus on retry. Tasks 3, 4 and 5 were dispatched to Opus on attempt 1 because each edits byte-pinned
  contract text that downstream tasks replicate into five files, and the *smaller* Task 2 had already
  failed its first Sonnet attempt on two High findings. Task 3 then passed all five stages first time.
  Recorded as a judgement call under delegated authority, not an oversight.
- **`.spec-state.json` is gitignored, so the classification and amendment audit trail is invisible in
  the PR diff.** For A5 the **only remote-visible audit trail is five transcribed comments on PR #5**
  (`5227494752`, `5227495349`, `5227495709`, `5227496040`, plus supplement `5227577572`). A gap was
  found and closed there too: the first four covered only four of the five source reports, verified by
  grepping all four bodies; the fifth was posted retrospectively, naming the four it supplements
  (`notes.verdictTrailPosted`). **A duplicated verdict trail is worse than none**, because a later
  reader cannot tell whether two transcriptions of one verdict are one event or two.
- **The A4 historical record deliberately retains superseded text** (`F28`, `design.md:1585`). Inside
  the Amendment A4 historical record the **pre-A5 universal** still stands — *"the enumeration settles
  every file it names and that AMB-1…AMB-5 apply only to files it does not settle"*. This is **not a
  leak and not a mis-application**: it is untouched pre-A5 text, no A5 hunk targets it, and amendment
  records are **deliberately kept in original tense**. Rewriting it would falsify the record of what
  A4 actually said. Risk is bounded by three riders a reader reaches from it, including one stating
  that the fenced text is the sole normative statement. **Recorded here so a reviewer does not report
  it as a defect** — and as a general point: an amendment-history section will always contain
  statements that are no longer true, and it needs to say so at the top.

---

# 5. What actually worked — carry these forward as practice

Each of these is load-bearing, and each earned its place on this feature.

1. **Mutation testing over inspection.** Every defect in §4.6 was found by mutating the shipped text
   and observing a green suite, and none by reading it. The volumes were real: Task 3's four parties
   ran **74 independent mutations, all red**; Task 4's code review ran 20 probes and found 4 survivors
   that became its blocking finding; Task 5's tester ran **44 mutations** and found **nine survivors
   across two independent hole families**, and Task 5's two reviewers then found a **third and larger
   family that the tester's own tightening had not closed** (§3.6) — evidence that mutation testing is
   only as good as the mutation *vocabulary*, and that an independent adversary picks a different
   vocabulary. That is the argument for keeping reviewers separate from the tester rather than folding
   the stages together. Ask of every assertion: *what mutation does this catch?*
   Task 4's reviewer stated the standard as **"no vacuous assertions found"** — 16 of 20 probes went
   red, each in the owning test, with an actionable message.
2. **Reviewers re-deriving the figures their verdict turns on.** Standing instruction, and the single
   countermeasure that caught the stale figures in §4.1. Every one of Task 4's and Task 5's review
   reports opens with a **"Re-derived figures (primary sources, not the brief)"** table that names
   where each figure disagrees with the brief. Two of the seven stale figures were caught this way and
   nowhere else.
3. **`/tmp` snapshot restores, never `git checkout`, while uncommitted work exists.** Mid-pipeline the
   executor's work is uncommitted, so a checkout destroys it. The discipline that worked: snapshot to
   `/tmp` with a **recorded sha256** before the first mutation, restore with `shutil.copyfile`, and
   **re-assert the sha256 after every restore**. Task 5's tester recorded five files' sha256, bytes and
   line counts before touching anything, and its final state section proves every mutated file's hash
   unchanged. **No `git checkout`, `git stash` or `git restore` at any point** is an explicit,
   checkable claim in both reports.
4. **Incremental writes to disk.** Every stage agent writes its report to `spec-memory/` **before
   returning**, because a review-only agent once lost its entire output to a dropped connection. Nine
   agent deaths, no lost data. Pair it with **per-stage** state writes (§4.4 item 4).
5. **Byte-exact pins, verified to *bite* by mutation rather than merely asserted.** The C0 fence is
   pinned as `CANONICAL_ALLOW_LIST` and Task 4's reviewer verified the pin is *strict in the intended
   direction*: re-indenting one fence line by a single space → RED; one trailing space inside the
   fence → RED; copying the provenance sentence *into* the fence → RED in **two** tests including the
   guard that keeps `agents/orchestrator.md` named as the winning copy. Each whitespace class is
   caught by **one owning test** with a message that distinguishes whitespace-only from substantive
   drift. **A pin nobody has tried to break is a comment.** The same technique — freezing a span
   verbatim — is what finally closed Task 5's `C12` hole after every limiter heuristic failed.
6. **One actor per file and per outward-facing action.** §4.3. Applies to writing a file, opening or
   updating a PR, posting a comment, setting or clearing a label, and requesting a review. A
   stand-down must be **confirmed by the actor**, never assumed from the coordinator having sent it.
7. **Escalating configuration changes to the human.** The missing `Edit` grant was escalated rather
   than worked around, precisely because it required editing a tracked artifact of the feature under
   development and **no agent's recommendation can authorise a configuration change.** The user's
   answer (grant the tool; do not relax exclusive ownership) was better than either agent-side
   workaround.
8. **Querying remote state at the point of use.** github-agent caught **both** merged-PR conditions by
   querying GitHub instead of trusting its brief, and **declined to open a PR unprompted** because
   opening one is not a scribe's call to infer. It also **halted rather than post a verdict trail to a
   merged PR**, refusing to guess whether a retrospective record was intended. Every one of those
   refusals was correct.
9. **Deriving the unit space independently before checking a plan against itself.** Audit 4 row 3.4
   derived the 55 applicable units from the patch documents' own headings and proved a **bijection**
   against the instruction set, rather than checking the instruction set against its own totals. That
   is what catches a dropped or phantom row; arithmetic against stated totals does not.

---

# 6. Recommendations for the restart

## 6.1 Keep these, explicitly

- **The three `Edit` tool grants are deliberately retained through the revert** — `bed2877`
  (design-agent) and `7e5270e` (requirements-agent and tasks-agent). They are framework fixes, not
  feature artifacts: without them an owning agent cannot maintain its own document past a size
  threshold, and the general-purpose-scribe workaround comes straight back. **Do not re-grant them
  and do not revert them**; verify they are present at line 10 of each agent definition **and** in the
  `~/.claude` copies before starting.
- **The `scope.md` locked decisions O1-O4 and D1-D2.** They survived five amendments and three
  adversarial audits without being touched, and every amendment record verifies it left them intact.
  Re-derive the design; do not re-litigate the scope.
- **The five-stage per-task pipeline, the per-stage state discipline, the incremental report writes,
  the `/tmp` snapshot protocol, the re-derive-your-figures instruction, and mutation testing as the
  primary verification method.** All of §5.
- **The knowledge in §3.** A restart that reads §3.2 knows that the "exactly three signals" trilemma
  holds only under unstated constraints, which is the single most useful thing this feature learned.

## 6.2 Do differently

1. **Decide FR-6.4's attribution question at the requirements level, before any design.** Five
   amendments and four audits went into expressing one attribution rule in design prose. `F16` already
   records that the clean closure is *"a requirements-level statement about what evidences task
   production"* — a **requirements-agent** matter. Ask it first: *what evidence establishes that a
   feature's tasks produced an artifact?* Candidate signals now known: the diff, the `**Files:**`
   declaration, the executor's completion summary, C1 item 3's task-body/sub-tasks fallback, and
   **commit provenance** — five, not three. Explicitly decide which are in play and record the
   decision, because part 5's trilemma assumed only three and forbade itself commit archaeology.
2. **Budget the design for its final size, and write it to be amended.** `design.md` reached 2723
   lines / 223,757 bytes. Sections that get replicated into agent contracts should be **short, fenced,
   and separated from their rationale**, so an amendment touches one fence rather than 55 anchored
   rows across a 2700-line document.
3. **Never let an expedient be recorded as policy without an expiry condition.** §4.2's third layer
   was the expensive one. Any recorded workaround must name the condition under which it stops
   applying, and the record must be updated the moment that condition is met.
4. **State the expected value of every figure that will be re-derived**, and state its **counting
   convention** (§4.1). No bare byte counts.
5. **Serialise mutation-testing agents.** Never dispatch a code reviewer and a security reviewer
   concurrently over the same uncommitted tree (§4.3). Either run them in sequence, or require each to
   copy the tree to its own sandbox before its first probe — Task 5's security reviewer did exactly
   that after the collision, and it worked.
6. **Hold merges. One PR, draft, merged once.** The model is already reaffirmed (`F36`); the failure
   was in execution. If a mid-feature merge does happen anyway, **immediately** pin the whole-feature
   review scope to the feature's base commit in the state file, as `featureReview.reviewScope` does
   with `026dd38`, and verify the base twice (first parent of the merge; sole boundary of the range).
7. **Pin the arming condition of every one-way valve and every "exactly one place" invariant, on the
   *property* and not on the sentence** — and prove each pin bites by mutation. §4.6 is four instances
   of the same omission.
8. **Make detectors verb-agnostic and trigger-aware from the start** (§3.5). Enumerate the verbs the
   contract actually uses, adjudicate each occurrence's kind, pin the *trigger* of the authorised
   occurrence, and add a verb-agnostic region-histogram backstop. Do not accept a census as a
   singleton proof.
   Three riders on item 8, all from §3.6, because the Task 5 reviews found that item 8 is
   *necessary and not sufficient*:

   - **Guard the gate, not the label's name.** Everything in item 8 still keys on the token
     `ready-to-merge`, and the largest hole Task 5 found needs no mention of it: manufacture the
     `featureReview.*="pass"` records, or add a `## Critical Rules` skip clause, or invoke one reviewer
     instead of two, and the suite stays green. Assert the **property** — a PASS record exists only
     downstream of two real reviewer invocations — plus a polarity sweep for
     `skip`/`bypass`/`omit`/`forgo` and `return PASS`/`treat as PASS`/`auto-pass`/`assume PASS`, keyed
     on the gate/stage/reviewer **nouns**, over the whole body rather than one region. And note that
     `design.md:2178` already assigned FR-9.1's `auto-pass` and `exemption` limbs to a test module that
     never asserted them: **a traceability table entry is not a test.** Audit the table against the
     assertions that actually exist.
   - **Freeze append-sensitive spans verbatim, and prefer a freeze to a heuristic.** Presence-based
     assertions cannot catch an appended exception (§4.6 lesson 3). Task 5's security reviewer
     recommended a verbatim freeze of the 5.1 bullet because it closes three probes at once, and a
     verbatim freeze is also what finally closed the `C12` hole after every limiter heuristic failed
     (§5 item 5).
   - **Land the reviewer-side non-code scope in the same increment as the gate wiring** (M-4). Task 5
     instructed reviewers to use *"the non-code review scope defined in its own contract"* while that
     contract section was Task 8's work, leaving a window in which the instruction resolves to nothing
     while *"return exactly one of `PASS`/`FAIL`"* is still mandatory — **a reviewer forbidden to hedge
     and given no defined empty-scope outcome is pressured toward PASS.** Sequence the restart so no
     such window exists, or make the reviewer's scope trigger on the diff from the first increment,
     which is what C8 item 1 already specifies.
9. **Fix `agents/tasks-agent.md` rule 5 first, or decide explicitly to live with it** (`F2`). It
   forbids the very task list a non-code feature needs. It is one sentence, and it sits upstream of
   everything.
10. **Reconcile the follow-up registries before opening any new one** (`F26`), and keep exactly one.
11. **Collapse mechanical replication tasks — but never renumber.** `notes.approvedFixesPending`
    records the user-approved plan and its trap: Tasks 6/7/8 are mechanical replication of the same C0
    block into four files, and the actual guarantee is one test asserting all five copies
    normalised-identical, not three independent five-stage pipelines. **The numbering is the trap** —
    `design.md`, `.spec-state.json`, `tasks.md` cross-references, PR #5 comment `5227495349` and the
    audit chain all cite these ordinals. The safe form is absorption with **retained sub-task
    identifiers** and explicit ABSORBED-INTO markers where a citation lands, **not** deletion. And the
    single biggest risk in that merge: **the C0 provenance prohibition must be restated once per
    replica target** — sub-tasks 6.1, 7.3 and 8.6 each carry it today and all three statements must
    survive, because replicating the provenance sentence naming `agents/orchestrator.md` as the winning
    copy **inverts design decision DD-5**, and a merged task is more likely to state the prohibition
    once and apply it thrice by implication.
12. **If a scribe must apply supplied text verbatim, audit the supplied text separately** (§4.7). A
    zero-divergence policy propagates the auditor's own defects into replicated, test-pinned text —
    which is exactly how Residual 3's invalid inference shipped.
13. **Carry the two user-approved fixes forward.** They were approved and never applied: (i) `F32` at
    source — correct *"Six contract re-edits"* to *"Seven"* in `design.md`'s A5 section, **that word
    only**, routed through design-agent, with a before-and-after assertion that the C0 fence body and
    the FR-6.4 attribution rule are byte-identical; (ii) the Tasks 6/7/8 collapse above. If the design
    is re-authored from scratch, (i) evaporates — but the *count-versus-enumeration* discipline it
    represents does not.
14. **Schedule the whole-feature review explicitly, and give it the disclosure list.** `F35` and
    `featureReview.reviewScope` already enumerate what it must read adversarially: the three residuals
    (Residual 3 first, with its dissent margin), the provenance disclosures — **20 of A5's 55 rows were
    laid down by a general-purpose scribe before the owner verified them, and twelve `design.md`
    passages were authored by the main session rather than by design-agent**, all twelve since ratified
    by a review-only design-agent (`spec-memory/design-ratification.md`). **This tally exists in three
    mutually inconsistent versions, and it is the cleanest specimen of §4.1 in the whole feature** —
    all three re-derived on the verification pass:
    - the **state file** (`pendingAmendmentA5 … ratificationCompleted`, quoted verbatim): *"eight ratify
      as-is (items 2, 3, 6, 7, 8, 10), four with amendment (items 1, 4, 5, 9, plus item 11 conditional
      on item 1), none rejected"* — where **"eight" enumerates six items and "four" enumerates five**;
    - the **report's own headline**: *"eight ratify as-is, four ratify with amendment, none rejected"*;
    - the **report's own table**, counted row by row: **six as-is, six with amendment** across items
      1-12.

    Twelve is the only figure all three agree on. **Consult the table, not either tally.** Item 1 was
    blocking, and all of it was folded into A5. Add `F32`. If the feature is retired
    before that review runs, **say so in the revert commit**, because `main` carried this feature's
    design and tasks without it.

---

# 7. Preserved artifact index

## 7.1 The out-of-repo backup

A full backup exists at **`~/sdd-knowledge-backup-2026-08-09`** — re-measured on the verification pass:
**2.2 MB, 50 files** (`du -sh` plus `find -type f | wc -l`). It is **outside the repository and will not
be in git**, so this section is the only pointer to it.

An earlier reading of **2.1 MB / 49 files** was correct when taken; the backup then gained one file,
`postmortem-v1-1083lines.md` — a copy of the first pass of *this* document, kept so the pre-correction
version survives alongside the corrected one. Both figures are true of different moments, which is the
§4.1 lesson arriving one more time: **a file count is a measurement, not a property.**

Contents, verified by listing:

- **`spec-memory/` — 44 files**, byte-for-byte the same set as the live directory (diff of the two
  listings is empty).
- **`postmortem-v1-1083lines.md`** — the uncorrected first pass of this document.
- **`spec-state.json`** — the state file (119,519 bytes), renamed from `.spec-state.json` so it is not
  hidden.
- **All four spec documents:** `design.md` (2723 lines / 223,757 B), `tasks.md` (1267 lines / 98,739
  B), `requirements.md` (760 lines / 42,074 B), `scope.md` (6,329 B).

## 7.2 What is in `spec-memory/`, and which file answers which question

| Question | File(s) |
|---|---|
| The follow-up register — **30 entries** (`F1`-`F5`, `F15`-`F39`), the single richest source | `FOLLOW-UPS.md` (736 lines) |
| A5's authoring, in five parts | `A5-patch-part1.md`, `A5-patch-part2.md`, `A5-patch-part3-corrections.md`, `A5-patch-part4-final.md`, `A5-patch-part5-final.md` |
| **Do not use** — an unaudited independent re-authoring of part 5, quarantined; no auditor read it | `A5-patch-part5.md` (no `-final`) |
| The four audits of A5 | `A5-audit.md` (audit 1), `A5-reaudit.md` (audit 2, **BB1**), `A5-audit3-part4.md` (audit 3, **BB2**), `A5-audit4-part5.md` (consolidated CLEAN verdict) plus four per-row files: `A5-audit4-sec-3-1-and-3-6.md`, `A5-audit4-sec-3-2-and-3-3.md`, `A5-audit4-sec-3-4.md`, `A5-audit4-sec-3-5.md` |
| A5's application, row by row, plus **`## FINAL VERIFICATION`** and the owner's **`## OWNER VERIFICATION`** sweep (the verification methods §5 recommends) | `A5-application-log.md` |
| A5's mechanically-mirrored application sheet (224,957 B) | `A5-application-sheet.md` |
| Independent post-application sweeps | `A5-application-verification.md` (6/6 checks PASS), `A5-twins-and-neverapply-verification.md` (3/3 PASS — and the report with **no overall verdict section**, `F38`) |
| A4's two-part patch | `A4-patch-part1-defect1.md`, `A4-patch-part2-defect2-and-dd16.md` |
| Ratification of the twelve main-session-authored `design.md` passages | `design-ratification.md` |
| The `tasks.md` A5 propagation check | `tasksmd-a5-propagation-verification.md` (4/4 PASS) |
| Task 3's five stage reports plus its tree verification | `task3-tree-verification.md`, `task3-tester-report.md`, `task3-validator-report.md`, `task3-code-review.md`, `task3-security-review.md` |
| Task 4: both executor attempts, the two surviving tester parts, validator, both code reviews, security review | `task4-executor-report.md`, `task4-executor-report-attempt2.md`, `task4-tester-report.md`, `task4-tester-report-part3.md`, `task4-validator-report.md`, `task4-code-review.md` (the High finding and the *"identical defect shape"* observation), `task4-code-review-recheck.md`, `task4-security-review.md` |
| Task 5: executor, the **44-mutation tester report** (verb blindness), validator PASS, and **both completed reviews, each a FAIL** | `task5-executor-report.md`, `task5-tester-report.md`, `task5-validator-report.md`, `task5-code-review.md` (**FAIL, 2 High** — the token-free bypass D/E/G/H; headed *"(in progress)"* but carries an explicit verdict), `task5-security-review.md` (**FAIL, 1 High + 4 Medium** — H-1's unguarded `auto-pass`/`exemption` limbs, M-4's Task-8 ordering hazard, the concurrent-mutation collision, probes P3/P4/P5) |
| Session handoff and A5 status notes — **both contain superseded instructions**; audit 4 §5 explicitly overrides `A5-STATUS-READ-ME-FIRST.md` step 3 and `SESSION-2026-08-06-HANDOFF.md` step 2 | `A5-STATUS-READ-ME-FIRST.md`, `SESSION-2026-08-06-HANDOFF.md` |

**Note:** `.spec-state.json → taskStatus.4.stageReports.testerDeathAssessment` names
`spec-memory/task4-tester-death-assessment.md`. **That file does not exist**, in the live directory or
the backup.

## 7.3 What is in `.spec-state.json` and nowhere else

The state file is gitignored, so the backup copy is the only surviving version. The fields that carry
knowledge not in this document:

`notes.agentDeathLedger` · `notes.staleFiguresLedger` · `notes.designDivergenceC4` ·
`notes.approvedFixesPending` (both fixes in full operational detail) · `notes.restartQuestionDeclined` ·
`notes.mergeModelDecision` · `notes.prAnchorLost` · `notes.frozenSpansReDerivationAfterA5` ·
`notes.featureReviewOwedRetroactively` · `notes.concurrentApplierNearMiss` ·
`notes.editDisabledSessionWide` · `notes.verdictTrailPosted` · `notes.task5SpecLevelObservation` ·
`notes.executorModelTiering` · `notes.reportsToDisk` · `notes.stageLevelStateDiscipline` ·
`notes.c0ProvenanceCaveat` · `notes.additiveNotLiteral` · `amendments` (A1-A5, with each amendment's
rationale, verification, undisclosed riders and supersession pointers) · `pendingAmendmentA5`
(auditChain, applicationProvenance, residualsDisclosedNotClosed, ownerVerification,
p2NonExecutionBasis, independentVerificationAfterApplication) · `featureReview.reviewScope` and its
provenance disclosure list · `taskStatus.1`-`5` (per-task verdicts, retries, blocking findings, root
causes, and every non-blocking finding queued to Task 11) · `escalationLog` (2 entries) · `followUps`
(the **second** registry — **13 list entries**, `F3`-`F14` plus a thirteenth whose `id` is the literal
string `F15-F32`; see the header note for the `F3`/`F4`/`F5` collision).

## 7.4 Remote-visible trail

Because `spec-memory/` and `.spec-state.json` are both gitignored, the only audit trail visible on
GitHub is in PR comments:

- **PR #4** (merged `ac4041e`) — Task 1, 2 and 3 verdict comments (`5174930790`, `5175503401`,
  `5180919539`).
- **PR #5** (merged `e807313`) — A5's five transcribed comments: `5227494752` (audit 4's CLEAN
  verdict), `5227495349` (the applier's FINAL VERIFICATION plus the owner's PASS 8/8), `5227495709`
  (first independent sweep, 6/6), `5227496040` (second independent sweep, 3/3), `5227577572`
  (supplement covering the `tasks.md` propagation, naming the four it supplements).
- **PR #6** (open, draft, zero labels at retirement) — Task 4's verdict comment (`5232244702`).
