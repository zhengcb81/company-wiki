# MAIN local PPTX OCR handoff

Status: this isolated implementation package is delivered. MAIN public batch/select/verify/NarrativeRef wiring and final cross-run/live integration remain MAIN-owned and are not claimed complete here.

- Base: `964886f887347c7a789402347f9ecd3172cf8c8c`.
- Tested implementation head: `a9534e5fb52e00c60b6b8cc5e015b4990f0eec6c`.
- Branch / delivery ref: `codex/main-local-pptx-ocr-20261009`.
- The normal documentation follow-up commit containing this file/manifest is the final delivery head; resolve that ref. The manifest binds the implementation head and final file hashes without a self-referential hash. No merge or push performed.

## Concrete API contract

`normalize_document` remains pure by default. Current HTML stays1.0.0/DOM1; current pure PPTX is1.1.0/shape2 with display ordinals and separate OOXML slide_id; explicit old PPTX1.0.0/shape1 keeps the old IDs and is read-only replayable. Historical replay ignores a currently configured global OCR adapter (zero inference). Unknown/empty version is refused; old locator meanings are never silently upgraded.

Explicit local OCR composition is2.0.0, locator cwp-pptx-image-ocr/1, with source SHA/display page/shape/media SHA/config fingerprint/bbox/text binding. Use `LocalOCRConfig.from_dict`/`to_dict`, `LocalOCRAdapter`, `OCRLimits` and `normalization_identity`. Exact live pathless fingerprint: `7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d`. Full actual identity is in real_22_page_statistics.json; verified_local_config.json is a non-secret machine inventory, not a production default.

`from_dict`, constructor and identity/fingerprint have no I/O or inference. Optional controlled `adapter.validate_environment()` verifies local hashes, exact RapidOCR/ORT/default-config versions, embedded dictionary and CPU engine initialization without calling image inference. Every actual worker owns its adapter/native engine; first `transcribe` performs validation. No model/provider inference guessing or automatic fallback/download/install.

`replay_evidence_spans(original, *, source_id, source_sha256, mime_type, evidence_spans, limits, ocr=None, ocr_limits=None) -> int` verifies the package once, then infers only verified selected media once per SHA. `replay_units` returns matching texts; `replay_unit` remains compatible. 10 spans/2 media=2 inference calls even with another image present. Config/media/shape/box/confidence/text/coordinate forgery is refused. Replay selected scope never proves full source coverage.

## Actual acceptance evidence

- Initial responsibility RED: actual slide IDs256/260 vs expected pages1/2 and missing explicit OCR API, 2failed/0.70s.
- Concentrated deterministic suite:81PASS/14.51s; final concrete legacy/current-config/empty-version/no-inference preflight tail4PASS/0.49s,15deselected. No broadened tests or second22-page rerun after the accepted node.
- Ruff: PASS for owned modules/new tests/all3 real runners; diff-checkPASS.
- Actual public official local import in owned TEMP -> SourceRef2.0 -> SourceVersionReader byte read: realSHA/4016522bytes, MICROSOFT CORP/MSFT/US/investor_relations; published_date=null, no inferred dates. Frozen alias src_presentation now mapped to an actual API-produced SourceRef in the receipt. Import download_events=0.
- Full real fixed22-page deck:1067lines,22unique-media calls,145.549077s. Selected8spans on4media:16.570420s, one package replay. 0network attempts/0supplier POST.
- One bounded page18 numeric QA:6raw excerpts, initial+replay2calls/14.822453s,0network; visible digits match, no financial-cell inference. No more real OCR is needed for this package.
- Parent hard deadlines:240s full check,60s numeric; native call remains noncooperative. Deterministic sleeping-adapter test proves outer kill before success publication.
- Owned TEMP catalog and six visual QA images+marker removed in finally/owned cleanup; originalSHA/size/mtime and three installed modelSHA unchanged. No production config/install/other repo was written.
- Normal commit; configured .githooks/pre-commit and commit-msg absent. Manual gates above are real; no hook pass claimed.

## Quality limitations MAIN must retain

Full-source recall is unverified: coverage_complete=false and all22image pages remain opaque/reviewable. Meaningful page7 transition first line and page18 restatement subtitle are absent, beyond small footer issues. Footer lacks last letter despite0.98347confidence; whitespace/LinkedIn errors also have high confidence. Pages11/20/21 each contain one detected low-confidence line. Page12 columns and page18 numeric row are interleaved by deterministic top-left box sorting; OCR does not identify financial cells or restore paragraph semantics. Exact selected spans and full-document correctness are different guarantees.

MAIN may retain independently replayed reliable high-confidence operating spans with source partial quality. Failed/unattempted images, parser errors and low-confidence selected spans remain named refusal/partial. Do not claim all body read, complete recall or exact numeric table conversion. No human gate is introduced.

## MAIN-owned remaining work

Follow INTERFACE.md for explicit config serialization into bounded worker/current read, finite language sampling, per-format parser routing, selected-span replay, and source-level versus selected-span quality. Include pathless OCR identity/fingerprint with source/parser/prompt/profile/version in the reuse owner's generation manifest. Recorded historic config must match replay; model absence or SHA/config mismatch must fail explicitly, not silently use current models. Explicit refresh/new config creates appropriate derivative generation.

Shared files remain untouched: automation/narrative_formats, batch_request/batch/worker_factory/runtime/select/replay/verify/transport and source_catalog official_source_flow. MAIN supplied its separately tested current public PPTX import during the TEMP check; its code is not in this package. Production installation and full public batch→select→verify→NarrativeRef read are not validated here.

All machine-readable evidence, concrete API examples, partial quality and restored environment records live in this package. handoff.json lists changed files and normalized-LF SHA256 values, excluding its self hash.
