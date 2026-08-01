# Page-aware PDF Parser Adapter v1

## Purpose and boundary

`company_wiki.parser_adapters.adapt_pdf_pages` is the pure canonicalization core
between a page-level PDF runtime and `ParserResult`. It consumes explicit physical
page snapshots and never opens a PDF, imports PyMuPDF/legacy scripts, calls an LLM,
or writes raw, derived files, databases, Wiki, review state, or StockWiki.

The pure core is **not production-wired** directly into a worker or scheduler and
still owns no file I/O. CW-2.20 separately wires the source-catalog PyMuPDF fallback
to build strict page snapshots and call this core. That wiring was validated only
with synthetic PDFs and temporary catalogs; it did not run the production backlog
or restart the production worker.

## Strict input

The caller supplies a verified `application/pdf` `SourceManifest`, a semantic
`parser_version`, and a non-empty sequence of page mappings. Each mapping has exactly:

- `page_number`: explicit physical page, contiguous and 1-based;
- `text`: NFC text with LF line endings;
- `tables`: page-local v3 table mappings with `markdown`, `rows`, `cols`, and
  rectangular `data`;
- `quality_score`, `ocr_used`, `ocr_confidence`, `layout_ambiguous`, and
  `encoding_repaired`;
- `error`: null or a page extraction error.

Unknown/missing fields, page gaps, invalid OCR metadata, non-rectangular tables,
non-finite values, non-NFC text, CR line endings, and conflicting error/output all
fail closed. Page identity is never guessed from an aggregate block or `[TABLE N]`.

## Output and locators

The immutable `PageAwarePDFResult` contains `normalized_text`, canonical
`parser_results`, and `page_count`.

- Paragraphs use `page_number + paragraph_index`; paragraph indexes are 0-based
  within a physical page.
- `char_start/char_end` are offsets in the adapter's **global normalized** text,
  preserving EvidenceSpan v1 semantics.
- Every table cell uses `page_number + table_index + row_index + column_index` and
  publishes both raw text and a deterministic structured value.
- An empty page creates page-only failed evidence with `empty_output`; a page error
  creates page-only failed evidence with `parser_error`. Both retain the physical
  page without publishing error text as source evidence.
- A table-only page is not misclassified as an empty page.

## Quality mapping

`ocr_used` is an informational flag and may remain `parsed`. Low OCR confidence,
layout ambiguity, repaired encoding, or quality below 0.30 yields `partial` output
with the corresponding stable EvidenceSpan v1 flags. The adapter does not perform
OCR or invent confidence.

## Composition

Pass `result.parser_results` to the only canonical `IngestService`. The service
revalidates the immutable raw's path, size, and SHA-256 before creating EvidenceSpan
values. Identical input replays byte-identically; raw drift, source mismatch, or
locator/output conflict continues to fail closed.

## Source-catalog PyMuPDF wiring

The PyMuPDF fallback detects tables before narrative blocks. Text blocks that
intersect a verified table bounding box are excluded from narrative text, so table
content is not published twice as both a paragraph and cells. Remaining text blocks
are joined with stable blank-line paragraph boundaries before adaptation.

If `Page.find_tables` is unavailable or table extraction/geometry cannot be trusted,
the page keeps extractable narrative but is marked `layout_ambiguous`; no table cell
locator is invented. A page text exception becomes page-only `parser_error`, while a
truly empty page becomes page-only `empty_output`. Document-level open, encryption,
or corruption errors continue through the source catalog's truthful unsupported
artifact path with zero EvidenceSpan output.
