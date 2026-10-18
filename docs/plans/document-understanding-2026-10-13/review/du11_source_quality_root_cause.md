# DU11 source quality: common root causes and implementation plan

Status: READ_ONLY_DESIGN_COMPLETE / CONTENT_C_OPEN. Reviewed main HEAD `a8eef273a90ac1ddb0f79f8bdd36e7c47f8eb377` on 2026-10-18. This investigation read source and already-existing compressed C evidence only. No tests, workers, PDF parsing, models, network, keys, original writes or production edits. Companion JSON binds inspected bytes. Receipt-write HEAD advanced to `9daa0c3899e459eb719e3fa1ee6438b43fe6f172`; all16 inspected source files remain newline-normalized identical to the reviewed `a8eef273` source baseline. ROOT owns the next PWF/update/implementation.

## What the actual C receipts prove

The byte/provenance and recovery protections worked. They did not prove business relevance, assertion completeness, speaker identity or important-fact retention. These are different observations; the repair belongs before canonical source-card admission, not in a second model that rewrites/deletes quotations.

| Actual development case | Observation | Consequence |
|---|---|---|
| CN 64 tasks / 64 claims / 96 spans; 10/10 required business anchors | Exact selected support, 1 real POST, paid/activation/same- and cross-run recovery passed. t9 p125 is option-pricing/fair-value policy; t64 p124 is lease remeasurement; t4/t6 are applicability checkboxes. | Recall alone masks low precision. Exclude pure policy/template from business cards while keeping originals retrievable. |
| CN t3 p31, t32/t34 p17 | t3 ends `不利影` with no quality flag; t32 native range38–108 begins `求的同时`; t34 has `该系列产品` without a specific product antecedent in its support/context. | Correct hashes and right punctuation cannot certify left boundary, complete assertion or referent. |
| CN t8 p176–177 | Real acquired CMP capability/complementary products and expected synergies occur under acquisition/goodwill notes. | Financial-chapter exclusion would destroy useful business evidence. Keep actual/planned states and context. |
| HK 55 tasks / 55 claims / 96 spans | t55 auditor `We evaluated...internal controls...impairment assessment` is classified as issuer operating milestone/company statement; audit/wealth-management boilerplate also enters. | A company filing is the container, not proof that every embedded “we” is the issuer. |
| HK tables/context | t1–4 carry two-year headers but only2023 values; t19/20 contain labels without dated values; t9 contains values without a bound year; t42 links a p239 financial heading to a p241 glossary. | Table purpose and reference membership are insufficient for period/value/section closure. Approximate `over7,500` is not exact7,504. |
| US 59 tasks / 54 claims; selected8/8 but canonical6/8 required facts | First-fit fixed byte planning admits preceding accounting/navigation material then defers t55–59, including complete RPO375b/commercial368b/as-of2025-06-30/40%next12months t59. | Honest deferral is still a failed business objective. Allocation must consume source-owned priorities before POST, within the same byte cap. |

CN raw-scope anchors: t3 body `936ee0fa22fbbde8fa3fd9a7862bcccdf58148624cd2f30d265d4cbe17baaa3d`; t9 body `583ebd79d25fdc6eb0f7ff9911b96ba471baa5a4a17363fc2f8fc0b613c3c82c`; t32 body `a7bfc67fcd0b9090b3a193824ff726a28fdf7cea63b412af413b5d3fd8448cd6`; t34 body `24bffdf6c291d379cd109243d17aedaad38bd73f8972aed23cf23b5b00bff31b`; t64 body `550ee6675b77a12643f8349d80b61e7794eaa808bfbd2528cbd268bfdb25ae78`; valuable t8 body `bc10a68d3cbd5e3f56cea59ebd079f72ca7adc50c67bf9d0130b4e0b6eb15fe1`. IDs are incident evidence, never runtime match rules. All prefixes are canonical `urn:company-wiki:evidence-span:sha256:`.

The three runs are development regressions, not blind holdouts. CN invalid MiMo ranking is a separate bounded-ranking issue; HK FF alias mismatch is a separate adaptation issue. This report neither waives them nor conflates them with source quality. Actual real paid decode-fault recovery was not injected in these C runs; the earlier loopback proof remains separate.

## Responsibility graph: where the defects originate

```
actual native original units / speaker & section evidence
  -> physical provenance + assertion/antecedent/table closure
  -> ONE SourceOperatingSession / business-purpose assessment
  -> narrative_reading admission + complete required-reference packages
  -> summary_tasks (reference-only projection)
  -> source_cards (consume readiness, never reinterpret prose)
  -> deterministic whole-card budget allocation BEFORE model POST
  -> advisory ranking / paid-response recovery / public bundle
```

