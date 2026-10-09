# W02 selection independent review

Review date: 2026-10-09. Reviewer: independent `fresh_selection_review` agent. Scope: W02 in `fresh_root_remediation_2026-10-09/IMPLEMENTATION.md`, on HEAD `2a978b67b37917db532b3e48988c4ffd283cf305` plus the coordinator's uncommitted W02 implementation. This report preserves the original frozen 64 finding mappings; the cases below are supporting engineering counterexamples, not additional company findings.

**Verdict: W02 requires correction before local major acceptance.** The transient matching representation preserves original evidence identity in the checked paths. Five concrete selection counterexamples remain in the reviewed implementation: incomplete atomic sentence closure, completed PDF sentence borrowing, governance metric false positives, cross-sentence English metric borrowing, and omitted English negative operating disclosures. No real company M3 acceptance is established here.

## Review scope and evidence

Read the assigned `narrative_matching.py`, `narrative_evidence.py`, `n6_candidate_operating_facts.py`, `narrative_group_candidates.py`, and `test_fresh_selection_semantics.py`, plus the existing completion, visual grouping, neighbor, finalize/budget, and version consumers needed to understand their boundaries. Used CodeGraph for structural context/node/caller questions, then known-file reads. No source, test, production configuration, protected original, old failure receipt, or existing plan was modified by this reviewer.

The coordinator supplied the preserved original RED `9 FAIL / 1 PASS` and concentrated `93 PASS` receipt. This reviewer did not overwrite or independently rerun that suite. The independently executed evidence consists of the synthetic selector counterexamples and restoration/boundary experiments below, using the actual installed code, no network and no model calls. A fixture PASS cannot establish CN/HK/US source recall, ownership, summary quality, or company M3 PASS.

Source snapshot taken after the counterexample runs at 2026-10-09 10:23:11 UTC, before the coordinator's subsequent source remediation:

| Reviewed source | SHA-256 |
|---|---|
| `narrative_matching.py` | `d9eaa7235f82b8d6e555504be041d9a396cdef72883f3d87fcf8f1cd0a79e693` |
| `narrative_evidence.py` | `f9e243620aca08a183061251d4943a0e3bfd47e3a9746e7811bc496c87509d4d` |
| `n6_candidate_operating_facts.py` | `4ebae23e7656fe52bb38914663fc63bcb80b74cfa4f73ab2fd29cf299b0cecf1` |
| `narrative_group_candidates.py` | `a66eb93a3b48fe62b08fc82cc9b36a65d11e48426a141fc1e5a37a09e1623271` |

The test file was concurrently owned by the coordinator, who began adding the new RED cases after receiving these findings. Its later hash is therefore not asserted to be the original test baseline.

## Actual counterexamples

All cases use the existing `select` helper from the assigned test file, with its generated source SHA, exact original units, page 41, consecutive paragraph indices, one PDF visual block, and company_filing role unless explicitly stated. Indices below are zero based. Every emitted span in the successful counterexample runs retained exact original raw text and the matching original `text_sha256`; the defects concern selection semantics, not source byte mutation.

### SR01 — P1: an over-eight-unit sentence becomes independently budgeted fragments

Exact fixture:

```python
lines = [
    "公司新产品",
    "已经完成客户验证，",
    "未来将进入量产阶段，",
    "本项目还需要",
    "补充设备安装，",
    "完成场地建设，",
    "办理生产许可，",
    "落实上游供应，",
    "以上安排尚未经董事会批准且可能取消。",
]
```

Actual outputs (`source_units=9`, `candidate_count=9` in every row):

| Limit | Selected indices | Omitted candidates | Status | Groups |
|---:|---|---:|---|---|
| 96 | 0–8 | 0 | selected | 0–7 in `G:operating-fact:0`; 8 in `G` |
| 8 | 8 | 8 | partial | `G` only |
| 7 | 8 | 8 | partial | `G` only |
| 1 | 8 | 8 | partial | `G` only |

Here `G=urn:company-wiki:context-group:sha256:0968c433676e55e44111a1971199f1a6775448f908b15a37bf7de598260fc37f`.

Root cause: `_complete_fact_window` relies on `completion_indices`, whose existing local API stops at `MAX_COMPLETION_UNITS=8`. It accepts that truncated range as a completed operating fact. `_special_ids` excludes the first eight assigned units, while `_add_general_members` supplies the remaining qualification under the enclosing group ID. The budget layer correctly budgets its input groups atomically, but those groups no longer represent the complete sentence. The high-priority isolated qualification is selected first under a tight budget; the statement's subject/action group then cannot fit. Raising `max_selected` does not repair this boundary.

Required acceptance: identify complete sentence closure within the bounded character context before final atomic membership. The whole subject/action/qualification statement must share one budget identity or be honestly refused as one bounded incomplete statement. Keep the existing local completion API's other responsibilities and page/role/image/heading/sentence barriers. Preserve omitted/partial or needs_review accounting when a complete statement cannot be retained.

