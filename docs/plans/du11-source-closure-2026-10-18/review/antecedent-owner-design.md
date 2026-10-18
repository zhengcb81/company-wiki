# B2 bounded product antecedents: source/operating owner design

Status: READ_ONLY_DESIGN_COMPLETE; IMPLEMENTATION_AND_FINAL_REVIEW_OPEN. Observed ROOT isolated branch `codex/du11-source-closure`, HEAD `f5a26b48c8facfe8e9ad8ecdda2099e340c41a18`. ROOT is concurrently implementing physical continuity: this is architectural observation, not a frozen-source B1 or B2 acceptance. Actual source bindings at report assembly are in JSON. No new permission, contract signature or minor review step is proposed.

## 1. Shared root and existing interfaces

`SourceOperatingSession` is already the source-owned bridge from original/final material to one `OperatingRelationSession` and one caller WorkBudget. `_prepare_group` makes a temporary analysis view of an explicitly closed group, preserving segment maps; `relations` maps the five relation ref families back to original units. `fact` reuses those relations and charges the compatibility recognition scan. This is the appropriate coordination layer, not PDF parsing, card compiler or LLM decoder.

`OperatingRelationSession.unit/matching_text/prepared` already cache one observed unit, one normalized reading text and exact original offset map keyed by **unit identity**, not text. `_np_candidates`, `_split_conjuncts`, `_classify_np`, `_clause_guarded`, `_to_ref` and `patterns` are the shared grammatical responsibility. Extend this owner narrowly for a product deictic's source dependency; do not create a second product lexicon in `narrative_reading` or geometry.

Crucially, current `detect(target, context_ids)` does NOT resolve product antecedents:

- `_detect_operating_relations` validates same `parent_id` and gathers `contexts_used`; it only merges the contexts' `_scan_name_classes` into target `name_classes` for related/third-party attribution.
- `_UnitScan.last_topic` and `last_actors` are inherited within the target view, not across those context units.
- `_ObservedUnits` exposes text/parent/role/kind/locator; **no section/project/scope metadata** reaches the relation engine. Same parent is necessary but not sufficient for a semantic referent. The source owner must provide only permitted ordered predecessor candidates.
- `_np_candidates` and `_classify_np` identify broad actor/object noun phrases, not a named series declaration. Codes alone (A/B/C) cannot be made products solely by a string match; use an explicit product/series declaration and its enumeration.
- `_split_conjuncts` is useful within a proved declaration, but splitting a series list must not create multiple completed event assertions.
- `patterns.PRODUCT_SUFFIX` handles basic object heads and is not a standalone plural/deictic grammar (English `products`, `devices`, and standalone `series` need deliberate treatment in the shared owner).

## 2. Important bypass: descriptions without an event still need readiness

`_predicate_gate` may return no operating relations before target/context offset preparation. `_admitted` can nevertheless admit ordinary descriptions because of their observed business reading role. A dependent card such as “该系列产品具有较高生产效率” therefore cannot rely on `result.relations` being nonempty to trigger reference checking. Implement a separate narrowly scoped readiness/reference operation in the **same** `OperatingRelationSession`, reusing its matching caches. Check the actual subject/object deictic before `strip_connector` removes `该`/`其`; do not flag every incidental word `this/其` anywhere in a sentence.

No recognized dependency means **not_applicable**, preserving the old source path. A dependency without proof means missing/ambiguous, not an invented explicit product. This must also work for real subject ellipsis only where the existing local grammar proves it; broad pronoun resolution is out of scope.

## 3. Minimal interface and responsibility split

Suggested internal method (names are design suggestions, not a new public wire):

```text
OperatingRelationSession.reference_closure(
    target_id, *, predecessor_unit_ids: tuple[str,...]
) -> {
    status: not_applicable | unique | collective | ambiguous | missing | partial,
    reference_refs: [exact target refs],
    declaration_refs: [exact original predecessor refs],
    member_refs: [optional exact explicitly enumerated product refs],
    required_unit_ids: [only the genuinely necessary original source units],
    attribution: issuer | quoted_related_party | other | unknown,
    diagnostics: [bounded reason data]
}
```

