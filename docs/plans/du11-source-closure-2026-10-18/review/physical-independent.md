# B2 physical source carry: independent frozen-source review

**Result: NEEDS_REPAIR (one shared statement-boundary cause, two independent controls fail).** This is an engineering review of physical multi-original support, not product-antecedent completion, real-source recall or paid-summary C acceptance. No production/test-fixture edits were made. Reviewed three exact files are SHA-bound below and remained byte-identical before/after the finite execution.

## Execution and source binding

- Author `test_cross_page_reference_plan.py`: all24 PASS.
- Independent pure controls:12 PASS /2 FAIL.
- Total: **38 cases,36 PASS /2 FAIL**, pytest24.06s, subprocess wall26.18s; no763-suite repeat.
- Actual WT source binding before/after:
  - `narrative_continuity.py`: `255368e962cc82b45a96504a341fdf13bdd36467a853f89292716f94b70181df`.
  - `narrative_reading.py`: `46c031ae78331975a8e69cb75140ba5d899a5dadbac28f530572b77a79fee01a`.
  - physical test file: `21120df389b44e328b286bb9dbd0d2375973f668b8f96b0e628b5558ac3a3a22`.
- Explicit WT/src and WT/tests on child PYTHONPATH; `-B`, no pytest cache, no plugin autoload, minimal allowlisted OS environment, network/model disabled, no API/config/key/original reads. Existing test conftest also blocks real sockets.
- Owned temporary test directory was created empty and removed; pytest's relocated basetemp emitted cleanup `removed=true`. No original or production catalog existed in that temp.
- XML/log/receipt: `physical-focused.xml`, `physical-focused.log`, `physical-focused-receipt.json`. Exact input UTF8 hashes and escaped pytest case IDs survive capture. The launcher completed tests, stored receipts and cleanup, then only its final console print raised a GBK UnicodeEncodeError; this is a reporting encoding error, **not** an extra source/test failure. No repeat of the tests was used to hide it.

## Confirmed P2 finding: an incomplete shared new-statement veto merges independent subjects

Owner: `narrative_reading._INDEPENDENT_SUBJECT` passed as `SourcePageFlow.independent_start` into `narrative_continuity._Analysis.pending_page_transition/page_edge`.

Using the same portable author fixture, left actual original page ends “公司的第一种设备尚在开展生产验”; next original page starts one of:

1. “本集團另一項目已開始量產。”
2. “Our new platform has begun production.”

Both are independent next-page assertions, but each produces a package whose support contains both original IDs. The new page gets attributed an unrelated unfinished predecessor. The independent control “The company has begun production of another product.” is correctly left separate. No original text/locator was rewritten, but the support scope is wrong, so the feature should not be accepted before this shared cause is repaired.

The source regex handles simplified “本集团” but not “本集團”; it also knows `our/the/this company`, not explicit new issuer-owned product subjects. This is not a geometry defect or a reason to broaden page joins. The native owner correctly delegates the boundary decision; its delegated policy currently misses valid explicit fresh statements.

### Minimal common repair and finite REDs

Use one **source statement-start** owner shared with existing statement splitting. Reuse the existing script matching/normalization responsibility for simplified/Traditional issuer forms and the existing operating grammar's bounded subject/NP + actual finite predicate/auxiliary evidence for explicit new subjects. Do not add company/product names or make every `Our` prefix independent, and do not build a second business dictionary inside geometry. Ambiguous linguistic starts may conservatively fail carry rather than manufacture an assertion.

Keep separate controls for:

- the two failed independent assertions above, with changed company/product spellings;
- ordinary simplified issuer + actual predicate and explicit Traditional issuer + actual predicate;
- an English issuer-owned product NP with actual finite predicate/auxiliary;
- true continuation “...delivered to” / “our customers, but rollout remains restricted.”, which must **not** become independent merely because `our` appears;
- a real dependent “these products...” plus negative/future qualifier, which must retain all original support/context or defer;
- no mutation of actual raw bytes or original locators and no unproved issuer substitution.

ROOT was notified before any source mutation. This report proposes no per-control permission or micro-signoff; a narrow repaired-source delta review is enough after ROOT implements/tests the common policy.

## Other reviewed physical invariants

### Correct current implementation choices

- Default `build_native_continuity` has no SourcePageFlow and remains same-page. The source opts in only when `parsed.coverage_complete` and PDF mime are true; unread, opaque and error controls reject carry.
- Cross-page candidate checks actual adjacent pages, same source/scope/frame/font/role, original ordinal/paragraph adjacency through proved furniture, bottom/top body positioning and actual nonempty column equality. Unknown, bool, blank, negative, NaN columns cannot certify an edge; column equality does not imply semantic resolution.
- `REPEATED_RUNNING_HEADER` diagnostic IDs alone supply the furniture set. The larger excluded-furniture union is not used as positive evidence. Intermediate unproved furniture retains an unresolved tail; the author's negative test now blocks both dependent originals rather than releasing them as standalone facts.
- Independent controls for changed source, role, coordinate frame, rotation, width, project scope all prevent a join. Existing author heading/table/section/font/page-gap/column controls also pass. This is evidence for barriers, not proof that every unsupported boundary can be semantically resolved.
- Window block cost uses `(source,page,pdf_block)`. `defer` emits page-local source ranges; `emit.page` is `None` for multi-page groups with actual `pages=[7,8]`. The separate original spans retain true pages and no synthetic native_range. The five-block number-reset test blocks every member; the final one-span budget test releases neither half.
- Source `blocked` members are excluded when generating complete-window packages, avoiding carriers that resurrect a known unresolved suffix. Native carrier logic retains its strict same-page implementation; no cross-page page-view parser was added.
- One parent WorkBudget is reused, native local work uses `.scoped`, already reviewed B1 reserve work remains in the existing source owner. The new boundary veto charges actual right-text scan before evaluation. On local/native failure, existing incomplete/unexamined and pending-run deferral channels are retained. No new balance/store/paid fallback or raised cap appears in the inspected diff.
- Existing96-span/48k-char limits, physical8units/4blocks/2048chars, public task/citation support-context interface, raw parser/locator/ref ownership remain unchanged. Product antecedent resolution is still a separate OPEN part of B2, not something this feature silently claims to solve.

### Honest limitations

This finite review ran no real PDFs and no model, so it does not claim CN's actual unknown column has become proven: **CN columnNone must still defer**. We did not rerun the existing763 tests or independently certify their outcome. Public two-view and typed source refs were reviewed for unchanged ports, not revalidated by a full downstream contract run here. Full default legacy and real-source/contentC remain ROOT's existing large-node responsibility.

## Follow-up

Repair the shared independent-statement boundary cause, freeze its affected source/test SHAs, rerun only its new continuation/independence matrix plus affected author group, then perform this same independent delta check. No new approval artifact, source copy or repeated global suite is needed for this finding. Keep missing/ambiguous product antecedent work explicitly OPEN.
