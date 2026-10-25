# CF1 native DOM structure design investigation

Status: READ_ONLY_DESIGN_COMPLETE. This is a design investigation, not implementation or source-content acceptance. No product, original, configuration or database changes; no network, paid calls, PDF replay or test run. ROOT owns implementation decisions and PWF summaries.

## Confirmed source and ownership findings

- The bounded actual-DOM observation binds HTML SHA `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`. Its current file reports 5,215 parse units; do not reuse earlier prose counts as current parser output. The business title at `0.1.22.10` is a standalone paragraph whose complete visible text is bold; `0.1.26.0` is bold+italic; their styles are absent from normalized metadata. The paragraph at `0.1.22.11` introduces a list; its child at `0.1.22.12.1` is inside a wrapper with an actual bullet sibling. Current owner emission puts body before its bullet-owner marker.
- `html_parser.py` preserves nearest-owner text, locator and source bytes, but only native h1–h6 heading metadata. Reordering or splitting owners would change historical replay semantics; neither is necessary to observe their native relationships.
- `structure/sections.py` is already the unique business-parent owner. Its native list frame, scope heads/members, stack restore and per-target context/source dependency maps are reusable. `_native_list_scopes` currently excludes DOM units and requires PDF bbox/page, so HTML cannot activate the existing path.
- `NativeSourceContext.page_neighbour` and `NativePageProof` are specifically physical PDF page/bbox evidence. Reuse its call-local source lookup/budget if useful, but do not fabricate pages, geometry or a PDF proof for DOM ancestry.
- `ObservationUnit` intentionally has typed slots. New DOM observations need an explicit bounded typed field and producer validation; merely attaching arbitrary metadata will not reach structure.

## Recommendation: one parser observation, one section owner, existing dependency closure

Implement two separable capabilities: **CF1a native list attribution** first, then **CF1b source-supported title hierarchy**. They share one HTML observation, but list ownership can be verified without solving every typography hierarchy. Do not build a second business graph, materialize another reader, change owner order, or turn a DOM path into a business parent on its own.

### Small, typed observation contract

Prefer a bounded `native_source_view.dom_structure` descriptor attached once, following the existing native-table descriptor convention. Project it through a named observation hint and parse it into typed records in the structure input owner. Alternatively attach a small per-unit descriptor; choose one representation, not both. These are source observations, not precomputed business sections.

Proposed transient schema `native-dom-structure/1`:

```text
source_id: original source ID (same original already verified by source owner)
blocks: records of {unit_id, owner_path, parent_path, owner_tag,
  explicit_heading_level?, formatting}
formatting: {bold_ranges, italic_ranges, underline_ranges,
  font_size_pt?, block_alignment?, leading_margin_pt?}
list_groups: records of {container_path, basis, item_records}
item_record: {item_path, member_unit_ids, marker_value_refs}
marker_value_ref: {unit_id, char_start, char_end}
basis: native_ul | native_ol | observed_marker_siblings
```

- Character ranges use the exact normalized owner text offsets already collected by `_OwnedText`; no raw HTML, source copy, arbitrary CSS, host path, model text or inferred business label in this contract. A normalized source descriptor owns references to originals, not copied prose.
- `owner_path`/`parent_path` identify actual element ancestry; they are not new locators. Unit references are filled after all original units exist, so postorder bullet emission does not require reordering.
- For `h1`–`h6`, or valid `role=heading` with a positive `aria-level`, the parser may emit explicit heading evidence. CSS typography alone remains formatting observation. Do not set `heading_like=True` for every bold paragraph.
- Observe visible text formatting in the same traversal as text collection. Honor inline inheritance, `normal` resets and numeric bold weights; `<strong>/<b>/<em>/<i>` are format evidence. Only compute supported inline declarations; stylesheets, CSS classes, script execution and browser rendering are not implied. Unresolved class-only appearance remains unknown.
- Full-block bold means union coverage of all visible non-space owner characters, not presence of one bold descendant or a bold first token. Hidden text and nested owners do not contribute. A formatting run cannot claim another owner's range.
- `native_ul/ol` membership comes from actual `li` ancestry. Custom lists require an actual visible marker region separated from a sibling body region inside the same wrapper. `display:flex`, a class called `list`, indentation, or a bullet character anywhere in a sentence is insufficient alone. Class names such as the observed issuer's `item-list-element-wrapper` are not a router.
- Build DOM parent/group/owner indexes once during parsing, bounded by existing source/text/unit/deadline limits. Do not call `find_parent` over the whole source for every pair or copy the complete block list into every unit.

