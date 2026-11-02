# SDD playbook — Explore → Promote

The orchestrator reads this file when the user chooses to explore. It is the one normative
definition of the Explore → Promote procedure; `agents/orchestrator.md` links here and holds the few
rules that bind even without this file, and `agents/explorer.md` holds the explorer's side. Explore
is a free agent solving a hard problem inside a scope the user grants once: no pipeline, no specs,
no per-attempt approval — but every project safeguard. Promote is the normal SDD planning and
implementation path over the proven solution; it adds **no** gate and removes none.

## 1. When — a user choice, between tasks only

Explore is a conversation choice, not a mandatory taxonomy. The user decides; no agent infers it
from the shape of the work, and a feature without a grant runs exactly as before. API-style work
(read the docs, implement, test) needs no exploration, and the existing probe tiers (*Discovery,
Prototypes and Probes*) still cover any phase; Explore is the larger grant for the case where the
probe tiers are too small.

Explore runs in a **window**, and a window opens **between tasks only**: Explore never runs while a
task is in progress, and nothing is parked for it. The main checkout is clean outside `.specs/`
when a window opens, so `HEAD` is the base of every attempt. Three window kinds:

- **`before-feature`** — before the first planning phase, when the right design appears only from
  simulation feedback (a scheduler, an instrument method, a protocol compiler): explore first, then
  promote through requirements → design → tasks.
- **`before-task-<N>`** — before task N starts, to find how to build it; the unaffected accepted
  baseline stays as it is, and the result enters as an amendment of the affected tasks only.
- **`after-task-<N>`** — after task N is committed, an **evaluation run**: the explorer exercises
  the delivered function and its fit in simulation. Its findings are evidence and are routed like
  any finding — into the findings index, or as a material amendment through its owner agent and the
  user. An evaluation never edits product code, never reopens or passes a task by itself, and never
  stands in for a gate or for the acceptance probe.

## 2. The grant — `exploreAuthority`, asked once, wide, never inferred

**Tooling-gap check first.** Before asking, check that the project's reviewed action path can do
what the objective needs (a runner that simulates one order cannot test two linked chains). When it
cannot, Explore does not improvise a route: either narrow the objective to what the path can test,
or extend the path first as a small reviewed change through the normal gates, then explore. Surface
the gap to the user with the two options; the user chooses. Check this before the grant, not after.

**Ask once per feature**, in the *Asking the User* shape (context, WHAT, WHY, HOW): the objective,
the boundary, the action path, the forbidden routes, the budget and the explorer, each in plain
words with its effect. A yes is recorded in `.spec-state.json`; silence or the absence of an
objection grants nothing:

```
exploreAuthority: {
  grantedAt, grantedBy: "user", quote,
  objective,    // what Explore must settle, e.g. "report every timing limit on two linked chains"
  boundary,     // what the explorer may create, simulate, inspect and delete — its own objects,
                // named with an explore prefix, plus local scripts, probe patches, copies of inputs
  actionPath,   // the project's reviewed route for every live action (e.g. `scripts/vm-run`)
  forbidden,    // every route the project forbids, listed explicitly, plus the standing list below
  budget,       // N attempts (an attempt is defined in §3) or H hours
  explorer,     // "explorer" — the dedicated subagent (`agents/explorer.md`)
  decisions: [] // per-permission user decisions added later: { decidedAt, permission, quote }
}
```

