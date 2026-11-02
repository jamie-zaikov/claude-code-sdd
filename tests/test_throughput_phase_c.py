#!/usr/bin/env python3
"""Prose-contract tests for pipeline-throughput Phase C — Explore → Promote.

Phase C codifies the Explore → Promote pilot: a free agent solves a hard problem inside a scope the
user grants once (`exploreAuthority`), then SDD promotes the proven solution through every normal
gate. `playbooks/sdd-explore.md` is the one normative definition; the orchestrator keeps the rules
that bind even without it. Each pin names a rule's key words and direction (`prose.near` refuses a
negated match; a rule that really is negative puts the negation inside its pattern), so a pin goes
RED when the rule is removed or inverted and stays GREEN when it is reworded or re-wrapped. Run:
    python3 -m unittest tests.test_throughput_phase_c -v
"""

import unittest
from pathlib import Path

try:
    from tests import prose
except ImportError:  # run from inside tests/
    import prose

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = read("playbooks/sdd-explore.md")
        cls.orch = read("agents/orchestrator.md")
        cls.executor = read("agents/task-executor.md")
        cls.tasks = read("agents/tasks-agent.md")
        cls.reqs = read("agents/requirements-agent.md")
        cls.claude = read("CLAUDE.md")
        cls.readme = read("README.md")

    def near(self, text, label, *terms, window=160):
        if not prose.near(text, *terms, window=window):
            self.fail(f"{label}: missing {' … '.join(terms)}")

    def lacks(self, text, pat, label):
        if prose.search(text, pat):
            self.fail(f"{label}: forbidden /{pat}/ present")


class PlaybookWhenTest(Base):
    """§1 — Explore is a user choice, never inferred, never a taxonomy."""

    def test_explore_is_a_user_choice(self):
        self.near(self.play, "choice", r"user choice, never inferred")
        self.near(self.play, "taxonomy", r"not a mandatory taxonomy", r"The user decides")
        self.near(self.play, "no grant", r"feature without a grant runs exactly as before")
        self.lacks(self.play, r"(may|should|must|shall) infer (it|explore)", "an agent infers Explore")

    def test_inside_a_feature_keeps_the_accepted_baseline(self):
        self.near(self.play, "inside", r"Inside a feature", r"bounded experiment",
                  r"unaffected accepted baseline stays as it is", r"amendment of\s+the affected tasks only",
                  window=300)

    def test_probe_tiers_stay_and_api_work_needs_no_exploration(self):
        self.near(self.play, "api", r"API-style work", r"needs no exploration")
        self.near(self.play, "tiers", r"existing probe tiers", r"still\s+cover any phase")


class PlaybookGrantTest(Base):
    """§2 — the grant: tooling gap first, one record, inherited rules, recorded explorer."""

    def test_tooling_gap_is_checked_before_the_grant(self):
        self.near(self.play, "gap", r"Tooling-gap check first", r"does not improvise a route",
                  r"narrow the objective", r"extend the path first as a small reviewed change",
                  r"before the grant, not after", window=400)
        self.lacks(self.play, r"check this after the grant", "gap check after the grant")

    def test_grant_record_has_every_key(self):
        self.near(self.play, "ask once", r"Ask once", r"\*Asking the User\* shape",
                  r"recorded in `.spec-state.json`", window=300)
        self.near(self.play, "record", r"exploreAuthority: \{", r"grantedAt, grantedBy: \"user\", quote",
                  r"objective", r"boundary", r"actionPath", r"forbidden", r"budget", r"explorer",
                  window=400)

    def test_grant_inherits_every_project_rule(self):
        self.near(self.play, "inherit", r"grant never revokes a project rule")
        self.near(self.play, "safeguards", r"removes ceremony", r"not safeguards")
        self.near(self.play, "standing", r"Standing forbidden list", r"did not create", r"publishing",
                  r"widening a client guard", r"product code in the main checkout", r"hardware",
                  window=300)

    def test_explorer_is_a_recorded_role_exception(self):
        self.near(self.play, "default", r"By default the\s+\*\*task-executor\*\*", r"`mode: prototype`",
                  r"writes probe code", r"main session writes none")
        self.near(self.play, "exception", r"role exception", r"`explorer: \"main session\"`")
        self.near(self.play, "not implied", r"Choosing to explore\s+does not imply it")
        self.lacks(self.play, r"By default the\s+(\*\*)?main session(\*\*)? writes", "main session default")

    def test_scope_of_the_authority(self):
        self.near(self.play, "no per-attempt", r"Inside the boundary there is no per-attempt approval")
        self.near(self.play, "uncovered", r"permission the\s+grant does not cover needs a new user decision")
        self.near(self.play, "overnight", r"Overnight mode never grants or widens `exploreAuthority`",
                  r"overnight run starts no\s+Explore attempt", r"Explore is attended work")
        self.near(self.play, "narrow", r"Start narrow", r"smallest objective",
                  r"wider\s+Explore is a new decision for the user")


