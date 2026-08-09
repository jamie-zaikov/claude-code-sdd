# Process Lessons (binding)

Hard rules earned on feature `non-code-feature-track` (retired 2026-08-09 after 4 of 11 tasks).
Full reasoning and evidence: `.specs/retrospectives/non-code-feature-track.md`.
These are binding on every agent, not advisory.

## 1. Re-derive figures. Never inherit a number from a brief.

The dominant cost on that feature was **plausible recorded numbers that nobody re-checked** —
seven or more instances, each sending agents down a wrong path: an obsolete tool-grant
constraint that hardened into cited policy, an audit's "0/6" that was really 1/6, a design
count saying "Six" while enumerating seven, a pull request recorded as an open draft after a
human had merged it, a merge commit named as an ordinary commit, and a state file reporting
"not started" while two stages sat complete in the working tree.

- Every reviewer and validator **re-derives the one or two figures its verdict turns on** from
  the primary source, and says so in its report.
- When recording a figure a later reader will re-derive, **state its expected value and why** —
  not just its historical value. `EXPECTED ON ANY RE-RUN: 6/6; a different check returns 1/6 and
  that is NOT a regression` beats `6/6`.
- Verify `.spec-state.json` against disk before acting on it. It is gitignored, so it has no git
  history to recover from — keep a backup when editing it.

## 2. Query external state. Never infer it.

A pull request's state, a branch's existence, a label set, an auth status: **query it**. A
mid-feature merge silently closed the PR that every local record still described as an open
draft, which left per-task verdicts and `blocked:*` labels with nowhere to land. Found only
because one agent ran `gh pr view` instead of trusting its instructions.

Corollary: `gh` in this environment authenticates through its own keyring, not `GH_TOKEN` /
`GITHUB_TOKEN`. Run `gh auth status` **before** halting with a `SECRET REQUEST`.

## 3. One actor per file. One actor per outward-facing action.

A stand-down sent to a **coordinator does not stop a subagent it already launched**. Confirm the
stop from the actor itself, never from its dispatcher. This was violated twice: two appliers ran
concurrently on one document, and two agents raced to open the same pull request.

**The asymmetric hazard:** for a replace-style edit a second applier fails loudly, because the
text it searches for is already gone. For an **INSERT whose anchor survives the insert**, the
anchor still matches afterward, so the second edit **succeeds and duplicates the block silently**
— `Edit`'s uniqueness guard cannot catch it. When auditing any applied patch, assert every
insert-shaped hunk appears **exactly once**.

## 4. Assume agents die mid-task. Design so it costs one step.

Eight-plus agents died mid-task on that feature (`ENOTFOUND`, `Connection closed mid-response`)
and **none lost data**, because of this discipline:

- Write reports to `spec-memory/` **incrementally**, never as one terminal write.
- Update state **after each stage**, not each task.
- Prefer many small `Edit`s to one whole-file `Write`. A truncated `Write` destroys the file
  rather than failing cleanly.
- While uncommitted work exists, restore mutations from a `/tmp` snapshot with a recorded
  checksum — **never `git checkout --`**, which destroys a prior stage's uncommitted output.
- Resume from the on-disk ledger; do not restart completed work. **Never re-run an already-applied
  propagation** (see the duplication hazard in rule 3).
- Silence is not death: check the report's mtime and the process list before replacing a quiet
  agent.

## 5. Prose contracts have no compiler. Mutate to verify.

Where the artifact is a behaviour-bearing contract in Markdown, inspection proves nothing. The
recurring defect was **correct logic that nothing pinned** — it read right, and no test held it
in place. Three separate High-severity findings shared that exact shape.

- Prove a pin **bites**: mutate the pinned text (re-indent one line, add one trailing space) and
  confirm the assertion goes RED.
- Prove a guard **discriminates**: a probe that matches both the forbidden text and its
  legitimate replacement proves nothing.
- Beware **verb blindness**: a census keyed on one verb (`set`) misses the same action phrased
  with another (`apply`) — producing zero occurrences and total invisibility rather than a
  visible mismatch.

## 6. Amendments must not accumulate as layers.

Five amendment layers left one design document at 2723 lines describing its own history as much
as its design, with only a fenced block normative. That is how later work gets authored against
the wrong baseline. Fold an amendment's outcome into the base text; keep the narrative as a short
changelog. Where an implementation ends up **better** than the design it implements, record the
divergence immediately and fix the design — never degrade the implementation to match.

## 7. One pull request per feature. The merge is human and gated.

Tasks accumulate on the feature branch under a single **draft** PR, merged by a human only after
the whole-feature review passes and `ready-to-merge` is applied. Mid-feature merges were tried
and are the deviation, not the model: they leave the whole-feature gate with no accumulated diff
to review and make `ready-to-merge` gate nothing.

If mid-feature merges have already happened, the whole-feature review must run over the **full
feature diff from the branch's base commit**, not the open PR's diff — otherwise it silently
reviews only the last batch.
