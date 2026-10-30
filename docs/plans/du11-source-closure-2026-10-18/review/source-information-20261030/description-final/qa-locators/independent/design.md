# Q&A cell locator — independent design review

Baseline: `f88221d2578eac078bb7b30d9a8c00b08f2ee6d2` (2026-10-30). Scope: source inspection, existing receipts, decompression of the saved native snapshot and pure synthetic row emission. No original PDF read/parse, SDK/model call, download, catalog write or product code edit.

**Decision: conditionally support native parser 0.1.2 with real cell character locators.** Compatibility and native-range requirements below are necessary. Clearing flags or relaxing the model material guard is not an acceptable fix.

## Root cause and evidence

`narrative_evidence._emit_pdf_qa_fragment` (line 1420) emits every sentence with page/table/row/column coordinates and unconditional `locator_unstable`. Multiple fragments in a cell share a locator although metadata already has source cell SHA, fragment range and fragment SHA. `_make_unit` distinguishes newer repeated QA unit identities using metadata ranges, but this does not make their public structural locator unique.

`automation.narrative_select._verify_selected_material` (line 560) rejects selected unstable/low OCR confidence spans before a model call. That guard is correct. `real-summary-v2/phaseC-090-68befe24f11e.native-failures.json` reports `PARSER_INCOMPLETE: selected material is not reliable parsed source evidence`; `receipt.json` reports POST attempts 0, tokens 0, estimated cost 0 and activation recovery `NOT_RECOVERABLE`.

Frozen `source-information-20261029/cn-ir-native-v4/parsed.json.gz` has 302 units, all parser 0.1.1; 75 are QA fragments, all unstable. Those 75 fragments use 6 distinct structural cell coordinates, giving 69 repeats. A read-only probe confirmed all 75 ranges are in bounds, match `row_cells[column][start:end]` exactly, and match cell/fragment SHA. States: 13 paired questions, 43 paired answers, 5 cross-page questions, 12 cross-page answers, 2 pre-question fragments. This is a general granularity mismatch, not an IR/company-specific detection defect.

## Smallest safe implementation

1. Add current native parser 0.1.2 while freezing 0.1.0/0.1.1 output, IDs and flags. Preserve `QA_FRAGMENT_VERSION = 0.1.1` as a historical contract constant. Use explicit finite version sets/helpers for modern QA grammar and stable locators; do not accept arbitrary future versions through lexical comparisons.
2. The new emitter supplies cell-relative zero-based half-open Python character ranges in existing `EvidenceCoordinates.char_start/char_end`, retaining page/table/row/column and existing proof metadata. The coordinate space is the exact extracted/trimmed cell stored in `row_cells[column]`, not PDF bytes, page text or UTF-8 bytes. Validate integer bounds, actual slice and SHA before stability is claimed. Unprovable ranges must fail or retain instability.
3. New 0.1.2 must reuse 0.1.1 grammar/discourse. Exact-equality branches requiring review in `narrative_evidence.py`: `_make_unit` (~611), `_pdf_qa_parts` (~665), `_CrossPageQaLinker.compatible` (~811), `continue_answer` (~825), `pair_answer` (~879), `_has_pdf_question` (~2370). At baseline a synthetic numeric question with two answer sentences becomes an orphan whole answer under version 0.1.2, whereas 0.1.1 produces the intended three paired fragments.
4. Same-cell continuation compares structural cell identity (source/parser/language/page/table/row/column/cell SHA), excluding char ranges. Keep range ordering/non-overlap. Distinct new coordinates in one cell must still inherit one QA group. Preserve cross-source/parser/language, distant-page and next-cell boundaries.
5. `narrative_replay._qa_fragment_matches` must apply strict checks to 0.1.2. Currently fragment SHA, group, question number and state are checked only when one side is exactly 0.1.1. Retain full locator/text-hash/role/kind round-trip keys, source/parser checks, and bind coordinate ranges to metadata ranges. Tampering with either representation or a discourse binding must fail.
6. Keep `_verify_selected_material` unchanged. No company/fixture branch, selector workaround, bulk flag deletion or second model material path is needed.

Main production files: `narrative_evidence.py`, `narrative_replay.py`, optionally `narrative_pdf_qa.py` for version feature declarations, plus `narrative_native_ranges.py` when upgrading the global default. Existing EvidenceCoordinates already validates and serializes char ranges; no database/schema or locator serializer change is needed. The excluded W21 files need no modification for this design.

