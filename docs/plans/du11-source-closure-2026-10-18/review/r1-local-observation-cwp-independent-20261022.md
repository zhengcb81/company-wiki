# CWP local preparation: independent engineering review

**PASS — bounded local preparation observation only.** Product `27be00fb5b16503b867886ea8cbc641027d6a8e2`; reviewer `/root/r1_w02_source_boundary` did not author the product. The author tree was clean and all six frozen source/regression file fingerprints stayed unchanged during the final run.

## Result and resolved root cause

| Version | Independent new cases | Existing/author related cases | Combined result | Time |
|---|---:|---:|---:|---:|
| Original `96ca254d` | 5P / 1F | 43P | 48P / 1F / 0S | 18.23s |
| Final `27be00fb` | 6P | 43P | **49P / 0F / 0S** | **18.43s** |

**CWP-OBS-1 resolved:** actual latest discovery first wrote a valid source assertion (`recorded`), then another original correctly failed with `fiscal_period_unresolved`. The original envelope retained its real budget operation but omitted that already completed owner write. This was real native catalog/owner execution; the reviewer only observed the real owner return, with no injected progress or SQL alteration.

ROOT fixed the common path with `_PreparationProgress.record_operation`: candidate and discovery both sanitize `source_ref`/`verified_locations` and append actual completed results to the same call-owned progress object. `not_relevant` remains only a call-local original-proved exclusion. No extra verification, permission, persistent negative cache, quota or source-reader changes. The same fixed independent counterexample is GREEN. ROOT also transferred the native sequence into a permanent product regression using current UTC, avoiding a future-dated fixture artifact. That additional author test is not counted twice in the49.

## What was independently checked

- Completed discovery writes survive a later semantic refusal; exactly one owner budget operation remains.
- A real metadata read followed by cancellation reports observed bytes but no accepted charged bytes, without guessing a byte cap or network fee.
- Actual non-relevance is call-local and re-proved in another call; bad metadata on a later requested scope remains blocking.
- Misleading old filenames plus conflicting actual issuer or unknown scope cannot inherit another document's exclusion.
- Latest does not return an old cached match while ignoring a newly discovered current target with unresolved period.
- Original22 relevance assertions, author9 budget, original7 boundary and existing5 latest tests remain GREEN. The selection uses the original four boundary nodes to keep the fixed43 related count.

Patch review confirmed only the shared operation recording change in the supplemental runtime diff. The native existing source owner remains responsible for identity/scope/SHA; call-local exclusion never comes from a filename or declared year. Existing failure behavior, caps, query contract and raw preservation remain. Two independently written review files pass Ruff (exit0). ROOT-reported44/full-src mypy/hooks results are author evidence, not additional independent tests.

## Frozen runtime bytes

| File | Physical/LF SHA-256 |
|---|---|
| `src/company_wiki/source_catalog/local_inventory.py` | `11d2dd529216d17d982c673b490754b8b199123ae43302047527282c9f8c4550` |
| `src/company_wiki/source_catalog/local_reconcile.py` | `0a6b5cc2972791380b24ec306f53f0535473bf9b3961c7ea2cc9c8f9591a4126` |

Full six-file physical/LF/Git-blob maps and before/after receipts are in `source-before-final.json` and `source-after-final.json`. Original RED evidence is separately frozen in `initial.log/xml` and `initial-discovery-before-later-failure.json`; final proof is `final-discovery-before-later-failure.json`.

## Reproduction

Worktree: `C:/Users/郑曾波/Projects/company-wiki-r1-local-observation`. Evidence is the same-named sibling directory of this report. Use an initially absent, reviewer-owned TEMP; do not target production. Review conftest disables dotenv, removes key variable names without reading values, and rejects socket connects. The archived independent fixture intentionally binds information date2026-10-22 and actual current owner proof; future-day replay must preserve that information clock, or use the transferred permanent current-UTC native regression.

```powershell
$env:PYTHONPATH='<worktree>;<worktree>/src;<worktree>/scripts;<worktree>/tests'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHON_DOTENV_DISABLED='1'
python -B -X utf8 -m pytest -c <evidence>/pytest.ini <evidence>/test_cwp_independent.py tests/contract/test_local_request_relevance.py tests/unit/test_local_budget_observation.py tests/contract/test_local_prepare_failure_boundaries.py::test_discovered_unrelated_original_ignores_its_unusable_date tests/contract/test_local_prepare_failure_boundaries.py::test_discovered_target_or_unknown_never_becomes_absence tests/contract/test_local_prepare_failure_boundaries.py::test_actual_nonrelevance_is_not_reproved_in_same_call tests/contract/test_local_prepare_failure_boundaries.py::test_wrong_declared_old_year_does_not_exclude_actual_requested_original tests/unit/test_latest_local_source_discovery.py --basetemp=<owned fresh TEMP> --junitxml=<evidence>/final.xml -v --tb=short
```

## Isolation, cleanup and limits

0 external API, 0 downloads, 0 paid requests; no credential values, production configuration/raw/database, author code/index or installed skill writes. Native fixture originals are byte-checked. Both fresh owned TEMP roots were removed after exact absolute-parent/reparse-root checks: initial `.planning/cwporv`354 files/19,444,599B; final `.planning/cwporvf`354 files/19,444,649B; both restored to their initial absent state. Each independent catalog fixture also closes its catalog, removes its own working root and verifies a pre-existing sentinel unchanged. `cleanup.json` is the receipt.

CodeGraph was not initialized in the read-only author worktree; no index was built. A guessed old test filename did not exist; the actual unchanged22 module was selected before execution, with no missing path counted as test evidence.

This report accepts **engineering local source preparation/observation**, not real providers, live paid generation, installed copies, model content quality or RF formula consumption. ROOT's separate actual CWP→FF→RF offline CLI test checks cross-layer budget transport, and is not substituted for this real discovery-history test. ROOT owns merge/push/install and overall PWF status.
