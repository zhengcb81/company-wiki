# FC-804 Independent Review Report

- Reviewer: reviewer-fc804-independent (did NOT implement FC-804)
- Review date: 2026-08-11
- Verdict: **ACCEPTED**
- Evidence receipt: `assurance/fc/FC-804/12_reviewer_receipt.json` (self-hash `00581f6b...`)

## Scope

FC-804 (concurrency, retry and recovery — DL-08 single-flight, OPS-02 bounded retry, DL-09
idempotent recovery) per the FCAP-2026-08-09-r2 honest-implementer protocol. Sealed triplet:
revenue `f7eef71` (unchanged) / filing `065976e` (unchanged) / wiki `f99e0fa` -> `d96e672`.
The review ran fresh in the clean review worktree; revenue-forecast and filing-fetch were
read-only.

## 1. Receipt + triplets

- Implementer receipt `11_implementer_receipt.json` present and valid; base/result triplets
  match the sealed values and repo HEADs: revenue-forecast HEAD == base == result (`f7eef71`),
  filing-fetch HEAD == `065976e`.
- `plan_sha256 158fc1e1...` recomputed from `task_plan.md` at revenue 2d64186 (the frozen
  FCAP r2 plan — same source FC-803's reviewer used): MATCH.
- `command_registry_sha256 215b8077...` recomputed on disk (`compatibility/command_registry.json`): MATCH.
- Ancestry: base wiki `f99e0fa` is an ancestor of result `d96e672` (WIKI-ANCESTRY-OK via
  `git merge-base --is-ancestor`). Wiki HEAD 7d9f40c = `d96e672` + receipt-only commit
  (only `assurance/fc/FC-804/11_implementer_receipt.json`).

## 2. Diff scope

- `git diff --stat f99e0fa d96e672` = exactly 3 files:
  `IMPLEMENTATION_PLAN_FC804.md` (+39), `src/company_wiki/source_catalog/close_gap.py`
  (+130/-13), `tests/contract/test_close_gap_concurrency_fc804.py` (+314). Zero unrelated changes.

## 3. Code read

- **DL-08 single-flight**: step 3 acquires a per-transaction file lock
  (`catalog_dir/close_gap_locks/<txn-sha256-suffix>.lock` via the existing
  `lock._acquisition_mutex` — msvcrt/fcntl byte-range lock with 0.05s poll), bounded by
  `_lock_timeout_seconds()` = coordinator timeout + 30s grace (default 600s). INSIDE the lock
  the gap is re-checked (metadata-only `latest_as_of` resolve): gap closed -> complete as
  reused with fetch=0 (`gap_closed_by_concurrent`); hash drift -> reject `stale_gap_hash`;
  otherwise fetch + commit. `CatalogOperationLockedError` -> `failed` with
  `close_gap_lock_timeout` reason (bounded failure, never a hang).
- **OPS-02 bounded retry**: staging loop retries only `AdapterProcessError` with
  `retryable=True`, max 3 attempts, backoff 1s/2s; non-retryable fails on attempt 1; DL-02
  `download not authorized` short-circuits to a rejection BEFORE retry classification on every
  attempt; final failure cleans the STAGING request's per-candidate staging dir and journals
  `failed`. `_reject_result` / `_is_retryable_staging_error` helpers as claimed.
- **DL-09 idempotency**: canonical commit is content-hash-deduped (`import_staged`); rerun
  reuses with fetch=0; `_finalize` only reports `completed` when the re-resolve reuses.

## 4. Fresh runs (worktree, `python -B`)

- `pytest tests/contract/test_close_gap_concurrency_fc804.py -q` -> **5 passed** (7.00s)
- `pytest tests/contract/test_close_gap_fc801.py -q` -> **7 passed** (1.11s, regression)
- `ruff check close_gap.py test_close_gap_concurrency_fc804.py` -> **All checks passed**
- Full suite not re-run per campaign convention (implementer: 2198 passed / 2 pre-existing
  PORT-01 Windows GBK).

## 5. Mutation replay (adversarial, both killed)

- **M1** (lock bypassed) -> `test_cg_c1_single_flight_one_fetch` FAILED with exactly the
  claimed signature: `AssertionError: single-flight violated: 2 fetches` (assert 2 == 1).
  Reverted; `git diff HEAD` empty.
- **M2** (`retryable = False`) -> `test_cg_c2_retryable_failures_retried` FAILED:
  `assert 'failed' == 'completed'`. Reverted; post-revert 12-test rerun green (7.38s).

## 6. Additional fresh evidence (reviewer probes, scratch only)

- **Lock timeout under real contention**: lock held in thread A (1.5s); thread B contended
  with `timeout_seconds=0.3` -> `CatalogOperationLockedError` after ~0.6s. Bounded, no hang.
- **In-lock re-check is the loser's path**: journal for a fresh CG-C1-style run records the
  loser as `reused_before_download / gap_closed_by_concurrent` (not the pre-lock
  `gap_already_closed` shortcut), fetch=1 total, one document committed.

## 7. Validator

- `python tools/receipt_validator.py --receipt .../FC-804/11_implementer_receipt.json`
  -> **OK: 1 receipt(s) valid** (exit 0).

## 8. Observations (non-blocking)

- CG-C4 as shipped is sequential — it never creates lock contention and only re-tests rerun
  dedupe; the bounded-timeout behavior it names was independently proven by the reviewer's
  contention probe. A contention-based CG-C4 follow-up is recommended.
- CG-C1 uses two threads rather than the plan's two subprocesses; the msvcrt byte-range lock
  serializes same-process threads (fetch==1 proves it) and is the same primitive used
  cross-process, so the single-flight property holds at the file-lock level.
- `_is_retryable_staging_error`'s docstring (and IMPLEMENTATION_PLAN_FC804.md) say
  `provider_unavailable` is retryable, but the code returns False for such RuntimeErrors.
  No code path raises that RuntimeError today (`provider_unavailable` is a GapPlan status
  field, not an exception), so the branch is dead code with a stale docstring — no live-path
  impact; the receipt's OPS-02 claim (AdapterProcessError.retryable only) is accurate.
- DL-02 authorization rejection still short-circuits before retries (ordering preserved from
  FC-801); staging cleanup on final failure uses the per-candidate STAGING request id
  (FC-803 REAL-FIX-3 preserved).

## 9. Findings

None. No blocking or non-blocking findings outstanding.

Verdict: **ACCEPTED** — all claims verified with fresh evidence; both mandated mutations
killed and reverted; receipt validator gate passes.
