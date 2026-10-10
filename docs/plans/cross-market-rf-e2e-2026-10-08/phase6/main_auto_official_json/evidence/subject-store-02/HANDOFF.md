# MAIN subject artifact storage node

## Delivery scope

Only source_catalog/narrative_artifact_store.py and tests/integration/test_official_json_subject_artifacts.py changed by this lane. No AUTO/contracts/CLI/projection leaf/config/installation/shared PWF changes. No commit.

## Frozen interfaces (Store and ReadonlyReader)

- visible_subject_generation_candidates(*, subject: NarrativeSubject, generation_sha256: str, limit: int = 32) -> tuple[NarrativeArtifactVersion, ...]
- read_current_subject(*, artifact_version_id: str, subject: NarrativeSubject, generation_sha256: str, expected_sha256: str | None = None, expected_size: int | None = None) -> tuple[NarrativeArtifactVersion, bytes]

## Actual metadata contract

Projection metadata requires subject_binding equal to NarrativeSubject.to_dict() (kind official_json) and generation_sha256. Existing raw metadata with missing/null subject binding remains compatible; optional explicit raw subject binding is also supported. The catalog treats generation SHA as opaque causal identity, not a model authorization or a proof that generation_manifest matches current model settings. AUTO remains responsible for building/verifying generation_manifest and its SHA; the source port remains responsible for original bytes, projection replay and issuer semantics.

Real first parent is only the existing document/source/SHA FK anchor. Prepare, activate, effect metadata read, subject candidate discovery and subject exact read all verify every declared parent remains active primary with its catalog SHA. Exact reads check every parent before and after opening artifact bytes. Full subject context is matched, not merely projection ID/SHA. Repeated parent observations are retained; duplicate relation checks are deduplicated locally.

Legacy raw latest/read_exact/read_visible and generation candidates exclude official_json artifacts. There is no virtual source/document, new table, migration, task ledger, permit or receipt gate. New Store methods reuse the existing readonly reader implementation; no writer transaction spans an object read. Subject candidate limits retain the existing 32 default / 100 maximum. JSON subject candidate lookup currently has no expression index; do not claim a large-library benchmark from this tiny fixture.

## Evidence

- red.log/red.json: 24 real failures before implementation. The separately retained launcher-error-01 was a pytest argv construction error, not RED evidence.
- green.log/green.json: 72 passed in 52.45 seconds (29 new subject tests, 43 pre-existing raw/generation/terminal/layering tests).
- static-final-ruff.log: Ruff exit 0 over final source and test.
- static-2.log/static.json: mypy exit 0 over the unchanged final source.
- handoff.json: current owned file hashes and base HEAD.

The first GREEN attempt exposed a test-fixture assumption: public importer also registers provenance sidecars, so two original pages have four sources. The fixture now compares the full actual pre-operation source/document ID inventory rather than guessing a source count. A second fixture mistake returned the prepared snapshot after activation; it now returns activate's real visible snapshot. Product assertions were not weakened. Those failed attempts are retained.

Every new test uses real official import and projection parsing in an owned temporary catalog, then exercises the actual SQLite/object store. Originals remain exactly two files with matching bytes, and the source/document ID inventories cannot grow during artifact work. The final runner's requested TEMP is removed; pytest's path-budget relocation also explicitly reports cleanup removed=true. No external provider/model calls or new API charges. Local replay models appear only in the pre-existing compatibility tests.

## Next MAIN integration

Use the subject-aware methods for projection pin/reuse/final read, keep raw methods for historical raw DTOs. Pass the exact generation SHA. Final bundle/effect/pin must use the same neutral subject and generation; dispatcher/publish/public read must still verify source bytes and semantics at their source-owned boundaries. This node does not implement or sign those AUTO steps.
