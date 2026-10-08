# Synthetic TXT transport golden

These files come from the real narrative runtime and public reference/read CLI,
using the local Replay fixture. They contain synthetic English transcript bytes;
no external model or network is used. Source bytes, span hashes and summary
semantics are checked exactly. Installation policy hashes, generated version ID
and read time are normalized as listed in metadata.json.

After an intentional prompt/selector version change, run:

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
