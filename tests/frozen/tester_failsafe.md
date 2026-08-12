
## When the Task Produces No Application Code

Some tasks produce no application code — a reconnaissance write-up, documentation, or a
knowledge-vault update. This section defines what you do instead of leaving the outcome undefined.

**Enter this section only on the orchestrator's payload.** The payload carries
`taskProducesApplicationCode`. Enter here only where its value is `false`. If the payload is
absent, unparseable, or the value is `"unknown"`, behave exactly as you do today — write tests as
normal — and say in your summary which of those cases applied. Never select this behaviour
yourself because a diff looked empty.

- **Do not write vacuous or placeholder tests.** An assertion that cannot fail, or a test that
  asserts a file exists where the requirement is about that file's content, is prohibited when
  written only to satisfy an expectation that tests exist.
- **Where the artifact is machine-checkable, write the check.** A structural or content lint over
  a markdown contract, a schema check, or a link check is a real test. Write it in the project's
  conventional test directory, following the existing patterns there.
- **Otherwise emit the block below** instead of a test file.
- **In all cases, still run the project's existing tests in the affected area** and report any
  regression, exactly as you do on the code path.
- **If the task in fact produced application code**, do not apply this section. Report the
  application-code paths to the orchestrator, which reclassifies the feature, and write tests for
  that code normally.

```
NO APPLICABLE TESTS
For each produced artifact:
  artifact:     <path, or the .write-log.jsonl entry that records it>
  requirement:  <the requirement ID this artifact satisfies>
  why no check: <why no automated check is feasible for this artifact>
Existing tests run in the affected area: <command> — <result>
```
