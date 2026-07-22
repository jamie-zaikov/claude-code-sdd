# Tasks: github-agent

<!-- Owned by the tasks-agent. Derived from the confirmed requirements.md and design.md. -->

## Overview

10 top-level tasks implement the `github-agent` scribe, its orchestrator lifecycle
integration, the CI enforcement layer (shared secret scanner, three GitHub Actions workflow
templates, a pre-push hook), the `install.sh` and `/sdd-init` distribution paths, the dogfood
instantiation in this repo's `.github/`, the `secret-guard.py` extension, and the documentation
updates. Tasks are ordered by dependency: the agent definition precedes the orchestrator wiring
that invokes it; the shared secret scanner precedes the CI workflow and pre-push hook that both
call it; distribution and dogfood follow the templates they ship; docs come last.

### How to read this list

Each top-level task is a single coherent component or concern, sized for the per-task
Execute → Test → Validate → Code Review → Security Review pipeline. Every task and every
meaningful sub-task cites the requirement IDs it satisfies. The final sub-task of each task is
always its test task. A traceability table at the end confirms every FR-1…FR-24 and NFR-1…NFR-8
is covered.

### Bootstrapping note (context, not a task)

`github-agent` is the artifact this feature *builds*; it does not exist while this feature is
being developed, so the orchestrator lifecycle hooks (FR-7…FR-12) are **not active for this
feature's own development** — they go live only for *future* features once this feature ships.
Do NOT create or expect any task here to invoke `github-agent`, run `gh`, push a branch, or open
a pull request: this feature's own commits and its first pull request into `main` are handled
normally by a **human** during development. The tasks below produce the definitions, templates,
scripts, and docs; they are exercised for real only from the next feature onward (design Flow A).

---

## Task 1: `agents/github-agent.md` — the scribe agent definition (C1)
- [ ] 1. Author the `github-agent` agent definition as an audited remote choke-point scribe.

**Description:** Create `agents/github-agent.md`, mirroring `agents/vault-writer.md`'s structure
and tone — a leaf scribe invoked only by the orchestrator that performs remote git/GitHub
mechanics and transcribes existing verdicts, never authoring content, judging quality, or merging.
Encode the invocation contract (D1), the return contract (D2), the label/branch vocabulary (D3),
and the "use, don't read" authentication rules.

**Sub-tasks:**
- [ ] 1.1. Write valid agent frontmatter (`name`, `description`, `tools`, `model`) consistent with
  the fleet: `tools: Read, Glob, Grep, Bash` — deliberately **no `Write`/`Edit`** (remote-only
  mechanics, DD-3) and **no `Agent`** (leaf, cannot delegate); `model: sonnet`;
  `user-invocable: false`. (FR-1, FR-1.1, FR-1.2, FR-1.3)
- [ ] 1.2. Write the *Charter* and *Rules* sections: scribe-not-author; the single audited
  choke-point that is the only component that runs `gh`/`git push`; publishes upstream-authored
  content verbatim. (FR-2, FR-2.2, NFR-4)
- [ ] 1.3. Write the *Permitted operations* section (create/switch branch, commit, push to a
  **non-protected** feature branch, open PR, update PR incl. draft toggle, post PR comment,
  set/clear label), with deterministic branch derivation `feature/<feature-name>` and draft PRs
  for features under active development. (FR-3, FR-3.1, FR-3.2, D3)
- [ ] 1.4. Write the *Prohibited operations* section: refuse-and-report (as `GITHUB BLOCKED`) any
  request to merge, force-push to a protected branch, or delete a branch; also refuse to produce
  its own PASS/FAIL judgement. (FR-4, FR-4.1, FR-4.2, FR-4.3, FR-2.1, NFR-1)
- [ ] 1.5. Write the *Authentication — `gh` under "use, don't read"* section: run `gh` and let it
  read `GH_TOKEN`/`GITHUB_TOKEN`, reference by env-var name only; never `gh auth token`/`printenv`/
  `env`/`set -x`; halt with `SECRET REQUEST: <need>` when neither var is set; halt with a clear
  missing-dependency report if `gh` is absent; report auth state as presence + var name only.
  (FR-5, FR-5.1, FR-5.2, FR-5.3, NFR-2, NFR-6)