### R1 — Generic grammatical operating relations are treated as business-purpose proof

Owners: `src/company_wiki/source_catalog/narrative_operating_relations.py::SourceOperatingSession.fact/financial_only`, `narrative_business_policy.py::assess_reading_business_fact`, `project_reading_business_fact`, `reading_financial_only`, and `narrative_reading.py::_admitted/_candidates`.

`project_reading_business_fact` promotes relations to operating reasons/core_business and makes any relation a financial exemption. `reading_financial_only` immediately accepts that exemption and otherwise refuses to reject an eligible fact. Generic model/risk words can already yield eligibility (CN option-pricing model/risk-free-rate), so accounting-purpose detection cannot correct the mistake. Scoped business roles also admit non-factual prose in `_admitted`. Actual t64 has `operating_restriction`; its exact low-level predicate match was not re-executed here and must be captured in the portable RED trace rather than guessed from that reason.

Fix the existing source-session assessment, once per actual bounded support/context group: distinguish observed operating product/customer/process/contract mechanisms and events from accounting measurement, audit procedures, treasury policy, pure navigation and no-event templates. A syntactic actor/action/restriction is not itself operating purpose. Waive finance rejection only for a *bound operating-purpose relationship*, not every relation. Match a local relation/object scope, not whole documents; real acquisition, franchise mechanics, business leases, segment scope, consumption models, RPO conversion, product mix/logistics and concrete litigation/risk can be useful inside financial notes. No company/task/page blacklist and no unconditional financial-section ban. Unknown role/state remains an honest uncertainty, not a new manual permission.

`source_catalog/admission.py` is document/path/type processing admission; it is NOT this semantic owner. Do not repair source-card precision there.

### R2 — Physical continuity is mistaken for complete source assertions

Owners: `narrative_evidence.py::_sentence_fragments/_emit_pdf_text_units`, `document_understanding/narrative_continuity.py::_Analysis.emit/finish/edge/build_native_continuity`, `source_catalog/narrative_reading.py::_prose_reading_packages`, `narrative_native_ranges.py::native_range_unit/verify_native_range_span`.

The producer correctly preserves the leftover tail of a native PDF block with exact offsets. That tail does not necessarily end an assertion. Current continuity focuses on same-page measured native joins and right terminators; an initial singleton is not necessarily deferred. `_prose_reading_packages` handles only background/paragraph_event, excludes risk from this path, and can return a singleton fallback. Thus an open risk fragment can bypass closure. A right-closed native window can still begin in the middle of a word or depend on an omitted antecedent. `structure/paragraphs.py::classify_paragraph` labels some risk/event/background text “complete” based on discourse recognition; this is not a reliable assertion-boundary proof.

Add an explicit bounded source-readiness observation for *every* prose kind and singleton, carrying left/right/assertion/referent status and exact required-context IDs. Do not make “ends in punctuation” a sufficient proof. Keep existing strict frame/font/rotation/column/source/native-range checks. Native same-page windows remain same-page; any cross-page continuation must be a graph of actual original canonical spans, with measured adjacency/section/role evidence, not a fabricated multi-page native_page_view. If unavailable or over budget, mark deferred/open/unknown and preserve raw retrieval. Never append the missing `响`, delete `求`, invent a product name or trim away the troublesome portion to call the card complete.

### R3 — Concrete referent, speaker and support/context responsibility is not closed

Owners: `document_understanding/operating_states/relations.py::OperatingRelationSession.detect/detect_operating_relations/_bind_event`; `narrative_reading.py::_context`; `document_understanding/summary_tasks.py::build_summary_task_plan`; `source_cards.py::source_cards`; `narrative_evidence.py::summary_claim_type_for_roles`.

Operating-state context can contribute name classes and bounded relation references; this does not establish a unique concrete antecedent for “该系列产品/this series”. `_context` defaults non-QA support to all required members, including section headings. Structural membership is being presented as factual support instead of separating observed assertion support from contextual dependencies. `summary_tasks` validates existing IDs/parent/order/partition only; `source_cards` accepts parsed nonempty support. Neither should invent missing semantic proof.

The PDF producer sets ordinary source_role=company_filing; `summary_claim_type_for_roles` maps this to company_statement. That is valid container provenance but insufficient speaker attribution for an embedded auditor. Preserve the original container role and introduce/consume *actual observed actor/speaker evidence* in the existing source assessment; without unique evidence retain unknown/third-party attribution, never issuer milestone by default. Section headings are context, not fabricated actor proof; explicit third-party business information may remain valuable with its actual attribution.

