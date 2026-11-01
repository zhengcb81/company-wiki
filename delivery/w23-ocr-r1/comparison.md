# W23-OCR-R1 Comparison (cwp-ocr-comparison/1)

PLAN_ID=w23-ocr-r1-2026-10-31 · worktree `company-wiki-w23-xiaomi-ocr-r1` · branch `codex/w23-ocr-r1-20261031` · base `946537d0`

**Status: PARTIAL.** R0 (production RapidOCR) and N0 (born-digital native-text
control) completed all 7 frozen pages inside one cumulative campaign. The
Xiaomi arm (X1F) was attempted **once** under the card's memory rule and failed
at load with `MemoryError`, because the measured available RAM made the allowed
cap (1.142 GiB) smaller than the engine's measured fixed load cost (1.33 GiB);
no retry was made and nothing about its quality is claimed. X2 is NOT_RUN. This
report replaces the 2026-10-30 exploratory result for the purpose of card
compliance; the old sample, gold and raw outputs remain untouched as history.

## 1. One campaign, one ledger

- Budget: **1800 s** total inference for R0 + X1F attempts + the formula
  control, per-request deadline min(180, remaining), single concurrency.
  Ledger file `campaign_ledger.json` (append-only; atomic writes; corrupt state
  refuses to run).
- **Consumed: 226.1 s** of 1800 s. Breakdown: R0 7 frozen pages = 144.2 s
  (12.8–28.1 s/page), real-engine pilot on the old non-holdout page
  (`byd_ar_2024_p021`, old eval page) = 19.4 s, X1F attempt 1 = 57 s (failed at
  load), N0 = 0 s (text layer), formula control R0 ≈ 5 s. The ledger also carries 7 zero-second R0
  rows from a timing defect in the first invocation (the backend returned no
  timing and the wrapper recorded 0); those rows were kept rather than edited,
  so the campaign can only over-count, never under-count. The corrected 144.2 s
  rows are the honest measurement.
- Every request was measured by the caller around the call; the X1 child runs
  under a Windows Job Object at `min(8 GiB, avail/2)` and a parent watchdog that
  kills a blocked request at its deadline.
- Cache: `.w23_cache/r1_cache` (persistent). A second invocation served records
  from cache with `cache_hit=true`, `inference_runs=0`, original measured time,
  and re-charged 0 s; the cross-process TDD (`tests/integration/
  test_w23_ocr_r1_campaign_processes.py`) locks that behaviour.

## 2. Frozen sample (this round)

Seven pages, frozen before any engine ran on them (`r1_sample_manifest.json`
sha256 `1d455f91…`, gold `r1_gold.json` sha256 `71f9d1bd…`, commit 970532af):

| page | market/lang | role | gold chars | notes |
|------|-------------|------|-----------|-------|
| r1_amec_ar2025_p029 | CN zh-CN | eval | 1,117 | 中微 2025 年报，行业/产能/客户 |
| r1_wuxi_ar2022_p010 | CN zh-CN | eval | 1,822 | 药明康德 2022 年报，管理层讨论 |
| r1_ksy_fy2025_results_p003 | HK zh | **holdout** | 947 | 金山雲 FY2025 业绩正文 |
| r1_ksy_fy2025_income_p012 | HK zh | eval | 2,063 | 未經審計簡明合併綜合虧損表（**真实 9 列业务表格**） |
| r1_biren_ar2025_p030 | HK zh | eval | 583 | 壁仞科技 2025 年报 |
| r1_brk2007_p001 | US en | **holdout** | 4,533 | Berkshire Hathaway 2007，Business Activities |
| r1_brk2007_p005 | US en | eval | 3,817 | Berkshire 2007，致股东信 |

No page reuses a document from the 2026-10-30 sample; the old pilot page
(`byd_ar_2024_p021`) was not run in this campaign at all. Gold was produced by
an **independent reviewer** from the PNGs only (no OCR, no PDF text layer as
truth), with per-page facts/conditions/number tokens and a documented revision
(one weak HK page replaced by two stronger pages from the same PDF, before any
engine ran). The gold revision block records the swap, why, and that the
retired page was not rewritten.

## 3. Results — full denominators, every page counted

| arm | pages scored / total | macro CER strict | macro CER narrow | macro WER | number-token recall | digit-present recall |
|-----|----------------------|------------------|------------------|-----------|---------------------|----------------------|
| R0 | **7 / 7** | 0.1022 | 0.0801 | — (only 2 EN pages; per-page WER below) | 0.9117 | 0.9905 |
| N0 (control) | 7 / 7 | 0.1178 | 0.0886 | — | 0.9965 | 1.0000 |
| X1F (attempt 1) | **0 / 7** | null | null | null | null | null |
| X2 | 0 / 7 | null | null | null | null | null |

Per stratum (R0, all pages present): CN/zh-CN 2, HK/zh 3, US/en 2 —
`coverage_by_stratum` in comparison.json is 1.0 for every stratum. English WER
is reported per page (two EN pages): `r1_brk2007_p001` 0.0178,
`r1_brk2007_p005` 0.0550 (macro 0.0364 over the two pages; N0 control
0.0048 / 0.0000, macro 0.0024).

Failure accounting is explicit and complete: every X1F row is
`status=error` / `MemoryError` at load with the cap and fixed-cost numbers in
comparison.json; they count as **zero** in every aggregate and remain in the
denominator. Nothing is zero-filled as if it had produced text.

