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

## 2026-10-13 — session 1, Phases 5–6 (done, branch committed)

- Native replay against 4 real originals: all resolved by SHA, **all four
  `raw_unchanged: true`**, `config/source_catalog.yaml` unchanged, 0 raw copies,
  0 network / 0 model / 0 paid calls. Real recall measured, not faked:
  cn-equity 0.000, cn-ir 0.143, cn-q-business 0.667, hk-annual 0.000.
- `make_bindings.py` bound **20/20** survey originals by SHA. It also proved the
  card's warning concretely: relative manifest paths resolve against the main
  checkout, not this sparse worktree, so the manifest alone cannot locate
  originals and bindings are required.
- Real-original tests made opt-in (`DU_BENCH_ALLOW_REAL_DATA=1`, plus the
  `real_data` marker) rather than the default, because `pytest.ini` is shared
  config this lane must not edit. Default suite stays fully offline at ~1.1s.
- Holdout surveyed: 263 non-development companies available. Recorded 广联达
  (software), 雅克科技 (manufacturing), 阿里巴巴 (retail) as candidates and
  **US holdout as UNAVAILABLE** with five acquisition requests.
- Wrote `README.md`, `holdout.json`, `handoff.md`, `handoff.json`.
- Final verification: ruff clean, **65 passed / 5 skipped**, offline CLI green
  with 53/53 applicable mutations detected, C-node report with
  `raw_all_unchanged: true`.
- Committed on `codex/du-benchmark-20261013`: `ad77758d` (implementation) and
  `74872d03` (handoff SHA). `git diff --name-only <base>...HEAD` is exactly the
  30 owned files; `git status` clean.

## Outcome at end of session 1 (superseded by session 2 below)

Session 1 closed with 4 development records and **zero** holdout, and reported
US coverage as UNAVAILABLE. Both were later corrected: real US originals did
exist locally, and holdout gold was authored in session 2. The measured recall
at that point was cn-equity 0.000 / cn-ir 0.143 / cn-q-business 0.667 /
hk-annual 0.000, and the strongest single finding — that `cn-ir` exhausted no
budget at all (11 candidates, 11 selected, 9 of 10 facts still absent) — was
confirmed and extended in session 2.


## 2026-10-13 — session 2: native replay re-verification + benchmark self-fixes

- Re-ran the C node against all four real originals. Originals still SHA-match both
  gold and the ROOT manifest; mtime_ns identical to session start
  (1608820218000000000 / 1779228233262998600 / 1779046989673803600 /
  1761392825000000000). No PDF was copied into the worktree.
- Native replay reproduces exactly: cn-equity FAIL 0.000, cn-ir FAIL 0.143,
  cn-q-business FAIL 0.667, hk-annual FAIL 0.000 (critical denominators 7/7/9/6).
  Exit 1, 0 network / 0 model / 0 paid calls, raw_unchanged true, config unchanged.
- Known misses reproduced by inspecting the selected text directly:
  恒锋 建设期/第一期/第二期 all absent (募集资金 present), 449 candidates with
  353 omitted; all 7 hk-annual facts absent including the p12 store table.
- Two corrections to the plan's phrasing: the 名创 miss is the p12 store-table
  facts (the bare string "TOP TOY" does appear elsewhere in the selection), and
  the 96-span cap binds on only cn-equity and hk-annual, not on cn-ir/cn-q-business.
- Found and fixed four real defects in the benchmark itself:
  1. peak_rss_bytes() always returned None — ctypes called GetProcessMemoryInfo
     without argtypes/restype, truncating the 64-bit HANDLE so both psapi and K32
     returned 0. Now measured: 121,929,728 native / 21,049,344 offline.
  2. install_sentinel() rewrote the sentinel unconditionally, so sentinel_stable
     compared a fresh file against itself and could never detect a clobbered
     pre-existing sentinel. Now captured pre-run and restored byte+mtime identical.
  3. restore_sentinel() had a NameError typo, caught by the new sentinel test.
  4. config_unchanged reported count=0 with no --probe-config, looking like a pass
     while proving nothing; the probe count is now printed and includes the sentinel.
- Added two regression tests (sentinel preservation across a real CLI run, peak-RSS
  measurement). Suite: 65 passed / 5 skipped offline; 5 real-data replay tests pass
  with DU_BENCH_ALLOW_REAL_DATA=1.
- Removed all 10 _scratch_* inspectors and __pycache__; kept a compact
  evidence.json so no measured number depends on throwaway scripts.
