# A01/A05 next-node design review: local native text flow and lane evidence

**Review type:** read-only architecture/design review; no implementation or tests run.  
**Product baseline:** `8a258b93404f351ae92cd3449198b42141ef4169`  
**Source original:** WuXi AppTec FY2025 annual report, SourceRef SHA-256 `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`.  
**Existing A05 result:** still OPEN. This note does not close A05 or approve a source-flow implementation.

## Recommendation

Keep the document-wide completeness result partial when a geometry/table request is deferred. Add a separate, call-local positive observation for native text pages, and make cross-page continuity consume that positive page observation rather than the document-wide `coverage_complete` flag. Separately, reuse the existing layout-hints lane detector for explicit multi-column lanes, and expose a truthful positive single-body-lane witness only when the detector has enough actual geometry to establish one. Missing lane evidence must remain unknown; do not write `column=0` as a default.

This is a small extension at the existing parser → `DocumentStructure` → observation → `NativeSourceContext` seam. It does not need a second task store, permissions layer, page parser, PDF pass, or persistent raw-text copy.

## Evidence and current behavior

### The “deferred table page” field is overloaded

The parse completion path in `src/company_wiki/source_catalog/narrative_evidence.py::_parse_pdf_document` assigns `state.geometry_session.deferred` directly to `NarrativeParseResult.deferred_table_pages`. With a geometry session, those pages are not necessarily deferred table extraction. `SourceGeometrySession.request` in `narrative_pdf_intent.py` records pages for several reasons: navigation conflicts, resource limits, partial candidate observations, plan capacity, exploration limits, and work-budget exhaustion. The actual replay summary reports reasons including `candidate_observation_partial`, `navigation_conflict_deferred`, and `not_requested_by_intent`.

The name `deferred_table_pages` therefore overstates what this list means for the intent-driven path. It should be described in planning and new interfaces as **geometry/request-deferred pages**. Preserve the existing field/wire for compatibility during this node; do not silently redefine overall completeness or remove the field in the same change.

The recorded parser observation is decisive for this sample:

- 249 physical pages, 249 read; no parser errors and no opaque pages.
- Fine PDF capture was requested only on page 16; its coverage is a separate axis from base text parsing.
- The native page-view side channel reports `complete=true`, 235,958 captured characters, and zero deferred native-view pages.
- The intent/layout summary is partial and contains many geometry-request deferred pages.
- `DocumentStructure.coverage_complete` remains false because its current formula also includes `deferred_table_pages`.
- The actual `NativeSourceContext` has `coverage_complete=false`, while its `unproven_pages` list does not contain pages 13 or 14. The 13→14 proof is rejected first by the global completeness check.

The replay artifact's old field name must not be read as proof that native text on every listed page is missing. In particular, do not change `parsed.coverage_complete` to true: that would erase the valid document-wide geometry incompleteness signal.

### The code path that couples unrelated page failures

1. `narrative_evidence._scan_pdf_pages` / `narrative_pdf_intent.scan_planned_pages` reads each page's base text blocks and emits canonical text units. The current run reads the entire 249-page source in one pass.
2. `_parse_pdf_document` attaches the geometry-session deferrals to `deferred_table_pages` and returns the original text units plus layout summaries.
3. `DocumentStructure.coverage_complete` in `narrative_document.py` is false when there are errors, opaque pages, or deferred-table pages.
4. `narrative_reading._understand` maps that one boolean to `native_scan="complete"|"partial"` and forwards `deferred_table_pages` as `deferred_pages`.
5. `observation_adapter.build_observation` stores `native_scan`, `opaque_pages`, and `deferred_pages` in one coverage object.
6. `document_understanding.pipeline.understand_units` constructs `NativeSourceContext` from that observation. `NativeSourceContext.__init__` derives `coverage_complete` from the whole-source `native_scan`; `page_neighbour` passes it as `coarse_complete` to `native_page_neighbour`.
7. `native_page_neighbour` rejects the edge with `CONTINUITY_PAGE_COVERAGE_UNPROVEN` before it reaches the current unknown-column check.

This is a responsibility-boundary problem: overall extraction/planning completeness is being used as a veto on an edge whose two text pages have their own source evidence.

## Minimal interface design

### 1. Keep independent completeness dimensions at the source owner

At the existing PDF parser owner, accrue a small typed, call-local page-text observation during the existing page loop. Do not infer it by parsing error strings or subtracting deferred geometry pages from `range(page_count)`.

Suggested shape (names illustrative; one compact field on `DocumentStructure` is sufficient):

```python
native_text_coverage = {
    "schema_version": "native-text-pages/1",
    "page_count": 249,
    "observed_pages": [...],       # only pages whose base text read/emission succeeded
    "unproven_pages": [...],       # text read failure, empty/opaque text page, or unknown status
    "complete": True,              # all page-text scan statuses are known; independent of geometry
}
```

