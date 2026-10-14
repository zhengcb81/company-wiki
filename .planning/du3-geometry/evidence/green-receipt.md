# DU3-GEOMETRY GREEN receipt (post-implementation + post-review verification)

Run from worktree root `.../shared-reading-completion-20261014/geometry` on 2026-10-14.

| Step | Command | Result |
|---|---|---|
| A+B offline (synthetic) | `python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots -q` | **47 passed, 7 skipped** |
| C real (opt-in) | `CW_DU3_GEOMETRY_REAL=1 python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots/test_c_real_snapshots.py -q` | **8 passed, 1 skipped** (Miniso UNAVAILABLE) |
| B layout_hints read-only consumer regression | `python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q` | **42 passed, 6 skipped** |
| static | `python -X utf8 -m ruff check <owned package+tests+fixtures>` | **All checks passed** |

- 47 = 23 snapshot_contract + 18 unit_binding + 6 projection/consumer + 2 real-probe offline self-check
  (includes 9 regression tests added for the independent-review fixes).
- Real opt-in 8 = fingerprint-preservation, jinhe multi-column, hengfeng cross-page, amec narrative,
  shihua new-company, real-no-paths + 2 offline self-checks; 1 skipped = Miniso (original absent on host).
- layout_hints 42 passed confirms the shared engine is a READ-ONLY consumer with NO regression.

Pre-commit hooks (ruff / dependency parity / host-assumption guard) passed on the implementation commit.
Independent review verdict: ACCEPT_WITH_FIXES — all P1/P2/P3 findings fixed and regression-tested (see handoff.md).