- The **source reading owner** derives the ordered predecessor candidates from actual original source sequence and active section/project/body/role/physical dependency scopes; no full-document search, hash-sorted “nearest”, forward unit, table, question or generic heading may nominate a product. Use a small suffix of preceding observed windows bounded by the existing total envelope. An explicit new subject/family/section/project/QA boundary stops borrowing. Actual context is not automatically all `required_context_unit_ids`: those include headings and QA context.
- The **relation owner** interprets only these permitted candidates, using its one matching/offset preparation. Recognize explicit declarations and whether they denote one concrete product or a named/explicitly enumerated collective. A plain “产品业务” chapter label is not a declaration. Candidate text is not allowed to supply a predicate, qualify a new fact, or change the target's raw text.
- `unique` means one proved referent matching the target category, not “pick the first product word”. `collective` means one explicit collective declaration or enumeration, even when it contains several distinct member names. Two unconnected series remain **ambiguous**, even if one occurs nearer, unless actual source grammar explicitly distinguishes the referent. Missing product evidence, out-of-scope candidates or exhausted work remain missing/partial.
- The method must not assign issuer merely because the surrounding document belongs to a company. Concrete third-party material can remain useful with its original `other`/related attribution; it cannot donate a product to an issuer's different assertion. Quoted/question material cannot assert management's result. Existing stage/polarity/modality/predicate/qualifier refs stay untouched.
- Prefer an additive **separate reference-closure result**, preserving old `detect` wire/default legacy behavior. If existing relations need annotated referent refs internally, do so with explicit ref namespace rules, not synthetic merged actor strings or a replacement object name.

## 4. Exact source integration point and no duplicate preparation

In `_candidates`, physical packages and exact per-page carriers are established before the context graph and source-state admission. The earliest semantic integration point is **after material namespaces are known but before `build_context_graph`**. Establish one SourceOperatingSession there; invoke reference readiness on a candidate body owner; resolve its source-approved predecessor declaration; add the resulting required context edge to that body's existing package; then build the one graph and continue `session.fact`/`financial_only` with the same session.

The predecessor original evidence must remain addressable even if some originals have been replaced by per-page carriers. Keep the already constructed original-unit lookup as a read-only fallback/alias port for reference preparation, alongside current final material/analysis views. `_ObservedUnits` is already an overlay and can carry this bounded source-owned lookup. This is an in-memory view, not a second Store/cache/task DB. Only explicit candidate IDs may be read. Do not instantiate a second detector and rescan the whole source or silently seed target `last_actors` from arbitrary contexts.

A proof made against original refs is validated/costed on originals, then its required IDs are projected via existing `_carrier_origins` into selection material. Keep original proof IDs available for raw replay and public `_selected_unit_spans`. Exact carrier membership does not reduce original 4-block/8-unit cost. Anchor/support are the actual dependent event/description; a preceding declaration is required **context**, not a new source statement asserting that each listed product achieved the target event. Existing `_context` can already produce support/context partitions, and `summary_tasks.build_summary_task_plan` carries them with no new model logic.

Source checks must run before selection on every relevant candidate, not only on whatever the ranking happened to retain. `missing/ambiguous/partial` withholds the dependent package through the existing reason channel. Do not mark unrelated whole documents blocked, restart a budget, call a model to fill the subject, or add a manual review gate.

## 5. Critical original-ref namespace rule

`SourceOperatingSession._original_refs(owner, refs)` currently ignores each `ref.unit_id`: it interprets every numeric range through `self.maps[owner]`. This is valid only for refs created on that same synthetic body analysis owner. Passing a declaration/context ref through it would silently move the same numeric offsets into the body's product or predicate text.

Minimal robust rule:

1. If `ref.unit_id == owner` and owner has an analysis segment map, project that ref through **that owner** once.
2. If the ref already names a valid original unit, preserve its unit ID/offsets after bounds/source validation.
3. If it names another known synthetic analysis owner, project using **that named owner's own map**, never the target's map; or disallow that shape and return original declaration refs directly.
4. Unknown namespace or out-of-range ref is incomplete/invalid proof, never a best-effort numeric remap. Exact per-page carrier refs retain their own parser/locator identity; mapping them to their underlying original members requires the actual carrier provenance port, not text matching.

Keeping `reference_closure`'s original declaration refs separate avoids changing all five relation arrays unnecessarily, but does not excuse unsafe generic ref projection if those refs ever enter it. Add same-numeric-offset target/context and two-synthetic-owner tests. Cached name attribution copied per call must remain isolated when another scope uses the same declaration unit.

## 6. One bounded envelope: required declaration is not free

Use the existing parent WorkBudget for predecessor indexing, every candidate unit/character read, grammar scan, normalization/offset map, enumeration matching, sorting and proof/ref mapping before that work. Existing prepared caches keyed by source identity avoid repeated script conversion; cache negative/missing/ambiguous closure per **target + exact ordered allowed context IDs/scope**, not just text or one product spelling. No global O(N*K) scanning or unconstrained graph search.

Before attachment, count the union of original body plus genuinely necessary declaration/context:

