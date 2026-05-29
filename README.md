# SDD Global — Spec-Driven Development for Claude Code

Install once, use in every project. Kiro-style SDD workflow for Claude Code's terminal mode in VS Code.

## What's Included

```
agents/
  orchestrator.md             # Lifecycle coordinator — the only user-invocable agent
  requirements-agent.md       # Owns requirements.md, EARS syntax
  design-agent.md             # Owns design.md, requirement traceability
  tasks-agent.md              # Owns tasks.md, hierarchical task breakdown
  spec-consistency-checker.md # Read-only cross-document auditor, runs before implementation
  task-executor.md            # Implements one task, worktree-isolated
  task-tester.md              # Writes tests for one task
  task-validator.md           # Validates implementation + tests, pass/fail

commands/
  sdd-init.md             # /sdd-init — scaffold .specs/ in any project
  sdd-feature.md          # /sdd-feature <name> — create a new feature spec
  sdd-status.md           # /sdd-status — show progress across all features
  sdd-resume.md           # /sdd-resume <name> — resume work on a feature

CLAUDE.md                 # Global instructions loaded in every session

steering-templates/       # Reference copies of default steering files
  product.md
  tech.md
  structure.md
```

## Requirements

- Claude Code v2.1.32 or later (`claude --version`)
- VS Code with the Claude Code extension (by Anthropic)
- Opus 4.6 or later (for agent team orchestration). Agents are model-tiered via `model:` frontmatter:
  Opus for planning (requirements, design), Sonnet for the rest. The task-executor escalates to
  Opus automatically on a retry after a validator failure.

## Install

```bash
git clone <repo-url> sdd-global
cd sdd-global
chmod +x install.sh
./install.sh
```

Or if you downloaded the archive:

```bash
tar xzf sdd-global.tar.gz
cd sdd-global
chmod +x install.sh
./install.sh
```

The installer will:

1. Copy all 8 agents to `~/.claude/agents/`
2. Copy all 4 slash commands to `~/.claude/commands/`
3. Install the global CLAUDE.md to `~/.claude/CLAUDE.md`
   - If you already have one, it offers to overwrite, append, or skip
4. Check if `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set
   - Offers to add it to your shell profile if missing
5. Print VS Code settings.json recommendations

## After Install

### 1. Set your VS Code settings

Open VS Code settings (Cmd+, or Ctrl+,) and add:

```json
{
  "claudeCode.useTerminal": true,
  "claudeCode.environmentVariables": [
    {
      "name": "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
      "value": "1"
    }
  ]
}
```

### 2. Restart your terminal

Source your shell profile or open a new terminal so the environment variable takes effect:

```bash
source ~/.zshrc    # or ~/.bashrc, depending on your shell
```

### 3. Verify

```bash
claude --version
# v2.1.32 or later

echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# 1
```

## Usage

### First time in a new project

```
claude
> /sdd-init
```

This creates `.specs/steering/` with template files and `.specs/features/` for your specs. Fill in the steering templates with your project's context.

### Start a feature

```
> /sdd-feature user-auth
```

Or just say:

```
> New feature: user authentication with email and OAuth
```

### Review the workflow

The orchestrator walks you through:

1. **Requirements** — clarifying questions, then EARS-format requirements → you confirm
2. **Design** — architecture with requirement traceability → you confirm
3. **Tasks** — hierarchical task list with testing sub-tasks → you confirm
4. **Consistency check** — runs automatically after tasks are confirmed. An independent, read-only
   auditor cross-checks requirements ↔ design ↔ tasks ↔ steering. A FAIL blocks implementation
   until the flagged issues are resolved; no extra action needed on PASS.
5. **Implementation** — per task: executor → tester → validator → pass/fail

Each phase requires your explicit confirmation (the consistency check is the one automatic gate). The state is saved to `.spec-state.json` so you can resume anytime.

### Resume work

```
> /sdd-resume user-auth
```

Or in a new session:

```
> Resume feature: user-auth
```

### Check progress

```
> /sdd-status
```

## How It Works

Everything installs to `~/.claude/`:

```
~/.claude/
├── CLAUDE.md        # Global — loaded in every session
├── agents/          # Global — available in every project
│   ├── orchestrator.md
│   ├── requirements-agent.md
│   ├── design-agent.md
│   ├── tasks-agent.md
│   ├── spec-consistency-checker.md
│   ├── task-executor.md
│   ├── task-tester.md
│   └── task-validator.md
└── commands/        # Global — available in every project
    ├── sdd-init.md
    ├── sdd-feature.md
    ├── sdd-status.md
    └── sdd-resume.md
```

Project-level files override global ones if they share the same name. So if a specific project needs a custom orchestrator, put it in `<project>/.claude/agents/orchestrator.md` and it takes priority.

Per-project artifacts live in the project repo:

```
<project>/
├── CLAUDE.md               # Project-specific (optional, additive to global)
└── .specs/
    ├── steering/
    │   ├── product.md      # Product context
    │   ├── tech.md         # Stack and conventions
    │   └── structure.md    # Codebase layout
    └── features/
        └── <feature-name>/
            ├── requirements.md
            ├── design.md
            ├── tasks.md
            └── .spec-state.json  # gitignored
```

## Uninstall

```bash
cd sdd-global
chmod +x uninstall.sh
./uninstall.sh
```

Removes agents and commands. Leaves `~/.claude/CLAUDE.md` intact (remove SDD sections manually if needed).

## Tips

- **Start fresh sessions between phases.** The `.spec-state.json` carries progress. Don't run the whole lifecycle in one conversation — that's how you get context rot.
- **Use `/compact` aggressively.** When context fills past 50%, compress.
- **Opus for planning, Sonnet for execution.** Model tiering ships in each agent's `model:` frontmatter: Opus for requirements/design, Sonnet for tasks/execution/validation. The task-executor auto-escalates to Opus on a retry after a validator failure. Override per agent by editing its frontmatter.
- **Worktrees for parallel tasks.** The task-executor has `isolation: worktree`. For manual parallel work: `claude --worktree task-3-api`.
