# Final functional acceptance and immutable legacy-effort history

Date: 2026-10-10. Status: PASS for this responsibility boundary.

## Scope

- MAIN isolated worktree: `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`.
- Source write set: only `src/company_wiki/automation/narrative_batch.py`, at the two resume expected/manifest comparisons and their small comparison/read-history helpers.
- Test write set: only `tests/integration/test_narrative_legacy_effort_history.py`.
- ROOT owns staging, merging, PWF status and project completion. No commit/merge/install/production/config/original modification was performed by this task.
- This is real public CLI functional validation, not an independent component review of this agent's earlier adapter/select/verify implementations.

## Root cause and narrow fix

The previous gen1 producer omitted `reasoning_effort` from the generation manifest while HTTP could receive an explicitly configured effort. The fixed producer binds actual effort, so a completed old run's immutable manifest no longer equals a recomputation. Old records must remain unknown, not be rewritten to current effort.

`_completed_history_generation_matches(expected, manifest, *, completed_history)` is a pure comparator. It permits only the missing gen1 model field, only for completed read history. It copies the expected model before removing the field and leaves both inputs unchanged. Generation2, existing/null effort fields, other model fields, source inputs and all other generation fields remain exact comparisons.

`_completed_read_history(reader, store, jobs)` requires:

1. Every scoped job is already terminal under the existing coordinator's terminal semantics.
2. Every existing effect has an actual delivered outbox and verified/applied effect state; a missing outbox is refused.
3. Every succeeded verify job has a publication effect.
4. Each publication is actually visible through the source artifact reader. ACK without activation is refused, so history normalization cannot enter the `activation_pending` worker path.

Both resume paths preserve the saved manifest/hash, event, pin, execution binding and fee ledger. Active model work, undelivered outbox and prepared-only artifacts still raise typed `BatchResumeError(BATCH_FROZEN_BINDING_INVALID)` before worker/model execution. New low/max runs retain distinct generation SHA and cannot reuse an effort-unknown old artifact.

## TDD and responsibility evidence

- True RED: real raw source import/catalog -> actual worker/model loopback -> publication/terminal compaction -> frozen old gen1 binding -> current resume rejected `BATCH_FROZEN_BINDING_INVALID`. The producer omission was reproduced through a test-only monkeypatch before generation creation; no old production record was edited. See `legacy-effort-red.log`.
- Initial focused GREEN: raw1 history + narrow comparator. The subsequent final run covers both public request versions.
- Existing historical-version compatibility: `test_narrative_batch_budget_and_resume.py`, **1 PASS / 51.12s**, see `legacy-effort-old-resume-compat.log`. This is separate responsibility compatibility evidence and is not added to the final 9-case count.
- Static: Ruff 0; mypy 0 on batch source. See `legacy-effort-static.log`.

A separate real raw-only request2/binding4 failure was identified during RED: the factory required projected execution versions based on the container schema despite having only raw work. The factory owner fixed classification from actual frozen projected work and supplied projected-version negative controls. Actual raw-only request2 worker/publish/history recovery is GREEN in this final run. The factory write was performed by the other owner, not this task.

## Final concentrated functional acceptance

Exactly **9 distinct pytest cases PASS / 80.38s** in one concentrated invocation:

| Responsibility | Cases | Assertions |
|---|---:|---|
| Mixed public CLI | 5 | Two issuer projections share complete parents plus raw TXT; first execution, same-run resume, cross-run reuse, refresh, partial reuse, real public bytes/evidence/terminal records; changed second-parent bytes, inactive second parent and wrong projection SHA refuse before model/AUTO initialization |
| Complete empty-native public CLI | 1 | Real import/worker/publish/public read/evidence-list/compaction/reuse; explicit unknown language, complete zero evidence, 0 POST and 0 model reservation |
| Legacy history | 3 | Both public request versions; actual low HTTP config; original old field absent; public history resume adds no POST; all AUTO/catalog table dumps, manifests/events/pins/fees and raw bytes unchanged; old/low/max keys distinct and old artifact not reused; active/pending/non-visible rejection; strict pure comparator and mutation isolation |

`final-mixed-empty-history.log` and `final-mixed-empty-history-receipt.json` are authoritative invocation evidence. Prior partial GREEN, the separate old test, and other agent responsibility suites are not cumulatively added to this count.

All HTTP was loopback. External provider calls: 0. External model calls/fees: 0. Fixture synthetic pricing remains measured in the test ledger and is asserted. Owned TEMP and Windows relocated basetemp were removed; the fixture's preexisting file and original test directory were restored. Source/test SHA snapshots before and after were identical.

The existing coordinator may create/acquire an empty generation `.lock` control file during history reads. ROOT explicitly accepted this control-file exception; no claim of zero filesystem control writes is made. Original documents, catalog/AUTO records, manifests, artifact bytes and charges remain unchanged.

## Frozen final SHA

- `src/company_wiki/automation/narrative_batch.py`: `7e17b29becfee0dbd22a753a0123e58ad7206130dfc5e2ba01009b26cae08dfd`
- `src/company_wiki/automation/narrative_worker_factory.py`: `69733204127ac7b1e7d76c2d3c3b206d9f1cf32c4f43a9d4007f4364b022457e`
- `tests/integration/test_narrative_legacy_effort_history.py`: `57828622b410a6e54020027085e9def2b3d61a98a52eaa74a4599e0978283412`
- `tests/integration/test_official_json_batch_e2e.py`: `a65e9adc35178bf3d6847797cb5f2f182916e96220d464be5c03b65055f2f3a3`
- `tests/integration/test_official_json_empty_batch_e2e.py`: `36caeee6b1d29268ec135f426394060b82ccbfb0c1ca43b18553706924798703`

No unresolved blocker was found in the final responsibility suite. This does not claim the whole AUTO/PWF project is complete or expand approval gates. Source writes are now stopped; ROOT may integrate.
