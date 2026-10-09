# W12 cache behavior receipt handoff

## Scope and baseline

- Isolated worktree: C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki
- Branch: codex/fresh-cache-receipts-20261009
- Production baseline:2350077ac31655d358e67390c6fbda129d80d7dc. MAIN reports0504aa9d has identical production source; this worktree is intentionally not reset.
- Only new tests/contract/test_fresh_cache_behavior_receipts.py and this own plan directory are written. No production source, real originals/config, W06 source-owner files, shared/root PWF, other repositories/installations, hooks or CI changed.
- No merge/push/install. Normal exact-path commit after final concentrated gate. MAIN owns independent review and integration.

## What the receipt measures

The test executes the existing finite narrative batch CLI, real spawned select/summarize/verify workers, current AUTO leases/reservations/outbox, and public transport reference/read with actual original-byte replay. A local HTTP model supplies prompt-derived synthetic drafts and known73+19 usage. Synthetic source acquisition is3 fixture calls outside the batches; no external provider/paid model call occurs. Passive interpreter profiling counts actual role/model/parser/replay/OCR entry and elapsed call duration in parent/worker/public-read processes; the real HTTP server independently counts model POSTs.

Whole-source generation is the accepted cache granularity. An affected source recomputes select→summarize→verify. There is no stage cache or second budget ledger. A hit still parses/replays locators. Artifact identity is exact artifact version ID + byte size + SHA + source reference; the public CLI reads and verifies the exact selected pin. Current metadata reference is separately recorded. Timestamped read receipts are observed, not used as immutable equality fields.

The parser variant actually executes supported transcript0.1.1 and leaves HTML1.0.0/PDF shared0.1.1 independent. Selector0.6.1 and prompt1.7.1 are explicitly synthetic upgrade pins, consistently declared by all producer/consumer processes. Prompt variant also changes the actual system instruction; it is not a released prompt. Model ID/settings variants travel over the actual HTTP wire. These observe the existing invalidation contract, not new production versions.

## Matrix expectations and observations

The completed engineering matrix before the final gate produced14 synthetic model POSTs across12 finite runs:

| Run | New POSTs / reservations | Charged tokens | New roles | Batch parse/replay |
|---|---:|---:|---:|---:|
| baseline, two sources | 2 | 184 | 2 each select/summarize/verify | 4/2 |
| same-spec new run | 0 | 0 | 0 | 4/4 |
| new owned source bytes | 1 | 92 | 1 each | 4/3 |
| supported transcript parser version | 1 | 92 | 1 each | 4/3 |
| selector / prompt / model / settings, each | 2 | 184 | 2 each | 4/2 |
| original spec recovered | 0 | 0 | 0 | 4/4 |
| known malformed model envelope | 1 | 92 | select/summarize1, verify0 | 1/0 |
| unknown malformed model envelope | 1 | 4302 conservative | select/summarize1, verify0 | 1/0 |
| reuse after both failures | 0 | 0 | 0 | 4/4 |

Unchanged HTML exact pin remains identical in bytes/parser cases. Unknown reservation count1 persists in its originating run; known/unknown reservation records remain byte-for-byte logically unchanged after later reuse. Failed refresh preserves previously readable artifacts. Same-spec new-run current public references remain unchanged; original spec can select its exact old compatible artifact behind newer model/settings publications.

Owned TEMP tree removed; pre-existing parent file SHA/mtime preserved; entire parent process environment and TEMP/TMP unchanged. Original source/sidecar bytes/SHA/mtime remain preserved. Failed observations1/2 are retained in first-run-receipt.json and second-run-receipt.json; both were errors in new fixture composition (catalog path / volatile read_at equality), not product defects. Third full matrix passed1/0skips in114.23s.

## Reproduction and final concentrated gate

Run at the assigned worktree root in a normal OS shell:

    $env:W12_RECEIPT_FILE = (Join-Path (Get-Location) 'docs/plans/fresh-cache-receipts-2026-10-09/acceptance-receipt.json')
    python -X utf8 -B -m pytest -q tests/contract/test_fresh_cache_behavior_receipts.py tests/integration/test_narrative_generation_reuse.py::test_different_configured_runs_default_to_one_generation_post_and_public_pin

