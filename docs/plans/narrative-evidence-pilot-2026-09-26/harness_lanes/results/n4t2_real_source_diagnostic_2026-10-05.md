# N4-T2 真实来源选择器基线诊断

Date: 2026-10-05
Status: READ-ONLY DIAGNOSTIC; no implementation changes.

## Method

- Opened the exact saved N4C run SourceRefs through `SourceCatalog` and `SourceVersionReader.open_version`, with `purpose="narrative_derivation"` and the current read-policy SHA pin. Verified byte count and SHA-256 in memory before parsing.
- Parsed the PDFs in memory with the current selector. The IR sample was checked both with the normal deferred-table pass and with `full_table_scan=True`; selected spans, if any, were checked through `verify_pdf_evidence_spans_bytes`.
- Output contains aggregate counts and SHA prefixes only. No source text was printed or saved, no source bytes were copied, and no model/provider/network call was made. The diagnostic did not independently compute a full production filesystem fingerprint.

## Quarterly report

Source SHA prefix `37f0eb13fc97`, 309,955 bytes. With full-table scanning the parser read 13/13 pages, produced 192 units and 11,645 characters, with complete coverage, zero parser errors, and zero opaque pages. The selector returned zero candidates and zero spans (`needs_review`). None of the seven current topic categories or high-value event patterns matched any unit or PDF context group; there were three units matching the broad progress regex and 15 matching the recency regex. This confirms the historic zero-candidate result, but does not prove the document has no valuable business narrative: the current topic vocabulary may itself be too narrow. Keep this result in review until the expanded coverage tests distinguish genuine absence from an unrecognized narrative.

## Investor-relations activity report

Source SHA prefix `3e25aab404a1`, 133,294 bytes. Normal parsing read all 3 pages and produced 57 units / 2,350 characters, zero parser errors and zero opaque pages, but correctly reported incomplete coverage because deferred tables remained. Full-table scanning produced 67 units / 4,689 characters and complete coverage, still with zero parser errors or opaque pages. Both passes returned zero candidates/spans and `needs_review`.

In the full scan, existing business-topic phrases occurred in 6 units: `new_business` in 2 and `overseas` in 5. Three PDF context groups contained a business topic together with both a progress signal and a recency signal; each also matched the diagnostic's specific-action pattern. None matched `_HIGH_VALUE_EVENT`. Current `_eligible` accepts progress plus recency only for `industry_dynamics`; it does not accept the corresponding current business/new-business/overseas progress. This is a concrete selector false negative, not an identity or PDF-parser failure.

The current catalog metadata has a non-empty title, so the old run's “normalized title absent” condition was not reproduced from that field. Keep an explicit synthetic test with an empty title and `existing_kind` set to `quarterly_report` or `investor_relations` to prove routing fallback.

## Required N4-T2 response

- Add a narrowly defined, source-only candidate path for concrete, current operating progress paired with an eligible business topic and a time cue. Cover core-business progress, new products/projects, and overseas expansion, and keep static background, generic “关注” boilerplate, table-of-contents rows, and financial tables unselected.
- Add synthetic Chinese tests for industry dynamics, operating progress, new business/project, and overseas expansion; exercise titleless quarterly/IR routing. Verify every selected PDF span replays against its exact source locator.
- Preserve `needs_review` when a complete scan has zero recognized narrative but the absence has not been established by the tested selector. Do not widen empty-result skip based only on zero current candidates.
- MAIN still owns the post-integration bounded real Worker batch, summary/citation verification, P4 profile measurement, RF N3a read, and storage accounting.
