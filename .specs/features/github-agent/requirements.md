# Requirements: github-agent

## Overview

The `github-agent` feature adds a single audited choke-point that bridges the local
Spec-Driven Development (SDD) lifecycle to GitHub. The agent is a **scribe**: it performs
remote git/GitHub mechanics (create/switch branches, open and update pull requests, transcribe
existing validator/reviewer verdicts as PR comments, set/clear labels) but never invents spec
content or code, never judges quality, and never merges. It mirrors the vault-writer's
audited-choke-point shape. Alongside the agent, the feature ships a **CI enforcement layer** —
GitHub Actions workflow(s) for secret-scan, review-gate, and build/test/lint, plus a pre-push
git hook — that re-runs the SDD quality gates server-side as the mandatory backstop to the
advisory local gates. Workflows and hooks are authored as templates that `/sdd-init` drops into
downstream projects and are dogfooded in this repo's own `.github/`. The feature also extends
`secret-guard.py` to cover GitHub-token dump vectors and updates CLAUDE.md and README docs.

This is a change to the SDD framework source repository itself; all artifacts are the agent
definition, CI templates, hooks, guard extensions, and documentation that make up the framework.

## Functional Requirements

### github-agent charter and least-privilege verbs

#### FR-1: Agent definition exists as a fleet member

The framework shall provide a `github-agent` definition at `agents/github-agent.md`.

##### FR-1.1
**The system shall** define `github-agent` with valid agent frontmatter (name, description,
tools, model) consistent with the other agents in `agents/`.

##### FR-1.2
**The system shall** declare `github-agent` as `user-invocable: false`, so it is invoked only by
the orchestrator, mirroring vault-writer.

##### FR-1.3
**The system shall** grant `github-agent` no `Agent` tool, making it a leaf agent that cannot
delegate.

#### FR-2: Scribe, not author

**Where** the orchestrator passes `github-agent` content to publish (commit messages, PR body,
verdict text, label names), **the system shall** publish exactly that content without inventing,
editing, or improving spec content or code.

##### FR-2.1
**If** `github-agent` is asked to produce a quality judgement (PASS/FAIL) of its own, **then the
system shall** refuse and instead only transcribe verdicts already produced by the task-validator,
code-reviewer, or security-reviewer.

##### FR-2.2
**The system shall** be the single audited choke-point for remote mutations: the agent definition
shall state that no other agent in the fleet runs `gh` or `git push`.

#### FR-3: Permitted remote operations

**When** instructed by the orchestrator, **the system shall** perform only the following remote
operations: create a branch, switch to a branch, commit, push to a non-protected feature branch,
open a pull request, update a pull request (including toggling draft state), post a PR comment,
and set or clear a label.

##### FR-3.1
**When** creating a branch for a feature, **the system shall** derive the branch name
deterministically from the feature name (e.g. `feature/<feature-name>`).

##### FR-3.2
**When** opening a pull request for a feature under active development, **the system shall** open
it as a draft.

#### FR-4: Prohibited operations

**If** `github-agent` is instructed or tempted to merge a pull request, force-push to a protected
branch, or delete a branch, **then the system shall** refuse the operation and report the refusal
to the orchestrator.

##### FR-4.1
**The system shall** never merge a pull request; merge authority remains with a human.

##### FR-4.2
**The system shall** never force-push to a protected branch.

##### FR-4.3
**The system shall** never delete a branch.

#### FR-5: Authentication via `gh` under "use, don't read"

**When** `github-agent` needs to authenticate to GitHub, **the system shall** run the `gh` CLI and
let it read the token from the `GH_TOKEN` or `GITHUB_TOKEN` environment variable, referencing the
token only by env-var name.

##### FR-5.1
**If** neither `GH_TOKEN` nor `GITHUB_TOKEN` is present in the environment, **then the system
shall** halt and return `SECRET REQUEST: <need>` proposing provisioning, rather than guessing or
working around the absence.

##### FR-5.2
**The system shall** never echo, print, or dump the token value (no `gh auth token`, `printenv`,
`env`, `set -x`, or authenticated `curl -v`).

##### FR-5.3
**When** reporting authentication state, **the system shall** report only presence/absence and
the env-var name used, never the token value.

#### FR-6: Verdict transcription

**When** the orchestrator supplies a completed verdict from the task-validator, code-reviewer, or
security-reviewer, **the system shall** transcribe that verdict verbatim (stage, pass/fail,
findings summary) into a pull request comment.

