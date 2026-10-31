# W23-XIAOMI-OCR Handoff (harness-handoff/1)

- workdir `C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr` · branch `codex/w23-xiaomi-ocr-20261030` · base `de7ffe48`
- final tested & reviewed commit: **c62ba969** (implementation 0d24c943 → 8469df7c → fde39dfe → c62ba969)
- overall status: **PARTIAL** — R0/N0 complete and independently verified; X1 unsupported by measured resource bound; X2 not_run.

## What ROOT receives

- `tools/ocr_comparison/` — the replayable comparator (R0 production path, X1 HF checkpoint arm with upstream prompt/decoding/resize, X2 declared slot, N0 control), frozen metrics contracts, run manifest builder. 41 tests (32 unit + 9 integration), no network/model in CI domain (`test_receipt.txt`).
- `docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json` — 7 documents / 14 pages (8 eval + 5 holdout + 1 declared synthetic degradation), frozen before any engine output; exact catalog identity + page PNG SHAs (200 DPI pypdfium2 4.30.0).
- `docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json` — human-verified gold (frozen pre-engine-output; post-review char-level corrections documented in `post_review_corrections`).
- `delivery/w23-xiaomi-ocr/comparison.{md,json}` (`cwp-ocr-comparison/1`), `raw_{r0,n0,x1,x2}.json`, `fact_scores.json`, `pilot_{r0,x1}.json`, `review_independent.md`, `handoff.json`.

## Result in one paragraph

R0 (production RapidOCR, full isolation + region-recovery path) passed all 14 pages: eval macro strict CER 0.1599 / micro 0.1737 / narrow 0.1250, English WER 0.300 (single EN eval page), number recall 0.9219 / precision 0.9833; holdout macro 0.1694 (WER 0.1917, single EN holdout page); peak engine memory 0.671 GB WS / 0.988 GB commit (fresh-interpreter instrumented receipt); 0 fabrication, 0 repetition loops; recurring defect classes are unreadable checkbox states, isolated line drops (garbage fragments on EN pages), o-for-0 substitutions, and table cell-order scrambles (values intact). Sample coverage gaps declared per card: no two-column (双栏) page and no seal/stamp page in the frozen catalog slice. X1 (Xiaomi-OCR-0 @ bbd8cf8d) never executed: the card's memory bound min(8GiB, avail/2) measured 0.84–1.155 GiB while the minimum feasible load peak is 3,493,875,712 B (2× weight bytes, bf16) — the preflight refuses with that arithmetic per page instead of thrashing the host. X2 (PP-DocLayoutV3 two-stage) is not_run for the same class of reason. No Xiaomi accuracy claim exists anywhere.

## Recommendation (card scope)

现有不动 for the production stack; treat R0's defect classes as reading-layer concerns. Any Xiaomi integration decision requires replaying X1 on a host with ≥3.3 GiB free RAM (bf16) or a GPU — the tool, manifest, gold and cache keys are ready for that replay and will not silently change identity axes. The reading-layer adapter sketch in comparison.md §4 is design-only, deliberately not implemented.

## Review trail

Independent agent review pass 1: NEEDS_FIXES (5 OPEN: runner field allowlist, resource-narrative provenance, fact-score accounting, §5 provenance wording, gold blemishes). Fixes in c62ba969 (runner passthrough + pipeline test, gold corrections + post_review_corrections, fact accounting verified programmatically, report corrections, final four-arm re-run). Closing re-review: **READY_FOR_ROOT, 0 OPEN** — reviewer independently re-hashed all frozen inputs, recomputed all aggregates to <1e-6, and re-ran the tests.

## Cleanup & assets

Temp render dirs, candidate texts, probe thumbnails, run temp dirs and post-review page PNGs deleted; ROOT untouched (additions-only diff confined to the card's allowed areas). Retained explicit asset: one HF model snapshot `xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…` at `.w23_cache/hub` (1,773,858,913 B, not committed) for the future X1 replay.
