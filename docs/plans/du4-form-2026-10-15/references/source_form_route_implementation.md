# §7.6 Source-owned FORM / call routing repair — read-only implementation design

**SOURCE/tests/PWF/Git STOP.** This document proposes the next ownership window; it does not implement a fix or certify new document types. Current publish remains ROOT-owned.

## 1. What is actually established

The saved `type-matrix-root/root-cause-followup/us-10q.json` establishes the real VRSK source failure: its visible **9-character `FORM 10-Q` at paragraph 4 / DOM `0.1.2.8`** is absent from 200/2,274 probes. Two genuine normalized `html_table_cell` / `company_filing` units contain only `Revenues:`. They become `SPEAKER_TURNS`; the primary route is wrongly `earnings_call`. A real visible `dei:DocumentType` in the already-read HTML contains `10-Q`. Supplying its value through the current generic `form_type` argument changes the route to quarterly but wrongly cites fallback cover/TOC units. That counterfactual establishes a missing observation path, not a valid final provenance fix.

This task performed **16 finite pure routing counterexamples**, one initial adapter-shape observation, and one additional identity-correct adapter observation: **18 observations total, no original parse, no normalizer/model/network/supplier call**. `observations.json` and `adapter-identity-observation.json` retain actual results. The second adapter observation recomputes the saved `Revenues:` unit ID exactly from the saved original SHA, DOM locator, literal text, native kind and role. It confirms:

- Adapter preserves the table carrier as `table_row` and role `company_filing`; it does not invent `management`.
- The routing `UnitRef` reduction retains kind/role but loses source-parent, speaker and turn hints. Structure `ObservationUnit` already retains those fields and protects real QA association.
- Arbitrary financial/header/caption colon labels also trigger a call. Adding `Revenues` to `NON_SPEAKER_LABELS` cannot repair the class of error.
- True named prose turns and true attributed turns inside a table remain calls in the current controls. A blanket table exclusion would break valid data.
- A policy-shaped title with actual native Q/A is correctly investor QA. Keep that control; do not force the saved IR specimen to administrative.
- Pure router Q/A can incorrectly pair different parents. Production `_understand` already partitions parents, and structure QA already checks source/turn association; keep those controls rather than rebuilding them.
- Outer `FORM 8-K` with actual call/10-K attachments correctly preserves the container and child routes. However a bare parent `10-Q` / supplied form value can lose to a child's printed `FORM 10-K`. Observed facts need scope, not unconditional metadata preference.

All source/package-policy/config/saved-receipt SHA, size and mtime checked during the primary probe stayed unchanged. The first adapter-shape wrapper used a synthetic parent/default MIME and is **not** an identity-certified reconstructed native record; use the corrected additional observation for identity/HTML assertions. No claim is made that the synthetic surrounding 2,274 units reproduce every real VRSK unit. The original real decision is already saved independently.

## 2. Current interfaces and exact responsibility gap

| Layer / actual file | Existing behavior | Correct repair responsibility |
| --- | --- | --- |
| `document_normalization/html_parser.py` `_emit`, `_walk_owner`, `_scan_children` | One already-open visible DOM walk; owns normalized text, DOM location and stable native units. Visible DEI text is retained, its native fact attributes are not exposed. | Observe a bounded own-form carrier during this walk; no second parse or document-family decision. |
| `document_normalization/document.py` `NormalizedDocument` | Has optional document metadata. | Do not place essential facts only here and then discard them when callers take `.structure`. |
| `source_catalog/narrative_normalization.py` `language_structure` | Copies unit metadata but returns `DocumentStructure`; general document metadata is dropped. | Reuse this surviving unit-carrier path, or explicitly wire a typed structure field. Do not add an unused metadata blob. |
| `source_catalog/narrative_document.py` `NarrativeUnit` | Has immutable metadata; `to_evidence_span` already strips transient layout fields. | If source observations live in transient unit metadata, strip that finite reading-only carrier before durable spans/legacy inputs. |
| `document_understanding/observation_adapter.py` `build_observation` | Passes limited optional document metadata and source/speaker/turn hints. | Project source-captured form facts using their actual units; declared source metadata stays separate. |
| `document_understanding/profiles/observation.py` `parse_observation` | First three plus spread heading/body probes; `UnitRef` discards turn/source hints. | Reserve genuine fact carriers inside existing caps and retain typed role/parent/turn information needed for routing. |
| `profiles/signals.py` `_detect_sec`, `_detect_qa_and_call` | Generic `form_type` fallback gets cover IDs; call inference accepts text-shaped names alone. | Form provenance and scope; positive unit-aware turn evidence. |
| `profiles/decision.py`, `profiles/child_ranges.py`, `profiles/__init__.py` | One primary/child route owner; actual attachment completeness is honest. | Consume scoped facts and maintain parent/child arbitration; preserve unread/partial ranges. |
| `source_catalog/narrative_reading.py` `_understand` | Calls existing `understand_units`, partitions native parents. | Integrate optional observed facts only through that existing owner; keep parent isolation. |

