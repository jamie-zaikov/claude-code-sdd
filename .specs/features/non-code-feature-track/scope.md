# Scope: non-code-feature-track

<!-- Owned by main session during pre-orchestrator scoping. Read by orchestrator and passed to all specialists. Fill in during scoping; lock before invoking the orchestrator. -->

## One-line description
Give the SDD pipeline a first-class path for features that ship no application code — recon/investigation write-ups, documentation, and knowledge-vault updates — so they reach a genuine reviewer PASS and earn `ready-to-merge` through the same audited code path as code features, instead of deadlocking on the CI review gate.

## Problem statement (observed)
A non-code feature's PR sits on a failed `sdd-review-gate` forever, with no labels. The only escape today is hand-adding `ready-to-merge`, which is exactly the audit bypass the gate exists to prevent.

Three places in the fleet hard-assume every feature ships code plus tests:

1. `agents/task-validator.md:39-41,77` — the validation checklist requires "at least one test exists for this requirement" and FAILs on "tests missing". A docs/recon/vault task has nothing meaningful to unit-test, so it FAILs, and the orchestrator sets `blocked:validation` (`agents/orchestrator.md:142`).
2. `agents/code-reviewer.md:45-46` and the security-reviewer equivalent — `feature` mode is defined as `git diff main...HEAD`. A vault-update feature's real output lands **outside** the repo (the vault is a separate Obsidian tree written by `vault-writer`), so that diff is empty or docs-only. Neither reviewer has a defined verdict for empty or non-code scope, so it hedges — and a hedge is neither PASS nor FAIL.
3. `agents/orchestrator.md:152-154` — `ready-to-merge` is applied in exactly one place, conditioned on "both reviewers PASS". No PASS → no label → `ci-templates/workflows/sdd-review-gate.yml:62-65` fails the PR permanently.

Confirmed by grep: no occurrence of an empty-diff, no-code, or docs-only path anywhere in `agents/`, `commands/`, or `ci-templates/`.

