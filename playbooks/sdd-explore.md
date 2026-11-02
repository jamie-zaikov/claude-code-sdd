# SDD playbook — Explore → Promote

The orchestrator reads this file when the user chooses to explore before or inside a feature. It is
the one normative definition of the Explore → Promote procedure; `agents/orchestrator.md` links
here and holds the few rules that bind even without this file. Explore is a free agent solving a
hard problem inside a scope the user grants once: no pipeline, no specs, no per-attempt approval —
but every project safeguard. Promote is the normal SDD planning and implementation path over the
proven solution; it adds **no** gate and removes none.

## 1. When — a user choice, never inferred

Explore is a conversation choice, not a mandatory taxonomy. The user decides; no agent infers it
from the shape of the work, and a feature without a grant runs exactly as before.

- **Before a feature**, when the right design appears only from simulation feedback (a scheduler,
  an instrument method, a protocol compiler): explore first, then promote.
- **Inside a feature**, when one mechanism turns out uncertain: a bounded experiment on that
  mechanism. The unaffected accepted baseline stays as it is; the result enters as an amendment of
  the affected tasks only.

API-style work (read the docs, implement, test) needs no exploration. A known design can expose one
uncertain mechanism later, and the existing probe tiers (*Discovery, Prototypes and Probes*) still
cover any phase; Explore is the larger grant for the case where the probe tiers are too small.

## 2. The grant — `exploreAuthority`, asked once per feature

**Tooling-gap check first.** Before asking, check that the project's reviewed action path can do
what the objective needs (a runner that simulates one order cannot test two linked chains). When it
cannot, Explore does not improvise a route: either narrow the objective to what the path can test,
or extend the path first as a small reviewed change through the normal gates, then explore. Surface
the gap to the user with the two options; the user chooses. Check this before the grant, not after.

**Ask once**, in the *Asking the User* shape (context, WHAT, WHY, HOW): the objective, the boundary,
the action path, the forbidden routes, the budget and the explorer, each in plain words with its
effect. A yes is recorded in `.spec-state.json`:

```
exploreAuthority: {
  grantedAt, grantedBy: "user", quote,
  objective,    // what Explore must settle, e.g. "report every timing limit on two linked chains"
  boundary,     // what the explorer may create, simulate, inspect and delete — its own objects,
                // named with an explore prefix, plus local scripts, probe patches, copies of inputs
  actionPath,   // the project's reviewed route for every live action (e.g. `scripts/vm-run`)
  forbidden,    // every route the project forbids, listed explicitly, plus the standing list below
  budget,       // N attempts or H hours
  explorer      // who writes probe code: "task-executor" (default) or "main session" (role exception)
}
```

- **Inherited rules.** The grant never revokes a project rule. Steering, the reviewed action path,
  runner safeguards, object ledgers, opt-in controls, cleanup checks, secret handling and the
  permission deny rules all stay in force. The grant removes ceremony (the pipeline, the specs, the
  test requirement), not safeguards.
