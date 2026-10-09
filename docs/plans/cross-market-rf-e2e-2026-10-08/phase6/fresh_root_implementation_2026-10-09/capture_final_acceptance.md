# W04 final independent acceptance

Date: 2026-10-09. Exact reviewed HEAD: **68333bc360eb35b84f0616564953411e306f7610**, parent `17e154a757ec0e6534b7b93d8bd599e4f02a8eca`; original delivery `c839af5857dc0d9720a3127f1a2d3028493b50f7`.

Worktree: `C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki`.

**Verdict: M2 engineering ACCEPT for the combined three-commit delivery.** The original three findings were closed by the first follow-up; the two residual boundaries and bounded identity-safe cleanup now have supporting independent execution. Merge/push/installation and exact-head remote CI remain MAIN-owned. Actual original CN/HK/US company M3 remains pending and is not established by this verdict.

## Scope and exact-state checks

Read the final HANDOFF.md, validation.json, progress/findings and exact parent-to-HEAD source/test diff. Reviewed the shared capture suffix mapping, `_load_retained(require_original=False)`, completed replay's verification-before-cleanup ordering, bounded streaming raw identity check, finite cleanup diagnostics, and changed body/cold-start fixture controls. Exact Git HEAD matched before and after; all **six** recorded source/test SHA-256 values matched; tracked worktree remained clean.

Prior `capture_independent_review.md`, `capture_residual_acceptance.md`, their real failed-run JSON and the original RED/GREEN history are retained unchanged. The implementation's initial 88-pass, 103-pass follow-up, residual six-test RED, unknown-sidecar RED and **73 passed /1 failed** observation run remain recorded. The final implementer **74 passed /67.45s** responsibility set was inspected, not claimed as independently rerun.

## Actual representative execution