- [ ] 1.6. Write the *Verdict transcription* section: transcribe task-validator / code-reviewer /
  security-reviewer verdicts **verbatim** (stage, PASS/FAIL, findings summary) into a PR comment,
  each attributed to its originating stage for auditability. (FR-6, FR-6.1, NFR-8)
- [ ] 1.7. Write the *On Invocation* (D1 request vocabulary) and *Return Contract* (D2
  `GITHUB DONE` / `GITHUB BLOCKED`, plus the bare `SECRET REQUEST` / missing-`gh` halts) sections.
  (FR-3, FR-4, FR-5.1, FR-6, D1, D2, NFR-6, NFR-8)
- [ ] 1.8. Structural test: assert the file parses as valid YAML frontmatter + markdown body;
  `tools` contains exactly `Read/Glob/Grep/Bash` and excludes `Write`, `Edit`, and `Agent`;
  `user-invocable: false` and `model: sonnet` are set; the Charter, Permitted, Prohibited,
  Authentication, Verdict-transcription, Invocation, and Return-Contract sections are all present.
  (No unit tests — this is a markdown/config artifact; the "test" is a frontmatter + structure lint.)

**Requirements:** FR-1, FR-1.1, FR-1.2, FR-1.3, FR-2, FR-2.1, FR-2.2, FR-3, FR-3.1, FR-3.2, FR-4,
FR-4.1, FR-4.2, FR-4.3, FR-5, FR-5.1, FR-5.2, FR-5.3, FR-6, FR-6.1, NFR-1, NFR-2, NFR-4, NFR-6, NFR-8
**Design Reference:** C1; contracts D1, D2, D3; DD-3
**Files:** `agents/github-agent.md` (new)

---

## Task 2: Orchestrator lifecycle integration (C2)
- [ ] 2. Wire `github-agent` into `agents/orchestrator.md` at the existing lifecycle gates.

**Description:** Add a "GitHub Integration (remote choke-point)" subsection to
`agents/orchestrator.md` (parallel to its "Vault Access" and "Secret Handling" subsections) and
targeted invocation lines at the exact lifecycle points, so the orchestrator is the sole invoker
of `github-agent` and authors/relays every piece of content it publishes. Depends on Task 1 (the
agent must exist before the orchestrator references it).

**Sub-tasks:**
- [ ] 2.1. On feature scaffold: invoke `github-agent` to `push` the deterministically-named feature
  branch to the remote with upstream set. (FR-7, FR-3.1)
- [ ] 2.2. On each planning-phase confirmation (requirements/design/tasks): invoke `commit-push` of
  the confirmed artifact, and on the **first** confirmation also `open-pr` as **draft**. (FR-8, FR-3.2)
- [ ] 2.3. On a per-task full-pipeline pass (validator PASS + both reviewers PASS): invoke
  `commit-push` of the task's changes, then `comment` with the three verbatim, stage-attributed
  verdict blocks. (FR-9, FR-6, FR-6.1, NFR-8)
- [ ] 2.4. In the Feature Review Gate on whole-feature review PASS: invoke `label set ready-to-merge`
  and `request-review` from a human — asserting the ordering that `ready-to-merge` is set only here
  and never earlier. (FR-10, FR-10.1, NFR-1, NFR-8)
- [ ] 2.5. On any blocking finding at any stage or in feature-review: invoke `label set blocked:<stage>`
  and keep the PR in draft; on resolution invoke `label clear blocked:<stage>`. (FR-11, FR-11.1, D3, NFR-8)
- [ ] 2.6. Document the human merge gate in the `complete` phase (report "ready for human merge",
  never merge) and specify that a `SECRET REQUEST` / missing-`gh` / `GITHUB BLOCKED` return from
  `github-agent` is handled via the existing Secret-Handling machinery (surface, provision, re-invoke;
  never read the secret; never work around a block). (FR-12, FR-4.1, NFR-1, NFR-2)
- [ ] 2.7. Structural test: assert `agents/orchestrator.md` still parses as valid markdown; the new
  GitHub Integration subsection and each lifecycle invocation (scaffold, phase-confirm, per-task,
  feature-review PASS, blocking finding + clear, complete) are present; the file states the
  orchestrator never runs `gh`/`git push` itself. (Markdown/config artifact — structural lint, not unit tests.)

