# W05 ROI preallocation: independent final acceptance

Date: 2026-10-11. **PASS_WITH_SCOPE.** Product non-author review of `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`. Accept the final frozen Windows OCR process boundary and production ROI allocation contract. No P1 defect found within this scope. ROOT owns merge/commit and shared PWF.

Final ROI source SHA: `d3890356211e7fe21fce22fcfb11ac71769941712dd77937d4d28e1d291f512c`; matching test SHA: `3acea08f310eb21549b5353e4f092ec4956bcba6be953f5eef6e52704211aa50`. Native process boundary remains `edade53c3c0fed2cb47ab115dbc969e1bd18be183280ee67a086fc876623d396`; composer and NarrativeNormalization hashes remain unchanged. The prior `independent-post-deadlock` PASS-with-pending-resource report is preserved; this report closes its **OCR-POST-07** for the final frozen ROI SHA.

## Independent concentrated execution

**34 vectors PASS / 0.383s**, standalone Python with bounded synthetic images/fake OCR, no model calls, raw documents, providers or network. All product/test SHA match before and after. Images stayed in memory; no test scratch or image files were created, so there is no data-directory residue to remove.

| Group | Vectors | What was proved |
| --- | ---: | --- |
| Margin/split/upscale × image/total cap | 6 | A rejected target renderer is never called; no extra fake inference; previous successful attempt charges persist; pixel/attempt counters remain atomic |
| Render and inference failures | 2 | Exact reserved pixels/attempt remain charged once; error diagnostic and no recovered text retained |
| Mode × transform reference | 15 | New samples match the old PIL crop/grayscale raster reference exactly in PNG bytes, transform and source coordinates; two preexisting CMYK PNG errors unchanged |
| Luminance mode reference | 8 | RGB/L/RGBA/P/CMYK/LA/1/RGBX source-window sampling matches independent PIL luminance reference |
| Source scan + expiry | 2 | No analysis crop/grayscale raster; only ROI alternate rows read; 64-column checkpoints and early stop exact |
| Former oversized case | 1 | Size-only 6000x2666 source plans 12000x5332; default cap rejects 63,984,000 pixels without allocating an actual image |

Budget probes exercise the recovery seam. A margin output cannot exceed the original image by geometry; its single-image-cap vector uses stricter limits after source preapproval. Under unchanged public limits the source image would already be rejected first. Split/upscale probes can exceed source area. `regions_started` marks the selected region even if the first reservation fails; the atomic guarantee concerns consumed pixels and attempts, not erasing that diagnostic marker.

## Static source-to-render boundary

The configured composer first opens image metadata, validates `max_image_pixels`, reserves the full-image request charge, and dispatches native OCR. The returned dimensions must match. Only then does `recover_regions` load/convert that already-validated original for ROI planning. That full source decode still costs memory within the existing source cap; it is not a newly unbounded transformed raster.

For every production ROI attempt the order is now:

1. Plan integer source window and exact target canvas.
2. Reserve **all target pixels**, including split padding and unused canvas columns, against image and shared total limits.
3. Increment attempt counters, render from that exact plan, check the same deadline and invoke OCR.

The renderer consumes the checked plan instead of scanning again. Failure/rejection does not refund already consumed work. Over-budget reservation performs no render or inference. There is no changed cap, extra approval or new identity layer.

Split preflight directly scans the selected loaded source ROI, not a transformed image: `W*ceil(H/2)` pixel visits and an **O(W)** column-count list, plus geometry/chunk tables. Its deadline is checked before column 0, every 64 columns and after the scan. Our 156x17 window sampled 1,404 pixels, with checkpoints exactly at 0/576/1,152/1,404; forced expiry at checkpoint 2 stopped after 576 samples. A source-only sentinel forbids crop/convert. Production recovery's input is RGB, so the alternate-mode one-pixel converter is not used there; P-mode utility cache is at most 256 entries.

This closes the previous default-limit gap: 16M source →64M upscale or padded split outputs were materialized before checking. Now only planned dimensions exist before reservation. Accepted source/transform/PNG buffers still have memory overhead, and no whole-process peak-RSS guarantee is claimed.

## ROOT's independent real replay and retained RED

Read, reconciled and not repeated: `preallocation-real-e2e/root-real-e2e-{result,receipt}.json` and `product-freeze.json` show **PASS /83.006s overall**, both original-bounded phases completed. Product SHA before/after are identical. Five raw/config SHA before/after match; owned 41,194-byte scratch returns from absent to absent; zero network/provider/LLM/fees.

All **22 original lines** remain exact in text, bbox and confidence. Exactly two visible definitions remain recovered at **0.98912/0.99044**, and text/boxes/confidences/locators agree with the preceding native-correction real PASS. A fresh adapter replays the two definitions plus one original locator exactly through the SourceVersionReader workflow.

Phase 1 retains the 85-second absolute native budget and 90-second harness emergency cutoff. Fresh replay retains the 90-second fallback and its own 90-second emergency cutoff; the runner retains 195 seconds. This is two requests/phases; the 83.006-second total is an observed result, not a combined 90-second product policy.

ROOT's two-file focused run remains **54 PASS /3.78s**, Ruff PASS. Author before/after receipts match for all 15 cases (13 PNG+transform and two retained errors). Seven original preallocation business FAILs remain in `preallocation/red.log`; the intermediate palette FAIL also remains. The previous 12-file independent manifest, native correction report/manifest and three original real FAIL files were reconciled byte-for-byte, with original real FAIL matching `c145da9b` committed blobs. No old record was overwritten. **184 combined tests remain the pre-native-correction baseline**, and 22 native tests predate this geometry-only change; neither suite was rerun or relabeled.

## Scope limits

Windows runtime is accepted; POSIX guardian only received static review. No maximum-size throughput/peak-RSS benchmark, guaranteed OCR recall, W04 summary quality, source financial fact accuracy, or RF economic judgment is asserted. The low-level `build_*` utility renderers have no resource argument and rely on the production planner/reservation caller; this review does not claim arbitrary standalone utility calls are guarded. Kernel-forced owner death may leave small owned TEMP files while OS ownership kills the native tree.

Writes were restricted to this new `independent-preallocation/` evidence directory. Product, production config/models/raw, shared PWF, installed skills and Git state were unchanged. Final machine-readable evidence is `probes.json`, `report.json`, and `manifest.json`.
