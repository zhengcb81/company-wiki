# W23-OCR-R1 Comparison (cwp-ocr-comparison/1)

PLAN_ID=w23-ocr-r1-2026-10-31 · worktree `company-wiki-w23-xiaomi-ocr-r1` · branch `codex/w23-ocr-r1-20261031` · base `946537d0` · platform fix `20dd0143`

**Status: PARTIAL.** R0 and N0 completed the 8-page frozen sample inside one cumulative campaign. X1F ran twice under the card memory rule and both attempts failed; no Xiaomi quality claim is made. X2 is NOT_RUN. The 2026-10-30 exploratory result is not reused.

## 1. One campaign, one ledger

- Budget **1800 s**; consumed **1431.4 s**; per-request cap 180 s; single concurrency.
- R0 8 pages, real timings (12.8–28.1 s/page); the corrected R0 charge is 144.15 s.
- The ledger is append-only. Two defects are disclosed rather than hidden: seven 0.0 s rows from the first R0 invocation (under-count of that first pass, re-measured at 144.15 s), and 1080 s charged to six pages that X1F attempt 2 never started because the child crashed (over-count; the code now charges 0 for never-started pages).
- Ledger remaining after all runs: **368.6 s**.

## 2. Frozen sample (this round)

| page | market/lang | role | gold chars | facts | conditions | numbers(raw) |
|------|-------------|------|-----------|-------|------------|--------------|
| r1_amec_ar2025_p029 | CN/zh-CN/annual_report | eval | 1117 | 20 | 12 | 4 |
| r1_wuxi_ar2022_p010 | CN/zh-CN/annual_report | eval | 1822 | 25 | 23 | 29 |
| r1_ksy_fy2025_results_p003 | HK/zh/annual_results_announcement | holdout | 947 | 24 | 11 | 40 |
| r1_ksy_fy2025_income_p012 | HK/zh/annual_results_announcement | eval | 2063 | 19 | 8 | 199 |
| r1_biren_ar2025_p030 | HK/zh/annual_report | eval | 583 | 15 | 13 | 4 |
| r1_brk2007_p001 | US/en/annual_report | holdout | 4533 | 36 | 14 | 6 |
| r1_brk2007_p005 | US/en/annual_report | eval | 3817 | 32 | 17 | 19 |
| r1_wanhua_qa2021_p003 | CN/zh-CN/investor_relations_qa | eval | 718 | 18 | 19 | 15 |

Gold was transcribed by an independent reviewer from the PNGs; the PDFs do have native text layers, which the reviewer reports not using as ground truth — on clean born-digital pages near-equality with the native layer is expected and disclosed as not evidence either way (revision 3; the revision block records the HK page swap and the correction of the Wuxi line 客户对公司的服务需求, which was found by the final review and corrected before this report; metrics were recomputed from the same captured outputs, no engine re-ran). **Disclosure:** the reviewer reports having used the PNGs only; on clean born-digital pages an accurate transcription is expected to closely match the native text layer, so near-equality is not evidence either way. The retired HK page's revision-1 transcription was never committed and cannot be recovered from git; `archived_pages` records that provenance limitation and the page's exclusion from every denominator.

## 3. Results — full denominators

| arm | scored/total | macro CER strict | macro CER narrow | micro CER strict | WER (2 EN pages) | number-token recall | digit-present recall |
|-----|--------------|------------------|------------------|------------------|------------------|---------------------|----------------------|
| R0 | 8/8 | 0.1000 | 0.0768 | 0.0829 | 0.0364 | 0.9158 | 0.9917 |
| N0 | 8/8 | 0.1095 | 0.0782 | 0.0568 | 0.0024 | 0.9966 | 1.0000 |
| X1F_attempt1 | 0/8 | null | null | null | null | null | null |
| X1F_attempt2 | 0/8 | null | null | null | null | null | null |
| X2 | 0/8 | null | null | null | null | null | null |

Per stratum (R0):

| stratum | pages | scored | coverage | macro CER strict | macro CER narrow | macro WER |
|---------|-------|--------|----------|------------------|------------------|-----------|
| CN/zh-CN/annual_report | 2 | 2 | 1.0 | 0.0299 | 0.0019 | — |
| HK/zh/annual_results_announcement | 2 | 2 | 1.0 | 0.2417 | 0.2002 | — |
| HK/zh/annual_report | 1 | 1 | 1.0 | 0.1355 | 0.1189 | — |
| US/en/annual_report | 2 | 2 | 1.0 | 0.0183 | 0.0186 | 0.0364 |
| CN/zh-CN/investor_relations_qa | 1 | 1 | 1.0 | 0.0850 | 0.0538 | — |

