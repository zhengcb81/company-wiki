# FC-703 Review Report — Round 3 (independent reviewer)

- **FC**: FC-703 (SQL pushdown + performance pins, OPS-03/EX-07/PERF)
- **Reviewer**: reviewer-fc703-r3-independent
- **Round**: r3 (receipt-only; code verdict carried from r2, which was GOOD)
- **Verdict**: ACCEPTED
- **Date**: 2026-08-11
- **Implementer receipt reviewed**: `assurance/fc/FC-703/11_implementer_receipt.json` at wiki commit d546558 (sha256 `b7f2329e265ff27bf44e653daa80555fccb85647a57db3ceb44d4ff89c51b309`)

## Context

r1 REJECTED (spy test satisfied by the SELECT projection; M1 survived). r2 code fix was
VERIFIED GOOD (M1/M3 both killed by WHERE-region assertions; fail-closed replay works), but
the r2 receipt was REJECTED at the receipt level on two defects:

1. **Critical** — `commands[4].exit_code = 2` violated schema 2.0 (receipt_validator.py
   requires `exit_code 0` for every recorded command) → machine gate failed.
2. **Low** — mutation.details claimed "ALL 5 tests FAIL" on M1; observed is 1 failed / 4
   passed (the 4 behavioral tests survive via the resolver's Python-side gates).

r3 is the receipt-fix round. The code is byte-identical to r2 (result wiki `ae91836`).

## What was verified in r3

### 1. Receipt fields (fresh evidence)

| Field | Expected | Found |
|---|---|---|
| plan_sha256 | `158fc1e1…4c78a` | MATCH — recomputed: task_plan.md at revenue-forecast 2d64186 (frozen plan); on-disk copy was later refreshed by d662c82 (4-line triplet/status-header change), consistent with the sealed value across all prior FC receipts |
| command_registry_sha256 | `215b8077…06b089` | MATCH — recomputed: compatibility/command_registry.json (tracked, unmodified); same pre-sealed value as FC-505 + compatibility/current.json |
| base_triplet | revenue `0cf30c16`, filing `6274be21`, wiki `4854380` | MATCH — revenue = revenue-forecast HEAD, filing = filing-fetch HEAD, wiki commit exists |
| result_triplet | revenue `0cf30c16`, filing `6274be21`, wiki `ae91836` | MATCH — wiki commit exists; `git merge-base --is-ancestor 4854380 ae91836` → ANCESTRY-OK |
| commands[4] | exit_code 0, non-zero semantics in text | FIXED — exit_code 0; result text preserves observed exit-2 fail-closed semantics ("printed 'FC-703 replay FAILED CLOSED'", "tool returned exit 2 … recorded as 0 here per schema 2.0") |
| mutation.details | accurate M1 wording | FIXED — now states the spy test FAILS with 'kind predicate not in WHERE region' and the other 4 tests survive via Python-side gates; no longer overstates "ALL 5 tests FAIL" |

### 2. Machine gate (the r2 blocker)

From revenue-forecast:

```
python tools/receipt_validator.py --receipt C:/Users/郑曾波/Projects/company-wiki/assurance/fc/FC-703/11_implementer_receipt.json
→ OK: 1 receipt(s) valid   (exit 0)
```

### 3. Spot M1 re-verify (the property FC-703 exists to pin)

In the clean r3 worktree (HEAD d546558): dropped `AND d.document_kind = ?` + its bound
parameter from `query_filing_candidates`, cleared `__pycache__` under src/ and tests/,
`python -B`:

- `test_fc703_query_uses_where_clauses` FAILS: `AssertionError: kind predicate not in
  WHERE region: WHERE d.source_status IN (?)…` — the exact r2-prescribed kill
- 1 failed / 4 passed (behavioral tests survive via Python-side gates — matches the
  corrected receipt wording)

Restored with `git checkout -- .`; focused suite re-run: **5 passed**. `ruff check
tests/contract/test_resolver_sql_perf_fc703.py tools/ex07_perf_replay.py` → clean.
Worktree left clean.

### 4. Not re-run in r3 (verified in r2, no code change)

Phase-7 cluster (23 passed), live replay + fail-closed replay, full suite (not rerun per
instructions; the 3 pre-existing failures were proven pre-existing at 4854380 in r2).

## Reviewer receipt

- `assurance/fc/FC-703/12_reviewer_receipt_r3.json` — schema 2.0, status `accepted`,
  reviewer `reviewer-fc703-r3-independent`, reviewed_at `2026-08-11`.
- Self-hash (documented one-step lag, same convention as the r2 reviewer receipt):
  recorded `c900db24e5c11b980f04449ca3ab3daee205f3ba8a19abfa19ae060c97660320` = hash of
  the file as written before the hash field was filled; the final on-disk file hashes to
  `0a7a8c6cca0b87e8168cf55bc1b5cfcfee6042cfce5905c3c7251f97aecab385`.

## Notes for closure

- The r2 reviewer receipts (`12_reviewer_receipt_r2.json`, `REVIEWER_REPORT_R2.md`) are
  still **untracked** in the main wiki checkout (`git status` shows `??`); the implementer
  merges them at closure together with this r3 receipt. An unrelated local modification to
  `llm_cost_log.csv` also exists.
- Informational findings carried from r1/r2 (ambient catalog writer, no remote branch,
  full suite not rerun) do not affect the verdict.

## Verdict

**ACCEPTED.** The two r2 receipt defects are fixed, the receipt passes the machine gate,
the record is honest (wording matches observed behavior), and the code was verified good
in r2 with the M1 kill spot-re-confirmed in r3.
