# W03 public official-source flow — interface 1

Base: c07852eaf2eb589675b73590e8fc494e1e02ef88. This document describes the W03 candidate, not installed main.

## Original import

```text
python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --operation import --config <isolated/config/catalog.json> --project-root <isolated> --input-file <absolute captured original> --request <import.json>
```

Library: `import_official_source(catalog, original=bytes, request=import_request)`.

`official-source-import-request/1` contains `request_id`, `source`, `content_sha256`, `mime_type`, `max_bytes`, `capture_receipt`.

- `source`: required actual `entity`, `document_kind`, `title`, `publisher`, `source_url`; optional `market`, `security_id`, `published_date`, `filing_date`, `fiscal_year`, `fiscal_period`, `period_end`, `language`, `canonical_entity_id`, `provider_document_id`. Unknown dates/year stay null. Language is en/zh/mixed/unknown/null.
- Kind uses existing SOURCE_FACT_KINDS; a PDF call stays investor_call_transcript, an official release normally investor_relations/news. Other-company material stays attributed to its own subject/publisher.
- MIME: application/pdf, text/html, application/xhtml+xml, text/plain, application/json. TXT/JSON must be supported actual transcript material.
- `capture_receipt`: required actual `capture_method`, `tool_name`, `tool_call_id`, timezone-aware `captured_at`, `response_bytes`, `content_sha256`; caller records its real event, not a synthetic HTTP success. SHA/byte count must match actual raw. Unknown publisher date is not filled from capture date.
- Max raw is 128 MiB and receipt 16 KiB. Caller can lower byte cap.

`official-source-import-result/1`: `status` imported_new|deduplicated, exact existing SourceRef `schema_version=2.0`, actual manifest `metadata`, `capture_receipt`, `download_events=0`. No canonical file path is returned. Input original is read-only. Shared CanonicalSourceWriter chooses storage and atomic registration. Same-SHA sidecar is never overwritten. This entry does not fetch or summarize; its download_events=0 records this local import only, not prior acquisition.

## Existing finite narrative request

Library: `prepare_official_narrative_request(import_results, batch_template=current_request_dict)` sets sources and delegates to existing NarrativeBatchRequest; it does not invent model/prices/budget.

```text
python -X utf8 -B scripts/narrative_batch_configured.py --llm-config <current readonly LLM config> --project-root <isolated> --catalog-config <isolated/config/catalog.json> --automation-db <isolated/AUTO.sqlite> --work-dir <isolated/work> --request <isolated/batch.json>
```

Every caller supplies existing request profile/limits/model/pricing. Configured launcher overrides model options through the existing Config loader. Local HTTP flag is only for the loopback fixture. The existing AUTO store owns tasks, leases, outbox, budget reservations and resume. No second DB or manual permission receipt is introduced. HTML DOM, PDF page, TXT/JSON byte locators use their existing versioned parsers. Carrier routing handles PDF calls through PDF parsing and detects unknown language from actual bytes.

## Consumer read: SourceRef → NarrativeRef → actual replay

```text
python -X utf8 -B -m company_wiki.source_catalog.narrative_transport_cli --config <isolated/config/catalog.json> --operation reference
```

stdin `{"schema_version":"narrative-reference-request/1","source_ref":<exact SourceRef 2.0>}`. stdout existing `narrative-ref/1`.

Read command same with `--operation read`; stdin `{"schema_version":"narrative-read-request/1","narrative_ref":<ref>,"as_of_date":"2026-10-09","expected_source":{"canonical_entity_id":null,"market":"US","security_id":"NVDA","document_kind":"investor_relations","fiscal_year":null,"fiscal_period":null}}`.

For Microsoft/OpenAI evidence use its own identity (not NVDA); The existing exact expected_source contract includes all six fields: canonical_entity_id, market, security_id, document_kind, fiscal_year, fiscal_period. Supply null for unknown/inapplicable fields (null is unconstrained, not a fabricated period). The CLI writes exact canonical narrative-bundle/2.0 bytes to stdout and the separate narrative-read-receipt/1 to stderr. Require exit 0, stdout byte_size/artifact_sha256 matching NarrativeRef, and stderr replay_status=verified. The bundle contains original SourceRef, actual evidence locators, source/parser/model versions and original-language summary; the receipt contains actual manifest and replay proof. Reference metadata alone is not consumed evidence. Failure/unknown/OCR gap stays explicit. Physical paths never cross this consumer boundary.

## Bounded discovery

```text
python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --operation discover --request <discovery.json>
```

`official-discovery-request/1`: `entity`, `start_date`, `as_of_date`, optional max_items(1..30), max_bytes(<=8MiB), max_seconds(<=120). Choose exactly one input mode:

- `urls`: 1..6 explicit official index URLs. Existing shared AcquisitionBudget and bounded HTTP stream account response bytes and deadline, no retries or paid API.
- `pages`: 1..6 actual captured index snapshots `{input_file:<absolute>,url,mime_type,capture_id}`; cumulative read is byte-bounded, no network.

Result `official-discovery-result/1`: candidates have metadata_only=true, is_business_original=false, materiality=not_assessed, actual index SHA/event/date. Known future/old-window items are excluded with reason. Notice is index_notice, not actual speech. Unknown date/dynamic Loading/limit/fetch failures are partial; no_documents_claimed is always false. Candidate URL must be captured and imported separately before business use. No recursive crawler, artificial latest period, or no-materials claim.

## Validation / current limitations

W03 uses fake/loopback HTTP only, no paid calls; MAIN owns real M2 and installation/merge. Current discovery parser accepts HTML/XHTML snapshots; unsupported/dynamic indexes explicitly remain partial and require existing browser/official API capture. Image-only PDF is PARSER_INCOMPLETE; no OCR or transcription is fabricated. Wider cross-run cache extensions remain their existing owner. No production original or sealed initial audit is changed.


## Actual HTML consumer golden

`html-bundle.json` is unmodified stdout from the public read CLI; `html-read-receipt.json` is unmodified stderr, and `html-read-request.json` is the complete six-field request. The actual producer emits source_class=filing, mime_type=text/html, language=en, transcript_lineage=null and transcript_byte_bindings=[]. Evidence uses cwp_document_normalization/1.0.0 and loc:v1/paragraph:1 with structured_value.source_locator=cwp-html-dom/1|n=0.1. The originally unknown PDF language is detected from actual bytes before the existing finite request produces en/zh/mixed. These are synthetic loopback engineering artifacts whose temporary catalog is deleted, not live supplier output.

Official capture timestamps retain their real timezone in capture_receipt; retrieved_at is converted to UTC. Independent supplied filing_date, published_date and period_end are retained using immutable provenance and the existing source-facts projection. Same-byte reuse returns the persisted publisher rather than a later caller's publisher declaration. Local discovery reaching the byte cap before remaining snapshots returns partial/byte_limit_reached. Exactly one discovery input mode is required.