- **Wide and durable.** One grant covers the whole feature: several windows, before and after
  different tasks, under one budget. It stays valid across sessions until the budget is spent, the
  feature reaches `complete`, or the user revokes it (`revokedAt` + the user's words). It is still
  asked once, never inferred, and never widened by an agent.
- **Inherited rules.** The grant never revokes a project rule. Steering, the reviewed action path,
  runner safeguards, object ledgers, opt-in controls, cleanup checks, secret handling and the
  permission deny rules all stay in force. The grant removes ceremony (the pipeline, the specs, the
  test requirement), not safeguards.
- **Standing forbidden list** — always in `forbidden`, beside the project's own: any object the
  explorer did not create; publishing; widening a client guard or an allow-group; a secret beyond
  the existing env vars; a change to product code in the main checkout; hardware.
- **The explorer is the `explorer` subagent** — a dedicated actor with a clean context, never the
  main session and never the task-executor. The main session is already the orchestrator and its
  context must stay small; the task-executor's `mode: prototype` touches no live system and keeps
  that rule. The explorer alone is allowed **and** bound to run live actions: it receives the full
  grant in its prompt (objective, boundary, action path, forbidden including the standing list,
  budget, attempts used, recorded decisions) and acts only through `actionPath` inside `boundary`.
- **Relation to the probe tiers.** `exploreAuthority` is a fourth, larger grant: it covers tier-2
  writing (probe code in a temporary copy; within its boundary it implies `prototypeAuthority`) and
  tier-3 actions on `boundary` objects through `actionPath` **only**. Explore's live actions are
  neither tier 2 nor a back door into tier 3: any other live action still needs its own
  project-level authority.
- **Scope of the authority.** Inside the boundary there is no per-attempt approval. A permission
  the grant does not cover needs a new user decision — one decision for that permission, recorded
  under `exploreAuthority.decisions[]` with the user's words; the explorer asks for it with
  `EXPLORE REQUEST: <permission>` and the orchestrator carries it to the user. Overnight mode never
  grants or widens `exploreAuthority`, and an overnight run starts no Explore attempt: Explore is
  attended work.
- **Start narrow.** Prefer the smallest objective that can settle the open uncertainty; a wider
  Explore is a new decision for the user, never a drift.

## 3. A window — the loop, one attempt per invocation

The orchestrator opens a window (`explore.window: { kind, task, openedAt }`, `explore.status:
running` while an explorer invocation is live, `idle` between invocations) and drives the
**explorer** through the *Specialist Execution Contract*: launched in the background, one attempt
per invocation, a fresh context each time. After each invocation the orchestrator reads **only that
attempt's log entry** (never the explorer's transcript or raw output), gives the user a short report
— hypothesis, result, what it teaches, attempts used of budget, open objects — and the user
continues, redirects (their words go into the next prompt) or closes the window. A `close`
invocation verifies the cleanup and writes the solution brief. The cadence is deliberate: the main
context grows by one log entry per attempt, and the user can redirect between every two attempts.

**One writer per artifact.** The explorer writes the attempt log, the object ledger, every patch
and manifest, and the brief; the orchestrator writes only the state file; no other actor writes any
of them, and no two explorer invocations run at once.

**An attempt** is one explorer invocation that issues at least one `actionPath` command for a
hypothesis. An invocation that ends before its first command (a setup failure, a stop before any
live action) is logged but does not count against the budget. `explore.attemptsUsed` counts
attempts, taken from the explorer's summary (`counted: yes`).

1. **Attempt log** — `spec-memory/explore/log.md`, append-only, one entry per invocation under
   `## <window> / attempt <n>`: hypothesis · change (patch path) · command · result (`Completed` /
   deadlock / error / timing limits met N of M) · what it teaches · objects · setup and run seconds.
   Failed attempts are kept: they are the evidence for the negative tests in Promote.
2. **Patch and manifest before the result is logged.** Each attempt that changes code or protocol
   output saves `diff -ruN <pristine> <working>` as `spec-memory/prototypes/<slug>.patch` **before**
   its log entry is written, and the entry names that path. Beside it a manifest,
   `spec-memory/prototypes/<slug>.manifest.json`: the base commit, the window and attempt, every
   generated or ignored input the attempt depended on (path and hash, or how to rebuild it), and the
   command. A patch carries no untracked or binary output and never a credential. A patch without a
   manifest beside it is a reference only, never applied; a patch that is only described in prose
   cannot be adopted in Promote.
3. **Object ledger** — `spec-memory/explore/ledger.md`: the ID and type of every object the explorer
   creates (orders, protocols, scripts, dependent objects), not just a name prefix, with the window
   and attempt that created it and the verified deletion.
4. **Evidence hygiene.** Every file Explore writes — log, ledger, manifest, brief — is scrubbed
   before it is written (hostnames, tokens, addresses, device connection blocks), and every
   `command` field in the log and the manifest names a secret by its env var, never its value — as
   in *Evidence and cleanup*.
5. **Budget stop.** When the budget is spent, or the current hypothesis cannot be resolved within
   what remains, Explore stops and reports; `explore.status: spent`. Never widen the budget or the
   boundary yourself: more is a new user decision.
6. **Cleanup, verified.** Every attempt ends with the deletion of the objects it created (or keeps
   the named ones the user asks for), each deletion verified through `actionPath`; the `close`
   invocation verifies the whole ledger again. A failed cleanup stays a visible open item in the
   ledger and in the next progress line; it is never dropped. After a stop-rule halt, or a session
   that ended mid-attempt (an explorer status file not `done`), cleanup is the **first action** of
   the next explorer invocation.
7. **Solution brief** — `spec-memory/explore/solution-<window>.md`, written by the `close`
   invocation: the mechanisms that work; the variants that fail and why (one line per failure
   mechanism); the product changes needed, each with its patch and manifest path; the **open
   limits** (e.g. 6 of 18 timing limits exceeded), never silently relaxed; and the evidence paths.
   The brief is evidence, not a spec.

