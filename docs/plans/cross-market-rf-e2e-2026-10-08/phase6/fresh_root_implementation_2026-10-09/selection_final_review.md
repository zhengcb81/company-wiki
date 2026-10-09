# W02 independent final review — repaired first-pass implementation

Date: 2026-10-09. Reviewer: independent `fresh_selection_review` agent. HEAD: `2a978b67b37917db532b3e48988c4ffd283cf305` plus the coordinator's uncommitted W02 repairs. The initial `selection_independent_review.md` remains intact. This report does not change the frozen original 64 finding map.

**Verdict: the five original exact counterexamples are repaired; W02 still has three concrete residual mechanism defects.** The independent focused suite passed **18 tests in 0.28s**. Actual selector replays also passed bounded PDF/OCR nine-fragment closure, tight quota omission, completed PDF neighbor separation, English negative operating recall, and OCR bullet/heading/role/page/image/sentence boundaries. Chinese governance metric predicate ownership, revenue-cause sentence separation, and over-character-window statement closure still fail the independent contrasts below. Company M3 remains **NOT_RUN** by this reviewer.

## Basis and write boundary

Reviewed the assigned W02 source files and additions `narrative_finalize.py` and `narrative_ocr_groups.py`, plus the changed `narrative_neighbors.py` needed for the completed PDF prior/reference rule. Known-file reads were used; the original review already obtained CodeGraph structural context. No implementation, test, production config, protected raw material, old failure receipt, or prior plan was changed by this reviewer.

The coordinator reports the expanded RED **7 FAIL / 10 PASS** and concentrated ten-file GREEN **187 PASS / 2.38s**, with the prior explicit `其中 GaAs...` reference expectation preserved. Those are coordinator receipts, not independently rerun ten-file results. This reviewer independently ran `tests/unit/test_fresh_selection_semantics.py` with cache disabled and an exclusive temporary root: actual **18 PASS / 0.28s**, pytest exit 0. No old expected result was edited by this reviewer.

Source hashes at the start of this final review, and unchanged throughout the independent focused test execution:

| Source | SHA-256 |
|---|---|
| `narrative_matching.py` | `d9eaa7235f82b8d6e555504be041d9a396cdef72883f3d87fcf8f1cd0a79e693` |
| `narrative_evidence.py` | `9a1551eae54a5bc50534ad1ee10cb3689e254d3fa120b7edfe3aa8b9818bd829` |
| `n6_candidate_operating_facts.py` | `b07c7358067e427726aacc7a6962ae84a91d32f9de4288304a411a4dcc73ba4d` |
| `narrative_group_candidates.py` | `99b07cd75b1f283c96c5f282c101a0838cc5bf095084b319aaa1ab602dd28bf7` |
| `narrative_neighbors.py` | `44fca7fd68a1c1365dbbc6c9700883a979f85bbfe4789236f19048fffcd6d09c` |
| `narrative_finalize.py` | `a935e3f0df39228ef7c8f79f78915e1b476b4230c383a46af0ad32688e15a7b4` |
| `narrative_ocr_groups.py` | `5078f6348d96ffb186e0bb3df9ac25ef93c153adfece98162f05df7fa586a93e` |
| `test_fresh_selection_semantics.py` | `415b3275e1b0955b67906b74bbb088ffa9152acef17524b9e4c2b2b39384968a` |

## Original issue disposition from actual independent replays

Reused the exact fixtures and selector helper documented in the initial report. All paragraph indices are zero based. Every emitted span was checked against the original unit's raw text, `text_sha256`, and coordinates; all such identity checks were true.

| Initial issue | Actual repaired result | Disposition |
|---|---|---|
| SR01: bounded nine-fragment statement split into two budget groups | PDF and OCR both select indices 0–8 in one group at limit 96; candidate 9, omitted 0, status selected. At limits 8, 7, and 1 both emit no spans; candidate 9, omitted 9, status partial. | Exact 76-character fixture repaired. Longer-than-character-window continuation remains open below. |
| SR02: completed unrelated PDF prior borrowed into following contract event | Exact two-line fixture emits only index 1; candidate 1, omitted 0, selected. The prior product description is absent. | Exact case repaired. Static neighbor rule retains an exception for an explicit following reference. |
| SR03: English board training on ad pricing mistaken for changed operating metric | Exact English fixture emits no spans; candidate 0, omitted 0, needs_review. | Exact English case repaired. Chinese equivalent remains open below. |
| SR04: stable advertising impressions plus a later training sentence joined across `!` | Exact two-line fixture emits no spans; candidate 0, omitted 0, needs_review. | Exact commercial-metric case repaired. The separate revenue-cause detector still crosses `!` below. |
| SR05: specific English supply/negative operating disclosures omitted | Each original single-line supply, capacity, and orders/backlog fixture emits index 0; candidate 1, omitted 0, selected. | The three exact negative disclosure cases repaired. |

