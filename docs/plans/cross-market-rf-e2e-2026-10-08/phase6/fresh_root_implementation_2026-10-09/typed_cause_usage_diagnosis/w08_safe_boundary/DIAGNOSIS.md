# W08 read-only diagnosis — RC14 / RC25

Date: 2026-10-09. Scope: existing CWP acquisition failure → FF public CLI → RF client/source preparation. This package changes no product code, configuration, original, installed skill, Dayu, IQS, audit run or shared PWF. The independent implementation will use MAIN-allocated FF/RF worktrees only. It does not claim M3.

## What was actually read

- Frozen `fresh_root_remediation_2026-10-09/IMPLEMENTATION.md` W08 and `issue_root_matrix.json` RC14/RC25, all linked findings and their acceptance conditions.
- Original three fresh `reports/fetch.json`: CN SHA `ff0874022ea44308f866755554834f6d3119341aba6bcbea8fb3892e65a5e4e1`, HK `9d4655497d61dbffccca39695f891114ea169e2424f7aa89fad8d08a91e81ce4`, US `c45ec33ba2dd1cf7474efa0766d37028c161c660df73502dcff2e238076c2f07`. These match the frozen matrix. CN's direct official GET deadline belongs to W04 and has no proven RC14/25-specific loss; don't invent a CN failure.
- HK FETCH-005: missing H1 metadata was expressed as generic not_found; unsupported_language was already correctly differentiated. US FETCH-001/004: current FF carries local_metadata_gap in reason text, RF exposes generic source_blocked. US FETCH-005 and actual_usage.json: first failed provider requests/bytes/cost remain unknown. HK STORAGE-007 and US STORAGE-006 share historical recorder gaps with W11; later zero usage cannot repair historical missing bytes/time/cost.
- Current CWP `acquisition_failure.py`, `download_budget.py`, `source_operation.py`, `operation_contract.py`, `operation_projection.py`, `cli.py`, `source_query_cli.py`, `source_reader.py`, `local_reconcile.py` and existing failure responsibility tests. CodeGraph identified operation projection and AcquisitionBudget; consumer index lacks new symbols, so their known exact files were read.
- FF `ff_provider_cause.py`, `filing_contracts.py`, `fetch_filing.py`, `ff_v2_envelope.py`, `ff_local_source_prepare.py`; RF `filing_upstream_cause.py`, `filing_fetch_client.py`, `source_preparation.py`, and existing cause tests.
- MAIN's published W04/W07 integration receipt: W04 final source `68333bc3`, main merge `410c456f`; FF W07 `44c778b4`, ET `c91f5f54`, actual configured FF→ET→CWP independent control first requests=1/bytes=862, two subsequent calls=0. W04 capture/recovery usage preservation and W07 ET measured request counters are separate working contracts; no need to replace them.

## Reproduction and retained facts

`reproduce.py` launches real CWP, FF and RF public CLIs, with synthetic security master/originals and a provider that performs **no HTTP**. It loads only the literal existing CWP hermetic provider fixture, not production configuration or secrets. Each layer is a separate actual subprocess. Injected FF wire controls are explicitly labelled: actual RF client/preparation, synthetic upstream wire. `observations.json`, `boundary-controls.json`, `wire-controls.json` retain arguments, exact safe response, exits, measured durations and cleanup. Synthetic leak values are replaced by `[SYNTHETIC_REDACTED]` before persistence, with the measured boolean retained.

The first text fixture did not qualify as an annual report and legitimately produced not_found. It is kept in observations.json and **not** used to prove metadata-gap failure. The corrected PDF-like annual path with explicit kind/period in boundary-controls.json produces the real local_metadata_gap. It has no publication date and is intentionally not a financial extraction fixture. This is fixture correction, not changed product expectations.

