# Final independent review: production-v4 finalization

**Verdict: PASS for the runner-finalization/accounting subtask only.** This does not approve source preflight CF1–CF4, a paid formal summary, narrative quality, or a complete Revenue Forecast run.

## Frozen evidence

The implementation matched the final freeze manifest at review time:

| File | SHA-256 |
|---|---|
| `tools/document_understanding_benchmark/phase_c_runner.py` | `4cab71dd8691d4d15fa7a8ab1e96829eeb948126a7f44e04a5033fa6157acc66` |
| `tests/test_phase_c_finalization.py` | `bca693d1b014c0aaac9d362d0290b2d7dedee1649ba95c278cb2221628dbb35d` |
| `docs/plans/du11-source-closure-2026-10-18/review/production-v4-formal-20261025/run_operation.py` | `635ac8e58b77cdda76c5f7c9fb182ff410f273287c461c9c797519d1990c0b3e` |

The shared verification receipt is `../finalization-verification.json`; it lists these same hashes and records zero paid calls and downloads. The finalization-specific tests passed 12/12 in 11.77 seconds. The wider four-file host run passed 59/59 before the journal-binding changes; it is not represented here as a run against the final source. The current 12-test finalization run covers the final changed code. Ruff and diff-check are reported green by the freeze receipt. Earlier red cases remain available under `review/st-a05-local-flow-20261025/review-finalization-*`.

## Review conclusions

The earlier independent findings are closed in the frozen version:

1. **Accounting failure cannot skip cleanup.** `run_pair` handles native-ledger failures and observations in nested finalization paths, then applies an absolute owned-temp-root check and cleanup. The check does not rely on `assert`, and cleanup failure is explicit `FAIL`. The receipt is written only after cleanup is attempted.
2. **Unknown cost is not reported as zero.** A failed accounting append records `native_usage_reconciliation_required`, run ID, and a conservative per-request hold. `mother_totals` sums actual native rows by run and adds only the per-dimension shortfall to the full run-level hold, avoiding double counting. The operation wrapper sets charged deltas to `null` and `usage_including_unknown_holds_within_limits` to `false` when reconciliation is required.
3. **Ledger persistence is prioritized.** The fallback is fsynced to the existing mother `usage.jsonl` before the diagnostic sidecar is attempted. A sidecar-write error does not erase an already persisted mother hold. If the ledger write fails, that error remains explicit and the operation cannot pass.
4. **Recovery works after the temporary AUTO database is gone.** `--reconcile-run-id` replays the existing native-usage journal through the same ledger-writing path without opening AUTO or sending a request. The fallback binds the journal’s SHA-256; missing or changed journals are rejected without releasing the hold. Empty usage after a recorded POST is rejected. Repeated replay is deduplicated, and a successful reconciliation appends a same-key zero hold while preserving the journal binding.
5. **The failure tests exercise the relevant boundaries.** They cover append failure with both absent/present simulated POST evidence, ledger success despite sidecar failure, durable replay after DB deletion, repeat replay, unknown-hold max accounting, empty journal after POST, and mutated/empty/unbound journal rejection. These tests use synthetic fixtures and make no real API call.

The fallback is intentionally conservative: if the native journal cannot be durably produced or the shared ledger cannot be written, the runner returns an explicit failed/unknown state and cannot claim a zero delta. If both the shared ledger and diagnostic output are unavailable, software cannot persist a durable shared hold; this is an infrastructure storage failure and must remain a failed run requiring reconciliation, not a successful or free operation.

## Scope boundary

This PASS only closes the cleanup and unknown-accounting/replay implementation in the three frozen files above. The verification receipt still says `formal_source_preflight: OPEN_CF1_CF2_CF3_CF4`. No real model request, provider spend, document download, or raw copy was performed in this review. The product source owners and reading catalog were not changed by this subtask.
