# SDD playbook — Explore → Promote

The orchestrator reads this file when the user chooses to explore. It is the one normative
definition of the Explore → Promote procedure; `agents/orchestrator.md` links here and holds the few
rules that bind even without this file, and `agents/explorer.md` holds the explorer's side. Explore
is a dedicated agent solving a hard problem inside a scope the user grants once: no pipeline, no
specs, no new permission grant per attempt — but every project safeguard. Promote is the normal SDD
planning and implementation path over the proven solution; it adds **no** gate and removes none.

**Honest scope.** Explore is an attended, **checkpoint-only** discovery facility: it runs between
tasks, one explorer invocation at a time. It does not solve mid-task discovery — a task that meets an
uncertainty while its tree is dirty keeps the existing discovery and prototype tiers as its path,
and nothing is parked or discarded to open a window. It is not a scheduler and adds no planning
lifecycle.

## 1. When — a user choice, between tasks only

Explore is a conversation choice, not a mandatory taxonomy. The user decides; no agent infers it
from the shape of the work, and a feature without a grant runs exactly as before. API-style work
(read the docs, implement, test) needs no exploration, and the existing probe tiers (*Discovery,
Prototypes and Probes*) still cover any phase; Explore is the larger grant for the case where the
probe tiers are too small.

Explore runs in a **window**, and a window opens **between tasks only**: Explore never runs while a
task is in progress, and nothing is parked for it. Three window kinds, and no other:

- **`before-feature`** — before the first planning phase, when the right design appears only from
  simulation feedback (a scheduler, an instrument method, a protocol compiler): explore first, then
  promote through requirements → design → tasks.
- **`before-task-<N>`** — before task N starts, to find how to build it; the unaffected accepted
  baseline stays as it is, and the result enters by the existing effect-based rule (§4): a
  recorded decision when it selects a method the confirmed text already permits, a material
  amendment of the affected tasks when it changes acceptance, a contract, authority or an agreed
  risk.
- **`after-task-<N>`** — after task N is committed, an **evaluation run**: the explorer exercises
  the delivered function and its fit in simulation. Its findings are evidence and are routed like
  any finding — into the findings index (by you, with stage `explore`), or as a material amendment
  through its owner agent and the user. An evaluation never edits product code, never reopens or
  passes a task by itself, and never stands in for a gate or for the acceptance probe. A read-only
  or no-change evaluation needs no patch. **Severity cap:** an explore-stage finding is recorded
  with severity at most `medium` (`medium`, `low` or `note`) — never `high` or `critical`; it never
  blocks a task by itself. A Critical/High claim
  from Explore is a material decision put to the user (*Asking the User*); only a gate's own
  re-derivation — the validator, a reviewer, or the Feature Review Gate — can make it blocking.

**Window entry — mechanical, against existing state.** A window opens only when all hold: no task
is `in_progress`; the main checkout is clean outside `.specs/`; no wave exists; no Level 1
speculation exists; no specialist writer is live (every status file for the feature is `done`,
`failed`, or `blocked` whose `blockedOn` the orchestrator has acted on and whose agent has ended).
While a window is open (until `window.closedAt` is set) **no task, Level 1
overlap or wave launches**. A `before-task-<N>` window is requested before task N could start
speculatively: when the user has asked for one, do not start N's overlap. `HEAD` is the base of
every attempt; record it in the window.

**Provisional commits.** A clean HEAD may hold `awaiting_candidate` commits (Phase B: committed,
not yet covered by a full suite). A window on that HEAD records them under `window.provisional`
and in the brief; an attempt may use them, but Explore never completes them, never replaces their
full suite, and needs no extra full suite to open. If a later candidate repair changes them, the
observations that depended on them are re-assessed before Promote relies on them.

## 2. The grant — `exploreAuthority`, asked once, wide, never inferred

