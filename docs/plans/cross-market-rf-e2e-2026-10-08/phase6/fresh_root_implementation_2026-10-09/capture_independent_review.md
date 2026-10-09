# W04 independent implementation review

Date: 2026-10-09. Target: `c839af5857dc0d9720a3127f1a2d3028493b50f7` at `C:\Users\郑曾波\.codex\worktrees\fresh-capture-20261009\company-wiki`. Reviewer: independent RF engineering lane, with no W04 source ownership.

**Verdict: M2 needs repair before unconditional acceptance.** Original durability, bounded naming and cancelable HTTP mechanisms have supporting evidence; three extra public recovery/validation contracts fail. Actual-company M3 was not run.

## Actual review and execution

- Read the handoff, validation/cleanup evidence, relevant source and new contracts. Exact delivered HEAD matched; all six recorded source/test SHA-256 values matched after review; tracked worktree stayed clean. Normal OS neighboring Git reads were required because sandbox Git status reported that it was not a worktree.
- Independently executed `python -X utf8 -B -m pytest tests/contract/test_official_capture_recovery.py -q --tb=short --basetemp <owned TEMP>/pytest`: **24 passed, 0 failed, 0 skipped, 17.67s**. Actual Windows run, including genuine loopback sockets. Repository basetemp hook relocated the requested fixture root to its bounded TEMP root and explicitly reported cleanup `removed: true`.
- Implementer's separate 88-pass grouped result was inspected; it was not represented as an independently rerun 88-test suite.
- Extra controls below used unchanged public APIs and the delivery's helper `lake`, `BODY`, `import_request`, `capture_request`, `loopback`, `retained`, `_cli`, with pytest.MonkeyPatch, in a separate TemporaryDirectory. Only one loopback GET was made. Synthetic originals and the one intentionally invalid descriptor were entirely in that owned TEMP root and were removed on exit.
- No implementation source, old original, production config, RF delivery, commit or push was changed. No real provider/model/paid calls; no credential/configuration values inspected. No successful XML or forecast output retained. The normal pytest process may maintain ignored cache; no preexisting cache was deleted without ownership proof.

## Confirmed defects

### IR-W04-01 — same capture ID cannot be retried after successful recovery [P2]

Mechanism: [successful cleanup](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:372) deletes staged body and descriptor after catalog/fact/journal success. [load retained](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:403) requires that descriptor; [public recovery](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:446) has no completed-capture resolution path. Locations refer to the reviewed commit.

Actual control: fault fixture copy once → import fails with capture ID → remove fault → `recover_official_source(capture_id=ID)` twice. First: `imported_new`. Second: `OfficialSourceError: retained_capture_receipt_unavailable`.

This fails the assigned idempotent recovery contract when the first successful response is lost. Canonical bytes are preserved; this is not a claim of raw loss after successful commit.

Repair contract: durably resolve completed capture ID through the existing acquisition journal/source identity, verify canonical bytes and immutable actual observation, return the same pathless SourceRef on repeated recover, zero new GET and explicit zero current acquisition delta. Keep successful cleanup; do not introduce another task/capture database.

### IR-W04-02 — retained same-SHA capture retry bypasses current max_bytes [P2]

Mechanism: [retained SHA branch](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:498) imports with the old stored request rather than checking the current cap. [canonical SHA branch](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:483) reads `cap+1` and validates the current cap.

Actual control: genuine loopback captures BODY=**72 bytes**; a copy fault leaves complete raw plus actual receipt retained. Retry same expected SHA with current **max_bytes=10**. Observed: `imported_new`, SourceRef byte_size=72, download_events=0, total loopback GETs=1. Retrying the exact same 10-byte request after registration takes the canonical branch and refuses `source_byte_limit`.

Thus current input acceptance depends on previous registration success. Zero-GET reuse and zero new acquisition delta work; duplicate HTTP charging was not observed. The defect is inconsistent current-request validation.

Repair contract: capture retry must enforce current cap/expected byte identity before consuming a retained body, retain old raw/receipt on refusal, and avoid another GET or rewriting the historical receipt. Explicit recovery may use the original request semantics; capture retry must consistently honor its current request.

### IR-W04-03 — invalid persisted receipt type causes inventory/CLI traceback [P2]

