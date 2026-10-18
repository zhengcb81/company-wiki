# Full-push parallel checks — independent design and implementation review

Verdict: **PASS_ENGINEERING; actual full-push latency remains to be measured.**

Scope: mother working tree `tools/pre_push_gate.py` and new `tests/unit/test_pre_push_parallel_phases.py`; no changes made to implementation, CI, source, tests, environment, originals or configuration by this reviewer. Review is limited to splitting the existing full-fallback push cases into two subprocesses. No claim of whole-suite parallel safety beyond the current selected smoke set, or of a successful real push.

## Frozen bytes reviewed

- `tools/pre_push_gate.py`: SHA-256 `4a6d7dcadada49dee234ee9e3f8216bc3a701e3243ddcf4bf633b6c7b4004274`.
- `tests/unit/test_pre_push_parallel_phases.py`: SHA-256 `4fe4d7cc1da89ef104fcd28ec0288e279a49a2b9dcc95c3815f4cedea4e3f1e7`.

## Findings

1. The split preserves the case set. Only `selected == ['tests/unit']` takes the parallel path. Group A runs all unit tests; group B is the existing smoke list after removal of cases already inside that unit directory. The current `cases[1:]` is correct because this branch requires exactly that singleton selection. Normal affected selection, standalone CI smoke and optional full local validation retain their prior paths. No tests, assertions or deadlines are removed.
2. Each subprocess retains its own 600-second timeout and receives a fresh `TemporaryDirectory`, explicit `--basetemp`, disabled pytest cache and disabled bytecode writes. Child environment copies, command-list copies and independent process module state avoid sharing Python monkeypatches, current directories or mutable pytest fixtures. The two threads only launch/capture subprocesses and print diagnostics. Each result is collected; exceptions become nonzero and do not abandon the other future. One failed/timeout result cannot be hidden by another green result. The executor context waits for both workers.
3. No concrete conflicting production write or fixed shared output was found in the current nonunit smoke set. Official-JSON persistence/CLI and source-scope tests use `tmp_path` catalogs/configs; worker-governance selected cases use temporary runtime/lock paths and mocked inventories/termination; OCR fake backend files are under its supplied temporary model/scratch root and its adapter is closed; remaining reviewed contract checks are in-memory or source/fixture reads. The B10 case scans source AST read-only. The global production-config integrity fixture only hashes the real configuration. The optional governance helper itself is read-only; it does not kill another process. This is an inspection finding, not a proof that arbitrary future tests may write shared files safely.
4. `push-914e0283.log` ends at the B10 node after other cases reached 99%, followed by the aggregate 600-second timeout. This identifies the interrupted test, **not** 600 seconds of B10 execution, and does not prove that the AST scanner is the root performance defect. Splitting independent work removes their serial sum from one timeout. CPU/memory contention and short native OCR deadlines still mean a measured speedup cannot be promised in advance. ROOT's next normal push is the performance acceptance evidence.
5. Direct pytest timeout/process-descendant behavior is unchanged: `subprocess.run` kills/waits for its direct child on timeout, while descendant cleanup relies on the existing test/adapter owners. This patch neither adds broad process killing nor proves new descendant guarantees. Temporary-directory cleanup exceptions remain red through the future exception path. Such failures should be reported explicitly, not treated as a green cleanup.

## Minimum engineering controls and actual evidence

The new tests cover a real two-thread barrier (both starts before either finishes), either-side failure including timeout code 124, real child processes with distinct basetemps and original-file sentinel restoration, exact full-fallback smoke dispatch, and wrapper exceptions with both temporary scopes restored. Existing temp-scope tests cover success/red cleanup, child Git-context isolation, bytes/string timeout output, 600-second preservation and GBK-safe diagnostics.

Read actual receipts:

- `.planning/shared-reading-production/du11/parallel-push-red.log`: 5 failures / 1.60s against the old source, specifically missing `_run_parallel_pytest_gates`; this is the initial feature-presence RED, not a falsely claimed post-implementation behavior failure.
- `.planning/shared-reading-production/du11/parallel-push-green.log`: **15 passed / 1.95s**, including the 8 new cases and 7 existing temp-scope cases.

Reviewer independently read the full implementation diff, test source and receipt tails; did not repeat these tests, run full units, start workers, call network/models or print environment values. No confirmed must-fix defect remains in this bounded delta. The previously unchanged normal affected/CI branches are also apparent in the exact diff; new dispatch tests do not by themselves constitute a new full CI execution.

## Acceptance boundary

Safe to integrate this engineering change and use the normal push hook to measure both groups. Keep the two labeled outcomes, original errors and cleanup diagnostics visible. A real full push must still show both subprocesses green within their existing timeouts; neither this review nor the small tests substitutes for that run. No additional approval, identity check, cache, test store or manual sign-off mechanism is proposed.
