# ROOT W05 ROI preallocation closure

Date: 2026-10-11. Worktree: `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`.

Only `ocr_region_recovery.py` and its matching `test_ocr_region_recovery.py` were modified and staged. No commit. No change to composer, `isolated_ocr`, NNorm, LocalOCRConfig, production config, original worker tree, shared PWF or source originals. No real OCR, cloud call, provider fee or raw-document access. ROOT owns final integration and exact original replay.

## Root cause and repair

The earlier shared budget protected inference, but transformation builders could first allocate an oversized raster. In particular, a 4000×4000 source and fixed 2× upscale could allocate an 8000×8000 (64M pixels) output before the default 16M single-image cap rejected it.

Recovery now executes:

1. Plan integer crop/canvas geometry without allocating a transformed raster.
2. Reserve its **exact entire output canvas**, including all split padding, against the same request-wide image/total limits.
3. Increment attempt counters; render only after successful reservation.
4. Check deadline, then call OCR. Failed renders/inference and rejected recognition remain charged once. A reservation rejected before allocation is atomic and leaves counters unchanged.

Margin and upscale plans depend only on the existing source dimensions and the same rounded crop window. Split cut points still depend on whitespace, so preflight scans only the selected source ROI on every other row. It reads loaded source pixels directly and keeps one column-count array; no source crop, ROI grayscale image, resized image or stack canvas is allocated during that scan. RGB luminance uses PIL's fixed integer coefficients; other modes use their luminance value or a reusable one-pixel converter, with palette cache bounded by 256 entries. The renderer consumes the exact preflight plan instead of scanning twice.

The previous canvas/transform semantics remain: same 0.35 vertical margin, 6.5 target aspect, 8 gap rows, cut selection, 2× upscale, PNGs and original-coordinate chunk mapping. Locator, parser, model settings and `bounded-source-roi/2` identity were preserved as ROOT instructed; this revision has not yet been published.

## Tests and evidence

- [red.log](red.log): **7 actual business FAIL** before implementation. Six cases cover all three transforms under single-image and remaining-total limits and show their renderer was called before rejection; the seventh demonstrates render failure was unreserved. No import-error REDs.
- [green-attempt.log](green-attempt.log): **53 PASS / 1 FAIL** after the main refactor. The new multicolor P-mode reference caught a real palette-core initialization error; product code was fixed using `putpalette`, leaving the reference test unchanged.
- [green.log](green.log): **54 PASS / 3.78s**, both recovery/composition test files, no cache provider. Includes prior complete-region, budget, replay and geometry assertions plus 16 preallocation/reference cases.
- [ruff.log](ruff.log): both modified files PASS.
- [before.json](before.json), [after.json](after.json): all **15 mode/transform receipts identical**, including **13 exact PNG SHA + transform** cases for RGB/L/RGBA/P and CMYK split. The two preexisting unsupported CMYK margin/upscale PNG errors are identical and explicitly retained.
- A size-only object proves the 16M→64M case without allocating a large source or output image.
- Split tests verify that exact canvas width/height include unused columns and inter-chunk padding; preflight and rendered dimensions match.
- [freeze.json](freeze.json): final two source SHAs, before/after equality, resource scope and small scan measurement.

## CPU and memory bounds

Only a triggered split branch scans pixels, once. For integer ROI dimensions W×H, the scan visits `W * ceil(H/2)` pixels, keeps O(W) small counts and checks the current deadline every 64 columns and on completion. It never scans outside the selected ROI or duplicates a full source/ROI grayscale raster. Margin/upscale allocate no analysis raster and perform no such scan.

The bounded synthetic diagnostic uses a **3180×170** ROI (**270,300 sampled pixels**). Two source scans took **0.175s / 0.157s**, compared with the old crop/grayscale reference's **0.084s / 0.054s**. The direct RGB calculation therefore costs approximately **0.10s extra** at this ROI size, while avoiding the pre-reservation raster copy. This measurement is not a guarantee for a maximum-size source; larger scans remain proportional to actual ROI pixels and interruptible by the request deadline. No large benchmark image was created. ROOT's next real PPTX run remains the practical performance/quality check.

## Final freeze

- `ocr_region_recovery.py`: `d3890356211e7fe21fce22fcfb11ac71769941712dd77937d4d28e1d291f512c`
- `test_ocr_region_recovery.py`: `3acea08f310eb21549b5353e4f092ec4956bcba6be953f5eef6e52704211aa50`

All modified files are released to ROOT. Helper mutation scripts in this folder already ran and are one-shot; do not rerun them. Original failures are retained. No optional tests or scans are pending in this lane.
