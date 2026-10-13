# DU-PROFILES task plan

PLAN_ID: du-profiles
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/profiles/.planning

## Base state (recorded before any write)

- repo: company-wiki worktree `C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/profiles`
- branch: `codex/du-profiles-20261013`
- base/HEAD: `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`
- `git status --short` at base: empty (clean)
- card: `docs/plans/document-understanding-2026-10-13/cards/DU-PROFILES.md`
- upstream plan: README/design/INTERFACES/implementation in `docs/plans/document-understanding-2026-10-13/`

## Objective

Deliver a composable, pure-function document-type routing package under
`src/company_wiki/document_understanding/profiles/` exposing the frozen wire:

```python
route_document(observation, *, limits=None) -> dict   # du-route/1
get_profile(profile_id) -> dict
list_profiles() -> list[dict]
```

No production wiring, no parent `__init__.py`, no writes outside owned paths.

## Owned paths (only these may be written)

- `src/company_wiki/document_understanding/profiles/**`
- `tests/unit/document_understanding_profiles/**`
- `tests/fixtures/document_understanding_profiles/**`
- `.planning/du-profiles/**`

## Steps

1. Record base SHA/status (done). Freeze `du-input/1` synthetic inputs plus expected
   routes for: annual, annual summary, director report (述职), IPO confirmation letter,
   `发行A股股票募集说明书`, SEC 10-K/10-Q/20-F, HK bilingual, IR policy/QA, untitled TXT,
   unknown, metadata-vs-body conflict. Write them RED first.
2. Type identification from disclosure metadata + cover/TOC/layered body signals;
   administrative misclassification handled first. Layered probing (cover / structural
   headings / document-span stratification), not blind first-N-chars. Record probed vs
   unknown.
3. Implement the three frozen public functions with a static profile registry and
   composition. Shared business/risk focus reused; per-type differences confined to
   section aliases / priorities / semantic units / summary focus. Not one full-text
   parser per type, not one skill per type.
4. Support recognizable sub-document ranges inside an already-supplied container;
   external links marked unread, never downloaded or invented. Revision/summary/
   confirmation distinguished by subtype, never by path-based country or security guess.
5. Negative cases: same-named sections, 10-K/prospectus mentioned only in cross
   references, missing/scan-only body, low-confidence generic_read. Low-value returns
   `administrative_candidate` only; the final skip decision stays with ROOT.
6. Use this plan's manifest/observations for real-adaptation observations (titles and
   bounded excerpts only, never copies of the PDFs, never company names or fixed page
   numbers as rules). Test English, Traditional Chinese, and missing titles.

## A/B/C nodes

- A: interface and counter-example RED plus profile matrix; no human permission needed.
- B: all package unit and boundary tests pass; immutable input, determinism, probe budget
  limits, contradictory metadata diagnostics.
- C: re-check with different companies/title variants, record real support vs missing
  samples; path-scope check and handoff. No per-helper review.

## Commands

- `python -X utf8 -m pytest tests/unit/document_understanding_profiles -q`
- `python -X utf8 -m ruff check src/company_wiki/document_understanding/profiles tests/unit/document_understanding_profiles`
- no network, no paid calls, no full suite, no CI additions

## Acceptance

- all frozen wire callable directly by ROOT
- confirmation letter never routed as a full IPO prospectus
- A-share "发行A股股票" wording recognized
- SEC and HK forms never cross-applied
- unknown remains readable (generic_read)
- every claim traceable to an input signal
- must NOT pass by raising max_probe, editing the sample oracle, or forcing unknown to annual
