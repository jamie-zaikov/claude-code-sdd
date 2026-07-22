---
description: Initialize SDD directory structure and steering templates in the current project
---

Create the Spec-Driven Development directory structure in this project.

## Directories to create

- `.specs/steering/`
- `.specs/features/`

## Files to create

### `.specs/steering/product.md`

```markdown
# Product Context

## Product Overview
<!-- What is this product? Who is it for? What problem does it solve? -->

## Users
<!-- Who are the primary users? What are their goals? -->

## Key Principles
<!-- What product principles should guide all feature decisions? -->
<!-- Examples: "Offline-first", "API-compatible with v1", "Accessible to screen readers" -->
```

### `.specs/steering/tech.md`

```markdown
# Tech Stack and Conventions

## Stack
<!-- Language, framework, runtime, database -->

## Code Conventions
<!-- Naming, formatting, module structure, import ordering -->

## Testing
<!-- Framework, conventions, directory structure, how to run tests -->

## Dependencies
<!-- Package manager, how to add dependencies, any restrictions -->

## Build and Run
<!-- How to build, run, lint, format the project -->
```

### `.specs/steering/structure.md`

```markdown
# Codebase Structure

## Directory Layout
<!-- High-level directory tree with descriptions -->

## Key Patterns
<!-- Architectural patterns in use -->

## Module Boundaries
<!-- What depends on what. Which modules should not import from each other. -->
```

## Gitignore

Ensure `.gitignore` contains the block below (create the file with it if absent; otherwise append any missing lines without duplicating). The `input-data/*` and `spec-memory/*` patterns keep every feature's dropped data and non-functional artifacts out of git, while the `!…README.md` negations keep each folder tracked and self-documenting.

```
**/.spec-state.json

# SDD per-feature scratch — data in, artifacts out; contents never committed
.specs/features/*/input-data/*
.specs/features/*/spec-memory/*
!.specs/features/*/input-data/README.md
!.specs/features/*/spec-memory/README.md
```

## CI templates

Distribute the SDD CI enforcement layer into this project **non-destructively**, using the identical append/skip discipline as the Gitignore step above: every file is **created if missing** and **never overwrites** existing user content — a name clash is skipped and reported, never clobbered.

Read every template from the copies `install.sh` stages under `~/.claude/ci-templates/` (`workflows/`, `hooks/`, `scripts/`), so a downstream project needs only the global install — not a clone of the SDD source repo. If `~/.claude/ci-templates/` is absent, the user opted out of the CI/pre-push step during `install.sh`: tell them so and skip this whole section without error.

### Workflows + shared scanner

Ship the workflow(s) and their scanner **together** — a workflow deployed without the scanner it calls is a permanently-red check.

1. Create `.github/workflows/` if it does not exist.
2. For each `~/.claude/ci-templates/workflows/sdd-*.yml`: if `.github/workflows/<name>` does **not** exist, copy it in; if a file of that name **already exists**, **do not overwrite it** — skip and report it (same non-destructive behaviour as the gitignore merge above).
3. Drop the shared scanner into **`.github/scripts/sdd-secret-scan.py`** (create `.github/scripts/` if absent; same create-if-missing / skip-and-report-if-present rule). This is the exact path both the workflow (`python3 .github/scripts/sdd-secret-scan.py`) and the pre-push hook's lookup expect, so all three agree on one location.

### Pre-push hook (opt-in)

Make the advisory pre-push hook **available** without force-activating it — activation stays opt-in, exactly like the secret-handling flow in `install.sh`.

1. Copy `~/.claude/ci-templates/hooks/pre-push` to a documented in-repo location, e.g. `scripts/git-hooks/pre-push` (create the directory if missing).
2. Use **sentinel-based idempotence**: the template's first marker line is `# >>> sdd-pre-push (managed) >>>`. If a file already exists at the destination and contains that sentinel, it is an SDD-managed hook — update it if changed, skip if identical. If a file exists there **without** the sentinel, it is the user's own hook — **do not overwrite**; report it and point at the template for a manual merge.
3. Tell the user how to activate it (opt-in — `/sdd-init` never activates it for them):
   - `git config core.hooksPath scripts/git-hooks` — repo-scoped and keeps the hook under version control, **or**
   - copy it into `.git/hooks/pre-push` and `chmod +x` it.

### Idempotence and non-destructiveness

Because each file is added-or-skipped independently and every merge is append-only, running `/sdd-init` again produces the **same result** — no duplicates, no overwrites, existing user content left untouched. A future `sdd-spec-lint.yml` needs no change here: once it exists under `~/.claude/ci-templates/workflows/`, the per-file loop above picks it up automatically (one-workflow-per-gate drop-in).

### Security guidance to give the user

When reporting what was added, warn the user about two things:

- **Do not add write `permissions:`, `secrets:`, or a `pull_request_target:` trigger to these workflows.** The templates are safe because their token is read-only (`contents: read`) and no secret is exposed to the fork-controlled `scripts/ci.sh` or scanner. Granting write permissions, exposing secrets, or switching to `pull_request_target` would turn the fork-controlled build/scan step into an exfiltration/write vector.
- **Configure `sdd-review-gate` as a REQUIRED status check on `main`** in the repository's branch-protection settings, and choose the required-check name so that a **skipped** run on a non-PR event is **not** treated as a passing check. The review-gate job runs only on `pull_request` events targeting `main`; without this branch-protection setting the server-side human merge gate (the `ready-to-merge` / `blocked:*` label enforcement) is not actually enforced.

## After creation

Tell the user:
1. Fill in the three steering templates in `.specs/steering/`
2. Use `/sdd-feature <name>` to start a new feature
3. Or say "New feature: <description>" to begin the SDD workflow
4. If CI templates were added: activate the pre-push hook (see above) and set `sdd-review-gate` as a required status check on `main` in branch protection, so the merge gate is enforced server-side
