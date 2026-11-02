# Transcript import wire fixtures

These files are literal, static request envelopes for
`company-wiki-transcript-import-request/2`. Their values and field order are
copied from the producing side, not generated from company-wiki's owner models:
no `dataclasses.asdict`, `to_dict`, `fields()` or `replace()` participates in
building them. Tests read the bytes from disk and hand them to the real CLI, so
an internal owner-model refactor cannot silently rewrite the expected wire.

The files are indented for review; JSON whitespace is not part of the wire, so
they are not claimed to be byte-identical to the producer's compact emission.
The field names and values are what is frozen.

## `ff_import_request_v2.json`

Shape copied from filing-fetch `scripts/transcript_tool_transport.py` at
`508aba30`:

- `source_request` is the dict literal returned by `_source_request()`
  (lines 191-219): `provider`/`provider_document_id`/`language`/`form_type` are
  `null`, `mode` is `"exact"`, `allow_download` is `true` (the fetch path sets
  it before `_import_fetched`).
- `candidate` is the dict literal returned by `_candidate()` (lines 825-864),
  including `adapter_payload_json` spelled exactly as
  `json.dumps(..., separators=(",", ":"), sort_keys=True)` produces it.
- `transcript_result` is `tests/fixtures/transcript_fmp/fmp_v2.fetched.json`
  (the earnings-transcripts producer golden, commit `4924d57`) with its
  `request_id` set to the identifier the company-wiki lookup side returns for
  this exact `source_request`. FF only forwards that id to ET and back, so the
  literal value is part of the real wire.

The payload is a synthetic, producer-generated offline fixture, not a live paid
API response. No API key is present. Publication date is unknown and the
as-of cutoff is explicitly unverified.

## `generic_html_import_request_v2.json`

The same envelope contract for a non-FMP (HTML) provider, kept because the
decoder serves both the FMP branch and the legacy HTML branch. Values are
frozen from the previous inline contract fixture so the file no longer depends
on `datetime.now()` or on owner-model projection.

Tests never write to these files.