Run from the exact worktree with `PYTHONPATH` pointing to its own src, `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, no inherited `GIT_*` child variables, and TEMP-owned cache/basetemp:

```text
python -X utf8 -B -m pytest tests/contract/test_official_capture_recovery.py -q --tb=short -k "body_read_deadline_preinitialized or public_stall_cli or completed_replay_cleans_only or completed_replay_cleanup_failure or completed_replay_refusal_preserves or completed_replay_keeps_changed" --basetemp <owned TEMP>/pytest -o cache_dir=<owned TEMP>/cache
```

Actual result: **10 passed /0 failed /0 skipped /36 deselected /8.52s**; Windows, Python3.13.9. Command/output and cleanup evidence: `capture_final_run.json`. The existing `asyncio_mode` warning reflects intentionally disabled automatic plugin loading, not a test refusal.

| Responsibility | Actual selected controls | Independent result |
|---|---|---|
| Body cancellation after real provider start | Prepared real AsyncHTTPTransport; both stall/trickle remain under product0.35s, require actual GET, positive incomplete prefix and raw/receipt/SHA agreement; stall requires exactly8 bytes | 2 passed |
| Cold total deadline | Public CLI includes transport setup; provider start derives from persisted client attempts, body progress from actual raw/receipt, server GET remains a distinct observation | 1 passed |
| Interrupted completion cleanup | Real loopback capture, faults at raw or descriptor deletion, public recover CLI, unchanged completed result/SourceRef/receipt, currentdelta0, no extraGET, unrelated sentinel and canonical source untouched | 2 passed |
| Repeated cleanup failure | Available original completed result plus pathless finite `staging_cleanup_failed/OSError`; raw preserved; later recover finishes cleanup | 1 passed |
| Refusal before cleanup | Currentcap10 or actual canonical SHA mismatch preserves pending raw/descriptor/result; after correcting fixture/currentcap, only matching remnants cleaned | 2 passed |
| Changed/unknown retained input | Changed raw or missing receipt retained with finite diagnostic and available true result; restore exact fixture identity then cleanup resumes | 2 passed |

The body test no longer depends on cold TLS construction finishing within0.35s: transport construction is outside this dedicated body-control timer, with no warm-up HTTP. The production total-deadline code is unchanged and continues covering initialization for normal/cold callers.

## Two additional independent unchanged-API controls

These are actual separate controls, not extra pytest cases or a full-suite claim. Exact finite observations: `capture_final_controls.json`.

### Cold CLI: attempt, server request and received bytes are separate facts

A new child process against the owned stall server produced:

- Product deadline: **0.35s**, error_code `deadline_exceeded`, safe JSON exit2.
- Persisted client `http_requests`: **1**.
- Remote server GET count: **0**.
- Actual retained body: **0 bytes**, empty-body SHA verified against the receipt.
- `provider_started=true`, `acquisition_usage_complete=false`.
- Failure usage/receipt usage and raw identity agreed exactly.

This independently reproduces the implementer's 73/1 observation distinction: no server GET does **not** prove no client connection attempt. The old residual report's suggested “zero GET only with provider_started=false” condition was too strong and is superseded here by actual attempt/byte evidence. A true clientattempt0 must still report no provider start, zero observed usage and complete=true. No product counting, deadline or usage assertion was weakened to force a green outcome.

### Unknown same-ID filename cannot be adopted for deletion

Using only a synthetic lake, a copy-failed local capture was recovered with one intentional post-result raw-cleanup fault. Its real completed projection and canonical original were already durable. Then only its fixture descriptor was changed to reference a same-UUID `.txt` sentinel while the real stored MIME requires `.html`.

Actual repeated recover:

- Returned the true completed result and immutable actual receipt with download_events0/currentdelta0.
- Added only `{status:retained,reason:invalid_retained_capture}`.
- Left the original staged raw, wrong-filename sentinel and completed-result bytes untouched; output contained no physical fixture path.
- After restoring the exact original descriptor, replay removed only the matching `.html` raw and descriptor. The `.txt` sentinel stayed byte-identical; completed result bytes stayed identical; SourceRef/receipt stayed identical; public SourceVersionReader read the canonical original equal to the original72-byte body.

This controls the added filename/MIME identity boundary without changing source code, accepting arbitrary replacement files or performing any new HTTP request.

## Why the repair is sufficient at M2

Completed replay first validates bounded strict JSON/SourceRef/receipt/historicalcap, composes current bytecap, and verifies current canonical bytes through SourceVersionReader. Only then, under the existing same-ID mutex, it attempts cleanup of its own validated descriptor and exact capture filename. Raw identity is checked by bounded streamed SHA/size and before/after file observations; changed or unknown bytes are retained. Already-removed raw permits descriptor-only cleanup. Currentcap/SHA refusal therefore precedes deletion.

Failure to clean redundant staging is diagnostic and does not fabricate a failed source or withhold the already verified completed result. Filesystem diagnostics emit fixed reason/error_type constants, without paths, exception text or arbitrary exception-class strings. Next recover retries cleanup. Existing canonical original/result and historical actual receipt remain unchanged.

The completed projection remains <=64KiB, references the existing acquisition attempt and contains no source body, new task database, queue, permission or human approval. There is no new HTTP receipt or historical-usage replay into current delta. The earlier original three defect closures, result-write interruption and genuine actual-SHA checks remain supported by the preceding independent review; unrelated tests were not repeated solely to increase counts.

## Isolation, cleanup and acceptance limits

- Two owned TemporaryDirectory roots, `w4f-` and `w4i-`, including pytest cache, synthetic originals/catalogs and fault material, were removed on exit and verified absent. Pytest basetemp was within the existing Windows budget and not relocated. Loopback servers were closed; no cleanup touched preexisting caches, mFresh, another lane or production originals.
- Zero external HTTP/provider/model calls, zero paid calls. Only loopback networking; existing helper guards in-process external connects and production HTTP transport uses trust_env=false. No credentials/full environment/config values were printed or copied.
- Production `config/source_catalog.yaml` SHA and mtime stayed unchanged around the representative run. No implementation file, Git ref, installation, sealed company record, other lane or prior report was modified. Final exact HEAD, six source/test hashes and clean tracked worktree were rechecked.
- This review stops after the representative tests and necessary independent controls. No new defect was found within the assigned scope. Arbitrary external filesystem writers/power-loss behavior, every possible cleanup failure and real-company source/research outcomes were not exhaustively established.
- MAIN may integrate c839af +17e154a7 +68333bc3 with normal hooks and then verify exact remote CI. M3 original CN/HK/US runs and independent research-quality reviews remain outstanding. Historical lost original bodies remain lost; a new capture cannot be labeled recovery of their exact SHA.
