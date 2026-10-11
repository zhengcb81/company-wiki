# W05-RF-FLOW: independent typed final review

## Verdict

**FAIL_NEW_PRICE_PERIOD_CORRELATION_P1. Do not accept or merge this freeze.**

The original three temporal P1s and the original point monetary stock alias are
now rejected correctly. The final shared type helper still permits a stock to
become annual income through cancellation of an ambiguous raw annual price.
This is a shared mathematical type/provenance defect, not a company-specific
case, source identity problem or missing permission.

## Frozen product and execution

All **30 files / 807,661 bytes** match `fix/root-product-inventory.json` before
and after independent execution. The frozen root is
`C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root`, declared base
`1b616622763ece6549676f2a74f596e6c65244af`, pending original delivery
`f1a782a478d255b9b4b8f531e7a3961134e257ba`.

The review executed **24 bounded synthetic cases**, including eight unchanged
inputs from `independent-final/original-point-stock-annual-fail.json`, thirteen
independently constructed formulas, and three native model positive controls.
There are 58 individually recorded validation/forecast/reader boundary outcomes
for the first 21 cases. Three new cases fail their reject expectations at all
four native boundaries. The independent run took 1.188 seconds after imports.

The original point stock P1 also received a separately rehashed forged output:
both strong readers reject it with the actual `typed flow` error. The original
FAIL file remains byte-identical. No former FAIL evidence was edited.

## New P1: price interpretation loses correlation through division

The raw annual `revenue_per_unit` leaf receives period powers `{0,1}` at
`scripts/contracts/period_flow.py:246`, representing transaction price or annual
ARPU. `combine` at line 231 forms a Cartesian product of these interpretations.
Division applies that product at line 288; the annual revenue check accepts if
the resulting set merely contains 1 at line 304.

Consequently the same price divided by itself can have powers `{-1,0,1}` rather
than the required scalar zero power. The code chooses an annual interpretation
for one occurrence and a spot interpretation for the same other occurrence.
Adding derived aliases does not fix that loss of shared origin. Two like annual
price leaves are likewise allowed to manufacture a turnover interpretation.

The independently built failing cases are:

| Case | Formula | Correct meaning | Observed result |
| --- | --- | --- | --- |
| `same_price_cancels_inline` | `stock20 * (annual_price2 / annual_price2)` | A monetary stock of 20 | Annual contribution 20; FY2026 low 170 |
| `same_price_cancels_derived` | Derived price ratio `x0/x0`, then stock × ratio | Stock × scalar, still a stock | Annual contribution 20; FY2026 low 170 |
| `distinct_equal_prices_cancel` | Ratio of two like annual prices, then stock × ratio | Like annual prices cancel their duration | Annual contribution 20; FY2026 low 170 |

For every row, `validate_document`, `run_forecast`,
`validate_published_forecast` and `validate_forecast_output` all accept the
complete synthetic document. All six exact accepted input/output artifacts are
retained beside this report with manifest hashes. The numbers do not depend on
a forged result or a failed publication environment: ordinary native publication
and both readers completed successfully.

The shared repair must preserve consistent interpretation of the same source
symbol and derived lineage. A dimensionless price ratio cannot supply annual
duration merely through an existential choice of spot/annual interpretation.
Matched quantity-stock × annual ARPU and annual operating-flow × transaction
price roles remain legitimate; real flow/stock turnover retains its flow
ancestry. Do not repair this by rejecting every price, introducing a permission
gate, checking a company or parameter name, or changing these expectations.

## Correct behavior retained

- The exact three original temporal P1 inputs reject: partial flow relabeled
  annual, moving a 2026 amount to 2027 with rationale, and H1 plus its own Q2.
- The original annual and dated stock aliases and zero-weight coverage padding
  reject. Additional independent stock/rate/scalar aliases, nested stock,
  stock-plus-flow, cancelling true flow back to stock, stock-derived ARPU and
  zero-weight price anchors reject.
- Point quantity × annual ARPU, annual income-derived ARPU, and stock × actual
  annual flow/stock turnover pass validation, forecast and both strong readers.
- Native subscription, asset-management fee and bank yield models keep their
  ordinary stock roles and exactly the prior consolidated revenue numbers.
- One independent native CLI replay, with network calls denied and a minimal
  child environment, passes. Its JSON and Markdown bytes equal the frozen CNY
  synthetic case exactly. Both strong readers accept its native result.

## Isolation and limits

The owned scratch was absent before execution and is absent afterward. Only
files created inside this report's `_owned_scratch` were removed; no preexisting
directory, canonical WIP, installed skill, original document or product code was
changed. Product hashes and original failure hashes are verified before/after.
No provider, LLM or network calls occurred; fees are $0. No 376-test suite or
3.9 compatibility suite was repeated.

This verdict covers engineering arithmetic, duration provenance and actual
native boundaries. Synthetic source claims are not evidence that real source
facts, group inclusion, forecast economic assumptions or buy-side research
quality are valid. Those remain separate source/research audit responsibilities.

## Next handoff

ROOT was notified immediately and has retained the RF acceptance/merge hold.
The author should add these exact failures to common-type TDD, repair consistent
symbol/price-period interpretation and freeze a new inventory. A later nonauthor
review must use a new output directory, replay the retained inputs unchanged and
check the legitimate price/turnover/native-role controls. Do not rerun
`probes.py` into this directory and overwrite the original failure evidence.

