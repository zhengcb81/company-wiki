# ROOT W06-FF-MATRIX independent intake

Scope: read-only external repositories and delivery; only this intake directory may be written. No real network/provider/LLM calls, installation, merge or product edits.

## Phases

- [x] A: exact Git/PWF/manifest/code provenance and producer binding.
- [x] B: narrow independent oracle/CLI controls and coverage review; preserve failures.
- [x] C: report MD/JSON, source manifest and explicit ROOT next action.

## Next Step

Intake complete. ROOT must repair shared harness causes before COMPLETE/merge acceptance; see independent-review.md/json.

## Findings

- Delivery is two normal commits ahead of FF main, with 139 added paths and 136,567 retained handoff bytes. Product `scripts/` unchanged; tests/tools are independent write sets.
- 23 / 25 declared SHA rows match. Only worker-owned task_plan.md/progress.md changed after the manifest; both actual diffs are final status updates. Input folder is untracked and ROOT owned.
- Nine recorded producer module hashes still match current bytes. The recorded FF run HEAD d9c5383e exists and its scripts match current HEAD, although it is not the delivered HEAD; actual CWP dependency was c145da9b, not the original fixed baseline, and was explicitly recorded.
- Delivered 12 pure units pass independently (3.19 s overall). They do not cover actual runner invariants and are green tests that detect fabricated report vectors, not a recorded test-first failing stub.
- 11 independent pure/helper probes: 10 FAIL, 1 correct explicit quarter-rejection control. No actual product/provider CLI or network was started; in-process CLI proof substitutes every producer and a fake clock, and is labeled scaffolding only.
- Harness does not meet no-secret-read/minimal-env declaration. `_hash_meta -> sha256_file -> Path.read_bytes` reads any present FMP key file; original worker does not necessarily contain that file, so this is not evidence a real key was read in delivered run. All non-FMP host credentials/URLs propagate to child environment. No leak or network send is established.
- Unverified code binding/220-second simulated batch still exits 0; over-budget case only warns. Supplied pre-existing scratch content is recursively deleted and sentinel overwritten, then restored=true is reported.
- Wrong returned Q2 for requested Q3, unrelated upstream error as cutoff evidence, repeated downloaded_new without source_ref, and unknown request count incorrectly zero are each reported PASS by case predicates. These are harness false-positive bugs; product correctness is not inferred from these synthetic helper probes.
- Matrix omits required wrong symbol, corrupt SHA, wrong MIME, oversize, timeout, post-call failure/retry restoration and full market×period coverage. Generic synthetic adapters do not prove actual StockInfoDLSimple routing.
- Existing cross-period prepare_local_source failure in original attempt-1 was avoided by changing the fetch case to an empty entity/kind, rather than retained as a named failing regression in final matrix. ROOT owns product repair; harness must report PARTIAL meanwhile.

## Initial facts

- Actual worktree is `_harness_worktrees/w06/ff-contract-matrix`, not the guessed `ff-matrix` path.
- FF canonical main is 08ec85b27133cdf8a8d3b38fdba15255fc1ebac2; only untracked config/FMP_API_KEY.txt observed. Secret contents are not read.
- Delivery claims COMPLETE, 12 unit tests and 16 synthetic matrix cases; declares cross-period preparation failure as follow-up and moved fixture case to avoid that path.
- Sandbox external git status produced `not a work tree`; read-only escalated status succeeded. No configuration or index change.
