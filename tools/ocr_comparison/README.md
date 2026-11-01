# W23 OCR Comparison Tool (experiment-only)

Compares the production CPU OCR stack (RapidOCR via `LocalOCRAdapter`, arm
**R0**) against Xiaomi-OCR-0 (0.8B VLM, arm **X1** whole-page; arm **X2**
two-stage when resource bounds allow, otherwise NOT_RUN) on a frozen set of
real company-document pages, with a born-digital text-layer control (**N0**).

This tool never wires anything into production: no production source file is
imported except the R0 adapter itself, and no FF/RF/StockWiki consumer may
call Xiaomi models through this code.

## Frozen inputs

- `docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json` — 7 documents /
  14 pages (8 eval + 5 holdout + 1 declared `synthetic_degradation`), catalog
  identity (`source_id`/SHA-256) and per-page PNG SHA-256 at 200 DPI
  (pypdfium2 4.30.0).  Frozen before any engine output existed.
- `docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json` — human-verified page
  transcriptions (`cwp-ocr-gold/1`), frozen before any engine output.  Native
  PDF text was only a candidate; corrections are recorded per page.

## Arms

| arm | backend | identity source |
|-----|---------|-----------------|
| R0  | production `IsolatedOCRAdapter` + bounded region recovery, config `config/local_ocr.json` | `LocalOCRConfig.identity_manifest` |
| X1  | HF checkpoint `xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…` on CPU fp32 transformers, upstream prompt / non-thinking / greedy / 2048-bound resize | `XiaomiX1.identity_manifest` |
| X2  | two-stage PP-DocLayoutV3 pipeline — NOT_RUN on this host (no GPU; paddlex stack outside resource bounds); never merged into X1 | declared reason |
| N0  | pypdfium2 text layer, born-digital control only | `NativeN0.identity_manifest` |

X1 has no word boxes or confidences: `bbox: null`, `confidence: null`,
`locator_quality: "none"`.  Nothing in this tool fabricates geometry or
scores; VLM markdown is never an EvidenceSpan.

## Usage

```bash
# one-page pilot (both engines, deadline-capped)
python -m tools.ocr_comparison.run_comparison --arms R0,X1 \
  --pages pilot:byd_ar_2024_p021 --out delivery/w23-xiaomi-ocr/pilot.json

# full frozen sample
python -m tools.ocr_comparison.run_comparison --arms R0,X1,N0 \
  --out delivery/w23-xiaomi-ocr/comparison.json
```

Environment: `CWP_PROJECT_ROOT` (worktree root, set by the runner),
`W23_XIAOMI_MODEL_DIR` (HF snapshot path of the frozen revision).  Page PNGs
render into an owned temp dir and are deleted on exit; raw texts and metrics
are kept under `--out`'s directory.

## Tests

- `tests/unit/test_w23_ocr_comparison_metrics.py` — metrics/cache/runner
  contracts (no model, no network).
- `tests/integration/test_w23_ocr_comparison_entry.py` — frozen-input and
  evaluation-pipeline checks (no model, no network, no literal host paths).

X2 is only scored when actually run; the report labels it NOT_RUN with the
resource reason, per the W23 task card.

## ROOT reception corrections (2026-10-31)

Historical receipts remain exploratory PARTIAL evidence: some requests used
600 seconds, the cumulative trial exceeded 30 minutes, and a declared holdout
was used as a pilot. These cannot be repaired by changing code or relabeling
old outputs. Exact stored BF16-to-F32 values do not prove compute parity.

The common CLI now delegates X1 to the isolated runner, enforces request <=180
seconds and batch <=1800 seconds, records actual artifact/runtime/code identity,
and accepts `--x1-weights-mode mapped-f32` only as an explicit variant.
Use `--cache-dir <owned-experiment-directory>` to persist checksummed per-page
results across restarts. A hit preserves measured latency and performs zero
inference; corrupt entries are misses. `--no-cache` explicitly re-executes.
The caller must account for cumulative time across separate invocations.

Checkpoint conversion is explicit and streaming:
`python -m tools.ocr_comparison.make_fp32_copy --source <bf16-file> --output <new-fp32-file>`.
It never selects or overwrites a model snapshot implicitly.

Pure metrics, manifest, cache and CLI imports are portable. Actual X1 inference
currently requires Windows committed-memory enforcement; unsupported platforms
raise `MemoryLimitUnavailable` before model inspection or child launch. The
adapter reuses the shared process-tree `WindowsJob` with the original process
handle and a cap over total owned-job commit (at least as strict as one model
process). Linux memory observations come from `/proc/meminfo`; absent values
stay null and observations do not imply supported enforcement. Fake-backend
CI tests remain portable; the actual Job allocation test is Windows-only.
# R1 campaign recovery (ROOT R6 correction)

`campaign init` creates one finite ledger (0–1800 seconds). Reuse that ledger
and the explicit `--cache-dir` for every resumed invocation; never change the
campaign ID or delete accounting to escape prior work. In a source checkout,
put `src` on `PYTHONPATH` so the shared OS mutex infrastructure is available.

Inference starts only after a short transaction reloads the current balance
and durably reserves work. It runs outside the mutex. A failed/crashed request
keeps its hold. The real X1/R0 routes read captured cache outputs first, even
with zero balance; missing pages remain explicit `not_run` rows. X1 batches
only uncached pages with one model load. Captures retain original measured
time and actual effective deadline; cache reuse is not a zero-time benchmark.

The same cache stores a small completion marker before ledger settlement, so
death after capture can recover accounting without another model call. A
missing marker/output stays unknown instead of causing silent re-inference.
Actual measured overruns are recorded rather than clipped and make the batch
`partial`. Empty/fully recorded old ledgers can migrate in place. Observed
zero-second real-inference rows with unknown cost block new allocation, while
cache remains readable; this is a resource fact, not a manual approval.

Historical R1 outputs/ledger/review remain unchanged. Their recorded charges
contain both unknown original R0 work and over-counted never-started work;
the new transaction code does not retroactively prove the old 1800-second
bound or accept the experimental model for production.
