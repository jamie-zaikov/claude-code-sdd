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

## After creation

Tell the user:
1. Fill in the three steering templates in `.specs/steering/`
2. Use `/sdd-feature <name>` to start a new feature
3. Or say "New feature: <description>" to begin the SDD workflow
