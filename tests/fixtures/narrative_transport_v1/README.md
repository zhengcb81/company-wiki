# Synthetic TXT transport golden

These files come from the real narrative runtime and public reference/read CLI,
using the local Replay fixture. They contain synthetic English transcript bytes;
no external model or network is used. Source bytes, span hashes and summary
semantics are checked exactly. Installation policy hashes, generated version ID
and read time are normalized as listed in metadata.json.

The root JSON files are the historical v1 compatibility vector and remain frozen.
The provenance-only helper below is not a current-generation upgrade command;
it deliberately rejects semantic/identity evolution. Historical maintenance only:

```powershell
python -B tests/support/refresh_narrative_transport_golden.py
python -m pytest tests/contract/test_narrative_transport_cli.py::test_current_public_producer_regenerates_normalized_txt_golden -q
```

The refresh command permits provenance changes only (versions, prompt version and
Replay response hash). It refuses source/span/summary semantic changes so those
must be inspected. It updates the bundle, reference, read request, receipt and
metadata hashes together. It is a developer action, not a daily CI step.

Span `parser_version` may change as provenance; span ID, SHA, locator, original
text and structured fields must still match exactly. The 2026-10-07 refresh
only updates parser 0.1.0→0.1.1, selector 0.3.1→0.4.2 and prompt 1.3.0→1.6.0;
all source, span and summary semantics are unchanged.

## Current material and historical availability

`narrative-read-request/1` keeps its four required fields. An explicit
`as_of_date: null` reads currently available source material without claiming
historical availability. The receipt echoes null and retains the true or unknown
publication date. An ISO date continues to require a known publication date no
later than that cutoff. Missing, empty, or malformed dates do not select current
mode. Source identity, original/artifact hashes, and locator replay apply in both
modes. Existing dated golden files remain unchanged.

## Reviewed current-v2 snapshot (2026-10-21)

`current-v2/` is the exact current producer expectation; the root v1 JSON bytes,
reference, request, receipt and metadata hashes are unchanged. Both snapshots
remain strict bundle/wire/hash compatibility vectors. The public current-producer
test compares all bytes against current-v2 after the same documented installation
normalization, and never removes provenance or accepts arbitrary span IDs.

The reviewed evolution has 12 changed JSON paths:

- Parser0.1.1 to0.3.1 uses the versioned speaker/boundary parser; the synthetic
  transcript's exact source text, coordinates, locator and original byte binding
  are unchanged and replay successfully under both saved parser versions.
- Selector0.4.2 to0.8.0 classifies the same launched-product and expanded-capacity
  sentence as `core_business`, in addition to every previous topic. This is
  classification metadata; no new operating assertion, number or unit is added.
- The same four selection reasons are emitted in the current deterministic
  order (specific business event before progress/change language).
- Those two structured-output changes legitimately change output SHA and span
  ID. The claim citation and transcript byte-binding citation point to that
  exact new span; neither uses an unrelated or historical span ID.
- Prompt1.6.0 to1.7.0 is recorded in both model and versions metadata. Original
  source SHA/bytes, full claim text, selection counts and all remaining fields
  are equal. Derived reference/artifact hashes and sizes bind the new exact bytes.

`tests/support/narrative_golden_evolution.py` reconstructs only these inspected
changes from v1, demands full-object equality with v2, validates span hashes and
IDs through EvidenceSpan, and replays both parser eras from the synthetic TXT.
Negative tests reject an invented numeric fact, added unit or old-span citation.
The proposal was generated into isolated tmp through the real runtime/CLI, then
copied as a new versioned fixture only after that semantic comparison passed.
No provenance-only refresh of the root v1 files was performed.
