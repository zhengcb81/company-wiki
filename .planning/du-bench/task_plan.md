# DU-BENCH Task Plan

PLAN_ID: du-bench
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/benchmark/.planning
Worktree: C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/benchmark
Branch: codex/du-benchmark-20261013
Base: 7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8

## Goal

Build an **independent** gold/oracle, offline counterexample suite, and native
read-only replay for document understanding. The benchmark must be able to
detect real omissions and hallucinations; it must never derive expectations
from the current selector's output, and must never modify production
algorithms to make the benchmark pass.

Owned paths (exclusive):

- `tools/document_understanding_benchmark/**` (including its own tests/fixtures)
- `.planning/du-bench/**`

Forbidden: `src/**`, other tests, config, CI, the other two DU packages, the
parent plan, RF/FF/Audit/Dayu/IQS.

## Next Step

Write `.planning/du-bench/handoff.{md,json}`, run the scope self-check, and
commit this branch. ROOT owns integration.

## Phases

### Phase 1 — Interface freeze + RED
**Status:** complete

- Freeze `du-gold/1`, `du-observed/1`, `du-evaluation/1` and the public
  `evaluate(observed, gold) -> dict` entry point.
- Write RED tests using synthetic correct/incorrect `observed` records before
  implementing the oracle.

### Phase 2 — Real gold from originals
**Status:** complete

- Read the originals (text + images) and record per-fact source/scope/subject/
  period/modality/quantity basis. Facts chosen from the document, not from what
  the new implementation happens to select.
- 20 survey samples seeded as `development`. Samples already used to tune
  rules (中微 etc.) are explicitly **not** holdout.

### Phase 3 — Oracle + checkers (node A)
**Status:** complete

- Separate checkers for: route type accuracy, critical-fact recall, context
  completeness, citation replay, role/modality/quantity basis, bilingual
  redundancy, derived-space, time/resource, untested semantics.
- Regex/numeric agreement never auto-proves semantic entailment:
  `NOT_EVALUATED` for unreviewed entailment, plus a human/independent-agent
  spot-read list handed to ROOT.
- Node A records the real FAIL/PARTIAL of the current baseline; it is not
  required to be green first.

### Phase 4 — Offline CLI + counterexample mutations (node B)
**Status:** complete

- Synthetic, no-network CLI over ≤200KiB fixtures.
- Negative mutations: dropped subject, deleted negation, 万元→亿元, total→new
  addition, GMV→revenue, future→actual, question→company statement, dropped
  table header, missing page yet `complete`, TOC-only, stale reuse of a new
  source version, test output self-certification.
- Bad observations must fail. If the oracle cannot detect a mutation, say
  `NOT_EVALUATED` honestly.
- Oracle unit tests + offline CLI green; independence and missing-field states
  pass.

### Phase 5 — Native CLI read-only replay (node C)
**Status:** complete

- Resolve originals by SHA + local bindings; ROOT survey manifest is a locator
  clue only; temporary paths may vanish → `UNAVAILABLE`.
- Observe existing public parser/selector only; never write a new selector.
- Recovery test: sentinel in own TemporaryDirectory, verify original/config
  SHA+mtime unchanged, sentinel restored, own scratch deleted.
- Missing new structure/model summary ⇒ `NOT_EVALUATED`, not a fake PASS.

### Phase 6 — Holdout + handoff
**Status:** in_progress

- Prefer A/H/US holdout companies spanning manufacturing/retail/software.
- Where real US S-1/F-1/8-K/6-K containers are missing, write `UNAVAILABLE`
  plus a ROOT FF acquisition request list; never substitute synthetic samples
  for real coverage.
- `.planning/du-bench/handoff.{md,json}` per INTERFACES §7, plus dev/holdout
  counts, missing types, per-dimension denominators, baseline problems, not
  yet automatically checkable semantics, acquisition requests, 0 paid calls /
  0 original writes, recovery and size.
- Commit on this branch and stop. ROOT owns integration.

## Decisions Made

| # | Decision | Why |
|---|---|---|
| D1 | Gold facts are authored from the original PDFs/pages read directly, never from selector output | Card requirement: measure real omission/hallucination |
| D2 | Oracle checks are pure functions over JSON-serializable mappings; no import of `src/**` | Independence: the measured system must not shape the measurement |
| D3 | `du-gold/1` uses `any_support_sets` (multiple equivalent evidence sets) | Avoid overfitting to one line number |
| D4 | Entailment that the oracle cannot verify deterministically is reported as `NOT_EVALUATED`, never PASS | Regex/numeric agreement is not entailment |
| D5 | Native replay observes the existing public parser/selector; missing DU fields ⇒ `NOT_EVALUATED` | Baseline has no new structure; cannot fabricate new fields |
| D6 | Originals resolved by SHA-256 via local bindings with `UNAVAILABLE` fallback | Survey temp roots may vanish; no path hardcoding |
| D7 | Gold facts declare `modality` and `role`, not only text and quantity | Plan-vs-actual and question-vs-statement errors are otherwise undetectable |
| D8 | Mutation outcomes are three-valued: DETECTED / NOT_DETECTED / NOT_APPLICABLE | Counting inapplicable mutations as misses understates; counting them as hits fakes |
| D9 | US holdout is recorded `UNAVAILABLE` with acquisition requests | No local US original exists outside the development set; a synthetic substitute would fake coverage |
| D10 | Real-original tests need `DU_BENCH_ALLOW_REAL_DATA=1` | The card requires the offline suite and the native quality report to be separate, and shared `pytest.ini` is not mine to edit |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Inline `python -c` with quotes broke PowerShell parsing | 1 | Wrote a temp `.py` file instead of inline `-c` |
