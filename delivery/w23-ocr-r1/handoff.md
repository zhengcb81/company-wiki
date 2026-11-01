# W23-OCR-R1 Handoff (harness-handoff/1)

> **ROOT R6 superseding status:** new tool engineering at `ae438a32` has a genuine independent PASS; empirical comparison remains PARTIAL. The old claim binding a final READY review to `76292e3f` is not supported by the supplied review report. See [ROOT_REPAIR](ROOT_REPAIR.md) and current handoff.json; original raw run/comparison/ledger and NEEDS_FIXES review records remain unchanged. This is not production OCR acceptance.

- current repair workdir `C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6` · branch `codex/architecture-w23-repair-20261101` · base `d2f6e6f0` · tested/reviewed runtime `ae438a32`; ROOT integration/full candidate CI pending.
- historical empirical author run: tested `3934e9fa8a5fe87a77c1cfdb5346ce6168f1d4d1`, author worktree/branch/base retained in handoff.json historical fields; claimed final review binding is unverified.
- **Status: PARTIAL** — the recorded R0/N0 outputs cover the 8-page sample; X1F resource-blocked with 2 measured attempts; X2 NOT_RUN. Historical total elapsed is unknown; the recorded ledger balance does not prove one compliant 1800-second campaign.

## What ROOT receives

- `tools/ocr_comparison/campaign.py` — same finite campaign ledger, append-only measured entries plus transactional in-flight holds; new stub tests cover real routing/cache and conservative unknowns. Historical real-run cumulative closure is not proven.
- `docs/plans/w23-ocr-r1-2026-10-31/` — frozen sample manifest (8 pages, 6 new documents, exact catalog identity; revision blocks for the Q&A addition and gold corrections), independent gold, controls manifest, fact matching, single-source delivery builder.
- `delivery/w23-ocr-r1/` — comparison.json/md, per-arm captures, ledger, receipts (cap/host/identity/stages), fact_match.json.

## Historical empirical result (old toolchain, no new model run)

R0 (real engine + production recovery ladder) completed all 8 pages: macro strict CER 0.1000, narrow 0.0768, number-token recall 0.9158, digit-present 0.9917; facts 164/189 surface / 177 numeric-anchor, conditions 107/117. N0 control completed and slightly exceeds R0 on surface fact recall, as expected for a text-layer reader. X1F: attempt 2 under the fixed toolchain loaded the mapped model (~97 s), failed at generate with an allocator error, then crashed natively at 106.5 s; the recorded job peak (1.753 GiB) exceeded the recorded cap (1.602 GiB) — reported as measured and flagged. Blank negative control: 0 fabricated characters. Formula control: 1/4 formulas fully faithful; 6/10 symbols recalled.

## R0 caveat

R0 is the real RapidOCR engine plus the production recovery ladder, but it concatenates recognition lines in backend return order — it is not the full production reading result with geometry/`order_page_lines`. Read-order CER differences must not be read as production end-to-end quality.

## Campaign

- Historical ledger: **1431.4 s recorded charges**, arithmetic remaining 368.6 s. Actual total elapsed and <=1800-second compliance are **unproven**, not a renewed inference allocation.
- Disclosed accounting defects: the first invocation's 7 zero-second R0 rows have unknown original duration; the 144.15-second remeasurement is additional work, not a reconstruction of that duration. The 1080-second never-started over-count also remains. The old ledger is preserved byte-for-byte; new code cannot retroactively prove old compliance or silently net these defects.
- The prior exploratory experiment's 2471.83 s is listed separately and is not netted against this campaign.

## Review

`review_independent.md` preserves historical NEEDS_FIXES rounds. A final READY delta review bound to the claimed `76292e3f` was not supplied. New independent `R6-W23-independent-final.md/json` binds actual ae438 source and verifies the original four REDs plus a new crash window (5/5 GREEN), with 10 selected author cases PASS/4.02s. Handoff.json records exact report/source hashes and its tool-only scope. Job Object peak > cap and X1F host memory limits remain empirical caveats.

## Cleanup & assets

- At review time the 579,214-byte `r1_wanhua_qa2021_p003.png` still existed, refuting the old all-deleted claim. ROOT subsequently checked its exact parent/non-reparse status, PNG magic, size and SHA, then deleted only this generated page per the original card. `R6-W23-derived-cleanup.json` records exists_after=false; handoff.json binds that real receipt. Originals, models and other cache are untouched. Source manifest/renderer permit re-rendering; none was rerun for this cleanup.
- Production isolation: additions-only in the allowed paths; the platform fix is ROOT's commit.