class PlaybookLoopTest(Base):
    """§3 — the loop: log, patch + manifest, ledger, budget stop, verified cleanup, brief."""

    def test_probe_code_outside_the_checkout_and_live_actions_through_the_path(self):
        self.near(self.play, "copy", r"Probe code lives in a temporary copy outside the product checkout")
        self.near(self.play, "path", r"Live actions go through\s+`actionPath` only", r"inside `boundary` only")

    def test_attempt_log_before_the_next_attempt(self):
        self.near(self.play, "log", r"Attempt log", r"`spec-memory/explore/log.md`", r"one entry per attempt",
                  r"written before the next\s+attempt starts", r"patch path", window=300)
        self.near(self.play, "failed kept", r"Failed attempts are kept", r"negative tests")

    def test_patch_and_manifest_saved_before_the_result_is_logged(self):
        self.near(self.play, "patch", r"Save the patch before the result is logged",
                  r"`spec-memory/prototypes/<slug>.patch`", r"before\*\* its\s+log entry is written",
                  window=300)
        self.near(self.play, "manifest", r"`spec-memory/prototypes/<slug>.manifest.json`", r"base commit",
                  r"path and hash, or how to rebuild it", r"command", window=300)
        self.near(self.play, "no secret", r"never a credential")
        self.near(self.play, "prose", r"only described in prose cannot be adopted")
        self.lacks(self.play, r"(after|once) (its|the) (log entry|result) is (written|logged)[^.]{0,40}save",
                   "patch saved after the log")

    def test_object_ledger_records_ids_not_prefixes(self):
        self.near(self.play, "ledger", r"Object ledger", r"`spec-memory/explore/ledger.md`",
                  r"ID and type of every object", r"not just a name prefix", window=300)

    def test_captures_are_scrubbed_before_they_are_written(self):
        self.near(self.play, "scrub", r"Scrub every capture before it is written anywhere", r"tokens")

    def test_budget_stop_never_widens(self):
        self.near(self.play, "stop", r"Budget stop", r"Stop when the budget is spent", r"report",
                  r"Never widen the budget or the boundary yourself", r"new\s+user decision", window=300)
        self.near(self.play, "state", r"`explore: \{ attempts, status, reason \}`",
                  r"`active` \| `spent` \| `stopped` \| `promoted`")

    def test_cleanup_is_verified_and_a_failure_stays_visible(self):
        self.near(self.play, "cleanup", r"Cleanup, verified", r"delete every object in the ledger",
                  r"verify each deletion through `actionPath`", r"failed cleanup stays a visible\s+open item",
                  r"never dropped", window=300)
        self.lacks(self.play, r"failed cleanup (is|may be|can be) (dropped|ignored|closed)", "cleanup dropped")

    def test_solution_brief_keeps_open_limits(self):
        self.near(self.play, "brief", r"Solution brief", r"`spec-memory/explore/solution.md`",
                  r"mechanisms that work", r"one line per failure mechanism", r"patch and manifest path",
                  r"open limits", r"never\s+silently relaxed", r"evidence, not a spec", window=300)