Eval split (R0): 6/6 pages, macro strict 0.1194. Holdout split: 2/2 pages, macro strict 0.0419.

**R0 caveat (ROOT reception P2):** this arm is the real RapidOCR engine plus the production recovery ladder, but it concatenates recognition lines in backend return order; it is not the full production reading result with geometry/`order_page_lines`. Read-order CER differences must not be read as production end-to-end quality.

## 4. Programmatic fact / condition / number counts

Rule in `fact_match.py` (declared): surface presence = all numerals matched (value+unit+12-char currency window) and ≥60% CJK bigram / English content-word overlap; numbers need numerically well-formed entries (25 raw entries are nil dashes or spelled-out numbers and are excluded with the list kept). Full denominators include failed pages.

| arm | facts surface | facts numeric-anchor | conditions surface | numbers |
|-----|---------------|----------------------|--------------------|---------|
| R0 | 164/189 | 177/189 | 107/117 | 288/291 |
| N0 | 173/189 | 180/189 | 111/117 | 290/291 |
| X1F_attempt2 | 0/189 | 0/189 | 0/117 | 0/291 |
| X2 | 0/189 | 0/189 | 0/117 | 0/291 |

Unachievable raw number entries (excluded from the number denominator, listed in comparison.json): 25.

Sampled relation checks (gold is image-verified): KSY `338,857` → R0 emits `338.857` (comma→decimal); KSY 9-column header is emitted word-per-line, losing column binding; BRK `Business Activities` → `BusinessActivities`. Surface counts cannot prove relations; these checks are reported on top of them.

Unsourced-line negative control (card C3): each output line is checked against the image-verified gold by bigram containment (≥85% = sourced). R0: 38/501 unsourced (7.6%); N0: 5/308 (1.6%). This is an UPPER bound on fabrication: lines with recognition errors and justified line-wrap shifts count here even though no new claim was invented.

## 5. Controls (synthetic, excluded from all real denominators)

- **Formula symbol control**: 6/10 symbols kept; output `E = mc2
△G = △H - T△S
f(x) = ax² + bx + c
P/E = 23.7 x`.
- **Blank negative control**: R0 produced 0 characters (fabricated=False).

## 6. X1F — attempts, evidence, no quality claim

- `receipts\x1_20261101T152545_receipt.json`: cap 1.602 GiB, recorded peak 1.753 GiB, rc 3221225477, wall 106.5 s; 10 stage events, last: generate_start

Attempt 2 is the record: the model loaded (mapped fp32) in ~97 s, page 1 failed at generate with an allocator RuntimeError, page 2 crashed natively (0xC0000005) at 106.5 s wall. The recorded job peak exceeded the recorded cap, so the Job Object bound did not hold as expected — an OPEN platform question for ROOT, reported as measured, not hidden.

## 7. Coverage gaps (declared, not filled)

- No CN table and no US table in the frozen set (HK table covered, 9 columns).
- No genuine scanned/stamped/skewed/low-resolution page; no dual-column page.
- No IR-Q&A or conditional-negation page in this round's sample (the HK results prose and the Wuxi/Berkshire text carry conditions, but no Q&A format).
- Formula coverage is synthetic only.

## 8. Recommendation

- **现有不动** for production: R0 completed all 8 pages (macro strict CER 0.1000, number-token recall 0.9158).
- **困难页补救候选**: table-heavy pages (cell linearization, comma→decimal errors).
- **小米**: cannot be judged here. A card-compliant X1F result needs a host where the card cap (avail/2) exceeds the engine's measured fixed cost; both attempts' evidence and the platform-bound question are recorded for ROOT.

## 9. Artifacts

- `comparison.json`, `run_r0.json`, `run_n0.json`, `run_x1_attempt1.json`, `run_x1_attempt2.json`, `run_control_r0.json`, `run_r0_cache_resume.json`, `run_pilot_old_page_r0.json`, `campaign_ledger.json`, `fact_match.json`, `receipts/`.
- Frozen inputs (committed): `docs/plans/w23-ocr-r1-2026-10-31/{r1_sample_manifest.json,r1_gold.json,r1_control_manifest.json}`.