Record the status in the same code that reads and emits each page: `_scan_pdf_pages`, `_scan_and_emit_pdf_pages`, and `narrative_pdf_intent.scan_planned_pages`. A page is positive only after the base text extraction and text-unit emission for that page succeed. A page with no text blocks is not a positive endpoint. Keep any QA/table opacity or table-discovery status in its owning dimension; do not treat an enhancement-only failure as missing base text, and do not treat `opaque_pages` as a substitute for this new typed fact without first classifying its producer semantics.

`complete` in this sidecar means that the parser has an explicit status for every physical page, not that every page contains extractable prose or that all table/layout work completed. Global `DocumentStructure.coverage_complete` remains unchanged and can remain false.

Keep this evidence transient to the parse/selection call. It should contain page numbers/status/counts and, optionally, existing page-view digests—not page text, paths, a copied PDF, or a second canonical source record. Reuse `page_count`, the page loop and existing unit provenance; charge only incremental status/index work to the same `WorkBudget`.

### 2. Pass positive page coverage to `NativeSourceContext`

Extend the current `narrative_reading._understand` → `understand_units` → `build_observation`/`NativeSourceContext` seam with an optional `native_text_coverage` mapping. No new store or context service is needed.

- Keep `native_scan`, geometry-request `deferred_pages`, and `layout_coverage` for the existing whole-document/reporting semantics.
- Add a distinct `coverage.native_text` (or equivalent private constructor argument) with the source-owner positive page statuses.
- `NativeSourceContext` validates the schema and page-number bounds before indexing it. Missing, malformed, truncated, or unrecognized coverage means “no local positive proof”; retain fail-closed behavior for callers that do not provide the new field.
- A cross-page edge may proceed only if **both endpoint pages** are positively observed native-text pages, neither is text-unproven, both unit observations are valid, and every intervening unit remains accounted for by the existing positively identified furniture rule. Use local page state for this edge. Do not turn the whole source's `native_scan` to complete.
- Preserve the existing global completeness bit for reporting and other consumers. Rename it internally if desired for clarity, but do not let that rename accidentally change its public meaning.

The local edge must still pass every existing physical predicate: same immutable source; exact adjacent physical pages; ordered unique source units; compatible page frame/rotation/font/role; positive running-furniture IDs for any skipped units; and the current geometric proximity/overlap checks. A table or geometry-request deferral on an unrelated page must not erase local base-text evidence, but unknown local text coverage must still reject the edge.

### 3. Reuse explicit layout lanes; add no default lane

The existing multi-column path is already partly connected:

- `understand_units` calls `layout_bridge.apply_layout_hints` **before** constructing `NativeSourceContext`.
- `layout_bridge._apply_layout` runs `layout_hints.derive_layout_hints` and writes a proven `text_column` to `observation.units[*].layout.column` when one exists.
- `NativeSourceContext.observe_native_source_unit` reads that actual `layout.column` and the source bbox/frame.
- `layout_hints.columns.detect_document_lanes` uses document-wide gutter cuts and page-local lane groups; the lane evidence can be used for actual separated columns. If it reports no lane, the context correctly sees no column today.

That means a second-column implementation or profile-based guess is not needed. A clear, explicit multi-column assignment should be consumed by the current observer; an unknown/different column must stay rejected.

There is a narrower gap for a single body lane. `detect_document_lanes` records `basis=["no_column_gap"]` when there are enough candidates but no cut; with too little geometry it records `insufficient_geometry`. `LaneLayout.confidence` stays `unknown` in the no-cut branch. `_build_unit_hints` discards the no-cut basis for ordinary prose and emits `text_column=None`/`basis=["no_lane_split"]`. `build_reading_order` can label an unsplit order `high` simply because `lanes` is empty, so that confidence is not a single-lane proof. Do not use `no_lane_split`, `reading_order.confidence=high`, `native_ranges.complete`, a profile ID, or a missing `column` to set `column=0`.

The minimal extension is to expose a **separate positive lane witness** from the existing layout-hints producer only when it has enough real geometry to support the claim. It can reuse the lane detector's existing page units, cuts, body-unit exclusions and shared work budget. A single-lane witness should carry an explicit nonnumeric lane identity (or an explicit `single_body_lane` basis), a bounded source/layout digest and the measured basis. Only `no_column_gap` is a candidate input, not sufficient by itself: require adequate non-furniture prose geometry, complete source geometry for both pages, compatible coordinate frames/rotation/page dimensions, and no conflicting/spanning lane evidence. If any prerequisite is absent, retain unknown. For explicit split layouts use the existing numeric lane IDs and do not merge opposite lanes.