## 4. Programmatic fact / condition / number counts

Computed from the per-page gold and per-page records by a fixed rule stated in
`fact_match.py` (declared before the run): a fact/condition is present when all
its numeric tokens appear with matching units (comma/space-insensitive) and
≥60% of its CJK bigrams / Latin words appear in the arm text; a number is
present when its (value, unit) pair appears. Full-sample denominators include
failed pages; the 2026-10-30 totals are **not** carried over — these are
this round's numbers.

| arm | facts (hit/total) | conditions (hit/total) | numbers (hit/total) |
|-----|-------------------|------------------------|---------------------|
| R0 | 106 / 171 (62.0%) | 75 / 98 (76.5%) | 268 / 301 (89.0%) |
| N0 | 115 / 171 (67.3%) | 79 / 98 (80.6%) | 271 / 301 (90.0%) |
| X1F | 0 / 171 | 0 / 98 | 0 / 301 |

This surface-form rule cannot prove semantic relations (the card's warning), so
three relation checks were sampled from the original-image-verified gold:

1. **KSY income statement, `338,857`** — gold prints 338,857 (thousands); R0
   emits `338.857`, i.e. the thousands comma became a decimal point. The digit
   string matches, the printed unit/relation does not.
2. **KSY table header order** — gold's 9 columns (Q1–Q4'24/'25 RMB, USD,
   FY2024, FY2025 RMB/USD) are printed as a 5-line header; R0 emits each header
   word as a separate line in reading order, so column-to-value binding is lost
   even though all header words exist.
3. **BRK p001 sentence** — gold `Business Activities` (section head); R0 emits
   `BusinessActivities` (space lost). Content preserved, form changed.

## 5. Formula-symbol control (synthetic, declared)

The frozen real pages contain no formula (confirmed by the gold reviewer), so
the card's minimal control uses `r1_formula_control.png` — a declared synthetic
white page with `E = mc²`, `ΔG = ΔH − TΔS`, `f(x) = ax² + bx + c`,
`P/E = 23.7 ×`. R0 output: `E = mc2` (superscript ² lost), `△G = △H - T△S`
(Δ→△, minus→hyphen), `f(x) = ax² + bx + c` (² kept here), `P/E = 23.7 x`
(×→x). Result: **1 of 4 formulas fully symbol-faithful**. It is a control page
only, excluded from every real-document denominator and from all market/genre
statistics.

## 6. X1F attempt — measured reason, no quality claim

- Attempt 1, inside this campaign: host available RAM 2.28 GiB at start →
  allowed cap 1.142 GiB; the engine's measured fixed load cost (imports +
  processor) is 1.33 GiB, so the child received `MemoryError` at load.
  All 7 pages: `error`, `MemoryError`, 57 s charged.
- Later checks in the same campaign window: cap 0.838 GiB (avail 1.68 GiB).
  The condition never improved, so no second attempt was made (the card forbids
  repeated timeouts and auto-retries that wash costs).
- Identity recorded: frozen checkpoint `d4551e9f…b5d5348`, exact-fp32 derivative
  `ddd3b661…9dcc71f`, read-only mapping, upstream prompt/greedy/postprocess,
  explicit `max_new_tokens=4096` (never 16384 this round), per-request 180 s.
- What the earlier exploratory run showed (declared variant, 2026-10-30) is
  **not** used as a card-compliant result here; it stays exploratory history.
  Saying "Xiaomi is invalid" is not supported by this evidence either: the
  failure is a host-memory bound, not a model quality result.

## 7. Coverage gaps declared (not filled)

- No **CN table** and no **US table** in the frozen set (HK table covered).
- No genuine scanned page, stamp, skewed or low-resolution page (all born-digital).
- No dual-column / multi-article reading-order page.
- Formula coverage is synthetic only (by design).
- Both BRK pages print widened sentence spacing; scoring uses the declared
  whitespace normalization.

## 8. Recommendation

- **现有不动** for the production stack: R0 completed all pages with
  macro strict CER 0.102 and 89% number-token recall, and its failure classes
  (table cell linearization, thousands-comma errors, missing characters) are
  observable in the diagnostics.
- **困难页补救候选**: table-heavy pages need a structure-aware reader; R0's
  cell-order linearization is the concrete gap measured here.
- **小米（X1F）**: cannot be judged on this host in this campaign. To produce a
  card-compliant X1F result the host must have roughly ≥6.5 GB available RAM at
  run start; then the existing campaign entry reruns with the same ledger rule.
  No integration decision should be taken from the exploratory run.

## 9. Artifacts

- `comparison.json` — machine report (`cwp-ocr-comparison/1`) with campaign
  ledger summary, per-page rows with source/page/image SHA, per-stratum coverage,
  fact_match counts, arm statuses.
- `run_r0.json`, `run_n0.json`, `run_x1_attempt1.json`,
  `run_formula_control_r0.json` — per-arm captures.
- `campaign_ledger.json` — append-only budget ledger (206.7 s spent).
- `fact_match.json` — per-page fact/condition/number hits for all arms.
- Frozen inputs (committed): `docs/plans/w23-ocr-r1-2026-10-31/
  {r1_sample_manifest.json,r1_gold.json,r1_control_manifest.json}`.
