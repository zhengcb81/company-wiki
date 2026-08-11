# FC-703 Independent Review — REJECTED

- Reviewer: reviewer-fc703-independent (independent of the implementer; fresh evidence from a clean worktree)
- Reviewed at: 2026-08-11
- Base wiki: 4854380b53166292184bda41dd913ffe6d496885 → Result wiki: 41b060ddb89d8913b8fdb4f1f3f7b03ebc37da1b (receipt commit 545a986 on top, adds only the receipt)
- Revenue 0cf30c16 / filing 6274be21 unchanged (verified at HEAD, both clean)
- Verdict: **REJECTED** — the implementer receipt's central mutation claim is not reproducible, and the committed tests do not pin the behavior FC-703 exists to pin.

## What passed (verified with fresh evidence)

1. **Sealing hashes**: plan_sha256 `158fc1e1...4c78a` recomputed from task_plan.md at frozen commit 3e805a8 — matches. command_registry_sha256 `215b8077...b089` matches the working tree, no drift.
2. **Diff scope**: `git diff --stat 4854380 41b060d` = exactly 2 files, 256 insertions (test 150 + replay tool 106), zero production code; receipt commit adds only the receipt.
3. **Fresh runs** (clean worktree, `python -B`): FC-703 focused 5 passed; Phase-7 cluster (fc703+fc702+fc701+fc604) 23 passed; ruff clean.
4. **PERF baseline genuine**: `tools/ex07_perf_replay.py` against the live catalog reproduced the receipt — catalog_documents=23521, all REUSED_EXACT, side_effects all zero, p50 44.2/43.5/13.7/14.1ms vs receipt 42.4/42.1/14.2/14.1ms (jitter). The tool's own code path is read-only (resolver has zero write statements; store read path mode=ro + query_only; count via mode=ro URI).
5. **Validator**: `receipt_validator.py --receipt ...FC-703/11_implementer_receipt.json` → `OK: 1 receipt(s) valid`.
6. **Production behavior is correct as committed**: service.py `query_filing_candidates` genuinely carries `WHERE d.document_kind = ? AND d.source_status IN (...) AND (json_extract(...fiscal_year...))` (source read + captured-SQL probe).

## Why it is REJECTED (critical finding)

**The tests do not pin the document_kind/source_status SQL pushdown — the core deliverable of this test-only FC.**

Mutation replay in the clean worktree (live code, `python -B`, pycache-free):

| Mutation | Result | Mechanism |
|---|---|---|
| M1: drop `AND d.document_kind = ?` WHERE clause + param (the natural 'remove the pushdown' mutation) | **5 passed — NOT KILLED** | spy test's substring assertions (`"document_kind" in docs_sql`, `"source_status" in docs_sql`) are satisfied by the SELECT projection columns (`d.document_kind`, `d.source_status`); behavioral tests survive via the resolver's Python-side gates (document_kind_mismatch / rejected_source_status) |
| M2: kind/status removed from projection AND WHERE (full pushdown removal) | 5 failed — killed, but by `IndexError: No item with that key` (row-mapping crash), NOT the WHERE assertions | pins only that the query SELECTs the columns |
| M3: fiscal_clause + params removed | 1 failed — clean assertion kill (`assert 'fiscal_year' in ...`) | fiscal_year token appears only in the WHERE — the sole genuinely pinned predicate |

Consequence: the implementer receipt's claim "WHERE-clause removal mutations killed by the spy test (OPS-03)" is **not reproducible**, and OPS-03's "no Python full-table scan" property is **unpinned**: a regression moving kind/status filtering into Python would pass the entire committed FC-703 suite (verified — all 5 tests pass with the kind WHERE clause gone).

## Secondary findings

- **Low**: `tools/ex07_perf_replay.py` does not fail closed without a catalog — in a catalog-less worktree it creates an empty `.source_catalog` DB (a write) and exits 0 with a 0-document baseline. The receipt's PERF numbers reproduce only from the main checkout (verified there). Artifacts from my worktree test were removed; worktree clean.
- **Informational**: an ambient process continuously modifies the main checkout's catalog.sqlite3 (4 distinct hashes during review with no tool running; worker_state/runs jsonl rotating) — skews latency baselines (observed 239ms p95 outlier).
- **Informational**: fcap branch has no remote counterpart (same as FC-701/702); full suite not rerun per instructions — implementer's 3 failures are the known PORT-01/FC-1205 + Windows worker-bootstrap flakes, consistent with prior FCs.

## Recovery path (cheap, no production change)

1. Strengthen `test_fc703_query_uses_where_clauses` to assert the kind/status predicates inside the WHERE region (e.g., regex on the SQL after `WHERE` for `document_kind\s*=\s*\?` and `source_status\s*IN`).
2. Re-run M1 (must fail) + focused suite + ruff.
3. Re-seal with a new result triplet and updated implementer receipt; re-review required per protocol (all affected commands rerun, old reviewer receipt superseded).