| Path | Current actual behavior | Contract result |
|---|---|---|
| Known discovery failure | CWP full operation DTO: 17 bytes/$0.01, started=true, complete=true. FF/RF safe six-field cause survives. Numeric usage absent after FF. | Cause GREEN; usage RED |
| Unsupported language | Exact safe unsupported_language survives CWP→FF→RF. | GREEN; no account/entitlement inference |
| Malformed usage bool count | CWP retains started=true, complete=null, acquisition_usage=null; RF null survives. | GREEN; never unknown-as-zero |
| Invalid receipt after discovery/fetch | CWP validation_failed, cumulative92 bytes/$0.02, complete=true; FF/RF keep code, lose numbers. | Usage RED |
| Provider timeout after checkpoint | CWP adapter_timeout, lower bound36 bytes/$0.03, started=true, complete=false; FF/RF keep flags, lose numbers. | Usage RED |
| Legitimate no candidates | CWP pathless not_found has no operation usage receipt, even though synthetic discovery reported17 bytes/$0.01. FF/RF cannot infer HTTP or cost from status/count. | Producer observation limitation; preserve honest unknown, no consumer-made receipt |
| Existing annual missing publication | CWP query miss then local_prepare blocks with local_metadata_gap. FF reason text carries it; no safe cause. RF error_code=upstream, no typed metadata cause or counts. | RED |
| Truly absent local annual | No provider invoked. FF not_found/no_registered_local_source, calls=3/downloads=0. RF has no structured subtype/counts. | RED distinct from metadata |
| Synthetic safe CWP/FF failure | Known cause preserves all bool/null observations to RF. CWP's malicious provider message is not echoed by FF/RF. | GREEN |
| Synthetic FF top-level error, non-JSON stderr, exit0 failed v2 reason | Actual RF clients echo secret-bearing URL/message in final stderr in all three controls. | RED; safe cause can coexist with unsafe human error |
| FF selected source followed by actual CWP reader refusal | Actual RF error names reader_unavailable but loses already observed FF calls=2/downloads=1. | RED; don't report a fresh pre-provider zero |

Numbers above are **synthetic operation measurements**, not actual paid costs. Each probe is a distinct operation; don't aggregate four probes into one operation. FF `calls` counts CWP subprocesses, `downloads` counts committed original downloads; neither is an HTTP request count. For the no-HTTP provider the zero HTTP fact is fixture code, not inferred from `calls` or a missing receipt.

`check_expectations.py` evaluates retained observations against frozen contracts, intentionally returning nonzero on unchanged code. The exact RED/GREEN counts are in contract-red.json. Existing focused responsibility suites remain green: **CWP48 / FF26 / RF14 = 88 passed, 0 failed, 0 skipped**. Logs and `current-checks.json` retain actual timings. This explains why previous tests didn't catch the issue: they assert cause's six fields and rejection shapes, not numeric usage/phase/count continuity or RF raw-text fallback isolation.

## Actual loss points

1. FF `_run_company_wiki_json` consumes CWP stderr. `diagnose_stderr` validates the seven-field acquisition_failure but reduces it to `(code,started,complete)`. `FilingFetchError` has only upstream_cause; actual numeric operation usage is then inaccessible to its emitter. Returned failure GAPs have the same reduction in `_pathless_operation_gap`. This is transport projection loss, not accounting failure.
2. FF `_run_source_query` and `ff_local_source_prepare._validated` convert CWP result into an exception string/stage, without finite cause construction. Normal no-candidate `_pathless_operation_handle` has no machine source subtype. The local metadata reason belongs to this consumer boundary; don't relabel it as an acquisition provider failure.
3. FF v2 `error_envelope` receives code/retryable/stats/cause only; unlike v1, it never receives existing stage/attempts. The stage is lost before RF, so fixing RF alone cannot recover it.
4. RF `_ClientError` and `_emit_error` carry only cause/status/code/retryable/candidates, dropping CWP operation usage and existing FF calls/downloads/stage/attempts. `_run_filing_fetch` then carries only cause. Reader failures after successful FF response have no existing result observation attached at all.
5. RF `resolve_filing_result` copies `payload.error`, v2 `filing.reason` and raw fallback stderr into exception text; `_run_filing_fetch` copies its stderr tail, and the CLI publishes it. A cause validator by itself does not sanitize that human text.
6. Current producer normal empty result lacks operation usage projection. This diagnosis does not ask a consumer to fabricate it, expand CWP write set, or rewrite the budget. Record it as explicit producer unavailable/unknown; MAIN can consider one additive producer projection later if a real receipt is required. Historical losses remain historical.

