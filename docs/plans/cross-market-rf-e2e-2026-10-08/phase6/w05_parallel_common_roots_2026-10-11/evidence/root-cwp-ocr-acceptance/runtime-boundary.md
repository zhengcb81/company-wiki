# W05-CWP-OCR: production runtime boundary review

- Date: 2026-10-11. Read-only review of delivered `codex/w05-cwp-ocr`, HEAD `6fe9a82a6a96fe024774791e2018c882a098d512`.
- Result: **FAIL, two P1 resource-boundary defects**. No product edits, real OCR, cloud calls, downloads, shared PWF edits or original-file writes. One in-memory synthetic fake-adapter probe.
- CodeGraph context/search/callers were attempted first. This canonical index returned no `enrich_pptx` / `normalize_document` symbols, so the explicitly identified delivery files and literal call sites were read directly.

## 1. P1: configured native OCR has no own hard deadline, including coordinator preflight

`src/company_wiki/document_normalization/local_ocr.py:595-608` performs model validation/loading and `_engine(pixels)` synchronously; deadline checks occur before work and after native return. A stuck native call prevents the return check. `ocr_composition.py:117-119` and `ocr_region_recovery.py:598-600` likewise call the adapter directly. Public normalize/replay do not supply a native process boundary.

There ARE existing isolated processes elsewhere; this is not a claim that the whole project lacks isolation. `source_catalog/normalizer.py:519-617` owns a multiprocessing parser, with Windows Job/process-tree termination and parent-liveness monitoring. That route wraps `_normalize_source`, not `NarrativeNormalization`. AUTO worker execution has supervisor child processes and batch-finally stop (`automation/narrative_batch.py:1627-1707`). However real coordinator preparation occurs BEFORE supervisor starts: `narrative_batch.py:1242-1257` -> `_current_sources` unknown-language branch `:172-174` -> `NarrativeNormalization.sample_text` `source_catalog/narrative_normalization.py:214,236`. Both `_prepare_ocr` model preflight and inference therefore may block the coordinator itself.

The delivery real E2E uses `threading.Timer` / `os._exit` in its test script, not production. A Python timer is also conditional on being able to execute while native code runs; it is not a general proof against native code retaining the GIL. The script restarts its 90-second timer for replay, so it does not establish one combined 90-second bound for both parse and replay. No claim of an observed orphan is made: this review did not run actual native hangs. The missing owned process boundary prevents proving deadline enforcement and cleanup for these public/preparation routes.

### The old test changed 2 -> 20 seconds

`tests/document_normalization/test_local_ocr_adapter.py:349-401`: only the TEST'S `subprocess.run(timeout=...)` changed 2 to 20, with a cold Windows interpreter/import explanation. The fake backend sleeps 30 seconds; ready marker and no-publish assertions remain. No product budget/configuration changed. This is reasonable startup tolerance for that harness, but it proves the harness parent kills its child, not that product normalize/replay/sample_text enforces `OCRLimits.deadline`.

## 2. P1: ROI total-pixel limit is checked after forbidden inference already occurred

`ocr_composition.py:114-116` accounts original image pixels before initial OCR. But `recover_regions` only increments its ROI counters (`ocr_region_recovery.py:590-599`) and calls OCR; it never reserves/checks the remaining request-wide `max_total_pixels`. Only AFTER all recovery calls return does the composer add `outcome.roi_pixels` and check (`ocr_composition.py:136-137`). The accumulator is shared across images, but the resource bound is an after-the-fact result rejection, not a bound while doing work.

Minimal in-memory counterexample imported the delivered test fake and normalized a synthetic 320x80 image with cap=25,601 pixels (only ONE ROI pixel remains after full image). Observed:

```text
max_total_pixels: 25601
allowed_roi_pixels: 1
transcribe_calls: [(320, 80), (290, 54)]
result: normalization limit exceeded: max_total_pixels=25601 (local OCR)
elapsed: 0.846 seconds
```

The 15,660-pixel ROI was decoded and transcribed despite remaining allowance 1. Existing `test_roi_pixels_are_charged_request_wide_not_per_image` asserts eventual failure but does not assert the over-budget call is never made.

## Minimum systemic repair recommendation