### SR02 — P2: the PDF neighbor pass borrows a completed unrelated prior sentence

Exact two-line fixture (`language="zh"`, `limit=96`):

```python
[
    "公司新产品技术采用独立架构，不涉及本年度的业务进展。",
    "公司已签订海外客户的供货合同。",
]
```

Actual: `status=selected`, `source_units=2`, `candidate_count=2`, `omitted=0`, selected indices `[0, 1]`. Both spans have group `urn:company-wiki:context-group:sha256:708c48f73f8608a2e528e6b8c26fe3bf495e1b75a1aeef7ada64854e153cb5c4:sentence:1:1`. Index 0 has only `adjacent_subject_context`; index 1 has `business_narrative_signal`, `progress_or_change_language`, and `specific_business_event`.

Root cause: existing `narrative_neighbors._valid_previous` rejects a completed preceding sentence only for OCR. For PDF text it accepts the preceding `新产品` topic even though that sentence ended with `。` and cannot be the later contract sentence's subject. The new fact-window completion guard cannot prevent this later neighbor enrichment.

Required acceptance: apply completed-sentence separation at the actual PDF neighbor boundary as well as the fact-window builder. Retain a real unfinished subject continuation while refusing this completed prior sentence.

### SR03 — P2: an English governance training sentence is classified as an operating metric

Exact fixture (`language="en"`, `limit=96`):

```python
["The board training on ad pricing increased awareness of internal anti-fraud policies."]
```

Actual: `status=selected`, `source_units=1`, `candidate_count=1`, `omitted=0`, selected index `[0]`; group `urn:company-wiki:context-group:sha256:211ca0329907d3b09e1c3ddc2aca4961217d44312d45084b79ff0af08ebd5394:operating-fact:0`; reasons include `quantified_operating_status` and `progress_or_change_language`.

Root cause: `_COMMERCIAL_METRIC_CHANGE` accepts an operating noun followed within 45 characters by a change verb, without requiring that the noun is the measure changed. In this sentence board training increased awareness; ad pricing did not change. No number is present, yet the emitted reason says quantified operating status.

Required acceptance: distinguish the predicate's operating measure from governance/training vocabulary. Avoid a global ESG/governance ban: concrete commercial restrictions or effects disclosed in ESG material remain eligible.

### SR04 — P2: an English metric window crosses an already-ended sentence

Exact fixture (`language="en"`, `limit=96`):

```python
[
    "Advertising impressions were stable!",
    "Our fraud-awareness training increased completion rates.",
]
```

Actual: `status=selected`, `source_units=2`, `candidate_count=2`, `omitted=0`, selected indices `[0, 1]`, one group `urn:company-wiki:context-group:sha256:fc9580676b19da684e768372027ca536ea6343ccfe362ae98bc8d72aef2629ac:operating-fact:0`. Both receive `quantified_operating_status`.

Root cause: the new commercial metric pattern excludes `。；.;` between its measure and action but permits `!` and `?`. `_minimal_matching_unit_windows` finds a joined cross-sentence match first. `_complete_fact_window` bounds its later expansion but does not reject a minimum input window that already crosses a sentence barrier. Both individually non-material units are consequently promoted together.

Required acceptance: sentence barriers must constrain the original matching window, not only its expansion. Include English `!`, `?`, and completed independent sentences in contrast fixtures.

### SR05 — P2: specific English supply/operating deterioration remains outside the candidate inventory

Independent single-line fixtures (`language="en"`, `limit=96`):

```python
"Supply constraints delayed deliveries to customers by six weeks."
"Production capacity decreased 20% following an unexpected factory closure."
"Customer orders declined 20% and our backlog fell by five million units."
```

Actual for each: `status=needs_review`, `source_units=1`, `candidate_count=0`, `omitted=0`, no selected spans. This status is honest about the empty source, but the omitted-candidate counter cannot show these lost material passages because they never became candidates. In a mixed document with other selected material they would likewise be absent from candidate-based recall accounting.

Positive contrast: `"During the quarter, active users declined 20%."` produces `status=selected`, one candidate and one selected span with `quantified_operating_status`.

Root cause: the new metric detector covers only selected commercial measure names; `_SUPPLY_DELIVERY_RISK` and the existing `_BUSINESS_RISK_SIGNAL` cover Chinese phrases; the existing English operating events predominantly require growth/expansion actions. English delivery constraints, capacity deterioration, and declining orders/backlog therefore lack a materiality signal despite explicit quantified business consequences.

Required acceptance: add generic English business restriction and negative operating status detection with governance and finance-only contrasts. Keep source wording and uncertainty; this selector does not assert that a forecast or risk condition occurred.

## Passed boundaries and remaining limits

