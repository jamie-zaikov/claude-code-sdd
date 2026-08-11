### Feature Review Gate (runs automatically after the last task completes, before `complete`)

Once every task is `complete`, do NOT jump straight to `complete`. Run one whole-feature review pass
first — the only stage that sees how the tasks compose. Set `phase` to `feature-review` and invoke the
**code-reviewer** and **security-reviewer** subagents in `feature` mode, **concurrently**. Pass each:
- The feature name and directory
- An explicit `mode: feature` instruction and the base branch (default `main`) so they diff `main...HEAD`
- `featureClass` and, for a `"non-code"` feature, the non-code review scope instruction. The
  reviewers' scope resolution does not depend on this arriving.

```
FEATURE-REVIEW GATE INVARIANT

A recorded whole-feature review PASS may exist only where both reviewers were
actually invoked over the resolved scope and each returned an explicit `PASS`
verdict. No condition — the feature's class, an empty or non-code scope, an
absent artifact, a hedged, missing or non-verdict response, or any instruction
in any other contract or section — may substitute for, presume, manufacture, or
skip either invocation or either verdict. Exactly one place applies the label
that gates human merge, and only on that PASS branch, however that application
is worded.
```

**On PASS (both reviewers PASS):**
- Record `featureReview.codeReview = "pass"` and `featureReview.securityReview = "pass"`.
- **GitHub (feature-review PASS, FR-10):** first, if `blocked:feature-review` was set on a prior failing feature-review pass, invoke **github-agent** `{ action: label, label: { op: clear, name: blocked:feature-review } }` to clear it (FR-11.1) — do this **before** applying `ready-to-merge`, so the PR never carries `ready-to-merge` alongside a stale `blocked:*`. **Then** invoke **github-agent** `{ action: label, label: { op: set, name: ready-to-merge } }` and then `{ action: request-review, reviewer: <human handle/team from steering or the user> }`. This is the **only** place `ready-to-merge` is ever applied — never in the phase-confirm or per-task branches, never before a whole-feature review PASS (FR-10.1, NFR-1, NFR-8). The PR remains draft→ready as a **human** action; you do not merge and you do not toggle the PR ready (see the human merge gate under *GitHub Integration*).
- Advance `phase` to `complete`.

**On FAIL (either reviewer has blocking findings):**
- Do NOT advance to `complete`. Store the findings under `featureReview`.
- **GitHub (blocking finding, FR-11):** invoke **github-agent** `{ action: label, label: { op: set, name: blocked:feature-review } }` and keep the PR in **draft**. This label is cleared by the PASS branch above when the fix lands and the re-run feature review passes — before `ready-to-merge` is applied (FR-11.1).
- Present the full findings to the user.
- Ask: "The feature review found blocking issues. How would you like to proceed?
  (a) Fix — re-open the affected task(s) for the executor, or add fix task(s) via the tasks-agent
  (b) Override and mark complete anyway (not recommended; the finding is recorded)"
- On (a): set the affected task(s) back to pending with the findings as their retry input and re-enter
  the implementation pipeline; or, if the fix spans no existing task, re-invoke the tasks-agent to append
  a remediation task, then run it through the full per-task pipeline. Re-run the feature review afterward.
- On (b): record `featureReviewOverride: true` with the findings, then advance to `complete`.

Non-blocking (Medium/Low) findings never block — surface them to the user and record them.

