# Mixed model prompt admission foundation

## Actual root cause

The first true mixed public CLI node rejected projected model requests before HTTP because run.prompt_version stored the raw1.7.0 while projection requests use official-json/1.0.0. The caller collapsed a RunConflictError into budget denial. After that admission repair, NODE02 made exactly the correct HTTP calls and settled actual usage, then genuine sys.settrace at the public CLI found the same single-version assumption in store._compact_terminal_narrative. Original RED logs and the safe code-position-only trace are retained. This handoff concerns the ledger foundation; root owns batch binding/caller classification/terminal integration.

## Frozen API and storage

`model_prompt_version(binding_json: str | None, *, job_id: str, default_prompt: str) -> str` is a pure shared lookup. No database, source, model or provider reads. Optional immutable binding_json.job_prompt_versions maps model job IDs to nonempty unpadded prompt strings. Missing map preserves old strict default_prompt. Present map with no requested job raises RunScopeError rather than silently using raw default; malformed values raise RunConflictError.

create_run's existing scope query also reads job_type, and optional map keys must exactly equal the scoped source.narrative_summarize jobs. Zero model jobs allow an empty map. Validation precedes run/member insertion in the same transaction. reserve_model_attempt uses the shared helper and retains existing model/pricing, membership, active lease/generation, request replay and all budget caps. Table layout and public method signatures are unchanged. This ledger validates the binding's declared prompts; the batch owner derives and freezes them from the actual execution manifests. It does not infer issuer/source meaning or re-open original bytes.

## TDD and responsible tests

Unique source: src/company_wiki/automation/narrative_run_store.py. Unique new test: tests/unit/test_official_json_run_prompt_admission.py. Initial24 tests:17 FAIL/7 PASS before implementation. Shared helper5 tests initially FAIL before the helper existed. Final29 new plus22 existing ledger tests:51 PASS in9.63 seconds. Ruff and mypy report0 issues. See run-prompt-red.log, run-prompt-helper-red.log, run-prompt-final-green.log/json and run-prompt-final-mypy.log.

The tests use real owned TEMP SQLite runs/jobs/attempt leases. Same run admits raw and projected correct prompts, charges the same token/cost/output budget and prevents request replay from sending again. Swapped prompt/model/pricing, malformed/missing/extra/non-model map scopes and non-model reservations fail without inserting or charging. Old no-map runs retain strict single-prompt behavior, frozen maps cannot change on resume, and token/cost/output caps cannot be bypassed by selecting another prompt. TEMP cleanup is recorded. No HTTP or external provider is called in this ledger suite, and no commits were created.

Root separately connects immutable batch binding4 and terminal compaction to this helper; full mixed public CLI acceptance is reported separately in BATCH_E2E_HANDOFF.md after the final genuine node.
