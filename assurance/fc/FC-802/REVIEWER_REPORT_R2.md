# FC-802 Independent Review (r2) — reviewer-fc802-r2-independent

**Verdict: REJECTED** (2026-08-11, schema 2.0, evidence in `12_reviewer_receipt_r2.json`)

r2 re-review of the F1 remediation. Reviewed from the clean worktree `C:\Users\郑曾波\Projects\.fcap-review\fc-802-r2\company-wiki` (HEAD `74f8ec0`; receipt on wiki HEAD). filing-fetch main checkout (`7409ad8`) read-only; mutation replays ran in a temporary filing-fetch worktree, removed afterwards; company-wiki and filing-fetch main checkouts clean.

## 1. Receipt + triplets — PASS

- Revenue `aa12d9e7` == revenue-forecast HEAD == base == result (unchanged).
- Filing base `85731b2` / result `7409ad8`; `7409ad8` == filing-fetch HEAD; `git merge-base --is-ancestor 85731b20 7409ad8` -> ANCESTRY-OK (r2 sits on r1 `abde149`).
- Wiki base `d09243f` / result `ca4c0b1` == the `--mode` fix commit; `git merge-base --is-ancestor d09243f8 ca4c0b1` -> ANCESTRY-OK; wiki HEAD `74f8ec0` = `ca4c0b1` + receipt docs commit (touches only `11_implementer_receipt.json`).
- `plan_sha256` 158fc1e1... MATCH — frozen `task_plan.md` at revenue commit `2d64186` (campaign baseline constant, same as FC-801/705/604/704). Working-tree plan is 12e6ba80... (later acceptance docs appended) — frozen baseline seals per convention.
- `command_registry_sha256` 215b8077... MATCH — `compatibility/command_registry.json` on disk at revenue HEAD.

## 2. Diff scope — PASS

- filing r2 delta (`git show 7409ad8`) = `scripts/fetch_filing.py` (+15/-5) + `tests/test_fc802_gap_orchestration.py` (+21) only. Full span `85731b20..7409ad8` additionally carries the r1 content (`filing_contracts.py`, `IMPLEMENTATION_PLAN_FC802.md` — FC-801 F3 precedent). Zero unrelated changes.
- wiki r2 delta (`git show ca4c0b1`) = `src/company_wiki/source_catalog/cli.py` +8 only (ensure subparser `--mode`, choices `exact`/`latest_as_of`, FC-802 help text; mirrors resolve `cli.py:415` and close-gap `cli.py:485`). `_parser()` has one call site (`main`, cli.py:679).

## 3. F1 code fix — PASS (both halves present and correct)

- **wiki ca4c0b1**: ensure subparser gains `--mode` — the r1 parse-time rejection is gone.
- **filing 7409ad8**: `main()` (fetch_filing.py:952-961) passes a `{status:"gap",...}` dict through **unwrapped**; every other result keeps the `capture_ready` wrapper.

## 4. LIVE end-to-end proof — PASS (F1 closed at runtime)

Real CLI, real production catalog, `mode=latest_as_of`, `as_of_date=2026-08-11`, 紫金矿业 (CN, annual_report):

```
RETURNCODE: 0
{
  "status": "gap",
  "gap_plan": { "as_of_date": "2026-08-11", "gap_hash": "d5d086ef...",
    "missing": [], "future": [], "newer_revision": [],
    "provider_unavailable": true, "provider_reason": "...fiscal_year is required for CN discovery...",
    "reuse": [ ...existing 2025 annual report 601899, capture_ready: true... ] },
  "resolution": { ..., "resolution_envelope": { "policy_hash": "2d3d2ee8...", ... } }
}
```

Top-level `status=gap` with a complete `gap_plan` — **NOT** a `capture_ready` wrapper. The provider's metadata discovery was unavailable (adapter error) and the plan still returned — exactly the provider-fallback the design calls for. First attempts hit `database is locked` (production worker PID 15736 holds the catalog write lock — environment contention, cleared on retry); in every attempt `--mode` was **accepted by the parser** (r1's instant parse rejection never recurred). GBK mojibake in printed entity/titles = expected Windows artifact.

## 5. Fresh runs — PASS

- `python -m pytest tests/test_fc802_gap_orchestration.py tests/test_fetch_filing.py -q` -> **209 passed, 2 skipped, 54 subtests**.
- `python -m ruff check` on the 3 changed filing files -> **All checks passed**.
- Receipt validator -> `OK: 1 receipt(s) valid`, exit 0.

## 6. FINDING — F-r2-1 (BLOCKING): the F1 regression test is dead code; the passthrough mutation survives the entire suite

`test_main_passes_gap_through_unwrapped` (tests/test_fc802_gap_orchestration.py:300-323) is non-functional:

1. **Placement**: defined inside `if __name__ == "__main__":` **after** `unittest.main()` — pytest never collects it. `pytest tests/test_fc802_gap_orchestration.py::test_main_passes_gap_through_unwrapped` -> `no tests ran` / `not found`; collect-only shows `Fc802GapTests` unchanged at 5 methods (same as r1).
2. **Logic** (even if relocated): `main()` reads the request file at fetch_filing.py:931-932 **before** calling `resolve_filing` (line 943). The test's `--request-file missing.json` raises FileNotFoundError -> `request_error`, rc=2 — the mocked gap is never consulted. Reproduced empirically: payload `status == "request_error"`. The test's own comment ("resolve_filing is mocked so no file is read") is false.
3. **Mutation spot-check FAILED to kill**: disabling the gap passthrough (`if False and ... handle.get("status") == "gap"`) in a temporary worktree at 7409ad8 leaves the **entire** suite green — focused 209 passed; full suite **261 passed, 8 skipped, 54 subtests**. The F1 passthrough has zero regression protection in the sealed tree.
4. **Receipt accuracy**: "7 passed (6 + F1 main() passthrough regression)" is not reproducible — the focused command yields the pre-existing counts with no regression test collected.

The F1 **code** fix is correct and live-proven (Section 4); only the test deliverable is broken. Remediation is small: relocate the test into `Fc802GapTests` and fix its logic (feed a valid request via stdin or a temp request file so the mocked gap flows through `main()`'s output branch; assert top-level `status=gap`, `gap_plan` passthrough, and absence of `capture_ready`), then re-seal. The verified code (filing 7409ad8 main() + wiki ca4c0b1 ensure `--mode`) can stand unchanged.

## 7. Side effects

Zero downloads, zero file writes outside `12_reviewer_receipt_r2.json` + `REVIEWER_REPORT_R2.md`, zero reviewer-side catalog mutations. Mutation worktree removed; both main checkouts clean.
