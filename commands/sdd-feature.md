---
description: "Scaffold a new feature directory under .specs/features/ with state tracking"
arguments:
  - name: feature-name
    description: "kebab-case slug only — no spaces (e.g. user-auth, payment-flow). Description is collected separately."
    required: true
---

Extract the feature slug: take only the first whitespace-delimited token from `$ARGUMENTS` as the slug. Everything after the first space (if any) is an inline description (Case A). Use the slug for all file paths and branch names.

Create the feature scaffold at `.specs/features/<slug>/`.

## Directory and files to create

### `.specs/features/$ARGUMENTS/.spec-state.json`

```json
{
  "feature": "$ARGUMENTS",
  "phase": "requirements",
  "lastModified": {
    "requirements": null,
    "design": null,
    "tasks": null
  },
  "confirmed": {
    "requirements": false,
    "design": false,
    "tasks": false
  },
  "implementationProgress": {
    "total": 0,
    "completed": 0,
    "lastCompletedTask": null,
    "currentTask": null
  },
  "taskStatus": {},
  "escalations": 0
}
```

### `.specs/features/$ARGUMENTS/scope.md`

Create the file with this template. This artifact captures the pre-orchestrator scoping work — resolved open questions, scope boundaries, discrepancies reconciled — produced during main-session discovery before requirements-agent is invoked. The orchestrator reads this file on session start and passes it to every specialist as authoritative input.

```markdown
# Scope: $ARGUMENTS

<!-- Owned by main session during pre-orchestrator scoping. Read by orchestrator and passed to all specialists. Fill in during scoping; lock before invoking the orchestrator. -->

## One-line description
<What the feature is, in a sentence>

## Open questions resolved
<!-- Decisions made during scoping that aren't requirements but constrain them -->
- O1: <question> → <resolution> (source: <conversation/doc>)

## Discrepancies reconciled
<!-- Conflicts between source documents or stakeholders, and the chosen direction -->
- D1: <conflict> → <resolution>

## Scope boundaries
- In v1: <what is included>
- Deferred: <what is explicitly out, with a note on phase>

## Cross-cutting rules
<!-- Constraints that apply across all requirements — e.g., variables-only, no-mocks, single-machine -->
- <rule>

## Sources consulted
- <protocol doc, prior feature, steering, memory entry>
```

### `.specs/features/$ARGUMENTS/requirements.md`

Create an empty file with just:

```markdown
# Requirements: $ARGUMENTS

<!-- This file is owned by the requirements-agent. Do not edit manually during SDD workflow. -->
```

### `.specs/features/$ARGUMENTS/design.md`

Create an empty file with just:

```markdown
# Design: $ARGUMENTS

<!-- This file is owned by the design-agent. Do not edit manually during SDD workflow. -->
```

### `.specs/features/$ARGUMENTS/tasks.md`

Create an empty file with just:

```markdown
# Tasks: $ARGUMENTS

<!-- This file is owned by the tasks-agent. Do not edit manually during SDD workflow. -->
```

### `.specs/features/$ARGUMENTS/input-data/README.md`

Create the `input-data/` folder with a single committed `README.md`. This folder is where the user drops any source material the feature needs — reference docs, exports, sample payloads, screenshots, config dumps. Everything in it except this README is gitignored (see below), so it is safe to drop private or bulky data here.

```markdown
# input-data — $ARGUMENTS

Drop any source material this feature needs here: reference docs, exports,
sample payloads, screenshots, config dumps.

Everything in this folder except this README is gitignored — safe for private
or bulky data. Agents read from here; they never delete what you drop.
```

### `.specs/features/$ARGUMENTS/spec-memory/README.md`

Create the `spec-memory/` folder with a single committed `README.md`. This folder is where agents and the main session write **non-functional artifacts** — anything that is not a spec document (requirements/design/tasks), not application code, and not user-supplied input. Examples: request drafts (e.g. a network-access ask), email drafts, investigation notes, decision logs, ad-hoc summaries, throwaway analysis. Everything except this README is gitignored, so these artifacts never clutter the repo root or the commit history.

```markdown
# spec-memory — $ARGUMENTS

Agents and the main session write non-functional artifacts here — anything that
is not a spec document, not application code, and not user input. Examples:
request/email drafts, investigation notes, decision logs, ad-hoc summaries.

Everything in this folder except this README is gitignored. This keeps scratch
artifacts out of the repo root and out of commits.
```

## Gitignore

Ensure `.gitignore` contains the per-feature scratch patterns below (append any that are missing; do not duplicate). These keep the contents of every feature's `input-data/` and `spec-memory/` out of git while keeping each folder's `README.md` tracked so the folder survives a clone and stays self-documenting.

```
# SDD per-feature scratch — data in, artifacts out; contents never committed
.specs/features/*/input-data/*
.specs/features/*/spec-memory/*
!.specs/features/*/input-data/README.md
!.specs/features/*/spec-memory/README.md
```

## After creation — git branch setup

After creating the spec files, ask the user what branch type this is (`feat`, `fix`, or other) and confirm the branch name, then create and switch to it branched from `main`:

```bash
git checkout main
git checkout -b <type>/$ARGUMENTS
```

If `main` does not exist locally, report the error and ask the user how to proceed — do not attempt to create it.

After the branch is created and checked out, confirm to the user:
- The spec scaffold that was created (note the `input-data/` folder for source material and the `spec-memory/` folder for non-functional artifacts, both gitignored except their READMEs)
- The branch name and what it was branched from

Then ask the user to describe what the feature should do, and offer two paths:

- **(a) Scope first (recommended for non-trivial features):** Stay in main session to do scoping work — resolve open questions, reconcile source documents, set boundaries. Populate `scope.md` as you go. When scoping feels complete, invoke the orchestrator with `Resume feature: $ARGUMENTS`.
- **(b) Skip to requirements:** If the feature is small or scope is already clear (e.g., parameterized variants of an existing feature), leave `scope.md` minimal and invoke the orchestrator now.

Default to (a) unless the user indicates the feature is well-scoped already.