Use the existing operating-state/source session to resolve unique bounded actual product antecedents and speaking actors; carry only references/proof status forward. Generic section title alone, chapter proximity or another product cannot lend identity. Keep negatives/plans/qualifiers as complete dependencies. `summary_tasks` projects those native decisions, `source_cards` consumes them and withholds unsupported card scopes; neither becomes a second classifier/parser/LLM. Do not add an approval/acceptance database.

### R4 — Operating table purpose is confused with dated metric closure

Owners: `document_understanding/structure/table_purpose.py::qualify_table/qualify_native_rows/qualify_package_table`, existing native table/field/header owners and `native_table_bridge.py::bind_native_tables`; `narrative_reading.py::_qualified_table/_candidates/_context`.

`TablePurpose` reports eligible/not_business/incomplete and eligible rows. This answers what kind of table was observed, not whether a particular value has its matching year, row label, unit and approximation qualifier. The graph can retain incomplete or competing representations without certifying which value belongs to2024. Reuse real native descriptors/cell/header provenance for a bounded metric-closure result. Closure must follow actual table/row/column/period/unit scope; text alternatives need their own proven context. Labels without values are not complete metrics. An incomplete table may retain independently complete business prose; don't silently let the incomplete representation assert a dated number. Competing native/text alternatives must not supply each other's missing fields by proximity. Stale nearest headings must stop at real section boundaries or remain unknown, rather than manufacture glossary attribution.

### R5 — Order-dependent first-fit allocation hides useful tail evidence

Owner: `automation/narrative_model_extractive.py::compile_extractive_plan` (actual whole-card UTF8 accounting); metadata owners `narrative_reading` + `summary_tasks`.

The current loop processes `source_cards(plan, known)` in native task order and fills fixed draft bytes. Advisory model ranking runs afterwards, so it cannot restore a late RPO card excluded before POST. Keep exact whole-card accounting/deduplication and every task row. First improve R1 precision, then consume one source-owned bounded priority/coverage policy in this allocator. Priority comes from actual reading strategy/operating relation/purpose/closure metadata, never gold, company name, task key or model preference. Keep stable task/evidence identities; choose a deterministic stable order under the same byte cap and emit explicit deferred reasons. Changes should be order-robust for important operating mechanisms across CN/HK/US, not claim an unbounded optimal knapsack. Reuse precomputed serialized sizes and bounded sorting; charge work at the existing owner and do not repeat source parsing/classification. Keep max96 spans, existing work/character caps,64KiB final/56KiB draft and32KiB report. No extra paid request.

## Smallest shared interface change

Prefer extending the existing source-session result and reading package metadata; do not create another registry, cache, summary store or reviewer gate. A compact immutable per-package assessment may carry:

- purpose: operating / accounting_policy / audit_procedure / template_no_event / unknown, with finite reason;
- physical/left/right/assertion/referent/speaker/table closure states (proven / open / ambiguous / unknown), actual proof/context unit references only;
- ready / deferred / irrelevant, a bounded reason, and source-policy priority/coverage class;
- actual relation/subject/modality provenance, leaving uncertain or third-party descriptions honest.

This is a proposed implementation shape, not an existing API. ROOT should freeze the minimal concrete schema at node A. Avoid multiplying independent classifiers: one cached source assessment feeds selection and card readiness. `SourceSummaryTask.to_binding()` must bind any carried readiness/priority so request identities reflect it. All selected tasks get a bounded execution disposition. A semantic omission must not be disguised as invalid locator, model failure or missing authorization. Original raw spans remain accessible whether or not a card is useful.

## Portable TDD specification (before implementation)

