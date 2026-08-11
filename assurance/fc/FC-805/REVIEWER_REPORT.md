# FC-805 Independent Review — ACCEPTED

- **Reviewer**: reviewer-fc805-independent (did NOT implement FC-805)
- **Protocol**: honest-implementer, FCAP-2026-08-09-r2 (Phase 8: FC-805 real-provider isolated E2E)
- **Reviewed**: 2026-08-11
- **Verdict**: **ACCEPTED**
- **Receipt**: `assurance/fc/FC-805/12_reviewer_receipt.json`

## Claim sealed

Base 170ab3e (revenue, unchanged) / 065976e (filing) / cb04bf3 (wiki)
→ Result filing `81d9cd98c6c6a680c859b20917fd9d47db707564` / wiki `44d8098af8ff6d00216025f83e3630e72e2dd3cd`.

Scope: filing-fetch adds `tests/test_fc805_real_download_t3.py` (+186) and updates
`tests/test_fc803_minimal_download.py` (+6/-2, LT-07 year-scoped fixture); company-wiki adds the
discovery-year derivation in `src/company_wiki/source_catalog/acquisition.py` (+27/-1).
No unrelated changes in either diff. Both bases are ancestors of their results (ANCESTRY-OK).

## Evidence

1. **LIVE T3 CN reproduced** (61.17s): real cninfo download of 紫金矿业's latest annual report
   into an isolated temp wiki; structured gap (provider metadata hash = gap_plan.gap_hash) →
   authorized close-gap (snapshot_sha256 verified byte-for-byte against the downloaded file) →
   second request reports gap closed (`missing == []`), zero new files, journal exactly one
   `downloaded_new`. The implementer's sealed evidence is reproducible.
2. **Mutation M1 KILLED** (3.42s, zero bytes fetched): with the discovery-year derivation removed,
   the real CN T3 test fails — `provider_unavailable: true, missing: []`, provider reason
   `"fiscal_year is required for CN discovery"` (ValueError). The hint is load-bearing and the
   gap plan fails closed (LT-05) against the live provider. Reverted byte-identically (sealed blob
   sha ead30424… == main checkout); post-revert live CN T3 passed again (57.72s).
3. **AUTH-GATE verified**: without `FC805_REAL_DOWNLOAD`, the T3 suite is 3 skipped in 0.07s —
   blocked, never counted as pass (skipUnless at import, per scenario_matrix T3 rules).
4. **Regressions green**: `test_fc803_minimal_download.py + test_fc802_gap_orchestration.py`
   → 113 passed, 1 skipped, 27 subtests; wiki contracts `test_close_gap_fc801 + test_close_gap_concurrency_fc804`
   → 12 passed; `ruff check` on acquisition.py → clean.
5. **Sealing hashes match**: plan_sha256 `158fc1e1…` (recomputed from git show 2d64186), 
   command_registry `215b8077…` (on-disk at revenue-forecast HEAD 170ab3e).
6. **Code read**: the fix is scoped to the metadata-only `_gap_plan_result` discovery path,
   guarded by `fiscal_year is None`, graceful on unparsable dates; the download path consumes
   gap-plan candidates, not the hint; original `request_id` preserved in the gap plan. The CN
   adapter double-filters on fiscal_year (API client + candidate re-validation), which explains
   both the pre-fix defect and the 3.42s mutation kill.
7. **Validator gate**: `receipt_validator.py` → `OK: 1 receipt(s) valid` (exit 0).
8. **Side effects**: only real-provider downloads were the two reviewer T3 runs into temp wikis
   (auto-torn-down); zero writes to production catalog/roots; all main checkouts byte-untouched.

## Findings

None. No unresolved findings.

## Notes

- Review worktree file is the CRLF working-tree variant (Windows autocrlf) vs the LF main
  checkout; git diff HEAD empty throughout — environment artifact, no content difference.
- Full suites not rerun per instructions (implementer: filing 267 passed / 11 skipped; wiki
  2198 passed / 2 PORT-01 pre-existing failures).
