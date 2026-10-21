# R5 contract debt isolated repair handoff

Ready for ROOT integration. This is an engineering repair handoff and does not accept any company R1/business result.

- Branch: `codex/r1-contract-debt`.
- Base: `45195e96cb15a1652b13899a99cfb827932a62f1`.
- Reviewed implementation commit: `f1dba9b735a914f6e4a2e78b798092487aa20531`.
- Worktree: `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`.
- Final accepted run: **green-reviewed,195 passed /0 failed /0 errors /0 skipped,pytest exit0**,2026-10-21T21:36:55.305839Z–21:38:52.413483Z. Only this run is final GREEN.
- Independent review: **PASS_CONTENT_BOUND,0 open blocking findings**, `/root/r1_contract_fix_review`; exact report MD/JSON preserved beside this file. It binds24 actual source/test/helper/current+historical golden content hashes; all still match after implementation commit. JSON handoff records the exact commit-to-review mapping.

## Changes and evidence

Bounded WAL retry and its5s deadline remain intact. Static waits are permitted only in the existing WAL setup function, with the prior peer/deadline/nonbusy behavior tests retained and other-loop negative tests added. The store import whitelist was not widened: neutral `FinalArtifactPin.effect_target` owns raw/projected naming with no serialized field added.

Three store wildcard queries now project only required fields. Real extended-schema tests verify that private extra columns do not widen reads, compaction stays idempotent, and paid/verify recovery preserves original attempts, fees and response ownership.

The first GREEN attempt exposed the same defect in public RunStore reservation readers. Independent review rejected narrowing that assertion. The original `reservations_for_run` assertion was restored; four separate reader regressions were recorded RED, then `_reservation`, `_budget`, `model_attempts_for_job` and `reservations_for_run` were fixed with one projection derived from `ReservationRecord` fields. The independent reviewer reproduced RED→PASS without the author fixture.

Historical v1 JSON bytes remain unchanged. A separate `current-v2` exact producer vector records the12 reviewed changes. Full-object equality after explicit expected changes, real source replay under both saved parser implementations, original byte ranges, unchanged claim text and valid derived hashes/references are checked. `core_business` classifies the existing launched-product/expanded-capacity sentence; no number/unit/fact was added. Negative tests reject invented facts, units and old-span citations. No blanket refresh or provenance stripping was used.

## Validation and honest intermediate results

| Receipt | Result |
|---|---|
| red-original |27 pass/4 fail/0 skip|
| red-projections |3 real wildcard-column failures|
| red-target |2 target-contract failures before implementation|
| red-run-readers |4 public-reader TypeErrors before shared projection fix|
| green-reviewed |**195 pass/0 fail/0 skip**|

`green`151/1 exposed the ledger defect. `green-final`152pass is the superseded narrowing experiment and is explicitly marked as such; it is not the accepted final result. Final Ruff on11 changed source/test/helper files and mypy on3 changed production files passed. All96 protected config/entity-file hashes and all24 tested content hashes stayed unchanged during the final run.

Tests used the mother `.venv` executable with worktree cwd and explicit worktree src/scripts/tests PYTHONPATH; execution.json proves actual imports. Normal commit hooks used the existing Miniconda runtime and ordinary hook environment. Two failed hook-environment attempts were preserved: missing pre_commit in the test venv, then test-only scripts PYTHONPATH injecting sitecustomize. No install, policy/config change or hook bypass was used. The successful implementation commit ran Ruff and host-assumption guard PASS; other configured hooks had no matching staged files.

## Isolation and remaining scope

No mother source/config/original/executor files were changed. Only explicitly authorized synthetic `.planning/r1ctfix` temp/log/cache was written in mother. Historical worktree `.planning` materials were preserved and never staged; the small dedicated PWF receipts are under this directory. Synthetic tmp remains available for audit; no unrelated files were deleted. No network/download/paid-model/API operation, Dayu change, ACL/global config change or install occurred.

This worker did not integrate or push master and did not rerun full7k, all-contract, RF/FF or paid E2E suites. It makes no arbitrary future-schema claim beyond the fixed reservation DTO/store contracts and no company-business acceptance claim. ROOT owns integration and push. The handoff-only commit following the implementation contains documentation and commit receipts; no tested source content changes after the independent review.