| RED family | Required result and paired control |
|---|---|
| CN/繁體/EN fair-value share-option and IFRS16 lease-measurement policy using model/risk/termination words | Not operating cards. Positive: new AI product model, a real factory/customer lease and new acquired process capabilities inside the same notes. |
| CN/HK/US auditor evaluation/testing/going-concern boilerplate within a company filing | Never issuer operating milestone. Positive: actual issuer tested/launched a named product; useful explicit third-party business change remains third-party. |
| N/A checkbox, section cross-reference and treasury approval template | No false business event. Positive: specific negated production/customer statement and a mixed template with a separately complete actual business assertion. |
| Risk singleton ending `不利影` / English word tail; page-start `求的同时` / partial English word | Source kept, card deferred/open until actual context proves closure. Final punctuation alone must not make it ready. No letter repair/trimming. |
| Same-page measured wrapped statement and permitted original multi-span continuation | Retain exact original IDs/locators and all qualifiers. Reverse order, other parent, cross-column, missing frame, incompatible font/rotation or intervening heading must not join. Preserve strict existing native-range tests. |
| `该系列/該系列/this series` with one explicit product vs generic heading/multiple products/another speaker | Ready only with unique actual bounded antecedent refs; otherwise deferred/uncertain at the appropriate granularity. Do not borrow a question as the answer's factual support. |
| Two-year header + old-year-only values; labels only; numeric row without date/unit; approx vs exact | No false dated metric closure. Positive: actual same native row/column headers, units and values; independently complete prose can remain. |
| Long accounting/template prefix + complete late RPO/order-conversion passage, reordered unseen-company controls | Under identical actual UTF8 cap, retain important admissible business card and explicit dispositions without truncating it or increasing caps. Move source order/task keys without changing business priority outcome. Pure money balances remain negative, real RPO scope/recognition mechanisms positive. |
| Budget/context unavailable | Explicit bounded defer; no singleton fallback bypass or second uncharged recognition. Existing unknown-budget/paid usage remains intact. |
| Cache/dependency causality | Changed source readiness/policy/continuity/priority implementation changes current causal identity; old paid v4/v5 generation remains immutable/read-only, never silently re-signed as repaired quality. |

Existing tests to extend/reuse, not all to run: `tests/unit/document_understanding_selection/test_reading_native_continuity.py`, `tests/unit/du11_production/test_native_prose_continuity.py`, `tests/unit/test_narrative_native_ranges.py`, `tests/unit/test_source_summary_tasks.py`, `tests/unit/test_narrative_extractive_runtime.py`, `tests/unit/test_narrative_partial_source_admission.py`, `tests/unit/document_understanding_selection/test_reading_decision_inventory.py`, `tests/unit/document_understanding_selection/test_attributed_context_quote_oracle.py`, `tests/unit/du4_operating_states/test_root_boundaries.py`, `tests/unit/du4_operating_states/test_b_synthetic_specs.py`, `tests/unit/du4_operating_states/test_c_contract.py`, `tests/unit/du11_production/test_native_table_projection.py`. Preserve existing paid/activation/cache controls at the one concentrated integration gate; don't replay the entire historic suite per small fix.

## Implementation order and three acceptance nodes

**A — Freeze portable RED and minimal source contract.** ROOT begins in an isolated branch/worktree. Use synthetic CN/TC/EN fixtures plus compact exact incident anchors. Capture actual assessment reasons/relations, not just accepted strings. Freeze unique owners and expected source dispositions. All above is implementation work, not a new authorization gate.

**B — Fix shared owners and perform one concentrated cross-layer gate.** Source session relevance/actor + physical/assertion/referent/table closure -> reading admission/context -> reference-only task/card -> deterministic whole-card allocator. Test raw canonical IDs, actual closure reasons, current/planned/negated/third-party states, exact byte bounds and important-fact retention. Independently review final source SHAs and fix all confirmed defects. Keep runtime changes out of FF/RF author worktrees. No per-function sign-offs.

**C — Actual production quality, then unseen-company holdout.** First replay captured original support and existing paid-response observations offline without altering old run/generation or claiming a new production call. After offline precision/closure/recall pass at frozen committed version, ROOT runs the configured three suppliers serially under the existing cumulative mother budget and actual provider config. Check source precision and canonical critical-fact coverage separately, every task disposition, explicit raw-context closure, actor/period/unit/approximation, real paid/activation/same-cross-run0POST, consumers and test-directory restoration. Three current companies remain regression fixtures; then use different companies for genuine holdout and the planned RF audit loop. Content C stays OPEN until those agreed checks actually pass.

### Version and cache obligations

`document_understanding/decision_inventory.py::_versions` already binds actual business-policy/continuity/table/native versions and current PDF producer algorithm hashes. Its PDF algorithm tuple does not explicitly hash `narrative_reading.py`; a new readiness owner must have a real semantic version/actual source dependency in the current appropriate identity, not a manually frozen SHA. `automation/narrative_model_extractive.py::extractive_boundary_identity` already hashes source_cards, summary_tasks, protocol and role-quality owner, so changes there naturally alter boundary identity. Verify this causally with a narrow test and update the actual source semantic version when behavior changes. Do not use old immutable capture/request hashes to certify new code, and do not relax old raw replay/hash/generation/usage checks.

No completed quality claim is made here. This plan specifically prevents another cycle where all tool tests pass because quotations match already-defective selected fragments.
