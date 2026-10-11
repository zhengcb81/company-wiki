# ROOT W05 OCR recovery systemic fix

Date: 2026-10-11. Scope: only assigned isolated ROOT tree `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`. No commit, provider call, LLM fee, raw opening/modification or worker-tree change. ROOT retains final integration and real-data acceptance.

## Cause and implementation

1. Composer previously accumulated original pixels separately from recovery pixels and checked the combined total only after ROI inference. `RecoveryBudget.reserve_pixels` now checks `max_image_pixels`, cumulative `max_total_pixels` and deadline, then atomically charges original and ROI images **before** each backend call. One accumulator spans unique media. Failed attempts remain charged; rejected reservations do not mutate counters. Composer reports this same total.
2. Adapter score filtering moved unread text into `region_diagnostics.dropped`, while the recovery evaluator inspected only surviving lines. Both margin and stack now reject recovery when unread diagnostic text intersects the original source ROI. A genuinely external margin neighbor does not veto recovery. Unmappable diagnostic text remains an explicit rejection. Attempt observations include filtered text/score, and original dropped diagnostics remain unchanged. A second counterexample showed that checking only a dropped box's center still concealed an overlapping source fragment; positive-area source-box intersection now guards that case.
3. Split-stack originally assigned a detector bbox to whichever chunk contained its center and treated the last chunk as unbounded. It now requires the **entire** bbox to fit the actual chunk's horizontal and vertical extent, including the final canvas boundary. Cross-chunk, right-padding and below-last-chunk boxes return `None`; an otherwise clean attempt with such ambiguous text cannot claim recovered content.
4. PIL 90° and 270° inverse transforms used the wrong pre-rotation dimension. They now use width for inverse 90° and height for inverse 270°. Regression goldens derive forward boxes from actual rotated PIL pixels on a rectangular canvas, rather than copying the inverse formula.
5. `LocalOCRConfig.identity_manifest` adds `region_recovery_algorithm: bounded-source-roi/2`. Old/new configuration fingerprints differ. Diagnostic schema, parser version and replay locator grammar remain compatible. No recognition threshold was lowered.

## TDD receipts

- [red.log](red.log): original new formal cases **9 FAIL / 2 PASS**, including cumulative pre-inference budgeting, filtered partial margin/stack, PIL inverse rotations and complete chunk bounds. These are business assertion failures. Two sandbox pytest-cache warnings did not cause them; subsequent runs disable the cache provider.
- [overlap-red.log](overlap-red.log): additional concrete outside-center/inside-overlap source-fragment case **1 FAIL** before its guard fix.
- [first-green-attempt.log](first-green-attempt.log): **3 FAIL / 31 PASS**. The remaining failures were old synthetic fake boxes crossing the first chunk's actual 81px width, now correctly rejected by production code.
- Exactly three impossible old fake boxes were corrected: `part` max x becomes `min(100, actual_chunk_width-1)`, and two first-chunk fake max x values 150 become 70. Their original success/failure/retry business assertions and low-score thresholds are unchanged. The former wrong 90° test golden was corrected to true pre-rotation geometry and independently strengthened by PIL forward/inverse cases.
- [green.log](green.log): final two-file suite **38 PASS / 3.38s**, using `python -B -m pytest -q -p no:cacheprovider tests/document_normalization/test_ocr_region_recovery.py tests/document_normalization/test_ocr_region_composition.py`.
- [ruff.log](ruff.log): all five assigned files PASS with `ruff check --no-cache`.

One-shot helper scripts in this evidence folder have already run; do not rerun them. Original independent FAIL receipts remain preserved. These bounded offline results do **not** replace ROOT's full normalization suite, isolated hard-deadline verification, exact raw/PPTX replay and genuine two-definition plus 22-line acceptance.

## Handoff

Product changes are finished. ROOT owns `ocr_composition.py` again for its separately identified hard-deadline adapter seam. Other assigned source/test files are also released after this report. No changes made to production configs, source catalog, selector, CI, gate tooling, raw originals or sibling repositories.