## Open questions resolved
- O1: How far should the fix go? → **First-class non-code track.** The orchestrator classifies a feature as code-bearing or not; for non-code features the tester/validator switch to artifact-conformance (tests optional, absence is not a FAIL) and the reviewers get a defined verdict for empty/docs-only scope, reviewing the spec artifacts and the vault changelog rather than nothing. (source: user decision, this conversation)
- O2: Should CI change? → **No.** The track must still terminate in a real reviewer PASS so `ready-to-merge` flows through the existing single code path in `agents/orchestrator.md:152-154`. `sdd-review-gate.yml` stays strict and untouched. A CI-side escape-hatch label was considered and rejected — it would weaken server-side enforcement and introduce a label no review PASS backs. (source: user decision, this conversation)
- O3: Should the currently-failing PR (`make-squid-great-again` #2) be unblocked as part of this? → **No.** That is a genuine code PR awaiting its feature review; it is blocked correctly, not by this gap. Out of scope. (source: user decision, this conversation)
- O4: Should this change be made directly or through the SDD pipeline? → **Through the pipeline**, matching how `github-agent` was built in this repo. The change alters agent contracts and needs tests. (source: user decision, this conversation)
- O5: Which evidence signals may establish that a feature's tasks produced an artifact (the FR-6.4 attribution question)? → **All five are in play**, and this is a requirements-level decision, settled before any design is written. The five: (1) the git diff, (2) the task's `**Files:**` declaration, (3) the executor's completion summary, (4) C1 item 3's task-body/sub-tasks fallback, and (5) **commit provenance**. Amendment A5 part 5's trilemma — that the attribution rule must re-open either BB1 (a false-FAIL reinstating the exact deadlock O1 exists to remove) or BB2 (a false-PASS reaching `ready-to-merge`) — was derived under two unstated constraints: that only signals (1)-(3) were available, and that commit archaeology was forbidden to it. Both constraints are lifted here. The trilemma therefore does **not** carry over as a proven impossibility; requirements-agent must re-derive it against all five signals and state plainly whether it still binds. (source: user decision, restart conversation 2026-08-09; postmortem §6.2 item 1, §3.2, and finding `F16`)

## Restart provenance (read before authoring anything)

This feature is a **restart**. A first attempt ran 4 of 11 tasks and was retired on 2026-08-09
(revert commit `41880b7`, merged as PR #7 / `e784b2c`). It was retired for the cost of its own
correction chain, not because the work was wrong — one requirement, FR-6.4, consumed five design
amendments and four adversarial audits, and `design.md` reached 2723 lines.

- **The postmortem is a required input:** `.specs/retrospectives/non-code-feature-track.md`.
  §3 carries the technical knowledge (the C0 allow-list asymmetry, the FR-6.4 attribution problem,
  the three residuals, two places where the shipped behaviour beat its design); §6 carries the
  binding restart recommendations. `.specs/steering/process-lessons.md` distils nine hard rules
  from it and is loaded every session.
- **Sections O1-O4 and D1-D2 above are restored byte-identical from the retired attempt.** They
  survived five amendments and three adversarial audits untouched. Re-derive the design; do not
  re-litigate the scope. O5 is the one addition, and it is a decision the postmortem explicitly
  says must be taken here rather than in design.
- **BB1 and BB2 must not be reintroduced.** The retired attempt's own argument against restarting
  was that a fresh author would not know about them. Any author on this restart does — read §3.2
  before writing the attribution rule.
- **Finding F2 is already fixed upstream, not by this feature.** `agents/tasks-agent.md` Task
  Design Rule 5 no longer forbids non-code tasks; the fix and its mutation-verified pin landed on
  a separate chore branch (`chore/pre-restart-framework-fixes`, PR #8). Do not re-fix it and do
  not claim it as a task of this feature.
- **The three `Edit` tool grants are retained deliberately** (`bed2877`, `7e5270e`), verified
  present at line 10 of `agents/{design,requirements,tasks}-agent.md` in both the repo and the
  `~/.claude` live copies. Do not re-grant them and do not revert them.
- **Prior working artifacts survive** in this feature's gitignored `spec-memory/` (48 reports from
  the retired attempt, including the retired `.spec-state.json` as
  `retired-attempt1-spec-state.json`) and out of repo at `~/sdd-knowledge-backup-2026-08-09`.
  Postmortem §7.2 indexes which file answers which question.
- **The task ordinals of the retired attempt are cited externally** — from `design.md`,
  `.spec-state.json`, PR #5 comment `5227495349`, and the whole audit chain. If this restart
  reuses or collapses them, §6.2 item 11 applies: absorb with retained sub-task identifiers and
  explicit ABSORBED-INTO markers, never renumber and never delete.

## Discrepancies reconciled
- D1: "Non-code" is not one thing — a recon write-up commits markdown to the repo, while a vault update commits (almost) nothing and mutates a tree outside it. → Treat them as one track with two sub-shapes; the classification must key on *what the tasks produce*, not on whether the git diff happens to be empty, because an empty in-repo diff and a docs-only in-repo diff both need to reach PASS.
- D2: Tests-optional risks becoming a loophole a code feature could slip through. → Classification must be explicit and recorded in `.spec-state.json`, and a non-code feature that turns out to touch application code must fall back to the full code path rather than keeping its exemption.

## Scope boundaries
- In v1:
  - Orchestrator: classify the feature (code-bearing vs non-code), record it in `.spec-state.json`, and route the per-task pipeline and the feature-review gate accordingly.
  - `task-validator`: artifact-conformance mode — validate the produced artifacts against cited requirements; missing unit tests are not a FAIL when the task produces no code.
  - `task-tester`: defined behaviour when there is nothing to unit-test.
  - `code-reviewer` + `security-reviewer`: a defined, emittable verdict for empty or non-code scope, with the review re-pointed at spec artifacts, committed docs, and the vault changelog.
  - Tests in `tests/` covering the new agent-contract text, mirroring the existing `test_orchestrator_label_lifecycle.py` / `test_github_agent_def.py` pattern.
  - Docs: `CLAUDE.md` (both copies are kept in sync by hand) and `README.md` where they describe the pipeline stages.
- Deferred:
  - Any change to `ci-templates/workflows/sdd-review-gate.yml` or the label vocabulary.
  - Retro-unblocking existing PRs.
  - Automatic detection of vault mutations for audit purposes beyond what `vault-writer`'s changelog already records.

## Cross-cutting rules
- The invariant holds: `ready-to-merge` is applied in exactly one place, only after a whole-feature review PASS. The non-code track produces a *real* PASS; it never bypasses the gate.
- No agent gains a new tool or a new write target.
- `sdd-review-gate.yml` is not modified.
- Changes are to agent definitions (markdown contracts) plus tests — this repo's "code" is largely prose, which makes it an instance of the very problem being fixed; the feature itself is code-bearing (it adds tests), so it runs the normal path.

## Sources consulted
- `agents/orchestrator.md` (lines 139-179, 254-288, 359-363), `agents/task-validator.md`, `agents/code-reviewer.md`, `agents/security-reviewer.md`
- `ci-templates/workflows/sdd-review-gate.yml`
- Failing run: https://github.com/jamie-zaikov/make-squid-great-again/actions/runs/30868636491 (PR #2, `sdd-review-gate` — "the 'ready-to-merge' label is required")
- Prior art in this repo: `.specs/features/github-agent/` (requirements/design/tasks shape), `tests/test_orchestrator_label_lifecycle.py`
