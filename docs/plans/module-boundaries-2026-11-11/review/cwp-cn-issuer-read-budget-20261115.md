# CWP CN issuer proof: shared request read budget

**Status:** implementation independently reviewed PASS; targeted tests green; local publication pending.
**Review snapshot:** local branch `master@7fd7f248deed8ff161ddab439f6b4d8a2875b239` plus the four modified source/test files identified by SHA-256 below. The local 512MB-cap commit is not on `origin/master`; publication will replace that unpublished intermediate with the net root fix.

## Root cause

CN issuer proof was using a second, fixed aggregate byte counter (`_MAX_CN_PROOF_BYTES=64MB`). The source catalog already owns a request-scoped `ReadBudget` (default 2GiB and 64 candidates), but `SourceVersionReader.open_described_version()` did not accept the caller's budget. The proof path therefore bypassed the canonical accounting owner and rejected a valid 36-filing corpus totaling about 126MB. Raising the private limit to 512MB would only move the arbitrary threshold and leave duplicate budget ownership.

## Change

- `PublicCanonicalBrowser.browse()` creates one `ReadBudget` for that browse request and passes it to each CN issuer proof read.
- `SourceVersionReader.open_described_version()` accepts the optional shared budget and forwards it to the existing verified-location resolver.
- The duplicate aggregate byte cap/counter is removed. Actual byte-size and SHA verification, shared candidate/byte accounting, and each-PDF/page/text limits remain in the existing owner paths.
- Exceeding the shared byte budget still returns the existing pathless `cn_primary_proof_budget_exceeded` result. A new browse receives a fresh budget.
- An existing exact-history contract test created a second SQLite catalog without closing it. The full assertion run passed but pytest teardown exited 1 due the locked file; both catalogs are now closed in `finally`.

## Verification

- Behavior regression: 36 documents × 3.5MB = 126MB are read under one browse-scoped budget without creating a large test fixture; a second browse receives a new budget.
- Exact source reader regression: the caller's real budget is charged for the verified bytes and a too-small byte budget is rejected before consuming bytes.
- A first full affected-file run reported 62 passed but exited 1 during cleanup. The SQLite leak was fixed; rerun completed with **62 passed in 171.67 seconds, exit code 0**, and `CW-BASETEMP-CLEANUP removed=true`.
- Targeted Ruff: all checks passed. `git diff --check` passed. Current-status and boundary-matrix JSON both parse.
- Independent read-only review: **PASS — no production blocker**. It confirmed shared budget reaches resolver accounting and actual SHA/size verification; per-file CN PDF limits (16MB, 1,000 pages, 8M extracted characters) remain. The reviewer noted one non-blocking coverage gap: no direct CN-browser test exhausts `max_candidates` and asserts the final pathless envelope. Generic source-reader budget behavior and pathless CLI behavior are covered separately.

## Independent review file hashes

| File | SHA-256 |
|---|---|
| `src/company_wiki/source_catalog/public_canonical_browser.py` | `d3835b8548fce2d57eb7fee69497b63e41c2d108180357e3a9d4deb52d714d40` |
| `src/company_wiki/source_catalog/source_reader.py` | `c070edbfbcf458cda78e96af39ed820a5a3dbee30ddfb55aa3393370fc6d2cfe` |
| `tests/contract/test_public_canonical_browser.py` | `709cae27ff4d09d83cbe6cc782e450b2ba5511056dafe9994c2aa95cd6e8d087` |
| `tests/contract/test_source_reader_exact_history.py` | `3e20f62ae9806225cc71d5f6ffe8b420ac1aba6c9d33f8b5a6b2164d242bb306` |

The exact hashes identify the reviewed change independently of the subsequently amended local-only commit. Full GitHub CI for the root fix has not yet run; the preceding committed baseline's exact-head CI remains a separate receipt.
