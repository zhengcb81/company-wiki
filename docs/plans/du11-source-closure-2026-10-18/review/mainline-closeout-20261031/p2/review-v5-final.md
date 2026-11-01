# P2 final independent review — v5

Review date: 2026-10-31. This continues the same P2 review node and supersedes the engineering OPEN in `review-v3.md` for the final v5 case and the exact RF code hashes below. It does not replace or erase the earlier failures.

## Layered decision

| Layer | Final verdict | Scope |
|---|---|---|
| Raw sources, annual/API amounts, CNY units and annual periods | PASS | Original v3 source checks remain valid; v5 uses the identical annual/API/IR bytes. |
| Actual parameter/formula adoption | PASS | `t3-source` binds to the used `Footwear/base/FY2026 units` parameter; the native formula multiplies it by footwear-only realized revenue per sold pair. |
| Full summary/use-reason/citation persistence | PASS | Exact selected summary, artifact/source identities, original support/context spans, quality limits, explicit reason and native dependencies are frozen in input, forecast and snapshot, and rendered in the formal report. |
| Formal output/snapshot/local registry mechanics | PASS | Independent canonical hashes, snapshot identity and all three registry links match. Mode is formal and attestation remains `unattested`. |
| Reviewed implementation/regression scope | PASS | The review-discovered standalone, present-null, missing-backlink and projected-parent/pointer regressions have specific fixes and meaningful failing-then-passing tests. |
| Package membership | PASS, static and recorded-test scope | New module is inside the recursively shipped `scripts/` closure; no tests/tools/network/model dependency was introduced into forecast calculation. |
| P2 bounded engineering adoption acceptance | **PASS — no remaining blocking finding in the reviewed scope** | One-year real-source integration case only. |
| Current company research/economic adequacy | **OPEN** | Five communication categories and six research dimensions remain unresolved; scenario levels are explicit conditional assumptions. |

No P1 overall, P3 company loop, full-company RF-audit, buy-side forecast quality, remote CI, mainline merge or global installation completion is signed by this review. ROOT owns the subsequent integration/deployment gates. This review did not run the author harness, forecast runtime, tests, network, model, downloads or PDF parsing. It wrote only this review directory.

## Earlier findings closed by the actual v5 artifacts

**P2-01 (previous high/P1) — CLOSED.** The native claim still keeps its short first-span excerpt as a locator anchor, but now explicitly identifies `excerpt_scope=source_anchor_only` and embeds a bounded `revenue-summary-provenance/1` record. The record contains the exact artifact ref, public-reader receipt, original SourceRef, complete `t3-source` claim and hash, five original support spans (IR p1/28–32), the separate question context span (p1/27), source-owned reading group, explicit research reason and actual parameter/formula targets.

The complete object is identical in the formal input, result's embedded input/evidence set, and snapshot's embedded input/result. The formal input hash therefore binds the use explanation and entire selected original closure. It is no longer dependent on a detached consumption receipt. The independent probe compares every persisted span with the exact existing CWP bundle, not merely with another caller-authored copy. All match.

The report at `C:/Users/郑曾波/Projects/revenue-forecast/.planning/m8-native-adoption-20261031/v5/report.md:203` prints the artifact/source SHA, selected claim ID, full uncertain answer, original support/context table and use explanation. It preserves high inventory and conservative forecasts, differentiated brand orders, and the expectation of partially filling some gaps. It does not turn that history into proven 2026 orders or complete offset.

**P2-02 (previous medium/P2) — CLOSED.** Native rationale claims now carry the actual FY2025 sold-pair/growth evidence (p15/20 and p17/21), nominal capacity evidence (p19/17–20) and footwear-price numerator/denominator evidence (p16/13–14,20 and p17/21). The future parameters remain `analyst_assumption`, with locator text explicitly saying the historical capacity is not a 2026 actual. These are source-linked historical anchors for a conditional calculation, not exact-value claims about future results.

**P2-03 (previous low/P2) — CLOSED.** The report now displays nonzero `0.00010996115` and the unit `CNY million per pair` in its parameter mapping (line 196), rather than rounding the actual coefficient to `0.00`. The coefficient is approximately `109.961148 CNY/pair`. Ordinary money tables retain their normal two-decimal display.

## Implementation and test review

