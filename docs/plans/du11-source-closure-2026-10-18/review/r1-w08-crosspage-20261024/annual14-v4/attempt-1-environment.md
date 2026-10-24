# V4 natural-suite environment retry

The first full-suite attempt on 2026-10-24 ran 2,140 tests successfully, skipped 11, and reported 13 fixture setup errors. Those errors were all temporary-directory creation failures under the sandbox AppData TEMP path after `conftest.py` relocated the requested pytest basetemp. The outer harness cleanup also received `PermissionError` on that sandbox TEMP path. No product assertion failed. The exact generated paths were later confirmed absent.

The root cause was the runner inheriting a system TEMP directory that is not writable from this sandbox. The runner was corrected to set `TEMP`, `TMP`, `TMPDIR`, and `CW_BASETEMP_FALLBACK_ROOT` to a fresh, repository-local temporary root. The successful rerun collected 2,164 tests: 2,153 passed, 11 skipped, 0 failed in 60.42 seconds. The project pytest cleanup event reports `removed: true`, and the runner verified the owned root no longer exists.