`NativeSourceContext` can consume that lane witness as an additional observed field alongside `column`; it must not synthesize a lane from the endpoint x-coordinates alone. Existing bbox overlap and left-origin tolerances remain necessary supporting checks, not a replacement for positive lane identity. The native page-view's per-block bbox/order/hash can corroborate page text and geometry without carrying the full text to the model, but its aggregate `complete` flag alone is not a lane identity.

`PdfReadingContext`, `prepare_geometry_reading`, geometry-policy profiles and `SourceGeometrySession` provide intent/navigation/table-candidate selection. They do not encode physical text columns. Do not infer a lane from `cn_annual` or another company/document profile.

## Cache identity and one-budget requirements

The current `decision_inventory.py` has three distinct source-code digest groups, plus a conditional source-usability digest:

- `business_algorithms` directly hashes all 28 modules named by `business_modules`. In the grouped names below, a leading dot means “append to the immediately preceding package prefix”: `company_wiki.source_catalog.{narrative_business_policy,narrative_recognition_scope,narrative_revenue_guidance,narrative_predicate_state,narrative_business_meaning,narrative_source_purpose,narrative_reporting_rules,narrative_business_disclosures,narrative_operating_relations,narrative_reading,narrative_native_dependencies,narrative_finalize}`; `company_wiki.document_understanding.{pipeline,structure,structure.sections,structure.layout,structure.contract,layout_bridge,observation_adapter,layout_hints.headings,operating_states.relations,operating_states.patterns,operating_states.text_view,operating_states.product_reference}`; `company_wiki.document_normalization.{text_matching,form_fields,table_shapes}`; and `company_wiki.source_catalog.n6_candidate_operating_facts`. In particular, `narrative_reading`, `pipeline`, `observation_adapter`, and `layout_bridge` are already covered by actual source bytes; listing them as missing would be incorrect.
- `continuity_algorithms` directly hashes `document_understanding/narrative_continuity.py` and `document_understanding/indented_tail_geometry.py`.
- When `pdf_frontend=True`, `pdf_reading_algorithms` directly hashes `company_wiki.document_understanding.geometry_intent.reading`, `.geometry_intent.planner`, `.geometry_intent.contracts`, `.profiles.geometry_policy`, `company_wiki.source_catalog.narrative_pdf_intent`, `.narrative_pdf_candidates`, `.narrative_evidence`, and `company_wiki.resource_budget`.
- `_source_usability_version` directly hashes `automation/narrative_select.py` plus the selected material-matcher module: the explicitly supplied matcher, or `document_normalization/replay.py` for normalized MIME types, or `source_catalog/narrative_replay.py` for PDF/plain-text/JSON. This set depends on the inventory inputs.

The returned version map also records `PIPELINE_FEATURE_VERSION`, `OBSERVATION_ADAPTER_VERSION`, and `LAYOUT_HINTS_VERSION`, plus PDF frontend/capture/projection/native-range/page-intent version values. Those strings participate as version labels; they are not transitive source-code digests of modules imported by their owners. In particular, `narrative_pdf_layout.py` and `narrative_native_ranges.py` are represented here by selected version constants, not source-byte hashes.

Three relevant source files are not directly covered by any current source-code digest group: `source_catalog/narrative_document.py`, `document_understanding/layout_hints/__init__.py`, and `document_understanding/layout_hints/columns.py`. The package initializer is imported by `layout_bridge.py` and supplies the recorded `LAYOUT_HINTS_VERSION`, but its source bytes are not directly hashed. `layout_hints/headings.py` is directly hashed; `layout_hints/columns.py` is not. Hashing an owner does not transitively hash its imported modules: `layout_bridge.py` does not cover changes in `layout_hints/__init__.py` or `columns.py`, and `narrative_reading.py` does not cover `narrative_document.py`. A code-only change in these three files can therefore leave the current source-code digests unchanged unless an associated version string is manually bumped. If the local-flow implementation changes any of these owners, add their source bytes to the existing digest closure (or an equivalent single digest) and keep the relevant feature-version bumps where the wire/behavior contract changes. If the parse-result coverage contract changes, bump that parser/model contract version too.

Keep the existing direct hashes for `narrative_evidence.py`, `narrative_pdf_intent.py`, `narrative_continuity.py`, geometry-intent reader/planner/contracts, geometry policy, and resource budget. Do not describe `narrative_pdf_layout.py` or `narrative_native_ranges.py` as directly hashed: only their listed feature/version values are present. Version bumps alone are not a substitute for hashing changed algorithm-owner source when the cache identity is intended to follow code changes.

The cache test must prove that the old no-parent result cannot be replayed under the changed coverage/lane implementation. Test both: same source + same code reuses the identity, and changing any changed owner source/version changes it. No paid summary should be regenerated for this structural node.

