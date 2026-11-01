# P2 independent review — v3

Review date: 2026-10-31. Reviewer: independent P2 agent. Scope: the bounded, one-year Huali real-source adoption case, not a complete company forecast audit. This review made no network/model/parser/forecast-runtime calls, did not run repository tests, and changed no product, test, config, or PWF files. Only this review directory is written.

## Verdict

| Layer | Verdict | Meaning |
|---|---|---|
| Official/raw bytes, API reconciliation, currency, units and annual periods | PASS | Existing originals and normalized source spans independently cross-check. |
| Native used parameter and numerical formula | PASS | The selected parameter is Footwear/base/FY2026 units, multiplied by the footwear-only realized price. It is not an unused metadata parameter. |
| Formal publication/snapshot/isolated registry mechanics | PASS | v3 has formal, unattested publication receipts; independent canonical hashes, snapshot identity and all three registry links match. This is not a host-signed or economically accepted forecast. |
| Full t3-source semantic closure into formal artifacts | OPEN — blocking | The separate consumption receipt retains the complete summary/citation closure, but input/forecast/snapshot retain only the first support span. See P2-01. |
| Current company research/economic adequacy | OPEN | Five communication categories and six research dimensions are gaps; low/base/high are conditional assumptions. No company-audit completion is signed. |
| Overall P2 bounded adoption acceptance | OPEN pending P2-01 repair/review | Arithmetic and publication PASS cannot substitute for preserved summary meaning. |

P1 overall and P3 company-loop completion are outside this review. In particular this does not sign the Berkshire zero-POST attempt or its deferred important cards.

## Findings

### P2-01 — high / P1: native publication loses the full selected summary and source closure

Observed files:

- `C:/Users/郑曾波/Projects/revenue-forecast/.planning/m8-native-adoption-20261031/v3/consumption-receipt.json:138`
- `C:/Users/郑曾波/Projects/revenue-forecast/.planning/m8-native-adoption-20261031/v3/input.json:688`
- `C:/Users/郑曾波/Projects/revenue-forecast/.planning/m8-native-adoption-20261031/v3/report.md:194`
- `C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_narrative_context.py:216`
- `C:/Users/郑曾波/Projects/revenue-forecast/scripts/narrative_summary_usage.py:216`

The public reader path is real: `consume_narrative_input` calls `read_narrative_context`, which invokes CWP's `company_wiki.source_catalog.narrative_transport_cli` subprocess. The consumption receipt binds exact artifact body `ec1831a2fdf2952a9a80aba0c9e5db65c8bc581ea5c0a10d53d01ef2faba52d8`, `t3-source`, claim digest `29df07901b23643bfd748cd0daef1c3b082c8797699eedbfddb8a644b3faefd6`, all five support IDs (p1 paragraphs 28–32), the p1/27 question as context, the explicit research reason and an actual native formula reference.

But the input before/after diff changes only `parameters` and `evidence_claims`: one parameter gains source/claim IDs and one RF claim is added. Neither its numerical value nor its pre-authored rationale changes. The added native RF claim contains only p1/28: “A：目前部分运动品牌的库存比较高，同时由于国际政治、经济形势复杂，很多品牌基”. That incomplete sentence does not contain old/new customer divergence, conservative order forecasts, or the expectation of partly filling gaps. Those meanings occur in p1/29–32.

The input has no versioned narrative citation/summary-use record. Its exact artifact SHA, `t3-source`, full original support text and use explanation are absent from both embedded input documents, the result and snapshot. The report renders the same first-span fragment. The separate unbound consumption receipt retains the semantic closure, but the published forecast hash does not freeze it. `status=used_in_parameter_rationale` therefore proves the adapter's joined sidecar, not complete summary adoption in the formal report/snapshot. Merely retaining a source ID and a half-sentence claim cannot establish the intended rationale.

Required acceptance expectations:

