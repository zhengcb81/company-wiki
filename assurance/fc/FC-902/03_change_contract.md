# FC-902 Change Contract — SourceBundle 进入 resolver 生产响应

> Owner: company-wiki · Base triplet: revenue `ca213c9` / filing `81d9cd9` / wiki `16bf9b2`
> Dependencies: FC-901 (accepted) · Scenario IDs: MIG-03 (rerun idempotent), AR-related bundle consistency; new bundle-in-envelope behaviors

## Intended behavior delta (observable)

`query_source_bundle` ceases to be a test/CLI island: the production resolve
path (CLI resolve/ensure + close-gap re-resolve) attaches a **snapshot-consistent
SourceBundle** to the `ResolutionEnvelope` whenever the resolution reused a
document. The envelope's `bundle_status` becomes `available` (with
`bundle_hash` + `bundle` dict) instead of the FC-704-era hardcoded
`unavailable`; `unavailable` remains only when no bundle can honestly be built.

## Snapshot consistency (the core invariant)

The bundle is built from the SAME document bytes the handle claims:
`query_source_bundle(..., expected_content_sha256=<handle.content_sha256>)`
fails closed — if the catalog `sources.content_sha256` differs from the handle's
content hash, NO bundle is served (`None`), never a bundle built from other
bytes. The envelope keeps carrying the same `policy_hash`/`activation_epoch`
pinned at request start; bundle and handle share that context.

## Unknown artifact role fails closed

`build_source_bundle` gains a role gate: an artifact whose `artifact_role` is
not in the frozen known set (`ROLE_DEPENDENCIES` keys: normalized, markdown,
summary, sections, consumer_analysis) becomes an invalid handle with reason
`artifact_role_unknown` — never a valid handle, never silently dropped.

## Canonical generator registry (single source of truth)

`GENERATOR_REGISTRY` (in `source_bundle.py`, versions from `models.py`):
`source_catalog_normalizer 1.0.0`, `source_catalog_llm_summary 1.0.0`,
`source_catalog_section_extractor 1.0.0`. Production bundle builds default to
this registry instead of a per-caller ad-hoc dict.

## Allowed symbols / files

- `src/company_wiki/source_catalog/source_bundle.py` — GENERATOR_REGISTRY +
  KNOWN role gate in `build_source_bundle`.
- `src/company_wiki/source_catalog/resolver.py` — `ResolutionEnvelope` gains
  `bundle_status=available|unavailable` semantics + `bundle_hash` + `bundle`;
  `build_resolution_envelope(..., bundle=None)`.
- `src/company_wiki/source_catalog/service.py` — `query_source_bundle` gains
  `expected_content_sha256` (fail closed); new `bundle_for_resolution()`
  production helper (production caller of `query_source_bundle`).
- `src/company_wiki/source_catalog/cli.py` + `close_gap.py` — wire the bundle
  into the two CLI envelope paths and close-gap `_finalize`.
- NEW `tests/contract/test_fc902_bundle_in_resolver.py`.

## Forbidden changes

- Changing resolver match logic, journal reconciliation, or outcome mapping.
- Serving a bundle whose source hash ≠ the handle's content hash (must fail closed).
- Silently dropping unknown-role artifacts (must be invalid handles with reason).
- Faking `bundle_status=available` with an empty/None bundle.
- Any write to the catalog/roots in the resolve path (bundle build is SELECT-only).

## Expected call-edge delta

- NEW production caller edge: `query_source_bundle` ← `bundle_for_resolution` ←
  CLI resolve/ensure + close-gap `_finalize` (CodeGraph production caller >= 1).
- No legacy edge removed.

## Side-effect budget

| Effect | Budget |
|---|---|
| catalog writes | 0 (resolve/envelope/bundle paths are SELECT-only) |
| external root writes | 0 |
| file reads | artifact files only (bundle validation hash check, per valid artifact) |
| deletions | 0 |

## Rollback

Additive contract fields + new helper; revert = revert commits. No data written.

## Diff budget

~5 touched files + 1 new test file (≤350 lines total). Exceeds → split.
