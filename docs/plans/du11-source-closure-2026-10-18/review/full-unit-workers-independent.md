# Full-unit two-worker scheduling: independent bounded review

**PASS_BOUNDED_ENGINEERING_REVIEW.** No confirmed source defect in the inspected1tool+1test change. This is not proof that the full local suite finishes faster or under600s: normal pre-push still has to run the entire actual inventory. It is not an extra permission/review gate.

## Frozen scope and delta

Reviewed ROOT isolated WT `tools/pre_push_gate.py` SHA `a2df2fcb824a97642cf4003aae1d359aca14a330e121cad4242c5213d46aefb9` and new `tests/unit/test_pre_push_full_unit_workers.py` SHA `e42810640d838a5be5c9921c687602cd48887e5e6ce2e976e33abef1e02d741e`. Both stayed identical before/after independent execution and final receipt assembly. FF root branch a9c2dcf was not touched. Source edits/commit/push by this reviewer:0.

The diff changes only the exact-token `if 'tests/unit' in cmd` branch from verbose/durations to adding **`-n 2 --dist=loadfile`**, retaining verbose/durations. It does not remove or replace any collection path, add a deselection marker, fail-fast, maxfail, skip or retry option. Existing narrow and contract gate command paths remain unchanged. The existing full-push dispatcher still runs full units once and the remaining independent nonunit smoke once; its old parallel-phase failure and cleanup tests are unchanged. The existing `_run` default600 and caller per-test `--timeout=180` remain unchanged. `.github/workflows/ci.yml` is not edited; its direct full-unit pytest remains the CI responsibility.

`pytest-xdist>=3.3.0` is already in `requirements-test.txt`, not an undeclared assumption. Using2 workers is a fixed bounded choice, not auto-spawning12. `loadfile` places a file's tests together so module fixtures remain coherent; session-scoped fixtures still correctly occur separately in each interpreter, so only the real full-suite run can determine any existing cross-file shared-state assumption.

## Independent execution

1. **New4cases PASS,4.69s**: command scope full-vs-narrow; actual nested pytest with two source files/four collected cases; success and intentional-failure paths; exactly1skip, failure count0/1, three executed observations, workers `{gw0,gw1}` and two distinct PIDs. The child failure remains nonzero; all cases are accounted for. Owned test directory restored and outer temp removed; existing pytest relocation receipt says removed=true. One harmless unknown `asyncio_mode` warning results from deliberately disabled automatic plugin loading in this small independent outer run, not a test failure.
2. **Three independent narrow/nonzero controls**: `tests/unit/test_small.py`, `tests/contract/test_small.py`, near-prefix `tests/unitary`; each gets no `-n`, preserves fake exit7 and cleans its owned basetemp. These are finite argument/return controls, not a real full test run.
3. **One actual forced-controller-timeout/worker-lifecycle control**, detailed below. It executes two genuine xdist worker processes with live SQLite connections in worker tmp_path and30s sleeps, while only the diagnostic wrapper passes timeout5 to the unchanged `_run`. No600s production constant was altered. Returned124, both worker PIDs dead on return, owned gate/outer Temp removed, no manual process kill required.

The earlier author84PASS/6.44s log was read, not repeated or represented as this reviewer's execution. The737/763/full suites were not run here. Evidence: `full-unit-workers-focused.{log,xml,json}`, `full-unit-workers-timeout-control.json` and the bounded probe source.

## Actual process and temp isolation

This uses xdist's real interpreter workers, not threads sharing application module globals. Installed `xdist.workermanage.WorkerController.setup` creates each local worker's basetemp at the controller base / `popen-<gateway.id>`; `xdist.remote.setup_config` installs that exact worker-specific path. Existing outer `TemporaryDirectory(prefix='cwpp-')` remains invocation-owned. File scheduling is not a claim of isolation from deliberately shared external production resources; hermetic unit fixtures must continue using their existing owned paths.

## Timeout behavior established from source AND one live control

Installed execnet `gateway_base.BaseGateway._thread_receiver` catches EOF, finalizes channels and calls `WorkerGateway._terminate_execution`. The worker first waits5s for execution; if still active it calls `interrupt_main` on Windows (SIGINT on Unix), then waits10s more and calls `os._exit(1)` if necessary. Installed xdist also converts channel shutdown into its finite SHUTDOWN marker for normal scheduling. This is concrete current dependency code, SHA-bound in JSON, not an inference from experience.

The real control returned **124 in20.064s** for an explicitly injected5s diagnostic runtime timeout. Two workers `{gw0,gw1}` had actually started and held SQLite connections while sleeping. Both were gone when `_run_pytest_gate` returned; the SQLite-holding worker basetemp and all owned outer files were removed. Thus this ordinary-Python busy-worker condition is handled by EOF termination; the test did not merely time out before workers started and did not fix cleanup by killing unrelated processes.

**Time accounting must remain honest:** subprocess execution timeout stays600s, but execnet may require approximately15s shutdown grace. Do not describe the entire wall clock as strictly capped at600s. Windows `subprocess.run`'s post-kill communicate can wait for the worker-owned pipe handles to close during that grace, which is consistent with the observed5+15 result. No deadline was raised in production; the distinction is runtime deadline versus bounded process teardown. This control does not establish termination of arbitrary native code that prevents the receiver thread from running, or arbitrary grandchildren created by a test. Existing native-isolation/owned-process tests and the actual full suite remain responsible for their own subprocesses; no new general process-permission framework is proposed.

## Review controls and retained diagnostic harness mistake

A first own timeout probe created synthetic Python source using Windows default encoding despite a non-ASCII temporary path literal. Pytest correctly rejected those two files during collection; no blocking test or lifecycle result was obtained. That self-authored harness error is retained as `harness-encoding-full-unit-workers-timeout-control.{json,log}` and is **not** a product failure or evidence of timeout robustness. The corrected standalone probe writes UTF8 and uses path-relative source (no embedded owner path), then performed the single meaningful live timeout control reported above. Product source stayed frozen through both; no assertion was weakened.

Minimal allowed OS/runtime environment only, no inherited credentials, no dotenv or auto plugin loading; the nested synthetic tests explicitly load xdist. Original/key/config/API access:0. No full PDF or external provider invoked. All diagnostic owned directories removed; any process cleanup would have targeted only recorded owned PIDs, but actual `owned_forced_cleanup` was unnecessary.

## Next existing project action

ROOT may make its normal tool/test commit and run the ordinary full pre-push, preserving all cases and current600s execution timeout. Record actual full-suite test counts, runtime and failure/timeout result; only then conclude whether two-worker scheduling fixes the observed96%-progress timeout. No early performance or remote-CI success claim is supported by this bounded review.