### CF1a: introduction → actual native list items

1. Parser records list groups/items/markers using actual DOM. It does **not** name a business parent or infer which company division a list describes.
2. Shared structure code resolves the nearest preceding visible block at the list's flow boundary. An introductory colon plus a genuinely adjacent native list is sufficient syntax; walk only transparent wrappers, and stop at intervening prose, heading, table, footnote, semantic section boundary, source change, or an unrelated sibling group. Do not perform a document-wide backward keyword search.
3. Create the existing `_NativeListScope` with the introduction as its head and that group's actual native unit membership. Distinguish readable body units from marker-only member units: marker units must remain in the scope's traversal membership so the current frame is not accidentally popped between two list bodies, but they are not semantic body material. Add `native_dom_list` basis; current `native_numbered_list` is PDF-specific and should not mislabel DOM. Open it under the existing current section, and restore the prior stack once membership ends. Sibling lists must not inherit the preceding list's local introduction.
4. Populate the **existing** `required_context_by_unit_id[child] = intro refs` for readable source meaning. This is not a page-continuation claim. Existing `collect_native_dependencies` already checks readable refs, source consistency and transitive closure without requiring a physical page proof. It can remain unchanged for this minimal path.
5. Keep marker-only units addressable, but do not select them as standalone useful prose or automatically put markers in model material. Their native descriptor provides list syntax. Do not set `required_source_unit_ids_by_unit_id` merely to force a proof through a PDF-only wire.
6. Native DOM groups can contain noncontiguous current ordinals because a parent marker owner emits after child text. Resolve group membership by IDs and original paths, not `ordinal ± 1`. Preserve the original order for final material. Nested groups need a single section-parent stack, bounded membership, cycle rejection and source boundaries; no duplicate semantic graph.

This first node can fix the introduction/list definition loss even if CF1b title depth remains partial. The introduction itself already contains its source subject in the real example. That does not prove every later consumption paragraph's business ancestry.

### CF1b: restore title evidence without pretending typography is explicit depth

An inferred heading needs a conjunction of source observations and title-like syntax:

- Standalone paragraph/eligible block, all text in a distinctive source-observed formatting run; not a table/cell/caption/list marker/footnote or a form field.
- Short title-like content; reject full sentences, currency/quantity-only or mixed numeric tails, plain year rows, response labels, colon-ended list introductions and inline emphasis. Reuse existing form/table-tail exclusions. Punctuation rejection alone is insufficient: `Revenue increased sharply` is still a sentence-like claim without a period.
- Require local structural support, such as a following body block in the same flow, explicit heading neighbors, or repeated document-local typography used as titles. A globally bold document does not create a heading for every paragraph. Do not use an issuer-name or business-name allowlist.
- Keep `heading_level_source` distinguishable, for example `dom_typography`, and confidence medium/low when inferred. Explicit h/ARIA depth wins. The current `is_heading` table-region logic deliberately admits only native heading evidence; inferred typography must not evade that protection by being labeled `native`.
- Font size ordering is usable where the document supplies clear differing sizes. With equal font size, **bold versus bold+italic does not logically prove parent/child depth**. An explicit profile rule can treat consistent additional emphasis as a lower inferred level, but it must be versioned, tested on independent examples, and marked inferred. Conflicting/unsupported profiles remain unknown; do not silently claim exact native levels.
- The observed business title and its detailed product title live in separate page-wrapper `div`s. DOM ancestry therefore cannot prove their parent relationship. Wrapper crossing can preserve an already established source section stack, but arbitrary DOM depth, sibling `div` depth or the issuer-specific class does not define heading depth. Explicit section/article, equal-or-higher headings and source changes stop inheritance. Formatting peers must close one another, not accumulate as parents.
- Once a hierarchy is justified, `build_sections` is the only parent writer. Existing `SectionDraft.parent_id` and context inheritance provide the business-heading chain to selection/model compilation. The observation adapter must explicitly allow this inferred HTML-heading evidence: its present `has_body_parts` branch suppresses nonnative paragraph headings, so adding metadata alone will not work.

