# DU-PROFILES progress

## 2026-10-13 A — reconnaissance and RED freeze

- Read card DU-PROFILES, plan README/design/INTERFACES/implementation, worktree AGENTS.
- Recorded base: branch `codex/du-profiles-20261013`, HEAD
  `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`, `git status` clean.
- Extracted bounded real evidence from the plan's `sample_observations.json.gz` and
  `sample_manifest.json` (titles, TOCs, short excerpts only; no PDF copied, no network,
  0 paid calls). Findings recorded in findings.md.
- Confirmed the two headline real defects: confirmation letter with
  `title_only_kind=prospectus` and empty native text; `发行A股股票募集说明书` with
  `title_only_kind=unknown`.
- Confirmed `cn-ir-policy` in the manifest actually contains an IR activity record body,
  so metadata/content conflict is a real observed case.
- Next: write the A-node RED tests and fixtures against the frozen `du-route/1` wire.

## 2026-10-13 A — RED frozen

- Wrote `tests/fixtures/document_understanding_profiles/` (builders + bounded real
  fragments) and three unit modules: wire/profile matrix, routing matrix, negatives +
  limits/determinism.
- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q`
  -> **64 failed** (module `company_wiki.document_understanding.profiles` does not exist).
  RED confirmed: no test passes for the wrong reason and no oracle was relaxed.
- Next: implement the package until green.

## 2026-10-13 A/B — implementation green

- Implemented `vocabulary.py`, `model.py`, `registry.py`, `observation.py`, `signals.py`,
  `decision.py`, `__init__.py` (18 required section roles, 15 profiles, 3 public functions).
- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q`
  -> **64 passed**.
- Real defects found and fixed during the loop (each one was a genuine routing bug, not a
  test adjustment):
  1. a pageless 3-unit document had its whole text taken as "cover", so a results release
     produced no body evidence -> positional cover now disabled below
     `MIN_UNITS_FOR_POSITIONAL_COVER`;
  2. `see our Form 10-K` / `详见…招股说明书` in prose was treated as self-identification ->
     added a cross-reference cue + heading-like gate (`is_title_evidence`);
  3. a wrong `form_type=10-K` beat real HK bilingual structure -> cover/section evidence
     now outranks metadata, and the disagreement is reported;
  4. a scan-only/unavailable body was still hinted as `read` -> `read` now requires at
     least one non-blank unit.
- Next: B-node hardening (determinism, immutability, budget, calibration) and ruff.

## 2026-10-13 B — invariants green, lint clean

- Added `test_b_invariants.py` (74 independent checks): purity/repeatability, input
  immutability, JSON-serializability, vocabulary closure, reason unit-ids must exist,
  never-skip, no path/company leakage, budget monotonicity (a smaller probe may never
  raise confidence), contradiction survives any budget, unknown never forced to annual,
  profile composition/reuse, SEC vs HK vocabulary separateness, negative hints are not
  delete rules, external attachments never become SourceRefs, 5k-unit scale trend.
- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q`
  -> **138 passed**.
- `python -X utf8 -m ruff check src/.../profiles tests/unit/document_understanding_profiles
  tests/fixtures/document_understanding_profiles` -> **All checks passed** (repo CI runs
  ruff over `src` and `tests/unit` with default rules, so this matches the real gate).
- Note: test modules obtain the package through `import_profiles_module()` rather than a
  pytest fixture, because an imported fixture name reused as a parameter trips ruff F811.
- Next: C-node on real sample shapes, then handoff.

## 2026-10-13 C — real originals routed, four more real defects fixed

- Added `.planning/du-profiles/_cnode_real_probe.py`: opens the 7 real originals named by the
  coordinator (5 PDF + 1 HTML + 1 TXT), verifies each SHA-256 against `sample_manifest.json`
  BEFORE parsing, reads them with the **existing** production parsers
  (`source_catalog.narrative_evidence.parse_pdf`, `document_normalization.normalize_document`),
  routes them, and writes bounded evidence to `.planning/du-profiles/c-evidence/`.
  Excerpts capped at 8 KiB/document; originals never copied into the worktree.
- First run: 6/7 observed. `us-10k-msft-2025` UNAVAILABLE (my probe read `unit.text` where the
  normalizer exposes `raw_text`) -> fixed the probe, not the package. **hk-annual-miniso-2024
  routed to `earnings_call`** — a real defect, not a probe bug.
- Real defects the real originals exposed (all fixed, all locked by
  `test_c_real_shape_regressions.py`; none passed by relaxing a test or an oracle):
  1. `SPEAKER_TURN` matched the statement-footnote labels `Notes:`/`Note:` (33 occurrences in
     the 246-page Miniso annual report) -> real annual report routed to `earnings_call`.
     Added `is_speaker_turn()` + closed `NON_SPEAKER_LABELS`.
  2. Cross-regime QA/transcript candidates could outrank a regime-specific periodic candidate
     (`_call_candidate` 76 > `_hk_candidate` 70). Added `_regime_is_structural`, so shape
     candidates only compete across regimes when no structural form was established.
  3. An SEC form label in running prose ("...the risk factor section of our Form 10-K" on the
     MSFT earnings call) was read as this document's own cover label -> transcript routed to
     `annual`. `labelled_units` now requires title evidence or real SEC item structure. This
     also fixed the pre-existing synthetic negative
     `test_sec_10k_mentioned_only_in_a_cross_reference_is_not_a_10k`.
  4. A `《募集资金管理办法》` heading *cited inside* a prospectus was read as that prospectus's
     own administrative purpose -> a 429-page IPO prospectus routed to `administrative`.
     The title channel (`observation.title`) and the in-body heading channel are now separate:
     an in-body bracketed title is always a citation, while the real 鼎龙 confirmation title
     `关于《…招股说明书》的确认意见` still self-identifies via `allow_self_purpose`.
- Final real-original result: **7/7 OBSERVED, 7/7 family agreement, 0 headline regressions.**
  Both headline defects verified fixed on the real originals:
  a) 鼎龙 confirmation letter -> `administrative` / `administrative_candidate` (legacy title
     router says `prospectus`; the original really has 0 native text characters, 1 opaque page);
  b) 恒锋 发行A股股票募集说明书 -> `offering` / `cn_exchange` / `equity_offering` (legacy title
     router says `unknown`).
- Honest limits: every real document is `confidence=low` because `ROUTE_PROBE_LIMIT` fires
  (3 000–4 000 units vs the 200-unit/64 000-char probe budget). No OCR was run, so the Miniso
  opaque page 246 and scan-only routing are **not** proven. Only the *family* decision is
  checked here; section/semantic/summary recall is out of this lane's scope.
- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q` -> **150 passed**
  (4.34 s wall). Ruff over the three owned trees -> **All checks passed** (0.15 s).
