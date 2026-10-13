# DU-BENCH — document-understanding quality benchmark

An **independent** gold set, counterexample suite and read-only native replay
for the document-understanding upgrade. It measures two things the current
pipeline cannot measure about itself:

1. **Real omissions** — business facts that are present in the original and do
   not survive into the selected evidence or the summary.
2. **Fabrications** — claims the observation asserts that its own evidence does
   not support.

The benchmark never derives expectations from the selector's output, never
imports `company_wiki` into the oracle, and never edits production code to make
a result pass.

## Reception repair, 2026-10-13

The previous recall implementation incorrectly accepted flattened selected text
or generated claims as original evidence. Old recall rates and the statement
that general HTML had no frontend are **superseded diagnostic observations**,
not valid current quality measurements. Original sources, quotes, importance,
the second HK sample and CID legibility checks are retained.

Current recall uses only actual selected locator -> original-text rows, with
source page/line constraints and AND within a support group / OR between groups.
One opaque alternative cannot invalidate another readable complete group.
Missing legacy source mappings report `NOT_EVALUATED`; claims cannot supply them.

Gold target classes are `required_business`, `disposition_context` and
`correctness_if_emitted`. Pure financial quarters can legitimately produce zero
selected evidence, zero summary and zero model calls. Every financial claim that
is emitted remains subject to direction/unit/period and contradiction checks.
Normal business misses remain visible as `PARTIAL`; critical business misses fail.

Declared `complete` is not context proof. Actual required original locators and
resolved dependencies must be observed. An unaudited generated summary makes
whole quality `PARTIAL`; an empty/incomplete/duplicate semantic review cannot
certify all claims. Mutation detection compares individual checks against the
baseline, so a pre-existing `PARTIAL` never counts as automatic detection.

Read the additive [evidence contract](EVIDENCE_CONTRACT.md). The independent gold
responsibility changes and reasons are in
`.planning/du-benchmark-reception/gold-classification.json`; no support quote or
importance was removed. Historical holdout split labels are preserved for paired
regression, but samples already inspected by the project are **not a fresh blind
validation set**.

Real Microsoft FY2025 10-K HTML: existing normalization read 5,215 units;
96 selected spans all mapped to original units, no new parser. The current
baseline still misses four of eight required critical business facts (4/8 recall,
`FAIL`). This is a measured remaining production quality gap, not a broken
benchmark. Native baseline emits no summary, so model fidelity is untested.

## Entry points

```python
from tools.document_understanding_benchmark import evaluate

result = evaluate(observed, gold)              # -> du-evaluation/1
result = evaluate(observed, gold, limits={...}, review={...})
```

CLI (this is the public command; it is **not** wired into pre-commit, pre-push
or daily CI):

```bash
# offline: synthetic fixtures only, no original, no network, no model call
python -X utf8 -m tools.document_understanding_benchmark \
    --mode offline --output <owned-dir>

# native: read-only observation of real originals resolved by local bindings
python -X utf8 -m tools.document_understanding_benchmark \
    --mode native \
    --bindings <local bindings.json> \
    --output <owned-dir> \
    --probe-config config/source_catalog.yaml

# with an independent semantic review applied
python -X utf8 -m tools.document_understanding_benchmark \
    --mode native --bindings <local bindings.json> --output <owned-dir> \
    --review tools/document_understanding_benchmark/reviews/fixtures-independent-review.json
```

Exit codes: `0` all evaluated samples PASS, `1` any FAIL, `2` refused to run
(bad gold/bindings/adapter/review), `3` PARTIAL or UNAVAILABLE present.

`--bindings` is a **local, uncommitted** `{sample_id: absolute_path}` JSON file.
Keep it outside the worktree (for example `~/.du-bench/bindings.local.json`) so
the repository stays clean. Originals are never copied, and a missing binding or
SHA-256 mismatch yields `UNAVAILABLE` — never a substituted or synthetic document.

## Historical baseline before reception repair (not current quality acceptance)

Reported separately and never merged: the development samples were used to tune
rules, so only the holdout split speaks to generalisation. Facts that could not
be read (`UNAVAILABLE`) **leave the denominator** and are reported as `coverage`
instead, so "could not read" is never reported as "found none".

| split | documents | critical recall | evaluable/declared | coverage | narrative (all facts) | document_meta |
|---|---:|---|---:|---:|---|---:|
| development | 11 | **11/60 = 0.183** | 60/86 | 0.698 | 13/68 = 0.191 | 1/19 = 0.053 |
| holdout | 6 | **0/31 = 0.000** | 31/54 | 0.574 | 1/79 = 0.013 | 0/1 |