**Tooling-gap check first.** Before asking, check that the project's reviewed action path can do
what the objective needs (a runner that simulates one order cannot test two linked chains). When it
cannot, Explore does not improvise a route: either narrow the objective to what the path can test,
or extend the path first as a small reviewed change through the normal gates, then explore. Surface
the gap to the user with the two options; **the user chooses**, never the agent. Check this before
the grant, not after. The same check requires a **`reconcile` capability** whenever `boundary`
permits creating live objects — without it a create whose response was lost can never be found or
deleted; `reconcile: none` is acceptable only for a read-only or simulate-only boundary that creates
nothing.

**Ask once per feature**, in the *Asking the User* shape (context, WHAT, WHY, HOW): the objective,
the boundary, the action path and its reconcile capability, the forbidden routes, the budget, the
cadence and the explorer, each in plain words with its effect. A yes is recorded in
`.spec-state.json`; silence or the absence of an objection grants nothing:

```
exploreAuthority: {
  grantedAt, grantedBy: "user", quote,
  objective,    // what Explore must settle, e.g. "report every timing limit on two linked chains"
  boundary,     // what the explorer may create, simulate, inspect and delete — its own objects,
                // named with an explore prefix, plus local scripts, probe patches, copies of inputs
  actionPath,   // the project's reviewed route for every live action (e.g. `scripts/vm-run`)
  reconcile,    // the action path's command that lists the explorer's own objects by recorded ID
                // or ownership — needed to settle an uncertain outcome; none if the path lacks one
  forbidden,    // every route the project forbids, listed explicitly, plus the standing list below
  budget,       // N attempts — attempts only in this release (an attempt is defined in §3)
  cadence,      // "step" (default) or { mode: "continuous", upTo: N }
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
  grant in its prompt (objective, boundary, action path and reconcile command, forbidden including
  the standing list, budget and attempts used, cadence, recorded decisions) and acts only through
  `actionPath` inside `boundary`.
- **Relation to the probe tiers.** `exploreAuthority` is a fourth, larger grant: it covers tier-2
  writing (probe code in a temporary copy; within its boundary it implies `prototypeAuthority`) and
  tier-3 actions on `boundary` objects through `actionPath` **only**. Explore's live actions are
  neither tier 2 nor a back door into tier 3: any other live action still needs its own
  project-level authority.
- **What the authority means.** The authority is durable: no new permission grant is asked per
  attempt. Execution still advances **one requested attempt, or one requested bounded sequence, at
  a time** (the cadence, §3). A permission the grant does not cover needs a new user decision — one
  decision for that permission, recorded under `exploreAuthority.decisions[]` with the user's
  words; the explorer asks for it with `EXPLORE REQUEST: <permission>` and you carry it to the
  user. A `decisions[]` entry never covers a hook block or a `permissions.deny` result: those are
  security denials, reported as possible false positives, never re-run under a recorded decision.
  Overnight mode never grants or widens `exploreAuthority`, and an overnight run starts no Explore
  attempt: Explore is attended work.
- **Start narrow.** Prefer the smallest objective that can settle the open uncertainty; a wider
  Explore is a new decision for the user, never a drift.
- **Completing an older grant.** A grant recorded before a key this release requires (`reconcile`,
  `cadence`) is completed on the user's word only: ask once, in the *Asking the User* shape, and
  record the added fields under the grant with `amendedAt` and the user's quote. An agent never
  fills a missing key in and never assumes a default; until the user completes it, the explorer
  stops with `grant missing or incomplete`.

## 3. A window — the loop, one invocation at a time

You open a window (`explore.window: { kind, task, openedAt, head, provisional: [], closedAt: null
}`) and drive the **explorer** through the *Specialist Execution Contract*: launched in the
background, one invocation at a time, a fresh context each time. Each launch gets the contract's
**invocation number** (`invocations["explore-<window>/explorer"]`), which names its status file
(`explore-<window>-explorer-a<n>.json`); the **attempt id** is a separate counter that lives only in
the log heading and the summary. An `attempt`, a `recover`, a `close` and a respawn each take a new
invocation number; a `recover` reuses the attempt id it settles. Each explorer launch is also
recorded under `explore.invocations[]` as `{ n, kind, attemptId, window }`: `kind` is `attempt`,
`recover` or `close`, and `attemptId` is set only when one exists — never for a `close`.

**Cadence — chosen in the grant.**
- `step` (default): after each invocation you read **only that attempt's log entry** (never the
  explorer's transcript or raw output), give the user a short report — hypothesis, result, what it
  teaches, attempts used of budget, retained and open objects — and the next attempt starts only on
  the user's word: continue, redirect (their words go into the next prompt) or close the window.
- `continuous, upTo: N`: the user asked, in the grant, for a bounded sequence. You launch the next
  attempt without waiting, up to `N` attempts in this window and never past the budget; after every
  attempt you still give the short report, and a user message that arrives between attempts is
  steering for the next prompt. A **mandatory stop** ends the sequence and waits for the user: a
  boundary or authority change (an `EXPLORE REQUEST`), the budget or `upTo` reached, an unknown
  action outcome (a `recover` pending), open cleanup, or a material decision. Silence never creates
  or extends a continuous request; the next sequence is the user's word again. Overnight still
  starts no attempt. There is no wall-clock cap in this release. The contract's grace window is a
  liveness detector, not a deadline: an explorer with fresh status writes may run on past it, and
  only `upTo` and the budget bound a sequence. In every cadence only you launch an explorer; the
  explorer never launches itself.

**Budget and reservation — attempts only.** An **attempt** is one explorer invocation that issues
at least one `actionPath` command for a hypothesis. **Before** each `attempt` launch you reserve
the slot in the state file: `explore.attempts[]` gains `{ id, invocation, window, state:
"reserved" }`, and `attemptsUsed` counts every entry that is not `released`. **You are the primary
budget stop:** reserve only when `attemptsUsed < budget` (the count before the new reservation);
otherwise set `explore.status: spent` and launch nothing. Pass the explorer `attemptsBefore` (the
count before its reservation); its own guard compares that count, never one that includes its own
slot. A crash, a kill or a
lost result never frees the slot. Only the explorer's written evidence of a setup failure before
its first command (`released: …` in its log stub) lets you mark the entry `released`; the stub's
`commands issued: yes` or any uncertainty marks it `counted` (or `uncertain`). An attempt whose
outcome is uncertain is settled by a `recover` invocation under the same id before any new
hypothesis.

**Recovery is never exploration.** Re-dispatch goes by the recorded kind: an `attempt` whose slot
is `reserved` or `uncertain` (a respawn under the contract, step 4; a status file not `done`; a
lost result) and an interrupted `recover` run a `recover` invocation under the same attempt id —
`recover` runs only for such an attempt; a failed or killed `close` is repeated as `close` (a new
invocation number, no budget charge, never an attempt id invented or borrowed). A `recover`
invocation: cleanup of
`open` objects, reconciliation of a lost result through the grant's `reconcile` command (an object
created with a lost response is found by recorded ID or ownership — never by a name prefix, and a
create with an unknown outcome is never re-issued), a log entry, no hypothesis. A missing stub, or
a stub without `commands issued` evidence either way, is uncertain — never a release. The next `attempt`
needs the user's word (`step`) or the active continuous request. A grant whose `reconcile` is
`none` stops on an uncertain outcome until the user settles it.

**One writer per artifact.** The explorer writes the attempt log, the object ledger, every patch
and manifest, and the brief; you write only the state file; no other actor writes any of them,
and no two explorer invocations run at once.

**Killed before its entry.** When an explorer ends `failed`, is killed, or leaves a log stub without
a result, you report from the stub (the reservation), the ledger and the status file's last `step`
— never from its transcript — and the next invocation goes by its kind: a `recover` for an
`attempt`, a repeated `close` for a `close`.

1. **Attempt log** — `spec-memory/explore/log.md`, append-only, one entry per invocation under
   `## <window> / attempt <id>`, opened as a reservation stub (`invocation`, `started`, `commands
   issued`) and completed with: hypothesis · change (patch path) · command · result (`Completed` /
   deadlock / error / recovered / timing limits met N of M) · what it teaches · the next
   discriminating question · objects · setup and run seconds · `counted`. Failed attempts are kept:
   they are the evidence for the negative tests in Promote.
2. **Patch and manifest before the result is logged.** Each attempt that changes code or protocol
   output saves `diff -ruN <pristine> <working>` as `spec-memory/prototypes/<slug>.patch` **before**
   its log entry is completed, and the entry names that path. Beside it a manifest,
   `spec-memory/prototypes/<slug>.manifest.json`: the base commit, the window and attempt, every
   generated or ignored input the attempt depended on (path and hash, or how to rebuild it), and the
   command. A patch carries no untracked or binary output and never a credential. A patch without a
   manifest beside it is a reference only, never applied; a patch that is only described in prose
   cannot be adopted in Promote. A read-only or no-change evaluation writes no patch.
3. **Object ledger** — `spec-memory/explore/ledger.md`: the ID and type of every object the explorer
   creates (orders, protocols, scripts, dependent objects), not just a name prefix, with the window
   and attempt that created it and its **state**: `open` · `deleted-verified` · `retained-by-user`
   (with the user's decision recorded). Cleanup targets `open` objects only; a retained object is
   never deleted and the user never repeats the retention.
4. **Evidence hygiene.** Every file Explore writes — log, ledger, manifest, brief — is scrubbed
   before it is written (hostnames, tokens, addresses, device connection blocks), and every
   `command` field in the log and the manifest names a secret by its env var, never its value — as
   in *Evidence and cleanup*. Raw captures are deleted the same turn.
5. **Budget stop.** When the budget is spent, or the current hypothesis cannot be resolved within
   what remains, Explore stops and reports; `explore.status: spent`. Never widen the budget or the
   boundary yourself: more is a new user decision.
6. **Cleanup, verified.** Every attempt ends with the deletion of the `open` objects it created,
   each deletion verified through `actionPath`; the ones the user asks to keep become
   `retained-by-user`. The `close` invocation checks the whole ledger again and separates
   **retained** from **unresolved**; so does every progress line. An unresolved object stays a
   visible open item in the ledger and in the next progress line; it is never dropped. After a
   stop-rule halt, or a session that ended mid-attempt (an explorer status file not `done`),
   cleanup is the **first action** of the next explorer invocation (a `recover` for an attempt, a
   repeated `close` for a close).
7. **Missing evidence is a stop.** When the grant is live and `attemptsUsed > 0` but the log or
   the ledger file is missing (a fresh clone, lost gitignored files), a cleanup cannot be verified:
   stop, report, and start no attempt until the user re-provides the files or declares the boundary
   clean (recorded under `decisions[]`). Run this check **before you reserve** an attempt, so the
   first attempt of a fresh feature never stops on its own reservation.
8. **Solution brief** — `spec-memory/explore/solution-<window>.md`, written by the `close`
   invocation: the mechanisms that work; the variants that fail and why (one line per failure
   mechanism); the product changes needed, each with its patch and manifest path; the **open
   limits** (e.g. 6 of 18 timing limits exceeded), never silently relaxed; the provisional commits
   the window used; and the evidence paths. The brief is evidence, not a spec. Closing the window
   sets `window.closedAt` and `explore.status: closed`. On revocation the `close` writes a **stub
   brief** instead, and only this: the window kind, `head`, `provisional`, the attempt ids with
   their results, the retained and unresolved objects, `reason: revoked` with the user's words, and
   the line `no mechanism claimed` — Promote never reads a stub brief as a solution brief.

## 4. Promote — SDD implements the solution

- **No extra gate.** The user accepts the solution and its named limits where they see the exact
  contract: in the requirements confirmation (new feature) or in the confirmation of the affected
  amendment (existing feature). An acknowledgment of the brief alone approves no unseen design or
  tasks. Explore never confirms a planning gate.
- **The effect decides — decision or amendment.** Apply *Amendments — material vs internal
  reconciliation* to every discovery: a result that only selects a method the confirmed text
  already permits is a **recorded decision** (`spec-memory/decisions.md`), not an amendment and not
  a new planning cycle; a result that changes acceptance, a `Contract:`, authority, an external
  effect or an agreed risk is a **material amendment** through its owner agent and the user.
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
- **Phase B's candidate stays the unit.** Tasks are integration units (a producer with its
  consumer; process work inside the unit that needs it), not one task per administrative step and
  **not one unit per mechanism or per patch**: patches and mechanisms are traceability, and several
  may map to one coherent candidate. Each retained patch is named on the **one** task block that
  applies it (`**Prototype:** <path>`) — one owning task applies a patch, never two; a patch no task
  adopts is listed under `## Not adopted` in `tasks.md` with the reason. The consistency checker
  flags a `Prototype:` path whose patch or manifest is missing.