These are **actual** paths, including files the CodeGraph index currently omits. Earlier provisional `normalization/...` or `profiles/observation` guesses must not be copied as different project directories. No new router, Source Store, cross-repo writer, identity receipt or approval chain is needed.

## 3. Minimal source-observation contract

Freeze one small internal contract before implementation. Recommended exact NEW module: `src/company_wiki/source_contract/document_observation.py`, a lower, standard-library-only value contract. It must not import normalization, SourceCatalog, structure, routing or a Store. The profile package may consume this common contract without acquiring those stage dependencies. Recommended record:

```python
@dataclass(frozen=True)
class SourceFormObservation:
    value: str                     # exact normalized source value, e.g. "10-Q"
    origin: Literal["visible_inline_xbrl_document_type", "visible_own_form_label"]
    carrier_unit_ids: tuple[str, ...]  # actual same-parent units, not cover fallback IDs
```

Source ID, source byte SHA and locators already exist on the observation/units; do not duplicate them in signed receipts or invent timestamps. DOM location is the existing native unit's location, not a new locator. The parser observes literal facts; the existing profile router alone decides quarterly/annual/offering/call and chooses scope. Unknown form values remain observed literals and route conservatively rather than growing a hardcoded company/file list.

**Recommended transport:** a bounded transient `reading_source_observations` entry on its native carrier unit, copied through `language_structure`, then projected to optional `du-input/1.metadata.observed_source_forms`. The record can point to the actual carrier after its stable ID is built. Unit identity does not need a new raw digest; no raw text or full DOM is durably copied. `NarrativeUnit.to_evidence_span` must remove this reading-only field, following the existing transient-layout pattern. This is preferable to adding document metadata that `_understand` never receives.

If ROOT instead chooses a typed `DocumentStructure` field, the same record/semantics must pass normalizer→structure→`_understand`→adapter; choose **one** transport. Do not support two competing form sources.

Contract invariants, validated at the owner boundary once:

- Actual carrier IDs exist in the current immutable parent; the visible value is represented by those native units, with actual DOM/locator provenance.
- Plain provider `form_type`, file title/stem, declared document kind and source metadata **never manufacture** an observed record. They can remain suggestions/conflict diagnostics.
- Hidden, excluded, external-linked, missing-carrier or foreign-parent facts do not silently become observed parent-form proof. Hidden-only DEI is not certified by this visible-carrier design; retain a diagnostic until an explicitly replayable hidden-byte contract is designed.
- Same-owner inline wrapping is allowed. Multi-owner/split text needs a source-captured same-parent association; do not concatenate adjacent unrelated cells into an invented `FORM` unit.
- Keep the record finite (proposed up to eight own-form observations, each at most four actual carrier IDs and a short literal value). Overflow/ambiguous scope is visible. These are candidate implementation bounds, not a finding that all documents fit them.

The route's `COVER_HEADING`/form reason must cite the actual carrier IDs. If a declared-only fallback remains for compatibility, its reason explicitly says declared metadata and has no fabricated observed-cover provenance. Do not fix a label while leaving its reason false.

