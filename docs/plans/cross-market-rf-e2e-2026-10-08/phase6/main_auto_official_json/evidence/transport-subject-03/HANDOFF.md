# Transport subject foundation handoff

Scope: only the three transport/replay source files and two new tests in handoff.json. No commit, provider/model request, config/install/database write outside owned TEMP. This is not acceptance of full AUTO.

## Frozen APIs

- `NarrativeRef`: old first five constructor positions retained; optional `source_ref`, appended typed `subject_binding: NarrativeSubject | None` and `generation_sha256: str | None`. `.subject` derives neutral raw binding for ref1. Ref2 exact wire excludes raw anchor.
- `NarrativeReadRequest`: old positions retained; appended `expected_issuer`. Read2 exact wire accepts null or partial concrete six issuer keys; no fiscal identity.
- `parse_projected_reference_request(value) -> tuple[NarrativeSubject, str]`; old parser unchanged.
- `NarrativeTransportReader(..., projection_loader: Callable[[NarrativeSubject], VerifiedProjectionView] | None = None)`.
- `reference_subject(subject, *, generation_sha256)` uses exact subject/generation catalog query. Metadata-only discovery does not open source/model.
- `read` branches on ref version. Ref2 uses `read_current_subject` exact artifact/hash/size/generation/current all-parent SQL relationships; then one source-owned loader/export; exact full subject and verified original native spans replay.
- `replay_verified_projection(view, selected) -> int` is shared by public read and future verify handler. It does not export/open parents again. Only selector annotations may be added. Rawtext/token/pointer/parents/parser/role/language/coordinates/quality/source facts must match. Text hash and unit kind annotations are checked, as are actual DTO source language and parser generation.

Receipt2 exact keys: schema_version, status, narrative_ref, subject_binding, parent_source_refs, as_of_date, observed_at, locator_count, selection_status, quality_status, replay_status. observed_at is this read event clock, not an invented parent-source timestamp. No whole records, paths, financial identity, review approval, or policy receipt.

## TDD and verification

RED unit: 24 fail/15 pass; RED integration: 17 fail/39 pass; additional re-signed metadata RED: 2 genuine failures. Final 116 passed/1 explicitly deselected in 29.54s; Ruff zero; mypy zero in three source files. New 58 tests all green; legacy 58 green.

Known excluded legacy test `test_current_reader_preserves_older_summary_above_new_generation_targets` fails during published_fixture's model step before any transport call: ReplayNarrativeModel emits >280 character evidence as claim, summary model rejects CLAIM_TEXT. Parent owns shared model/fixture resolution. Initial full failure retained in green-tests.log; no test weakened/removed. This is not a full-green claim. Re-run complete 117 after that parent fix.

Integration uses real import request2, persisted projections, two shared parents/two issuers, artifact prepare/activate and source export. It checks exact generation, A/B isolation, legacy latest exclusion, second-parent bytes/state/primary refusal, corruption non-cache-miss, source loader once per read, issuer/cutoff prechecks, re-signed locators and language/parser false metadata, all original raw bytes and document/source ID inventories retained. TEMP and relocated pytest directory cleanup evidence is in logs. Synthetic bundles are constructed locally; tests do not evaluate model summary quality or full three-job DAG.

## Next owner steps

Connect public CLI/verify handler and mixed batch runner to these same APIs. Add genuine loopback HTTP three-job E2E, then whole MAIN integration node. Ref2 source_ref is None: consumers must branch before raw access and must never publish an anchor as the projection identity. Source port owns actual all-parent bytes/issuer/as-of verification; catalog owns SQL state, transport owns exact ref/locator replay; do not repeat source exports.