Keep the one caller `WorkBudget`. Record coverage while the parser already walks pages; reuse the already-built observation and layout-hints output; do not parse the PDF twice, rebuild all page units for a sidecar, or create a second budget. Precharge any per-page map/set materialization and per-edge checks under the current account. The existing 16M document work ceiling and PDF collector limits remain in force.

## TDD and acceptance matrix

| Case | Expected result |
|---|---|
| All base text pages read; one or more unrelated pages are deferred by geometry/table candidate planning | Whole-source coverage stays partial; a valid local edge between positively observed pages 13→14 may proceed if lane and all physical checks pass |
| Text read exception, missing page, empty/opaque endpoint, incomplete page status, malformed coverage contract | No local positive text proof; edge rejects |
| Geometry request deferral on an endpoint, while base text is positively read | Text proof may still pass; lane proof remains independently required. Do not mistake “table not requested” for missing text or for a valid lane |
| Known explicit two-column layout, endpoints in same lane | Lane identity is explicit; continue to other physical checks |
| Known explicit two-column layout, endpoints in opposite lanes | Reject |
| Single-lane candidate with sufficient source geometry and no conflicting lane evidence | Emit a distinct positive single-lane witness; never manufacture integer column 0 |
| `insufficient_geometry`, no lane proof, unknown column, spanning/cross-lane block, incompatible frame/rotation/dimensions | Reject |
| Non-furniture unit between edge endpoints; wrong source; nonadjacent pages; duplicate ordinal/unit; missing bbox/font/frame | Reject, preserving current behavior |
| Existing horizontal-instability and vertical-drift red probes | Remain red after the positive path is added |
| Existing same-page counterfeit/duplicate-parent, source-boundary, unknown-coverage and opposite-lane negatives | Remain red; do not edit old inputs/assertions to make the new positive pass |
| Budget-exhausted page status or layout computation | Return unknown/partial and reject; no budget reset or partially published positive proof |
| Cache identity | Old cached page-flow/selection cannot be reused after any changed owner algorithm; unchanged code still has deterministic identity |

Use focused tests in `tests/unit/test_narrative_evidence.py`, `tests/unit/document_understanding_selection/test_reading_native_continuity.py`, `test_reading_native_list_ancestry.py`, `tests/unit/document_understanding_layout_hints/`, and `tests/unit/du11_production/test_cache_identity.py`. Retain the existing physical observer and source-ancestry negatives as-is. Run only the focused parser/continuity/lane/cache cluster plus Ruff and mypy at the implementation node; do not restart the long full suite for each small adjustment.

### Real-source acceptance (the decisive test)

After the focused red/green tests, perform one offline replay of the same SourceRef using `SourceVersionReader` and the real company catalog, with no download, no model call and no raw copy. Assert:

1. Verified original SHA; 249/249 physical text-page statuses are accounted for, with the exact text-failed/empty/opaque pages reported separately from geometry-request deferred pages.
2. The overall/geometry status remains partial where its current capture/planning evidence says partial; the parser does not claim the whole report has full table/layout coverage.
3. Pages 13 and 14 have positive local native-text proof; each endpoint's actual page/layout/frame and lane basis is recorded without raw text duplication.
4. The actual physical page-neighbour observer is called once for the 13→14 edge; all intermediate units are either absent (adjacent ordinals) or independently identified running furniture. The proof's source SHA, endpoints, page numbers, ordinals, frame, lane identity and basis match the original.
5. The selected D&M/TIDES facts have the p13 Chemistry business parent as an ancestor/context in their own actual compiled tasks; the parent name appearing in a different task does not satisfy the assertion. Testing/Biology remain excluded from those tasks.
6. All prior approved checkpoints and A13 actual-input assertions remain unchanged; no widening of the selected cap or previously accepted evidence to make this edge pass.
7. Work stays under the existing 16M budget; no second parse, no source/catalog/config mutation, no model call, no download and no raw copy.

Only after this real assertion and the existing negative matrix pass should the parent mark the A01/A05 local-flow component complete. New paid formal summary/cache recovery is a later step; it must use the newly invalidated source-code identity and the configured budget/provider, not rerun during this structural design or implementation test.

## Stop conditions and scope

- If the source parser cannot positively state local native-text completeness, leave the edge OPEN; do not infer it from `pages_read`, `native_ranges.complete`, or absence from the current geometry-deferred list alone.
- If layout hints cannot prove a same-lane witness, leave the edge OPEN; do not fill `column=0` or relax the current physical predicates.
- Do not change the old counter/page-number, parser-provenance, source identity, raw storage, prompt, provider, or model response gates in this node.
- This is an architecture recommendation only. No source/test/PWF files outside this new review directory were changed; no test, API, acquisition or raw-document operation was run.

## Product source hashes

SHA-256 hashes of the inspected source snapshot are recorded in `source-hashes.json`. They bind this design note to the stated product HEAD. The new directory is not part of the product source hash set.
