# Transcript 0.3.1 boundary repair handoff

## Root cause from original bytes

The versioned MSFT TXT fixture has SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`, 66,324 bytes and 340 raw lines. The deterministic original-text extractor produces 175 material lines, preserving original byte lineage. Those material indices, not the raw blank-line indices, are the parser's line coordinates.

Two generic boundary bugs were confirmed:

1. The first natural wrapper heading `Earnings Call Transcript` at material line 2 is accepted before the actual `Full Conference Call Transcript` at line 67. `CALL PARTICIPANTS` at line 12 is a syntactically valid two-word speaker label followed by a management title, so the roster and 52 editorial summary units inherit a management role. This is incorrect attribution, beyond the later coverage failure.
2. The real close at line 171 is `Operator: ... You may disconnect ...`. The shared end pattern matches it, but the recognized speaker branch returns to the loop before the end check. The parser continues through editorial footer text and then reports `transcript_end_missing`; the real select handler correctly rejects that parser error as `PARSER_INCOMPLETE`.

No path/identity gate relaxation fixes either cause. The original/derived byte binding is valid, and selected line ranges were all replayable.

## Versioned implementation

New current `TRANSCRIPT_PARSER_VERSION = 0.3.1`, layout `natural_affiliation_boundary`.

- `transcript_versions.py` now owns the exact version registry, contract dataclass, and resolver. Existing public imports from `narrative_evidence` remain explicit re-exports. The independent PDF parser remains 0.1.1.
- Registry mappings for 0.1.0, 0.1.1, 0.2.0 and 0.3.0 are unchanged. No saved version is silently upgraded.
- Only the new layout asks `body_start(..., prefer_explicit=True)` to select actual explicit transcript markers before wrapper/natural headings. If an explicit marker exists but no substantive nearby speaker body can be verified, it does not fall back to labeling the roster as the body. With no explicit marker, existing bounded natural heading checks remain.
- Only the new layout checks the existing shared end pattern on recognized inline speaker turns before continuing. A closing statement is still parsed as its actual speaker role, then footer parsing stops. This uses structural speaker/end patterns, without any issuer name or hardcoded Operator identity.
- Existing affiliation and stable QA rules remain; the change does not rewrite original strings, line numbers, character ranges, or byte mapping.
- `parser_component`, raw generation manifests, actual select parsing, and replay all resolve the same current 0.3.1 from the central registry. An explicit saved-version replay resolves that saved layout instead.

## Measured real fixture result

| Parser | Units | Management / analyst / operator | Body material lines | Errors | Selection | Span replay |
|---|---:|---|---|---|---|---|
| saved 0.3.0 | 550 | 499 / 30 / 21 | 12–175 | transcript_end_missing | partial, 58 spans | 58/58 |
| current 0.3.1 | 489 | 447 / 30 / 12 | 68–171 | none | selected, 51 spans | 51/51 |

New coverage is true, editorial roster/summary/footer is excluded, and every selected source span round-trips exactly. The original SHA remains unchanged. Saved 0.3.0's full unit snapshot SHA remains `2acb887d51d0aa1ffeab9bb775419624ef68a9d63c83700402c8f20c0ffa238b`, including unit IDs, text, roles, coordinates, and metadata.

## Completeness semantics and boundary

Per ROOT direction, existing explicit `Full Conference Call Transcript` formats retain their EOF semantics. A recognized explicit format may have parser coverage true without an end marker, as before; this is coverage of the captured source format, **not proof that the provider captured the entire telephone call**. A natural fallback without an end marker continues to report `transcript_end_missing` and false coverage. When a real end marker exists, the new parser stops exactly before footer content. No coverage assertion was weakened, no tests skipped, and synthetic fixtures were not rewritten to accommodate the change.

## TDD and acceptance

- Aligned RED, before source implementation: **8 FAIL / 5 PASS**. The five passing tests prove existing specific-version and saved snapshot behavior. An earlier RED fixture used the normalized text SHA in place of the original source SHA; its log is retained separately and does not count as implementation evidence.
- First GREEN attempt: **55 PASS / 1 FAIL**. Only an existing current-default test hardcoded 0.3.0. With explicit ROOT authorization, changed that single expectation to the public current constant; all old explicit versions and coverage assertions remain.
- Final **57 PASS** in 9.28 seconds: 14 new boundary/version/generation tests, 19 existing parser compatibility tests, 10 official layout tests, 13 affiliation/role tests, and the specified real MSFT public `evidence-search`/`evidence-lookup`/directory restoration integration test.
- New controls cover roster before a real marker, arbitrary recognized speaker names and inline end markers, dash/two-line labels, natural EOF truncation refusal, all legacy explicit-format EOF semantics, strict-event generation parser identity, whole old 0.3.0 real snapshot, and every real selected span replay.
- Ruff all three source files and two test files: 0. Mypy all three source files: 0. Exact commands, timing, and cleanup are in `final.json`; no deselection.

## Write scope and cleanup

Only new `transcript_versions.py`, `transcript_layout.py`, and the agreed `narrative_evidence` registry/import + `parse_transcript_text` ranges were changed. No whole-file formatting/restoration was used; ROOT's shared claim-quality helper was left intact. Test scope is one new unit file plus the one authorized current-default assertion/import in `test_official_transcript_layouts.py`. Logs and this handoff are only in the lane's evidence directory. No shared PWF files or commits were changed.

All owned final TEMP and pytest's relocated TEMP were removed, and the public integration fixture verifies its directory returns to its original state. No external/provider/model requests. No production raw, production configuration, or real source originals were modified.

## MAIN integration notes

Use the unchanged public `transcript_parser_contract()` / `parser_component()` API for default generation. Saved bundle versions must pass their stored parser version to replay; never substitute current default. New generation SHA naturally changes because its parser component is now 0.3.1, so a 0.3.0 artifact cannot silently satisfy a current request. Review metadata coverage as parsed-source coverage, rather than a provider-content completeness guarantee.