## Native-range compatibility

Current native range parser 0.1.0 binds exactly base parser 0.1.1. `native_range_unit` rejects any other base. `narrative_replay._parser_version` enforces that pairing and one replay base across ordinary/range spans. A global default bump alone can silently disable native range composition or reject mixed ordinary/range replay.

Do not mutate old `NATIVE_RANGE_BASE_PARSER_VERSION = 0.1.1`. Recommend a small explicit map:

| Range parser | Base native parser |
| --- | --- |
| 0.1.0 (frozen) | 0.1.1 |
| 0.1.1 (new) | 0.1.2 |

Generate the range version from members' uniform base version; persist the existing base binding. Replay validates the pair, derives one actual base and rebuilds the complete binding. Reject mixed members, mixed replay bases, unknown versions, modified base claims and missing/foreign member IDs. Existing schema/page-view feature versions may remain if bytes/semantics are unchanged.

A new range parser identity matters: current range unit ID hashes parser version/coordinates/source/text but excludes base parser and member IDs. Supporting both bases under unchanged range parser 0.1.0 can yield identical unit IDs with different bindings. A new range version avoids this alias and preserves legacy byte reconstruction. If this compatibility extension is deferred, defer the global default switch too; losing existing range behavior is not an acceptable minimal fix.

## Cache / historical replay

`NativePdfBackend.describe_recipe` advertises native parser version; `PdfReading` freezes the recipe and validates returned base unit producer identity. `generation_manifest` binds parser component and complete recipe. The bump should therefore create a new base generation and miss old cache entries without rewriting old artifacts.

New parser/locator changes unit IDs and EvidenceSpan identity. Existing unit-addressed layout, parents, relationships, source proofs and selection results must be regenerated consistently for the new generation, not mechanically reused or relabeled in place. Historical spans continue replaying through their pinned versions. A terminal failed job is not activation-pending recovery; do not rerun its old frozen generation under silently changed software.

No selector bump is inherently necessary when only parser identity/locator proof changes and 0.1.1 QA meaning is preserved. Deliberate new selection semantics require separate review. Frozen-cell reconstruction is sufficient for offline range/selection regression but is not proof that production parser 0.1.2 read original bytes; label fixture proof distinctly from later real execution.

## Normalization boundary

Cell emission strips strings; `_make_unit` additionally normalizes NFC/CRLF. Non-NFC/CRLF offsets can therefore differ from raw_text length or exact canonical slices. Define this explicitly. Minimal conservative behavior claims stability only for provable exact slices and retains instability/fails unsupported cases. A versioned normalized-cell coordinate space with verified mapping is a wider alternative. Do not guess offsets with substring search or reinterpret legacy offsets.

## Recommended TDD and acceptance

1. Old guard negative control: old selected QA with `locator_unstable` still raises `PARSER_INCOMPLETE` before verification/model transport; low confidence does likewise. A manually unstable 0.1.2 span also remains rejected.
2. Freeze representative 0.1.0/0.1.1 emitted JSON, IDs, locators, flags and metadata; legacy numeric-marker behavior stays unchanged and pinned replay works after the default bump.
3. New range positive cases: multiple questions/sentences, repeated identical answers, whitespace, Unicode; assert actual source slices, SHA/bounds, unique locators/IDs and metadata-coordinate agreement. Do not test only disappearing flags. Include NFC/CRLF conservative failures or explicit mapping.
4. Parameterize modern grammar/anti-markers (dates/times/ratios/projects), cross-page multi-sentence linking, distant-page/source/parser/language and next-cell negative boundaries. Distinct ranges must inherit one intended QA group.
5. Tamper matrix: coordinate range only, metadata range only, both inconsistent with replay, cell/fragment SHA, group/question/state, role/text/source/parser name/version. Genuine spans pass; each mutation fails. Include equal answer text in separate ranges/cells.
6. Native range matrix: old range/base output remains byte-identical; new pair passes; same text/coordinates across versions has distinct identity. Reject cross-version binding swaps, mixed members/base replay, missing members, foreign sources; preserve view-budget/exact-substring constraints.
7. Cache identity: advertised/current parser and actual units agree; old/new recipes create different generation hashes; old cache misses without changing immutable bundles; frozen execution cannot silently adopt new recipe; cache prechecks do no model/original IO.
8. Frozen actual-cell regression: reemit saved original cells through new code, compare text/order/role/group meaning and regenerate IDs/dependencies. Cover all 75 QA fragments including 17 cross-page paired fragments. Do not relabel the snapshot as new production parse evidence.

