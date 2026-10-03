# CI migration snapshot race — 2026-10-03

## Cause and narrow correction

Remote company-wiki CI run `37121441436`, commit `6ab25373`, failed only
`test_m14_concurrent_init_produces_one_v2_schema`; the captured error was
`UnknownSchemaError("unrecognized tables in uninitialized database: ['runtime_gate']")`.
The Unit job otherwise passed 1,115 tests in 14.91 seconds.

`_classify_existing` used a read-only connection with `isolation_level=None`.
Its `PRAGMA user_version` and subsequent `sqlite_master` query therefore used
separate autocommit snapshots. Another initializer could commit the atomic v2
migration between them. The classifier then combined version 0 with the v2
table list, an impossible schema state that legitimately triggered rejection.
Neither SQLite write migration atomicity nor the test's concurrent contract
was defective; the preflight reader needed a consistent snapshot. WAL opening
retries and longer timeouts cannot repair this logical inconsistency.

The product change is three added lines in `_open_readonly_connection`: an
explanation and explicit `BEGIN` after read-only connection configuration.
Classification, read-only v2 validation, and `validate_database` now share one
read transaction. Existing callers close the connection in `finally`, releasing
the snapshot before a write migration. The write transaction still rechecks
the schema version after `BEGIN IMMEDIATE`, so a concurrent completed migration
remains a successful no-op.

No DDL, backup policy, corrupt-file handling, version handling, timeout, retry,
schema-validation requirement, or existing M14 test was removed or weakened.

## Deterministic regression and results

New stable node:

```text
tests/unit/test_automation_migrations.py::test_m14_classification_uses_one_snapshot_during_concurrent_init
```

The fixture is a real empty WAL SQLite database. An Event schedules a second
real `migrate_database` call to commit v2 after the first caller reads version
0 and before it reads tables. The patched version-read helper only controls
this schedule; it does not invent schema data or exceptions. There are no
sleeps. Both Event waits and the thread join are bounded. The setup connection
is explicitly closed, and the writer is joined in `finally`.

The reader must succeed with no applied migration, the writer must apply
versions `(1, 2)` exactly once, their schema fingerprints must match, and the
final database must validate as the exact v2 table set with successful integrity.

| Node | Result |
| --- | --- |
| New deterministic node against unchanged product code, Windows | RED: the exact remote `UnknownSchemaError` with `['runtime_gate']`; 1 failed, 0.39 s |
| `test_automation_migrations.py` + `test_automation_migrations_v2.py`, Windows/Python 3.13.9 | GREEN: 32 passed, 2.16 s |
| Same two files and same source, actual Ubuntu WSL/Python 3.12.3 | GREEN: 32 passed, 3.19 s |
| New node after explicit fixture-connection closure and unrelated format restoration, Windows | GREEN: 1 passed, 0.35 s |
| Ruff check of the two owned source/test files | Passed |

The scoped suite includes existing concurrent M14, immutable invalid-file M15,
v1 backup-hook checks, DDL rollback, exact structure/drift checks, future-version
rejection, and read-only v2 repetition. No full repository suite or extra gate
was introduced by this lane.

WSL already had pytest 9.0.3 but lacked `pytest_timeout`. The first attempt
failed while importing that plugin, before collecting tests. The successful
run used existing pytest without optional plugin autoload; no dependency was
installed. Both platforms emitted the existing `asyncio_mode` configuration
warning when that optional plugin was not loaded.

The root coordinator adds only the deterministic node to the existing fast CI
regression list and extends the existing commit-smoke path matching to these
two files. The broader suite is not made mandatory for every commit.

## Isolation and handoff

Windows test roots are exactly `.ci-m14-red` and `.ci-m14-green` under the
repository. Linux uses exactly `/tmp/cw-ci-m14-green`; all are temporary test
data, and are removed after validation. No production database, raw document,
B3 archive, configuration, root planning file, other repository, Git index,
commit, or push was modified by this lane.

Final code scope is three added product lines and one new regression test.
All unrelated formatter changes were restored. Root owns publication,
planning updates, remote CI observation, and subsequent B3 production apply.
