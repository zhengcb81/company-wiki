# B2 bounded antecedent: final source interface recommendation

Status: READ_ONLY_INTERFACE_CONVERGED; IMPLEMENTATION_AND_BEHAVIOR_VALIDATION_OPEN. This is implementation guidance, not an additional approval gate. Observed ROOT WT HEAD `2022432ea17f391ee8ba08bfd400ab81a97dee0d`. No runtime, tests, original, author worktree, model or provider was executed or changed.

## 1. Concrete owner split

- `narrative_reading` owns **which original predecessors may be examined**, using existing observation order, structural section and actual project/body membership. It owns closure costs and attachment to the existing package/context graph. Neither geometry nor the model should resolve product references.
- The existing `SourceOperatingSession` coordinates one original/material lookup and one `OperatingRelationSession` on the same caller WorkBudget. Its engine owns the narrow deictic/declaration grammar and exact source offsets, reusing `unit`, `matching_text`, `prepared` caches. Do not call `detect_reading_business_fact` again to build a predecessor list.
- `OperatingRelationSession.detect(target, context_ids)` currently checks parent and copies contextual name classes. It does **not** carry a previous product topic into the target. A new additive `reference_closure` operation is necessary even when no operating predicate matches: descriptive admission currently bypasses the event gate.
- Existing `contexts` are not this operation's search space: they include headings, questions and other structural dependencies. Product declarations must come from the explicitly permitted predecessor IDs.

## 2. Build one bounded predecessor port in the existing traversal

Reuse the already reserved `_prose_reading_packages` observation/section/package-membership pass. While processing each observed original body, retain references/IDs and finite scope descriptors; do not serialize whole wires, copy all text, sort the whole source again, or walk all parsed units per target. Existing source indexes may remain O(N); the **added grammar work** is O(N * K), where K is the fixed original closure envelope, not a new source-wide semantic scan. Charge actual metadata edges/retained membership before constructing them and each finite candidate/character before preparation.

Minimum source-side descriptor (internal only, not an observation/public schema):

```text
OriginalBodyPosition = {
  unit_id, parent_id, ordinal,
  section_id, project_key, body_region_key,
  boundary_kind, predecessor_unit_id
}
```

`section_id` comes from actual `structure.sections` membership (or its existing `native_section_key` override); `project_key` is the actual project-package identity tuple already formed in prose ownership. `body_region_key` is a source-owned run of eligible body with no observed structural barrier, not a new semantic label or generated product name. Preserve original roles/locators in the original lookup instead of copying them into the descriptor. Unknown or multiply contradictory scope is not equivalent to another unknown scope; report incomplete rather than inventing equality. A non-project body has no active project; this is different from unknown/conflicting project membership.

Use the actual source ordinal as the ordering coordinate. Page-local `paragraph_index`, hash-sorted IDs, package priority and post-carrier material order are not predecessor order. Physical cross-page access is allowed only through the existing proved source-flow edge; this interface must not bypass unknown counters, unread/opaque pairs or geometric limits. Proven furniture may be skipped by existing source-flow proof; ordinary excluded material is a boundary, not free permission to search further back.

Stop a predecessor run at another original parent, actual section/project/body/QA/role boundary, table/list with separate ownership, excluded/unread interval, unproved physical ordering or work/cap exhaustion. A heading may establish a scope boundary and remain required context, but its product-like words cannot nominate a product. Do not stop merely because a preceding sentence is an independent **declaration**: that is precisely the evidence being sought. A grammar-proved new unrelated actor/family can stop borrowing; source indexing itself must not manufacture a second family classifier.

For each body owner, expose this finite source-only request:

```text
AntecedentWindow = {
  target_original_unit_ids: tuple[str, ...],  # original order, not a carrier discount
  predecessor_original_unit_ids: tuple[str, ...], # source order, strictly before target
  complete: bool,
  stop_reason: source_boundary | beginning | cap | work | unknown_scope | unread
}
```

This is a view of the existing source lookup, not a second Store/cache or a prose copy. Return only the suffix that fits the combined envelope. Preflight lengths/block keys before concatenation or normalization. A candidate or required declaration which cannot fit is not silently skipped to reach an older cheaper one. When truncation leaves a relevant dependency unresolved, return partial/defer, never infer absence or uniqueness from an unexamined tail.

The envelope counts the union of target originals, selected declaration originals **and existing required context**, with duplicates removed by original identity:

- at most 8 original units;
- at most 4 distinct `(parent_id, physical_page, pdf_block)` keys;
- at most 2048 original characters, using full necessary source material;
- the same parent work account and existing final span/character caps.

