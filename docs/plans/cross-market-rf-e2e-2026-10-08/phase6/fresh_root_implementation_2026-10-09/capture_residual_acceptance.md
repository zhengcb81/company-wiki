# W04 residual independent review

Date: 2026-10-09. Exact reviewed HEAD: `17e154a757ec0e6534b7b93d8bd599e4f02a8eca`, parent `c839af5857dc0d9720a3127f1a2d3028493b50f7`.

Worktree: `C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki`. Independent reviewer owns this report only, not implementation, integration, installation or publication. The previous `capture_independent_review.md` is unchanged.

**Verdict: M2 needs a small follow-up before acceptance.** The three previously reported defects are repaired. Two remaining boundaries were actually reproduced: a cold-start timing fixture still assumes network progress before a total deadline, and a completed-result replay does not finish interrupted staging cleanup. No real-company M3 conclusion is implied.

## Exact-state verification and actual execution

- Read HANDOFF.md, validation.json, the selected lane task_plan/findings/progress, the two-source follow-up diff and relevant original source/tests. Exact HEAD matched before and after; all six recorded source/test SHA-256 values matched; tracked worktree stayed clean. Git child environments omitted inherited `GIT_*` variables, so hook/sandbox environment did not select another worktree.
- Executed only the representative capture contracts, not another six-file/full regression suite. Command from the exact worktree:

```text
python -X utf8 -B -m pytest tests/contract/test_official_capture_recovery.py -q --tb=short -k "same_capture_id or current_cap or invalid_retained_json_shapes or completion_record_write_failure or completed_result_wrong_shape or completed_replay or real_total_deadline or public_stall_cli or public_capture_cli or shared_budget or capture_different_sha" --basetemp <owned TEMP>/pytest -o cache_dir=<owned TEMP>/cache
```

- Actual result: **20 passed /1 failed /0 skipped /18 deselected /23.57s**, Python 3.13.9, Windows. Failure was the first cold-start `test_real_total_deadline_stops_stream_and_retains_usage[trickle]`: line 197 required positive received bytes but measured zero. This failed run is retained in `capture_residual_run.json`; it was not hidden by retrying for an eventual green. The harmless `asyncio_mode` warning is a consequence of disabling automatic pytest-plugin loading in this isolated execution.
- Separately executed three unchanged-API controls through Python with TemporaryDirectory and pytest.MonkeyPatch: prepared-transport trickle, prepared-transport stall and one post-result cleanup fault. Exact observations are in `capture_residual_controls.json`. These are observed controls, not three additional pytest passes or a full-suite claim.

## Original three findings — repaired with independent support

| Previous finding | Actual rerun and inspected mechanism | Result |
|---|---|---|
| IR-W04-01: response-loss retry cannot resolve successful capture ID | First recovery followed by a reopened public recover CLI and third recovery returned identical SourceRef, first completed status and immutable actual HTTP receipt. Only the initial GET occurred; repeated recover reported download_events=0 and current acquisition_usage={schema_version:1.0,response_bytes:0,cost_usd:0}. The completed projection remained <=65,536 bytes and contained no source body. | Repaired |
| IR-W04-02: retained reuse ignores current max_bytes | Actual 72-byte captured body was refused by current cap10 through retained capture retry, explicit recover and public CLI; descriptor/raw stayed byte-identical and no extra GET occurred. After successful cap72 recovery, canonical reuse and completed-ID replay likewise refused cap10. | Repaired |
| IR-W04-03: valid JSON non-object triggers inventory/CLI traceback | Eight retained top-level/nested shape controls and three completed-result shape controls passed. `[]` and invalid nested objects produced inventory unavailable or safe named JSON exit2; no traceback or invented usage/provider-start claims; originals remained. | Repaired |

The fifteen appended repair controls all passed in the representative run. Completion-result write interruption preserved staged raw/descriptor and later resumed; current canonical bytes were altered only inside a synthetic fixture and public-reader SHA verification rejected replay. Existing wrong-expected-SHA refusal remained strict. Receipt/current-cost separation and ordinary public capture success remained green.

## Residual R-W04-01 — cold-start body-progress fixture is not deterministic [test defect]

The product intentionally includes TLS transport construction in its total acquisition deadline. In a cold process, the 0.35-second budget can expire before a real request or body read. Requiring positive partial bytes in that scenario is an unsupported startup-speed assumption. The corrected public CLI test already distinguishes real observed progress; the in-process body test at lines 189–209 still constructs the transport inside that same short deadline.

Independent control used the existing `transport=` parameter and constructed `httpx.AsyncHTTPTransport(retries=0)` immediately before starting the body-control timer, without an HTTP warm-up or external call. **The product deadline stayed exactly 0.35 seconds.**

