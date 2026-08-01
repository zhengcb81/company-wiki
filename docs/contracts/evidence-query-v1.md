# Evidence Query v1

## Scope

`company_wiki.source_catalog.EvidenceQueryService` is an exact, read-only access
boundary over an existing source-catalog database. It returns source material and
provenance only. It does not normalize, download, summarize, call an LLM, read a
whole raw binary, write StockWiki, or create research conclusions.

## Exact lookup

`lookup(source_id=..., locator=...)` requires:

- a canonical source URN (`urn:company-wiki:source:sha256:` plus 64 lowercase hex);
- a canonical `loc:v1` locator whose ordered segments round-trip through
  `EvidenceCoordinates` byte-for-byte.

The database key is the exact `(source_id, locator)` pair. Unknown sources,
unknown locators, source/locator mismatch, reordered or duplicate segments,
invalid coordinates, and noncanonical integers fail explicitly. The service never
falls back to a nearby paragraph or fuzzy path match.

## Result and integrity

Every result contains schema version `1.0.0`, the complete validated EvidenceSpan,
document identity/type/date/status, source hash/size/MIME, and deterministically
ordered location references for that same source and document. It does not return
summary or artifact bodies.

The persisted `span_json` is reconstructed with `EvidenceSpan.from_dict()`. Its
source ID, locator, span ID, raw text, parser/version/status, output hash, and source
content hash must agree with the denormalized catalog columns. Any conflict is an
integrity error rather than a partial answer.

## Bounded listing

`list_spans()` accepts exactly one canonical `source_id` or `document_id`, plus a
positive `limit` no greater than 500 and a nonnegative `offset`. Ordering is stable
by source, locator, and span ID. Empty exact identities return not-found rather than
silently changing the filter.

## Physical read-only behavior

The service does not instantiate writable `CatalogStore`. It opens the existing
SQLite database with URI `mode=ro`, `PRAGMA query_only=ON`, and a bounded busy
timeout. A static database with no WAL uses `immutable=1`, preventing lock/WAL/SHM
creation. If a WAL exists without its SHM, the service fails unavailable instead of
creating a sidecar; an existing WAL+SHM pair is read with ordinary read-only SQLite
snapshot semantics.

A missing database does not create its parent directory. Runtime contracts trace
SQL and reject DML/DDL, compare database/source size, mtime, and hash before and
after queries, and verify machine-readable CLI success/failure.

## CLI

- `evidence --source-id ... --locator ...` performs one exact lookup.
- `evidence-list (--source-id ... | --document-id ...) [--limit N] [--offset N]`
  enumerates a bounded page.

Both commands emit JSON. They use the same strict errors as the Python API and do
not call the fuzzy metadata `query` command.
