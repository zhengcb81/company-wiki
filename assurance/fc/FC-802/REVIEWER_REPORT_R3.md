# FC-802 Independent Review (r3) — reviewer-fc802-r3-independent

**Verdict: ACCEPTED** (2026-08-11, schema 2.0, evidence in `12_reviewer_receipt_r3.json`)

r3 re-review of the F-r2-1 remediation (relocate + repair the F1 regression test). Reviewed from the clean worktree `C:\Users\郑曾波\Projects\.fcap-review\fc-802-r3\company-wiki` (HEAD `c6b6027`). filing-fetch main checkout (`01cd018`) read-only; the mutation replay ran in a temporary filing-fetch worktree at `01cd018`, removed afterwards. filing-fetch and company-wiki main checkouts clean throughout.

## 1. Receipt + triplets — PASS

- Revenue `aa12d9e7` == revenue-forecast HEAD == base == result (unchanged).
- Filing base `85731b2` / result `01cd018`; `01cd018` == filing-fetch HEAD; parent == `7409ad8` (r2) — ANCESTRY-OK; base is an ancestor.
- Wiki result `ca4c0b1` == the `--mode` fix commit (no wiki code delta in r3); wiki HEAD `c6b6027` = `ca4c0b1` + r3 receipt docs commit (touches only `assurance/fc/FC-802/`).
- `plan_sha256` 158fc1e1... MATCH — recomputed from frozen `task_plan.md` at revenue commit `2d64186`.
- `command_registry_sha256` 215b8077... MATCH — on-disk at revenue HEAD `aa12d9e7` (repo clean).
- Diff scope (`git diff --stat 7409ad8 01cd018`): **ONLY** `tests/test_fc802_gap_orchestration.py` (+18/-9). Zero unrelated changes.

## 2. Relocated regression test — PASS (F-r2-1 closed)

`test_main_passes_gap_through_unwrapped` (tests/test_fc802_gap_orchestration.py:299-327) is now a real method **inside `Fc802GapTests`**, before the `__main__` guard (line 330). It:

1. writes a **valid request file** (`schema_version` 1.2, AMD / annual_report / `latest_as_of`) into the `setUp` temp dir (`mkdtemp` — no repo pollution),
2. patches `fetch_filing.resolve_filing` to return the structured gap,
3. invokes `fetch_filing.main(["--config", "x", "--request-file", <file>])`,
4. asserts `rc == 0`, `payload["status"] == "gap"`, `gap_plan.gap_hash` passthrough, and `capture_ready` absent.

The r2 logic defect is fixed: `main()` reads the request file (fetch_filing.py:931-932) **before** calling `resolve_filing` (943) — the file now exists, so the mocked gap reaches the output branch (952-961).

## 3. Fresh runs — PASS

- `pytest tests/test_fc802_gap_orchestration.py -q` -> **109 collected, 108 passed, 1 skipped** (the file also collects the ~102 `FilingFetchTests` via import, pytest 9 default `*Tests` collection). Collect-only **lists** `Fc802GapTests::test_main_passes_gap_through_unwrapped`; node-id run -> **1 passed**.
- `pytest tests/test_fc802_gap_orchestration.py::Fc802GapTests -q` -> **6 passed**.
- Full suite `pytest tests/ -q` -> **262 passed, 8 skipped, 54 subtests** (47.6s) — one more than the r2 261, exactly the now-collected regression test.
- `ruff check tests/test_fc802_gap_orchestration.py scripts/fetch_filing.py` -> **All checks passed**.
- Receipt validator -> `OK: 1 receipt(s) valid`, exit 0.

## 4. Mutation replay (the r2 blocker) — PASS: the test now KILLS the mutation

In a temporary worktree at `01cd018`, removed the gap-passthrough branch (`if isinstance(handle, dict) and handle.get("status") == "gap":`) leaving an always-wrap output. Result:

```
Fc802GapTests -> 1 failed, 5 passed
tests\test_fc802_gap_orchestration.py:325: AssertionError
```

The regression test **FAILS (not errors)** — payload status is `capture_ready`, expected `gap`. The kill is **precise**: the other 5 gap tests stay green, so the test targets `main()`'s output branch specifically. This is exactly the protection that was missing at r2. Worktree removed; filing-fetch main checkout clean and byte-identical.

## 5. Observation (non-blocking)

The implementer receipt's command counts are stale/imprecise but non-hiding: it claims "7 passed" for the focused command and "261 passed" for the full suite; this checkout yields 109 collected / 108+1 for the file (the extra collection comes from `FilingFetchTests` imported into the module — a pytest 9 `*Tests` default) and **262** for the full suite (r3 adds the now-collected test). The substantive claims — regression test collected, all green, ruff clean — are all verified above.

## 6. Side effects

Zero downloads, zero catalog mutations, zero writes outside `12_reviewer_receipt_r3.json` + `REVIEWER_REPORT_R3.md`. Mutation worktree removed; both main checkouts clean.
