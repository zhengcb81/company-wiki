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
