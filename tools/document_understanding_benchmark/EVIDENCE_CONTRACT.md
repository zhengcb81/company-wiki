# Additive evidence contract, du-observed/1

This is test observation data, not a permission or production SourceRef contract.
The parser/source layer owns byte and identity verification; the oracle stays
independent, reads mappings only, and never imports company_wiki.

## Original material

`selected_evidence` is an optional array. Absent/null means legacy unmeasured;
`[]` means the observer actually knows no original material was selected.
Each row has required nonempty `locator` and `text` from an actual original unit
in the observed immutable source. Locators are unique; only rows also present in
`selected_locators` can prove business recall. Never create rows from a model
claim or the flattened `selected_text`; the latter is legacy display only.

Optional fields: `page` (positive physical page), `line`, `line_end` (positive
original source line range), `unit_id`, `source_role`, `language`, `scope_id`,
`period`. Unknown metadata may be null. Do not fabricate physical pages for HTML:
its real DOM locator is enough when the gold declares `location_kind=document`.

Native observer uses actual parser units, requiring the public selected span
locator and raw_text to match an original unit. The SHA-bound source is read-only.
ROOT's DU observer must build rows from its actual final selected original units.

`context_evidence` has the same row shape but is optional metadata/disposition
material. It is evaluated separately, never silently counted as business recall.

## Supporting facts

Every gold `any_support_sets` is OR across groups and AND within one group.
Each anchor checks its original page or source line range plus exact quote.
An equivalent fully readable group can pass despite another opaque group. A
readable complete group without the expected fact is a miss; all groups unread
is UNAVAILABLE. A legacy observation lacking locator/text mapping is
NOT_EVALUATED and leaves the recall denominator, with an explicit unknown count.

Gold anchor `location_kind` is page/line/document; document is for a known
non-paginated source, not a way to evade a PDF page requirement. Historical HTML
virtual page=1 is retained but explicitly marked document, not claimed physical.
Gold may constrain `scope_id`, `source_role`, `period`; unknown source fields are
NOT_EVALUATED rather than guessed. A fact with `require_same_scope=true` must
have a common nonempty concrete scope across all anchors of one supporting group.
Use project/semantic-group scope only, never the entire document as a shared scope.
Generated claims are never a bridge joining anchors from unrelated projects.
Literal support does not establish semantic entailment: independent review remains
separate and cannot be replaced by role labels or a matching number.

Gold `target_kind`:
- required_business: concrete business mechanisms/events/stages/operating drivers.
- disposition_context: source form, reporting period, coverage, audit/format status.
- correctness_if_emitted: routine financial/shareholder values; no recall demand,
  but every emitted related claim retains contradiction/unit/period checks.
Legacy `document_meta` defaults to disposition_context; other legacy facts default
to required_business. No quote/importance is removed by reclassification.

## Context completeness

Each `semantic_units` item may add `required_locators` and
`dependencies_resolved` (boolean/null). The observer obtains the required set
from the real materialization/closure, not from unit.locators after truncation.
All members and required locators must be selected and have original text.
A self-reported completeness=complete alone is NOT_EVALUATED. Missing known
required material or an explicit incomplete semantic unit is FAIL. Unknown
requirements remain visible; this is no production authorization gate.

## Whole-result honesty

Critical business omission/integrity/correctness errors fail. Normal business
recall shortfall is PARTIAL. An unreviewed generated summary is PARTIAL; an
empty/incomplete/duplicate review cannot certify all claims. Pure financial
sources with no business facts can succeed with 0 selected spans/claims/calls;
context/semantic dimensions remain individually labelled rather than invented.

Mutation detection counts only a newly adverse per-check result relative to the
original observation. A baseline PARTIAL is never automatic DETECTED. Synthetic
fixtures test these rules, not real model quality or previously unseen companies.