- Originals re-verified after all parsing: SHA-256, mtime and byte size all unchanged for all
  7 files (`c-evidence/originals-{pre,post}-snapshot.json`).
- Next: handoff + commit.

## 2026-10-13 C — recorded-shape recheck (complementary to the real-original pass above)

- Added `.planning/du-profiles/_cnode_probe.py`, which routes the plan's own *recorded*
  bounded observations (titles, TOC lines, heading lines, short excerpts) for all 20
  samples and prints an agreement table against the manifest's expected families. This
  complements `_cnode_real_probe.py`: that one proves the decision on 7 genuine originals,
  this one exercises all 20 recorded shapes, including the ones whose originals are gone
  (the temp captures) or absent from this machine.
- First run: **15/20**. Five further genuine router bugs surfaced that neither the
  synthetic fixtures nor the 7 real originals could reach. All five were fixed in the
  router, never by relaxing an expectation:
  1. a bare ``声明`` section (mandatory front matter of every A-share report, and
     ``发行人声明``/``特别提示`` in offering documents) was read as an administrative
     purpose -> removed from the administrative vocabulary;
  2. ``annual report`` as a plain English phrase fired the HK annual signal on a US filing
     -> HK signals now require HK vocabulary or a bilingual heading;
  3. Traditional ``中期報告`` was missed because NFKC does not fold Traditional to
     Simplified, so a real HK interim report routed to the annual family -> both spellings
     are now listed explicitly;
  4. bare form names in prose were trusted, so a 10-Q's own "our annual report on Form
     10-K" sentence reclassified it as a 10-K -> a form name only counts from a printed
     form label or cover line, never from a pointer to another filing;
  5. an offering whose only offering evidence was a later fundraising unit (front matter
     only in the probed window) fell into the periodic family -> fundraising structure now
     identifies an offering, while a real periodic report that names itself keeps its family.
- Added `test_c_real_shape_regressions.py`: 12 regression locks, one per defect, each naming
  the real sample that exposed it.
- Final recorded-shape agreement: **19/20**. The one remaining row is the honest outcome
  rather than a failure: ``cn-ipo-confirmation`` has one opaque page and zero readable
  characters, and the confirmation wording lives only in the *filename* -- which the router
  is forbidden to read. With a real title supplied, the same document routes to
  ``administrative`` / ``administrative_candidate``; with no readable evidence at all it
  returns ``generic_read``. Both are safe; neither guesses.
- Also verified refusal to over-fit: ``cn-ir-policy`` is recorded in the manifest as
  ``ir_policy`` but its observed body is an ``投资者关系活动记录表``, so the body wins and the
  declared-kind disagreement is reported as ``DECLARED_KIND_CONFLICT``.

## 2026-10-13 final verification

- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q` -> **150 passed**
- `python -X utf8 -m ruff check src tests/unit` -> **All checks passed** (the exact scope CI uses)
- `python -X utf8 -m compileall -q src` -> exit 0
- `python -X utf8 .planning/du-profiles/_acceptance.py` -> **ALL ACCEPTANCE CRITERIA
  SATISFIED**: the three frozen functions are callable; the confirmation letter is never a
  prospectus; ``发行A股股票`` is recognized; SEC and HK vocabularies do not cross-apply;
  unknown stays readable; reasons carry codes and unit ids; and no company name or file path
  appears anywhere in executable logic (company names occur only in docstrings recording
  which real sample motivated a rule).
- Next: handoff + commit.

## Coordination note for ROOT

- Two writers touched this worktree during the session: the recorded-shape recheck above and
  the real-original probe were developed concurrently, and parts of `signals.py` /
  `decision.py` were reformatted by the other writer while this session was editing them.
  The final tree was re-verified after the last external write: 150 tests pass, ruff over
  `src tests/unit` is clean, and the acceptance script passes. The delivered state is
  coherent, but ROOT should know the tree had two concurrent writers -- treat
  `git diff --name-only <base>...HEAD` as the authority on what shipped.