**Requirements:** FR-7, FR-8, FR-9, FR-10, FR-10.1, FR-11, FR-11.1, FR-12, NFR-1, NFR-2, NFR-8
**Design Reference:** C2; contracts D1, D3
**Files:** `agents/orchestrator.md` (modify)

---

## Task 3: `secret-guard.py` extension — GitHub-token dump vectors (C6)
- [ ] 3. Extend `hooks/secret-guard.py` to deny GitHub-token dump vectors without over-blocking `gh`.

**Description:** Add targeted patterns to `hooks/secret-guard.py`'s `is_blocked` that deny commands
which would print a GitHub token, while leaving sanctioned `gh` use untouched. Reuse the existing
shared `DENY_REASON` so messaging stays uniform. Independent of the other tasks.

**Sub-tasks:**
- [ ] 3.1. Add a `GH_TOKEN_DUMP` pattern matching `gh auth token` (and its argument variants) — the
  canonical GitHub-token print command. (FR-22.1, FR-5.2)
- [ ] 3.2. Add explicit coverage for env-print vectors keyed to `GH_TOKEN`/`GITHUB_TOKEN` that the
  base `PRINTENV` regex misses — `echo "$GH_TOKEN"`, `echo ${GITHUB_TOKEN}`, `printf` of those vars,
  etc. (FR-22.2, FR-5.2)
- [ ] 3.3. Route the new blocks through the existing shared `DENY_REASON` pointing at "use, don't
  read" and `SECRET REQUEST`. (FR-22.3, NFR-2)
- [ ] 3.4. Ensure sanctioned token *use* is NOT matched: `gh pr create`, `gh pr comment`,
  `gh pr edit`, `gh label`, `gh api` mutations pass through. (FR-22.4)
- [ ] 3.5. Test (unit): `py_compile` the file; assert `is_blocked` returns True for `gh auth token`,
  `echo "$GH_TOKEN"`, `printf '%s' "$GITHUB_TOKEN"`, and `printenv GITHUB_TOKEN`; assert it returns
  False for `gh pr create ...`, `gh pr comment ...`, `gh label add ...`, and `gh api ...`; assert
  the deny reason text is the shared "use, don't read" / `SECRET REQUEST` message. (FR-22, NFR-2)

**Requirements:** FR-22, FR-22.1, FR-22.2, FR-22.3, FR-22.4, FR-5.2, NFR-2
**Design Reference:** C6
**Files:** `hooks/secret-guard.py` (modify)

---

## Task 4: Shared secret scanner `ci-templates/scripts/sdd-secret-scan.py` (C3 / DD-2)
- [ ] 4. Build the shared Python secret scanner reused by both the CI secret-scan job and the pre-push hook.

**Description:** Create `ci-templates/scripts/sdd-secret-scan.py`, a standalone scanner that reuses
`hooks/secret-redact.py`'s proven secret-shaped regex family (AWS/GitHub/GitLab/Slack/Google/Stripe
tokens, JWTs, private-key blocks, secret-shaped `key=value` pairs) and scans a changed range. It is
the single implementation both CI (Task 5) and the pre-push hook (Task 6) call, guaranteeing CI
mirrors local by construction (no new external dependency such as gitleaks). Build before Tasks 5
and 6, which depend on it.

**Sub-tasks:**
- [ ] 4.1. Implement scanning over a changed range: accept a git diff range (e.g. against the PR
  base, or the pushed range) and scan the added/changed content for secret matches. (FR-13, FR-16)
- [ ] 4.2. Reuse the `secret-redact.py` regex family for detection so local and CI logic are
  identical. (FR-16, NFR-3, DD-2)
- [ ] 4.3. Exit **non-zero** when any secret is detected and zero when clean; on a match report by
  **type and `path:line`, never the value**, consistent with the secret-handling reporting rule.
  (FR-13, NFR-2)
- [ ] 4.4. Test (unit): `py_compile` the file; feed fixture content containing each secret family
  and assert a non-zero exit and that the report contains the type and `path:line` but **not** the
  secret value; feed clean content and assert a zero exit. (FR-13, NFR-2, NFR-3)