Prefer a **reusable owned child inside the configured `LocalOCRAdapter`** over isolating the entire `NarrativeNormalization` operation through the old catalog parser. The adapter seam covers all configured native calls from public normalize, replay, sample_text and preflight; one lazy child owns one CPU engine and amortizes engine/model startup across original + ROI images. Whole-parser isolation would require a new normalized-document/opaque-asset envelope and duplicate ownership for coordinator sample/preflight, and could reload the engine per parse/replay. No new authorization chain, task store or access gate is needed.

Edit seams:

1. `document_normalization/local_ocr.py`: split parent adapter from child engine construction/inference. Send immutable config + image bytes + absolute deadline, return bounded validated primitive OCR output. Parent watches the remaining SAME deadline during both model preflight and inference; on timeout/cancellation/error, terminate/reap owned child, reject success, clear stale handle. Provide explicit close/context ownership. Child parent-liveness guard and Windows Job/Unix process-group ownership must prevent an engine surviving parent death. Reuse existing `_bounded_process` / `_process_tree` ownership primitives where suitable rather than a second home-grown timer. Fake/user-provided `OCRAdapter` protocol remains compatible; no pickling arbitrary adapters and no real ONNX in CI.
2. `ocr_composition.py`, `ocr_region_recovery.py`: one request budget owns full-image AND ROI pixel reservations. Check/reserve the exact transformed size BEFORE generating/decoding or dispatching each ROI; insufficient capacity stops attempts with honest diagnostic status (or established resource error policy), never calls native OCR. Do not double-charge returned outcomes. Bound max-image size before transform allocation too.
3. `source_catalog/narrative_normalization.py`: model preflight must receive the effective request deadline (currently `_prepare_ocr` calls `validate_environment` without one). Carry the same request deadline through sample_text across images. Public calls with no explicit deadline need an existing configured finite default or one clearly defined OCR request default; choosing a fresh per-call timer would reset the budget for every ROI and leave the combined request unbounded. `normalize_document`/`enrich_pptx` and replay should resolve that effective deadline once at the outer OCR request. Cold startup time counts toward the request, not a new allowance.
4. Keep the adapter/algorithm fingerprint accurate if OCR execution/recovery behavior changes; verify old artifact/replay handling. Do not alter original source hashes or silently stamp old results as new.

Tests at one substantial node:

- TDD fake configured-native worker stalls in engine INIT and in inference, first full image and later ROI; parent finishes within requested bound + explicitly bounded reap grace, no success publication. No real OCR required.
- Deadline already expired makes zero native dispatches. One absolute deadline survives original + multiple ROI + second image and warm-child reuse; no reset between phases.
- Child death and parent death clean process ownership, descendants if supported; terminated PID is reaped, timeout cannot later publish or be reused; subsequent valid request gets a fresh child. Use readiness synchronization instead of a tight interpreter cold-start timeout.
- Pixel cap exactly equal/below next ROI size; assert fake transcribe call count before error, including second attempt and second image; rejected transformations do not allocate/transcribe oversize images. Request success accounting matches actual full + ROI work.
- Existing protocol/three-argument ImageOCRResult, score thresholds, stable bbox/locator/replay and unique-media cache tests remain green. ROOT real configured local slide7 once verifies 22 preserved + 2 definitions recovered, bounded owned process and exact source SHA, scratch restored. An E2E external emergency cutoff remains only a test emergency guard, never substitutes for the production deadline assertion.

## Scope passes

- A supplied absolute deadline is propagated unchanged across original/ROI/multiple-image composer calls and checked on each native return; no per-image deadline reset was found. This is cooperative enforcement only until P1-1 is fixed.
- Per-image 4-region/2-attempt/8-attempt ladder exists. Request recovery counters are shared and unique media is cached once.
- The test's 2 -> 20 change did not alter production resource limits.

## Reviewed source SHA-256

- local_ocr.py `9b3b02a3891ac6c06bdb34f9244ca84c4cc73a67338b02bfcb1d1f9c120bc6f9`
- ocr_composition.py `3b938a0fb2085713914f2593f7222d2318b26f2794515cf747dae67fc0979400`
- ocr_region_recovery.py `c021cee73e2509bfa2c5e70a7a12d03aef6b2ca60b18ccccab578ab3368fae2c`
- test_local_ocr_adapter.py `53d99507129c9f28d70de8fd0ea49408fabe966368ad7357f2fd7b8505c7003f`