`narrative` counts all facts (critical and normal) about business content;
`document_meta` counts facts about the document as an artifact (audit status,
fiscal-vs-calendar year, TOC-vs-body, page counts, provenance, text legibility).
They are split because the evidence selector owns the first and a front-end layer
owns the second; mixing them would blame the selector for facts it was never
scoped for.

Findings from that measurement:

- **Candidate generation is the bottleneck, not the selection cap.** `cn-ir` had
  11 candidates, selected all 11, and still missed 9 of 10 gold facts.
  `cn-q-sparse` produced **zero candidates from 429 units** and
  `holdout-cn-glodon-q1` **zero from 257**; `holdout-cn-yake-q1` produced 2 from
  369. Raising the cap cannot help any of them.
- **A fully garbled document parses clean.** A real 415-page HK annual report has
  **0 pages of readable Chinese** (402 garbled), yet the parser reports 9,618
  units with **zero quality flags and zero errors**, and the selector picks plain
  mojibake as narrative evidence. `integrity.text_legibility` now catches this:
  the garbled file measures 2.663% characters in never-in-prose blocks versus
  0.000–0.076% for six clean filings.
- **There is almost no front-matter layer.** `document_meta` critical recall is
  **1/19**: facts like audit status, fiscal-year definition and TOC-vs-body
  barely reach any evidence. That is a missing layer, not under-selection.
- **US filings cannot be scored at all today.** The production replay path offers
  only PDF and transcript HTML. Real 10-Ks passed through the only HTML route
  return `units=0` with `transcript_start_missing`, so they are reported
  `UNAVAILABLE` rather than as documents with no business content.
- **The transcript path works but loses role facts.** `us-txt` routes correctly
  (`investor_call_transcript`), reads 489 units, completes its scan — and still
  recalls only 1 of 11 critical facts (0.091), almost all of them role and
  modality facts.
- **The documented title trap reproduces.** The one-page scanned confirmation
  opinion routes to `document_kind=prospectus`, yields 0 units, and its single
  page is reported opaque.

## Independent semantic review

`semantics.entailment` can never pass on regex or numeric agreement alone:

| state | meaning |
|---|---|
| no review supplied | `NOT_EVALUATED` — the honest default |
| review verdicts all entailed | `PASS` |
| review found an unsupported claim | `FAIL` |
| review could not decide | `PARTIAL` — uncertainty is not a defect |

A malformed review refuses the run rather than being ignored, because ignoring it
would report `NOT_EVALUATED` where the operator believed a review had been applied.

`controls.py` measures whether the review layer earns its place. Three injected
meaning-level defects — an unsupported interpretation attached to a correct
number, a dropped qualifier, and an invented causal attribution — **all pass every
deterministic check and all fail under review**. Separately, an all-`ENTAILED`
review cannot upgrade a deterministic `FAIL`: the layer can only add scrutiny.
A test asserts those properties, so the justification fails loudly if the
deterministic checkers ever become strong enough to make review redundant.

## Modes

| mode | reads | network | model | writes |
|---|---|---|---|---|
| `offline` | ≤200KiB synthetic fixtures | no | no | only the `offline/` child it creates |
| `native` | whitelisted originals via bindings | no | no | only the `native/` child it creates |
| `adapter` | a ROOT-injected observer file | no | no | nothing |

In `native` mode the benchmark **observes** the existing public surface
(`source_catalog.narrative_evidence.parse_pdf_bytes` / `parse_transcript_text` /
`document_normalization.normalize_document` / `select_narrative_evidence`) and never reimplements selection. When ROOT injects
a real adapter, `observer.observe_du_adapter()` passes a `du-input/1` mapping
through it.

## What is checked

| dimension | how |
|---|---|
| route type | does the observation's family match the gold's expected families |
| text legibility | are the parsed characters real text, or a broken CID font mapping (measured against a control) |
| critical-fact recall | is each gold fact carried by replayable evidence, via any of several equivalent support sets |
| context completeness | are semantic units complete and attached (NOT_EVALUATED when the baseline emits none) |
| citation replay | does every cited locator actually appear in the selected set |
| role / modality / quantity | negation kept, plan not stated as actual, question not restated as a company fact, total not restated as an increment, investment not restated as revenue, unit basis preserved |
| bilingual redundancy | is one fact summarised once across language lanes |
| derived space | is derived output within budget |
| time / resource | elapsed and call counts, measured rather than assumed |
| untested semantics | **NOT_EVALUATED** unless an independent review is supplied |

### Honesty rules baked into the oracle

- `coverage.native_scan == "unavailable"`, or a fact whose evidence page is
  opaque, yields **UNAVAILABLE** — never FAIL and never PASS.
- `coverage.complete` never substitutes for business recall, and claiming
  completeness over an unread page is itself a failure.