The bounded nine-fragment groups are now:

- PDF: `urn:company-wiki:context-group:sha256:0968c433676e55e44111a1971199f1a6775448f908b15a37bf7de598260fc37f:sentence:0:8`.
- OCR: `urn:company-wiki:context-group:sha256:111647f700ee35dc8ec6d9aba744f1c3e3742bf7b95a5740e4084129aa4f9dc2:sentence:0:8`.

The added finalization status rule honestly distinguishes quota omission of all complete groups from absence of narrative. The independent limit 8/7/1 outputs establish this behavior at the selector package boundary.

## OCR and original identity controls

Independent current-code OCR negative controls at limit 96:

| Exact input / change | Actual selected indices | Candidate / omitted / status | Boundary result |
|---|---|---|---|
| `['Agents and Infra', '• Revenue grew 30%, driven by the new platform', 'and higher customer adoption.']` | 1, 2 | 2 / 0 / selected | The owner before the new bullet was not borrowed. |
| `['Agents and Infra', '1、其他业务风险', 'Revenue grew 30%, driven by the new platform', 'and higher customer adoption.']` | 2, 3 | 2 / 0 / selected | The heading and earlier owner were not borrowed. |
| Original three-line English owner/predicate/tail; owner role changed to editorial | 1, 2 | 2 / 0 / selected | No role crossing. |
| Original three-line English owner/predicate/tail; owner moved to page 8 | 1, 2 | 2 / 0 / selected | No page crossing. |
| Original three-line English owner/predicate/tail; owner image SHA changed to `c * 64` | 1, 2 | 2 / 0 / selected | No image crossing. |
| Original three-line English owner/predicate/tail; owner changed to `Agents and Infra.` | 1, 2 | 2 / 0 / selected | No completed-sentence owner borrowing. |

Each result's retained predicate/tail spans had one group. The shared `ocr_sentence_continues` predicate is used by both OCR search grouping and bounded rejoining. It checks actual OCR identity/adjacency, prior sentence termination, headings, and the following bullet boundary. This is a sound shared boundary for the verified cases; the real slide's semantic ownership remains an M3 task.

Repeated the match-only restoration experiment with Traditional raw text `公司新產品已通過客戶驗證，並已進入海外市場量產。`, table headers `['產品', '客戶驗證']`, row cells `['已通過', '海外量產']`, and an unrelated metadata field. The matching copy changed its text/headers; the input object/raw remained unchanged; restoration returned the exact original object, metadata, and SHA. All six checks were true. The existing paired-script tests also passed independently. No transformed source representation leaked into the checked exported evidence.

## Remaining concrete defects

These are additional contrast cases for the same W02 mechanisms, not new company findings or a new small-node approval gate. All were executed with the same real selector helper; no network or model was used. They were sent to the coordinator before this report was written.

### FR01 — P2: Chinese governance sentence still changes the wrong subject

Exact single-line fixture, `language='zh'`, `limit=96`:

```python
["董事会关于广告价格的培训提升了员工的反舞弊意识。"]
```

Actual: `source_units=1`, `candidate_count=1`, `omitted=0`, `status=selected`, selected index `[0]`; group `urn:company-wiki:context-group:sha256:a8856fd2162c124e45e3139eaa963e059c5d93e6674d44471346bf8a2cb74e6f:operating-fact:0`. The selected reason is `quantified_operating_status` although the training improved awareness and the ad price did not change.

Root cause: `_ENGLISH_OPERATING_CHANGE` now constrains measure and predicate position, while `_COMMERCIAL_METRIC_CHANGE` still matches a Chinese measure phrase followed by any change verb within 45 characters. The governance/materiality defect therefore remains in the Chinese path introduced by W02. The remedy should preserve actual operating restrictions disclosed in ESG materials and distinguish the predicate's subject instead of globally banning governance words.

### FR02 — P2: revenue-cause detector still borrows causality across an ended sentence

Exact fixture, `language='en'`, `limit=96`:

```python
[
    "Revenue grew 30%!",
    "Our anti-fraud training was driven by higher customer adoption of the new policy.",
]
```

Actual: `source_units=2`, `candidate_count=2`, `omitted=0`, `status=selected`, selected indices `[0, 1]`; one group `urn:company-wiki:context-group:sha256:65d2792d00fdf1cd2ceb286cd037b5e0b41923a3eb594a07c6d3c68cd85b6b02:operating-fact:0`.

Root cause: `_REVENUE_CAUSE` still uses `[^.;]` for its bounded gaps, which permits `!`/`?`. Minimal joined windows are found before semantic closure; `_complete_fact_window` does not reject a minimum window that already crosses a completed sentence. The later sentence coalescer also preserves an existing wider atomic group when a group already spans both sentences. The commercial metric repair closed the original advertising fixture but did not establish the sentence boundary for all newly added fact detectors.