1. Preserve a versioned native record for the exact artifact/summary claim, original source/capture, full support/context closure with locators and text/hash, the caller's explicit explanation, and used parameter/formula targets. Include it in the input/result/snapshot hash domain.
2. Show the complete source-owned answer (or an exact bounded continuous answer plus auditable full closure) and the research explanation in the formal report; a single first span is insufficient here.
3. Preserve `uncertain`, `needs_review`, partial selection and unknown publication/FY without upgrading these to semantic acceptance. This historical IR is mechanism context, never evidence of realized FY2026 volume or full gap offset.
4. Verify that the native persisted record matches the public-reader material and the current parameter dependency graph; do not accept a caller-assembled, self-hashed statement of closure alone.

Negative cases that must fail or become explicitly unclosed: remove p1/32 while claiming the same complete t3 closure; promote p1/27's question to support; swap t3 or artifact/source hash; alter a frozen support excerpt/hash or research reason without rebinding; point to a different company/scenario/period or unused parameter; change the formula mapping after adoption; retain only p1/28 and claim complete summary use. No new LLM call is needed for this repair.

### P2-02 — medium / P2: historical operating anchors are not individually cited in the formal evidence set

`C:/Users/郑曾波/Projects/company-wiki/.planning/mainline-closeout-20261031/run_p2_native.py` reads and checks p17 sold pairs (22,699万双, FY2025, 1.59% reported growth) and p19 nominal capacity (24,757万双, FY2025). The saved normalized spans do support those facts. However all future operating parameters' native evidence claims cite the broad p15/25–42 strategy/order narrative; the p17 and p19 numeric anchors do not enter their formal claim chain. The fixed-price rationale similarly cites p15 rather than the footwear-revenue/sold-pairs conversion inputs.

This does not make the conditional numbers false, and it does not imply an exact FY2026 measurement. It limits the standalone auditability of the case's stated historical anchoring. Carry the FY2025 volume/growth/capacity and footwear-only price derivation as historical rationale evidence with their real periods and units. Do not label them FY2026 actuals or management guidance.

### P2-03 — low / P2: report rounds every unit price to zero

`C:/Users/郑曾波/Projects/revenue-forecast/.planning/m8-native-adoption-20261031/v3/report.md:86` shows `unit_revenue = 0.00`, although its actual value is `0.00010996114816480902 CNY million per pair`, equivalent to about `109.961148 CNY per pair`. JSON and arithmetic are correct, but a report-only reader cannot reproduce the displayed multiplication. Render meaningful precision or a clearly labeled yuan/pair display conversion.

## Independent source and numerical checks

The executable independent probe and detailed machine-readable observations are `probe_v3.py` and `probe-v3.json` in this directory. All 24 checks passed their stated predicates, including the explicit predicate documenting P2-01's missing native closure; that count is not an overall semantic PASS.

- Annual raw decompression matches SHA `15eb6c7669af7d05b341ec0f42b47c1da469776e56d299addb18ca53511a4c74`, 4,079,810 bytes. Source identity: 华利集团/300979, FY2025 annual report, published 2026-04-10.
- Financial raw decompression matches SHA `9c5d794314df3033fb72f5af374e6f817ebe0f8838f83c10aa14dbf2394ac9a5`, 176,598 bytes. Its provider amount rows preserve `unit=null`, `scale=null`; currency is CNY, annual consolidated period ends are 2024-12-31 and 2025-12-31, and knowledge mode is current snapshot, not historical PIT.
- The API values are precisely `24,006,393,622.27` (2024) and `24,980,125,148.09` (2025). Annual p8/15 supplies column years, p8/16 supplies “营业收入（元）” and both values, and p6/16 defines yuan as RMB. Dividing by 1,000,000 therefore produces the native CNY-million values without inventing a provider scale.
- Annual p16/20 gives Footwear `24,960,081,021.93` yuan plus Other `20,044,126.16` yuan, exactly the total. Other remains separately flat and is excluded from footwear ASP; there is no double count.
- Sold pairs: `22,699 × 10,000 = 226,990,000`; nominal annual capacity: `24,757 × 10,000 = 247,570,000`. Sold-pair ASP is footwear revenue only divided by actual sold pairs, not production or capacity.

