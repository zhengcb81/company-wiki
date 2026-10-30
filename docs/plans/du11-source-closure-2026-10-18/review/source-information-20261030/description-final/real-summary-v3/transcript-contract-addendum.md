# PDF default contract addendum

**PASS, 0 OPEN.** Reviewed `tests/contract/test_official_transcript_layouts.py` at HEAD `0bf2805fa229c5d843483b9c22b2a4637776bd15`. The entire working-tree diff is one expectation line: current `parser_component("application/pdf")` changes from native parser 0.1.1 to 0.1.2. This matches the previously reviewed native QA cell character locator migration and the PdfReading producer identity. It does not change a transcript legacy pin.

Explicit transcript 0.1.1 parsing/routing, the old/new transcript unit identity separation, old transcript evidence replay with no failures, and explicit transcript 0.2.0 routing remain unchanged. The old PDF default literal was stale after the intentional native version migration; updating it preserves the test's intended current-default assertion.

The root reported 10 tests passed in 1.58 seconds. This addendum is independent read-only source/diff review; no redundant test run or summary semantic assessment was performed. The normal pre-push hook remains enabled; no bypass occurred.

- Bytes: 7743
- Raw SHA-256: `06ed87582ae11030f52f6602a74fd9fad6232122e98bfc56e84f30a492bc1b29`
- LF-normalized SHA-256: `785f7aeb018e35a687bda094396d649b842fe46fef4259207fb281e021a46527`

No product edits, original PDF reads, SDK/model calls or downloads were performed. This addendum certifies only the single contract update; final paid-summary semantic adoption is outside its scope.
