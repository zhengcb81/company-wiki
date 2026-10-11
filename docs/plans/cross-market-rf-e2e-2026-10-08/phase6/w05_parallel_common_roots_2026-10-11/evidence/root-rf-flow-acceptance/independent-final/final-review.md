# W05-RF-FLOW — independent final acceptance, first freeze

## Verdict

**FAIL_NEW_TYPED_ANCESTRY_P1. Do not accept this freeze yet.** The original three P1 counterexamples are fixed, but an independent typed stock alias still passes as annual recognized revenue. ROOT and the author were notified immediately; ROOT has assigned a systematic typed-ancestry repair.

The product root is `C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root`, HEAD declared `1b616622763ece6549676f2a74f596e6c65244af`, pending worker merge `f1a782a478d255b9b4b8f531e7a3961134e257ba`. All 29 ROOT inventory SHA/byte records match. Exact key-file SHA values are in `final-review.json`; period-flow SHA is `31ac27d37180c4a08f801745efe399ffc1281adad89b145f677fa5e94622841e`.

## New P1: point stock can bypass the annual wrapper

`validate_windowed_composition` skips an annual derived parameter with no `period_flow` ancestor; `validate_annual_consumption` accepts its annual label. A `point_in_time`, `monetary_balance` value 20 is passed through `derived_fact formula=x0` with outer `dimension=revenue` and `time_basis=annual`. The ordinary acquisition adjustment consumes it: `validate_document`, `run_forecast` and both strong readers all accept; FY2026 low revenue increases from 150 to **170**. No stock-to-flow model or annual pricing driver supports the conversion.

The exact complete input is preserved as `original-point-stock-annual-fail.json`, case `independent_point_stock_cannot_be_annual_revenue_alias` / `cases[5].input`. The constructor is `probes.py:stock_as_annual`. The corresponding dated wrapper is rejected correctly, proving the hole is the annual no-dated-ancestor trigger, not financial arithmetic.

The repair should validate typed ancestry through all relevant annual wrappers while preserving legitimate native stock quantity × annual price/ARPU and stock-flow model formulas. It must not become a blanket annual-only rejection, company-specific branch, rationale exemption or permission check.

## Independent executed results

The original three P1 builders and reject expectations were reused without edits: partial derived → annual, rationale moving a 2026 window to 2027, and H1 + own Q2 all now receive real composition errors. The original post-control bridge and small negative disposal pass formal forecasting and both readers. The nonzero/zero-weight coverage probe is correctly rejected. The dated stock alias rejects; the annual stock alias incorrectly passes. All eight exact inputs/results are retained.

The first harness omitted an explicit publication registry and encountered sandbox denial of the default external-tree artifacts path. That result remains in `first-unconfigured-registry-probes.json` and is not counted as a correct business rejection. The isolated rerun uses an owned registry, so the P1 truly reaches formal publication and strong readers. The immutable registry's read-only attribute initially prevented ordinary cleanup; the owned absolute scratch was checked, its temporary attribute cleared and the directory removed. `probe-cleanup.json` records absent → absent.

## Scope and remaining checks

Authored 356+36 daily and 52+7 portable compatibility GREEN evidence, recognition validation ordering and the explicit-root registry split were reviewed without rerunning the large suites. Additional H1/Q3, annual-rate extrapolation and rate/scalar controls have not been independently run; ROOT requested this turn stop after P1 evidence. No independent CLI subprocess was completed here. A final follow-up should replay the preserved P1 and selected legitimate typed-pricing controls after the author's freeze.

This is an engineering/temporal semantics verdict. It does not verify real source facts, group/subsidiary business inclusion, the validity of arbitrary scope text or buy-side forecast economic quality. No original, live provider, LLM, installed copy or product code was changed. Cost is zero.