Mechanism: [JSON load](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:409) calls `.get` before validating top-level object type. [inventory catch](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_flow.py:435) handles OSError/ValueError/KeyError. [safe CLI catch](C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki/src/company_wiki/source_catalog/official_source_cli.py:150) does not handle AttributeError.

Actual control: in the owned synthetic fixture only, change a retained descriptor to valid JSON `[]`, leaving raw untouched. Inventory: `AttributeError: 'list' object has no attribute 'get'`. Public recover CLI: exit **1**, traceback present, no JSON failure envelope. Fixture-root path was absent from stderr; implementation stack/location was exposed.

This specifically proves invalid top-level type handling, not that normal writes produce `[]`. Missing receipts and syntax-invalid/truncated JSON have other existing paths.

Repair contract: validate descriptor and nested request/receipt object shapes before member access, raise named OfficialSourceError, mark inventory unavailable, and return safe JSON exit2 without deleting raw. Add beside the existing receipt-write failure test.

## Reproducible control outline

Import unchanged helpers from `tests/contract/test_official_capture_recovery.py`; use TemporaryDirectory and MonkeyPatch.context.

```python
# 1: capture ID retry
patch.setattr(canonical_writer.shutil, "copyfile", fail_OSError)
# import_official_source(... BODY, import_request()) -> exception.capture_id
# Remove the patch, then call recover_official_source(... capture_id) twice.

# 2: current cap parity
# With loopback, patch copyfile during capture_request(url) to retain BODY.
retry = capture_request(url, expected=sha256(BODY).hexdigest())
retry["max_bytes"] = 10
# capture_official_source(... retry) imports 72B; repeat refuses source_byte_limit.

# 3: receipt shape
# After faulted local import, only inside that owned TEMP fixture:
retained(catalog)[0].write_text("[]", encoding="utf-8")
# list_retained_official_captures -> AttributeError
# _cli(root, recovery_request_with_ID, operation="recover") -> exit1 traceback
```

Actual observations were sent to MAIN and the implementer; the implementer owns repair in the original W04 worktree. This review report remains separately owned.

## Supporting evidence and limits

| Contract | Mechanism/independent observation | Assessment |
|---|---|---|
| Win32 bounded name, full metadata | canonical_writer.py:437 uses content-derived names, UTF-16 path units and reserved provenance atomic suffix. All four deep-root/document-kind tests passed and preserved full title/provider ID. | Supported locally |
| Durable capture before import | official_source_flow.py:246 write-once raw+sidecar and fsync precede import. cleanup_staged=False keeps raw through fact/journal completion. | Supported locally |
| Copy/rename/provenance/catalog/fact failures | Five rerun fault contracts preserved exact body/receipt and resumed successfully; unrelated sentinel unchanged. | Supported locally |
| Journal/receipt persistence failure | Primary error, raw and actual usage retained; receipt-unavailable capture refuses false recovery. | Supported locally |
| Same SHA zero GET, different bytes | Real loopback canonical/retained reuse and distinct immutable-body tests passed. IR-W04-02 is a separate current-cap gap. | Supported with defect |
| True HTTP deadline/shared budget | Trickle and stalled read tests passed. Async wait_for bounds connection/body work by request duration and existing remaining deadline; existing transport charges raw bytes once. Failure preserves lower-bound/incomplete usage; shared-budget delta test passed. This verifies network acquisition deadline, not hard cancellation of arbitrary filesystem work. | Supported locally |
| Local import truthfulness | _OriginalStorageReceipt has no HTTP status; imported_original/deduplicated_original journal outcomes and legacy loading pass; MIME parser executes once. | Supported locally |
| Repeat recovery, malformed receipt refusal | Three independent controls above fail. | Needs repair |
| Original CN/HK/US company M3 | Not executed here; fixtures do not recover genuinely lost historical bodies or establish company/research PASS. | NOT_RUN |

## Concentrated follow-up

Keep the passed W04 suite and add these three controls. Require successful same-ID recovery, same SourceRef and zero current usage; retained/canonical cap parity without a new GET or changed receipt; safe unavailable/exit2 handling for invalid receipt shapes. Rerun through public CLI plus loopback, then independently review the exact new commit at M2. Real-company M3 and its independent source/research verdicts remain outstanding.