## 4. Bounded route and turn algorithms

### FORM / probe allocation

Actual current routing defaults are **200 probe units / 64,000 probe characters** (`profiles/vocabulary.py`). These are distinct from formal selection's **96 spans / 48,000 selected characters**. This task keeps both defaults; do not confuse one layer's caps with another or raise either to hide the missing nine-character carrier.

1. Producer observes visible `dei:DocumentType` at its existing DOM owner and a literal standalone own-form line. Reuse one finite source-form lexical observer; do not duplicate company/type classifiers or broad corpus inference in normalization.
2. Adapter forwards genuine records. Probe allocator reserves their actual carriers **before** first-three/heading/body spread, deducting their units and characters from the same current caps. It then fills remaining slots with the existing deterministic strategy. No increase to 200 units or current char budget, and no hidden scan that is reported as only 200 observed text units.
3. If a lowered caller cap cannot fit a carrier/record, report it as limited/deferred; do not claim to have observed it. IDs/ordinals alone cannot provide textual form evidence.
4. Reuse the existing attachment boundary/range owner to scope carrier facts. Parent inference must exclude a known child-owned carrier; a child receives only observations whose carriers belong to its actual same-source range. `child_ranges` must filter the new record when it clears parent metadata. No second primary classifier.
5. Genuine own-source form and readable structure outrank declared/file suggestions. Contradictions remain diagnostics. An unread container/attachment is not assumed to have the family's full business coverage.

### Call / QA

Keep regex-shaped `Name:` only as a lexical candidate. A routing predicate consumes `UnitRef`, including native kind, role, source parent and genuine speaker/turn hints, and requires a real speech body/associated continuation or source-owned turn association. Empty labels, table/header/caption furniture and regular `company_filing` financial cells cannot count as turns merely because their text matches a capitalized colon regex. This repairs arbitrary `Revenues:`, `Headcount:`, `Utilization:` and future labels without a blacklist.

Positive attributed table-shaped turns remain valid; table shape alone is not a rejection rule. Prepared statements may provide transcript speaker evidence but must not become investor answers or an invented Q/A pair. Marker fallback for untyped prose is anchored and scoped, requires a genuine same-parent question→answer/turn association and non-furniture content, and never pairs unrelated parents. Preserve actual declared-source versus observed-turn distinction.

Use current structure QA's role/turn/source semantics as controls. Do not import structure's mutable stage or rebuild its exchanges inside routing; project one source-owned hint contract and evaluate it within the existing pure profiles package. The reproduced IR denial omission has correct structured roles, grouping and closure already; its fix is shared operating-meaning admission, not route/QA reconstruction.

## 5. TDD implementation and review nodes

No tests have been written in this read-only task. Proposed new files below are **NEW test paths**, not existing documents to search for:

| RED group | Proposed package and exact assertions |
| --- | --- |
| A — source carrier | `tests/document_normalization/test_source_form_observations.py` (NEW): public HTML normalization with three incidental lead units, visible FORM/DEI at fourth paragraph, many ordinary units, arbitrary financial colon labels; genuine source carrier/DOM/IDs, source bytes unchanged, same-parent inline wrapping, hidden/unrelated/foreign carrier negative controls. No filename-selected answer. |
| B — bounded route | `tests/unit/document_understanding_selection/test_observed_source_forms.py` (NEW): exact carrier included at unchanged 200/current chars; real form reason cites it; zero/tightened budgets honest; declared wrong form is diagnostic; no observed field derived from plain `form_type`; 8-K parent plus complete/unread external/partial 10-K/call child; child cannot replace parent or inherit parent facts. |
| C — speech semantics | `tests/unit/document_understanding_selection/test_scoped_route_turns.py` (NEW): arbitrary empty/nonempty financial labels and header/caption furniture are not calls; named operator/CFO/analyst prose and genuine attributed table turns stay calls; real Q/A under policy-shaped title; prepared statement/rhetorical question controls; foreign-parent/wrong-turn no pairing. |
| D — production E2E | `tests/integration/test_source_form_routing_e2e.py` (NEW): public normalize→language structure→formal 0.9 pipeline→selection over isolated synthetic SEC HTML; quarterly route, actual form carrier reason, no false SPEAKER_TURNS, expected scoped reading profile, raw/native locator and original bytes stable. Existing None/v1 historical/ref and old 0.8 wire/replay remain controls. No fake successful route/selector callbacks. |

