# Tech Stack and Conventions

<!-- Fill this in with your project's technical context. Every agent reads this. -->

## Stack
<!-- Language, framework, runtime, database, etc. -->

## Code Conventions
<!-- Naming, formatting, module structure, import ordering, etc. -->

## Modularity
<!-- The "no god files" rule. Every agent reads this; the code-reviewer enforces it mechanically
     with ~/.claude/tools/sdd-module-size.py. A source file may not end over the limit AND grow.
     Existing god files may only hold or shrink; new code goes into a new module. -->
- Module size limit: 500 lines
<!-- Optional: globs the check skips (generated code, vendored code). Docs and data are never checked. -->
<!-- - Module size exempt: generated/**, vendor/** -->

## Testing
<!-- Framework, conventions, directory structure, how to run tests -->
<!-- Example: "pytest in tests/, mirror source structure, run with `pytest -v`" -->

## Dependencies
<!-- Package manager, how to add dependencies, any restrictions -->

## Build and Run
<!-- How to build, run, lint, format the project -->

## Knowledge Vault
<!-- Optional. If this project has a curated Obsidian/markdown knowledge vault, give its
     absolute root path here. The orchestrator passes this to the vault-reader / vault-writer
     agents as the default; it is never read into the main session directly. -->
<!-- Example: "Vault root: /Users/you/Projects/lynx-manager/vault (MOC: workspace-management.md)" -->
<!-- Vault root: -->