##### FR-6.1
**The system shall** attribute each transcribed verdict to its originating stage/agent so the PR
comment is auditable.

### Orchestrator lifecycle integration

#### FR-7: Feature scaffold triggers a branch

**When** a new feature is scaffolded, **the system shall** have the orchestrator invoke
`github-agent` to create the feature branch.

#### FR-8: Phase confirmations trigger commits and a draft PR

**When** a planning phase (requirements, design, tasks) is confirmed by the user, **the system
shall** have the orchestrator invoke `github-agent` to commit the confirmed artifact and, on the
first such confirmation, open a draft pull request.

#### FR-9: Per-task pipeline pass triggers a commit and verdict comment

**When** a task completes its full pipeline (validator PASS and both reviewers PASS), **the system
shall** have the orchestrator invoke `github-agent` to commit the task's changes and post the
transcribed per-task verdicts as a PR comment.

#### FR-10: Whole-feature review PASS triggers the ready-to-merge label and human review request

**When** the whole-feature review passes (both reviewers PASS), **the system shall** have the
orchestrator invoke `github-agent` to set the `ready-to-merge` label and request review from a
human.

##### FR-10.1
**The system shall** apply the `ready-to-merge` label only after a whole-feature review PASS, and
never before.

#### FR-11: Blocking finding triggers a blocked label and keeps the PR in draft

**If** a blocking finding is raised at any pipeline stage or in the whole-feature review, **then
the system shall** have the orchestrator invoke `github-agent` to set a `blocked:*` label (naming
the failing stage) and keep the pull request in draft state.

##### FR-11.1
**When** the blocking condition is later resolved, **the system shall** clear the corresponding
`blocked:*` label.

#### FR-12: Human merge gate

**The system shall** require that any merge to a protected branch is performed by a human and
gated on the presence of the `ready-to-merge` label; no agent performs the merge.

### CI enforcement layer — GitHub Actions workflows

#### FR-13: Secret-scan workflow

**The system shall** provide a GitHub Actions workflow job that scans changes for secret material
and fails the check when a secret is detected.

#### FR-14: Review-gate workflow

**When** a pull request targets a protected branch, **the system shall** provide a GitHub Actions
workflow job that enforces the SDD review gate — verifying the `ready-to-merge` label is present
and no `blocked:*` label remains — and fails the check otherwise.

#### FR-15: Build/test/lint workflow

**The system shall** provide a GitHub Actions workflow job that runs the project's build, test,
and lint steps and fails the check on any failure.

#### FR-16: CI mirrors local gates as the mandatory backstop

**The system shall** ensure the CI jobs (secret-scan, review-gate, build/test/lint) re-run the
same checks enforced locally, so the gates survive leaving the operator's machine; CI mirrors and
never replaces the local gates.

##### FR-16.1
**The system shall** trigger the CI workflow(s) on pull request events targeting protected
branches (and on pushes to feature branches for fast feedback).

### CI enforcement layer — git hooks

#### FR-17: Pre-push hook for local fast feedback

**The system shall** provide a pre-push git hook that runs the same secret-scan and
build/test/lint checks locally before a push, as the advisory fast-feedback layer.

##### FR-17.1
**If** a local check fails, **then the system shall** cause the pre-push hook to block the push
with a message pointing at the failing check.

#### FR-18: Optional hook installation via `install.sh`

**Where** the operator opts in during `install.sh`, **the system shall** install the pre-push
hook consistent with the existing secret-handling hook installation flow (prompted, idempotent,
skippable).

##### FR-18.1
**If** the operator declines, **then the system shall** skip hook installation and continue
without error, matching the existing secret-handling opt-out behaviour.

### Distribution and templates

#### FR-19: Workflows and hooks authored as templates

**The system shall** author the CI workflow(s) and git hook(s) as reusable templates suitable for
instantiation into any downstream project.

#### FR-20: `/sdd-init` drops the templates into downstream projects

**When** `/sdd-init` runs in a downstream project, **the system shall** create the CI workflow(s)
under the project's `.github/workflows/` and make the pre-push hook available, appending any
missing entries without duplicating existing ones.

##### FR-20.1
**If** a target workflow or hook file already exists in the downstream project, **then the system
shall** not overwrite user content silently (append/skip consistent with the existing `/sdd-init`
gitignore-merge behaviour).

#### FR-21: Dogfood in this repository

