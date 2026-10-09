# W02 residual acceptance — local M2

Date: 2026-10-09. Reviewer: independent `fresh_selection_review` agent. Reviewed HEAD: `2a978b67b37917db532b3e48988c4ffd283cf305` plus the coordinator's uncommitted W02 residual repairs. Prior `selection_independent_review.md` and `selection_final_review.md` remain preserved.

**Verdict: ACCEPT W02 local M2 for the reviewed implementation.** FR01–FR03 passed independent exact replay and exclusion/identity checks. The four corresponding focused tests independently passed **4 PASS / 18 deselected / 0.26s**, exit 0. No direct implementation safety defect was found in this limited residual review. Actual company M3 remains **PENDING / NOT_RUN** by this reviewer; this acceptance makes no real-source recall, summary, ownership, downstream research, or company quality claim.

## Scope and retained receipts

This is the same M2 closure node, limited to the three residual findings and original-text/exclusion-count integrity. No new semantic generalization, paid call, network request, or acceptance gate was added. The frozen original 64 finding map was not changed.

The coordinator reports retained residual RED **4 FAIL / 18 PASS** in `selection_final_review_red.txt` and ten responsibility suites GREEN **191 PASS / 2.00s**, with prior assertions unchanged. These are coordinator receipts. The independent result below is the exact four-test residual subset plus actual selector calls and observations at the finalization boundary; it is not a claimed independent rerun of all 191 tests.

Known-file inspection covered the updated Chinese metric predicate, revenue-cause terminators, complete-sentence exclusion DTO/store, OCR character counting, forwarding of exclusions into finalization, and final whole-group refusal/accounting. No source, test, production configuration, protected original, prior failure receipt, or existing report was modified by this reviewer.

## Actual residual results

Each actual selector call uses the retained test helper with `max_selected=96`. Original source SHA and unit identity are synthesized deterministically by that helper. Paragraph indices are zero based.

| Residual | Exact case | Selected indices | Source units | Candidate count before/after finalization | Omitted | Status |
|---|---|---|---:|---|---:|---|
| FR01 | `董事会关于广告价格的培训提升了员工的反舞弊意识。` | none | 1 | 0 / 0 | 0 | needs_review |
| FR02 | `Revenue grew 30%!` followed by `Our anti-fraud training was driven by higher customer adoption of the new policy.` | none | 2 | 0 / 0 | 0 | needs_review |
| FR03 PDF | Retained 1,678-character nine-fragment statement, including final unapproved/possible-cancellation condition | none | 9 | 4 / 4 | 4 | partial |
| FR03 OCR | The same retained 1,678-character statement using OCR units | none | 9 | 8 / 8 | 8 | partial |

The exact FR03 fixture remains:

```python
lines = [
    "公司新产品", "已经完成客户验证，", "未来将进入量产阶段，", "本项目还需要",
    "补充设备安装细节，" + "有关项目具体实施安排及前置条件，" * 100,
    "完成场地建设，", "办理生产许可，", "落实上游供应，",
    "以上安排尚未经董事会批准且可能取消。",
]
```

Both FR03 paths passed all nine statement unit IDs to finalization as `excluded_context_unit_ids`; their paragraph indices were exactly `[0,1,2,3,4,5,6,7,8]`. No unqualified prefix or isolated condition was emitted. `candidate_count` retained the original represented candidate inventory, rather than being reset after filtering. The independently observed arithmetic was exactly `omitted_candidate_count == candidate_count - len(evidence_spans)` in all four calls.

Counts 4 and 8 refer to represented candidates, while all nine parsed units belong to the excluded statement. These truthful counts are not asserted to measure all material source passages. The `partial` status correctly prevents this refusal from being represented as absence of narrative or a fully selected statement.

## Identity and direct implementation safety

For the exact selector replays, a temporary in-memory wrapper observed the arguments passed to the original `finalize_selection` and then delegated to it unchanged. The wrapper was restored in `finally`; no project implementation or test file was edited.

For every actual candidate in the FR03 PDF and OCR calls, the candidate unit was the **exact original parsed unit object** by identity. Its source ID matched the original structure; recomputed UTF-8 text SHA matched its original `text_sha256`. Exact original object restoration also preserves the original metadata and coordinates. Both paths therefore excluded original IDs without persisting transformed match text or altering the parsed source units. FR01/FR02 had no candidates, so their empty identity checks are not used as positive evidence of restoration; the nonempty FR03 checks establish it.

