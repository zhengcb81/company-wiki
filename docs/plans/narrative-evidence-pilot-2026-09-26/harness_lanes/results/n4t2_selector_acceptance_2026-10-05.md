# N4-T2 MAIN selector implementation and acceptance

Status: MAIN IMPLEMENTATION PUSHED; CI SUCCESS; EXTERNAL HARNESS RECONCILIATION PENDING

## Code and tests

- Base: `4807c019e0e33a00b08934eee57c3510ca9b0372`.
- Commit: `ea9dd266fd659852c04b6e0a33882f86a47f037a`, fast-forwarded to local `master` and pushed. A post-push read-only `git ls-remote` confirmed `origin/master` at the same SHA.
- Changed paths: narrative candidate rules, PDF candidate composition, selection finalization, routing, and the two selector unit-test files. No automation/model transport, provider configuration, raw document, production catalog, or RF files changed.
- TDD evidence: a new route test first failed on all six business-bearing document types because a complete scan with zero recognized candidates would auto-skip. Routing was narrowed to administrative IR policy/meeting-notice cases; fully classified finance-only documents can still skip after complete coverage.
- Focused MAIN regression: **104 passed / 2.33s**, with one existing `asyncio_mode` warning because optional pytest plugin autoload was disabled. Ruff passed, `git diff --check` passed. The same 104 tests passed in the isolated worktree before merge. Pre-commit Ruff, mypy contract modules, and host-assumption guard passed.
- An initial test invocation had 2 setup errors because the dedicated basetemp parent directory did not exist; after creating the parent, the full focused set passed. Both temporary test roots were removed after verifying their exact absolute paths.

## Real source verification

- Used `SourceCatalog` and `SourceVersionReader.open_version` with `purpose="narrative_derivation"` and the current read-policy SHA pin. Checked exact source SHA and byte size in memory, then parsed/selected/replayed in memory. No raw text was printed or persisted, no bytes were copied, and no model/provider request or production write occurred.
- IR activity PDF, SHA prefix `3e25aab404a1`, 133,294 bytes: full scan, 67 units, complete coverage; metadata title absent and routing used `investor_relations` kind fallback. Selector returned 2 candidates / 2 spans / 4,813 selected-text bytes; both locators replayed successfully.
- Quarterly PDF, SHA prefix `37f0eb13fc97`, 309,955 bytes: full scan, 192 units, complete coverage, zero candidates. Result stays `needs_review`; it is not silently skipped because unrecognized business narrative may remain.
- Selected bytes are excerpts from the verified source and were held only in memory for locator checks; no raw excerpt appears in this report.

## CI and external harness coordination

- GitHub Actions run [37268779206](https://github.com/zhengcb81/company-wiki/actions/runs/37268779206) completed successfully for the exact commit above (about 82 seconds).
- The user reports the previously dispatched external N4-T2 harness is still running. This implementation was already pushed before that update arrived. The external worktree was not inspected or changed; its code/test write set overlaps this commit. Do not merge the duplicate delivery blindly. Once its handoff is available, compare its base..head diff with `ea9dd26` and retain only distinct, valuable improvements. Keep the task card open until this reconciliation is recorded.
- The main checkout still contains the pre-existing user modification to `config/source_acquisition.yaml`; it was not staged or changed.

## Next major node

After external-card reconciliation, execute the planned bounded N4C real Worker batch with P4 as a candidate profile. Validate selected summaries, verified spans, language/citations, the public CWP read path and RF N3a consumer, actual incremental output/scratch/database space, and remaining model budget. Keep legacy derived files until the RF default SourceBundle/readers have migrated and the separate S5/S6 deletion nodes pass.