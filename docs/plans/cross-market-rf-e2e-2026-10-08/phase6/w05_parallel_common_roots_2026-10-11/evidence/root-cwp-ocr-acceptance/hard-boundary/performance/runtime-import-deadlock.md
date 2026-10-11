# W05 configured OCR failure: common runtime cause and correction

## Conclusion and current acceptance boundary

The failure was a Windows native runtime deadlock introduced by the new isolation boundary. It was not slow OCR inference, lost model configuration, ROI retries, or proven machine load. The native worker's duplicate parent-liveness thread blocked in `os.read(0, 1)`, holding the Windows UCRT descriptor 0 lock. Native `_fstat64(0, ...)` then could not complete. NumPy's C extension was stuck while RapidOCR imported it.

Corrected only `src/company_wiki/document_normalization/isolated_ocr.py` in the ROOT integration worktree: removed that worker stdin-reader thread and its helper. Windows Job ownership and the separate POSIX guardian remain the single parent-liveness path. Moving the thread until after imports would leave the same defect in future native calls, so it was removed entirely. No config, model, source byte, request limit, OCR identity or public assertion changed. No new telemetry, policy gate, daemon, or status database was added to product.

**Focused status: 22 PASS, 25.58 seconds; Ruff PASS. Real configured RapidOCR import now completes in 1.259 seconds (whole isolated import probe 2.088 seconds), within the identical 15-second diagnosis budget.** ROOT subsequently reported its configured PPTX composition and locator replay E2E PASS; details are below. Its 184-test combined baseline passed before this thread correction and was not rerun afterward: do not present it as a post-correction combined run.

## Read-only diagnosis before changing product

1. ROOT's original real E2E failure remains separately immutable, pushed in `c145da9b`: first full image `response-0`, deadline 85.047 seconds, no image result. It failed before any ROI.
2. `probe_one_image.py` reads the exact original via `SourceVersionReader.open_version(..., purpose="source_export")`, verifies PPTX/media SHA, uses the actual `config/local_ocr.json`, and passes a single absolute 85-second product deadline through startup, native preflight and inference. It forbids network and restores its owned scratch. No ROI or translation was added.
3. The transparent diagnostic subclass logs events outside child scratch; it does not alter engine parameters. Its ONNX session hooks were never reached before failure. Trace `probe-one-image-trace.jsonl` shows:

   | Stage | Measured elapsed |
   |---|---:|
   | Parent start to ready | 3.668 s |
   | Native model verification before RapidOCR import | 0.069 s |
   | RapidOCR import | never returned before the same 85 s deadline |
   | ONNX session construction / det / cls / rec | not reached |

   During the block, the owned child had approximately 2 CPU seconds, 5 threads and 54 MB working set. This does not support a compute or load explanation. `probe-one-image.json` records FAIL at 85.008 seconds, zero network, unchanged config/source identities and restored scratch.
4. One import-only diagnosis used the same product boundary, **15-second total deadline**, no image inference. `faulthandler` captured an independent native stack after 5 seconds (`probe-import-stack.txt`): the worker liveness thread was in `isolated_ocr.py`'s `os.read(0, 1)`; the main thread was loading NumPy `_core.multiarray`'s C extension through `cv2` and `rapidocr`. It timed out at 15.002 seconds with scratch restored.

## Formal RED and causal controls

The correction was not based solely on co-occurring stack frames:

- `red-stdin.log`: Python `os.isatty(0)` completed in both preflight and inference (2 PASS). This rejected an overbroad claim that every stdin inspection blocks.
- `red-crt-stdin.log`: real UCRT `_isatty` and `_get_osfhandle` completed; native `_fstat64(0, ...)` deadlocked and the **existing product deadline** killed/reaped the worker. **1 true business RED / 2 controls PASS**. The failure was `NormalizationLimitError` waiting for `response-0`, not test import failure.
- Cold Python/bootstrap handshake is warmed separately for these fast metadata calls. Native calls retain a 1-second deadline. Neither deadline nor expected result was changed for GREEN.
- The native metadata regressions use dummy model files, importable fake backends and no network. They do not require RapidOCR, ONNX weights or a specific company.