The receipt destination is optional and restricted to this owned plan directory. Without it the normal test writes only owned temporary fixtures. Existing configured reuse test parametrizes HTML/PDF/TXT; final gate collects4 cases total. acceptance-output.txt contains exact normal run output; acceptance-receipt.json contains test/production file SHA, per-run frozen snapshots/jobs/attempts, real call trace/count/duration, HTTP wire instruction/data hashes, exact public identities/read receipts, conservative accounting, time/storage and cleanup. Final pass count/time will be appended after completion.

## Limits and remaining owner work

- These are synthetic engineering receipts, not real-company M3 repeat receipts or model-quality review.
- The owned TXT/HTML fixtures do not invoke OCR; observed zero OCR cannot establish visual-deck cache behavior or OCR performance.
- Walltimes are instrumented local observations, not performance thresholds. Engine storage receipt measures its persistent increment and publication scratch peak; owned fixture tree totals additionally include test instrumentation/request files, so they are separately labelled.
- Every new completed miss recomputes all3 roles for the affected generation; no claim of per-stage reuse.
- Tests use235 baseline. MAIN must perform the distinct concentrated integration recheck after W06, then its authorized normal merge/push/exact CI.
- ROOT M3 remains bounded real same-spec repeats for each of the3 actual companies. No additional provider/model invocation is made by this handoff.

## Final concentrated acceptance
2026-10-09: 4 PASS / 0 FAIL / 0 SKIP,112.88s. Normal ruff check PASS. The final receipt SHA matches the committed test bytes; actual production/test file SHA is also in source-test-sha256.json. Normal pre-commit hooks will be recorded in commit output.
Test SHA256: 18d7637ad795d9f5afd07da05f28c424a4657b168f460c3a8d5b86aafeaefdc5
| Run | POSTs | reservations | tokens | unknown | select/summarize/verify | parse/replay/OCR | wall s | public read s | persistent added bytes | scratch peak bytes |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| baseline | 2 | 2 | 184 | 0 | 2/2/2 | 4/2/0 | 4.134 | 3.546 | 303039 | 4063 |
| same-spec-new-run | 0 | 0 | 0 | 0 | 0/0/0 | 4/4/0 | 1.094 | 3.714 | 135 | 0 |
| new-source-bytes | 1 | 1 | 92 | 0 | 1/1/1 | 4/3/0 | 3.753 | 3.841 | 70008 | 4121 |
| parser-version | 1 | 1 | 92 | 0 | 1/1/1 | 4/3/0 | 5.326 | 3.555 | 61759 | 4063 |
| selector-version | 2 | 2 | 184 | 0 | 2/2/2 | 4/2/0 | 4.099 | 3.605 | 122852 | 4063 |
| prompt-version | 2 | 2 | 184 | 0 | 2/2/2 | 4/2/0 | 4.023 | 3.613 | 118756 | 4063 |
| model-identity | 2 | 2 | 184 | 0 | 2/2/2 | 4/2/0 | 4.216 | 4.504 | 110577 | 4069 |
| model-settings | 2 | 2 | 184 | 0 | 2/2/2 | 4/2/0 | 4.185 | 3.721 | 115257 | 4063 |
| original-spec-recovered | 0 | 0 | 0 | 0 | 0/0/0 | 4/4/0 | 1.113 | 3.770 | 137 | 0 |
| known-failure | 1 | 1 | 92 | 0 | 1/1/0 | 1/0/0 | 3.282 | 0.000 | 20617 | 0 |
| unknown-failure | 1 | 1 | 4302 | 1 | 1/1/0 | 1/0/0 | 3.319 | 0.000 | 20846 | 0 |
| after-failures-reuse | 0 | 0 | 0 | 0 | 0/0/0 | 4/4/0 | 1.104 | 3.725 | 8329 | 0 |

Function-entry counts and non-exclusive nested duration semantics are explicit in the receipt. New-run hit's persistent increment is finite run bookkeeping, not a new narrative object or model reservation. No physical parse count or additive time decomposition is claimed.

Cleanup: {"environment_unchanged": true, "owned_temp_removed": true, "parent_files_restored": true, "temp_environment_unchanged": true}. Fixture acquisition calls: 3; synthetic HTTP model POSTs: 14 in this final matrix; external/paid providers:0. The fixed source_baseline field denotes fixture authoring baseline235; future post-W06 receipts must distinguish their actual production SHA.
