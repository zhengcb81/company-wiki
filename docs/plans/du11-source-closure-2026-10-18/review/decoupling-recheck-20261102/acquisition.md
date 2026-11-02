# Acquisition boundary recheck

Scope: current FF -> ET/provider -> CWP import, Sina statements and shared process limits. Read-only review; no product files, existing WIP, production config/DB/originals, provider network or paid service calls changed. Probe-only files are in this directory; the unique scratch directory is removed. This is a current-code recheck, not a re-run of the old acceptance label.

Versions: CWP `a591e48909b4b912adfaea54dc63bcad181269ef`; FF `508aba308cf5206c486119c446b66172debdc09a`; ET `003c1c065109d0b02c7bd4de09ad3e8461a99c0e`.

## Conclusion

The process/storage direction is substantially decoupled: FF uses six public operations through one connection adapter; original acquisition is ET/provider work, original admission/storage is CWP work; Sina fetching, normalization and dedicated-table storage stay inside CWP. No current FF production import of CWP implementation or SQLite access was found, and no reverse dependency in the inspected ET formal tool/worker/provider files was found.

However, the broad D3 claim is incomplete in two concrete places: the public transcript import decoder still derives its wire shape from internal dataclass fields, and optional subprocess stderr can still turn a complete native answer into a failure. Additional protocol-evolution/capacity limitations should be stated without pretending they are observed production data loss.

## P2 A1 — public transcript import is coupled to internal dataclass shape

- Owner: CWP `src/company_wiki/source_catalog/transcript_import_cli.py:72-92`.
- Production path: FF `scripts/transcript_tool_transport.py:989-1005` sends `source_request` and `candidate`; CWP `run_import` passes these to `_dataclass_from_object(SourceRequest/DownloadCandidate)`.
- `_dataclass_from_object` enumerates all init fields using `dataclasses.fields(cls)` and requires exact set equality. Internal optional fields thus become required wire fields without a wire-version change. Current FF's `_source_request` at lines 190-219 and `_candidate` at 823-864 mirror the whole current owner model.
- Reproduction: `probe_boundaries.py` obtains the real FF request dictionary; current type and bridge accept it. A subclass adding one defaulted internal field accepts the same dictionary directly, while the unchanged bridge rejects it with `source_request fields differ from schema`. This is a synthetic independent-evolution probe, not a claim that the hypothetical internal field exists today.
- Existing test blind spot: CWP `tests/contract/test_transcript_import_cli_e2e.py:119-120` builds requests from the current model's `to_dict()` and candidates via `asdict()`. This validates matching present versions but does not freeze an independently produced wire or test internal-model evolution.
- Fix: make the versioned import request decoder explicit about public fields and defaults, then translate into owner types. Use the existing documented SourceRequest projection and an explicit candidate projection; don't create a second identity store or shared mutable SDK. Private cache/implementation fields must not affect request acceptance. Preserve required source identity, request scope, bytes and original admission checks. Test literal FF-produced portable fixtures and a harmless owner-internal default addition.

## P2 A2 — optional process diagnostics can still veto a successful native result

- Owner: FF `scripts/ff_process_transport.py:21-24,137-150,288-289`; affected thin clients include `ff_financial_statements.py:166-189`, `fetch_filing.py` and `transcript_tool_transport.py:_run_json`.
- The shared default stderr cap is 64KiB. Exceeding it raises `OutputLimitExceeded`, and the statements client translates it into `upstream_error`; no log/diagnostic-only distinction applies here. Verified-open already explicitly uses `stderr_cap_bytes=None`, so this remaining behavior is inconsistent across public operations.
- Reproduction uses an explicitly configured independent command, not a CWP checkout. The child consumes stdin, prints/flushed a valid complete response to stdout, then emits 65,537 bytes of diagnostics. Identical request without those diagnostics returns complete; with them it raises `FilingFetchError(upstream_error)` caused by `OutputLimitExceeded`. All elapsed <1s in the final probe. No provider or actual source data used.
- Fix the shared owner: separate business payload from optional logs; spool/drain or explicitly retain diagnostics without making an arbitrary log-size cap a native failure. Preserve real resource controls for requested raw/HTTP reads, hard deadline, process-tree termination, malformed business JSON and incomplete stdin. Do not indiscriminately remove all transport resource controls. Add one focused real-child regression for valid native output + long stderr, including ET usage retention if shared behavior changes.