The adapter constructs the per-claim record only from the already verified public-reader context. Formal validation performs no extra source read. `contracts/document.py` delegates to the new provenance module; it reuses the existing wire span/summary owner, citation resolver, a shared summary-scope validator, and native dependency owner. It does not duplicate revenue calculation or create another source permission/approval chain.

The following defects were independently identified while reviewing the initial repair and then corrected before this sign-off:

| Review finding | Final change and evidence |
|---|---|
| Legal standalone/ungrouped citations have `None` group-role lists; an unconditional `set(None)` prevented formal publication. | Common `validate_summary_scope` preserves the existing single-span/no-context rule for standalone use and full partitions for closed views. Positive formal/report/snapshot tests now cover raw, projected, assessed and standalone contexts. Recorded standalone RED includes the exact TypeError; it is not counted as success. |
| A present `narrative_summary_use: null` silently passed validation but failed report rendering. | Absent remains optional; present-null now fails the explicit provenance schema check. A regression test proves the rejection. |
| An orphan proof could still claim adoption after its claim ID was removed from the parameter's evidence references. | The validator now requires the native parameter's claim backlink as well as its real formula dependency. A negative test removes that backlink while leaving other valid annual evidence. |
| Projected spans initially received only canonical raw-span validation and could retain locally contradictory parent/projection/pointer/range bindings after rehashing. | The public pure helper now reuses `_projected_span` for projected data. A compact subject ref supplies only the selected item key; a local validation subject uses the current single SourceRef. This does not claim knowledge of a missing full parent set. Four negative tests rehash spans and rename all local references before testing wrong parent SHA, projection ID, pointer and byte range. |

The tests are substantive: the projected negative cases no longer fail merely on stale span hashes, and the reason-change test checks an existing publication anchor after altering the reason. Synthetic unit tests mock the reader and make no source-authenticity claim; the real v5 case independently supplies the source-to-native integration evidence.

Recorded tests read by this reviewer:

- Initial implementation RED: 8 failures, including missing native persistence and zeroed small numbers.
- Standalone/assessed formal regression RED: 2 failures; present-null/backlink RED: 2 failures.
- A focused regression/package checkpoint passed 171 tests in 39.96 seconds before the final projected-specific change. The earlier package failure was missing `agents/` in the sparse work area, not a successful installation check.
- Correct projected RED: `rf-lineage-projection-red-v3.log` records four `DID NOT RAISE ValueError` failures. Earlier broken-prefix/escaping attempts do not establish these failures.
- An intermediate compact-subject mistake produced 5 real failures in a 175-test run. It remains preserved in `rf-lineage-release.log` and is not represented as green.
- Final affected/new test suite: `rf-lineage-projection-final.log`, **29 passed in 2.86 seconds**, including the projected formal positive and all four correctly constructed negatives.

The final affected suite closes the final projected change. This report does not call the earlier 171-test checkpoint a rerun of the frozen final code or claim a whole-repository/remote CI pass. ROOT can apply its normal precise integration gates without repeating source/model work.

## Independent v5 probes and numerical result

`probe_v5.py` uses only Python's standard library and executes none of the author runtime. Its **32 checks all pass**. Full observations, exact code/file hashes and independent decimal calculations are in `probe-v5.json`.

| Case | Conditional pairs | Independently recomputed company revenue, CNY million | Stored result | Difference |
|---|---:|---:|---:|---:|
| Low | 204,291,000 | 22,484.117045897 | 22,484.117045896997 | -3e-12 |
| Base | 230,599,141 | 25,376.990436338687 | 25,376.990436338685 | -2e-12 |
| High | 247,570,000 | 27,243.12557732176968 | 27,243.125577321767 | <3e-12 absolute |

The arithmetic is Footwear actual FY2025 revenue divided by actual sold pairs, multiplied by conditional FY2026 pairs, plus the separately flat Other revenue. The coefficient is positive, so the adopted pair parameter is a real numerical dependency. ROOT's separate 1% scenario perturbation was not duplicated by this reviewer.

Final identities independently recomputed:

