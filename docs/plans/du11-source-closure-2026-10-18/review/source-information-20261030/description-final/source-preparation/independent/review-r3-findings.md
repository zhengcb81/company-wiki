# Follow-up source preparation review, findings open

The original two CN findings now pass all six original independent checks.

## P2: persisted SEC kind depends on the first request

An actual synthetic FY2001/FY/10-K is first encountered during `regulatory_filing FY2026 Q2` preparation. The new nonmatching-scope persistence correctly stores original year 2001, period FY, form 10-K, but sets `document_kind` from the unrelated request to `regulatory_filing`. A subsequent `annual_report FY2001 FY` request returns `not_found/no_registered_local_source` for those same bytes. The existing annual-report request has a one-way correction for nonannual forms; the reciprocal source kind is not canonical when a regulatory request first sees an annual original. Persisted source kind should be owned by the actual form grammar, independent of request order. See `test_us_scope_neutral.py` and `replay-r3.{xml,txt}` (1 failed, 6 passed, 1.54 s including original CN checks).

## P2: wrapped reference bypasses the new reference guard

`请查阅海川股份有限公司\n2026年年度报告` is still promoted to a proved annual title: the candidate beginning at the suffix line avoids the guard on the first line. This is candidate provenance across PDF wrapping rather than a new reference verb. The preexisting annual candidate loop could also exhibit the split-line behavior; the new shared helper/guard does not yet close that boundary. See `cn-r4.{xml,txt}` (1 failed, 6 passed, 1.21 s). Real standalone and wrapped legal titles must continue to work.

No product or author-test file was changed. `replay-r2` records a reviewer harness import error (`integration` path missing), fixed only in the independent test before the valid `replay-r3` run. Synthetic fixture state uses the repository's pytest temporary-directory owner; its printed cleanup receipts are retained. No original financial documents, SDKs, models, external APIs, or production state were accessed.

Both findings were sent to ROOT immediately; final five-file approval is pending repairs and stable bytes.
