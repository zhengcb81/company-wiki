# W08 official JSON capture provenance — stable owner handoff

Status: SOURCE_STABLE / responsibility node tested, not whole W08 research accepted.
No vendor/model/network calls or fees; no production config/DB/raw, Git or installation writes. All new catalogs/original copies live inside a TemporaryDirectory beneath pytest tmp_path; every completed fixture verifies restoration to its original byte map. Public CLI processes close catalogs and then the owned directory is removed.

## Root cause and existing public contract

Actual M3 qa-first-form-receipts.json captures declare `url`, `method`, `content_sha256`, `response_bytes`, `complete` and response observation fields. The planned later local import stores the old row under `capture_receipt.original_capture_observation`; it does not fabricate a new HTTP event. Previously `_commit_shared` discarded that URL for the primary source fact and wrote `https://official.invalid/shared-json`. Existing capture provenance remains in the immutable sidecar, but SourceExportBundleV2 only projects source_reader.describe_version, whose source_url comes from the indexed acquisition declaration. Public projection export provides parent refs and spans, not the capture URL; a consumer cannot obtain the actual primary URL from its existing manifest.

## Minimal implementation and exact interface

- `official_json_import._captured_source_url(receipt: dict[str, Any]) -> str | None`: use an existing direct `receipt.url`, or when that field is absent, the existing `original_capture_observation.url` only with matching content_sha256 and response_bytes. These are observed capture fields; no JSON body URL, issuer name, event namespace or HEAD request is used. An HTTP(S) URL must be nonempty, bounded, contain no whitespace/control characters, have hostname and valid port, and contain no credential userinfo. Missing, malformed or another-page observations return None; they do not reject raw import.
- `_commit_shared` passes that single value to the existing shared original writer. The same method handles retained recovery, so recovery cannot revert to the placeholder.
- `canonical_writer` changes only `_SharedOriginal.source_url` and `import_shared_original_staged(..., source_url: str | None, ...)` annotations. The existing scanner, reader and v2 wire already support null. No schema change, optional request field, policy/signoff, extra export payload or consumer parser was added.
- Existing same-SHA rows remain first-capture immutable: no sidecar/primary metadata replacement on dedup. The test constructs the true old writer path with a placeholder, reimports the exact bytes with a real capture URL and proves the original legacy row/bytes remain unchanged. This does not migrate historical placeholder rows; those require a separately justified metadata/provenance correction if needed.

## TDD and one concentrated node

1. RED: new public tests 6 FAIL in14.71s, all expose the actual placeholder URL. Two pages/two issuers project/persist/reopen/replay/export already succeeded before the final URL assertion; retained-copy failure and same-capture recovery likewise reached the wrong exported URL. Original log retained.
2. Implementation plus narrow same-page-size and old-immutable-row controls: 58-test import/writer/official JSON concentrated group produced57 PASS/1 FAIL in26.53s. The sole failure was the new test assuming indexed source_url lived at metadata_json top level; scanner's existing storage schema is `metadata_json.acquisition.source_url`. Its public URL assertion had already passed. Production source was not changed to fit that test.
3. Only that assertion was corrected to its real persistent container. The same public two-parent/two-issuer CLI case then1 PASS in9.10s. Union of the concentrated node and this targeted correction is58 passing responsibilities; no repeated whole suite. Logs preserve the original57/1 result and final targeted result separately.
4. Ruff0, mypy0 in2 source files; final Ruff0 after the persistence-container test correction. No skip/xfail or loosened expected URL.

Covered controls: shared two-originals only; both issuer projections bind the same parents but distinct issuer records; source manifests publish true URLs and unknown publication/owner facts; reopened export matches; duplicate returns sameRef/download_events0 and keeps original bytes/config/export; direct capture URL; absent URL; userinfo-invalid URL; wrong parent SHA or size cannot be promoted; BODY URL is never provenance; failure retains exact bytes/receipt; recovery and completed-output reuse preserve the same capture; old immutable placeholder remains immutable. No paid workflow or research completeness claim.

## Remaining boundary

This producer fix makes newly imported SSE pages' source manifest usable without every RF/FF consumer reading a sidecar. It does not import the86 real pages, qualify their as-of/publication date, execute selection/model batches or finish three-company RF/four independent reviews. No historical immutable record is silently repaired. Full MAIN release, normal commit/push/exact CI and PWF integration remain ROOT responsibility.

## Frozen files

- `src/company_wiki/source_catalog/official_json_import.py` SHA256 `83402ff4aece891ff55cb3c000334363be062a440b3ff8460ebec54114346f9b`
- `src/company_wiki/source_catalog/canonical_writer.py` SHA256 `26d9c475442f5438b19b8ad6a1c8578d0f14cfd13660b5955fd04c75a798e70f`
- `tests/integration/test_official_json_capture_provenance.py` SHA256 `84c1abf4b1c7d28314383840094822105c5982e45dd06f688ce171608ecfbf74`

## Original evidence bytes

- `RED.log` SHA256 `7f58c26e568c5ea69e520d3f9443b55db2198e67200a476fb69fe1ad6bec561c`
- `GREEN.log` SHA256 `229fd90569457bed04b19d166178ed9fbf572df7bffbe2ca3bd8a828509d4fcf`
- `GREEN_final_targeted.log` SHA256 `3064ac7c6271fed31c2f83a54238456bca9a1e3c7baa6a49124de0a3e6bc86a0`
- `ruff.log` SHA256 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`
- `mypy.log` SHA256 `0c37c4158c91ef55c724ba017bf6465f26018199badb08e3ff13f98acdf056c2`
- `ruff-final.log` SHA256 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`