- CWP artifact body: `ec1831a2fdf2952a9a80aba0c9e5db65c8bc581ea5c0a10d53d01ef2faba52d8`.
- Selected t3 claim: `29df07901b23643bfd748cd0daef1c3b082c8797699eedbfddb8a644b3faefd6`.
- Canonical RF input: `c73dcad35d16053e3b94f8cd8ef08ee9e2a26cf5f9ccd3ee0aff4389db2d53ec`.
- Published result: `d9b2ba1e5a083c30b7ef1f3c81df5a04996cb376326bf10e5917730bbce108b5`.
- Snapshot ID: `85893de7654ab410bccc46e1506816ffd7266c6b8dfe4f5519030a0179f51c2c`.

The result and snapshot are structurally formal and `unattested`. Registry rows independently match the two identical formal computations and the snapshot anchor, including every chained line hash. The v5 temporary root is removed. The adoption receipt records zero new POSTs/downloads and real locator replay; it does not call replay “zero parsing.” Preparation's earlier API/annual downloads remain separate, recorded source acquisition work.

## Trust boundary and economic OPEN

The persisted partial DTO proves local consistency and binds the analyst's use to a frozen formal input. A digest of a full CWP artifact cannot be independently recomputed from a small selected subset; this DTO is not a Merkle proof or a trusted host signature. External authenticity still depends on the actually executed source-owner read/download records and their byte checks. The module documentation and v5 `TRUST_BOUNDARY.md` state that limit. This review also compares the subset against the existing exact artifact, but does not promote the formal publication to host-signed authority.

The old IR source's publication date and fiscal year/period remain unknown. The original frozen header identifies meetings on May 11, 12, 17 and 18, 2023; the filename's May 19 is not substituted for a meeting date. Current verified open proves 2026-10-31 availability, not a 2023 publication date or a new 2026 development. `needs_review`, uncertain modality, partial selection and semantic `not_evaluated` are retained. Source-quality acceptance is never an investment conclusion.

Low = 90% of 2025 sold pairs; Base = repeating the disclosed rounded 1.59% growth; High = assumed sell-through at 2025 nominal annual capacity with flat inventory; and all three use flat 2025 realized footwear price. These remain explicit analyst assumptions. No calibrated probabilities, management 2026 guidance, guarantee of complete new-client offset, or verified current capacity/demand are claimed.

The formal report still records five of six management-communication categories as incomplete and six of nine research dimensions as gaps. Latest 2026 results/calls/presentations/announcements, independent demand/competition/reference-class calibration, and a complete company economic review remain OPEN. Runtime hard-gate PASS and the approximate 60/100 evidence/workflow score do not close these gaps or establish forecast probability. CWP holds source/test/review records; formal forecast/report/snapshot/registry remain in RF's owned directory.

## Exact reviewed RF code

Code root: `C:/Users/郑曾波/Projects/_r2`, branch supplied by ROOT `codex/p2-summary-lineage-20261031`. File comparison to the RF baseline and exact file reads were used; the local Git worktree metadata did not permit `git diff` in this reviewer process. No repository/config recovery was attempted.

| File | SHA-256 |
|---|---|
| `scripts/narrative_summary_provenance.py` | `14e7d4e90b61bdbde313fab0f2b8249287e6c6d08c198f6ab98fc5ee9719126c` |
| `scripts/narrative_summary_usage.py` | `3c2d6838e3985f2a43e17e20aba85ddbd72fc144cc652e7db54e71ea64a587b4` |
| `scripts/source_narrative_context.py` | `c71b53bf25ea67a1c1b5b83d5ecad6a63fe653786298f5b5ed3625e35a66a5fe` |
| `scripts/company_wiki_narrative_contracts.py` | `14c3d5d6d3c88c4f8862b6cc464480555655cfa36492dad732151eb05fa7d02f` |
| `scripts/contracts/document.py` | `b7fda4e863b12da50509e48f3801695741d39e6e0f9468a907b7aa30532423ef` |
| `scripts/revenue_report.py` | `3f5c1324e2be453ffcb8c58945304fc4e5ca831a71266d5c6b80620874915b23` |
| `tests/test_summary_publication_lineage.py` | `697ac76da7965c705851ef75f39c47fba04338712e578ef2f81cd9f6d34daeea` |

The actual v5 harness SHA is `be7eabe12451b8705b9ef796f753ba1b6c012c9f58a9183968eaf7f326018677`. Any materially changed file/artifact needs an appropriate delta review rather than reusing this signature blindly.