## Minimum common implementation, in order

1. Freeze one additive consumer interface with MAIN; preserve existing six-field `filing-upstream-cause/1` shape, legacy status/error_code/retryable/exit semantics and owned accounting. Add only finite operation/reason vocabulary required by current local_prepare/query/missing/schema boundaries. Keep bool/null proof and never turn arbitrary message into a machine code.
2. First add TDD consumers: real safe producer DTO through FF nonzero/GAP/v1/v2 then RF; known17 and lower-bound36 with exact decimal cost; null malformed usage; after-provider import/journal/cleanup code controls; local metadata vs true missing; invalid schema; process deadline; counts vs HTTP; secret-laden raw text; successful-selection reader failure retaining known counts. Original CWP88 responsibility behavior remains protected. Don't write tests asserting a new implementation literal.
3. FF: strictly validate/project the **existing CWP acquisition-failure/1** as an optional observation beside cause; attach it to exception, v1 error and v2 filing failure/GAP. Forward existing stage/attempts in v2. Convert documented local/query reasons into finite safe cause only; unknown or malformed reason remains named unknown with honest nullable flags. Bounded process transport, budget, retries, credential launch and transcript companion behavior stay unchanged.
4. RF: one pure failure decoder/projector used by both client and source_preparation. Add optional safe acquisition_failure and measured FF stage/attempt/count fields to exception/error projection. Preserve observed FF counts on downstream reader/record construction failure. Never recalculate producer cumulative usage, duplicate a charge, infer HTTP from process counts or replay a charged operation.
5. RF human error text: replace untrusted raw error/reason/stderr with bounded fixed messages plus the validated **real cause/stage**, not blanket unknown. Unknown bad wire receives a fixed malformed/upstream diagnostic; known causes continue exact subtype. No key registry lookup or printing environment is needed.
6. Run concentrated responsibility sets once after coherent implementation, then actual public FF→RF synthetic cross-process controls. One independent major-node review checks finite wire, accounting completeness, no-leak, compatibility and original fixture intent. Normal hooks commit source/PWF. MAIN handles merge/push/selected installation and M3 original-company attempts. No small-node human signature/canary/private/public permission is added.

### Exclusive writes

FF worktree MAIN allocated: `C:/Users/郑曾波/AppData/Local/Temp/ff-fresh-transcript-launch-20261009`, base44c778b4, branch codex/fresh-typed-cause-20261009. Source: ff_provider_cause.py, filing_contracts.py, fetch_filing.py, ff_v2_envelope.py, ff_local_source_prepare.py; focused tests and own docs/plans/fresh-typed-cause-2026-10-09. Add a pure consumer projection helper only if it reduces duplicated validation. No transcript credential/provider/core process edits.

RF worktree MAIN allocated: `C:/Users/郑曾波/AppData/Local/Temp/rf-fresh-dag-20261009`, base5acad6a1, same branch. Source: filing_upstream_cause.py, filing_fetch_client.py, source_preparation.py; focused tests and own docs/plans/fresh-typed-cause-2026-10-09. No forecast/DAG/output, installed copies, shared CI/hooks or audit-run code. MAIN independently owns W11 outer recording; safe receipts are inputs to that recorder, not a competing ledger.

## Limits and cleanup

All owned cwp-w08-readonly-* and cwp-w08-current-checks-* roots are absent after execution; receipts contain actual absence. CWP test conftest also created/removed its own cw-pytest-basetemp root; the cleanup log explicitly says removed=true. Production originals/configs/keys were never read for reproduction or changed. Zero external HTTP/paid calls; no installation delta. Initial failed US supplier usage/cost and overwritten HK/US authoring bytes/time remain unknown. This diagnosis is enough to implement shared consumer fixes; it is not final provider entitlement, full source coverage or company research acceptance.
