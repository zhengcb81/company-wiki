# Page-local source readiness — independent delta review

Verdict: **PASS_PAGE_LOCAL_READINESS_ENGINEERING** at the exact two files below. No confirmed runtime defect remains in this delta. This does not sign off product-antecedent resolution, whole-source semantic closure, real-provider summary C or the whole PWF.

## Exact scope

- Runtime `src/company_wiki/document_understanding/narrative_continuity.py`: SHA-256 `f63cdfea6330de09b32975cea17b6a9e437d772f36799ff3d2586076242b65fc`.
- Four author behaviors `tests/unit/du11_reference_readiness/test_native_page_local_positions.py`: SHA-256 `5275ae7110b109cddcb27bde8e644c39b6fb2710358b2c0b37a4251165f3b409`.

Both final byte hashes matched before/after independent runs. Reviewer made no runtime/author-test changes, no commits, no original PDF reads, no API/model calls and no full 77-test or real-source replay rerun. Mother CI/push tooling is outside this source review and was not modified.

## Root-cause repair and source ownership

1. `ordinal` describes the observed source-global sequence; `paragraph_index` is an original page-local locator. Cross-page `page_edge` now verifies global ordinal continuity rather than pretending paragraph 43 on page 16 must be followed by paragraph 44 on page 17. It still compares paragraph adjacency **inside** a single page/furniture suffix. Missing source-global positions or a broken same-page prefix produce `CONTINUITY_PAGE_ORDER_UNPROVEN` and defer the originals. Original locator fields and IDs are not renumbered or rewritten.
2. Positively identified furniture is still source-owned through the existing `SourcePageFlow.running_furniture_unit_ids`, with source/page/ordinal/local-paragraph checks. Stored furniture contains exactly four scalar original-reference fields (`unit_id`, `page`, `ordinal`, `paragraph_index`), not copied raw wire/paragraph bodies. Positive proof continues to list only those original IDs.
3. A bottom-of-next-page ordinary paragraph encountered before the real top body can conservatively retain the unfinished prior-page dependency. It is **not** classified as a proven footer and does not create a positive page edge. Once the actual top body is observed, an unproved prefix/order causes both original halves to be deferred through existing page-local ranges. A genuine fresh independent statement clears that pending association instead of being attributed to, or blocked by, the earlier product. Other scope/source/frame/font/role/column/coarse/fine-coverage vetoes remain in the previously reviewed owner.
4. Retaining a pending run charges its list-copy length through the existing scoped account; normal native checks and the source-statement scan continue to charge the same parent. A local refusal preserves the unused parent balance. No new budget/cache/task store, permission, positive counter heuristic, fake page view or source-text repair was added. Existing actual continuity-source hash binding invalidates the corresponding dependency identity.

## Finite execution and corrected reviewer control

Independent first run: **9 passed / 1 failed / 16.29s** (one disabled-plugin config warning). All four author cases and five independent controls passed. The failed **reviewer-created** budget assertion incorrectly required the parent `exhausted=True`; actual result was honest partial, no windows, parent used=9/12 and **not exhausted** because its child scope rejected the next scan before charging the parent. That is the already accepted B1 contract, not a new production defect. Runtime/author tests were not changed to satisfy it.

Only that one external control was corrected to require actual parent work equality, bounded consumption, `CONTINUITY_WORK_LIMIT`, an unexamined index and a preserved parent balance. It then **passed / 7.94s**, process exit 0; the nine passing behaviors were not repeated. Thus **10 distinct selected behaviors passed** across two runs, not one all-green ten-test process. Initial failure remains in `page-local-readiness-independent.{log,xml}`; single-case completion is in `page-local-readiness-budget-control.{json,log,xml}`. Original run command/hashes/cleanup: `page-local-readiness-independent-test.json`; corrected independent control source: `page-local-readiness-independent-controls.py`.

Independent additions cover:

- Fresh Traditional issuer and English negative-state product assertions after an unknown counter remain unblocked and their raw text is unchanged.
- Same-page paragraph reset remains a barrier; an unproved same-page furniture-prefix gap cannot certify a cross-page suffix.
- Unknown-counter flow remains partial under a deliberately small shared budget, preserving the parent balance and original-span/deferred semantics.
- Positive furniture handoff carries only four exact scalar fields and the actual two original IDs.

Both reviewer-owned outer temporary directories and the first run's actual relocated basetemp were removed and independently checked absent. Minimal allowlisted OS environment, explicit isolated `src`/`tests`, `-B`, no cache/bytecode and disabled external pytest plugins were used. No environment dump or credential read. The first warning is only `asyncio_mode` with its plugin disabled; no async behavior was tested.

## Correct real-source diagnostic boundary

Reviewer inspected ROOT's `page-scope-after-counter-fix/page-scope.json` and companion `cn-h1.json` read-only. The diagnostic binds this exact runtime SHA and explicitly says its wrappers are **not frozen acceptance or timing evidence**. It records 0 API, 0 raw copies, unchanged original. The companion record remains `ENGINEERING_PASS_CONTENT_OPEN`: selected/canonical required anchors 10/10, gold/original unchanged; old t32 has `selected_matches=0`, while old t34 still has one selected match (`t29-source`). These are ROOT-executed observations inspected by the reviewer, not another independent PDF execution or semantic acceptance.

The repair therefore addresses the real page-local numbering/unknown-counter readiness cause and prevents the specific t32 suffix from being released. The remaining t34 antecedent dependency and broader first-body/project-scope interpretation still require the following source/reference-owner work. Known-anchor counts or this engineering PASS must not be described as fully correct company analysis or completed formal summary C.
