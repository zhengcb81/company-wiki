# Correlated price period root repair — final frozen handoff

## Latest freeze; prior typed reception is historical

Independent review found 3 genuine P1s: a stock times the same/like annual price ratio was accepted as annual income at validation, forecast and both strong readers. Original inputs and accepted outputs remain untouched in independent-typed-final. This freeze supersedes the earlier typed freeze; it is engineering delivery for nonauthor review, not already merged acceptance or real-company research quality PASS.

## Shared root and repair

The old period_powers={0,1} Cartesian products chose different spot/annual meanings for repeated prices. The single contracts/period_flow.py owner now carries **affine period expressions with shared symbols and equations** through actual AST operands and recursive aliases. Multiplication/division add/subtract original symbols; addition/subtraction and each intermediate annual revenue impose equations. All equations must have one consistent interpretation, rather than choosing each occurrence independently. Like raw temporal prices of one existing price dimension share a role. Original unit/currency/scale responsibilities remain unchanged; the 3 price dimensions bound inference to at most 8 assignments, independent of leaf/alias count.

This is NOT an x/x name special case. Same symbol, derived ratio, nested alias, equivalent expression, distinct prices with different amounts and scalar coefficients all preserve actual stock/flow type. A price ratio scales existing income and cannot supply duration to a stock. Actual AST references carry constraints; an unused input does not independently constrain the formula. Derived prices keep actual income/quantity ancestry. Real turnover flow/stock, point quantity times annual ARPU, real dated/annual quantity times transaction price, and native subscription/fee/bank yield controls remain legitimate.

No new schema, source/identity store, authorization, review receipt, consumer exception or gate was added. Source/annual consumers reuse the same owner. Schema3.9/earlier wiring and defaults remain unchanged. If one generic formula genuinely needs both raw ARPU and transaction price of the same dimension, use actual flow-derived ARPU or existing native model roles; free text does not prove distinct roles. Source economic truth, dates, scopes and buy-side assumptions remain independently audited responsibilities. Generic dated stock-pricing is not a sum of evidenced interval contribution flows.

## Formal tests and execution

- exact-red.json: unchanged 3 independent inputs/outputs accepted at all 12 boundaries, actual FAIL retained.
- business-red.log: 6 stock cancellation/alias/equivalent/coefficient cases FAILED; 7 real-income scaling and annual quantity controls passed. Negative assertions were not changed.
- focused-green.log: 158 tests +33 subtests PASS in3.19s across common rules and prior period/consumer/reader suites. One additional requested dated quantity positive control then joined the existing final gate.
- final-node-before-host-fixture.*: first gate retained, 386 tests +36 subtests passed/4 failed. One NEW positive fixture had a revenue-helper currency field on quantity; repaired with the existing quantity contract helper, original business assertion unchanged. Three existing CLI integration cases were given explicit FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT after this runner omitted their configured roots. No source dependency or gate code changed.
- final-node.log/json: ruff and public mypy11 files PASS; **390 tests +36 subtests PASS**, pytest42.00s/entry46.311s. The single existing daily gate was used; no added gate.
- exact-final-green.json: the same 3 frozen inputs and outputs now reject with actual typed-flow errors at all **12 boundaries**, not publication-environment errors.
- Two native forecast JSON/Markdown outputs plus C1 immutable snapshot (5 files) are **full-byte equal** to the earlier legitimate frozen outputs. Date/currency rehash checks pass. Owned scratch absent before and after.
- 0 provider calls, 0 LLM calls, $0. Canonical assurance/output WIP unchanged; original worker clean. No commit, push, main merge or installed-file write.

## ROOT handoff

Latest root-product-inventory.json carries exact current product SHA/bytes; latest install-readonly-plan.json carries current 17 runtime source files and old target SHA at 2 real targets (.claude junction deduplicated). Only --plan ran. ROOT should perform nonauthor replay in a NEW evidence directory, then normal hooks/merge/selective install/push, preserving canonical WIP. Original earlier FAILs and the 8 frozen legitimate artifacts must remain unchanged.
