# DU-BENCH Progress

Append-only session log.

## 2026-10-13 — session 1

- Read the DU-BENCH card plus parent README / design / INTERFACES /
  implementation / findings. Confirmed the card's work directory, branch and
  owned paths.
- Confirmed worktree HEAD `7f6f7cbd`, branch `codex/du-benchmark-20261013`,
  clean, no pre-existing `.planning/`.
- Verified all 20 survey originals present with matching SHA-256 (0 paid calls,
  0 original writes, 0 copies).
- Created `.planning/du-bench/{task_plan,findings,progress}.md`
  (PLAN_ID=du-bench, PWF_PLAN_ROOT=<worktree>/.planning).
- Next: Phase 1 — freeze the interfaces and write RED tests.

## 2026-10-13 — session 1, Phase 1 (RED)

- Wrote `tools/document_understanding_benchmark/{__init__,schema,records,evaluate}.py`
  and `tests/{synthetic,test_evaluate_red}.py`.
- RED evidence: `python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q`
  → **19 failed, 8 passed**, every failure caused by
  `NotImplementedError: RED: evaluate() is not implemented yet`. The 8 passing
  tests are schema validation, which is implemented first on purpose.
- The 19 RED tests encode: correct observation PASSes; wrong route family
  FAILs; missing route = NOT_EVALUATED; dropped critical fact FAILs; fact
  carried only by replayed selection text still counts; unread page =
  UNAVAILABLE not FAIL; invented claim FAILs; locator never selected FAILs
  replay; total→net-addition FAILs; negation flip FAILs; question premise
  promoted to company fact FAILs; 万元→元/亿元 FAILs; investment→revenue basis
  FAILs; bilingual duplicate summary FAILs; derived-space over budget FAILs;
  entailment stays NOT_EVALUATED with a spot-read list; SHA mismatch =
  UNAVAILABLE; `coverage_complete` alone never PASSes.
- Oracle implemented in `checkers.py` + `textutil.py` + `evaluate.py`;
  **27 passed** (RED → GREEN with the same tests, none loosened).
- Overall-status rule decided: `NOT_EVALUATED` on `semantics.entailment` is the
  expected unaudited state and does not by itself downgrade to PARTIAL;
  UNAVAILABLE on anything the benchmark actually measures (source identity,
  recall, route, replay) still does. `FAIL` always wins.
- Note recorded: `must_not_assert` literal tokens do **not** catch paraphrases
  ("净新增门店7,504家" vs token "净新增7,504家"). Added an explicit
  `quantity_basis` field to gold facts plus `basis_contradiction()` so
  total→increment, investment→revenue, plan→actual restatements are caught.

## 2026-10-13 — session 1, Phase 2 (real gold)

- Next: read the originals and author real gold.

## 2026-10-13 — session 1, Phase 2 done + Phases 3–4

- Read originals directly (bounded page extraction): 恒锋 p61–63, 万润 p1–3,
  名创 HK 年报 p12, 中微 2026Q1 p2–4. Two independent subagents read the US
  filings (MSFT 10-K, MSFT call TXT, TAL 20-F, VRSK 10-Q) and reported verbatim
  quotes; a third attempt confirmed the 鼎龙 scan is image-only.
- Authored 4 real gold records (cn-equity 10 facts, cn-ir 10, cn-q-business 11,
  hk-annual 7) — 38 facts, 29 critical, each **0.42–0.56KiB** of quoted text,
  far inside the 8KiB/document budget. Facts were taken from the document, not
  from selector output; the selector's misses are recorded as misses.
- Implemented `checkers.py`, `textutil.py`, `gold.py`, `observer.py`,
  `recovery.py`, `mutations.py`, `fixtures.py`, `__main__.py`.
- Offline CLI green: 5 synthetic fixtures, 14,309 fixture bytes of the 200KiB
  budget, 0 network calls, 0 model calls, 0 paid calls, sentinel stable.
- Mutation suite measured and then fixed: 48/53 → **53/53 applicable detected**
  (42 correctly reported NOT_APPLICABLE because their target does not exist in
  that fixture). Two classes were kept separate so neither inflates the gap nor
  fakes a hit.
- Real bugs found by the suite and fixed in the oracle:
  1. `must_not_assert` literal tokens miss paraphrases → added `quantity_basis`
     + `basis_contradiction()`.
  2. Anchor-quote-only claim association missed rewritten claims → added
     `_related_claims()` keyed on subject words and the fact's number.
  3. No way to express "this fact is a plan" → added a gold `modality` and
     `role` field with `_modalities_conflict()`.
  4. Stage collapse (量产验证 → 已量产) was invisible → added `STAGE_ORDER`
     and `stage_regression()`.
  5. `coverage.complete` over unread pages was unchecked → added
     `check_coverage_honesty`.
  6. Quantities without unit/period (dropped table header) were unchecked →
     added `check_quantity_provenance`.
  7. Subject swap (controller → listed company) was unchecked → added
     `_fact_subject()`/`_has_foreign_subject()`.
  8. **False positive found by the new fixture**: `不超过35,978.71万元` was read
     as negation because of the 不 character, failing a legitimate plan claim →
     `_BOUND_PHRASES` now strips quantity bounds before negation detection.
- Test suite: **47 passed** (27 oracle + 20 mutation/fixture/CLI).
- Next: Phase 5 native read-only replay + recovery evidence.