class PlaybookPromoteTest(Base):
    """§4 — Promote: no extra gate, the existing path, intent-first requirements, units, fixtures."""

    def test_no_extra_gate_and_explore_never_confirms(self):
        self.near(self.play, "where accepted", r"No extra gate", r"requirements confirmation",
                  r"confirmation of the affected\s+amendment", window=300)
        self.near(self.play, "ack", r"acknowledgment of the brief alone approves no unseen design or\s+tasks")
        self.near(self.play, "never confirms", r"Explore never confirms a planning gate")
        self.lacks(self.play, r"brief (is|counts as) (the|a) (spec|confirmation)", "brief as spec")

    def test_the_existing_planning_path_with_every_gate(self):
        self.near(self.play, "path", r"existing planning path, every gate",
                  r"Requirements → design → tasks → consistency check →\s+classification → implementation",
                  r"security-reviewer", r"feature review", window=300)
        self.near(self.play, "amendment", r"only the affected amendment", r"unchanged accepted work is not rewritten")

    def test_requirements_start_from_intent_not_the_experiment(self):
        self.near(self.play, "intent", r"Requirements start from intent", r"intended behaviour and constraints",
                  r"not from whatever the experiment produced", window=300)
        self.near(self.play, "limits", r"open limit the brief names becomes\s+either a requirement or an explicitly accepted deviation",
                  r"never dropped in silence")

    def test_integration_units_and_one_patch_per_unit(self):
        self.near(self.play, "units", r"Integration units", r"producer\s+with its consumer",
                  r"not one task per administrative\s+step", window=300)
        self.near(self.play, "patch to unit", r"`\*\*Prototype:\*\* <path>`", r"one unit per patch",
                  r"`prototype: <path>`", r"after the tasks and classification confirmations",
                  r"every gate runs on the delivered result", window=300)

    def test_a_run_is_an_observation_not_an_oracle(self):
        self.near(self.play, "oracle", r"A run is an observation, not an oracle",
                  r"completion, not correctness", r"Reviewed observations become regression fixtures",
                  r"independent invariants and accepted constraints", r"decide correctness", window=400)
        self.near(self.play, "hardware", r"Simulator evidence never stands for hardware")
        self.lacks(self.play, r"run (becomes|is) the (golden|acceptance oracle|oracle)", "run becomes oracle")

    def test_one_negative_test_per_failure_mechanism(self):
        self.near(self.play, "negative", r"One representative test per distinct failure mechanism",
                  r"not one per failed attempt")

    def test_acceptance_probe_stays_user_authored(self):
        self.near(self.play, "probe", r"acceptance probe stays user-authored",
                  r"Run evidence never replaces its command or its\s+criteria")


class PlaybookStopAndMetricsTest(Base):
    def test_stop_rules(self):
        self.near(self.play, "stop", r"Stop Explore at once", r"outside\s+`boundary` or bypasses `actionPath`",
                  r"cannot be attributed to an attempt", r"cleanup cannot be verified", r"budget is spent",
                  window=300)
        self.near(self.play, "promote stop", r"Stop Promote when\s+a promoted unit loses a gate",
                  r"no verdict is reused from Explore")

    def test_amendment_count_is_a_metric_not_a_stop_rule(self):
        self.near(self.play, "metric", r"material amendments", r"diagnostic metric", r"not a stop rule")

    def test_metrics_recorded_separately(self):
        self.near(self.play, "explore metrics", r"Explore: attempts", r"setup and run", r"objects created and deleted")
        self.near(self.play, "promote metrics", r"Promote: tasks and\s+units", r"consistency rounds",
                  r"full-suite runs", r"material\s+amendments with cause", window=300)
        self.near(self.play, "separately", r"Record simulated duration, suite\s+runtime, elapsed delivery, external wait and billed usage\s+\*\*separately\*\*")
        self.near(self.play, "directional", r"directional, not a controlled benchmark",
                  r"zero attempts while a live system is down is\s+no evidence")


