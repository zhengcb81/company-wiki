# Findings

The W05 plan claims preservation of parser 0.1.1 while introducing transcript parser 0.2.0 separately from PDF. Actual push-gate errors show parser 0.1.0 rejection and metadata/replay parser-version disagreement. CodeGraph tools are unavailable in this tool session; use exact known source paths.

## Compatibility contract findings

Exact RED on original assertions: 3 failed in 0.97s (red_exact.txt). parse_transcript_text rejects preserved 0.1.0. Resolver's package metadata guard correctly catches a mismatch: test helper declares NARRATIVE_PARSER_VERSION=0.1.1 while default transcript parse creates 0.2.0. Keep assertions; bind fixture contract to actual format identity, then retain strict forged-version rejection. Current pilot resolver supports only PDF/TXT, so actual official HTML needs bounded extraction and byte-line verification through existing transcript material API. No extractor modification needed.

Design: keep shared PDF pin 0.1.1 unchanged. Define explicit transcript format/version contract in assigned narrative_evidence module (no extra source file), consumed by parser_component, parser dispatch and resolver. Legacy 0.1.0/0.1.1 use identical existing legacy path; 0.2.0 uses natural-body path. Version error is named before package metadata guard. Formats route TXT directly as before, and HTML/JSON through verified original-byte extraction.

## Confirmed classification and delivery

The initial resolver-product hypothesis was incorrect: before source changes, actual parser_component text/plain/transcript identity was 0.2.0, selected groups were 0.2.0, and accurately declared current package replay succeeded. The fixture alone declared 0.1.1. Production pilot bundle generation uses its representative span identity (scripts/narrative_evidence_pilot.py lines335–338), so nonempty current packages are correctly declared already. Keep guard strict and correct fixture setup, without assertion changes.

Actual product changes: one explicit transcript layout contract (0.1.0/0.1.1 original path;0.2.0 natural path) replaces duplicated parser/generation version lists. Resolver translates unsupported transcript versions to its named resolve error and adds explicit HTML byte-material replay using the existing bounded extractor/line SHA verification. PDF shared pin stays0.1.1. No version fallback or reinterpretation; wrong declared supported version fails the original metadata guard.

Real immutable MSFT M2 proof:273436B,481lines,body90–414,515units,41selected/verified/indexed/replayed spans and groups;query models4hits resolved. Raw SHA bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656 and mtime unchanged. Own TEMP and TEMP/TMP env restored; no raw copies, external providers, model calls or cost. This is the existing selected-only in-memory bundle resolver, not a claim of catalog/StockWiki consumer API acceptance.

## Concentrated responsibility RED outside the transcript defect

Initial focused suite:201PASS/1SKIP/1FAIL4.74s; only PPTX transport literal 1.0.0 assertion failed. Exact untouched base7762bfd1c5542fbc37e606c361cb6d661b0f02c3 reproduced the same1FAIL4.05s in an owned TEMP archive of src + synthetic test dependencies only. Git diff confirmed normalization/PPTX source and original test unchanged before this proof. No production raw copied. The format's declared PPTX_PARSER_VERSION is1.1.0; HTML has its own declared PARSER_VERSION1.0.0. MAIN authorized updating only this test's expected version using these separate declarations, keeping all public transport/read/replay/locator/cleanup assertions intact. No PPTX or normalization source changed.

Mypy caught new HTML local variable original (bytes) shadowing the existing later original (mapping); rename to original_bytes. No behavioral change.
