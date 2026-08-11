# FC-801 Independent Review — reviewer-fc801-independent

**Verdict: ACCEPTED** (2026-08-11, schema 2.0, evidence in `12_reviewer_receipt.json`)

Reviewed in the clean worktree `C:\Users\郑曾波\Projects\.fcap-review\fc-801\company-wiki` (HEAD `bf502af`, base wiki `7e8c35f` -> sealed wiki `4a444ae` -> receipt commit `bf502af`).

## 1. Receipt + triplets — PASS

- `git merge-base --is-ancestor 7e8c35f 4a444ae` -> ANCESTRY-OK.
- Base hashes exist in their own repos: revenue `d362a4` == revenue-forecast HEAD; filing `85731b2` == filing-fetch HEAD; wiki `7e8c35f`/`4a444ae`/`bf502af` in company-wiki.
- Result triplet: revenue/filing unchanged; wiki `4a444ae`. Receipt commit `bf502af` touches only `11_implementer_receipt.json`.
- `plan_sha256` 158fc1e1... recomputed MATCH — frozen `task_plan.md` at revenue commit 2d64186 (campaign baseline; same constant as FC-604/704/705 receipts).
- `command_registry_sha256` 215b8077... recomputed MATCH — `compatibility/command_registry.json` at revenue HEAD.

## 2. Diff scope — PASS

Sealed commit diff = 5 source/test files (close_gap.py +323, authorization.py +26/-8, cli.py +75, test_close_gap_fc801.py +335, test_source_catalog_download_authorization.py +33) + `IMPLEMENTATION_PLAN_FC801.md` (process artifact, same convention as FC-704/FC-705 sealed commits; content faithfully matches the receipt's scenarios). Zero unrelated changes.

## 3. Code read — key properties verified

- **Fixed step order** (close_gap.py `execute`): policy binding (DL-03, fail-closed `no_runtime_policy` / `stale_policy_hash`) -> gap revalidation (`latest_as_of` metadata only; `stale_gap_hash`; gap-already-closed -> reused) -> authorize + fetch staging (DL-02; coordinator validates the receipt before any fetch) -> validate (DL-07 inside `coordinator.resolve_or_stage._validate_receipt`: bytes/size/SHA-256/magic/http) -> canonical commit (`import_staged`, content_sha256 idempotent) -> journal record -> re-resolve with LT-10 finalize guard -> FC-704 envelope.
- **DL-02 vs DL-07 distinction**: coordinator raises `AcquisitionError("download not authorized: ...")` for authorization denials -> `_reject` (fetch=0, no journal); any other staging/fetch exception -> `_fail` (journaled `failed` + txn id) plus auditable staging cleanup.
- **Staging cleanup key**: `_cleanup_staging(request.request_id)` -> `staging_root / request_id.rsplit(":", 1)[-1]` — matches the coordinator's own staging-dir naming (acquisition.py line 425).
- **LT-10 guard**: `_finalize` claims `completed` ONLY on REUSED_EXACT/REUSED_EQUIVALENT re-resolve; otherwise `failed` with `re_resolve_did_not_reuse:<status>`, envelope=None. Empirically load-bearing (M4 below).
- **policy_hash binding**: `DownloadAuthorization.policy_hash` is required (ValueError when empty/len!=64) and participates in the deterministic receipt digest (CG-08).
- **request_id reconciliation**: journal keyed by binding.request_id; FC-704 envelope reconciles by resolution.request_id; CG-03/04/06/07 pin the equality contract. (See F1.)

## 4. Fresh runs (python -B, pycache cleared)

- Focused: `test_close_gap_fc801.py` + `test_source_catalog_download_authorization.py` -> **20 passed** (7 CG + 13 auth).
- Phase-8 cluster (adds test_resolution_envelope_fc704, test_legacy_observation, test_resolver_sql_perf_fc703) -> **50 passed**.
- `ruff check` on the 5 changed files -> clean.
- Full 7-min suite not rerun (per protocol); implementer's 2193 passed / 2 pre-existing PORT-01 recorded.

## 5. Mutation replay (adversarial, independent of the implementer's 4)

- **M1** (disable `stale_policy_hash` check) -> `test_cg01` FAILS. Reverted.
- **M4** (bypass `writer.import_staged`, fabricate `imported_new`) -> `test_cg07` FAILS with status `- completed / + failed` — the LT-10 finalize guard catches the commit bypass (document never resolves). Reverted byte-identical; 20 green again; worktree git diff empty.

## 6. Validator

`python tools/receipt_validator.py --receipt <company-wiki>/assurance/fc/FC-801/11_implementer_receipt.json` -> `OK: 1 receipt(s) valid`, exit 0. (The reviewer receipt is a distinct document type per the FC-705 r2 precedent and is not a validator input.)

## 7. Findings (all informational, no action required)

- F1: `execute()` does not runtime-enforce binding.request_id == request.request_id; a divergent id would silently degrade the envelope (structural outcome, download_events=0) while the txn still reports completed. Pinned by tests; CLI reads request_id from the binding file; plan does not mandate the check. Suggested hardening only.
- F2: cli `--mode` flag is accepted but inert (transaction hard-codes latest_as_of/exact step modes).
- F3: IMPLEMENTATION_PLAN_FC801.md ships in the sealed commit outside the receipt's file lists — identical to FC-704/FC-705 precedent.

## 8. Side effects

Zero downloads, zero catalog mutations, zero journal writes. Mutations reverted byte-identical in the isolated worktree. Only `12_reviewer_receipt.json` + this report written (main checkout).
