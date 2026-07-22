# Design: github-agent

<!-- This file is owned by the design-agent. Do not edit manually during SDD workflow. -->

## Overview

`github-agent` adds a single audited choke-point that bridges the local Spec-Driven
Development (SDD) lifecycle to GitHub. It is a **scribe** built in the exact shape of the
existing `vault-writer`: a leaf agent (no `Agent` tool, `user-invocable: false`) invoked only
by the orchestrator, that applies the remote mutation it is told to make and returns a short
confirmation. It performs remote git/GitHub mechanics (branch, commit, push, open/update PR,
PR comment, label) but never authors spec content or code, never judges quality, and never
merges. It is the only component in the fleet that runs `gh` or `git push`.

Alongside the agent, the feature ships a **CI enforcement layer** authored as reusable
templates: three GitHub Actions workflow jobs (secret-scan, review-gate, build/test/lint) and a
pre-push git hook, all wired to the same underlying scan/check scripts so CI mirrors — never
replaces — the local gates. `/sdd-init` drops these templates into downstream projects
non-destructively; `install.sh` optionally installs the pre-push hook into the current repo
(mirroring the existing secret-handling opt-in); and the templates are instantiated in this
repo's own `.github/` as dogfood. Finally, `secret-guard.py` is extended to block
GitHub-token dump vectors, and both `CLAUDE.md` files plus the `README` are updated.

The design touches seven areas, each a component below:

1. `agents/github-agent.md` — the scribe agent definition.
2. Orchestrator lifecycle integration — where/how the orchestrator invokes github-agent.
3. CI GitHub Actions workflow templates — secret-scan, review-gate, build/test/lint.
4. Pre-push git hook + `install.sh` integration.
5. `/sdd-init` template distribution mechanism.
6. `secret-guard.py` extension for GitHub-token dump vectors.
7. Documentation updates — README + both `CLAUDE.md` files.

### Bootstrapping caveat (read first)

`github-agent` is the artifact this feature builds; it does **not** exist while this feature is
being developed. Therefore the orchestrator lifecycle hooks (FR-7–FR-12) are **not active for
this feature's own development** — they only go live for *future* features once this feature is
implemented and shipped. This repository's own first pull request for the github-agent feature is
opened by a **human**, not by github-agent. The integration points below are designed as they
will operate for future features; github-agent never invokes itself and is never in the loop for
its own bootstrap PR. See "Deferred hooks / bootstrapping note" at the end.

## Architecture

### Components

#### C1 — `agents/github-agent.md` (the scribe agent)

A new agent definition file matching the frontmatter format, tone, and section conventions of
`agents/vault-writer.md` (the closest analogue — an audited scribe choke-point).

**Frontmatter** (FR-1, FR-1.1, FR-1.2, FR-1.3):

```yaml
---
name: github-agent
description: >
  The single audited choke-point that bridges the local SDD lifecycle to GitHub. Invoked only by
  the orchestrator to perform remote git/GitHub mechanics — create/switch branches, commit, push
  to a feature branch, open and update pull requests (including draft state), transcribe existing
  validator/reviewer verdicts as PR comments, and set/clear labels. A scribe, not an author: it
  never invents spec content or code, never judges quality, and never merges. It is the only agent
  in the fleet that runs `gh` or `git push`.
tools:
  - Read
  - Glob
  - Grep
  - Bash
model: sonnet
user-invocable: false
---
```

- `tools` deliberately **excludes `Agent`** — github-agent is a leaf and cannot delegate
  (FR-1.3), exactly like vault-writer. `Bash` is required because all remote mechanics run
  through the `git` and `gh` CLIs. `Read`/`Glob`/`Grep` let it locate the artifacts and verdict
  text it is asked to publish. No `Write`/`Edit`: it never authors files, it only runs remote
  commands (contrast vault-writer, which does write into the vault).
- `model: sonnet` matches the other non-planning, non-review agents (vault-writer, task-executor
  default).
- `user-invocable: false` (FR-1.2) — only the orchestrator invokes it, mirroring vault-writer.

