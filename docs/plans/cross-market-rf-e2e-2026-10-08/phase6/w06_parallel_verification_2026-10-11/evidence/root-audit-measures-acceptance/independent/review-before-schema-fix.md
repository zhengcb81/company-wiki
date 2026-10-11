# W06-AUDIT-MEASURES — independent ROOT acceptance review

## Conclusion

**Accept the declared typed-math repair, with one P2 report-schema correction before final packaging.** No P1 defect was found in this review. Source truth, source qualification, company-wide coverage and forecast research quality are outside this verdict.

Reviewed product SHA: `294af2a66f30334cd332b5e8e7210adb4d8793bf38959f2d902ee8db1474d808`. The exact seven product/test/wiring hashes are in `final-review.json`.

## Evidence

- The original 19 intake vectors were replayed without changing their ledgers or expected statuses: all 19 now satisfy the frozen expectations; no exception occurred.
- Eight additional probes check legal cross-entity market share, missing factual source, future assumptions, invalid source shape, boolean rounding, unavailable-at-as-of evidence and top-level invalid shapes: all eight have the expected arithmetic status.
- A real CLI invocation using malformed-but-valid JSON returns exit 2 and writes an immutable `INVALID` report; it does not crash the batch. Its owned scratch directory was absent before and after the invocation.
- Two pure-core invalid-shape outputs and that CLI report reproduce the P2 omission below. These original reports are retained in `final-counterexamples.json` and `cli-structured-invalid.json`.
- Author evidence was read: 76 focused / 296 complete tests passed, unchanged numeric tests and synthetic CN/HK/US CLI/E2E checks passed. This review did not repeat the complete suite.

## P2 — inconsistent nonattestation field on invalid top-level inputs

`financial_measure_audit.py:587` uses `_empty_report` without `source_qualification_verified:false`, while normal reports and the documented contract include it. Inputs `[]` and `{observations:{}, relations:[]}` remain correctly `INVALID`, but their report shape differs and a strict downstream consumer could fail with `KeyError`. Add the same field to the empty-report factory and verify these two cases once. This correction does not introduce a permission, identity check or review gate.

## Architecture and semantics reviewed

Input and result entity/definition/kind/currency/scale/time compatibility, invalid dependencies, fixed arity, comparable periods, actual versus future roles, schema and as-of handling were checked. Decimal comparisons reject unbounded tolerances and coerced boolean precision. Legal cross-entity market share works with explicit scope. Unknown required factual provenance remains `UNRESOLVED`; optional unknown publication availability is a diagnostic, with source qualification always unverified.

ROOT's three wiring files (`SKILL.md`, `review-process.md`, `review-analyst.md`) explicitly keep the numeric tool supplementary to the four independent reviews. A tool `PASS` does not satisfy source reading, company-wide exhaustive coverage or the analyst's causal model and reasonableness assessment.

## Practical limits

Declared source IDs, scope, definitions, FX sources and display-precision descriptions are not verified against actual source bytes by this pure tool. Parallel segment sums and unequal 52/53-week comparability are not silently inferred. No provider, LLM, production document or paid resource was touched. This report signs no W04 economic quality or real-company research result.
