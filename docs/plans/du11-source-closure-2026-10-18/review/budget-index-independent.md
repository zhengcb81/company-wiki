# B1 shared budget / metadata indexes — independent review

Final verdict: **PASS_B1_ENGINEERING**. The two findings below are fixed and independently rechecked. This is not a B2 cross-page/reference review or a real-provider C acceptance.

## Reviewed working bytes

- `src/company_wiki/document_understanding/narrative_continuity.py`: `5e9b2dc07ad9d79bafc47efe8e95256b0dccc0caa59d6dc43f8f06a2802084f0`.
- `src/company_wiki/source_catalog/narrative_reading.py`: `6a76203353b81c0e50881607851fdd1f91925942381bad873c64787a9940fdfe`.
- `tests/unit/du11_source_closure/test_source_metadata_budget.py`: `912b2df330badcc86f7d94e612e07831207c4cb7c82f2340fd1f7a26fbe7f5be`.

Reviewer read the two production diffs, full affected functions, current `WorkBudget` owner, actual dependency hashes and all nine final tests. No source edits, model/API/PDF access or large test rerun. Tiny independent controls explicitly prepended this isolated `src` and `tests`; the actual module path was verified as this worktree, not the editable mother installation. The three final SHA values matched byte-for-byte before and after review execution.

## Findings, repaired and closed

### F1 (CLOSED): section metadata expanded before its reservation

Two entry points share this remaining preallocation-order defect:

1. `_candidates` charges the unit/exclusion indexes, then constructs its `headings` comprehension **before** `_prose_reading_packages` can reserve section metadata. With 96 existing source units, a section referencing 32 headings and 64 body IDs, and parent limit 300, the actual result was `used=193`, exhausted/partial `OPERATING_WORK_BUDGET`, but heading references had already been visited 32 times. The rejected attempt must not first build that unreserved collection.
2. `build_native_continuity` constructs `tuple(heading_ids) + tuple(body_ids)` before charging `1+len(ids)`. The same 32/64 section and parent limit 0 yielded `work_units=0`, partial, **32 heading and 64 body visits**. Local scope sharing does not prevent this allocation because reservation happens afterward.

Both controls use actual source-owned unit IDs, not megabyte text or an external original. Expectation: rejected section reservation leaves those counted sequences uniterated; derive the cost from sequence lengths before constructing copies/sets. `_candidates` should defer its heading collection until a suitable reservation succeeds, or reserve it explicitly in its existing budget. Preserve the current exact source refs and honest partial state; do not add a new budget, increase limits or make failing operations free. This is one resource-owner ordering issue, not a request to redesign B2.

Final correction: `_candidates` now runs the budgeted prose preparation before its separately reserved heading-set construction. Continuity reserves `1 + 2*len(heads) + len(body)` before any ID visit, then iterates with `chain` rather than copying the tuple. Both independent actual-ID controls now record **0 heading and 0 body visits** on refusal, retaining used=193/300 and used=0/0 respectively. ROOT's precise behavior RED is retained in `budget-preallocation-red.log`: 7 passed, 2 failed / 5.71s.

### F2 (CLOSED): four new test cases did not reach the claimed behavior

The actual `budget-index-full-green.log` ends **733 passed / 4 failed / 50.08s**, not green:

- `test_exhausted_parent_budget_does_not_start_an_unmetered_geometry_scan` references undefined/unimported `page_case`.
- All three `test_large_real_context_fanout_is_reserved_before_expansion` variants stop in `deepcopy(parsed)` with `TypeError: cannot pickle 'mappingproxy' object`, before invoking the budgeted path.

Use existing valid source fixtures and a stable original-IR projection/snapshot for equality rather than changing immutable production IR to satisfy `deepcopy`. Preserve the 0/1/1000 fanout assertions and add the section-preallocation controls above. No repeated 737-test suite is requested; a small corrected frozen group suffices for independent delta review.

Final correction: undefined `page_case` was replaced with the already supported `source_case`; recursive dataclass/mapping/sequence snapshot includes all original IR fields without pickling mapping proxies. No production IR mutability change was made. All three fanout variants now reach their original budget/visitation/no-geometry/whole-IR assertions.

## Valid parts retained

- `_Analysis` uses `work_budget.scoped(local_limit)` and charges the same parent; a local ceiling cannot reset or mark the parent globally exhausted. Reported successful work is the local scope's successful charges.
- External required context is indexed once per package and the excluded-member union once per invocation. The set difference and owner lookup preserve the previous external-context meaning; native grouping and original IR are not rewritten by the index optimization.
- Actual package membership/context fanout and section heading×body expansion are reserved before their corresponding new loops in `_prose_reading_packages`. The source catches metadata budget exhaustion as bounded partial, rather than publishing a fabricated smaller complete fact.
- `decision_inventory` binds actual normalized module-byte hashes: `business_algorithms` includes `narrative_reading`; `continuity_algorithms` includes `narrative_continuity` plus tail geometry. Both B1 source changes therefore invalidate the relevant cached algorithm dependencies, without requiring a fabricated version-only proof.

## Final independent verification and acceptance boundary

Actual independent final execution: **9 passed / 3.27s**, subprocess return 0; wrapper with three finite controls 12.778s. Controls replayed both original actual-ID refusals and additionally verified a positive source container with two support members and two external context refs: both resulting packages retain exactly those external refs. Source bytes before/after matched. Full command, hashes, controls and cleanup are in `budget-index-independent-green.json`; full small-run stdout/stderr and JUnit are in the corresponding `.log`/`.xml`.

Invocation used explicit isolated source PYTHONPATH, `-B`, disabled cache/bytecode and reviewer-owned temporary directory. Its outer directory was removed and independently checked absent; the existing Windows path relocation emitted its own `removed=true` cleanup receipt and its effective basetemp was also checked absent. No model, original PDF, network, large matrix, production config/database or draft B2 test was executed. No confirmed unresolved finding remains in this B1 component.

ROOT's broad result remains separately owned evidence; reviewer did not repeat it. B1 engineering PASS does **not** certify cross-page/antecedent implementation, full original quality, real summary C or all-PWF completion. Draft `test_cross_page_reference_plan.py` remains outside B1 and was neither changed nor required green.