**Requirements:** FR-13, FR-16, NFR-2, NFR-3
**Design Reference:** C3 (scanner); DD-2
**Files:** `ci-templates/scripts/sdd-secret-scan.py` (new)

---

## Task 5: CI GitHub Actions workflow templates (C3 / DD-1)
- [ ] 5. Author the three one-file-per-gate workflow templates: secret-scan, review-gate, build/test/lint.

**Description:** Create `ci-templates/workflows/sdd-secret-scan.yml`, `sdd-review-gate.yml`, and
`sdd-build-test-lint.yml` — one file per gate (DD-1) so a future `sdd-spec-lint.yml` drops in with
no edits and `/sdd-init`'s per-file add/skip stays trivial. All share the common trigger block
(PR to `main` + push to feature branches). Depends on Task 4 (the secret-scan workflow invokes the
shared scanner).

**Sub-tasks:**
- [ ] 5.1. `sdd-secret-scan.yml`: a `secret-scan` job that checks out with enough history to diff,
  then runs the shared `sdd-secret-scan.py` over the changed range and fails the check on detection.
  (FR-13, FR-16, NFR-3)
- [ ] 5.2. `sdd-review-gate.yml`: a `review-gate` job that runs only on `pull_request` events
  targeting `main`, reads the PR labels from the event payload with an inline step (no external
  action), and **fails** unless `ready-to-merge` is present **and** no `blocked:*` label remains;
  it is a no-op on push-to-feature-branch events. This is the server-side enforcement of the human
  merge gate. (FR-14, FR-12, NFR-1, NFR-3)
- [ ] 5.3. `sdd-build-test-lint.yml`: a `build-test-lint` job that runs `scripts/ci.sh` if the
  project provides one, else prints a clear "not configured" notice and exits successfully; fails
  on any check failure. (FR-15, FR-16, NFR-3)
- [ ] 5.4. Give every `sdd-*.yml` the shared trigger block (`pull_request` on `main`;
  `push` `branches-ignore: [main]`) and the common `sdd-` naming so a deferred spec-lint job slots
  in by copying the pattern. (FR-16.1, FR-19)
- [ ] 5.5. Test (structural): assert each file is valid YAML (and passes actionlint if available);
  the trigger block matches the spec; there is exactly one gate per file; the review-gate condition
  requires `ready-to-merge` and forbids `blocked:*`; the secret-scan job references
  `sdd-secret-scan.py`. (Config artifact — YAML/workflow lint, not unit tests.)

**Requirements:** FR-13, FR-14, FR-15, FR-16, FR-16.1, FR-19, FR-12, NFR-1, NFR-3
**Design Reference:** C3; DD-1, DD-2
**Files:** `ci-templates/workflows/sdd-secret-scan.yml`, `ci-templates/workflows/sdd-review-gate.yml`,
`ci-templates/workflows/sdd-build-test-lint.yml` (new)

---

## Task 6: Pre-push git hook template (C4)
- [ ] 6. Author the reusable `ci-templates/hooks/pre-push` hook as the advisory local fast-feedback layer.

**Description:** Create `ci-templates/hooks/pre-push`, a POSIX shell hook that, before a push, runs
(a) the shared `sdd-secret-scan.py` over the range being pushed and (b) the project's `scripts/ci.sh`
build/test/lint entrypoint if present, blocking the push on any failure. It begins with a sentinel
comment line (e.g. `# >>> sdd-pre-push (managed) >>>`) so installers can detect an SDD-managed hook
and stay idempotent. Depends on Task 4 (calls the shared scanner). It is advisory; CI (Task 5) is the
mandatory backstop.

**Sub-tasks:**
- [ ] 6.1. Run the shared `sdd-secret-scan.py` and `scripts/ci.sh` (when present) over the pushed
  range, invoking the **same** scripts CI uses so the two cannot drift. (FR-17, FR-16, NFR-3)
- [ ] 6.2. On any failing check, exit non-zero to block the push and print a message naming the
  failing check and how to re-run it. (FR-17.1)
- [ ] 6.3. Add the SDD sentinel comment line for idempotent install detection, and author the file
  as a reusable template. (FR-19; supports NFR-5 install idempotence)
