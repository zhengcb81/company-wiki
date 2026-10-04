# N4-T2：Chinese report and IR narrative selection coverage

Status: READY TO DISPATCH
Card date: 2026-10-04
Owner: isolated harness; MAIN owns final real-data batch, provider calls, storage measurement, and shared PWF.

## Goal

Select concise, replayable evidence about industry developments, main-business progress, new businesses, products/projects, overseas expansion, and other concrete operating changes. Exclude routine financial tables, static definitions, contents pages, and boilerplate. A complete document with no business narrative may be skipped; an incomplete parse or uncertain coverage must never be mislabeled as a clean skip.

The previous real N4C attempt showed a genuine gap:

- A verified quarterly PDF (13 pages) produced 192 text blocks and 11,645 extracted characters. A full table scan completed with no parser errors or opaque pages, yet the selector returned zero candidates and zero spans; the job became PARSER_INCOMPLETE.
- A verified IR activity PDF (3 pages) produced 57 text blocks and about 2,350 extracted characters, with no parser errors or opaque pages, yet returned zero candidates and zero spans. Its normalized title is absent, so routing must continue to use the existing document_kind fallback.
- Both are known valuable source types, so current conservative behavior correctly refused to silently skip them. The task is to recover true narrative evidence and make fully scanned, genuinely non-narrative inputs skippable without hiding false negatives.

No raw company paragraph or complete source document is included in this card.

## Worktree and exclusive write set

Use a dedicated company-wiki worktree outside the MAIN checkout. If N4-T1 runs concurrently, use a different worktree. If the cards run sequentially, reuse N4-T1's dedicated directory after its tests finish and its changes are committed. Record N4-T1's delivered head as this card's base, and report only this card's base..head delta. Preserve N4-T1's committed implementation; do not reset it or include its paths as new N4-T2 changes. No extra approval is needed between cards.

Write only:

- src/company_wiki/source_catalog/narrative_candidates.py
- src/company_wiki/source_catalog/narrative_routing.py
- src/company_wiki/source_catalog/narrative_finalize.py
- src/company_wiki/source_catalog/narrative_evidence.py, only if the selector composition itself must change
- tests/unit/test_narrative_selection_architecture.py
- tests/unit/test_narrative_evidence.py
- tests/unit/test_narrative_select_handler.py
- a lane handoff report in this card's handoff section or a returned report; do not edit shared task_plan.md, progress.md, findings.md, configuration, or another lane's files.

Do not edit any file under src/company_wiki/automation, batch/AUTO scheduling, model transport, shared export contracts, provider configuration, raw sources, production catalog, or another repository.

## Required behavior

1. Preserve deterministic, source-only processing. Do not call an LLM, translate, or include financial statement data as a narrative claim.
2. Add synthetic Chinese RED/GREEN cases for each target category: industry dynamics, operating progress, a new business/product/project, and overseas expansion. Require source locator and replay verification for each selected span.
3. Add boilerplate, static background, table-of-contents, and ordinary financial-table controls that remain unselected.
4. For investor_relations and quarterly_report, select concrete narrative when present even if title is missing and the known document_kind is the only routing hint.
5. A document may receive skipped_no_narrative only after complete parser coverage and a deterministic result that no eligible narrative remains. If parsing is incomplete, the result must remain review/incomplete and the worker must not treat it as a successful skip.
6. When the selector finds valuable text but cannot produce a replayable locator, preserve the existing failure behavior. Do not weaken SHA, source identity, locator replay, or coverage checks.
7. Keep selected output bounded by the existing selector budget. Do not increase the default document limit just to make tests pass.

## Real-source diagnostic interface

The MAIN workspace currently has verified SourceRefs for the quarterly, IR, annual, and restored prospectus samples. If the harness performs a real-source check, use only the official SourceCatalog + SourceVersionReader.open_version path with purpose=narrative_derivation and the expected current read-policy hash. Verify the opened SHA and byte count in memory. Do not open a physical path directly, copy source bytes into the worktree, persist parsed text, or print raw text.

Only aggregate values may appear in the report: source hash prefix, document kind, page/unit counts, character counts, candidate/selected counts, parser errors/opaque pages, coverage state, span replay count, and bytes added by the test. The selector implementation tests must remain synthetic and run offline. MAIN will repeat the authoritative production-read verification after merge.

## Tests and finish

Run the focused tests:

~~~powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -p no:cacheprovider --basetemp tmp/n4t2-test tests/unit/test_narrative_selection_architecture.py tests/unit/test_narrative_evidence.py tests/unit/test_narrative_select_handler.py
~~~

Also run Ruff on only the changed Python files and git diff --check. Keep the test root inside this worktree, verify it was not relocated, and remove only that exact generated root after the test exits. No network or paid model request.

Commit and push the lane branch; do not merge to main. Return base/head SHA, exact changed paths, RED/GREEN commands and durations, candidate/skip semantics, replay proof, confirmation no text/source copy or provider call was made, and remaining limitations. MAIN owns cross-layer worker/E2E verification and the final document/storage measurements.

## MAIN integration boundary

After both N4-T1 and N4-T2 are delivered, MAIN integrates the disjoint code paths and runs a single bounded real-source batch under the existing remaining aggregate budget. MAIN retains ownership of the main PWF and the production N4C run records.