Do not bypass this uncertainty by matching a product word elsewhere in the document, treating an identically named heading as the earlier list child, or adding a second classifier in the strategy configuration. If a heading-to-earlier-list-item cross reference is genuinely needed, it is a separately proved relationship with ambiguity/duplicate-label controls, not a shortcut for CF1a.

## Source proof boundary: avoid unnecessary public-contract expansion

Current `NativePageProof` includes actual adjacent PDF page numbers, ordinal endpoints, coordinate frame, column and furniture IDs. `structure/__init__.py` assumes `furniture_unit_ids`, and `collect_native_dependencies` only accepts basis `observed_adjacent_page_flow` with `right_page == left_page + 1`. HTML DOM ancestry cannot satisfy this contract honestly.

For CF1a use readable dependencies and parser-bound DOM metadata as above; **no new proof union is needed**. If later consumers actually require source-only DOM marker references, then explicitly add a tagged DOM proof variant with its own same-source/path/marker binding validator and serializer; do not add fake page values, empty geometry or accept arbitrary `dict` proofs. That is a distinct optional follow-up, not a blocker or another approval gate for simple DOM list attribution.

`NativeSourceContext` may offer the existing call-local unit/provenance lookup and common work budget. Do not use `observe`/`page_neighbour` to manufacture HTML geometry, or instantiate a second physical observer/cache. The parser can provide one precharged native DOM index, and sections consumes it; source byte verification remains at its current owner.

## Version, replay and cache requirements

1. Introduce format-specific `HTML_PARSER_VERSION = 1.1.0` and preserve explicit legacy `1.0.0`, using existing per-format version machinery rather than changing base `PARSER_VERSION` for all formats. Default HTML parsing/current `normalization_identity` chooses 1.1; explicit legacy parsing emits the complete old metadata exactly. Preserve text, owner order, coordinates, unit kinds and `cwp-html-dom/1` locators in both paths; IDs can and should differ because parser version differs.
2. Pass selected HTML parser version through `normalize_document` → `parse_html` → scan state → `build_unit`/`NormalizedDocument`. Keep `require_parser_version` authoritative for supported HTML versions. Do not duplicate parsing implementations: one scan with version-gated added observation attachment.
3. `replay_units` compares **entire metadata**, not just text/ID/locator; `replay_evidence_spans` also binds candidate metadata. Adding fields to same-version 1.0 is therefore a replay regression, despite unchanged text. Test an independently frozen 1.0 unit before implementation, replay it through current public API, and compare full metadata/coordinates/ID; test current 1.1 likewise.
4. Bump observation adapter/pipeline feature identity when actual behavior changes. Bind HTML parser/DOM observation algorithm bytes to the existing source dependency identity, including any new owned helper. The recently added structure package closure covers new structure children but does **not** automatically cover normalization children. Use the existing format-owner dependency fingerprint; do not create another cache. Validate same source/config keeps identity, changing HTML DOM algorithm invalidates it, irrelevant external/test paths do not.
5. Historical raw/source manifests remain untouched. A reparse is a derived new normalization/read generation, not replacement of an immutable source original. No new public/private, signed policy hash, source identity gate, approval JSON or source-per-task verification is warranted.

## Neutral TDD matrix and acceptance nodes

### Node A — exact parser compatibility + native observation

Freeze legacy expected unit text/order/locator/ID/coordinates/complete metadata **before** code changes. New neutral HTML fixtures should use invented Alpha/Beta businesses, with no Microsoft/Azure keywords.

Positive cases: native h1–h6 and role/ARIA; native ul/ol/li; full visible bold text across multiple inline spans; full bold+italic observation; inherited inline formatting and `normal` reset; literal bullet sibling + nested body with marker emitted after body; transparent inline-XBRL wrapper; repeated page-like wrappers without semantic heading tags.

Negative cases: hidden bullet, marker in prose, `class=list` without marker/native li, flex layout without list, bold inline fragment of normal prose, all-bold complete sentence, quantity/year/currency rows, bold table/caption, malformed/overlapping char refs, hidden/nested-owner text in coverage, missing class stylesheet information, duplicate owner text at different paths. Deadline/unit/text limits still enforced and paid before expansion.

