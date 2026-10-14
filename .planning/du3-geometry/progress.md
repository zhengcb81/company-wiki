# Progress
2026-10-14 ROOT created sparse code checkout and local ledger; READY_NOT_STARTED.
2026-10-14 geometry harness:
  - Recon: read DU3-GEOMETRY card + INTERFACES, baseline layout_hints/adapter/parsers, PyMuPDF 1.26.7 available.
  - A (TDD): wrote 13 synthetic builders + contract/unit_binding counterexample tests; RED confirmed
    (ModuleNotFoundError: layout_snapshots) -> evidence/a-red-receipt.md.
  - B: implemented layout_snapshots (identity/contract/unit_binding/projection). Offline GREEN 36 passed / 7 skipped.
    layout_hints read-only consumer regression 42 passed / 6 skipped. ruff clean.
  - C: real snapshots via read-only PyMuPDF dict/words/find_tables (reuse native probe, bounded). Real opt-in
    8 passed / 1 skipped (Miniso UNAVAILABLE). Evidence evidence/c-real-snapshots.json. Originals 4/4 preserved.
  - Fixed max_pages count-vs-pagenumber bug caught by real jinhe p223 data; locked by synthetic test.
  - Handoff written (handoff.md / handoff.json). Git status clean: only the 4 exclusive paths.
2026-10-14 NEXT: independent agent review of all card acceptance requirements, then STOP for ROOT.