The governance training sentence supplies an unrelated cause to a finance-only growth sentence. A shared initial-window sentence boundary, with appropriate explicit-reference treatment where needed, should prevent this class across fact detectors.

### FR03 — P1: character-window overflow silently publishes an incomplete statement as selected

Start from the exact original nine-fragment fixture:

```python
nine = [
    "公司新产品", "已经完成客户验证，", "未来将进入量产阶段，", "本项目还需要",
    "补充设备安装，", "完成场地建设，", "办理生产许可，", "落实上游供应，",
    "以上安排尚未经董事会批准且可能取消。",
]
long = nine.copy()
long[4] = "补充设备安装细节，" + "有关项目具体实施安排及前置条件，" * 100
```

The full sentence has **1,678 original characters**. All nine units are parsed and source coverage is complete. No unit finishes the sentence before the final cancellation qualification. At `limit=96`:

| Format | Actual selected indices | Candidate count | Omitted count | Status | Actual groups |
|---|---|---:|---:|---|---|
| PDF | 0, 1, 2, 3 | 4 | 0 | selected | Two groups: `G` and `G:operating-fact:0` |
| OCR | 0, 1, 2, 3, 5, 6, 7, 8 | 8 | 0 | selected | Two separate groups |

PDF `G=urn:company-wiki:context-group:sha256:42a623675290ce5b2b7df0fcc7c0b19bd5bd438a6acd0dc650dcec1df368dc84`. The PDF result excludes the explicit unapproved/possible-cancellation condition at index 8. OCR groups are `urn:company-wiki:context-group:sha256:0daf1bbc3ced3a9c472fa9276cdc3b2c5fe2d5438d93a6220bb0b427fe279016` and `urn:company-wiki:context-group:sha256:f10c34c956f0118b8862497f525114c933bfbe2148b05a9a607a047a9b2b3a6e:operating-fact:0`.

Root cause: `_coalesce_sentences` simply skips a sentence whose characters exceed the existing character budget. Previously enriched incomplete candidates remain in the store. PDF general enrichment stops before the large middle unit; OCR cannot rejoin the search chunks across that large unit. Finalization sees all represented candidates selected and emits `selected`/`omitted=0`, although the complete subject/action/condition statement was not represented by one atomic group. This is a limitation of represented candidate inventory, not raw parsing failure.

The bounded character budget should remain enforced. Overflow needs an honest source selection outcome or an omission/quality reason for the incomplete statement; it should not export the unqualified prefix as a fully selected business statement. The revised finalization rule currently covers quota omissions, but not this earlier context-bound refusal. This does not require raising `max_selected`, extending the character cap, or running paid tests.

## Version and company acceptance boundary

Selector version remains `0.6.0`. The initial review established that batch input/execution versions, selection result identity, verify, and public replay consume that selector version; source SHA and parser identity are preserved. These corrections are still uncommitted pre-acceptance work. No real 0.6.0 publication/cache or no-charge repeat receipt was produced by this reviewer. W12 must verify the intended real reuse/invalidation behavior once the final selector semantics are frozen.

No original CN p41/p62, HK p6/p9, or US slide 7 was opened or accepted in this final engineering review. No public real-source summary or RF consumption was executed. The 187-test coordinator receipt and independent 18-test receipt establish local behavior only. Materiality coverage, actual conditional context, segment ownership, source replay, summary support, and company M3 are still pending.

## Actual execution and restoration receipts

Executed normal-OS Python `-X utf8 -B` in exclusive `TemporaryDirectory` roots. Socket connections were disabled. The focused pytest command used `-p no:cacheprovider`, an owned `--basetemp`, and `-o addopts=`. The existing pytest basetemp hook relocated its test directory inside the same owned root and emitted `removed=true` at cleanup. No install, commit, push, paid model call, download, or production write occurred.

Only TEMP/TMP and the tempfile cache were read for restoration. Production `config/source_catalog.yaml` was read solely for SHA/mtime comparisons; no content or credential was printed. Every final normal-OS command finished with exit 0. The counterexample runner intentionally printed failed expectation comparisons for FR01–FR03 instead of making its execution exit look like a code crash.

The focused test/restoration command emitted:

```json
{"focused_pytest_exit_code":0}
{"temp_restored":true,"cache_restored":true,"owned_work_deleted":true,"production_config_sha_mtime_unchanged":true,"reviewed_source_test_hashes_unchanged":true}
```

The independent selector and OCR domain runs each also confirmed TEMP restoration, tempfile cache restoration, owned directory deletion, and production config SHA/mtime unchanged. This final report is the reviewer's only new persistent repository write in this follow-up. The initial report and all earlier findings remain preserved.
