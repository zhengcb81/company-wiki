# Semantic selection v2 — frozen for independent review

Author: `/root/c3_pdf_env_independent_review`; 2026-10-26. This supersedes v1 implementation receipts, not the preserved initial independent RED. No commit/push by this agent.

## Root fixes

- **SEM-IR-01:** plan negation belongs to the existing shared predicate grammar (English and simplified/traditional Chinese). The resource observer has no separate negative blacklist. A different actor keeps its own actual resource observation.
- **SEM-IR-02:** resource headcount binding consumes the shared owner’s equal-length modal view, keeping original coordinates and original predicate interpretation. `will/将/將` targets yield plan-only, never achieved staffing.
- **SEM-IR-03:** prepare boundaries, modal indexes and period once. Repeated bounded queries inspect fixed neighbors with binary search and perform zero regex rescans. Project-noun and will-disclosure grammar is derived from existing shared patterns; inapplicable contextual scans are skipped using already observed modal tokens.
- Public single-observation and scope functions remain available; numeric commas, condition attachment, future frames, subject switches, referenced quantities, project nouns and source roles retain tests. 0.8 remains separate. No caps, budgets, work multiplier, planner ranking or gold fixtures changed.

## TDD and final validation

- Genuine new RED before product repair: **16 failed / 3 passed / 59 deselected, 2.85s**. Not an import-error test. Initial independent review files remain untouched.
- Initial focused implementation: **129 passed / 4.39s**. Expanded same-owner compatibility suite: **539 passed / 21.56s**.
- Final source after skipping irrelevant contextual scans: **539 passed / 17.16s** across original ten files plus prepared-context tests. All old assertions preserved; Ruff and `git diff --check` pass.
- Two warnings arise from intentionally disabled plugin autoload (`asyncio_mode`, timeout marker); no model or expensive full batch was run.

## Real scan accounting

Instrumentation delegates every actual compiled-regex operation and counts its input window across preparation and queries. It does not replace recognition with a fake counter.

| Neutral workload | 16 hits | 32 hits | 64 hits |
| --- | ---: | ---: | ---: |
| Separate comma assertions: total regex-input chars | 11,289 | 22,601 | 45,225 |
| One assertion, repeated targets: preparation + query chars | 6,670 | 13,390 | 26,830 |
| Additional regex-input chars from one-assertion queries | 0 | 0 | 0 |

Boundary input equals source length; modal input scans each bounded assertion once. Counts and per-pattern breakdown are in `scan-counts-v2.json`. Fixed resource charge stays **18**.

## Final source binding

| File | LF SHA-256 |
| --- | --- |
| `src/company_wiki/source_catalog/narrative_operating_resources.py` | `f2ebc6236524f8a6df0b7a0049c14555af71474d4a29bbc88e5641519641ae44` |
| `src/company_wiki/source_catalog/narrative_predicate_state.py` | `780b5792a5fdeb45a4f0c3679837edb805eec504a7914dd641eb02b35fa47979` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `6b77dc6193e2084674d6bda44599729bb48c5cbc446e8b54f03bfd1a967e122a` |
| `src/company_wiki/document_understanding/decision_inventory.py` | `1dead1dc88e686156289739264ae66e3ef72e66004b871985c9579e489c9c849` |
| `tests/unit/document_understanding_selection/test_reading_operating_resources.py` | `f3be33da958ec3494ac2b8232f61f53ab89d9ed0d62bfe3c3f1b2afa50dbbd08` |
| `tests/unit/document_understanding_selection/test_prepared_predicate_context.py` | `2fd27260553791f7e8816f437ae6cd5762da51ea5f0a2e7804613dc7f9e91a22` |

Raw SHA, sizes and evidence SHA are in `handoff-v2.json`.

## Limits and cleanup

- This is the current three-finding semantic repair, not universal natural-language understanding. No PDF, model, raw-source, paid-provider, production-config or new holdout work occurred.
- Resource consumers use prepared bounded assertion spans. Public compatibility still accepts a cross-delimiter target through a cached fallback; arbitrary overlapping unbounded targets are not the bounded API performance promise. Other existing consumers were not migrated.
- All test processes completed. Exact `C:/Temp/c3sem-v2` was verified and removed; cleanup receipt retained. Only the six owned files above changed for this node; no ROOT PWF/CI owner edits.
- **Next:** ROOT’s independent reviewer checks this frozen source and SEM-IR-01/02/03; ROOT then owns any final release, real source acceptance, commit/push and pause. No implementation continues from this agent without follow-up.
