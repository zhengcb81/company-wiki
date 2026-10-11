# W05 OCR native runtime: independent post-deadlock review

Date: 2026-10-11. Product non-author review. Product tree: `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`, base HEAD `f10a8a677b022ea81c1f00f4c4f929c6385e8930`.

## Decision and exact scope

**PASS for the frozen Windows native process boundary and stdin/UCRT correction. Overall resource-cap acceptance remains pending ROI preallocation repair.** ROOT has assigned that repair separately. This report does not authorize a different source freeze, report a POSIX runtime PASS, or certify company/forecast economic quality.

Reviewed freeze:

- `isolated_ocr.py`: `edade53c3c0fed2cb47ab115dbc969e1bd18be183280ee67a086fc876623d396`
- `test_isolated_ocr.py`: `cae823beff8cf78d49fd28cd4621aa12596868b517f462d9fcd7dfeba5013c04`
- `narrative_normalization.py`: `b29a4fe2069713800d171c30ecd09d7bcf3a35984ef2f872ed85d8d4986ccbfd`
- Preallocation review uses `ocr_region_recovery.py` `2803919d0f9b816c5cff45cf6344709abea8104f124945d9a3da24862417823e`, `ocr_composition.py` `9a4d517114d6bcd4b692eee4520c9fc2d16f6caa84854f348d1c655d668bd9fe`.

Only this `independent-post-deadlock/` folder was written by this review. Product, Git state, shared PWF, original materials, config, previous independent reports and old FAIL records were not changed. Original committed FAIL files and the prior independent manifest are reconciled in `review.json`.

## Native correction is supported by causal evidence

The old native worker blocked a duplicate thread in `os.read(0, 1)`. On Windows this held UCRT descriptor 0's lock. Native `_fstat64(0, ...)` could then block while NumPy imported through RapidOCR. The diagnosis separates this from slow inference: ONNX initialization had not started; model verification completed; the native import never returned. Python `os.isatty`, native `_isatty`, and `_get_osfhandle` were passing controls. Actual `_fstat64` was a business RED at the unchanged 1-second native metadata deadline. Removing the worker stdin-reader thread corrected this common runtime cause; delaying it until after imports would retain the future native-call defect.

The correction leaves ownership outside the native interpreter:

1. Windows Job is created with non-inheritable default security attributes and `KILL_ON_JOB_CLOSE`. The waiting bootstrap is assigned before its single release byte. Native worker and descendants inherit that Job. Timeout, close and owner death terminate the owned tree independently of a held GIL. Before assignment/release, parent pipe EOF exits the bootstrap without launching native work.
2. The POSIX guardian is a separate process/session, watches EOF and kills the owned group. Its stdin read does not share the native worker's CRT lock. **Static review only; not run on Windows.**
3. One pinned minimum absolute deadline includes cold startup, preflight, inference, IPC and subsequent images/ROIs. The finite fallback starts once. A later larger deadline cannot extend the request.
4. Image/result bytes cross bounded owned files (32 MiB each), with bounded atomic controls; the stdin pipe is not a bulk-data transport. Every handled error/cancellation/timeout rejects late success and stops the tree. Normal close reaps the owned process before deleting generated scratch. The 2.5-second cleanup grace is separate from request work and cannot renew it.
5. Public configured composition wraps an exact `LocalOCRAdapter` in `IsolatedOCRAdapter`, closing it on return. `NarrativeNormalization` uses the isolated adapter by default for preflight/sample/normalize/replay; custom legacy protocol injection remains compatible. Direct low-level native adapter calls are cooperative primitives and are outside those reviewed entrypoints.

Abrupt kernel owner death can leave bounded owned TEMP files. Job ownership still prevents a surviving native tree. Exact filesystem restoration is claimed for handled success/failure, not impossible post-mortem Python cleanup.

## Verification without repeating expensive work

Independent new execution: original cold startup probe copied byte-for-byte into this new evidence folder; 50 ms product deadline; **PASS at 52.074 ms**. A real bootstrap spawned (PID 79896), was reaped, the backend never started, adapter worker PID cleared, generated scratch removed, and configuration identity remained exact. No outer emergency timer or real OCR inference was used.