class OrchestratorTest(Base):
    """The pointer section and the rules that bind even without the playbook."""

    def test_pointer_names_the_one_definition(self):
        self.near(self.orch, "pointer", r"Explore → Promote — `playbooks/sdd-explore.md`",
                  r"read\s+`~/.claude/playbooks/sdd-explore.md` and follow it exactly", r"one definition",
                  window=300)
        self.near(self.orch, "binding", r"rules\s+hold even without the playbook")
        self.near(self.orch, "summary", r"no pipeline, no specs, no per-attempt approval, every project safeguard",
                  r"no extra gate")

    def test_explore_is_the_users_choice(self):
        self.near(self.orch, "choice", r"Explore is the user's choice", r"never inferred",
                  r"never a\s+mandatory taxonomy", r"feature without a grant runs exactly as before")

    def test_one_grant_per_feature_with_the_record(self):
        self.near(self.orch, "grant", r"One grant per feature", r"asked once", r"tooling-gap check",
                  r"`exploreAuthority: \{ grantedAt, grantedBy: \"user\", quote, objective, boundary,\s+actionPath, forbidden, budget, explorer \}`",
                  r"never revokes a project rule", window=300)

    def test_no_live_action_outside_the_path_or_boundary(self):
        self.near(self.orch, "outside", r"No live action outside `actionPath` or `boundary`",
                  r"permission the grant does not cover\s+needs a new user decision",
                  r"never improvises a route", window=300)

    def test_explorer_role_exception_is_recorded(self):
        self.near(self.orch, "explorer", r"explorer is a recorded role exception", r"By default the task-executor",
                  r"`mode: prototype`", r"you write none", r"`explorer: \"main session\"`", r"does not imply it",
                  window=300)

    def test_patch_manifest_and_ledger_rules_bind(self):
        self.near(self.orch, "patch", r"Every patch is saved with its manifest before its result is logged",
                  r"only\s+in prose cannot be adopted", r"deletion is verified", window=300)

    def test_budget_stop_binds(self):
        self.near(self.orch, "budget", r"Budget stop", r"Explore stops and reports",
                  r"never widen the budget\s+or the boundary yourself")

    def test_explore_never_confirms_a_planning_gate(self):
        self.near(self.orch, "gate", r"Explore never confirms a planning gate", r"evidence, not a spec",
                  r"requirements or amendment confirmation", r"`prototype: <path>`",
                  r"every gate\s+runs on the delivered result", window=400)

    def test_overnight_never_grants_or_widens(self):
        self.near(self.orch, "overnight", r"Overnight mode never grants or widens `exploreAuthority`",
                  r"starts no\s+Explore attempt")

    def test_state_keys_list_the_grant(self):
        self.near(self.orch, "keys", r"Keys this playbook adds", r"`exploreAuthority` and `explore`",
                  r"\{ attempts, status, reason \}", window=300)

    def test_critical_rule(self):
        self.near(self.orch, "critical", r"NEVER run an Explore action outside the grant's `actionPath` and `boundary`",
                  r"never grant, widen or infer `exploreAuthority` yourself", r"asked once per feature")

    def test_retained_prototypes_rule_is_kept(self):
        self.near(self.orch, "retained", r"Retained prototypes", r"`prototype: <path>`",
                  r"never recorded as a passed\s+task", window=600)


class ExecutorTest(Base):
    def test_manifest_read_first_and_limits_never_relaxed(self):
        self.near(self.executor, "manifest", r"Adopted prototype", r"`<slug>.manifest.json`", r"read it first",
                  r"adapt the patch when the base differs — never force it", window=600)
        self.near(self.executor, "limits", r"open limit the solution brief names", r"never\s+relaxed in silence",
                  r"`MATERIAL CHANGE`")


class TasksAgentTest(Base):
    def test_plan_from_the_brief_one_unit_per_patch(self):
        self.near(self.tasks, "brief", r"solution brief", r"`spec-memory/explore/solution.md`",
                  r"one integration unit \(rule 1a\) per\s+mechanism",
                  r"`\*\*Prototype:\*\* spec-memory/prototypes/<slug>.patch`",
                  r"one unit per patch, never a patch on\s+two tasks", window=400)
        self.near(self.tasks, "not adopted", r"patch no task adopts is listed under `Not adopted`")
        self.near(self.tasks, "negative", r"one negative test in the unit that owns the mechanism,\s+not one test per failed attempt")
        self.near(self.tasks, "evidence", r"brief is evidence, not a spec",
                  r"confirmed requirements\s+and design decide")

    def test_template_has_the_prototype_line(self):
        # A template field, not a rule: a raw presence check (the fenced block's backtick parity
        # defeats the negation heuristic of `near` here).
        self.assertTrue(prose.search(self.tasks, r"\*\*Prototype:\*\* <Optional[^>]*retained Explore patch this task adopts"),
                        "template: Prototype line missing")


class RequirementsAgentTest(Base):
    def test_requirements_come_from_intent_and_keep_open_limits(self):
        self.near(self.reqs, "brief", r"solution brief", r"evidence, not a spec",
                  r"intended behaviour and constraints", r"not from whatever the experiment produced",
                  window=400)
        self.near(self.reqs, "limits", r"Every open limit the brief\s+names appears as a requirement or as an explicitly accepted deviation",
                  r"none is dropped in silence")


class DocsTest(Base):
    def test_claude_md_states_the_policy(self):
        self.near(self.claude, "bullet", r"Explore → Promote", r"`playbooks/sdd-explore.md`", r"never inferred",
                  r"`exploreAuthority`", r"grants once per\s+feature",
                  r"no per-attempt approval, but every project safeguard", window=400)
        self.near(self.claude, "promote", r"no extra gate", r"observation, not an oracle")
        self.near(self.claude, "overnight", r"Overnight mode\s+never grants or widens `exploreAuthority`")

    def test_readme_lists_the_playbook(self):
        self.near(self.readme, "readme", r"sdd-explore.md", r"Explore → Promote")


if __name__ == "__main__":
    unittest.main(verbosity=2)