- **Standing forbidden list** (always in `forbidden`, beside the project's own): any object the
  explorer did not create; publishing; widening a client guard or an allow-group; a secret beyond
  the existing env vars; a change to product code in the main checkout; hardware.
- **Explorer — a recorded role exception.** By default the **task-executor** (`mode: prototype`)
  writes probe code, as in the isolated-prototype tier, and the main session writes none. The user
  may name the main session as explorer so each attempt is visible in chat and can be redirected;
  that is a role exception, recorded in the grant as `explorer: "main session"`. Choosing to explore
  does not imply it.
- **Scope of the authority.** Inside the boundary there is no per-attempt approval. A permission the
  grant does not cover needs a new user decision — one decision for that permission, not a new
  grant. Overnight mode never grants or widens `exploreAuthority`, and an overnight run starts no
  Explore attempt: Explore is attended work.
- **Start narrow.** Prefer the smallest objective that can settle the open uncertainty; a wider
  Explore is a new decision for the user, never a drift.

## 3. Explore — the loop

Probe code lives in a temporary copy outside the product checkout (as the isolated-prototype tier:
`git archive HEAD | tar -x -C <dir>`, a pristine and a working copy). Live actions go through
`actionPath` only, on objects inside `boundary` only.

1. **Attempt log** — `spec-memory/explore/log.md`, one entry per attempt, written before the next
   attempt starts: hypothesis · change (patch path) · command · result (Completed / deadlock /
   error / timing limits met N of M) · what it teaches. Failed attempts are kept: they are the
   evidence for the negative tests in Promote.
2. **Save the patch before the result is logged.** Each attempt that changes code or protocol output
   saves `diff -ruN <pristine> <working>` as `spec-memory/prototypes/<slug>.patch` **before** its
   log entry is written, and the entry names that path. Beside it a manifest,
   `spec-memory/prototypes/<slug>.manifest.json`: the base commit, every uncommitted or
   generated/ignored input the attempt depended on (path and hash, or how to rebuild it), and the
   command. A patch carries no untracked or binary output and never a credential. A patch that is
   only described in prose cannot be adopted in Promote.
3. **Object ledger** — `spec-memory/explore/ledger.md`: the ID and type of every object the explorer
   creates (orders, protocols, scripts, dependent objects), not just a name prefix, with the attempt
   that created it.
4. **Evidence hygiene.** Scrub every capture before it is written anywhere (hostnames, tokens,
   addresses, device connection blocks), as in *Evidence and cleanup*.
5. **Budget stop.** Stop when the budget is spent, or when the current hypothesis cannot be resolved
   within what remains, and report. Never widen the budget or the boundary yourself: more is a new
   user decision. Record `explore: { attempts, status, reason }` in the state file (`status`:
   `active` | `spent` | `stopped` | `promoted`).
6. **Cleanup, verified.** At the end delete every object in the ledger (or keep the named ones the
   user asks for) and verify each deletion through `actionPath`. A failed cleanup stays a visible
   open item in the ledger and in the next progress line; it is never dropped.
7. **Solution brief** — `spec-memory/explore/solution.md`: the mechanisms that work; the variants
   that fail and why (one line per failure mechanism); the product changes needed, each with its
   patch and manifest path; the **open limits** (e.g. 6 of 18 timing limits exceeded), never
   silently relaxed; and the evidence paths. The brief is evidence, not a spec.

## 4. Promote — SDD implements the solution

- **No extra gate.** The user accepts the solution and its named limits where they see the exact
  contract: in the requirements confirmation (new feature) or in the confirmation of the affected
  amendment (existing feature). An acknowledgment of the brief alone approves no unseen design or
  tasks. Explore never confirms a planning gate.
- **The existing planning path, every gate.** Requirements → design → tasks → consistency check →
  classification → implementation (executor, tester, validator ∥ code-reviewer ∥ security-reviewer)
  → feature review. For an existing feature only the affected amendment goes through the current
  amendment rules; unchanged accepted work is not rewritten.
- **Requirements start from intent.** Pass the brief to the requirements-agent. Requirements come
  from the intended behaviour and constraints, refined by the evidence and the explicitly accepted
  deviations — not from whatever the experiment produced. An open limit the brief names becomes
  either a requirement or an explicitly accepted deviation; it is never dropped in silence.
- **Integration units.** Pass the brief to the tasks-agent. Tasks are integration units (a producer
  with its consumer; process work inside the unit that needs it), not one task per administrative
  step. Each retained patch is named on the task block that adopts it (`**Prototype:** <path>`),
  one unit per patch; the orchestrator passes it to that unit's executor as `prototype: <path>`
  (*Retained prototypes*), after the tasks and classification confirmations. The executor may
  adopt it; every gate runs on the delivered result.
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

## 5. Stop rules

Stop Explore at once, report, and wait for the user when: an action touches anything outside
`boundary` or bypasses `actionPath`; evidence cannot be attributed to an attempt (no log entry, no
patch, no manifest); a cleanup cannot be verified; or the budget is spent (§3.5). Stop Promote when
a promoted unit loses a gate — the normal retry rules apply, and no verdict is reused from Explore.

The number of material amendments during Promote is a diagnostic metric (with its cause and the
comparable scope), not a stop rule: a stop rule on it would punish useful discovery and invite
hidden amendments.

## 6. Metrics — record, do not infer

Explore: attempts, wall time per attempt split into setup and run (setup dominates in the pilot:
~20 s simulation, ~5 min setup), objects created and deleted, external wait. Promote: tasks and
units, consistency rounds, full-suite runs and their seconds, review findings by severity, material
amendments with cause, defects found at feature review or later. Record simulated duration, suite
runtime, elapsed delivery, external wait and billed usage **separately**. The comparison with the
old flow is directional, not a controlled benchmark; zero attempts while a live system is down is
no evidence either way.