If a block coordinate is unavailable, it cannot be used to prove compliance with a PDF four-block cap. Do not equate missing block keys. Source-native complete range projection may reduce retained material only if its existing provenance owner proves the full declaration/attribution; this implementation must not manually trim noun substrings or reinterpret carriers as one cheap block.

## 3. Minimal semantic request/result

Suggested additive interface, preserving legacy `detect` behavior:

```text
OperatingRelationSession.reference_closure(
    target_id: str,
    predecessor_unit_ids: tuple[str, ...],
    *, window_complete: bool
) -> ReferenceClosure

ReferenceClosure = {
  status: not_applicable | unique | collective | ambiguous | missing | partial,
  reference_refs: tuple[OriginalRef, ...],
  declaration_refs: tuple[OriginalRef, ...],
  member_refs: tuple[OriginalRef, ...],
  required_original_unit_ids: tuple[str, ...],
  attribution: issuer | quoted_related_party | other | unknown,
  diagnostics: bounded tuple[{code, unit_id?}, ...]
}

OriginalRef = {unit_id: str, char_start: int, char_end: int}
```

The engine sees only permitted candidate IDs and the same parent lookup. It validates IDs/parents and bounds, caches preparation by unit identity, and caches this operation by target plus exact ordered predecessor IDs plus completeness. Cache no-match/ambiguous/partial distinctly; do not cache a scoped unique result by text. The source coordinator need not expose section/project metadata to the grammar because it already restricts the input; `window_complete` prevents resource-truncated searches masquerading as complete proof.

Check actual product-deictic subject/object before connector stripping, using the existing prepared matching/NP grammar. Incidental words such as `其中`, quoted `this`, or a concrete direct object do not automatically create a product dependency. A description without a recognized event still needs this check. Recognize one explicit named declaration or one explicit collective enumeration; two unrelated declarations remain ambiguous, not nearest-wins. Preserve third-party/question attribution and stage, polarity, modality, units and dates; no declaration can donate a new predicate to its members.

`not_applicable` preserves old admission. `unique/collective` requires bounded complete proof and attaches original declaration material as context. `ambiguous/missing/partial` withholds only the affected package by the existing reason channel. No model recovery, manual permit, issuer guess, or whole-document veto is introduced.

## 4. One-session graph integration and source namespaces

Current `_candidates` builds the graph **before** constructing `SourceOperatingSession`; merely calling the new method there would add dependencies too late. Minimal reorder:

1. Keep original `units_by_id` read-only. Prose continuity and native range ownership remain unchanged.
2. Establish final material/carriers and analysis-group maps, and initial structural contexts, without building the graph yet. Group/context construction uses package IDs, not graph output.
3. Construct **one** `SourceOperatingSession` with final material plus an explicit read-only original fallback mapping. Overlay lookup priority: analysis owner, exact final material, original fallback. Reject conflicting same-ID records rather than choosing by text.
4. For original target members (including every relevant project/citation view), get the bounded window and run reference readiness through that same engine before ordinary `fact` admission. Do not check just the first package anchor or the rank-selected subset.
5. On success attach the needed original declaration IDs to the original package's `required_context_unit_ids`; project each through `_carrier_origins` for its budget/material package. Source required-context and analysis `contexts` must be refreshed before `fact`; do not mutate engine preparation or reuse a previously cached target fact computed without these dependencies. Prefer finish all readiness/context setup before the first `fact` call.
6. Build the existing single graph once from the updated budget packages. Continue ordinary fact/financial checks using the same session. If any necessary declaration is excluded, unavailable, exceeds the combined original envelope or cannot survive final selection, defer the target too.
7. Original packages remain the authority for `_context`, `citation_views`, `_selected_unit_spans` and source-card support/context. Target remains support; declaration remains context. Do not turn declarations into extra achieved-product claims or carrier IDs into original parser IDs.

`_ObservedUnits` currently exposes only final material plus analysis. An optional original fallback is required for replaced original members, not a second full copied mapping or a second detector. Existing raw original text and locator objects must be accessed lazily through that lookup.

### Required reference projection correction

Current `_original_refs(owner, refs)` applies `self.maps[owner]` to **every** ref and ignores `ref.unit_id`. That is only safe for existing same-analysis refs. Do not pass new declaration refs through it unchanged.

