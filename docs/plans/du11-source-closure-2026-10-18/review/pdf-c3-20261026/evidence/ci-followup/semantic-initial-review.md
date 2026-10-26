# C3 resource semantics — independent review

Reviewer `/root/c3_cache_independent_review`, not the semantic implementation author. Date 2026-10-26.

**CHANGES_REQUESTED — three P2 findings OPEN.** The production layer placement, finite source-derived topics, legacy separation and dependency hash addition are appropriate. The resource observer still exposes common predicate gaps and repeats full-sentence scanning. Author GREEN does not close these counterexamples.

## Frozen review scope

The following four hashes match the author's `handoff.json` exactly. Raw SHA and byte sizes are preserved in `scope-cleanup.json`.

| File | LF SHA-256 |
| --- | --- |
| `src/company_wiki/source_catalog/narrative_operating_resources.py` | `33794202dff05867e2a81cbd97f2011061e6977a521bf9f235846c51d51cd6e9` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `6b77dc6193e2084674d6bda44599729bb48c5cbc446e8b54f03bfd1a967e122a` |
| `src/company_wiki/document_understanding/decision_inventory.py` | `1dead1dc88e686156289739264ae66e3ef72e66004b871985c9579e489c9c849` |
| `tests/unit/document_understanding_selection/test_reading_operating_resources.py` | `41cfa30ad1439f45eee20149fc5a0da2db0df703db0093c2e48e3635a4470c98` |

Also inspected existing `narrative_predicate_state.py` (LF `0f002d36ab8d4d32af1c2d62af54a4f02b7b986fd08216a5e41125f75d75d27b`), SourceOperatingSession work admission, matching-text conversion and the published `SELECTION_ROOT_DESIGN.md/json`. No product or existing test file was changed by this review.

## SEM-IR-01 / P2 — negated plans become positive operating plans

Location: `narrative_operating_resources.py:131` consumes shared predicate state; `narrative_predicate_state.py:_MODAL` does not recognize the common negative governing forms below. Production projection at `narrative_business_policy.py:808` consequently upgrades them to `eligible=True`, reason/topic `operating_plan` (and meaningful material value), despite their explicit denial of a plan.

Actual failing examples:

- `We have no plans to invest in research and development.`
- `We have no current plans to invest in research and development.`
- `公司暂无计划投入技术研发。`
- `公司不计划投资技术研发。`
- `本集團暫無計劃投資技術研發。`

Controls `We will not invest USD 4 million in research and development.` and `公司尚未确定计划投入技术研发。` correctly receive no new positive resource/plan reason. Thus this is a governing-negation gap, not an issue with the neutral fixture or all negative classification.

Fix in the **shared predicate owner**: model negation of the plan predicate, with bounded scope and language parity. A negative resource statement can remain useful source restriction/context, but it cannot assert an existing positive plan. Do not add a second blacklist to the resource observer, suppress the entire paragraph, or drop another actor's independent affirmative statement. Freeze these and subject-switch/conditional controls in the shared owner plus production projection tests.

## SEM-IR-02 / P2 — ordinary future personnel targets do not bind to their resource

Location: `narrative_operating_resources.py:33` (`_COUNT`) has a closed adjacency vocabulary between the workforce subject and quantity. It accepts observed `numbered/reached` and some constructions with an outer expectation, but rejects `will`/`将` in that same relation before the shared state owner can classify them.

Actual failing examples return `eligible=False`, empty reasons/topics:

- `Our research staff will number 2,400 people next year.`
- `Our R&D staff will reach 2,400 employees next year.`
- `公司研发人员将达到2,400人。`
- `本集團研發人員將達到2,400人。`

The semantically equivalent outer-expectation control `We expect our research staff to reach 2,400 people next year.` does produce `operating_plan`. These are core explicit-quantity future forms from the design, not a demand for a universal natural-language parser.