Direct inspection found:

- The Chinese metric detector now requires a clause-position measure and a local performance predicate. The retained training sentence no longer qualifies.
- `_REVENUE_CAUSE` excludes the full declared English/Chinese terminal punctuation set in each bounded gap. The retained cross-`!` cause fixture no longer qualifies.
- `GroupEnrichmentResult` returns immutable exclusion IDs, and each candidate store uses its own `set` via `default_factory`; no shared mutable exclusion default was introduced.
- OCR overflow detection sums original unit lengths and records IDs/references without constructing an unbounded joined string for the full sentence. It reuses the shared physical/sentence/heading/bullet continuation predicate.
- Finalization filters the excluded IDs and their already-assigned atomic groups before dedup/budget, while deriving `candidate_count` and omission from the original incoming candidate list. The selector forwards the exclusion set after restoring candidates to the original units.
- The existing character caps, parser/source identity, and original evidence coordinates are preserved. No cap or production parameter was raised to make the test pass.

The reviewed selector remains version `0.6.0`. This is acceptance of the final local implementation under that uncommitted version boundary; the previously documented actual public generation/replay and W12 cache receipts remain later integration work.

## Independent execution and hygiene

Executed normal-OS Python `-X utf8 -B` with a dedicated `TemporaryDirectory`. Socket connections were blocked, pytest cache was disabled, and basetemp was confined to the owned temporary root. The repository's existing basetemp hook relocated its directory within the same owned root and recorded `removed=true`.

The focused invocation selected only the retained residual tests:

```text
tests/unit/test_fresh_selection_semantics.py
-k "operating_subject_and_cause_cannot_be_borrowed or statement_over_the_character_cap"
-p no:cacheprovider
--basetemp <owned TemporaryDirectory>/pytest
-o addopts=
```

Actual output: `4 passed, 18 deselected in 0.26s`. The command completed with exit 0. TEMP/TMP and tempfile cache restoration, owned directory cleanup, production config SHA/mtime preservation, and source/test hash preservation all passed:

```json
{"focused_residual_pytest_exit_code":0}
{"temp_restored":true,"cache_restored":true,"owned_work_deleted":true,"production_config_sha_mtime_unchanged":true,"source_test_hashes_unchanged":true}
```

Only TEMP/TMP were read for environment restoration; no complete environment or credential material was inspected. `config/source_catalog.yaml` was read only to compare SHA/mtime, with no content printed. No download, model use, charge, installation, commit, push, raw-source write, or production write occurred. This acceptance report is the reviewer's only new persistent repository write in this follow-up.

Reviewed source/test SHA-256 values, captured before execution and unchanged after it:

| Source | SHA-256 |
|---|---|
| `narrative_matching.py` | `d9eaa7235f82b8d6e555504be041d9a396cdef72883f3d87fcf8f1cd0a79e693` |
| `narrative_evidence.py` | `c2aa937dfafc690ef12704bc9413afc1c7aaa5f31054200aeaeae3f1035b5a4a` |
| `n6_candidate_operating_facts.py` | `f05f884167b1789a028b0628f1104f3d699059f658a60f6572fc8efa49950a9a` |
| `narrative_group_candidates.py` | `cface6b409883958142aa1e3906c5d7abdcb1ea6e4a164a85491725a8ec5b04b` |
| `narrative_finalize.py` | `c6840d8772681f88ba99207686dedad85a4d58615a36eb4b136a5bc1213b0916` |
| `narrative_ocr_groups.py` | `5078f6348d96ffb186e0bb3df9ac25ef93c153adfece98162f05df7fa586a93e` |
| `test_fresh_selection_semantics.py` | `8422a6f0954f9ad4e7cc0f519e0c45aeb910e38a1f6a9e8c36883fbc99ea3df7` |

## Acceptance boundary

FR01, FR02, and FR03 are closed for this local engineering review. Together with the preserved preceding independent review of the original five fixtures and OCR/identity controls, this supports **W02 local M2 ACCEPT**. There is no unresolved direct residual defect in the authorized scope of this closure review.

Real CN/HK/US source semantics, materiality recall, conditional context, OCR owner assignment, locator replay, public summary support, W12 repeat/invalidation behavior, and downstream company quality must still be assessed at M3. This local acceptance does not mark those tasks complete.