| Actual control | GET observations | Received and persisted bytes | Elapsed | Usage |
|---|---:|---:|---:|---|
| Prepared-transport trickle | 1 actual `/original` | 9, exact prefix and SHA verified | 0.375s | provider_started=true; complete=false |
| Prepared-transport stall | 1 actual `/original` | exactly 8, exact prefix and SHA verified | 0.373s | provider_started=true; complete=false |

Both actual network reads were interrupted before the fixture's complete 72-byte body, within the existing <1.3s observation allowance. The public cold-start CLI contract separately remained green with total deadline unchanged and actual persisted progress rather than an unconditional GET assumption.

Required follow-up: make the dedicated network/body fixture prepare its transport outside the short timer, keep strict actual GET/partial-SHA/body-prefix assertions and stall8, and retain a cold-start total-deadline control that permits zero GET only with observed provider_started=false/zero usage. Do not change product timeout, pretend server-written bytes were client-read bytes, or simply rerun until warm-start green.

## Residual R-W04-02 — successful completed replay leaves interrupted raw cleanup [product recovery defect]

Mechanism: `_import_retained` persists `<capture_id>.result.json` at official_source_flow.py:417 before raw/descriptor cleanup at 419–420. If cleanup fails or the process stops in that gap, `recover_official_source` at 615–617 verifies/returns the completed projection directly. It never finishes the owned staged-body/descriptor cleanup.

Actual unchanged-API control:

1. A copy-faulted local import retained the original 72-byte body and its descriptor.
2. Patch only `CanonicalSourceWriter._remove_staged` to raise `OSError("fixture-after-result-cleanup")` during recover. The result was already durable; raw and descriptor were preserved.
3. Remove the patch and recover the same ID again.
4. Recovery succeeded with status `imported_new`, download_events0 and zero current acquisition delta. **Raw and descriptor still existed**, and inventory still reported that ID as `retained` with byte_size72.

No raw loss or repeated HTTP charge was observed. This is a recovery-cleanup gap: a successful replay permanently leaves the redundant source body and misleading pending recovery item behind. Each body can be as large as the bounded original request, so the issue also matters to the project's storage-footprint requirement.

Required follow-up: after validating the durable completed projection, current cap and actual canonical SHA under the existing same-ID mutex, idempotently finish only that capture's validated owned staging remnants. If cleanup itself fails, preserve canonical original/result and return an explicit recoverable diagnostic. Never delete a descriptor's arbitrary path, remove other captures, weaken damaged-result/current-SHA refusal, or add a second task queue. Add this one fault control beside the existing result-write-interruption control.

## Bounded projection / contract review

The completion object stores SourceRef, initial completion status, historical cap, actual capture_receipt and existing acquisition journal attempt ID. `_persist_completed` enforces <=64KiB, flushes and fsyncs its temporary file then atomically replaces the result before raw cleanup. It contains no original body, canonical physical path, new task status or authorization receipt. The same-ID recovery uses the existing OS file mutex. `_read_capture_record` bounds input and rejects duplicate keys, nonfinite/deep invalid JSON and non-object shapes before member access. Completed replay checks current cap and calls the actual public SourceVersionReader.verify_version; it does not manufacture a new HTTP receipt or copy historical acquisition usage into the current delta.

This metadata projection is compatible with the assigned abstraction and durability responsibilities. The post-result cleanup gap above is the sole newly demonstrated product repair requested by this review. No general permissions, human sign-off or fresh authorizations are added.

## Isolation, cleanup and limits

- Two explicitly owned TemporaryDirectory roots, prefixes `w4r-` and `w4c-`, were removed on exit and verified absent. Requested pytest basetemp was within the existing Win32 path budget, not relocated; cache and synthetic catalog/originals were entirely within the first root. The second held only the three independent controls. Loopback servers were closed.
- Zero external HTTP/model/provider calls and zero paid calls. Loopback URLs only; the helper socket guard rejected non-loopback addresses in-process, and HTTP transport uses trust_env=false. No actual credential or complete environment/config value was printed.
- Production `config/source_catalog.yaml` SHA and mtime were unchanged around the representative run. No production original, sealed company run, other lane, source file, skill installation, Git ref or old review was modified. Worktree stayed clean and all six acceptance hashes remained exact.
- The implementer's six-file **103-pass** grouped result was inspected, not independently claimed as rerun. This review's first actual run exposed a timing-fixture defect; its receipt remains available. Normal publication hooks and exact remote CI remain MAIN-owned.
- Real original CN/HK/US M3, genuine lost historical body recovery, cross-company forecast/research quality, filesystem durability under power loss and every possible I/O fault were not established here. M3 remains pending; a new peer capture must never be labeled recovery of a historically lost exact SHA.

## Concentrated next acceptance

Repair only the two residuals above in the original W04 worktree. Run the deterministic body/cold-start boundary plus post-result-cleanup fault and original response-loss/current-cap/actual-SHA controls once at the exact new commit. Keep previous RED/GREEN evidence and this report. MAIN can then make M2 acceptance without repeating unrelated full suites or introducing small-node manual approvals.
