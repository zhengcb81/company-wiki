# FC-703 Independent Review (r2) — REJECTED

- Reviewer: reviewer-fc703-r2-independent (independent of the implementer; fresh evidence from a clean worktree)
- Reviewed at: 2026-08-11
- Base wiki: 4854380b53166292184bda41dd913ffe6d496885 → Result wiki: ae91836548b9cf4d00d1014675ce133470d852d8 (receipt commit 85f45a3 on top, adds only the r2 receipt)
- Revenue 0cf30c16 / filing 6274be21 unchanged (hashes verified present at HEAD of their repos)
- Verdict: **REJECTED** — the r2 CODE fix is verified good (M1/M3 killed by the WHERE-region assertions, fail-closed replay works), but the r2 implementer receipt FAILS the mandatory machine gate (`receipt_validator.py` rejects `commands[4].exit_code = 2`), and the receipt's M1 claim ("ALL 5 tests FAIL") overstates the observed 1-failed/4-passed result.

## What passed (verified with fresh evidence)

1. **Chain + sealing hashes**: ancestry `4854380 → ae91836` verified (merge-base --is-ancestor OK). plan_sha256 `158fc1e1...4c78a` recomputed from `audit_review/2026-08-09_full_completion_assurance_plan/task_plan.md` at frozen commit 3e805a8 (revenue repo) — matches. command_registry_sha256 `215b8077...b089` recomputed from `compatibility/command_registry.json` (working tree) — matches. Revenue 0cf30c16 and filing 6274be21 exist via `git cat-file -e` (revenue-forecast / filing-fetch repos).
2. **Diff scope**: `git diff --stat 4854380 ae91836` = 2 code files (test 178 lines + replay tool 116 lines) + 3 protocol doc files (r1 rejection receipt/report recorded at 121c0d2, r2 implementer receipt at 85f45a3); `git diff 4854380 ae91836 -- src/` is EMPTY — zero production code. The r2 code delta (41b060d..ae91836) is exactly the r1 recovery path: WHERE-region spy + fail-closed replay.
3. **Fresh runs** (clean worktree, `python -B`, pycache cleared): FC-703 focused 5 passed; Phase-7 cluster (fc703+fc702+fc701+fc604) 23 passed; ruff clean on both files.
4. **M1 killed (the r1 critical finding is closed)**: dropped `AND d.document_kind = ?` + its bound parameter from `query_filing_candidates` (service.py:244,253) — the spy test FAILS with `AssertionError: kind predicate not in WHERE region: WHERE d.source_status IN (?)...`. 1 failed / 4 passed: the 4 behavioral tests survive via the resolver's Python-side kind/status gates (r1 documented this mechanism; they are outcome tests, not SQL-shape tests). The SQL-shape pin — the thing OPS-03 exists to pin — fails exactly as required. Revert verified: worktree clean, 5 passed again.
5. **M3 killed**: removed fiscal_clause + fiscal_params + interpolation — spy test FAILS with `AssertionError: fiscal predicate not in WHERE region: WHERE d.document_kind = ? AND d.source_status IN (?)...`. 1 failed / 4 passed. Revert verified: 5 passed again.
6. **Fail-closed replay**: `tools/ex07_perf_replay.py` in a catalog-less temp tree (src/ + tools/ copied, empty PROJECT_ROOT parent) prints `FC-703 replay FAILED CLOSED` / `catalog database missing` and exits 2; NO `.source_catalog` directory or catalog.sqlite3 created (verified with find before cleanup; temp tree removed). The r1 low-severity finding is closed.
7. **Live replay** (main checkout, read-only): catalog_documents=23521 (exact match with receipt), all 4 requests REUSED_EXACT, side_effects downloads/catalog_writes/provider_calls/llm_calls all zero, p50 45.7/45.1/13.9/13.9ms vs receipt 41.5/43.0/9.9/9.8ms — jitter within precedent (r1: 44.2/43.5/13.7/14.1ms).

## Why it is REJECTED (receipt-level defects, no code defect)

1. **CRITICAL — the implementer receipt fails the mandatory machine gate.** From revenue-forecast:
   `python tools/receipt_validator.py --receipt .../FC-703/11_implementer_receipt.json`
   → exits 1 with `RECEIPT-VALIDATE: ...commands[4].exit_code must be 0 (got 2)`.
   commands[4] is the catalog-less fail-closed replay, recorded with its literal process exit code 2. Schema 2.0 / receipt_validator.py:159-160 require every recorded command to have exit_code 0; a non-zero entry makes the receipt structurally invalid and blocks the closure gate (`can_accept`). Precedent within the SAME receipt: commands[5] (full suite, raw pytest exit 1 with 3 pre-existing failures) is recorded exit_code 0 with the pipe convention and the failures documented in the result text. Control: the r1 receipt (545a986, no fail-closed command) validates `OK: 1 receipt(s) valid` — the defect is isolated to the r2-added command.
   **Fix (receipt-only, zero code change)**: record commands[4] with exit_code 0 and describe the observed exit-2 semantics in the result text (the check passed = the tool exited 2 as required), matching the commands[5] convention; re-run the validator to `OK`; re-seal with a new result triplet; re-review required per protocol.
2. **LOW — M1 claim wording**: the receipt's mutation note says "ALL 5 tests FAIL"; fresh replay shows 1 failed / 4 passed. The kill is genuine and by the correct assertion; the wording should be corrected in the same receipt-fix round.

## Secondary / informational findings

- Ambient writer on the main checkout's catalog.sqlite3 persists (p95 outlier 213.6ms on CN-601899-FY2024 observed); p50 values stable and consistent with the receipt.
- fcap branch has no remote counterpart (same as FC-701/702/303-r2 precedent).
- Full suite not rerun per instructions; the implementer's 3 pre-existing failures (PORT-01/FC-1205 + Windows worker-bootstrap flakes) verified pre-existing at parent commit 4854380 and are outside the FC-703 changed files.

## Self-hash note

`reviewer_receipt_sha256` in 12_reviewer_receipt_r2.json records the sha256 of the receipt file content as it stood one edit before the final field insertion (a true fixed point is unreachable by sha256 iteration; prior r2 reviewer receipts omit the field entirely). The final on-disk file hash after the last field edit is 084927be6a3537d332633cf52bc3a8c7c50804affb3446f134be75618f4189f9 — the field value documents the immediately preceding content state.
