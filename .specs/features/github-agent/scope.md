# Scope: github-agent

<!-- Owned by main session during pre-orchestrator scoping. Read by orchestrator and passed to all specialists. Locked before invoking the orchestrator. -->

## One-line description
Add a `github-agent` to the SDD framework — a single audited choke-point that bridges the local SDD
lifecycle to GitHub (branches, PRs, verdict transcription, labels) as a scribe that never merges —
plus a CI enforcement layer (GitHub Actions workflows + git hooks) that makes the SDD quality gates
mandatory server-side, shipped as templates that `/sdd-init` drops into downstream projects and
dogfooded in this repo's own `.github/`.

## Open questions resolved
- O1: How much remote autonomy does github-agent get? → **Scribe only; humans merge.** The agent may
  create/switch branches, open and update PRs (including draft state), post review verdicts as PR
  comments, and set/clear labels. It MUST NOT merge, force-push to protected branches, or delete
  branches. Merge authority stays with a human. (source: this conversation)
- O2: What does CI enforce in v1? → **secret-scan, review-gate, build/test/lint.** (source: this conversation)
- O3: Who consumes the workflows + hooks? → **Templates shipped by `/sdd-init`** into every downstream
  project, AND dogfooded in this repo's own `.github/`. (source: this conversation)
- O4: How does github-agent authenticate to GitHub? → **`gh` CLI using a `GH_TOKEN`/`GITHUB_TOKEN`
  env var, under the "use, don't read" rule.** The token value never enters context; the agent runs
  `gh`, the binary reads the token. If the token is absent, the agent halts with `SECRET REQUEST`
  rather than guessing or working around it. (source: CLAUDE.md secret-handling protocol)
- O5: Does github-agent judge quality itself? → **No.** It only transcribes PASS/FAIL verdicts that
  the existing validator / code-reviewer / security-reviewer already produce into GitHub artifacts.
  This keeps it a scribe (mirrors vault-writer), not an author. (source: this conversation)

## Discrepancies reconciled
- D1: spec-lint was pitched as the highest-value CI job but NOT selected for v1 → **spec-lint is
  explicitly deferred to a later phase**, not silently dropped. v1 CI covers secret-scan,
  review-gate, and build/test/lint only. The requirements should note spec-lint as a named
  deferred item so it is easy to add. (source: this conversation)

## Scope boundaries
- In v1:
  - A new `agents/github-agent.md` agent definition (scribe charter, least-privilege verbs, `gh`-based).
  - Integration of github-agent into the orchestrator lifecycle at the existing gates (feature
    scaffold → branch; phase confirmations → commits/draft PR; per-task pipeline pass → commit +
    verdict comment; whole-feature review PASS → `ready-to-merge` label + request human review;
    blocking finding → `blocked:*` label + keep draft).
  - GitHub Actions workflow(s) implementing **secret-scan**, **review-gate**, and **build/test/lint**.
  - Git hook(s) (pre-push) as the local fast-feedback layer for the same checks, installed optionally
    by `install.sh` consistent with the existing secret-handling hooks.
  - Distribution: workflows + hooks authored as templates that `/sdd-init` drops into downstream
    projects, and instantiated in this repo's own `.github/` (dogfood).
  - Extend `secret-guard.py` blocklist to cover GitHub-token dump vectors (e.g. `gh auth token`,
    `printenv GH_TOKEN`).
  - Documentation: update CLAUDE.md agent-ownership + README to describe github-agent and the CI layer.
- Deferred:
  - **spec-lint** CI job (EARS FR-N/NFR-N syntax, task→requirement citation, requirement→design
    traceability) — named, designed-for, but not built in v1.
  - Autonomous / auto-merge behavior of any kind.
  - GitHub Issues management, project boards, release automation, changelog generation.
  - Multi-remote / non-GitHub forges (GitLab, Bitbucket).

## Cross-cutting rules
- **Scribe, not author:** github-agent transcribes verdicts and performs remote mechanics only; it
  never invents spec content or code, and never merges. Single audited choke-point for all remote
  mutations — nothing else in the fleet runs `gh` or `git push`.
- **Secrets: use, don't read.** GitHub tokens are referenced by env-var name only; never echoed,
  printed, or dumped. On a missing/blocked token the agent halts with `SECRET REQUEST`.
- **Least privilege / human merge gate:** merge to a protected branch requires the `ready-to-merge`
  label, which only appears after whole-feature review PASS, and is executed by a human.
- **Enforcement mirrors, never replaces, local gates:** CI jobs re-run the same checks server-side so
  they survive leaving the operator's machine; they are the mandatory backstop to advisory local gates.
- **No agent modifies another agent's artifact** (existing framework invariant preserved).
- **All spec artifacts in English; EARS syntax for requirements.**

## Sources consulted
- CLAUDE.md (global + project) — agent-ownership model, phase gates, secret-handling protocol,
  knowledge-vault isolation pattern (github-agent mirrors vault-writer's choke-point shape).
- Prior CC session `9e2fafe8` — the original brainstorm prompt and repo reconnaissance.
- This conversation's brainstorm + three scoping decisions (autonomy, CI scope, distribution).
- Repo state: existing `agents/`, `hooks/` (secret-guard.py, secret-redact.py), `commands/`,
  `install.sh`, empty `.github/`.