1. **Match-only text/metadata restoration:** constructed a Traditional Chinese table unit with raw text `公司新產品已通過客戶驗證，並已進入海外市場量產。`, headers `['產品', '客戶驗證']`, row cells `['已通過', '海外量產']`, and an unrelated metadata field. The matching copy changed its raw text and selected headers. The input object remained unchanged, and `original_candidates` restored the exact original object, original metadata, and original text hash. All six explicit checks were true. The production selector similarly restored original raw text/hashes in every emitted counterexample span. No inspected route persisted the transformed representation or rewrote raw source bytes.
2. **OCR ownership and physical boundaries:** plain `['Agents and Infra', 'Revenue grew 30%, driven by the new platform', 'and higher customer adoption.']` selected three original spans in one group. Independently setting the owner to excluded role `editorial`, moving it to page 8, changing its image SHA to `'c' * 64`, or adding an ending period selected only indices `[1, 2]`; no test borrowed index 0 across the changed boundary. Each result had `candidate_count=2`, `omitted=0`, `status=selected`. The role/page/image protections in OCR identity and adjacency work for these checks. These synthetic protections do not establish the real US slide's owner or support completeness.
3. **Version 0.6.0 boundary:** `NarrativeBatchRequest.execution_versions` and `input_hash` include the current selector version; the select result records it; verify rejects a non-active selector version; public narrative replay rejects a contract with a selector version other than the active version. This makes old 0.5.0 selection incompatible with the current selection/verification/replay contracts. The parser name/version and source identity remain unchanged in the inspected W02 diff. This is source inspection of the invalidation boundary, not a completed real no-charge/recompute receipt; W12 and company M3 remain required. Any later semantic revision after 0.6.0 publication must obey the same version boundary.
4. **Counters:** successful reproduction showed truthful candidate-minus-selected counts for the nine-fragment budget omission, but those counts measure represented candidates rather than all material source passages. Do not use `omitted=0` or `12/12 selected` as proof of full recall.

## Execution and TEMP hygiene

Executed Python with `-X utf8 -B`, imported the known selector/test helper, disabled socket connection calls, and used an exclusive `TemporaryDirectory`. Only TEMP/TMP and `tempfile.tempdir` were read for restoration; no full environment, credentials, key files, endpoints, source contents, or paid APIs were inspected. The production `source_catalog.yaml` was read only to compare its SHA and mtime, without printing its contents.

The first default-sandbox counterexample command printed the actual findings, then its TemporaryDirectory cleanup raised `PermissionError [WinError 5]`. Its `finally` restoration had already run. This was an execution/cleanup limitation, not a selector failure. A later normal-OS check found that exact sandbox directory absent; a subsequent default-sandbox read also reported `FirstSandboxReviewDirectoryExists=False`. No other directory was enumerated or deleted. The later approved normal-OS counterexample run finished with exit 0 and explicit receipts:

```json
{"temp_restored":true,"tempfile_cache_restored":true,"owned_work_deleted":true,"production_config_identity_unchanged":true}
```

A first metadata/OCR harness printed all six successful metadata restoration checks, then failed because the review harness tried to access non-existent `EvidenceSpan.source_role`. That harness mistake was corrected in the independently rerun output loop; no project code or test was changed to obtain the result. The corrected normal-OS OCR run finished with exit 0 and explicit receipts:

```json
{"temp_restored":true,"cache_restored":true,"owned_work_deleted":true,"production_config_sha_mtime_unchanged":true}
```

No commit, push, installation, network, model, download, or original-source write was performed. This report is the reviewer's sole persistent repository write. All five failures were sent to the coordinator before remediation; review closure requires fresh RED→GREEN evidence and an independent review of the repaired mechanism. Actual original CN p41/p62, HK p6/p9, and US slide 7 opens, selected locator replay, public bundle, and downstream use were not executed here and remain M3 work.

## Minimal replay recipe

Run on the reviewed pre-remediation source snapshot with normal OS permissions and an exclusive TEMP root. The existing helper supplies exact source bytes/hashes and coordinates without production materials:

```python
import os
import runpy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
select = runpy.run_path("tests/unit/test_fresh_selection_semantics.py")["select"]
before = {key: os.environ.get(key) for key in ("TEMP", "TMP")}
cache_before = tempfile.tempdir
with tempfile.TemporaryDirectory(prefix="w02-selection-review-") as work:
    try:
        os.environ["TEMP"] = os.environ["TMP"] = work
        tempfile.tempdir = work
        # Use each exact fixture above with language="zh" or "en" as stated.
        # For SR01 repeat limits 96, 8, 7, 1.
        package, originals = select(lines, language=language, limit=limit)
        print(package.status, package.candidate_count,
              package.omitted_candidate_count)
        for span in package.evidence_spans:
            i = span.coordinates.paragraph_index
            print(i, span.raw_text,
                  span.structured_value.get("selection_group_id"),
                  span.structured_value.get("selection_reasons"),
                  span.structured_value["text_sha256"] == originals[i].text_sha256)
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        tempfile.tempdir = cache_before
assert before == {key: os.environ.get(key) for key in ("TEMP", "TMP")}
assert tempfile.tempdir == cache_before
assert not Path(work).exists()
```
