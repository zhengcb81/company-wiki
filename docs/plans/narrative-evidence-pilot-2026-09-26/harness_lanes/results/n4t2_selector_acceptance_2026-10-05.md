# N4-T2 MAIN selector implementation and acceptance

Status: EXTERNAL DELIVERY REVIEWED; DISTINCT IMPROVEMENTS SELECTIVELY INTEGRATED; N4-T2 ACCEPTED

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

## CI and external harness reconciliation

- GitHub Actions run [37268779206](https://github.com/zhengcb81/company-wiki/actions/runs/37268779206) completed successfully for the exact commit above (about 82 seconds).
- External delivery branch `codex/n4t2-selective-narrative-coverage` ended clean at `2b5bec91466e13deeb92feb5ac369ecb222563f0`, based on N4-T1 `4a53080`. Its six-file N4-T2 commit overlaps the MAIN selector write set; it is not a fast-forward of `ea9dd26`. The branch's focused tests passed **82/82**, Ruff passed, and `git diff --check` was clean. No formal N4-T2 handoff/acceptance report was present in its planning results; the code commit and reproducible test results were used as delivery evidence. The external worktree was read-only during acceptance and remains untouched.
- Selectively retained the useful vocabulary and event additions: industry prosperity, production/throughput/capacity utilization, overseas business/revenue/bases, and explicit formation/start of a new business unit, product, institute, or R&D project. MAIN keeps its concrete-action-plus-recency eligibility requirement. The external branch's removal of that action condition and its proposed automatic skip for signal-free business/quarterly documents were rejected: the real quarterly sample has complete parser coverage but zero recognized terms, which cannot establish that it has no valuable narrative.
- Added synthetic titleless quarterly/IR PDFs covering industry conditions, operating progress, new business/project, and overseas expansion. Tests exclude boilerplate and table-of-contents text and replay every selected locator against exact PDF bytes. A titleless, signal-free quarterly remains `needs_review`.
- After selective integration, the focused MAIN suite passed **107 tests / 1.50s**; Ruff passed. With optional pytest plugin autoload disabled (the normal environment's `langsmith` import hits a `pydantic_core` DLL access error), pytest emitted only the existing `asyncio_mode` unknown-option warning. The isolated basetemp was removed and verified absent.
- The selective improvement was committed as `0657579d43dc51f327991a0e41aee552e18eb483` and pushed to `origin/master`. The configured fast pre-push contract set passed. GitHub Actions run [37273071081](https://github.com/zhengcb81/company-wiki/actions/runs/37273071081) matches the exact head SHA and completed successfully.
- The main checkout still contains the pre-existing user modification to `config/source_acquisition.yaml`; it was not staged or changed.

## Post-integration real Worker replay and next node

- Re-ran the isolated E6 real-data Worker test after the selector vocabulary update: **1 passed / 246.39s**. It handled annual report, prospectus, IR activity, transcript TXT, and a positive skip sample at P1/P2/P4; all three profiles had 5 visible artifacts, 4 model calls, 20,597,846 raw bytes, 445,842 narrative artifact bytes (2.16%), 1,441 skip bytes, zero retries, zero SQLite busy errors, and zero WAL bytes. Source SHA/locator replay, model-call ceiling, budget assertions, production/source/config fingerprints, and temporary-root restoration passed; both test roots were absent afterward.
- Profile measurements: P1 93.006s, 154.8 documents/hour, queue-wait p95 76.177s, handler p95 41.639s, peak process-tree RSS 373,583,872 B; P2 89.453s, 161.0 documents/hour, queue-wait p95 73.355s, handler p95 40.521s, RSS 459,042,816 B; P4 62.527s, 230.3 documents/hour, queue-wait p95 41.893s, handler p95 38.773s, RSS 686,489,600 B. The run is slower than the earlier E6 record (P2 34.384s, P4 29.091s); it therefore supports P4 only as a bounded candidate, not an unrestricted default. Queue wait and process-tree RSS remain explicit N4C capacity signals.
- N4-T2 external delta is reconciled, selectively integrated, published, and CI-accepted; no whole-branch merge is needed. Next, diagnose the changed E6 latency enough to set a conservative P4 cap, then run the planned N4C consumer-integrated batch: verify selected summaries, verified spans, language/citations, the public CWP read path and RF N3a consumer, total incremental output/scratch/database space, and remaining model budget. Keep legacy derived files until RF's default SourceBundle/readers migrate and separate S5/S6 deletion nodes pass.
