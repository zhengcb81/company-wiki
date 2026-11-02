# Run binding metadata cap — incremental independent review

PASS_INCREMENTAL_ENGINEERING_ONLY. No actionable P1/P2 finding in the three frozen files. All3 source/test SHA matched before and after execution.

The two-line post-serialization262144B veto is removed from NarrativeRunStore.create_run. Canonical JSON, exact source/job scope, immutable run identity, price/token/output limits, atomic persistence and changed-binding conflicts remain. The batch change is a docstring only. Actual _run_prepared passes _frozen_binding into create_run, so the serializer and ledger are directly connected rather than maintained by a separate bypass.

An independent in-process control used the actual production _frozen_binding with417 unseen synthetic source records, then the public ledger API: full canonical metadata reopened byte-exact, identical request returned the same record, changed canonical metadata raised RunConflictError without changing the original, and noncanonical JSON raised ValueError. Existing limits300tokens/180microUSD/200outputbytes and empty reservations were preserved. Precise runtime/metadata length/hash are in JSON. No model, download, originals or existing catalog was used. This did not rerun23/87 or whole suites.

The CLI read(262145) is a real request-file reading budget, not a second cap on already serialized opaque metadata, and stays outside this change. No schema, source identity, paid-unknown/CAS or resource owner was changed. Scope is this engineering delta only, not true paid recovery or full PWF acceptance. ROOT may combine this review with existing selected tests for normal publication. Native cleanup of the owned initial-absent temporary ledger tree is recorded in JSON.