**Body sections** (mirroring vault-writer's structure):

- *Charter* — "You are the GitHub Agent, the only component allowed to mutate the remote
  (branches, PRs, labels) or run `gh`/`git push`. Every remote change flows through you, so every
  change is deliberate, minimal, and auditable. You are a scribe, not an author: the content you
  publish — commit messages, PR bodies, verdict text, label names — is authored upstream by the
  orchestrator or relayed from a specialist. You place it precisely; you never improve, expand,
  edit, or invent it." (FR-2, FR-2.2, NFR-4)
- *On Invocation* — the invocation contract (see Interfaces / D1 below).
- *Permitted operations* (FR-3): create a branch, switch to a branch, commit, push to a
  **non-protected** feature branch, open a PR, update a PR (including toggling draft state), post
  a PR comment, set or clear a label. Branch names are derived deterministically (FR-3.1); PRs for
  a feature under active development are opened as **draft** (FR-3.2).
- *Prohibited operations* (FR-4): **refuse and report** any request to merge a PR (FR-4.1),
  force-push to a protected branch (FR-4.2), or delete a branch (FR-4.3). The refusal is returned
  to the orchestrator as a `GITHUB BLOCKED` result (see D2). github-agent also refuses to produce
  a quality judgement of its own (FR-2.1) — it only transcribes verdicts already produced by
  task-validator, code-reviewer, or security-reviewer.
- *Authentication — `gh` under "use, don't read"* (FR-5, NFR-2): github-agent authenticates by
  running the `gh` CLI and letting it read the token from `GH_TOKEN` or `GITHUB_TOKEN`, referring
  to the token **only by env-var name**. It never runs `gh auth token`, `printenv`, `env`,
  `set -x`, or authenticated `curl -v`/`-i`, and never echoes/prints/dumps the value (FR-5.2).
  When reporting auth state it reports only presence/absence and the env-var name used, never the
  value (FR-5.3). If **neither** `GH_TOKEN` nor `GITHUB_TOKEN` is set, it halts and returns
  `SECRET REQUEST: <need>` proposing provisioning (operator `export`s it, or drops it in a
  gitignored `.env`), rather than guessing or working around it (FR-5.1). If the `gh` CLI itself
  is not installed/on `PATH`, it halts and reports the missing dependency clearly rather than
  attempting an unauthenticated workaround (NFR-6). This section is copied in spirit from the
  Secret Handling sections already present in the other agents.
- *Verdict transcription* (FR-6): when the orchestrator supplies a completed verdict block from
  task-validator, code-reviewer, or security-reviewer, github-agent transcribes it **verbatim**
  (stage, PASS/FAIL, findings summary) into a PR comment, and attributes each verdict to its
  originating stage/agent so the PR comment is auditable (FR-6.1, NFR-8). It does not summarize,
  re-word, or re-judge. The verdict blocks arrive in the exact format the reviewers already emit
  (e.g. `## Code Review: <task N | feature> — PASS/FAIL`), so transcription is a copy, not a
  transformation.
- *Return Contract* — `GITHUB DONE` / `GITHUB BLOCKED` (see D2), modeled on vault-writer's
  `VAULT WRITE DONE` / `VAULT WRITE BLOCKED`.
- *Rules* — the terse do/don't list: scribe not author; single choke-point for `gh`/`git push`;
  never merge / force-push protected / delete branch; token by env-var name only; `SECRET
  REQUEST` on missing token; leaf, no delegation.

#### C2 — Orchestrator lifecycle integration (`agents/orchestrator.md`)

The orchestrator gains a new subsection, "GitHub Integration (remote choke-point)", parallel to
its existing "Vault Access" and "Secret Handling" subsections, plus targeted invocation lines at
the exact lifecycle points below. The orchestrator is the **only** invoker of github-agent, and
it authors (or relays) every piece of content github-agent publishes. It never runs `gh`/`git
push` itself. The integration points:

| Lifecycle event (existing orchestrator location) | github-agent action | Content the orchestrator passes |
|---|---|---|
| **Feature scaffold** (new feature; branch already created locally by `/sdd-feature`) — FR-7 | `push` the feature branch to the remote and set upstream | `branch` name (deterministic, FR-3.1), `base` (`main`) |
| **Planning phase confirmed** (requirements / design / tasks confirm in Phase Routing) — FR-8 | `commit-push` the confirmed artifact; on the **first** confirmation also `open-pr` as **draft** (FR-3.2) | commit message, changed paths, PR title/body (authored by orchestrator) |
| **Per-task pipeline pass** (validator PASS *and* both reviewers PASS, in `implementation`) — FR-9 | `commit-push` the task's changes, then `comment` the transcribed per-task verdicts | commit message, changed paths, the three verbatim verdict blocks with stage attribution (FR-6, FR-6.1) |
| **Whole-feature review PASS** (both reviewers PASS in `feature-review`) — FR-10 | `label set ready-to-merge` and `request-review` from a human | reviewer handle/team (from steering or user), the `ready-to-merge` label name |
| **Blocking finding** at any pipeline stage or in feature-review — FR-11 | `label set blocked:<stage>` and keep the PR in **draft** | the failing stage name → `blocked:*` label (see D3) |
| **Blocking finding resolved** — FR-11.1 | `label clear blocked:<stage>` | the label to clear |

**Ordering / invariants the orchestrator enforces:**
- The `ready-to-merge` label is applied **only** after a whole-feature review PASS and **never**
  before (FR-10.1). It is set in the `feature-review` → PASS branch of the orchestrator's existing
  Feature Review Gate, not anywhere earlier.
- On any blocking finding the PR stays draft; github-agent is told to keep draft state, not to
  toggle it ready. Draft→ready is a human action gated by the merge rule.
- **Human merge gate** (FR-12, NFR-1): the orchestrator never asks github-agent to merge, and
  github-agent refuses if asked (FR-4.1). Merge to a protected branch is performed by a human and
  is gated by the `ready-to-merge` label — enforced in CI by the review-gate job (C3) and in
  GitHub branch protection. The orchestrator's `complete` phase reports "ready for human merge"
  rather than merging.

The orchestrator handles a `SECRET REQUEST` or missing-`gh` halt from github-agent exactly as it
already handles specialist `SECRET REQUEST`s (its existing "Secret Handling" subsection): surface
the request to the user with the proposed provisioning, never read the secret itself, and
re-invoke github-agent once the env var is set. It handles a `GITHUB BLOCKED` refusal by
reporting it to the user; it does not attempt a workaround.

#### C3 — CI GitHub Actions workflow templates

Templates live in the repo under a new top-level `ci-templates/` directory (paralleling the
existing `steering-templates/` reference-copies convention), instantiated verbatim into a
project's `.github/workflows/` by `/sdd-init` (C5) and dogfooded into this repo's own `.github/`
(FR-21).

```
ci-templates/
  workflows/
    sdd-secret-scan.yml       # FR-13
    sdd-review-gate.yml       # FR-14
    sdd-build-test-lint.yml   # FR-15
  scripts/
    sdd-secret-scan.py        # shared scanner — reused by CI job AND pre-push hook (FR-16, NFR-3)
  hooks/
    pre-push                  # git pre-push hook template (C4, FR-17)
```

**Separate file per concern (design decision DD-1).** Each gate is its own workflow file rather
than one file with three jobs. This makes the deferred **spec-lint** job a pure drop-in — add
`ci-templates/workflows/sdd-spec-lint.yml` later with no edits to the existing files (FR-19,
scope requirement to structure for spec-lint without redesign). It also makes `/sdd-init`'s
non-destructive append trivial: each file is added or skipped independently (C5, FR-20.1). All
files share a common naming prefix (`sdd-`) and a common trigger block so a future job slots in
by copying the pattern.

**Common trigger block (FR-16.1)** — every `sdd-*.yml` uses:

```yaml
on:
  pull_request:
    branches: [ main ]          # PR events targeting the protected branch
  push:
    branches-ignore: [ main ]   # pushes to feature branches, for fast feedback
```

**`sdd-secret-scan.yml` (FR-13).** Job `secret-scan` checks out the repo with enough history to
diff, then runs the shared scanner `ci-templates/scripts/sdd-secret-scan.py` over the changed
range (`git diff` against the PR base, or the pushed range on branch pushes). The scanner reuses
the same secret-shaped regex family as `hooks/secret-redact.py` (AWS/GitHub/Slack/Google/Stripe
tokens, JWTs, private-key blocks, `secret=…` pairs) and **exits non-zero** when a secret is
detected, failing the check (FR-13). Because the *same* script is invoked by the pre-push hook
(C4), CI and local run identical logic (FR-16, NFR-3). The scanner reports a match by **type and
`path:line`, never the value**, consistent with the secret-handling reporting rule.

**`sdd-review-gate.yml` (FR-14).** Job `review-gate` runs only on `pull_request` events targeting
`main`. It reads the PR's labels from the event payload and **fails** unless the `ready-to-merge`
label is present **and** no `blocked:*` label remains. Implemented with a small inline step over
`github.event.pull_request.labels.*.name` (no external action needed), so it enforces the SDD
review gate server-side as the mandatory backstop to github-agent's label-setting (FR-14, NFR-3,
NFR-1). On push-to-feature-branch events it is a no-op/skip (there is no PR label context yet).

