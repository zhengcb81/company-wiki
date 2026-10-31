# W23-XIAOMI-OCR Handoff (harness-handoff/1)

- workdir `C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr` · branch `codex/w23-xiaomi-ocr-20261030` · base `de7ffe48`
- final tested & reviewed commit: **c62ba969** (implementation 0d24c943 → 8469df7c → fde39dfe → c62ba969)
- overall status: **PARTIAL** — R0/N0 complete and independently verified; Xiaomi executed via the declared X1F variant (13/14 pages, all EOS, in-bounds); upstream-bf16 arm timeout with partial text; X2 not_run; one holdout page unattempted (budget).

## What ROOT receives

- `tools/ocr_comparison/` — the replayable comparator (R0 production path, X1 HF checkpoint arm with upstream prompt/decoding/resize, X2 declared slot, N0 control), frozen metrics contracts, run manifest builder. 41 tests (32 unit + 9 integration), no network/model in CI domain (`test_receipt.txt`).
- `docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json` — 7 documents / 14 pages (8 eval + 5 holdout + 1 declared synthetic degradation), frozen before any engine output; exact catalog identity + page PNG SHAs (200 DPI pypdfium2 4.30.0).
- `docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json` — human-verified gold (frozen pre-engine-output; post-review char-level corrections documented in `post_review_corrections`).
- `delivery/w23-xiaomi-ocr/comparison.{md,json}` (`cwp-ocr-comparison/1`), `raw_{r0,n0,x1,x2}.json`, `fact_scores.json`, `pilot_{r0,x1}.json`, `review_independent.md`, `handoff.json`.

## Result in one paragraph

The Xiaomi model WAS executed for real, under the card's own memory rule. Three measured root causes had made the upstream load path impossible on this host (copy-loading needs ~3.1 GiB private commit vs card caps 1.1-2.3 GiB; `torch.from_file` silently charges the whole copy-on-write view against commit; prefill built one ~2.85 GiB logits tensor; `generate()` ran cache-less for this hybrid linear-attention architecture; and large bf16 GEMMs run at 0.5 GFLOPS on this AMX-less CPU vs 330 GFLOPS fp32). The executed arm is therefore the declared **X1F variant**: the frozen checkpoint widened losslessly bf16→fp32 (same numbers, no quantization), mapped read-only into the process (commit-free, tensor-byte equality verified), decoded greedily with an explicit cache, upstream prompt/template/postprocess. Card-compliant pilot: ok in 69 s with EOS. Batch: **13/14 pages ok, every one finished with EOS**, 1801.6 s of request time against the 1800 s card budget (+0.09%: the last in-flight page was allowed to finish, disclosed), job peaks 2.32-2.81 GiB under caps 3.75-3.90 GiB (Windows Job Object enforcement); the 14th page not_run (budget); the upstream-exact bf16 arm got one attempt and timed out at the 600 s upstream request deadline with 242 correct partial tokens.

Headline comparison (eval split): X1F strict CER **0.086** vs R0 0.160; narrow 0.038 vs 0.125; English WER 0.10 vs 0.30. X1F reads every checkbox state ("☑适用 □不适用"), the negation line, the English opening line and the superscript footnote (392.0) that R0 structurally misses; its misses are table-cell concatenation (digits present, exact tokens scrambled; digit-present recall 0.89 vs token 0.73) and the stylized "2024 年度報告" year art. Human facts: eval 76/76 + conditions 10/10; holdout 31/32 + 8/8; zero fabrication, zero loops. Cost: 57-235 s/page vs R0's ~16 s. X2 (two-stage) remains not_run.

## Review trail

Independent agent review pass 1: NEEDS_FIXES (5 OPEN: runner field allowlist, resource-narrative provenance, fact-score accounting, §5 provenance wording, gold blemishes). Fixes in c62ba969 (runner passthrough + pipeline test, gold corrections + post_review_corrections, fact accounting verified programmatically, report corrections, final four-arm re-run). Closing re-review: **READY_FOR_ROOT, 0 OPEN** — reviewer independently re-hashed all frozen inputs, recomputed all aggregates to <1e-6, and re-ran the tests.

## Cleanup & assets

Temp render dirs, candidate texts, probe thumbnails, run temp dirs and post-review page PNGs deleted; ROOT untouched (additions-only diff confined to the card's allowed areas). Retained explicit asset: one HF model snapshot `xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…` at `.w23_cache/hub` (1,773,858,913 B, not committed) for the future X1 replay.