- [ ] 6.4. Test (structural): `bash -n` (and shellcheck if available) the hook; assert the sentinel
  line is present; assert that a simulated failing check causes a non-zero exit with a message
  naming the check; assert it references `sdd-secret-scan.py`. (Shell artifact — `bash -n`/shellcheck,
  not unit tests.)

**Requirements:** FR-17, FR-17.1, FR-16, FR-19, NFR-3
**Design Reference:** C4 (hook template); DD-2
**Files:** `ci-templates/hooks/pre-push` (new)

---

## Task 7: `install.sh` pre-push hook installation (C4 / DD-4)
- [ ] 7. Add a prompted, idempotent, skippable pre-push hook install step to `install.sh`, mirroring the secret-handling opt-in.

**Description:** Extend `install.sh` with a new prompted block mirroring the existing
"Secret-handling safeguards" opt-in (the `read -rp ... (y/N)` pattern). On opt-in it installs
`ci-templates/hooks/pre-push` into the current repo's hooks dir (resolved via
`git rev-parse --git-path hooks`) using sentinel-based idempotence and non-destructive handling of a
pre-existing non-SDD hook, and copies the hook template + shared scanner into `~/.claude/` so
`/sdd-init` can distribute them downstream without a source clone. Installing into this repo is the
hook side of the FR-21 dogfood (DD-4). Depends on Task 6 (the hook template must exist).

**Sub-tasks:**
- [ ] 7.1. Add the prompt ("Install the SDD CI pre-push hook into this repository? (y/N)") reusing
  the existing `python3`-availability guard; on decline, skip and continue without error. (FR-18,
  FR-18.1)
- [ ] 7.2. On opt-in, resolve the repo hooks dir and install the hook: copy + `chmod +x` when no
  `pre-push` exists; when an SDD-sentinel `pre-push` exists, skip if identical / update if changed
  (idempotent); when a non-sentinel user hook exists, do **not** overwrite — warn with manual-merge
  guidance. (FR-18, NFR-5)
- [ ] 7.3. Copy `ci-templates/hooks/pre-push` and `ci-templates/scripts/sdd-secret-scan.py` into
  `~/.claude/` alongside the secret hooks so `/sdd-init` can distribute them downstream. (FR-21;
  supports FR-20)
- [ ] 7.4. Test: `bash -n` (and shellcheck if available) on `install.sh`; verify idempotence by
  running the hook-install logic twice and asserting the same result with no duplication; verify the
  decline path skips cleanly; verify a pre-existing non-sentinel hook is not overwritten. (FR-18,
  FR-18.1, NFR-5)

**Requirements:** FR-18, FR-18.1, FR-21, NFR-5
**Design Reference:** C4 (install.sh integration); DD-4
**Files:** `install.sh` (modify)

---

## Task 8: `/sdd-init` template distribution (C5)
- [ ] 8. Extend `commands/sdd-init.md` to drop the CI workflow and hook templates into downstream projects non-destructively.

**Description:** Add a "CI templates" section to `commands/sdd-init.md` applying the identical
append/skip discipline the command already uses for its `.gitignore` merge. It creates
`.github/workflows/` if absent, adds each `sdd-*.yml` template that is missing (skip + report if a
file of that name already exists), drops the shared `sdd-secret-scan.py` into a conventional project
location the workflows reference, and makes the pre-push hook available (copied to a documented
location with activation guidance), using the same sentinel-based idempotence. Reads templates from
the `~/.claude/` copies installed by Task 7. Depends on Tasks 5, 6, 7 (the templates and their global
copies must exist).

**Sub-tasks:**
- [ ] 8.1. Document creating `.github/workflows/` and adding each `sdd-*.yml`: create if missing,
  **do not overwrite** an existing file of that name (skip + report), and drop the shared scanner
  into a conventional project path the workflows reference. (FR-20, FR-20.1, FR-19)
- [ ] 8.2. Document making the pre-push hook available (copy to a documented location + activation
  guidance via `git config core.hooksPath` or `.git/hooks/`), opt-in like the secret-handling flow,
  with sentinel-based idempotence. (FR-20, FR-19, NFR-5)
- [ ] 8.3. State that running `/sdd-init` more than once produces the same result (each file added
  or skipped independently, append-only), and that a future `sdd-spec-lint.yml` is picked up
  automatically once it exists in the templates. (NFR-5; DD-1 spec-lint drop-in)