**`sdd-build-test-lint.yml` (FR-15).** Job `build-test-lint` runs the project's build, test, and
lint steps and fails on any failure. Because downstream stacks vary, the template invokes a
**conventional entrypoint** — it runs `scripts/ci.sh` if the project provides one, else prints a
clear notice that the project has not configured build/test/lint and exits successfully (a
documented placeholder the downstream fills in). For this repo's dogfood instance the entrypoint
runs the framework's own checks: `python3 -m py_compile` on the hook scripts, a `secret-guard.py`
/ `secret-redact.py` smoke test (the commands already documented in `hooks/README.md`), and a
`bash -n`/shellcheck pass on `install.sh`. This keeps FR-15 concrete for the dogfood repo without
inventing a build system for arbitrary downstream projects.

**Mirrors, never replaces (FR-16, NFR-3).** The secret-scan and build/test/lint checks call the
same scripts the pre-push hook calls locally; the review-gate re-checks server-side the same
label state github-agent maintains locally. Even if the local hook is absent or bypassed, CI
enforces the gates. CI is additive: it never disables or substitutes for the local gate.

#### C4 — Pre-push git hook + `install.sh` integration

**Hook template** `ci-templates/hooks/pre-push` (FR-17): a POSIX shell script that, before a
push, runs (a) the shared secret scanner `sdd-secret-scan.py` over the range being pushed and
(b) the project's `scripts/ci.sh` build/test/lint entrypoint if present. If either check fails,
the hook **exits non-zero to block the push** and prints a message naming the failing check and
pointing at how to re-run it (FR-17.1). It is the advisory fast-feedback layer; CI (C3) is the
mandatory backstop. The hook begins with a sentinel comment line (e.g.
`# >>> sdd-pre-push (managed) >>>`) so installers can detect an already-installed SDD hook and
stay idempotent.