- **The `Prototype:` line has one consumer.** Before Stage 1 you pass `prototype: <path>` to the
  executor when the task block has the line and both the patch and its manifest exist (*Retained
  prototypes*, after the tasks and classification confirmations). When either file is missing the
  task halts: attended, the user decides (run without the patch, or stop); overnight, record it
  under `userApprovalNeeded` and park the task. The executor may adopt the patch, rework it into
  the product shape or read it as reference; every gate runs on the delivered result.
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
  boundary, budget, cadence) and the attempts used **of** the budget (`attemptsUsed` includes
  `reserved` and `uncertain` entries — list each such entry by id; the next invocation is a
  `recover` under that id), list retained and open ledger items, then continue the feature.
  A new attempt starts only on the user's word (or an active continuous
  request stated again by the user — a sequence never survives a session by itself); an explorer
  status file not `done` is re-dispatched by its recorded kind — a `recover` for a
  `reserved`/`uncertain` attempt, a repeated `close` for a `close`, never a `recover` with an
  invented attempt id. A missing log or ledger with `attemptsUsed > 0` is the stop of §3.7.
- **Status.** `explore.status` is `closed` | `idle` | `running` | `spent` | `revoked`. `closed`
  means no window is open (before the first window, between windows, and when the feature reaches
  `complete`); `idle` is the interval between invocations inside an open window; `running` while an
  explorer invocation is live. You set `spent` at the budget stop, and `closed` when a window
  closes and at `complete`. **Revocation:** on the user's word you first launch one final `close`
  invocation (cleanup of `open` objects, verified; the brief, or the stub brief of §3.8; the
  progress line keeps retained and unresolved objects), set `window.closedAt`, then set `revoked`;
  task, overlap and wave launches resume only after that. Open objects are never left as they are.
  **Sequence while an explorer is `running` or stale:** wait for the invocation to end, or kill it
  per the contract and confirm it is gone; if its attempt is `uncertain`, run `recover` first; then
  the final `close` — never `close` before that `recover`, because `close` reconciles nothing.