- A ref naming a known analysis owner is projected using **that ref's named map**, once, preserving the existing exact source segment arithmetic.
- A ref naming a known original unit is preserved after integer/bounds/parent validation against that original text. Original range length is not checked against target text.
- A final carrier ref stays in its own namespace unless the actual carrier provenance explicitly projects it to original members; never map it by fuzzy text or target offsets. For this new operation, return original declaration refs directly, avoiding an extra reverse-carrier range mapper.
- Unknown namespace, cross-parent reference, invalid/empty/out-of-range coordinates or any unmapped nonseparator analysis range makes proof invalid/incomplete, not a partial best-effort remap. Analysis-only inserted separators have no source position; they must not manufacture characters. A request entirely in a separator cannot yield successful proof.

A narrow fix can preserve the five legacy relation arrays while applying one shared namespace-aware ref projector. Do not fork separate numeric-offset rules for antecedents. If the initial implementation deliberately disallows another analysis owner, return an explicit incomplete result rather than remapping through the current owner.

## 5. Actual saved CN case and remaining truth

The inspected latest `page-scope-after-counter-fix/cn-h1.json` reports t34 still present once: physical page17 paragraph12 chars375–432, text SHA `8ff2eacd4cfb23f277697cea3e0f61701df95b2d7fd5527828b808b42092c107`, beginning “该系列产品已交付多个先进…”. That is syntactically terminal but its product family is outside its selected material. The same ROOT-run receipt has required canonical/source 10/10, not a semantic closure PASS.

The existing bounded native investigation states paragraphs9–11 declare the metal-silicide system and SA/SU, SPTi, ALDTiNM; paragraphs12–14 are dependent material. Whole9–14 uses five original blocks. This review did not reread the PDF and does not prove a smaller sufficient declaration. Under the unchanged four-block/8-unit/2048-character union, if a sufficient full declaration cannot fit, expected behavior is **defer this dependent card**, not increase caps, select one member or invent a family name. Generic management-discussion scope is insufficient to resolve it. The existing t32 fix is separate and must not regress.

## 6. Implementation TDD checklist (one engineering node)

1. Source interface: known same source/section/project/body order yields only preceding original IDs. Target in project/risk/background receives the same readiness check. Cross-section/project/parent, table/QA and unknown scope stop borrowing; ID lexicographic order and package-priority changes do not alter proof. Page paragraph reset is not a boundary by itself; unproved physical edge is.
2. Grammar: Chinese unique product, Traditional collective and English collective; descriptions without operating predicates; two competing series ambiguous; heading-only and forward declaration missing; unrelated self-contained assertion not_applicable; rival/question source cannot become issuer. Negative, not-yet and planned target strings remain exact.
3. Original caps: test inclusive 8/4/2048 and first excess 9/5/2049, counting body+existing context+declaration, shared block number on two pages distinct, carrier replacement not discounted. No expensive normalization before zero/small-budget admission; unresolved tail partial. A complete independent sibling remains selectable.
4. Namespaces: same numeric target/context offsets preserve distinct IDs/bytes; two analysis owners use their own maps; original declaration refs remain original after carrier replacement; wrong parent/unknown ID/out-of-bounds/separator-only refs do not succeed. Traditional/line-wrap offset replay remains exact.
5. No repeated work: instrument observed-unit reads and matching preparation for 16/32 body members and repeated targets; bounded source metadata pass plus bounded lookup, no N-scan per target, no second classify invocation, no whole mapping enumeration via fallback. Cached result differs when permitted context order/scope/completeness changes. Grammar and source owner actual module bytes enter existing cache dependencies.
6. End-to-end source assembly: use `_candidates` → selection → `_context` → `build_summary_task_plan`/source-card compilation with synthetic original evidence. The target's complete support and declaration context survive typed/public partitions, refs/hash/period/units unchanged. Forced span/char limit must defer the entire dependent card, not export a bare deictic. No provider/model is needed for this engineering node.
7. After implementation, ROOT can replay the existing real three-source suite once under the same budget/unchanged originals and fixed gold. Require t34 either proved closed or explicitly deferred; do not predeclare its disappearance as correctness or repeat paid ranking to fill the source gap. Formal content/paid C remain separate OPEN work.

## Method / boundaries

CodeGraph mother structural context was reused, followed by exact ROOT WT source reads. Read the prior design and saved compact investigation/diagnostics; no tests or PDF/model/provider ran. A literal read initially requested two nonexistent convenience filenames; exact existing paths were then used. One historical page-scope JSON read was larger than necessary; it was not copied or written. Only this report pair was created. No runtime/public wire/config/Store/author files were modified, and no new approval/identity/cache subsystem is proposed.