**`install.sh` integration (FR-18, FR-18.1, NFR-5).** Add a new prompted step mirroring the
existing "Secret-handling safeguards" opt-in block (the `read -rp ... (y/N)` pattern at
`install.sh` lines ~173–250):

- Prompt: "Install the SDD CI pre-push hook into this repository? (y/N)".
- On **yes**: resolve the current repo's hooks dir via `git rev-parse --git-path hooks`, then
  install `ci-templates/hooks/pre-push` there:
  - If no `pre-push` exists → copy it and `chmod +x` (installed).
  - If a `pre-push` exists **with the SDD sentinel** → compare; skip if identical, update if
    changed (idempotent — running twice yields the same result, NFR-5).
  - If a `pre-push` exists **without the sentinel** (a user's own hook) → do **not** overwrite;
    warn and print manual-merge guidance (non-destructive, FR-20.1-style behaviour, NFR-5).
- On **no / decline**: skip and continue without error (FR-18.1), matching the secret-handling
  opt-out.
- Because `install.sh` is run from a git clone of this repo, this step installs the hook into
  **this repo** — that is the dogfood path (FR-21 for the hook side). It also copies the hook
  template and scanner into `~/.claude/` (alongside the secret hooks) so `/sdd-init` can
  distribute them downstream without needing the source clone.

This reuses the same `python3`-availability guard the secret-handling block already has (the
scanner is Python), warning and skipping if `python3` is absent.

#### C5 — `/sdd-init` template distribution mechanism

Extend `commands/sdd-init.md` (which today creates `.specs/` dirs, steering templates, and does a
**non-destructive `.gitignore` merge** — "append any missing lines without duplicating") with a
new "CI templates" section that applies the identical append/skip discipline (FR-19, FR-20,
FR-20.1, NFR-5):

- **Workflows.** Create `.github/workflows/` in the downstream project if absent, then for each
  `ci-templates/workflows/sdd-*.yml` file: if the target does not exist, create it from the
  template; if a file of that name already exists, **do not overwrite** — skip and report it,
  consistent with the existing gitignore-merge non-destructive behaviour (FR-20, FR-20.1). Also
  drop the shared `ci-templates/scripts/sdd-secret-scan.py` into a conventional project location
  (e.g. `.github/scripts/` or `scripts/`) the workflows reference.
- **Pre-push hook.** Make the hook **available** for the downstream project: copy
  `ci-templates/hooks/pre-push` into the project (e.g. under `scripts/git-hooks/pre-push` or a
  documented location) and tell the user how to activate it (`git config core.hooksPath` or copy
  into `.git/hooks/`), using the same sentinel-based idempotence as C4. `/sdd-init` makes the hook
  available but, like the secret-handling flow, does not force-activate it — activation stays
  opt-in (FR-20 "make the pre-push hook available").
- The templates `/sdd-init` reads from are the ones installed to `~/.claude/` by `install.sh`
  (C4), so a downstream project needs only the global install, not a clone of this repo.

Because each file is added-or-skipped independently and each merge is append-only, running
`/sdd-init` more than once produces the same result without duplication or overwrite (NFR-5), and
a future `sdd-spec-lint.yml` is picked up automatically once it exists in `ci-templates/`
(spec-lint drop-in path).

#### C6 — `secret-guard.py` extension (GitHub-token dump vectors)

Extend `hooks/secret-guard.py` (PreToolUse, matcher `Bash`) to deny commands that would dump a
GitHub token into context, while leaving sanctioned `gh` use untouched (FR-22). The existing
guard already blocks `printenv`, bare `env`, `set -x`, and dump-tools reading a secret store, and
returns a `DENY_REASON` pointing at "use, don't read" and `SECRET REQUEST`. The extension adds
targeted patterns to `is_blocked`:

- `GH_TOKEN_DUMP` — matches `gh auth token` (and `gh auth token …` variants) — the canonical
  command that prints a GitHub token (FR-22.1).
- Env-print vectors for the token vars (FR-22.2). The current `PRINTENV` regex already catches any
  `printenv …`, so `printenv GH_TOKEN` / `printenv GITHUB_TOKEN` are covered today; the extension
  adds explicit coverage for the analogous vectors the base regex misses — `echo "$GH_TOKEN"`,
  `echo "$GITHUB_TOKEN"`, `echo ${GH_TOKEN}` / `${GITHUB_TOKEN}`, and `printf` of those vars — via
  a new pattern keyed to the `GH_TOKEN`/`GITHUB_TOKEN` names.
- **Deny reason** (FR-22.3): reuse the existing `DENY_REASON` text so it points the agent at the
  "use, don't read" pattern and the `SECRET REQUEST` escalation, consistent with current guard
  messaging. A single shared reason string keeps messaging uniform.
- **Do not over-block** (FR-22.4): the new patterns match only token-**print** commands. Any `gh`
  subcommand that *uses* the token without printing it — `gh pr create`, `gh pr comment`,
  `gh pr edit`, `gh label`, `gh api` for a mutation — is **not** matched and passes through, so
  github-agent's sanctioned operations are never blocked. The new checks follow the guard's
  existing "match a print vector, not a use vector" discipline.

The companion `hooks/secret-redact.py` already redacts `gh[pousr]_…` / `github_pat_…` / `glpat-…`
shaped strings from Bash output, so a token that slips through in output (e.g. a `gh` error dump)
is scrubbed by the existing backstop — no change needed there, but it is the defense-in-depth
partner (NFR-2).

#### C7 — Documentation updates

- **`README.md` (FR-24).** Add `github-agent.md` to the `agents/` listing in "What's Included"
  and to the `~/.claude/agents/` tree in "How It Works" (bumping the "12 agents" counts to 13).
  Add a new subsection (parallel to "Security & secret handling") describing github-agent as the
  audited remote choke-point scribe and the CI enforcement layer: the three workflow gates
  (secret-scan, review-gate, build/test/lint), the pre-push hook, the **human merge gate**, and
  the `ready-to-merge` / `blocked:*` label semantics (FR-24). Add a `ci-templates/` entry to the
  "What's Included" tree and note the `/sdd-init` distribution and dogfood in this repo's
  `.github/`. State that CI mirrors and never replaces the local gates (NFR-3).
- **Both `CLAUDE.md` files (FR-23)** — the project `CLAUDE.md` at repo root and the global one at
  `~/.claude/CLAUDE.md` (kept in sync, per the repo↔global sync convention). In the **Agent
  Ownership** section add a `github-agent` bullet: "the audited remote choke-point scribe —
  performs branch/commit/push/PR/label mechanics and transcribes existing verdicts, never merges,
  never authors content." Add a line stating that **github-agent is the only component that runs
  `gh` or `git push`** (FR-23.1), and preserve the existing invariant line "No agent modifies
  another agent's artifact" (FR-23.1, NFR-4). Optionally add a short "GitHub Integration" note in
  the phase-gates narrative describing the human merge gate and label semantics, consistent with
  the existing Secret-Handling / Knowledge-Vault subsections.

### Data Model

No persistent data store, schema, or migration. The feature's "state" is:
- GitHub-side artifacts (branches, PRs, comments, labels) — owned by GitHub.
- The orchestrator's existing `.spec-state.json` — unchanged in shape; the orchestrator already
  tracks `taskStatus`, `featureReview`, and verdicts there, which are the inputs it relays to
  github-agent. No new state fields are required by this design.

Controlled vocabularies (contracts) are defined in Interfaces below.

### Interfaces

#### D1 — github-agent invocation contract (orchestrator → github-agent)

The orchestrator passes a single structured request. `action` selects the operation; the
remaining fields are the **content authored upstream** that github-agent publishes verbatim.

```
{
  action:   create-branch | switch-branch | commit-push | push | open-pr |
            update-pr | comment | label | request-review,
  feature:  <feature-name>,
  branch:   <branch name, e.g. feature/<feature-name>>,   # deterministic (FR-3.1)
  base:     main,                                          # protected base
  message:  <commit message>,                             # commit-push
  paths:    [ <changed path>, ... ],                       # commit-push (what to stage)
  pr:       { title, body, draft: true|false },            # open-pr / update-pr
  comment:  <verbatim verdict block(s) with stage attribution>,  # comment (FR-6/6.1)
  label:    { op: set|clear, name: ready-to-merge | blocked:<stage> },  # label
  reviewer: <handle-or-team>                               # request-review
}
```

Rules encoded in the agent: for `open-pr` during active development `draft` is `true` (FR-3.2);
`label set ready-to-merge` is honored only when the orchestrator asserts a feature-review PASS
context (the orchestrator enforces FR-10.1 ordering — github-agent does not second-guess but also
never sets it on its own initiative); `action: merge` / force-push / branch-delete requests do
not exist in the vocabulary and any attempt is refused (FR-4).

#### D2 — github-agent return contract (github-agent → orchestrator)

Modeled on vault-writer's `VAULT WRITE DONE` / `VAULT WRITE BLOCKED`:

```
GITHUB DONE
action: <action>
target: <branch | pr#N | comment-url | label>
result: <1–2 lines: what now exists/differs on the remote>
auth: <present via GH_TOKEN | present via GITHUB_TOKEN>   # name only, never the value (FR-5.3)
```

```
GITHUB BLOCKED
action: <action>
reason: <prohibited op (merge/force-push/delete) | missing gh CLI | not a scribe task
         | ambiguous/absent content>
suggestion: <what the orchestrator should do next>
```

On a missing token the agent instead returns a bare `SECRET REQUEST: <need>` line (FR-5.1), and on
a missing `gh` CLI a clear missing-dependency report (NFR-6) — both halt rather than work around.

#### D3 — Label vocabulary and branch naming

- **Labels:** `ready-to-merge` (set only after whole-feature review PASS, FR-10.1); and the
  `blocked:*` family naming the failing stage: `blocked:validation`, `blocked:code-review`,
  `blocked:security-review`, `blocked:feature-review` (FR-11). A blocked label is cleared when its
  condition resolves (FR-11.1).
- **Branch naming (FR-3.1):** default deterministic derivation is `feature/<feature-name>`.
  github-agent uses the exact branch name the orchestrator passes, so it also honors the existing
  `/sdd-feature` convention (`<type>/<slug>`, e.g. `feat/<slug>`) when that is what the orchestrator
  supplies; the point of FR-3.1 is that the name is derived deterministically from the feature
  name, never invented ad hoc.
- **Protected branch:** `main`. Pushes go only to the feature branch; `main` is never pushed to by
  github-agent, and merge into `main` is a human action gated by `ready-to-merge` (FR-12, NFR-1).

## Requirement Traceability

| Requirement | Component(s) | Notes |
|---|---|---|
| FR-1 | C1 | New `agents/github-agent.md`. |
| FR-1.1 | C1 | Valid frontmatter (name/description/tools/model) matching the fleet. |
| FR-1.2 | C1 | `user-invocable: false`, mirrors vault-writer. |
| FR-1.3 | C1 | No `Agent` tool → leaf, cannot delegate. |
| FR-2 | C1, C2 | Scribe charter; orchestrator authors, agent publishes verbatim. |
| FR-2.1 | C1 | Refuses its own PASS/FAIL; only transcribes existing verdicts. |
| FR-2.2 | C1, C7 | Agent states it is the single choke-point; CLAUDE.md restates it. |
| FR-3 | C1, D1 | Permitted-verb list + invocation vocabulary. |
| FR-3.1 | C1, D3 | Deterministic `feature/<name>` derivation. |
| FR-3.2 | C1, C2, D1 | Draft PR on open during active development. |
| FR-4 | C1, D2 | Prohibited ops refused → `GITHUB BLOCKED`. |
| FR-4.1 | C1, C2 | Never merge; human merge gate. |
| FR-4.2 | C1 | Never force-push to protected branch. |
| FR-4.3 | C1 | Never delete a branch. |
| FR-5 | C1 | `gh` reads token from env var, name-only reference. |
| FR-5.1 | C1, D2 | `SECRET REQUEST` halt when neither token var set. |
| FR-5.2 | C1, C6 | No token-dump commands; guard blocks them too. |
| FR-5.3 | C1, D2 | Auth state reported by presence + var name only. |
| FR-6 | C1, C2, D1 | Verbatim verdict transcription into PR comment. |
| FR-6.1 | C1, D1 | Each verdict attributed to its originating stage/agent. |
| FR-7 | C2 | Scaffold → push feature branch. |
| FR-8 | C2 | Phase confirm → commit + first draft PR. |
| FR-9 | C2 | Task pass → commit + verdict comment. |
| FR-10 | C2 | Feature-review PASS → `ready-to-merge` + request human review. |
| FR-10.1 | C2, D3 | Label applied only after feature-review PASS. |
| FR-11 | C2, D3 | Blocking finding → `blocked:*` + keep draft. |
| FR-11.1 | C2, D3 | Clear `blocked:*` on resolution. |
| FR-12 | C2, C3, D3 | Human merge gate; review-gate CI + branch protection enforce. |
| FR-13 | C3 | `sdd-secret-scan.yml` + shared scanner, fails on detection. |
| FR-14 | C3 | `sdd-review-gate.yml` checks labels on PR to `main`. |
| FR-15 | C3 | `sdd-build-test-lint.yml` runs build/test/lint. |
| FR-16 | C3, C4 | Shared scripts → CI mirrors local; never replaces. |
| FR-16.1 | C3 | Trigger on PR-to-protected + push-to-feature. |
| FR-17 | C4 | Pre-push hook runs same secret-scan + build/test/lint. |
| FR-17.1 | C4 | Hook exits non-zero, names failing check. |
| FR-18 | C4 | `install.sh` prompted/idempotent/skippable hook install. |
| FR-18.1 | C4 | Decline → skip without error. |
| FR-19 | C3, C4 | Workflows + hook authored as reusable templates. |
| FR-20 | C5 | `/sdd-init` drops templates, appends missing entries. |
| FR-20.1 | C5 | Existing files not overwritten (append/skip). |
| FR-21 | C3, C4 | Dogfood: instantiate in this repo's `.github/` + repo pre-push. |
| FR-22 | C6 | `secret-guard.py` denies GitHub-token dump vectors. |
| FR-22.1 | C6 | Blocks `gh auth token`. |
| FR-22.2 | C6 | Blocks `printenv`/echo of `GH_TOKEN`/`GITHUB_TOKEN`. |
| FR-22.3 | C6 | Deny reason points at use-don't-read + `SECRET REQUEST`. |
| FR-22.4 | C6 | Sanctioned `gh` use (create/comment/label) not blocked. |
| FR-23 | C7 | Agent Ownership updated in both CLAUDE.md files. |
| FR-23.1 | C7 | "Only component that runs `gh`/`git push`" + artifact invariant. |
| FR-24 | C7 | README describes agent + CI layer + merge gate + labels. |
| NFR-1 | C1, C2, C3, D3 | Least privilege; label-gated human merge. |
| NFR-2 | C1, C6 | No token value ever in context; guard + redact backstops. |
| NFR-3 | C3, C4 | CI is mandatory server-side backstop mirroring local. |
| NFR-4 | C1, C7 | No agent modifies another's artifact; agent owns only its mechanics + templates. |
| NFR-5 | C4, C5 | Idempotent, non-destructive install/init. |
| NFR-6 | C1 | Missing `gh` CLI → clear halt, no unauthenticated workaround. |
| NFR-7 | (all spec docs) | This design and all artifacts authored in English; requirements EARS. |
| NFR-8 | C1, C2, D2, D3 | Verdicts attributed in PR comments; label changes map to lifecycle events. |

No orphan requirements: every FR-*/NFR-* above maps to at least one component. No orphan
components: C1–C7 each trace to at least one requirement.

## Sequence Flows

### Flow A — Future feature lifecycle (how the integration operates once shipped)

1. **Scaffold.** `/sdd-feature <name>` creates specs and the local branch (existing behaviour).
   The orchestrator invokes github-agent `push` → the feature branch is pushed to the remote
   with upstream set (FR-7).
2. **Requirements confirmed.** Orchestrator invokes github-agent `commit-push` (confirmed
   `requirements.md`) and, being the first confirmation, `open-pr { draft: true }` (FR-8, FR-3.2).
3. **Design / tasks confirmed.** Orchestrator invokes `commit-push` for each confirmed artifact
   onto the same draft PR (FR-8).
4. **Per task passes.** After validator PASS + both reviewers PASS, orchestrator invokes
   `commit-push` for the task's changes, then `comment` with the three verbatim verdict blocks,
   each attributed to its stage (FR-9, FR-6, FR-6.1).
5. **Blocking finding (any stage or feature-review).** Orchestrator invokes
   `label set blocked:<stage>` and the PR stays draft (FR-11). When the executor's retry resolves
   it, orchestrator invokes `label clear blocked:<stage>` (FR-11.1).
6. **Whole-feature review PASS.** Orchestrator invokes `label set ready-to-merge` and
   `request-review` from a human (FR-10, FR-10.1). No agent merges.
7. **CI on every push/PR.** `sdd-secret-scan`, `sdd-build-test-lint` run on the branch push;
   `sdd-review-gate` runs on the PR to `main`, passing only when `ready-to-merge` is present and
   no `blocked:*` remains (FR-13–FR-16.1).
8. **Human merge.** A human, seeing green CI (incl. review-gate) and the `ready-to-merge` label,
   merges to `main`. No agent performs the merge (FR-12, NFR-1).

### Flow B — Missing token

github-agent is invoked; neither `GH_TOKEN` nor `GITHUB_TOKEN` is set → it halts with
`SECRET REQUEST: GH_TOKEN or GITHUB_TOKEN not set; export it or add to a gitignored .env` (FR-5.1).
Orchestrator surfaces this to the user (never reading the secret), the user provisions the env
var, orchestrator re-invokes github-agent, which now authenticates via `gh` (value never in
context) (NFR-2).

### Flow C — Local pre-push then CI (mirror)

Developer/agent pushes the feature branch → the pre-push hook runs `sdd-secret-scan.py` and
`scripts/ci.sh`; a failure blocks the push with a message naming the check (FR-17, FR-17.1). If
the hook is absent or `--no-verify` bypasses it, the push still triggers the identical CI jobs,
which fail the check server-side (FR-16, NFR-3).

## Dependencies

- **`gh` CLI** — required for all GitHub operations by github-agent (auth, PR, label, comment).
  Missing → hard halt (NFR-6). Assumed available on the operator's machine and on GitHub-hosted CI
  runners (where `gh` is preinstalled).
- **`git`** — for branch/commit/push (already a universal repo dependency).
- **`GH_TOKEN` / `GITHUB_TOKEN`** — provisioned via the environment (locally by the operator, in
  CI as the built-in `GITHUB_TOKEN` secret). Referenced by name only; never read into context.
- **`python3`** — for the shared `sdd-secret-scan.py` (reused by the pre-push hook and CI) and the
  existing secret hooks. Same availability guard `install.sh` already uses.
- **GitHub Actions** — the CI runtime for the three workflow templates.
- **GitHub branch protection on `main`** — the human merge gate's server-side enforcement partner
  (require the review-gate check + the `ready-to-merge` label before merge). This is a repo
  setting the operator configures; the design relies on it but does not create it in code.
- No new libraries introduced; reuses the existing hook/regex machinery and CLI conventions.

## Risks and Mitigations

- **R1 — github-agent oversteps the scribe role (edits content, judges quality, merges).**
  Mitigation: no `Write`/`Edit`/`Agent` tools; explicit prohibited-verb list; refusal path
  returning `GITHUB BLOCKED`; verdict transcription is verbatim-only; merge is absent from the
  action vocabulary. Mirrors vault-writer's constraints (FR-2, FR-2.1, FR-4).
- **R2 — Token leaks into context.** Mitigation: `gh` reads the token; name-only references;
  `secret-guard.py` extension blocks dump vectors (C6); `secret-redact.py` scrubs output as
  backstop; `SECRET REQUEST` on absence (NFR-2).
- **R3 — Label spoofing bypasses the merge gate** (a human hand-adds `ready-to-merge`). Mitigation:
  the human merge gate is intentionally human-trust-based; CI review-gate + branch protection
  enforce label *presence/absence* mechanically, and the design documents that `ready-to-merge`
  semantically means "feature-review passed." Out-of-band label edits are a human/process concern,
  not something an agent can prevent (documented, not silently assumed).
- **R4 — `/sdd-init` or `install.sh` clobbers user files/hooks.** Mitigation: append/skip
  discipline and sentinel-based idempotence; never overwrite a non-SDD pre-push hook or an
  existing workflow file (FR-20.1, NFR-5).
- **R5 — CI diverges from local checks over time.** Mitigation: CI and the pre-push hook invoke
  the *same* scripts (`sdd-secret-scan.py`, `scripts/ci.sh`), so they cannot drift by construction
  (FR-16, NFR-3).
- **R6 — Bootstrapping confusion** (expecting github-agent to manage its own PR). Mitigation: the
  bootstrapping caveat below; the first PR for this feature is human-created.

## Design Decisions

- **DD-1 — One workflow file per gate** (not one file with three jobs). Rationale: makes the
  deferred spec-lint job a pure drop-in (FR-19 + scope's "structure so spec-lint can be added
  without redesign"), makes `/sdd-init`'s non-destructive add/skip trivial per file, and isolates
  each gate's triggers/permissions. Alternative (single multi-job file) rejected because adding a
  job later edits a shared file and complicates non-destructive merge.
- **DD-2 — Shared scan/check scripts invoked by both CI and the pre-push hook.** Rationale: the
  cleanest way to guarantee "CI mirrors local" (FR-16, NFR-3) is to run identical code in both
  places rather than maintain two definitions. The secret scanner reuses `secret-redact.py`'s
  proven regex family rather than adding a new secret-scanning dependency (e.g. gitleaks), keeping
  zero new external deps and consistent with the repo's existing patterns.
- **DD-3 — github-agent has `Bash` but not `Write`/`Edit`.** Rationale: unlike vault-writer (which
  writes files into a vault), github-agent's mutations are all remote and executed via `git`/`gh`
  on the CLI. Giving it `Write`/`Edit` would blur the scribe boundary toward authoring local
  files; withholding them keeps it strictly a remote-mechanics agent (FR-2, NFR-4).
- **DD-4 — `install.sh` installs the pre-push hook into the current repo (dogfood), and `/sdd-init`
  distributes downstream.** Rationale: `install.sh` runs from a clone of this repo, so the natural,
  low-surprise target is this repo's own `.git/hooks` (satisfying FR-21's hook side and FR-18's
  install-flow parity), while `/sdd-init` — which runs *inside* a downstream project — owns
  downstream distribution (FR-20). This splits the two install surfaces cleanly along the lines the
  existing tooling already follows.
- **DD-5 — Reuse the orchestrator's existing `SECRET REQUEST` handling** rather than adding a new
  escalation path. github-agent's missing-token halt flows through the exact machinery the
  orchestrator already documents for specialist secret requests (NFR-2), minimizing new surface.
- **DD-6 — Branch name is supplied by the orchestrator, defaulting to `feature/<name>`.** Honors
  FR-3.1's determinism while remaining compatible with the existing `/sdd-feature` `<type>/<slug>`
  convention, so the two do not conflict.

## Deferred hooks / bootstrapping note

- **Deferred (designed-for, not built in v1):** a **spec-lint** CI job (EARS `FR-N`/`NFR-N` syntax,
  task→requirement citation, requirement→design traceability). The one-file-per-gate structure
  (DD-1) and `/sdd-init`'s per-file add/skip mean it later ships as a new
  `ci-templates/workflows/sdd-spec-lint.yml` with **no redesign** of anything here. Also deferred
  per scope: autonomous/auto-merge behaviour, GitHub Issues/project-boards/release/changelog
  automation, and multi-remote/non-GitHub forges. None are designed against here.
- **Bootstrapping:** github-agent and its orchestrator hooks (FR-7–FR-12) are the artifacts this
  feature *builds*; they are **not active during this feature's own development**. This feature's
  own pull request into `main` is opened and merged by a **human**, and the CI workflows/pre-push
  hook only begin gating once instantiated (dogfood) as part of implementing this feature.
  github-agent never invokes itself and is never in the loop for its own bootstrap. From the next
  feature onward, the lifecycle in Flow A operates end-to-end.