- Commits on codex/du-benchmark-20261013: ad77758d (implementation),
  74872d03 / 3b7aa7ab / ebb5453f / aa817a4a / 1d5cfaa5 (handoff + evidence).
  31 files, all inside tools/document_understanding_benchmark/** and
  .planning/du-bench/**. .du-bench-out/ is regenerable scratch, not committed.

## 2026-10-13 — session 2: full holdout coverage, review layer, carrier reality

Session 1 left holdout at zero. This session closed it.

- **Holdout gold authored (5 records, 68 facts).** A-share 广联达 2025Q1 and
  雅克科技 2022Q1; H-share 阿里巴巴 FY2023 (360pp traditional Chinese); US
  MongoDB FY2026 10-K and NVIDIA FY2025 10-K. The US pair was read by an
  independent subagent that returned verbatim quotes plus documented traps.
- **Correction to session 1:** US originals *did* exist locally — four real
  10-Ks under `company-wiki/companies/{Alphabet,Apple,NVIDIA,MongoDB}`, none
  previously used in the DU work. The earlier UNAVAILABLE was replaced with
  real, SHA-bound gold rather than left as a request.
- **Development gold extended:** `cn-h1` (中微 half-year — a five-year target
  stated beside a present-tense coverage figure, and six distinct product
  verification stages) and `cn-ipo-confirmation` (the scanned page, encoded as
  an opacity/anti-fabrication test rather than a content test).
- **Scope reporting added end to end.** `evaluate`, the CLI and the run report
  separate development from holdout, and `test_gold_set.py` makes merging them
  a test failure. Measured: dev **9/41 = 0.220**, holdout **0/45 = 0.000**.
- **New findings, each measured:**
  - `holdout-cn-glodon-q1` produced **0 candidates from 257 units**.
  - `holdout-cn-yake-q1` produced 2 candidates from 369 units.
  - `holdout-hk-alibaba-fy2023` produced 2,221 candidates and selected none of
    its 14 facts; 18,038 units over 360 pages.
  - `cn-ipo-confirmation` routes to `document_kind=prospectus` with 0 units and
    an opaque page 1 — the documented title trap, now reproduced.
  - All 11 documents yield **0 claims and 0 semantic units**, which is why
    context/role/entailment stay structurally NOT_EVALUATED.
- **Review layer built and negative-controlled.** `review.py` (`du-review/1`)
  with a four-state entailment verdict; a real 5-fixture / 11-claim independent
  review artifact; and `controls.py` proving 3/3 injected meaning-level defects
  are invisible to deterministic checks and caught by review, while an
  all-ENTAILED review cannot rescue a deterministic FAIL. A test asserts those
  properties so a stale justification fails loudly.
- **Carrier reality measured.** The existing public path supports only PDF and
  transcript carriers: two real 10-Ks return `units=0` with
  `transcript_start_missing`, and their extracted text is led by inline-XBRL
  tokens. `observer.carrier_support()` and the native report now name
  unsupported carriers explicitly, so "carrier unsupported" cannot be misread
  as "document has no content".
- Verification: **100 offline + 7 real-data tests pass**, ruff clean, 53/53
  applicable mutations detected, `raw_unchanged` and `config_unchanged` true
  across all 11 samples, 0 paid calls, bindings moved outside the worktree.
- `evidence.json` is now **generated from the run artifacts**, so its recorded
  numbers cannot drift from what was actually measured.

## 2026-10-13 — session 3: audit against the card, four self-defects fixed

The user asked whether the work was actually complete and whether it had
problems. Both were true, so this session audited rather than asserted.

**Audit result: the card's step-2 minimum critical set had 4 of 9 elements with
no gold at all** — `cn-q-sparse` (财务季报负例), `us-10k` (微软消费制 Azure),
`us-txt` (电话会角色), `us-20f` (TAL 监管业务约束). All four originals were bound
and readable; the gap was mine. All four records are now authored and SHA-bound,
and `test_gold_set.py` fails if any element is renamed, dropped or hollowed out.
The set is now **14/14 covered, 0 gaps**.

Four defects in the benchmark itself were found and fixed:

1. **Recall denominator conflated "could not read" with "found none".**
   `critical_fact_recall` used the declared denominator while `fact_recall` in
   the same file excluded `UNAVAILABLE`. An unreadable document therefore
   reported `0.000` recall, which reads as a total miss. Both now exclude
   unavailable facts, `coverage` and `*_denominator_declared` are reported
   separately, and two regression tests guard it. `cn-ipo-confirmation` now
   reports `n/a` instead of a misleading `0.000`.
2. **`make_bindings` destroyed holdout bindings.** The survey manifest lists only
   the 20 survey samples; holdout records are not in it, so a rebuild silently
   dropped all 5. A dropped binding is indistinguishable from a missing original
   in the report, so holdout coverage silently collapsed to `0.000`. *This was
   hit for real during the session.* Non-manifest bindings are now preserved by
   default (`--replace` opts out), with a regression test.
3. **Gold facts did not separate business content from document facts.** `us-txt`
   mixed "the selector should carry this" with "the document says this", so its
   recall figure blamed the selector for front-matter facts. Added an optional
   `fact_scope` (`narrative` | `document_meta`, default `narrative`) and both
   splits are reported.
4. **No guard on the card's minimum set** (see above).

New measured findings this round:

- `cn-q-sparse` produced **0 candidates from 429 units** (`needs_review`) — a
  second independent zero-candidate case beside `holdout-cn-glodon-q1`'s 0/257.
- **`document_meta` recall is 0/9** in development: audit status, fiscal-year
  definition, TOC-vs-body, page count and provenance facts reach no evidence at
  all. That is a missing layer, not under-selection.
- **`us-txt` measured for real** (TXT is a supported carrier): routing is correct
  (`investor_call_transcript`), 96/107 selected, 489 units, scan complete — and
  only **1 of 11** critical facts recalled (0.091), almost all of them role and
  modality facts.

Final numbers, development and holdout kept apart with coverage beside recall:
development critical 10/57 = **0.175** (57 evaluable of 83, coverage 0.687;
narrative 0.191, document_meta 0.000); holdout critical 0/22 = **0.000**
(22 of 45, coverage 0.489; narrative 0/36).
Verification: 105 offline tests + 7 real-data tests pass, ruff clean, 53/53
applicable mutations detected, raw and config unchanged across all 15 samples,
0 paid calls.

## 2026-10-13 — session 4: second H-share, refusal-path bug, CID-mojibake class

Continuing the audit. Three more real gaps closed and one new defect class found.

- **Second H-share holdout added** (`holdout-hk-biren-fy2025`, 壁仞科技 FY2025,
  215-page traditional-Chinese annual report). The card asks for two new
  companies per market; H-share had one. Holdout is now A 2 / H 2 / US 2.
- **Checked extraction quality before authoring**, which is how the next finding
  surfaced: 小米集團－Ｗ's HK annual report extracts as **mojibake** (415 pages,
  0 readable Chinese, 402 garbled), because its PDF text layer uses an unmapped
  CID font. 壁仞科技 and 金山雲 extract cleanly, so 壁仞 was used.
- **New defect class: a fully garbled document parses clean.** The mojibake file
  yields **9,618 units, zero quality flags, zero errors, 2 opaque pages of 415**
  and the selector picks `姽⅌彨ṍ嘗` as narrative evidence. Failure mode is silent.
  Added `integrity.text_legibility` with a measured control: six clean filings
  score 0.000–0.076% characters in never-in-prose blocks; the garbled file scores
  **2.663%** (35x). A CJK-ratio test was tried first and **does not work** — this
  mojibake maps to valid-but-wrong CJK codepoints and still scores 44% CJK.
  Legibility is measured over **all parsed text**, not the selection: the garbled
  file kept only 195 selected characters, below any workable threshold.
- **Self-defect 5: a refused run clobbered the sentinel.** `install_sentinel`
  overwrites what it finds and relies on the caller restoring it, but both CLI
  modes `return EXIT_REFUSED` before `restore_sentinel`. Caught by writing the
  failure-case test the card asks for (RED first), fixed with `try/finally`.
- **Self-defect 6: the legibility check judged the wrong text** (selection rather
  than everything parsed), which made the defect invisible. Fixed and covered by
  three parsed-basis tests.
- Also corrected my own audit script twice (a literal token match produced a
  false "partial" for `hk-annual`, and a scratch `Set-Content` mangled a CJK path)
  — both were tooling errors, not product errors, and neither reached a commit.

Verification: **117 offline tests + 7 real-data tests pass**, ruff clean, 53/53
applicable mutations detected, raw and config unchanged across all 17 samples,
0 network / 0 model / 0 paid calls. Development critical 11/60 = 0.183
(coverage 0.698; narrative 0.191, document_meta 0.053); holdout 0/31 = 0.000
(coverage 0.574; narrative 0.013).