## Correction and verification

- `isolated_ocr.py:134–146`: no native worker thread reads fd0. Windows Job already kills the entire tree on timeout, close or owner death, independently of the native GIL. The POSIX bootstrap watches EOF in its own process, whose CRT state is independent of the native worker. Normal scratch cleanup remains the parent's responsibility; abrupt kernel owner kill can leave only small bounded owned temporary scratch, as already documented.
- `green-crt-stdin-and-owned-tree.log`: **22 PASS / 25.58 s**. Includes all previous uncooperative preflight/inference, GIL-holding native work, accumulated deadline, engine reuse, malformed/error/crash results, AUTO daemon compatibility, descendant termination, owner death and exact handled scratch cleanup tests. Original assertions remain.
- `probe_import_stack_after_fix.py` executes the same import-only probe, with fresh immutable output names. `probe-import-stack-after-fix.json` is PASS, 2.088 seconds; trace records the actual RapidOCR origin and 1.259-second import. No stack timer fired. Zero native image inference or network was invoked in this post-fix probe.
- Ruff check of both modified hard-boundary files: PASS. Product files/tests were then frozen and ROOT notified before its final real E2E; this agent will not run a second real image inference or alter frozen files.

### ROOT's post-freeze configured E2E result

ROOT reported PASS after running the corrected frozen product, with no extra real OCR run by this agent:

- Overall 88.83 seconds across the two phases; each phase remained within its original 85/90-second boundary.
- OCR composition 44.068 seconds; all 22 original lines retained exact text, box and confidence.
- Both business definitions recovered at confidence 0.98912 / 0.99044; locator replay exact.
- 41,195-byte owned scratch removed and restored absent; all five raw/config SHA identities unchanged.
- The earlier 184 PASS result is the **pre-correction baseline**. The post-correction verification is **22 focused PASS plus this real configured E2E**, with ROOT's independent final boundary review still to follow. No assertion or budget increase was used.

## Exact inputs and cleanup

- Config SHA `3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105`.
- RapidOCR `3.8.1`; ONNX Runtime `1.26.0`; configured CPU intra/inter threads `2/1`.
- Model hashes unchanged: det `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9`, cls `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c`, rec `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b`.
- PPTX SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`, 4,016,522 bytes.
- Media `ppt/media/image7.png`, SHA `d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea`, 331,246 bytes.
- All three diagnosis scripts record owned scratch restored. Six exact pytest base/cache roots under `C:/Users/郑曾波/AppData/Local/Temp/` (`cwp-w05-stdin-red*`, `cwp-w05-crt-red*`, `cwp-w05-crt-green*`) were individually resolved, checked for reparse points and removed after tests. No broad temporary-file sweep. Logs remain in this evidence directory.
- Original leaf, production configuration, raw source and model files untouched; no cloud calls, weights downloads, translation, API fees or git commit by this agent.

## Frozen product SHA-256

- `src/company_wiki/document_normalization/isolated_ocr.py`: `edade53c3c0fed2cb47ab115dbc969e1bd18be183280ee67a086fc876623d396`
- `src/company_wiki/source_catalog/narrative_normalization.py`: `b29a4fe2069713800d171c30ecd09d7bcf3a35984ef2f872ed85d8d4986ccbfd` (unchanged by this correction)
- `tests/document_normalization/test_isolated_ocr.py`: `cae823beff8cf78d49fd28cd4621aa12596868b517f462d9fcd7dfeba5013c04`

## Prevention

Keep parent-liveness ownership outside native workers. Add native descriptor metadata calls to the standard fake-engine runtime suite because sleep/crash tests alone miss runtime-global locks. Keep one configured real E2E at the large acceptance node: fake engines establish hard cleanup behavior; actual engine import and inference establish deployment compatibility. This does not require per-image approval, telemetry overhead or a longer runtime budget.
