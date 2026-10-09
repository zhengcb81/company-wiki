# Historical CI focused reproduction

Two exact historical filing-fetch trees were archived to uniquely owned temporary directories. Original working trees/config were not modified. No network, download, package install or paid operation was used.

Local runtime: Python 3.13.9; pytest 9.1.1. CI configured Python 3.12. Only dependency-free AST complexity tests ran.

Initial OS temporary extraction failed with PermissionError before pytest execution. The successful attempt used exact file-byte extraction into owned workspace temp without tar mode attributes.

## 3945efb42272f78daf7baa9cf44685137c462e87

- Command: `python -m pytest tests/test_complexity_ratchet.py -q --tb=short -p no:cacheprovider`
- Exact test bytes matched git blob: yes; SHA-256 `eaa12d90ec42b79efe7e45cf1800a654667a92413a408766c95ca2ed44e29398`.
- Exit: 1; wall time: 0.605 seconds.
- Owned archive root removed: True.

```text
.F                                                                       [100%]
================================== FAILURES ===================================
_________________________ test_new_files_stay_simple __________________________
tests\test_complexity_ratchet.py:65: in test_new_files_stay_simple
    assert actual <= NEW_FILE_MAX, f"{rel} max {actual} > {NEW_FILE_MAX}"
E   AssertionError: transcript_tool_transport.py max 15 > 10
E   assert 15 <= 10
=========================== short test summary info ===========================
FAILED tests/test_complexity_ratchet.py::test_new_files_stay_simple - Asserti...
1 failed, 1 passed in 0.18s
```

All metrics exceeding this historical gate:

- `transcript_tool_transport.py`: 15 > 10; worst function `_provider_usage` at line 45.

## afbef6536d3ee66615beb99a465d3a2a1f648313

- Command: `python -m pytest tests/test_complexity_ratchet.py -q --tb=short -p no:cacheprovider`
- Exact test bytes matched git blob: yes; SHA-256 `eaa12d90ec42b79efe7e45cf1800a654667a92413a408766c95ca2ed44e29398`.
- Exit: 1; wall time: 0.554 seconds.
- Owned archive root removed: True.

```text
.F                                                                       [100%]
================================== FAILURES ===================================
_________________________ test_new_files_stay_simple __________________________
tests\test_complexity_ratchet.py:65: in test_new_files_stay_simple
    assert actual <= NEW_FILE_MAX, f"{rel} max {actual} > {NEW_FILE_MAX}"
E   AssertionError: ff_provider_cause.py max 14 > 10
E   assert 14 <= 10
=========================== short test summary info ===========================
FAILED tests/test_complexity_ratchet.py::test_new_files_stay_simple - Asserti...
1 failed, 1 passed in 0.17s
```

All metrics exceeding this historical gate:

- `ff_provider_cause.py`: 14 > 10; worst function `_valid_acquisition_usage` at line 184.

## Interpretation and limits

Historical complexity ratchet assertion failures reproduced from exact archived blobs; public CI evidence confirms the matching focused suite failed but its complete log was unavailable.

Focused complexity tests only; no full historical regression suite. Local Python 3.13.9 differs from CI Python 3.12. Assertions use repository-local AST metrics and require no external runtime or data.

Saved public job records: run 37832787908 at 3945efb and run 37861936346 at afbef65 both failed in Run focused regression suite once (42 seconds each). Their preceding Ruff/import smoke, strict type and unique-symbol steps succeeded. Public annotations give exit 1 but no full test failure log. This reproduction establishes at least one deterministic failure at each SHA without claiming these were the only CI failures.

The e9b0d08 replacement removes test_complexity_ratchet.py from CI, replacing it with test_complexity_diagnostics.py and a nonblocking diagnostic. Historical failure does not imply the current tree still fails the deleted gate.

## Normal OS repeat

Both exact historical tests were repeated through require_escalated normal OS execution, as authorized. Results matched the workspace-temp reproduction; all owned OS temp roots were removed. The initial failed sandbox temp target no longer existed when checked from the normal OS, so no additional deletion was necessary.

- `3945efb42272f78daf7baa9cf44685137c462e87`: exit 1, wall time 0.567 seconds; owned temp removed True.
- `afbef6536d3ee66615beb99a465d3a2a1f648313`: exit 1, wall time 0.608 seconds; owned temp removed True.

The earliest failure is `_provider_usage` at transcript_tool_transport.py:45 (score 15). The later failure is `_valid_acquisition_usage` at ff_provider_cause.py:184 (score 14); `_acquisition_evidence` at :204 also scores 11. These are distinct functions and regressions.

## First failure correction control

The directly subsequent 697af966 commit extracts `_usage_counters` from `_provider_usage`. Exact archived ratchet tests at 697af966 exit 0: ..                                                                       [100%] 2 passed in 0.19s. Wall time 0.601 seconds. transcript_tool_transport.py max falls from 15 to 10. This independently corroborates the old task evidence for the first CI correction. All owned OS temp was removed.