**The system shall** instantiate the CI workflow(s) in this repository's own `.github/` so the
SDD framework repo enforces the same gates it ships.

### secret-guard extension

#### FR-22: Block GitHub-token dump vectors

**When** a Bash command would dump a GitHub token into context, **the system shall** have
`secret-guard.py` deny the command.

##### FR-22.1
**The system shall** block `gh auth token` and any equivalent command that prints a GitHub token.

##### FR-22.2
**The system shall** block `printenv GH_TOKEN`, `printenv GITHUB_TOKEN`, and analogous
env-var echo/print vectors for those variables.

##### FR-22.3
**When** blocking such a command, **the system shall** return a deny reason that points the agent
at the "use, don't read" pattern and the `SECRET REQUEST` escalation, consistent with the existing
guard messaging.

##### FR-22.4
**The system shall** not block sanctioned use of the token via `gh` (e.g. `gh pr create`,
`gh pr comment`) where the value never enters context.

### Documentation

#### FR-23: CLAUDE.md agent-ownership update

**The system shall** update the Agent Ownership section of both the project and global CLAUDE.md
to list `github-agent`, describing it as the audited remote choke-point scribe that never merges.

##### FR-23.1
**The system shall** state in CLAUDE.md that `github-agent` is the only component that runs `gh`
or `git push`, and that no agent modifies another agent's artifact (preserving the existing
invariant).

#### FR-24: README update

**The system shall** update the README to describe `github-agent` and the CI enforcement layer
(workflows + hooks), including the human merge gate and the `ready-to-merge` / `blocked:*` label
semantics.

## Non-Functional Requirements

### NFR-1: Least privilege and human merge gate

**The system shall** grant `github-agent` the minimum GitHub capabilities required for its scribe
role; merge to a protected branch shall always require the `ready-to-merge` label and shall be
executed by a human, never by any agent.

### NFR-2: Secrets — use, don't read

**The system shall** ensure no GitHub token value ever enters agent context: tokens are referenced
by env-var name only, and a missing/blocked token results in a `SECRET REQUEST` halt rather than a
workaround.

### NFR-3: Enforcement mirrors, never replaces, local gates

**The system shall** ensure CI is the mandatory server-side backstop: even if local hooks are
absent or bypassed, the same secret-scan, review-gate, and build/test/lint checks run in CI.

### NFR-4: No agent modifies another agent's artifact

**The system shall** preserve the framework invariant that no agent modifies another agent's
artifact; `github-agent` publishes content authored upstream and owns only its own remote
mechanics and the CI/hook templates delivered by this feature.

### NFR-5: Idempotent, non-destructive installation

**When** `install.sh` or `/sdd-init` runs more than once, **the system shall** produce the same
result without duplicating entries or overwriting existing user files, matching the current
installer behaviour.

### NFR-6: `gh` CLI dependency handling

**If** the `gh` CLI is not available, **then the system shall** halt and report the missing
dependency clearly rather than failing silently or attempting an unauthenticated workaround.

### NFR-7: English and EARS

**The system shall** author all spec artifacts in English; requirements use EARS syntax with
`FR-N` / `NFR-N` numbering.

### NFR-8: Auditability

**The system shall** make every remote mutation traceable: PR comments attribute transcribed
verdicts to their originating stage, and label changes correspond to a lifecycle event.

## Deferred / Future Items

These are explicitly named and out of scope for v1, but reserved for a later phase so they are
easy to add:

- **spec-lint CI job** (deferred, highest-value future work per discrepancy D1): a CI job that
  checks EARS `FR-N`/`NFR-N` syntax, task→requirement citation, and requirement→design
  traceability. v1 CI covers only secret-scan, review-gate, and build/test/lint. The workflow
  templates should be structured so a spec-lint job can be added without redesign.
- **Autonomous / auto-merge behaviour** of any kind.
- **GitHub Issues management, project boards, release automation, changelog generation.**
- **Multi-remote / non-GitHub forges** (GitLab, Bitbucket).

## Out of Scope

- Any merge performed by an agent (merge is a human action).
- Force-pushing to protected branches or deleting branches.
- github-agent authoring or editing spec content, code, or quality verdicts.
- Reading knowledge-vault content (this repo has no vault; no vault routing applies).

## Open Questions

- None. All open questions (O1–O5) and the discrepancy (D1) were resolved and locked in
  `scope.md` during pre-orchestrator scoping.
