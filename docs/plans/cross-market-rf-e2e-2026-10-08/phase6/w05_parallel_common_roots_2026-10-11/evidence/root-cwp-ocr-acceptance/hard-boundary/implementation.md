# ROOT OCR hard boundary implementation handoff

- This document records the initial hard-boundary checkpoint. The later configured-engine acceptance found and corrected a Windows native import deadlock; current code hashes and 22-test verification are in [runtime-import-deadlock.md](performance/runtime-import-deadlock.md).
- Implemented only in `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`. No commit; original worker leaf untouched.
- Product/test **frozen**. No real OCR/cloud/model download or project fee usage.

## Files and interfaces

1. New `src/company_wiki/document_normalization/isolated_ocr.py`:
   `IsolatedOCRAdapter(config, *, deadline=None, default_timeout_seconds=90.0, scratch_dir=None, _backend_factory=None)`.
   Preserves `config.identity_manifest` and fingerprint; `validate_environment(*, deadline=None)`, `transcribe(data, *, limits)`, `close`, context manager, diagnostic `worker_pid`.
   `_backend_factory` is an explicit importable test seam; production defaults to configured LocalOCRAdapter. It does not change provider/config choices.
2. `src/company_wiki/source_catalog/narrative_normalization.py`: default lazy factory is IsolatedOCRAdapter with the existing absolute deadline. Explicit injected fake adapters keep their old constructor and `validate_environment()` signature. Added close/context ownership; native child owns its engine until close. No production config changes.
3. New `tests/document_normalization/test_isolated_ocr.py`: 17 tests, real owned child processes with fake native work, no ONNX/model/provider dependencies.

## Runtime design

- Actual new-interpreter subprocess spawn, not multiprocessing children (AUTO daemon workers forbid multiprocessing descendants).
- One reusable native engine per lazy adapter; original + ROI calls reuse it. A single effective absolute deadline is pinned on the first native operation; later deadlines only shorten it. The 90s fallback applies only when no explicit deadline exists. Native startup, model preflight, input/result exchange and all inference are covered by this same deadline.
- Bounded owned input/result files (32 MiB), atomic small JSON control notifications (4 KiB), configuration envelope 64 KiB. No large blocking pipe payload. Native stdout/stderr do not hold IPC pipes open.
- Windows: existing bootstrap release after WindowsJob assignment, CREATE_NO_WINDOW, owned Job tree killed on timeout/close/owner death.
- POSIX: own session plus independent lightweight stdin-EOF guardian, so native code retaining the GIL cannot stop parent-death detection. This branch was inspected but not executed on this Windows host; ROOT/CI may verify platform behavior.
- The initial native-worker EOF monitor was later removed: its blocked fd0 read deadlocked Windows native `fstat` during NumPy import. OS ownership / the separate POSIX guardian remains the single liveness path. Abrupt uncatchable owner death guarantees native process termination, but scratch file removal on Windows is best-effort under an immediate kernel kill. Such killed-owner scratch is limited to its small system-temporary directory; no original/production files are changed. The parent-death test cleans only its own exact tmp directory. Normal/handled failures must restore owned scratch exactly.
- Cleanup has ONE separate 2.5s grace, not a renewed operation deadline. Tests uncovered Windows Job's asynchronous termination: bootstrap exited before native file handles were fully closed. Fixed by waiting for the actual recorded native worker PID and retrying owned scratch removal within that same grace; assertions were not relaxed.

## Evidence (all original failures preserved)

- `red.log`: formal 3 business failures on the direct-call baseline scaffold (soft checks wait until 2s native return, despite short requested deadline). No import failures counted as RED.
- `green-first.log`: first implementation 9 failed/1 passed from test factory's same-name conftest import conflict. Corrected the NEW test helper to be self-contained; no product checks weakened.
- `green-bootstrap.log`: next concrete failure identified missing image argument in proxy dispatch; corrected.
- `green-second.log`: proxy initial 10 tests + 24 existing narrative OCR composition contracts = **34 PASS**, 22.31s.
- `green-final.log`: expanded 14-test boundary pack + existing 24 = **37 PASS / 1 FAIL**, 71.22s. Failure was the real Windows Job/file-handle cleanup race above.
- `green-cleanup.log`: fixed race, all 6 directly affected hard-timeout/port tests **PASS**, 9.02s.
- `green-port-compat.log`: additional daemon AUTO compatibility, default NNorm deadline and legacy injected fake protocol **3 PASS**, 4.90s.
- Ruff check of all three files **PASS** after formatting only the new files.
- `mypy.log`: new proxy **PASS, no issues found**, follow-imports=silent/ignore-missing-imports; earlier new-file typing issues corrected, no broad baseline suppression introduced.

ROOT owns the final combined frozen suite and the ONE real PPTX configured engine E2E. Do not call the boundary complete solely from fake/native tests or the E2E emergency timer.

## Initial checkpoint SHA-256 (superseded by the linked correction)

- isolated_ocr.py `d59a52a35dc6fc9c196d9e293b962ea844f171caf132e5823ea97f66b4303c98`
- narrative_normalization.py `b29a4fe2069713800d171c30ecd09d7bcf3a35984ef2f872ed85d8d4986ccbfd`
- test_isolated_ocr.py `da9fff262d9617eecf0ad99cece8a09eff484d35381cec9c95eba17209e33edd`