- [ ] 8.4. Test (structural): assert `commands/sdd-init.md` parses as valid markdown and the CI
  templates section documents (a) per-file create-or-skip for workflows, (b) the shared scanner
  drop, (c) hook availability + activation, and (d) idempotent, non-destructive, no-overwrite
  behaviour. (Command spec is markdown instructions — structural check, not unit tests.)

**Requirements:** FR-19, FR-20, FR-20.1, NFR-5
**Design Reference:** C5; DD-1
**Files:** `commands/sdd-init.md` (modify)

---

## Task 9: Dogfood CI workflows into this repo's `.github/` (FR-21)
- [ ] 9. Instantiate the three workflow templates and shared scanner into this repository's own `.github/`.

**Description:** Copy the `ci-templates/workflows/sdd-*.yml` templates into this repo's
`.github/workflows/` and place the shared `sdd-secret-scan.py` where those workflows reference it, so
the SDD framework repo enforces the same gates it ships. Provide a concrete `scripts/ci.sh` for this
repo's `build-test-lint` job that runs the framework's own checks — `python3 -m py_compile` on the
hook scripts, a `secret-guard.py`/`secret-redact.py` smoke test (per `hooks/README.md`), and
`bash -n`/shellcheck on `install.sh`. Depends on Tasks 4 and 5 (templates and scanner must exist);
the hook side of dogfood is handled by Task 7.

**Sub-tasks:**
- [ ] 9.1. Create `.github/workflows/sdd-secret-scan.yml`, `sdd-review-gate.yml`, and
  `sdd-build-test-lint.yml` in this repo from the templates, and place `sdd-secret-scan.py` at the
  path the workflows reference. (FR-21, FR-16.1)
- [ ] 9.2. Add `scripts/ci.sh` running this repo's own build/test/lint (py_compile of hook scripts,
  guard/redact smoke test, `bash -n`/shellcheck of `install.sh`) so the dogfood build-test-lint job
  is concrete. (FR-21, FR-15)
- [ ] 9.3. Test (structural): assert each instantiated `.github/workflows/*.yml` is valid YAML with
  the correct triggers; assert `scripts/ci.sh` passes `bash -n`/shellcheck and, when run, exits zero
  on the current clean tree. (Config/shell artifacts — YAML lint + `bash -n`, not unit tests.)

**Requirements:** FR-21, FR-16.1, FR-15
**Design Reference:** C3 (dogfood instantiation)
**Files:** `.github/workflows/sdd-secret-scan.yml`, `.github/workflows/sdd-review-gate.yml`,
`.github/workflows/sdd-build-test-lint.yml`, `.github/scripts/sdd-secret-scan.py` (or the referenced
path), `scripts/ci.sh` (new)

---

## Task 10: Documentation updates — CLAUDE.md (both) + README (C7)
- [ ] 10. Update both `CLAUDE.md` files and the `README` to describe `github-agent` and the CI enforcement layer.

**Description:** Update the Agent Ownership section of the project `CLAUDE.md` (repo root) and the
global `~/.claude/CLAUDE.md` (kept in sync per the repo↔global convention) to add `github-agent`,
and update `README.md` to describe the agent and CI layer. Done last, after the artifacts they
describe exist. All prose authored in English (NFR-7).

**Sub-tasks:**
- [ ] 10.1. In **both** `CLAUDE.md` files' Agent Ownership section, add a `github-agent` bullet
  (audited remote choke-point scribe — branch/commit/push/PR/label mechanics + verdict
  transcription; never merges, never authors), add the line that `github-agent` is the only
  component that runs `gh`/`git push`, and preserve the "No agent modifies another agent's artifact"
  invariant. (FR-23, FR-23.1, NFR-4)
- [ ] 10.2. Optionally add a short "GitHub Integration" note in the phase-gates narrative of both
  `CLAUDE.md` files describing the human merge gate and `ready-to-merge` / `blocked:*` semantics,
  consistent with the existing Secret-Handling / Knowledge-Vault subsections. (FR-23, FR-24)
