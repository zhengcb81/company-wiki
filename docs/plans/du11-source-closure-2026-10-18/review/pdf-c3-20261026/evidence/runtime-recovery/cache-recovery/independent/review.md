# C3 completed-cache independent review — 2026-10-26

Reviewer: `/root/c3_cache_independent_review` (not implementation author).

Disposition: **CHANGES_REQUESTED — one P2 OPEN**, confined to malformed publication metadata handling. The core historical-read / execution-admission split is sound in the reviewed diff. No product files, existing assertions, index, or production data were changed by this reviewer.

## Frozen scope

Worktree HEAD at review: `65f42d418b1328784aecc1a3460aea535eedb3a8`; target changes are uncommitted. Exact raw and LF hashes, sizes, and cleanup receipt are in `scope-cleanup.json`. These hashes match the author handoff.

| File | LF SHA-256 |
| --- | --- |
| `src/company_wiki/automation/narrative_batch.py` | `770d482454bce479c1b737272e5d115b0608f2d5b43de5b8acd654c87f2c1a39` |
| `src/company_wiki/automation/narrative_generation.py` | `caf25bdd7d8903c975341feb07a07452768e7896f30a9a95ba0bd81a200fd2e4` |
| `tests/unit/test_narrative_batch_recovery.py` | `76aa67b4bf64f9d3504f2541b32be99493986e4e1f67eb95c564c692e22d5f34` |

The original integration test remains unchanged, SHA `b8ddb010e8943767a35f798e2be37eada23abd50235f49eda946c5e31908035a`.

## OPEN: C3-IR-01 / P2

`narrative_batch.py:468` resolves a selector-0.9 base manifest through `reading_candidate_manifest` before its own metadata shape check. `narrative_generation.py:534` immediately calls `.get` on JSON-decoded metadata. Valid JSON `[]` or `null` therefore raises `AttributeError`, outside the new helper's `TypeError/ValueError` normalization.

Two independent probes reproduce this. The normal malformed-metadata tests all pass because their manifests omit selector-0.9 and do not enter this branch. The public CLI catches this generically as `NARRATIVE_BATCH_AttributeError` / exit 1, instead of the intended frozen-binding validation diagnostic / exit 2. The record is rejected, so this is not an acceptance bypass or permission issue; it is an avoidable recovery/error-contract hole.

Recommended common-owner fix: validate decoded metadata is a dictionary in `reading_candidate_manifest` before accessing fields, raising `ValueError("BATCH_REUSE_MANIFEST_INVALID")`; `_validate_published_generation` can then consistently translate it. Add these two selector-0.9 cases to permanent tests. Avoid merely adding broad exception swallowing in CLI.

Reproduction: `test_review_counterexamples.py::test_base_selection_corrupt_metadata_is_controlled_rejection`, results in `counterexamples.log/xml` and `review-tests.log/xml`.

## What was verified

- A supplied frozen PDF/normalization recipe supplies parser identity directly; `generation_manifest` no longer instantiates today's reader before honoring that recipe. Both request schemas pass the forbidden-current-reader unit check.
- Request identity, source membership, generation hash, policy lineage, job membership and event binding remain decoded and compared. Completed publication validation compares the whole frozen manifest and hash, including runtime/reader implementation/paragraph enhancement.
- Removing `parser_components` from a modern binding does not make it legacy: its publication still contains the modern manifest, so exact comparison rejects it. Genuine pre-generation records retain the existing narrow no-manifest/no-recipe compatibility path.
- A valid selector-0.9 base generation resolves to the published final selection through the existing owner. Base fields and recipe remain exact, and the selection generation is validated.
- Only a completed/idle read that actually returns bypasses current execution admission. Pending jobs, activation pending and paid-recovery continuations still encounter `_validate_normalization_binding` and executable-version availability before worker/gate writes.
- Reused pins still open exact content and public source evidence. The existing source-read owner remains responsible for original bytes and locators.
- A separate concern about selector-0.8 completed reads was **disproved** with a real isolated CLI counterexample: complete a synthetic policy PDF batch, corrupt its original bytes, then resume. Result: exit 2, `no_verified_location`, no returned artifact, zero model requests/tokens/cost. This is not an OPEN finding.

## Independent execution

All execution used `C:/Miniconda/python.exe` 3.13.9, plugin autoload disabled, `-B`, own TEMP and the repository hermetic fixture. No live LLM, downloads, real source corpus, or global deployment.

| Evidence | Result | Meaning |
| --- | --- | --- |
| `review-tests.log/xml` | author's 25 tests PASS; two independent metadata probes FAIL; one probe fixture setup ERROR | 25 tests were independently rerun, not inferred from handoff. The setup error is reviewer fixture wiring, not product. |
| `counterexamples.log/xml` | both metadata probes FAIL; raw probe stops at reviewer fixture-count assertion | first raw probe incorrectly counted its `.source.json` sidecar; corrected only reviewer fixture selection. |
| `raw-final.log/xml` | 1 PASS, 13.08s | completed original corruption is rejected |
| `raw-reason.log/xml` | 1 PASS, 9.53s | repeats once to retain the actual `no_verified_location` reason; ensures an unrelated failure was not counted as integrity protection |

The short author suite plus independent counterexamples were sufficient for this review; the author's parser-upgrade, paid-outbox and PDF cross-run receipts were inspected rather than broadly rerun. These are offline engineering results, not a new real-provider/content-quality acceptance.

## Cleanup / next step

`owned-test-temp` and `C:/Temp/c3review-20261026` were boundary-checked then removed; no matching reviewer Python processes remained. Synthetic fixture contexts restored their baseline. Protected production configuration/catalog snapshots passed. Evidence and reviewer probe source are intentionally retained under this independent directory. See `scope-cleanup.json`.

ROOT/author should repair C3-IR-01, rerun its two short cases plus the existing recovery suite, and bind a final independent follow-up to the resulting source SHA. No need to rerun every expensive integration package for this shape guard alone.