- **Overnight.** `/sdd-overnight <feature> on` refuses to start while `explore.status` is `idle` or
  `running` (a window is open); an overnight run starts no Explore attempt and never grants or
  widens the authority.

## 6. Stop rules

Stop Explore at once, report, and **wait for the user** when: an action touches anything outside
`boundary` or bypasses `actionPath`; evidence cannot be attributed to an attempt (no log entry, no
patch, no manifest); a cleanup cannot be verified (including a missing log or ledger); an outcome
is uncertain and `reconcile` is `none`; or the budget is spent (§3.5). The explorer deletes its own
`open` objects when `actionPath` still permits it, and what remains is the first action of the
next invocation. Stop Promote when a promoted unit loses a gate — the normal retry rules apply,
and no verdict is reused from Explore.

The number of material amendments during Promote is a diagnostic metric (with its cause and the
comparable scope), not a stop rule: a stop rule on it would punish useful discovery and invite
hidden amendments.

## 7. Metrics — record, do not infer

Explore: attempts, wall time per attempt split into setup and run (setup dominates in the pilot:
~20 s simulation, ~5 min setup), objects created and deleted, user wait, external wait. Promote:
tasks and units, consistency rounds, full-suite runs and their seconds, review findings by
severity, material amendments with cause, defects found at feature review or later. Record
simulated duration, suite runtime, elapsed delivery, user wait, external wait and billed usage
**separately**. The comparison with the old flow is directional, not a controlled benchmark; zero
attempts while a live system is down is no evidence either way. Measure the specialist-based
pilot itself; the earlier main-session attempt does not stand for it.