Fix resource relation binding so it retains the subject/quantity/unit and relevant predicate span across ordinary auxiliaries; let the **single shared predicate owner** determine future/actual/negative/conditional meaning. Expected result is plan-only, never `operating_resource_stock`/allocation. Preserve direct headcount, future alternatives, accounting/identifier borrowing and same-actor boundary tests; do not infer future resources as achieved.

## SEM-IR-03 / P2 — fixed work charge hides quadratic sentence rescans

Locations: `narrative_operating_resources.py:111`, `:126`, `:131`. For every comma-delimited assertion, the observer passes the entire sentence to `observe_metric_predicate` once for the frame, then again for every matching resource/action. That shared function recomputes sentence and assertion boundaries with full-input scans. Adding `RESOURCE_READING_SCAN_PASSES = 18` does not make this fixed work.

The deterministic independent probe repeats the neutral, valid clause `our R&D staff numbered 2,400 employees` in one comma-separated source sentence:

| Assertions | Input chars | Predicate calls | Sum of predicate input chars | Declared resource work |
| --- | ---: | ---: | ---: | ---: |
| 16 | 638 | 32 | 20,416 | 11,484 |
| 32 | 1,278 | 64 | 81,792 | 23,004 |
| 64 | 2,558 | 128 | 327,424 | 46,044 |

Doubling the source length produces roughly four times the repeated full-text predicate input. These counts are a lower-bound input-volume diagnostic, not a wall-clock benchmark; the shared predicate function itself performs multiple scans. The issue is visible with only 2,558 characters and is not prevented by the finite document cap. Exhausted-entry fallback avoidance is correct but does not account for work after admission.

Fix by preparing shared predicate context/boundaries once and reusing bounded assertion spans, including inherited leading condition/future/subject context. Resource matching must consume that prepared owner result rather than rebuilding it per candidate. Do not merely increase 18, truncate valid source statements, add per-document exceptions, or fork predicate vocabularies. Verify linear deterministic scan growth and unchanged semantics for numeric commas, leading conditions, subject switches, and coordination.

## Validation and observations

- Independently ran `test_review_probes.py`: **10 failed, 3 passed**, 1.54s, exit 1. Five negative-plan failures, four future-target failures and one scan-growth failure. `review-red.log/xml` and `scan-counts.json` are the actual RED evidence. No repair is implemented or claimed green by this reviewer.
- Inspected author receipts: early new suite 47 passed; final focused suite **498 passed**, including 58 new cases, across ten files. These were not needlessly rerun and do not cover the failures above.
- The new resource entry is called only by the production projection, and exhausted `include_description=False` avoids it. The old text detector is unchanged; the current author compatibility test verifies that separate boundary, rather than altering legacy expectations.
- New module is in business algorithm fingerprint inventory and policy increments `/19`→`/20`. Selection caps and `reading_plan/3` remain unchanged. Topics are finite and source-derived; no company/page/market exceptions or financial value conversions were added.
- Existing author tests and inspected code preserve source role filtering, actual third-party resources without inventing issuer attribution, conditional plans without actual resource reasons, full native context closure, mixed accounting/personnel text and original wording. This review did not find another confirmed failure in these controls; it does not claim exhaustive linguistic coverage.
- ROOT's known-source HK observation and industry-cloud C2 gap remain separately owned. No holdout, PDF, Docling, LLM or raw-company input was opened by this reviewer.

## Cleanup and next node

Reviewer-only `C:/Temp/c3semantic-review-20261026` was absolute-boundary checked and removed; no scoped Python process remained. See `scope-cleanup.json`. The probe source and small evidence files are intentionally retained.

ROOT should authorize the original author to extend the existing predicate owner as necessary, implement the three shared fixes with these RED cases, then request a final independent review bound to the new source SHA. Related predicate/resource/source-selection tests are appropriate; there is no reason to rerun expensive full PDF/Docling or paid summaries while these small owner tests are still red.
