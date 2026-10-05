# Selected narrative evidence views v1

This source-only interface lists, looks up and searches a **single pinned final**.
It does not search the full lake or model summaries. Source discovery still uses
SourceRef v2; callers obtain a NarrativeRef with the existing `reference` operation.
Existing `reference` and `read` request/receipt schemas and exact bytes are unchanged.

## CLI and input

Module: `company_wiki.source_catalog.narrative_transport_cli`. All operations take
the existing `narrative-read-request/1` JSON on stdin, containing NarrativeRef,
`expected_source` identity/period constraints and `as_of_date`. No physical path
appears in the request; `--config` selects the storage adapter in the producer.

| `--operation` | Options | Result items / total |
|---|---|---|
| `evidence-list` | `--limit N --offset N` | Complete EvidenceSpan objects in final order / all spans |
| `evidence-lookup` | Exactly one `--span-id ID` or `--locator LOCATOR` | Exactly one EvidenceSpan / 1 |
| `evidence-search` | Required `--query TEXT`, optional limit/offset | Existing BM25 selected-text group hits / all matching groups |

List/search default limit 100, offset 0; limit 1–500, offset nonnegative. Query is
nonblank and at most 4096 UTF-8 bytes. Exact anchors are trimmed nonblank strings
at most 1024 UTF-8 bytes. Lookup accepts no pagination/query options. Filters on
`reference`/`read`, irrelevant filters, invalid numbers and unbounded strings are
rejected before catalog/raw access. A locator is meaningful **within the supplied
artifact version**; bare coordinates from another parser/version are not remapped.

## Verification and output

The existing NarrativeTransportReader verifies the exact artifact SHA/size,
current source SHA, identity, period, publication/as-of and policy. It replays **all
final locators**, including spans outside the requested page. Query filtering
occurs after that verification. A newer final never silently replaces the pinned
version. Technical `needs_review`/partial coverage is visible diagnostic data.

Success: exit 0; stdout is canonical UTF-8 JSON without an appended newline:

- `schema_version`: `narrative-evidence-view/1`;
- `operation`, pinned `narrative_ref`, pathless verified `manifest`, `source_metadata`;
- complete `selection`, `quality_status`, `versions`;
- `total`, effective `limit`, `offset`, `items`.

List/lookup items use the existing EvidenceSpan wire. Search items use the existing
NarrativeEvidenceHit wire: source ID/SHA, selection status/coverage, group/member
IDs and locators, snippet, BM25 score, matched terms and phrase match. Matching and
ranking use selected **original text**, not generated summary claims. A group may
contain several spans; search total is group count, list total is span count.
The index/group adapter exists only in query memory and writes no files/database.
Output is capped at `BUNDLE_MAX_BYTES + MAX_RECEIPT_BYTES` (1,327,104 bytes).

Stderr has one JSON line, at most 16 KiB, with schema
`narrative-evidence-read-receipt/1`, status `ok`, `view_sha256`, `byte_size`,
`narrative_ref`, `as_of_date`, `source_read_policy_sha256`, `replay_status` and
`locator_count`. SHA/size refer to **stdout view bytes**, not the original final.
Consumers check both; locator count covers the whole final, not the result page.

Failure: exit 2, empty stdout, existing bounded transport refusal receipt
`narrative-read-receipt/1`. Identity/as-of/raw/artifact failures retain their
existing named reason. Unknown exact evidence gives `narrative_evidence_not_found`;
multiple exact matches give `narrative_evidence_ambiguous`; oversized view gives
`evidence_view_too_large`. No fuzzy fallback, legacy span fallback or implicit job.

`skipped_no_narrative` gives explicit zero items and zero matching groups; lookup
is not-found. Raw with no visible final remains reference not-found and extraction
quality `metadata_only`; requesting retrieval does not parse/download/call a model.

## Legacy retirement and node tests

Source-catalog `evidence`, `evidence-list`, `sections-list` and public
EvidenceQueryService exports are retired. The explicit historical module
`company_wiki.source_catalog.evidence_query` remains for fixture read compatibility;
it is not the canonical runtime reader or a requirement to retain all old spans.

Run `tests/integration/test_s5_narrative_evidence_view.py` for actual three-job
publication, subprocess list/lookup/search, Chinese/English, policy skip, pinned
older/new partial versions, hash/as-of failures and isolated scratch restoration.
Its Microsoft sample uses immutable original TXT bytes with synthetic fixture
identity; it is a replay oracle, not a verification of Microsoft company identity.
Existing transport CLI contracts separately freeze the original reference/read
wire. These major-node tests do not add a long daily CI or per-document review.
