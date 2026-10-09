# Explicit bounded local source preparation

Code: 7ced0b50b8cabb5a8becc50374cd6f8216d212ff.

## Public command

`python -m company_wiki.source_catalog.local_prepare_cli --config CONFIG --request -`

`--request` accepts stdin `-` or a JSON file, at most 128KiB. Optional `--identity-cache-dir` selects an existing verified security-master cache; otherwise catalog/security_master. The configuration is supplied explicitly. No provider, HTTP or model operation exists in this command.

Request:

```json
{
  "schema_version": "local-source-prepare-request/1",
  "source_request": {
    "schema_version": "1.0", "entity": "Acme", "market": "US",
    "security_id": "ACME", "document_kind": "regulatory_filing",
    "fiscal_year": 2026, "fiscal_period": "Q2",
    "as_of_date": "2026-10-09", "allow_download": false
  },
  "limits": {"max_candidates": 64, "max_bytes": 134217728, "timeout_seconds": 30}
}
```

`source_request` accepts the existing `SourceRequest.to_dict()` fields. `allow_download` cannot make this command download. Optional registrations is a list of `{root_id, relative_paths}` explicit configured groups, at most16 scopes and total paths within max_candidates. `limits` defaults to16 candidates/256MiB/30s; allowed ranges1..256 candidates,1..1GiB, finite deadline>0..600s. The local verification and metadata read budget is shared across proof/replay and bounded discovery. Existing storage registration and public query/reader guards remain responsible for those stages.

Result has exactly eight fields:

```json
{
  "schema_version": "local-source-prepare/1",
  "status": "ready", "reason": "local_source_reconciled",
  "source_ref": {}, "blocks_download": false,
  "operations": [], "diagnostics": [], "download_events": 0
}
```

`source_ref` is the unchanged SourceRef2.0 DTO (or null); no physical path/root/location/bundle fields are exposed. Status is ready/not_found/blocked/unavailable/ambiguous. Named semantic outcomes exit0; malformed request failures return the same eight-field refusal and exit1. `ready` should be followed by the existing source query/read. `not_found` means no matched existing local period and may continue the caller's authorized acquisition; blocked/unavailable/ambiguous or `blocks_download=true` is a named local gap, never permission to fetch the same raw. Every result has download_events=0.

## Python/internal responsibility

`prepare_local_source(catalog, request: SourceRequest, *, identity_cache_dir=None, limits=None, registrations=())` is the explicit writer composition. Default source-query stays read only.

`restore_document_facts(catalog, *, ref, facts, evidence, retirement_observation, budget=None, fact_replay=None)` is an internal atomic API. `ref` is existing SourceRef2.0, observation comes from `observe_document`. Under existing CatalogOperationLock it rechecks exact inactive bytes and trusted retirement, optionally replays facts, then rechecks observations and commits sourcefacts projection/location restoration/audit together. Changed observations return named unavailable; any transaction failure rolls back all changes. This internal API is not a new public permission DTO.

No edits to source_reader, source_reader_cli or source_availability. Availability receipts remain MAIN-owned. Local meta.json filing_date is independent publication evidence bound to exact original hash/size/accession; it is not asserted as an archive/capture-time proof.

## MAIN FF dependency tested

Actual entry: ff-diagnostics/scripts/fetch_filing.py, HEAD a1e97fa462f6fc381f18ce39641224310c7228a8. Only explicit v2 reuse_only query-miss invokes localprepare; active hits retain zero extra preparation. fetch_if_missing/latest invoke the existing ensure composition, which prepares internally. The script SHA is pinned in actual_originals_receipt.json. FF remains a separate package for MAIN to merge.
