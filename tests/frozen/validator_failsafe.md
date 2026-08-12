
## Artifact-Conformance Mode

A feature that ships no application code still has to be validated. This mode validates produced
artifacts against the cited requirements, in place of validating code against them.

**Enter this mode only where `taskProducesApplicationCode` is `false`.** That is the whole entry
condition, stated positively so that no other combination can satisfy it. The payload carries
`featureClass` and `taskProducesApplicationCode`, and it arrives on **every** per-task invocation —
including every task of a `"code"` feature, where it carries `true`. In every case other than an
explicit `false` — `true`, `"unknown"`, an unparseable payload, or no payload at all — run ordinary
validation and say in your verdict which case applied. Never select this mode yourself because a
diff looked empty.

In this mode:

- **Map every cited requirement to at least one named produced artifact** — a file path, or an
  identified entry in `.specs/features/<feature-name>/vault/.write-log.jsonl` — and read that
  artifact. A requirement with no named artifact is a FAIL.
- **Each mapped artifact must exist, be non-empty, and substantively state or deliver what the
  requirement demands.** A placeholder, a stub, or a TODO-only file is a FAIL.
- **The "at least one test exists for this requirement" check is replaced in this mode only.** The
  absence of a unit test is not a failure here. That check stays unconditional on the code path.
- **Where machine checks were written for a produced artifact, run them.** Any failure is a FAIL.
- **If the executor modified application code, refuse the exemption.** Return FAIL and report the
  offending paths, so the orchestrator reclassifies the feature onto the code path. Judge the
  **executor's** output, not the tester's: a machine check the tester wrote under its no-code
  behaviour lands in the project's test directory, which the transmitted `CLS` block classifies as
  application code. Reading this bullet broadly would therefore reclassify a perfectly legitimate
  non-code feature — and reclassification is monotonic, so it cannot be undone.
- **The scope check and the quality check stay active**, unchanged.
- **The all-or-nothing rule is preserved**: every cited requirement must pass, or the verdict is
  FAIL.

Your verdict adds a `### Mode:` line reading `artifact-conformance`, and names, per cited
requirement, the artifact that satisfies it. Emit these additions **only** in this mode, so the
code-path verdict format is unchanged.
