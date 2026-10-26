# C3 completed-cache independent final review

Date: 2026-10-26. Reviewer: `/root/c3_cache_independent_review` (not either implementation author).

**PASS — C3-IR-01 CLOSED; OPEN = 0 within the reviewed three-file scope.** This final recheck supersedes the disposition in `review.md`, while preserving that original report and all RED evidence.

The fix is at the shared owner: `reading_candidate_manifest` checks the decoded JSON is a dictionary before calling `.get`, and rejects non-object values through its existing `ValueError(BATCH_REUSE_MANIFEST_INVALID)` contract. The batch helper then emits the existing `BatchResumeError(BATCH_FROZEN_BINDING_INVALID)`. No broad exception swallowing, validation bypass, new authorization gate, or additional current-SDK requirement was introduced.

Permanent tests cover five non-object JSON values (`[]`, `null`, `true`, `0`, string), each checking both owner rejection and batch normalization. The previous 25 recovery tests remain green. The reviewer's unchanged two original failing counterexamples now pass.

## Independent validation

Command scope: `tests/unit/test_narrative_batch_recovery.py` plus `test_review_counterexamples.py::test_base_selection_corrupt_metadata_is_controlled_rejection`.

- **32 passed**, zero failed/errors, pytest 2.30s; whole Python process 3.422s, exit 0.
- Interpreter: `C:/Miniconda/python.exe` 3.13.9, plugin autoload disabled, hermetic runtime, `-B`.
- Logs and JUnit: `final-tests.log`, `final-tests.xml`.
- One known `asyncio_mode` config warning is caused by disabled plugin autoload; no async tests were selected.
- No repeated heavy integration runs. The prior independently executed raw-corruption CLI proof remains applicable: selector-0.8 resume rejects `no_verified_location`, zero model calls. Author parser-upgrade/cross-run/paid-outbox receipts remain separately identified in the original report.

## Final binding

| File | Byte SHA-256 | LF SHA-256 |
| --- | --- | --- |
| `src/company_wiki/automation/narrative_batch.py` | `6f6db0abaeebb7d38c7f77402cd6943ec1beedfd290631ded29c492d446b9d9c` | `770d482454bce479c1b737272e5d115b0608f2d5b43de5b8acd654c87f2c1a39` |
| `src/company_wiki/automation/narrative_generation.py` | `720924613789251e0cc6433ba961fc710342969ebcbc276ea641f0a98edbea0c` | `64e9ddd7c63f5fa6b92abd3f15d8e2a8d430880fbdb70481604d763586edf1ff` |
| `tests/unit/test_narrative_batch_recovery.py` | `db8228d73d61b9d1bda5d77a5bb123724a8cb7e9db569d3e6f6d5b908ad77ced` | `97afb46df5004f5c401031477c10baab0328e54589db58237b8007c6aee97034` |

The two changed file hashes match `fix-c3-ir-01.json`. Batch source and original integration test hashes are unchanged from the first independent review. See `final-scope-cleanup.json` for machine-readable byte sizes and hashes.

## Cleanup and limits

The only new test directory, `C:/Temp/c3recheck-20261026`, was checked against its explicit absolute boundary and removed. No reviewer Python processes remain. Real supplier calls, downloads and production writes are all zero. Only review evidence was written by this reviewer. This acceptance covers the cache recovery engineering change, not a new live-provider/content-quality acceptance or unrelated worktree changes.