- Regex/numeric agreement is **not** entailment: `semantics.entailment` stays
  `NOT_EVALUATED` and the result carries a `spot_read_list` for the independent
  large-node review.
- A run with no route, no semantic units and no claims reports those dimensions
  `NOT_EVALUATED` rather than fabricating fields to look complete.

## Gold (`du-gold/1`)

`tools/document_understanding_benchmark/gold/*.json`. Each fact carries:

- `importance`: `critical` | `normal`
- `any_support_sets`: **several equivalent evidence sets**, so the gold never
  overfits to one line number; a support set may be bilingual
- `must_preserve` / `must_not_assert`: short field assertions and counterexamples
- `quantity_basis`: `total` / `incremental` / `period_flow` / `investment` / …
- `modality`: `actual` / `plan` / `negation` / `question` / `third_party`
- `role`: who is speaking (`company_filing`, `management_answer`, `analyst_question`, …)
- `fact_scope`: `narrative` (business content the evidence selection owns) or
  `document_meta` (audit status, fiscal-vs-calendar year, TOC-vs-body, page
  counts, provenance — owned by a front-end layer). Defaults to `narrative`.
- `reason`: why the fact matters and what the trap is

Quoted text per document is bounded to ≤8KiB; the largest current record uses 842 bytes.

Development gold — the 20 survey samples were already used to tune rules, so none
of these is holdout:

| sample | company | facts | critical |
|---|---|---|---|
| `cn-equity` | 恒锋工具 2020 equity offering | 10 | 7 |
| `cn-h1` | 中微公司 2026 half-year | 12 | 8 |
| `cn-ipo-confirmation` | 鼎龙股份 scanned confirmation opinion | 4 | 4 |
| `cn-ir` | 万润股份 IR record 20260515 | 10 | 7 |
| `cn-q-business` | 中微公司 2026 Q1 | 11 | 9 |
| `cn-q-sparse` | 世华科技 2026 Q1 (sparse quarter, negative example) | 13 | 9 |
| `hk-annual` | 名创优品 2024 HK annual | 7 | 6 |
| `hk-annual-mojibake` | 小米集團－Ｗ 2025 HK annual (CID-mojibake integrity case) | 4 | 3 |
| `us-10k` | Microsoft FY2025 10-K (consumption-based Azure) | 12 | 10 |
| `us-txt` | MSFT FY2026 Q4 earnings call (speaker roles) | 14 | 11 |
| `us-20f` | TAL FY2024 20-F (regulatory constraints) | 15 | 12 |

Holdout gold — none of these companies appears in the survey, the design
findings, or any tuning discussion, and the card's A/H/US-two-each target is met:

| sample | company | segment | facts | critical |
|---|---|---|---|---|
| `holdout-cn-glodon-q1` | 广联达 2025 Q1 | software | 9 | 5 |
| `holdout-cn-yake-q1` | 雅克科技 2022 Q1 | manufacturing | 13 | 7 |
| `holdout-hk-alibaba-fy2023` | 阿里巴巴 FY2023 | retail | 14 | 10 |
| `holdout-hk-biren-fy2025` | 壁仞科技 FY2025 | semiconductors | 12 | 10 |
| `holdout-us-mongodb-10k` | MongoDB FY2026 10-K | software | 16 | 11 |
| `holdout-us-nvidia-10k` | NVIDIA FY2025 10-K | semiconductors | 16 | 12 |

The nine elements the card names as its minimum critical set are all covered,
and `test_gold_set.py` fails if any of them is renamed, dropped or hollowed out.

## Counterexample mutations

`mutations.run_mutation_suite()` injects the card's defect list and reports, per
mutation, one of three outcomes:

- `DETECTED` — the mutated observation no longer passes.
- `NOT_DETECTED` — a real coverage gap, reported as a gap.
- `NOT_APPLICABLE` — the target does not exist in that observation, so nothing
  was injected. Counted as neither a hit nor a miss.

Current: **53/53 applicable mutations detected, 42 not applicable.**

## Current carrier support

`observer.carrier_support()` reports what the existing public path can actually
take in, without needing an original:

| carrier | supported | entry point |
|---|---|---|
| `.pdf` | yes | `parse_pdf_bytes` |
| `.txt` / `.md` | yes | `parse_transcript_text` |
| `.htm` / `.html` | yes | existing `normalize_document` HTML frontend |
| `.pptx` / `.docx` | yes | existing `normalize_document` frontends (opaque/OCR gaps stay explicit) |

A carrier the path cannot take in is reported `UNAVAILABLE`, and native run
reports list the unsupported suffixes explicitly, so "unsupported carrier" can
never be mistaken for "document with no business content".

## Historical pre-repair baseline on real originals (do not reuse its HTML attribution)

Read-only replay through the existing public parser/selector, 2026-10-13.
Development and holdout are kept apart on purpose.