- [ ] 10.3. In `README.md`, add `github-agent.md` to the `agents/` listing and the `~/.claude/agents/`
  tree (bumping the agent counts), add a `ci-templates/` entry to the "What's Included" tree, and add
  a subsection describing the agent, the three workflow gates, the pre-push hook, the human merge
  gate, the label semantics, the `/sdd-init` distribution + this-repo dogfood, and that CI mirrors and
  never replaces the local gates. (FR-24, NFR-3)
- [ ] 10.4. Test (structural): assert both `CLAUDE.md` files and `README.md` are valid markdown; the
  `github-agent` ownership bullet and the "only component that runs `gh`/`git push`" line appear in
  both `CLAUDE.md` files and the invariant line is preserved; the README subsection covers the agent,
  the three gates, the hook, the merge gate, and the label semantics; the two `CLAUDE.md` Agent
  Ownership sections are consistent with each other; prose is English. (Docs are markdown —
  structural/consistency check, not unit tests.) (FR-23, FR-24, NFR-4, NFR-7)

**Requirements:** FR-23, FR-23.1, FR-24, NFR-3, NFR-4, NFR-7
**Design Reference:** C7
**Files:** `CLAUDE.md` (repo root, modify), `~/.claude/CLAUDE.md` (modify), `README.md` (modify)

---

## Requirement Coverage

| Requirement | Task(s) |
|-------------|---------|
| FR-1        | Task 1 |
| FR-1.1      | Task 1 |
| FR-1.2      | Task 1 |
| FR-1.3      | Task 1 |
| FR-2        | Task 1 |
| FR-2.1      | Task 1 |
| FR-2.2      | Task 1 |
| FR-3        | Task 1 |
| FR-3.1      | Task 1, Task 2 |
| FR-3.2      | Task 1, Task 2 |
| FR-4        | Task 1 |
| FR-4.1      | Task 1, Task 2 |
| FR-4.2      | Task 1 |
| FR-4.3      | Task 1 |
| FR-5        | Task 1 |
| FR-5.1      | Task 1 |
| FR-5.2      | Task 1, Task 3 |
| FR-5.3      | Task 1 |
| FR-6        | Task 1, Task 2 |
| FR-6.1      | Task 1, Task 2 |
| FR-7        | Task 2 |
| FR-8        | Task 2 |
| FR-9        | Task 2 |
| FR-10       | Task 2 |
| FR-10.1     | Task 2 |
| FR-11       | Task 2 |
| FR-11.1     | Task 2 |
| FR-12       | Task 2, Task 5 |
| FR-13       | Task 4, Task 5 |
| FR-14       | Task 5 |
| FR-15       | Task 5, Task 9 |
| FR-16       | Task 4, Task 5, Task 6 |
| FR-16.1     | Task 5, Task 9 |
| FR-17       | Task 6 |
| FR-17.1     | Task 6 |
| FR-18       | Task 7 |
| FR-18.1     | Task 7 |
| FR-19       | Task 5, Task 6, Task 8 |
| FR-20       | Task 8 |
| FR-20.1     | Task 8 |
| FR-21       | Task 7, Task 9 |
| FR-22       | Task 3 |
| FR-22.1     | Task 3 |
| FR-22.2     | Task 3 |
| FR-22.3     | Task 3 |
| FR-22.4     | Task 3 |
| FR-23       | Task 10 |
| FR-23.1     | Task 10 |
| FR-24       | Task 10 |
| NFR-1       | Task 1, Task 2, Task 5 |
| NFR-2       | Task 1, Task 3, Task 4 |
| NFR-3       | Task 4, Task 5, Task 6, Task 9, Task 10 |
| NFR-4       | Task 1, Task 10 |
| NFR-5       | Task 7, Task 8 |
| NFR-6       | Task 1 |
| NFR-7       | Task 10 (all spec artifacts authored in English; requirements EARS) |
| NFR-8       | Task 1, Task 2 |

All FR-1…FR-24 and NFR-1…NFR-8 are covered by at least one task, and every task cites at least one
requirement. No orphan tasks; no orphan requirements. The deferred **spec-lint** CI job and other
scope-deferred items are intentionally NOT tasked; the one-file-per-gate workflow structure (Task 5,
DD-1) and `/sdd-init`'s per-file add/skip (Task 8) leave room for spec-lint to be added later without
redesign.