## P3 / coverage limitations, not observed production failures

1. FF `ff_financial_statements.py:39,171` hardcodes a 32MiB stdout allocation, with no caller/config option. A synthetic valid 33MiB response fails as expected from that allocation. This proves capacity is not exposed/propagated, **not** that current historical Sina data exceeds it or that an explicit larger response allocation is currently ignored (there is no such public field). CWP pages at 20,000 rows per statement with continuation. Decide and document the actual response-resource owner before changing it; don't conflate acquisition/network max_bytes with encoded local result bytes.
2. FF `ff_local_source_prepare.py:16-32` requires an exact receipt field set. Adding an `extensions` object turns ordinary not_found into upstream_error in the probe. That endpoint currently has no explicit extensions contract; classify as an additive-evolution gap, not a protocol-compliant current producer bug. `integration/README.md` broadly promises optional diagnostics in extensions, but current compatibility tests exercise raw/narrative readers, not all six FF operations. Either scope the claim accurately or define/test extensions consistently at the relevant versioned boundary.
3. CWP `financial_statements/provider_contracts.py:23-31` labels the port provider-independent, while `FetchedPage.normalized()` calls the Sina-specific `normalize_page`; `service.py:46-65` and replay inspect Sina's `result.data.report_list/item_source`. FF/CWP repository separation is correct; arbitrary provider replacement is not proven. Since this product currently requests Sina, this is an explicit generalization limit rather than a reason to add an unused provider. Future adapters should own raw-to-normalized decoding and replay hooks.

## Verified boundaries and legitimate checks

- `ff_company_wiki_connection.py` contains the legacy root/module/config-layout knowledge; explicit `WikiConnection` commands and cwd reach all six call sites. Missing configured operations do not silently choose a different producer.
- `ff_configuration.py` now validates a legacy root as a directory only; it does not inspect CWP catalog internals. A connection cwd need not be a CWP repo.
- FF supplies ET an actual raw-body/response allocation; `_import_fetched` forwards `import_max_original_bytes` independently of already-consumed network balance. CWP accepts explicit original budget, and raw verified-open is sized by SourceRef. Old constants still present as omission defaults are not, by themselves, a duplicate upper clamp.
- CWP/FF source bytes, source identity, period/as-of checks are appropriate owner/boundary work. ET formal worker owns actual provider requests, deadlines and unknown usage. No need for new manual review/approval chains.
- Sina provider and dedicated statement repository are inside the source owner; FF client consumes versioned JSON and doesn't import a Sina parser or write a database.

## Evidence and limitations

Run: `C:/Miniconda/python.exe -B -X utf8 .planning/decoupling-recheck-20261103/acquisition/probe_boundaries.py`.

Machine observations: `probe-results.json`. Scratch cleanup true; network calls zero. No whole-repo/full E2E or paid replay performed. Two preliminary probe fixture mistakes (missing self, then canonical_name) occurred before invoking boundary checks and were corrected; no product failures claimed from them. Native sibling Git reads initially hit sandbox permission denied; read-only supported host execution obtained HEADs. ET CodeGraph is uninitialized and FF index covers only two historical script files, so current explicitly located files/native literal searches were used; no index rebuilt. Shell wildcard-path errors were corrected by directory + `-g` filtering.

These findings do not erase the prior 39 passing combined cases; they show those cases did not test every promised independent-evolution and optional-observation boundary.