| sample | split | status | critical recall | spans | candidates | scan |
|---|---|---|---|---|---|---|
| `cn-equity` | dev | FAIL | 0/7 | 96 (capped) | 449 | partial |
| `cn-h1` | dev | FAIL | 2/8 | 96 (capped) | 369 | partial |
| `cn-ipo-confirmation` | dev | FAIL | 0/4 | 0 | 0 | partial, p1 opaque |
| `cn-ir` | dev | FAIL | 1/7 | 11 | 11 | complete |
| `cn-q-business` | dev | FAIL | 6/9 | 28 | 28 | partial |
| `hk-annual` | dev | FAIL | 0/6 | 96 (capped) | 254 | partial, p246 opaque |
| `holdout-cn-glodon-q1` | **holdout** | FAIL | 0/7 | **0** | **0** | partial |
| `holdout-cn-yake-q1` | **holdout** | FAIL | 0/8 | 2 | 2 | partial |
| `holdout-hk-alibaba-fy2023` | **holdout** | FAIL | 0/10 | 96 (capped) | 2221 | partial |
| `holdout-us-mongodb-10k` | **holdout** | PARTIAL | n/a | — | — | **unavailable (HTML)** |
| `holdout-us-nvidia-10k` | **holdout** | PARTIAL | n/a | — | — | **unavailable (HTML)** |

Totals: development 9/41 = **0.220**, holdout 0/45 = **0.000**.

These FAILs are the deliverable, not a broken test. Confirmed:

- 恒锋 建设期/第一期/第二期 never reach the selected text;
- 名创优品 p12 store table is entirely unselected — all 7 facts absent;
- 广联达 Q1 produced **zero candidates from 257 units**;
- 雅克科技 Q1 produced **2 candidates from 369 units**;
- 阿里巴巴 FY2023 produced 2,221 candidates and selected none of the 14 facts;
- 鼎龙 confirmation opinion routes to `prospectus` with 0 units on an opaque page;
- the two US 10-Ks have no carrier route at all.

## Tests

```bash
# default: fast, fully offline (143 passed / 7 real-data skips, 3.47s on reception host)
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q

# real originals, opt-in (needs the local bindings file)
$env:DU_BENCH_ALLOW_REAL_DATA = "1"
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q -m real_data
```

The real-original tests are skipped rather than deselected by default, because
`pytest.ini` is shared configuration this lane must not edit. That keeps the
default suite fully offline while still allowing the native quality report to be
run explicitly.

## Safety and restoration

`recovery.py` proves a run left the world as it found it:

- originals: SHA-256 **and** mtime unchanged, checked per sample and reported as
  `raw_unchanged`;
- production config passed via `--probe-config`: SHA-256 and mtime unchanged, and
  the number of probed files is reported (`restoration.config_unchanged.count`)
  so an empty probe list cannot look like a pass;
- a sentinel is **captured before the run overwrites it** and written back
  byte-identical with its original mtime afterwards; `restoration.sentinel_restored`
  reports `restored` (a pre-existing sentinel) or `created_by_this_run` (no prior
  content, so the check is that this run's own bytes survive);
- cleanup deletes **only** a child the run marked owned — an unmarked directory
  is refused, never removed.

`RAWS_COPIED: 0`, `MODEL_CALLS: 0`, `PAID_CALLS: 0` are asserted by the offline
CLI test.

## Package layout

| module | role |
|---|---|
| `schema.py` | frozen wire constants and enums |
| `records.py` | `du-gold/1` and `du-observed/1` validation |
| `textutil.py` | deterministic text, number, unit, modality and stage primitives |
| `checkers.py` | the nine check dimensions |
| `evaluate.py` | public `evaluate(observed, gold)` |
| `gold.py` | gold loading and SHA-bound original resolution |
| `observer.py` | read-only observation plus carrier capability |
| `mutations.py` | 19 counterexample mutations, three-valued outcome |
| `review.py` | `du-review/1` independent semantic review |
| `controls.py` | proof the review layer is load-bearing |
| `recovery.py` | fingerprints, sentinel, owned-directory cleanup |
| `fixtures.py` | offline synthetic fixtures |
| `report.py`, `make_bindings.py` | maintainer helpers |
| `gold/`, `reviews/`, `holdout.json` | data |

## Scope and ownership

Owned: `tools/document_understanding_benchmark/**` and `.planning/du-bench/**`.
Not touched: `src/**`, other tests, production config, CI, the other two DU
packages, the parent plan. This package deliberately does not import
`company_wiki` from its oracle; only `observer.py` touches it, and only to read
through the existing public entry points.

See `.planning/du-bench/handoff.md` and `handoff.json` for the A/B/C evidence,
known gaps, and the acquisition requests for ROOT.
