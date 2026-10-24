# Local repository hygiene and branch audit — 2026-10-24

## Scope and result

Read-only inventory covered company-wiki, revenue-forecast, filing-fetch, StockWiki, earnings-transcripts, MeetingConverter, industry-research, and QAbyLLM. No external repository files were changed. IQS was excluded because its separate task is active. The cleanup below was limited to generated test sandboxes inside company-wiki; original company source directories, production configuration, tracked source code, PWF receipts, and other repositories were not touched.

company-wiki was at `master` / `origin/master` SHA `808623377905520ec0c28c7330fe14243e4c6c04` before and after cleanup. Before cleanup, Git reported 16,893 untracked files / 413,986,038 bytes. After cleanup it reported 8,007 / 185,882,840 bytes: 8,886 fewer untracked files and 228,103,198 fewer Git-visible bytes. The removed roots occupied 379,243,632 filesystem bytes (13,919 files); the larger filesystem saving includes ignored files which Git status does not count.

## What was removed

Twenty-five exact roots were checked for workspace containment, reparse points, and protected source-tree prefixes, then removed:

- `.planning/r1w1` — test-generated synthetic project trees (`test_*`, ACME and generated fixture records), repeated SQLite/WAL/SHM and lock files. The 7,870-file tree occupied 314,470,994 bytes. Its appearance in `.planning/r1-w01-test/red-behavior.log` is retained as historical test output; it is not a live input or a current PWF receipt dependency.
- The `cwp-m5*` and `cwp-temp-m5-red-20261024` roots — repeated pytest basetemp outputs containing synthetic ACME/test-owned fixtures, including helper-generated PDFs. The protected company source directories were not part of these roots and were not touched.
- The three `cwpaW03-debug-*` test roots — outputs from the local W08 debug pytest runner.
- `.tmp-w08-final-20261024`, `.tmp-w08-full-20261024`, `.tmpw08f`, and `.tmp-w13-{final,focused,prepush-e2e,repro}` — repeated W08/W13 pytest basetemp outputs.

The deletion command verified every resolved target stayed under the company-wiki root, none was a reparse point or under `companies/`, `sectors/`, or `themes/`, and all 25 paths were absent afterward. No live Python/pytest process was visible at cleanup time.

## Preserved untracked material

The remaining 185,882,840 Git-visible bytes are mixed but mostly audit and run evidence, not disposable test scratch:

| Area | Current untracked size | Decision |
|---|---:|---|
| `.planning/r1ctfix` | 52.50 MiB | Keep: explicit paths, logs, and environment are cited by `docs/plans/r1-contract-debt-20261021` handoff/review receipts. |
| `.planning/shared-reading-production` | 44.44 MiB | Keep: local live-source/cache/provider receipts and usage state; this is the only local evidence for some runs. |
| `.planning/r1-w09-root-integration-20261023` | 27.22 MiB | Keep: RF integration inputs, snapshots, outputs, tests, and handoff evidence. |
| `docs/plans` | 14.10 MiB | Keep: current review reports, real-source replay receipts, and work-package handoffs; do not stage wholesale. |
| `pytest-of-*` | 4.17 MiB | Keep for now: a preserved publication inventory names a result under this root; renew that receipt before removing it. |
| Other W08/W11/R1 evidence roots and logs | remainder | Keep until each owning PWF receipt is reconciled. |

Related local checkout inventory: RF has 147 untracked files / 54.30 MiB under `output/cross-market-rf-e2e-2026-10-08` and three modified `assurance/runs/*alert*` state files; retain as test/operation evidence. StockWiki has two untracked files under `runs/c16b` (0.20 MiB); retain pending its run handoff. Earnings-transcripts has `eval_results.json` and two `.workbuddy-ai/memory` files (0.04 MiB); preserve pending purpose confirmation. FF has 89 small pytest output files (0.08 MiB); no changes made. MeetingConverter's tracked `.coverage` modification was pre-existing and explicitly protected by its card. Industry-research and QAbyLLM are clean.

## Branch and remote reconciliation

Current checkout HEADs match their configured remotes for CWP (`master`/`origin/master` 80862337), RF (`main`/`origin/main` c48f86bd), FF (`main`/`origin/main` e0d9642), earnings-transcripts (`main`/`origin/main` 2584b7e), and MeetingConverter (`master`/`origin/master` 8a33a7f). That does **not** mean every local side branch was merged.

- CWP has 14 local heads that are not ancestors of `master`. Several are already patch-equivalent to main and should not be bulk-merged. Non-equivalent commits remain on `codex/du3-dependencies-20261014` (decision-dependency fix), `codex/n4t2-selective-narrative-coverage` (narrative coverage), and `codex/w13-cwp-gates-20261024` (small review fix plus handoff). W13 has later mainline code (`67439d0a`); reconcile final file behavior before deciding whether the branch change is already superseded. Docs/provenance-only heads include `codex/g1-legacy-entry-retirement`, `codex/history/fc802-rejected-20261003`, `codex/rf-state-audit`, and `du11-close-docs`. Other non-ancestor CWP refs were patch-equivalent to main at this check. CWP remote is current; no branch was merged or deleted in this audit.
- RF has two non-ancestor local branches: `codex/revenue-source-reader` contains a source-code prototype; `codex/du5-rf-units-20261015` contains documentation/evidence. Neither was merged or deleted.
- FF has one non-ancestor local branch, `codex/transcript-companion`, with a source-code change and handoff. It was not merged or deleted.
- StockWiki has no local branch head outside local `master`, but its clone has no `refs/remotes/origin/*`; remote merge status cannot be established from this checkout.
- Earnings-transcripts and MeetingConverter have no non-ancestor local branch heads. Their current main branches match their configured remote heads.
- RF/FF/CWP have many registered linked worktrees (43/32/68 respectively). Worktrees were not removed: this audit did not establish that each is abandoned, and worktree cleanup is separate from untracked-file cleanup.

## Follow-up

1. Reconcile the three CWP code-bearing branch heads, RF `revenue-source-reader`, and FF `transcript-companion` against current mainline code and their PWF receipts; do not merge entire stale branches just to make ancestry green.
2. Decide whether the docs/provenance-only heads should be cherry-picked, archived, or left as historical refs after verifying their handoffs are already in canonical PWF.
3. Audit the remaining `.planning` roots by owning receipt before deleting or committing anything. Never use `git add -A` for this mixed workspace.
4. For future pytest runs, keep test basetemp outside the repository where possible and record/clean the exact test-owned root after the run. This prevents generated synthetic projects and SQLite sidecars from accumulating under project-local `.planning` directories.
