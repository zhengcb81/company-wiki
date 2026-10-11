# W06-AUDIT-MEASURES — independent ROOT acceptance review

## Conclusion

**Accept the repaired typed-math tool within its declared scope.** The one P2 report-schema omission found during this review has been fixed and independently verified. No P1 defect was found in this review. Source truth, source qualification, company-wide coverage and forecast research quality are outside this verdict.

Reviewed product SHA: `b48e20bb9ecf88c1cb86821978c668cb83e963989dc4b1ca099b5d5bbad48020`. The exact eight product/test/wiring hashes are in `final-review.json`.

## Evidence

- The original 19 intake vectors were replayed without changing their ledgers or expected statuses: all 19 now satisfy the frozen expectations; no exception occurred.
- Eight additional probes check legal cross-entity market share, missing factual source, future assumptions, invalid source shape, boolean rounding, unavailable-at-as-of evidence and top-level invalid shapes: all eight have the expected arithmetic status.
- A real CLI invocation using malformed-but-valid JSON returns exit 2 and writes an immutable `INVALID` report; it does not crash the batch. Its owned scratch directory was absent before and after the invocation.
- Two pure-core invalid-shape outputs and that CLI report reproduce the P2 omission below. These original reports are retained in `final-counterexamples.json` and `cli-structured-invalid.json`.
- Author evidence was read: 76 focused / 296 complete tests passed, unchanged numeric tests and synthetic CN/HK/US CLI/E2E checks passed. This review did not repeat the complete suite.

## Closed P2 — inconsistent nonattestation field on invalid top-level inputs

`financial_measure_audit.py:587` uses `_empty_report` without `source_qualification_verified:false`, while normal reports and the documented contract include it. Inputs `[]` and `{observations:{}, relations:[]}` remain correctly `INVALID`, but their report shape differs and a strict downstream consumer could fail with `KeyError`. ROOT added the missing field to the empty-report factory. Independent final verification checks the two invalid pure-core shapes, a normal control, and an actual CLI invalid-shape report against the new SHA: all four PASS. ROOT retains its RED log and 77-test financial GREEN log; this review did not repeat the earlier 19/8 vectors or complete suite after the one-field change. The original reports remain unchanged. This correction introduces no permission, identity check or review gate.

## Architecture and semantics reviewed

Input and result entity/definition/kind/currency/scale/time compatibility, invalid dependencies, fixed arity, comparable periods, actual versus future roles, schema and as-of handling were checked. Decimal comparisons reject unbounded tolerances and coerced boolean precision. Legal cross-entity market share works with explicit scope. Unknown required factual provenance remains `UNRESOLVED`; optional unknown publication availability is a diagnostic, with source qualification always unverified.

ROOT's three wiring files (`SKILL.md`, `review-process.md`, `review-analyst.md`) explicitly keep the numeric tool supplementary to the four independent reviews. A tool `PASS` does not satisfy source reading, company-wide exhaustive coverage or the analyst's causal model and reasonableness assessment.

## Practical limits

Declared source IDs, scope, definitions, FX sources and display-precision descriptions are not verified against actual source bytes by this pure tool. Parallel segment sums and unequal 52/53-week comparability are not silently inferred. No provider, LLM, production document or paid resource was touched. This report signs no W04 economic quality or real-company research result.

## Final freeze verification

`report-boundary-verification.json` records the final SHA, three pure checks and one CLI check; all PASS with scratch absent again. Earlier 19/8 results were run at SHA `294af2a66f30334cd332b5e8e7210adb4d8793bf38959f2d902ee8db1474d808`; the final delta adds only the previously omitted boolean field. `review-before-schema-fix.md/json` preserve the independent original finding.
