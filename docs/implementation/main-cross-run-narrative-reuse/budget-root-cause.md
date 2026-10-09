# Existing final-output accounting defect for MAIN

This package leaves `narrative_run_store.py` and `narrative_model_caller.py` unchanged. MAIN owns the budget-layer fix. The old-base budget_exhausted observation is not completion. Completed recovery is now separately accepted only with MAIN's corrected budget module temporarily integrated, then restored.

## Actual minimum counterexample

`tests/integration/test_narrative_batch_recovery_e2e.py::test_killed_coordinator_releases_owner_and_resumes_without_refunding_unknown_request` starts the formal finite CLI over one source, waits until the loopback server receives POST, observes the existing reservation, then kills the coordinator and observes its real spawned children exit. Original run `parent-kill` has 200000 tokens / 2000000 microUSD limits, a 2097152-byte final cap and normal persistent/scratch caps. No response receipt reaches the killed caller. The OS mutex is demonstrably released. A different AUTO entrypoint is refused with `BATCH_GENERATION_RECOVERY_REQUIRED` and creates no database or paid attempt.

Actual original-owner resume on this base: one local POST total; 3382 conservative tokens / 3782 microUSD; one unknown, zero unsettled reservation; `budget_exhausted`; summary `MODEL_BUDGET_DENIED`, dependent verify `DEPENDENCY_TERMINAL`. The original token/cost charge and request SHA remain. The only successful persisted result is select; effects count 0, content-addressed object count 0, scratch peak 0, reservation.output_bytes null. `pre-budget-fix-kill-proof.json` preserves these observations under `post-kill-owner-recovery`, including charged_output_bytes=2097152 and run_max_output_bytes=2097152.

## Existing chain and columns

1. `narrative_batch._run_prepared` creates run.max_output_bytes as min(source_count * request.max_final_bytes, request.max_persistent_bytes). One source defaults to 2097152.
2. `narrative_worker_factory` passes the finite max_final_bytes to `BudgetedNarrativeCaller.final_output_bytes_bound`. `BudgetedNarrativeCaller.generate` calls `NarrativeRunStore.reserve_model_attempt(output_bytes_bound=self._output_bound)` before POST, with a unique actual attempt/lease/generation.
3. `ReservationRecord.charged_output_bytes` returns `output_bytes_bound` whenever `output_bytes` is null. `_budget` sums it across all reservation attempts, as it correctly does for supplier tokens/cost.
4. `settle_finished_attempt_reservations` marks a finished attempt without a receipt unknown, sets error_code MODEL_WORKER_LOST and usage_settled_at. It preserves provider token/cost bounds, and leaves output_bytes/output_sha256/output_settled_at unset.
5. A retry of the same summarize job reserves another final bound. Admission checks charged_output_bytes + output_bytes_bound > run.max_output_bytes. 2097152+2097152 > 2097152 blocks the retry even though token/cost and physical-storage limits are sufficient.
6. `narrative_batch._final_documents` can only settle output after a verified visible artifact exists. No such effect/object exists in this case, so that path cannot release the old logical bound.

## Correct responsibility and remaining acceptance

Unknown supplier use is not proof of either zero or an additional local final object. The immutable original attempt and its full unknown token/cost bound must remain. Existing measured object/scratch guards continue to bound physical storage. Every source event has one summarize job and one verify job; exact run scope/job ownership and fenced results make one valid final slot per summarize job. Current `_final_documents` even settles all successful reservations for that same job to the same final version/hash/size. Different jobs/runs/refreshes have independent slots.

MAIN proposes aggregating local final reservation/output by summarize job (max unfinished bound / actual settled bytes), while summing all attempt tokens/cost. No new schema, database or refund is required. The actual same hard-kill test must subsequently require sufficient-budget owner resume -> completed visible artifact, with unknown fee preserved, then a new run exact pin/public replay -> zero additional POST. Do not relabel this package's budget_exhausted observation as recovery success.

## Verified MAIN correction

MAIN commit ce116dddb07184d99fe8fa9661171d2bc4aa88cc supplies per-job max final-output-slot accounting while retaining summed supplier token/cost across attempts. Its run-store file alone was overlaid for the exact hard-kill test. Old/restored SHA cfd28629ba573d09731830d7a6c5ed8baa45a89df70c5adfecae6b6d70156d83; overlay SHA 219340d3c96273588b222842bec615b72ba2deb65148df974b47cfa8492d336b. The owned module was restored in finally, remains identical to the code commit and is not included in this handoff's changes.

GREEN-integrated-kill-recovery-final: mandatory completed / 1 PASS / pytest 10.90s. Same job retries successfully within the existing 2097152-byte final slot, despite old output_bytes remaining null/bound 2097152. Token/cost totals include old unknown 3382/3782 plus receipt-known 92/111 = 3474 tokens / 3893 microUSD, unknown 1 / unsettled 0. Actual current effects/object count 1 and final bytes 4069. Fresh AUTO/run then pins the exact visible result, public current expected_source six fields and locator replay pass, zero new POST and zero own charged usage. The old receipt/hash is not invented or refunded. The strict test now rejects budget_exhausted.

The first overlay run's public caller failure is retained separately: catalog config at root lacked the public CLI's implicit config/.. project layout. The completed recovery assertions had already passed; a dedicated config/ fixture fixes this caller only. MAIN will rerun the same strict case after merging code with its budget correction.
