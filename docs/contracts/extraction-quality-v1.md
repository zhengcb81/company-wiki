# Extraction Quality Diagnostic v1

## Scope

This contract is **source/extraction quality only**. It answers whether an
already cataloged source has a current, internally consistent extraction that is
usable, requires technical review, or is unavailable. It never represents an
accepted/rejected investment conclusion and contains no rating, valuation,
target price, position, or buy/sell semantics.

The only entry point is an exact canonical `source_id` or `document_id`. The
service never performs fuzzy matching. An unknown identity fails not-found; a
source mapped to multiple documents fails ambiguous; corrupt persisted identity,
artifact, or EvidenceSpan data fails integrity validation.

## Result states

- `usable`: the current normalizer artifact is completed, a source location is
  active, and validated parsed output is available without a review-class flag.
- `review_required`: extraction output exists, but source capture is incomplete,
  normalization is partial, an EvidenceSpan is partial/failed/quarantined, or a
  non-benign extraction flag is present. `ocr_used` alone records provenance and
  does not force review.
- `unavailable`: the current normalization is pending, unsupported, or failed;
  no usable evidence exists; no source location is active; or the source is
  quarantined/upstream-rejected.

Reason codes are returned in deterministic priority order. These states describe
technical source availability, not the truth or investment significance of any
claim.

## Validated inputs

The service reads the exact current
`source_catalog_normalizer@NORMALIZER_VERSION` artifact and validates:

- document, primary source, SHA-256 source identity, and location status;
- artifact status and bounded metadata (`parser_name`, `parser_version`,
  `quality_flags`, and recorded `span_count`);
- every persisted EvidenceSpan through `EvidenceSpan.from_dict()` plus its
  denormalized identity/parser/status columns;
- artifact span count, parser identity, and aggregate quality flags against the
  validated spans.

An integrity conflict raises `ExtractionQualityIntegrityError`; it is never
silently converted into a lower-confidence report.

## Body-free output

The report contains stable IDs, source/artifact status, parser/version, quality
flags, status counts, and bounded **locator references**. Each locator reference
contains only `span_id`, `locator`, `parse_status`, `quality_flags`,
`parser_name`, and `parser_version`.

The report never returns `raw_text`, `structured_value`, normalized Markdown,
artifact paths, artifact error details, source binary bodies, summaries, or
research fields. `locator_limit` defaults to 100 and is capped at 500; truncation
is explicit.

## Physical read-only policy

The service opens only an existing SQLite database with `mode=ro` and
`PRAGMA query_only=ON`. When no WAL exists it also uses `immutable=1`, which
prevents query-created sidecars. When a WAL exists, the matching SHM must already
exist or the service fails unavailable. It never initializes a catalog, performs
DML/DDL, reads source files, invokes normalize/download/LLM, or writes quality
decisions.

## CLI

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --document-id <document-urn> --locator-limit 100
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --source-id <source-urn>
```

The two identity options are mutually exclusive. Output is machine-readable JSON
under schema version `1.0.0`.