ROOT execution was read and reconciled, not independently repeated:

| Evidence | Exact accepted scope |
| --- | --- |
| Formal RED metadata test | `_fstat64` timed out at same 1 s deadline; 2 native controls PASS |
| Final focused runtime suite | 22 PASS / 25.58 s, including native metadata, GIL stall, reuse, cumulative deadline, malformed/crash responses, descendants, parent death and AUTO daemon compatibility |
| Actual import-only GREEN | 2.088 s whole probe, 1.259 s RapidOCR import, same 15 s diagnostic cap |
| Final configured PPTX + replay | 88.83 s overall; composition phase 44.095 s, fresh replay phase 43.805 s; both completed within unchanged boundaries |
| Old 184 combined suite | Pre-EOF-correction baseline only; **not** a new post-fix whole-suite PASS |
| Old 6 independent source/geometry probes | Their three product SHA remain unchanged at this stage; no repetition |

Real E2E phase 1 had an absolute native 85-second budget, normalizer 88-second checks and a 90-second harness emergency cutoff. Fresh replay used the adapter's 90-second fallback and its own 90-second harness cutoff. The outer 195-second runner was an emergency guard. This is two bounded phases, not a claim that the entire run had one 90-second combined cap.

Final real evidence keeps all 22 original lines exact in text, bbox and confidence, adds exactly two visible business definitions at 0.98912/0.99044, and replays both plus one original locator exactly using a fresh adapter. Source/media/config identities remain unchanged. All five before/after raw/config SHA in the receipt match, the 41,195-byte owned scratch is restored absent, and network/provider/LLM fees are zero. Low-confidence partials remain diagnostics; recall stays unverified. The earlier 85.047-second FAIL and old independent FAIL report remain intact.

## Open common resource issue: pixels checked after ROI render

`ocr_region_recovery.py:605-625` builds crop/stack/upscale PNGs **before** `reserve_pixels`; the reservation is correctly before native OCR, but not before allocation. `max_side_len=3000` is passed into RapidOCR after dispatch, so it does not cap the parent-side PIL render. `geometry-bounds.json` contains only static integer formulas: no allocation, model or inference was used.

With default `max_image_pixels=16,000,000` and `max_total_pixels=96,000,000`:

- Margin crop is clamped within the source image: at most 16M pixels, but it can still be unnecessarily rendered when the remaining total budget is too small.
- Upscale has fixed 2x edge length: up to **64M pixels**, or at least 192 MB nominal RGB payload, before cap rejection. Additional source/crop/PNG/PIL buffers can increase peak memory; this review does not assert measured RSS. A valid 6000x2666 source and whole low-confidence line-like region has aspect 2.25, selects upscale and creates **12000x5332 = 63,984,000 pixels** before the existing 16M cap rejects it. This is not a company-specific case.
- Split-stack chunk width is at most `floor(6.5*crop_height)`, but there is no independent max output dimension. Whitespace can advance a cut by only `floor(0.3*max_chunk_width)`; 8-row gaps add height. Across valid default-cap inputs with crop height at least 12, the conservative static upper bound is **90,431,016 pixels** for width 1,333,333 / height 12; 78-pixel stack width and at most 57,969 chunks produce a 1,159,372-pixel stack height. This is a conservative bound, not observed allocation or proof that a real detector emits that region. It illustrates the lack of a pre-render cap; less extreme upscale already proves the practical gap.

Native over-budget inference is prevented, so the prior inference-budget issue is closed. **Render-allocation budgeting is not complete.** ROOT's assigned repair should calculate/plan exact transformed dimensions, reserve shared pixels, then materialize the same frozen geometry; over-budget cases must make zero transform render/native calls. Avoid merely checking after PNG creation or increasing caps. Normal-size accepted transform/locator bytes and diagnostic behavior should remain stable.

## Remaining limits

No claim for whole-process peak RSS, POSIX execution, guaranteed OCR recall, W04 selection/summary performance, company financial facts, or RF economic reasoning. No new permission/identity database, approval JSON, canary, provider, telemetry daemon, configuration/model change, or per-material review was introduced. Final overall resource merge acceptance should add the concentrated pure-geometry preallocation results to this native-runtime PASS.