## 4. Promote — SDD implements the solution

- **No extra gate.** The user accepts the solution and its named limits where they see the exact
  contract: in the requirements confirmation (new feature) or in the confirmation of the affected
  amendment (existing feature). An acknowledgment of the brief alone approves no unseen design or
  tasks. Explore never confirms a planning gate.
- **The existing planning path, every gate.** Requirements, design, tasks, the consistency check,
  classification, implementation (executor, tester, validator ∥ code-reviewer ∥ security-reviewer)
  and the feature review. For an existing feature only the affected amendment goes through the
  current amendment rules; unchanged accepted work is not rewritten.
- **The brief goes to every planning agent as evidence**: the requirements-agent, the design-agent
  and the tasks-agent each receive its path (*Phase Routing* payloads). Requirements come from the
  intended behaviour and constraints, refined by the evidence and the deviations the user accepts
  at the requirements confirmation — not from whatever the experiment produced. An open limit the
  brief names becomes either a requirement or an explicitly accepted deviation; it is never dropped
  in silence.
- **Integration units.** Tasks are integration units (a producer with its consumer; process work
  inside the unit that needs it), not one task per administrative step. Each retained patch is
  named on the task block that adopts it (`**Prototype:** <path>`), one unit per patch; a patch no
  task adopts is listed under `## Not adopted` in `tasks.md` with the reason. The consistency
  checker flags a `Prototype:` path whose patch or manifest is missing.
- **The `Prototype:` line has one consumer.** Before Stage 1 the orchestrator passes `prototype:
  <path>` to the executor when the task block has the line and both the patch and its manifest
  exist (*Retained prototypes*, after the tasks and classification confirmations). When either file
  is missing the task halts: attended, the user decides (run without the patch, or stop);
  overnight, record it under `userApprovalNeeded` and park the task. The executor may adopt the
  patch; every gate runs on the delivered result.
- **A run is an observation, not an oracle.** The experiment's generator, simulator assumptions and
  interpretation can share one defect that production then keeps (`Completed` with timing limits
  exceeded is completion, not correctness). Reviewed observations become regression fixtures;
  independent invariants and accepted constraints (timing, resource ownership, ordering, recovery,
  scientific rules) decide correctness. Simulator evidence never stands for hardware.
- **Negative tests.** One representative test per distinct failure mechanism the brief names (a
  deadlock class, a release-order fault), not one per failed attempt — that would recreate the
  suite growth.
- **The acceptance probe stays user-authored.** Run evidence never replaces its command or its
  criteria in `tech.md`.

## 5. Sessions, resume and overnight

- **Resume.** The grant survives a session. On any resume, show the user the grant (objective,
  boundary, budget) and the attempts used, list open ledger items, then continue the feature. A
  new attempt starts only on the user's word, as always; an explorer status file not `done` means
  the next invocation cleans up first (§3.6).
- **Status.** `explore.status` is `idle` | `running` | `spent` | `revoked` | `closed`. The
  orchestrator sets `running` while an explorer invocation is live, `spent` at the budget stop,
  `revoked` on the user's word, and `closed` when the feature reaches `complete`.
- **Overnight.** `/sdd-overnight <feature> on` refuses to start while `explore.status` is
  `running`; an overnight run starts no Explore attempt and never grants or widens the authority.

## 6. Stop rules

Stop Explore at once, report, and **wait for the user** when: an action touches anything outside
`boundary` or bypasses `actionPath`; evidence cannot be attributed to an attempt (no log entry, no
patch, no manifest); a cleanup cannot be verified; or the budget is spent (§3.5). The explorer
deletes its own objects when `actionPath` still permits it, and what remains is the first action
of the next invocation. Stop Promote when a promoted unit loses a gate — the normal retry rules
apply, and no verdict is reused from Explore.

The number of material amendments during Promote is a diagnostic metric (with its cause and the
comparable scope), not a stop rule: a stop rule on it would punish useful discovery and invite
hidden amendments.

## 7. Metrics — record, do not infer

Explore: attempts, wall time per attempt split into setup and run (setup dominates in the pilot:
~20 s simulation, ~5 min setup), objects created and deleted, external wait. Promote: tasks and
units, consistency rounds, full-suite runs and their seconds, review findings by severity, material
amendments with cause, defects found at feature review or later. Record simulated duration, suite
runtime, elapsed delivery, external wait and billed usage **separately**. The comparison with the
old flow is directional, not a controlled benchmark; zero attempts while a live system is down is
no evidence either way.
