# CI cache-precheck fixture root fix

Status: **IMPLEMENTED / LOCAL GREEN / AWAITING ROOT REVIEW AND PUBLICATION**. Author for this task: `/root/c3_cache_independent_review`; this is not a self-issued independent approval. No commit or push was made.

## Reproduction and root cause

CI run `40402565591` reported four `AttributeError` failures, all in `tests/unit/test_shared_reading_cache_precheck.py`. The exact local file reproduced **24 passed, 4 failed** in 10.57s. Every failing stack stopped at `_final_documents -> artifacts.read_exact`, because these older unit tests passed a bare `object()` instead of a publication reader. The changed-original negative case also provided only an artifact id and size instead of a complete publication pin.

The completed-cache change now correctly verifies the publication's frozen generation and hash before accepting reused output. The real production reader supports this operation. These four old doubles did not model that existing owner contract, so the tested source-read behavior was never reached. No product defect or need to weaken publication proof was found. The unrelated Actions runtime/summary annotations are not fixed or signed off by this narrow task.

## Systematic fixture repair

Only the authorized unit-test file was changed. A shared `published_reuse` fixture now creates an isolated real `CatalogStore`, seeds the source/document metadata, writes a real synthetic bundle through `NarrativeArtifactStore.prepare/activate`, and opens a real read-only `NarrativeArtifactReader`. The pin is generated from the actual published version. Published metadata contains the final frozen generation, generation SHA and base generation SHA; content SHA and byte count come from actual immutable bytes.

Both affected tests consume this same complete owner fixture. No `read_exact` or `_validate_published_generation` stub/lambda was added. Their original `read_reuse_pin` test boundary still observes 0/1 source reads and simulates a failed source read as before. New reads therefore exercise real publication bytes/metadata without adding a live original corpus or model.

All **26 existing assert statements across 15 original test functions are AST-identical**. Original parameter coverage, output/pin equality, zero duplicate owner reads, durable-binding omission and changed-original rejection remain intact. The common fixture replaces duplicated partial setup. One additional test corrupts the persisted publication generation hash while setting `verified_reuse_keys`; it verifies the batch rejects the publication before another source read. This protects the boundary from future “make the test pass” bypasses.

## Evidence

- RED: `red.log/xml`, **4 failed / 24 passed**, 10.57s, exact expected `object has no attribute read_exact` failures.
- GREEN: complete repaired file (**29 cases**) plus complete `test_narrative_batch_recovery.py` (**30 cases**): **59 passed**, 7.71s, process exit 0. `green.log/xml`.
- Ruff: `ruff.log`, PASS.
- Assertion preservation and final hashes: `static.json`.
- Test interpreter: `C:/Miniconda/python.exe`, own short TEMP, plugin autoload disabled, hermetic repository fixtures, no bytecode. The one `asyncio_mode` warning is from intentionally disabled plugin autoload and is irrelevant to these synchronous tests.
- Cleanup: `cleanup.json`; explicit `C:/Temp/c3precheck-20261026` boundary checked and removed, no scoped Python processes remain, zero real models/downloads/production writes.

Final unit-file raw/LF SHA-256: `0517a05bf03935e520cef380b4e81c94b883654915d9ec86b9497e2ce570802d`.

Product files remain at their previously reviewed hashes: narrative_batch LF `770d482454bce479c1b737272e5d115b0608f2d5b43de5b8acd654c87f2c1a39`; narrative_generation LF `64e9ddd7c63f5fa6b92abd3f15d8e2a8d430880fbdb70481604d763586edf1ff`. No semantic-owner changes were made.

## Why earlier local checks missed it / next step

The earlier narrow C3 validation covered the new recovery tests and selected production integrations, but omitted this existing unit consumer of `_final_documents`. Its incomplete reader double failed as soon as the product exercised the publication contract. The remedy is to retain this relevant consumer file in the focused cache-change verification selection, not run every unrelated test at each commit or remove product validation. The current scoped 59-case selection is under eight seconds locally.

ROOT should review the fixture/test-only diff, accept the bound SHA, then commit/push and inspect the exact resulting CI run. Local success here is not a claim that remote CI has already rerun green.
