CLS — ARTIFACT CLASSIFICATION

Deixis: every reference below is to the project being worked on, never to the
repository in which this contract happens to be stored. This block is installed
into other projects, so "the worked project" is always the subject.

NON-CODE ARTIFACT — exactly one of:
  1. a spec artifact under `.specs/features/<feature-name>/` (`requirements.md`,
     `design.md`, `tasks.md`, `scope.md`, `.spec-state.json`);
  2. a committed prose/documentation file (for example a markdown write-up under a
     documentation directory or the feature's own directory) that the worked
     project's layout or steering does NOT designate as source, agent/prompt
     contract, template, script, or configuration;
  3. a knowledge-vault mutation recorded by `vault-writer` in
     `.specs/features/<feature-name>/vault/.write-log.jsonl`.

APPLICATION CODE — any produced or changed file that is not a non-code artifact:
  executable source, tests, scripts, hooks, CI workflows, templates, runtime
  configuration, and any prose file the worked project designates as a
  behaviour-bearing contract (for example `agents/*.md` and `commands/*.md`).

PRECEDENCE — asymmetric. The asymmetry is load-bearing. Do not make it symmetric.
  - A file named on the APPLICATION CODE side is application code
    UNCONDITIONALLY.
  - FEATURE-DIRECTORY RULE. Any file under `.specs/features/<feature-name>/`
    that is not named on the APPLICATION CODE side settles as a NON-CODE
    ARTIFACT WITHOUT the CHECK. This covers limb 1's plan documents and equally
    a recon or investigation write-up placed in the feature's own directory.
    The CHECK cannot be used here: every project loads the feature directory
    into an agent's context, so a CHECK over that directory always fails, and
    it would designate the feature's own requirements.md — and the very recon
    write-up this track exists to serve — as application code.
  - A file named on the NON-CODE ARTIFACT side by LIMB 2 or LIMB 3 is a
    non-code artifact ONLY IF the designation CHECK below is run and passes.
  - A failed CHECK is itself the designation: the file is APPLICATION CODE. An
    UNRUN CHECK is a failed CHECK. There is no fallback to the category tests.

CHECK — bounded designation check. Read the worked project's repository-root
  `CLAUDE.md`, the files that `CLAUDE.md` imports, and `.specs/steering/*.md`.
  The CHECK FAILS if any of them designates the file a behaviour-bearing contract,
  or loads the file into an agent's context. The CHECK FAILS if it was not run.
  The CHECK also FAILS, whether or not anything designates the file, where the
  file sits in a location a tool reads as agent instructions BY CONVENTION — for
  example a `.github/` instructions directory, a prompts directory, or a rules
  directory. Silence is not an exemption: an undesignated file in such a
  location is APPLICATION CODE.
  Do not follow an import into a credential store. A denied, refused or
  unreadable import is a FAILED CHECK, never a skipped one.

OPEN ENUMERATIONS — both lists above are illustrative, not exhaustive. A file's
  absence from either list is evidence of nothing. The single exception is the
  FEATURE-DIRECTORY RULE in PRECEDENCE, which is closed by LOCATION rather than
  by list: it settles files under `.specs/features/<feature-name>/`, and nothing
  else. It does not make either list exhaustive.