Existing test anchors: `tests/unit/test_s7_pdf_qa_fragments.py`, `test_narrative_native_ranges.py`, `test_shared_reading_cache_precheck.py`, `du11_production/test_qa_closed_scopes.py`, `du11_production/test_qa_physical_container.py`, `test_pdf_qa_cell_range_locators.py`. Run focused tests then root-required domain/mypy checks. No paid run is needed for this review.

## Operations / limitations

CodeGraph located symbols; subsequent reads checked literal branches. Root owns shared planning; this worker writes only design.md/json and created no competing plan. Assigned directory lacked task_plan.md/progress.md. A pure-probe stdout attempt hit Windows GBK UnicodeEncodeError; explicit UTF-8 rerun succeeded. An initial report patch was rejected for delete/add targeting the same path; update patch corrected it. No product files were affected. This is design review, not implementation or model-quality certification.


## Final implementation review

**PASS, 0 OPEN engineering findings.** Frozen product/test raw and LF-normalized SHA-256 values are in `final-review.json`; 23 independent offline cases passed in 3.23 seconds. No original PDF, download, SDK/model or product-write operation was performed by this reviewer.

One P1 proof downgrade was found and fixed by root: clearing only quality_flags from a legacy unstable span had allowed it through replay and the production material boundary. Root bound ordinary span quality flags to the source unit in `_span_matches`, matching the strict native-range behavior. Independent old/new unstable controls and locator_unstable/low_ocr_confidence production controls now pass.

Independent acceptance includes baseline 0.1.0/0.1.1 emitted unit bytes/IDs, non-NFC/CRLF conservative refusal, metadata/coordinate tampering, cross-page multiple answers without next-cell leakage, legacy range bytes, distinct new range identity, mixed-version/binding rejection, and actual generation_manifest/hash separation. Literal old-version/constant inspection found no additional downstream native 0.1.1 assertion requiring a product change; transcript legacy version entries remain separate.

The first independent test run had two reviewer-fixture failures: attempting EvidenceSpan conversion of non-NFC row_cells is already forbidden by the source contract. The fixture was corrected to compare raw unit images/IDs against git baseline, preserving the intended legacy-byte check. This was not an implementation regression.

Root's qa-range-real-v1 receipt was inspected: 302 native units, 15 selected, no selected unstable locators, 15/15 original locator replay, 0 POST and 0 downloads. This reviewer did not reopen the original. Engineering proof and this receipt do not establish model summary quality, summary acceptance or RF adoption.


## Final conservative-diagnostic compatibility revision

**PASS, 0 OPEN.** The final 7-path raw/LF SHA fingerprints are in final-review.json. Rehashing confirmed they already matched the frozen files, so no source fingerprint changed at this final reseal. The preceding receipt text is retained in final-review-prior-text-v1.json.

Strict quality-flag equality was too narrow for an existing valid workflow: a consumer can conservatively annotate a clean replayable span as locator_unstable and retain needs_review. Final proof instead uses set(source-unit flags) ⊆ set(span flags). Every source-owner restriction must remain, while additional conservative diagnostics and flag ordering changes are permitted. Independent tests confirm clearing unstable/low OCR source restrictions, dropping one of two restrictions or replacing one with another is rejected. Additive/reordered cases pass. The actual material guard still rejects flagged source material before model use.

The final targeted command ran 28 neutral cases, 11 existing quality projection cases and 21 QA cell-range cases: **60 passed in 8.09 seconds**, bound to tests-final-superset.txt. The previously failing test_review_diagnostic_never_bypasses_actual_pdf_replay[False] passes with its original contract. Native-range proof remains unchanged.

This is targeted engineering proof, not a broad-suite pass or model summary adoption claim. Earlier broad-suite failure under exact equality remains a true historical result. No original PDF, paid/network or product modification was performed by this reviewer. One sealing helper initially expected two changed raw hashes; all seven already matched, so the helper was corrected to record that no source fingerprint changed.