Tests: public `normalize_document`, explicit versions, public replay of frozen old and new units/spans. All old source text/order/locators remain byte-for-byte equal. No directory writes needed.

### Node B — one sections owner + downstream actual model input

Use the real parser on neutral HTML, then production observation/pipeline/selector/scoped model compilation; avoid injecting prebuilt section parents into a fixture.

Positive cases: colon introduction + native list child retains subject/definition; custom native bullet wrapper same result; nested list retains both readable ancestors; adjacent peer title closes previous peer; an accepted detailed title retains its actual parent across transparent page wrappers. Selecting a child carries only the necessary parent/introduction and source ID+locator.

Negative cases: sibling business list does not borrow Alpha's introduction; colon followed by an intervening paragraph/table/heading does not attach; isolated marker never becomes a useful summary; same DOM path in different source cannot pair; repeated same heading text does not cross-bind; equal-size ambiguous style does not get claimed as native; duplicate/cyclic/foreign refs are rejected or remain partial. Existing PDF native-list and physical-proof tests must stay green without new fake DOM geometry.

Metering: one source index/group pass and bounded membership, charged to the existing WorkBudget; N/2N neutral list documents should show linear or n log n work, no all-pair DOM search. Keep current 16M/112 source limits.

### Node C — independent major-node review + one real HTML replay

After A/B pass, request independent architecture/quality review with explicit negative controls, complete old replay and source isolation. Repair every substantiated issue before publication. Then replay the existing verified HTML once in a new owned attempt: preserve original SHA/config/catalog, record actual backend/parser versions, selected support and scoped compiled input. Check source-specific frozen targets: list definition includes the server/cloud child; consumption mechanism retains its justified business parent or clearly reports unresolved ancestry; adjacent segment does not leak. Report content PARTIAL if hierarchy is not proved. Do not change gold to fit output.

No new paid summary is necessary to verify source structure; only after source checks pass does ROOT continue the separate formal summary/cache/RF node. Do not run full PDF/8k regression or repeated exhausted batches for this design node.

## Primary implementation touchpoints

| Owner | Path and responsibility |
|---|---|
| Native HTML facts | `src/company_wiki/document_normalization/html_parser.py`: `_OwnedText`, `_scan_children`, `_scan_cell_body`, `_emit`, final native attachment; keep old emission |
| Format versions | `src/company_wiki/document_normalization/units.py`, `__init__.py`: HTML current/legacy capability and selected version propagation |
| Replay | `src/company_wiki/document_normalization/replay.py`: existing exact matching, ordinarily no weakening needed |
| Wire projection | `src/company_wiki/document_understanding/observation_adapter.py`: whitelist native DOM observation, explicit/inferred heading source, body-part suppression fix |
| Typed input | `src/company_wiki/document_understanding/structure/contract.py`: bounded DOM descriptor parse/slot; do not repurpose NativePageProof |
| Unique parent owner | `src/company_wiki/document_understanding/structure/sections.py`: DOM list scope into existing frames and readable context; optional separate focused helper under structure |
| Existing output | `structure/__init__.py`: existing context output suffices for CF1a; no DOM-as-PDF proof |
| Existing closure | `src/company_wiki/source_catalog/narrative_native_dependencies.py`: reuse readable binding/closure; changes unnecessary for minimal path |
| Cache identity | `document_understanding/decision_inventory.py` plus existing format/source dependency identity; cover actual changed normalization helper |
| Tests | `tests/document_normalization/test_html.py` + new neutral DOM scope/integration test; reuse `tests/unit/document_understanding_selection/test_reading_native_list_ancestry.py` and `test_native_list_physical_observer.py` for PDF regressions |

## Investigation limitations and command errors

This report derives from current source, the bounded actual DOM observation and existing tests; it has not executed the proposed design. Source-only semantic hierarchy cannot be guaranteed by formatting alone. No claim of CF1 repaired or real-source content score improved is made.

Two exploratory reads requested a nonexistent `structure/semantic.py`, and PowerShell did not expand wildcard file arguments in explicit `rg` paths; those commands returned missing-path errors. Follow-up reads used actual `structure/__init__.py` and explicit dependency files. No test or implementation error is hidden. Only this assigned Markdown and its JSON companion are authored by this investigation.
