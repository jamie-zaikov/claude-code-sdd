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

## After creation — git branch setup

After creating the spec files, ask the user what branch type this is (`feat`, `fix`, or other) and confirm the branch name, then create and switch to it branched from `main`:

```bash
git checkout main
git checkout -b <type>/$ARGUMENTS
```

If `main` does not exist locally, report the error and ask the user how to proceed — do not attempt to create it.

After the branch is created and checked out, confirm to the user:
- The spec scaffold that was created
- The branch name and what it was branched from

Then ask the user to describe what the feature should do, and offer two paths:

- **(a) Scope first (recommended for non-trivial features):** Stay in main session to do scoping work — resolve open questions, reconcile source documents, set boundaries. Populate `scope.md` as you go. When scoping feels complete, invoke the orchestrator with `Resume feature: $ARGUMENTS`.
- **(b) Skip to requirements:** If the feature is small or scope is already clear (e.g., parameterized variants of an existing feature), leave `scope.md` minimal and invoke the orchestrator now.

Default to (a) unless the user indicates the feature is well-scoped already.
