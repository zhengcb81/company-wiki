# Progress — du3-dependencies

- 2026-10-14 ROOT created sparse code checkout and local ledger; READY_NOT_STARTED.
- 2026-10-14 worker started. Base `195aba20b0aecc2d661d7d04c5ba72f982bc02d0`,
  branch `codex/du3-dependencies-20261014`, worktree clean except the untouched
  `.planning/du3-dependencies/` ledger.
- 2026-10-14 baseline recorded before any edit: `python -m pytest
  tests/unit/document_understanding_profiles -q` -> 181 passed in 2.51s (exit 0).
  Python 3.13.9 (Anaconda Windows). No production config or original was read for
  writing; no model/network call made.
- 2026-10-14 **A (TDD, RED first).** A-node counter-examples written before any
  implementation: `51 failed in 1.80s` with
  `ModuleNotFoundError: No module named 'company_wiki.document_understanding.decision_dependencies'`.
  Receipt `evidence/a_red.json`.
- 2026-10-14 **B (implementation + engineering).** `decision_dependencies` package built
  to the frozen DU3/1 wire; 37 B-node tests including cross-process digest stability,
  closed manifest key set, budget behaviour and an AST import guard.
- 2026-10-14 **C (independent snapshot replay).** Read-only replay against the real
  installed `reading_catalog.json` (SHA-256
  `29bfefbe270cb8d2035bcd203dcf9b1226934dce7d0fd338132d9d559e18b46c`, unchanged before
  and after) with synthetic legal scopes. Matrix: relevant edit -> changed, losing
  participant edit -> changed, out-of-domain edit -> same, array reorder -> same,
  whole-catalog domain -> partial (78 scopes over 38 components, `SCOPES_LIMIT_REACHED`).
  Receipt `evidence/c_replay_receipt.json`.
- 2026-10-14 **Node runs.** `python .planning/du3-dependencies/run_nodes.py`:
  A 55 passed (exit 0, 3.107s), B 37 passed (exit 0, 3.458s), C 19 passed (exit 0, 3.156s),
  ALL 111 passed (exit 0, 3.554s). `evidence/nodes.json`.
- 2026-10-14 **100-source manifest encoding measured.** 2 scopes / 4 components /
  6 candidates per source: mean 2042.2 B, min 1970 B, max 2128 B, total 204216 B.
  `evidence/b_size_report.json`.
- 2026-10-14 **Static checks.** `ruff check` on the three owned trees exit 0;
  `mypy src/company_wiki/document_understanding/decision_dependencies` exit 0
  (5 source files). Pre-commit: dependency-declarations skipped, ruff Passed,
  mypy skipped, config doctor skipped, host-assumption-guard Passed.
- 2026-10-14 **Regression across the existing DU suites.** `607 passed, 17 skipped`
  in 20.26s over document_understanding_root/profiles/selection/structure/layout_hints
  plus the new lane. No regression.
- 2026-10-14 **Committed.** Implementation commit
  `bc63a74eac1f73e6184a87a4b1bb65044840c1ad` (14 files, 3807 insertions, code + tests).
  Ledger/handoff committed separately afterwards.
- 2026-10-14 **Handoff written.** `handoff.md` + `handoff.json`. STOP waiting for ROOT;
  no master merge, no push, no production default change.