| Case | FY2026 conditional pairs | Independently recomputed company revenue, CNY million | Stored result | Absolute rounding difference |
|---|---:|---:|---:|---:|
| Low | 204,291,000 | 22,484.117045897 | 22,484.117045896997 | 3e-12 |
| Base | 230,599,141 | 25,376.990436338687 | 25,376.990436338685 | 2e-12 |
| High | 247,570,000 | 27,243.12557732176968 | 27,243.125577321767 | <3e-12 |

The direct derivative of company revenue with respect to base footwear pairs is positive `0.0001099611481648090224 CNY million per pair`; actual model input driver IDs and actual stored driver values match this product. This is independent arithmetic, not another formal model run or ROOT's 1% sensitivity probe.

## Source meaning and temporal limits

The frozen original gold header for this exact IR source SHA identifies IR record 2023-010, meeting dates 2023-05-11, 12, 17 and 18. May 19 in the filename is not the meeting date. `published_date`, fiscal year and period remain unknown in the native IR source manifest. `current_verified_open` says only that exact bytes were available by 2026-10-31. The v3 report's gap at line 171 correctly says the content is May2023 and does not create a 2026 capacity plan.

The complete t3 source text preserves high inventory, conservative forecasts under uncertainty, declines at some brands, growth at others, and new-customer orders partly filling some gaps. It has `modality=uncertain`, `needs_review=true`; the sidecar does not claim all customers or complete offset. FY2025 annual p15/25–42 separately corroborates divergent customer orders, new-client ramps and actual shipments; p30/23–29 supplies demand/trade/tariff counterevidence. The native conditional rates remain analyst assumptions: Low is 90% of 2025 sold pairs, Base repeats the disclosed rounded 1.59% sold-pair growth, High assumes sell-through at 2025 nominal annual capacity with flat inventory, and ASP is flat. None is a calibrated probability band or current management guidance.

## Formal mechanics, attempts, recovery and boundaries

- v1 failed the input claim target-type schema; its draft catch also failed. v2 failed the growth-driver target binding. Neither is success. Their logs are preserved. v3's recorded formal entry invokes `run_forecast`, `validate_published_forecast`, and `create_snapshot` without a draft fallback.
- v3 canonical input SHA: `bb973e27c94a4f4052b887c06143e33d544bb2175c0ef287d6783e0528b1b7c0`; result hash: `4c2eba36fcbe1149d442fb6980c93d05a29e75e6213c8baf333ee02c21c52fdc`; snapshot ID: `feed49d0f2aec9ed2ed9b5e80c96a4109b990fcd85642f842609e82373e25c7d`. Exact embedded input/result objects and all independent canonical hash checks match.
- Publication mode is formal, schema 3.7, engine 4.3.0, attestation `unattested`. All three isolated registry rows chain correctly: first forecast, snapshot's repeated identical formal computation, snapshot anchor. The snapshot's full forecast digest differs from the result's digest by design because the latter excludes its own hash field.
- The financial acquisition records one HTTP/176,598 bytes; its second reuse records zero HTTP/zero bytes. The annual acquisition records one download; its reuse records zero downloads. These preparation downloads are distinct from v3's zero-new-download adoption run; do not report the whole P2 preparation as zero downloads.
- The v3 harness installs an AF_INET/AF_INET6 connect guard in parent and reader subprocess. It activates an exact previously prepared artifact in a temporary CWP lake and uses the public reader. Locator replay necessarily reopens/parses its PDF; no claim of zero PDF work is made. This review itself did not replay it.
- All three recorded temporary roots (financial, annual, v3 adoption) are absent and report `removed=true`; preparation receipts report protected files unchanged. Formal forecast/report/snapshot/registry live under RF's owned directory, while CWP retains source artifacts and test/review material. This review found no new CWP canonical research writer.

Current research remains OPEN: the report openly records only one of six management-communication categories checked, six research dimensions as data gaps, no historical backtest, no configured sensitivity and a conditional driver with limited evidence. Runtime `research_coverage`/`management_target_coverage` PASS and the approximately 60/100 evidence/workflow score do not mean complete economic research or a calibrated chance of forecast success. No additional research steps have been silently signed off here.
