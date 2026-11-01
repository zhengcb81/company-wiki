# W23-OCR-R1 Handoff (harness-handoff/1)

- workdir `C:\Users\郑曾波\Projects\company-wiki-w23-xiaomi-ocr-r1` · branch `codex/w23-ocr-r1-20261031` · base `946537d0` · required platform fix `20dd0143` (cherry-picked)
- final tested commit: `6705c3ea3a43323e0642a2ac3430b3fe98f1f8bd` · reviewed commit: recorded after the final review
- **Status: PARTIAL** — R0/N0 completed the 7-page frozen sample in one campaign; X1F resource-blocked with 2 measured attempts; X2 NOT_RUN.

## What ROOT receives

- `tools/ocr_comparison/campaign.py` — one cumulative 1800 s campaign ledger (append-only, atomic; corrupt state refuses; cache resume with 0 re-inference/0 re-charge; conservative charging for unknown in-flight time).
- `docs/plans/w23-ocr-r1-2026-10-31/` — frozen sample manifest (7 pages, 5 new documents, exact catalog identity), independent gold (rev 3, image-transcribed), controls manifest, fact matching, single-source delivery builder.
- `delivery/w23-ocr-r1/` — comparison.json/md, per-arm captures, ledger, receipts (cap/host/identity/stages), fact_match.json.

## Result in one paragraph

R0 (real engine + production recovery ladder) completed all 7 pages: macro strict CER 0.1022, narrow 0.0801, number-token recall 0.9117, digit-present 0.9905; facts 149/171 surface / 161 numeric-anchor, conditions 89/98. N0 control completed and slightly exceeds R0 on surface fact recall, as expected for a text-layer reader. X1F: attempt 2 under the fixed toolchain loaded the mapped model (~97 s), failed at generate with an allocator error, then crashed natively at 106.5 s; the recorded job peak (1.753 GiB) exceeded the recorded cap (1.602 GiB) — reported as measured and flagged. Blank negative control: 0 fabricated characters. Formula control: 1/4 symbols faithful.

## Campaign

- Ledger: spent **1406.5 s** of 1800 s; remaining 393.5 s; per-request cap 180 s; single concurrency.
- Disclosed accounting defects: 7 zero-second R0 rows from the first invocation (under-count; pages re-measured at 144.15 s) and 1080 s charged to six pages X1F attempt 2 never started (over-count; append-only ledger keeps it, code now charges 0).
- The prior exploratory experiment's 2471.83 s is listed separately and is not netted against this campaign.

## Review

An independent final review was run; its findings and the fixes are recorded in `review_independent.md` (Open items for ROOT: Job Object peak > cap in attempt 2; X1F host memory requirement).

## Cleanup & assets

- Rendered page PNGs deleted; SHAs and render scripts retained. Model assets reused read-only from the original worktree, not copied, not committed.
- Production isolation: additions-only in the allowed paths; the platform fix is ROOT's commit.
