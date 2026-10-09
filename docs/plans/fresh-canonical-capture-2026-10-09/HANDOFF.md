# W04 handoff: raw durability, bounded names and capture deadlines

## Ownership and tested state

Base ceac91e7, isolated worktree fresh-capture-20261009/company-wiki. Six source/test files changed plus this private engineering plan. No Dayu, production config/raw, sealed attempts, MAIN PWF, RF/FF/ET or CI/tools/hooks changes. Zero paid/external calls; real HTTP tests are loopback only. Final grouped M2: **88 passed /0 failed /0 skipped /46.79s**. Ruff and git diff check passed. See validation.json for exact tested file SHA and actual RED/GREEN evidence.

## Public additive interface

Existing import/discover remain compatible. Commands use `python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --config <isolated/current catalog> --request <request JSON> --operation capture|recover` with the current CWP src on PYTHONPATH as existing callers do.

Capture JSON schema `official-source-capture-request/1` fields: request_id; source (existing official source metadata, complete title/provider ID); mime_type; max_bytes (1..128 MiB); max_seconds (0..300); max_cost_usd (decimal text); optional expected_content_sha256. Shared in-process callers may pass the existing AcquisitionBudget. No provider, model, key or host authorization is invented. Official capture is for explicitly selected official URLs; configured filing providers and ET routing remain their proper owners.

Capture returns the existing pathless import result, actual capture_receipt, download_events for this call, and acquisition_usage delta. Redirect body bytes share the existing budget. HTTP status, times, SHA, measured request attempts and response MIME are real observations; no entire response headers, body or secrets appear in CLI diagnostics. Known SHA reuses verified canonical bytes, or resumes complete retained capture, with zero new GET and zero current acquisition delta. Without a byte pin a URL is not assumed permanently unchanged.

Recovery JSON `official-source-recovery-request/1`: no capture_id lists store-owned retained captures (IDs, hashes/byte size/status; no physical paths). With capture_id resumes exact stored bytes without another HTTP request. Complete original and immutable capture JSON are fsynced before import. Existing AcquisitionJournal points to failure/recovery material internally. The raw/fact/catalog/journal commit must complete before staging cleanup. Existing originals and immutable sidecars are reused and never rewritten.

Failures return exit2 and safe error_code. Post-capture errors carry capture_id; real HTTP errors carry acquisition_usage, acquisition_usage_complete and provider_started. Total deadline cancels actual async socket reads. Received partial bytes/receipt remain persisted; usage can be a lower bound and remains incomplete, never implicitly retried. Partial capture recovery refuses with `incomplete_capture_requires_new_request`. If the receipt's own disk write fails, bytes and safe journal observation are retained but inventory explicitly says `receipt_unavailable`; replay cannot be claimed until a real receipt is available. Impossible staging root is named before HTTP; impossible canonical root retains validated input for recovery after configuration repair.

## Storage changes and compatibility

Every new kind uses bounded content-derived physical names; full title/provider ID live in immutable metadata. UTF-16 path units reserve the source-sidecar atomic suffix and use a portable Win32 path budget. Existing files are not renamed or migrated. Provider import retains normal default staging cleanup. Official import uses cleanup_staged=False until fact/journal completion. Local imports use `_OriginalStorageReceipt` with no fabricated HTTP status and additive journal outcomes `imported_original`/`deduplicated_original`; old journal records still load. No second ledger or task queue.

## Tests and cleanup

Grouped command in validation.json. New suite covers deep root/multibyte entity/full long title across four kinds; exact different bytes; five import fault points; genuine loopback capture, slow trickle and stall; public CLI capture/recover; zero-GET reuse before and after registration failure; mismatched SHA; existing budget delta; journal and receipt-storage failures; one format parse per local import; public source reader actual bytes/SHA. Existing canonical/adapter/HTTP/official narrative suites remain green. Original historical bad-source early refusal tests remain unchanged; the old discard-on-storage-failure assertion is changed to exact raw+receipt preservation as required by W04.

All synthetic fixture directories named cwp-w04-*-20261009 under this lane's TEMP are removed after acceptance, with resolved containment and reparse checks; cleanup.json records actual bytes and absence. No mFresh, other lane or preexisting source directory is touched. No installation delta: this is CWP repository runtime/test code, not skill copies.

## MAIN follow-up

Cherry-pick the delivered commit with normal hooks. Independent review and integration use this exact write set; native M3 real-company reruns remain MAIN-owned. Replace future executor one-off urllib download with capture CLI for explicit official originals. HK GMTN known full SHA should reuse without GET. Historical Lam bytes are genuinely lost; any current peer capture is new evidence, never claimed to reconstruct the old exact body. No overall research or company PASS is claimed from local M2.