- max **8 original units**;
- max **4 distinct `(source_id, physical_page, pdf_block)`**;
- max **2048 original characters**, including needed full declaration material rather than only the few extracted product names;
- all selection context is also charged against the existing 96 spans / 48,000 chars and the same source/model draft caps.

A normalized carrier or a two-character noun ref must not discount a larger required original unit. If a tighter exact native source range can genuinely contain the full declaration and its attribution/scope, use the existing source-range owner, not manual trimming. Ambiguity requires retaining all relevant competing evidence or deferring; choosing a cheaper named fragment is not a proof.

**Real CN p17**: the existing read-only investigation identifies paragraphs9–11 describing the metal-silicide family and SA/SU, SPTi, ALDTiNM, followed by paragraphs12–14 dependent event material. The observed whole9–14 uses five original blocks. If no genuinely sufficient smaller closed declaration/context is proved, the correct result under the current four-block envelope is **defer that dependent card**. Do not raise limits, drop one collective member, or assert one named product achieved every family validation status. This report does not reopen/parse the original or assert any new smaller range exists.

## 7. Portable behavioral RED package

### Relation owner pure cases

- Simplified unique: “公司推出霁川X型设备。” -> “该设备计划于下半年交付。” Unique original declaration refs; target plan/future retained, no completed-shipment claim.
- Traditional collective: “本公司曉杉系列產品包括甲型及乙型設備。” -> “該系列產品尚未取得客戶認證。” One collective dependency, negative/not-yet preserved, no separate completed claims for甲/乙.
- English collective: “Our Lark series comprises Aster and Birch devices.” -> “These products are not yet commercially available.” Exact original refs, collective scope, not issuer-attribution guessed from neutral role.
- Description gate bypass: “The Lark series comprises Aster and Birch devices.” -> “These products offer a compact footprint.” Dependency readiness checked even if no existing operating event grammar matches.
- Two separate series declarations before “该系列/these products” -> ambiguous; generic “产品业务/Product overview” heading alone -> missing; future/forward-only declaration -> missing.
- Quoted rival/customer statement followed by different issuer assertion -> no borrowed issuer product; a clearly explicit third-party dependency may remain `other` with original text, never promoted to issuer. Analyst question naming a series does not prove answer completion.
- Unrelated non-deictic complete product assertion unchanged; incidental quoted word “this” or Chinese `其中` quantity clause is not a product dependency automatically. Local concrete direct object must not be overwritten by an older series.

### Source integration/caps/refs

- Target and context each have `char_start=0,char_end=4`; grouped body and original declaration keep different original IDs/bytes. Another group's same offsets map through its own segments, not target. Traditional conversion/native line wrap still returns original characters.
- Same source but different section/project/body scope, intervening table/QA/new explicit family, or candidates provided in hash-ID order must not create nearest-source proof.
- Necessary context within4blocks/8units/2048chars survives as context in typed/public/source-card partitions; a fifth distinct block (including same numeric pdf_block on another page) or ninth original unit or2049th character defers the entire dependent card.
- Span/char final-selection budget cannot export bare target after context is dropped. Original event predicate, qualifiers, dates, units, parser/locator/SHA remain replayable; unrelated complete sibling cards remain.
- WorkBudget0: no predecessor normalization/walk. Microbudget: partial closure and no fallback subject guess. Repeat call: prepared identity caches reused; different allowed-context tuple does not reuse a stale unique result. No unreferenced-unit scan, second account or negative-status reinterpretation as absence of dependency.

## 8. Existing targeted tests to reuse (no broad rerun)

- `tests/unit/du4_operating_states/test_b_synthetic_specs.py`: within-target topic borrowing, original Traditional refs, related/third-party actor attribution, predicate/state/modality controls.
- `test_root_boundaries.py`: zero-budget no normalization, unreferenced map not walked, exhausted context tail, conditional and embedded vendor assertions.
- `test_c_contract.py`: schema, context-missing/parent mismatch, immutability/exact offsets, deterministic bounded output.
- `tests/unit/document_understanding_selection/test_reading_native_material_mapping.py`: original-to-selected carrier mapping and cross-source rejection.
- Source-owner source-closure tests should assert final `_candidates` + `_context` + `build_summary_task_plan` support/context closure, rather than only seeing a nonempty relation dict. New antecedent tests are missing implementation work, not already green evidence.

## Method

CodeGraph structural context first, then actual ROOT WT owner source reads and existing bounded investigation only. No source edit, test/PDF/parser/model execution, network, original/key/config read, commit or external author worktree mutation. One literal-search command used Windows-invalid wildcard paths and returned a harmless path error; it was corrected with `rg --files tests` and exact known files, without rerunning tests or source scripts. Only this report pair was written. B1's739 tests and current physical source implementation were not re-reviewed or re-run.
