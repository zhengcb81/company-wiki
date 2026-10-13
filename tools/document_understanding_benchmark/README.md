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
```

Exit codes: `0` all evaluated samples PASS, `1` any FAIL, `2` refused to run
(bad gold/bindings/adapter), `3` PARTIAL or UNAVAILABLE present.

`--bindings` is a **local, uncommitted** `{sample_id: absolute_path}` JSON file.
Originals are never copied, and a missing binding or SHA-256 mismatch yields
`UNAVAILABLE` — never a substituted or synthetic document.

## Modes

| mode | reads | network | model | writes |
|---|---|---|---|---|
| `offline` | ≤200KiB synthetic fixtures | no | no | only the `offline/` child it creates |
| `native` | whitelisted originals via bindings | no | no | only the `native/` child it creates |
| `adapter` | a ROOT-injected observer file | no | no | nothing |

In `native` mode the benchmark **observes** the existing public surface
(`source_catalog.narrative_evidence.parse_pdf_bytes` / `parse_transcript_text` /
`select_narrative_evidence`) and never reimplements selection. When ROOT injects
a real adapter, `observer.observe_du_adapter()` passes a `du-input/1` mapping
through it.

## What is checked

| dimension | how |
|---|---|
| route type | does the observation's family match the gold's expected families |
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
- `reason`: why the fact matters and what the trap is

Quoted text per document is bounded to ≤8KiB; the four real records currently
use 0.42–0.56KiB each.

Current development gold (all `scope: development`; the survey samples were
already used to tune rules, so none of them is holdout):

| sample | company | facts | critical |
|---|---|---|---|
| `cn-equity` | 恒锋工具 2020 equity offering | 10 | 7 |
| `cn-ir` | 万润股份 IR record 20260515 | 10 | 7 |
| `cn-q-business` | 中微公司 2026 Q1 | 11 | 9 |
| `hk-annual` | 名创优品 2024 HK annual | 7 | 6 |

## Counterexample mutations

`mutations.run_mutation_suite()` injects the card's defect list and reports, per
mutation, one of three outcomes:

- `DETECTED` — the mutated observation no longer passes.
- `NOT_DETECTED` — a real coverage gap, reported as a gap.
- `NOT_APPLICABLE` — the target does not exist in that observation, so nothing
  was injected. Counted as neither a hit nor a miss.

Current: **53/53 applicable mutations detected, 42 not applicable.**

## Measured baseline on the four real originals (node C)

Read-only replay through the existing public parser/selector, 2026-10-13:

| sample | status | critical recall | all-fact recall | route | spans | scan |
|---|---|---|---|---|---|---|
| `cn-equity` | FAIL | 0/7 | 1/10 | family unknown → FAIL | 96/449 (capped) | partial |
| `cn-ir` | FAIL | 1/7 | 1/10 | investor_qa → PASS | 11/11 | complete |
| `cn-q-business` | FAIL | 6/9 | 7/11 | quarterly vs expected quarterly_report → FAIL | 28/28 | partial |
| `hk-annual` | FAIL | 0/6 | 0/7 | annual → PASS | 96/254 (capped) | partial (p246 opaque) |

These FAILs are the deliverable, not a broken test. Confirmed known misses:

- 恒锋 建设期/第一期/第二期 never reach the selected text (96-span cap,
  353 of 449 candidates omitted);
- 名创优品 p12 store table is entirely unselected — **all 7** hk-annual facts
  are absent, including TOP TOY store counts and the operating-model breakdown;
- the 96-span cap is genuinely partial on cn-equity and hk-annual
  (`selector_status: partial`, `omitted_candidate_count` > 150 in both).

## Tests

```bash
# default: fast, fully offline
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q

# real originals, opt-in (needs the local bindings file)
$env:DU_BENCH_ALLOW_REAL_DATA = "1"
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q -m real_data
```

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

## Scope and ownership

Owned: `tools/document_understanding_benchmark/**` and `.planning/du-bench/**`.
Not touched: `src/**`, other tests, production config, CI, the other two DU
packages, the parent plan. This package deliberately does not import
`company_wiki` from its oracle; only `observer.py` touches it, and only to read
through the existing public entry points.

See `.planning/du-bench/handoff.md` and `handoff.json` for the A/B/C evidence,
known gaps, and the acquisition requests for ROOT.