Implementation sequence:

1. Write A/B/C with independent expected carrier/role/scope assertions and run actual RED. Save all failures; a schema setup error is not semantic proof.
2. Implement the single source observation transport and bounded allocation, then unit-aware scoped signals/arbitration. Do not modify decisions in consumers to compensate for missing source facts.
3. ROOT wires transient exclusion, integration and causal version inventory. Run one concentrated unit/contract node, preserving old identity/bytes and the lowering-only budget API.
4. At the **large** integration node only, run D and one fresh bounded replay of the saved VRSK original (source opened once, deadline/guard/Temp; no durable raw/MD copy). Compare wrong-call→quarterly and actual reason IDs, not only route name. A separate genuine transcript/8-K-attachment original is a needed holdout if available. If no real specimen exists, say not evaluated; synthetic controls are not certification.
5. Independent focused quality review compares form/turn provenance, scoped reading and actual selected business content. ROOT normal commit/push and PWF update. No per-item approval, manual contract signoff or added tiny gates.

Do not raise parsing/probe/span budgets, remove honest coverage state, edit gold to obtain a green label, replace errors with generic success, or count DEI declared metadata as observed source. Real new-type coverage without samples remains **NOT_EVALUATED** (particularly unseen SEC form variants, hidden-only DEI and multilingual/split covers). HKIPO parser cost remains a separate resource-owner task, not a justification to weaken this route.

## 6. Nonoverlapping next-window ownership

| Owner | Exclusive writes | Output interface to ROOT |
| --- | --- | --- |
| FORM/route lane | `document_normalization/html_parser.py`; NEW `src/company_wiki/source_contract/document_observation.py`; `document_understanding/observation_adapter.py`; `profiles/observation.py`, `signals.py`, `decision.py`, `child_ranges.py`, `__init__.py`; its NEW A/B/C tests. All existing source paths in this table are relative to `src/company_wiki/`. | Minimal observed record + actual carrier provenance + bounded route decision; never budget/LLM/Store state. |
| IR operating meaning lane | `source_catalog/narrative_business_policy.py` and its already-existing single policy catalog/compiler assets **after that owner inventories exact paths**; its separate NEW predicate/admission tests. | Shared `detect_reading_business_fact` eligibility/topics/reasons for operating state/denial and relationship stage, preserving actor/modality; no parser/QA/router edits. |
| ROOT integration | `source_catalog/narrative_document.py` transient strip, any necessary `narrative_normalization.py` / `narrative_reading.py` glue, `document_understanding/pipeline.py` and causal inventory/dependency version wiring; NEW production D and existing shared fixture adjustments. | One source-owned production path, real replay, legacy/cache verification, PWF/publish. |

The FORM lane and IR lane can run concurrently **after ROOT freezes the small record/predicate interfaces**. They must not both edit `narrative_reading`, `pipeline`, causal inventory, shared support or public model boundaries. ROOT stitches their outputs. No changes to filing-fetch/RF/Dayu are required for these two root causes.

## 7. Evidence and STOP

- `probe.py` / `observations.json`: actual 16 current-code routing outcomes, intended future controls, bounded counts; inputs unchanged.
- `adapter_probe.py` / `adapter-identity-observation.json`: saved unit identity matches; actual HTML native kind→wire mapping and lost router fields, no parse.
- `protected.json`: exact read-only source/config/saved-receipt guard window.
- Earlier real `type-matrix-root/root-cause-followup` remains authoritative for VRSK original and IR actual omission. No original or gold was modified or parsed here.

STOP pending ROOT publish and the next explicit implementation window. This design does not introduce permission controls; it defines the evidence responsibilities that make routing reliable.
