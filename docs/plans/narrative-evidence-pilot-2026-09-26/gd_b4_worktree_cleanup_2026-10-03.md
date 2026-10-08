# G-D B4: exact historical worktree cleanup

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> Frozen 2026-10-03. Root owns this card and publication; space_reaudit owns only per-root execution and result receipts. No new user approval or test gate.

## Binding and boundary

- Input audit: harness_lanes/results/space_reaudit_2026-10-03.json
- Audit SHA-256: a777462988bb406987f28cea8a03a8bdf11c6f2609568690378a3c290cdc69c1
- Approved ordinary roots: exactly the following 23 roots, 1,414,586,922 logical bytes. No wildcard expansion.
- All HEADs are ancestors of current master; no unique commits, no tracked dirty/untracked files. Source/fact directory copies are tracked legacy projections and metadata, not unique downloaded originals.
- Permitted ignored data: pytest/ruff/mypy caches, __pycache__ Python bytecode, and the five individually verified 0-row .ingested/ingested.db SQLite stores. Unknown ignored files hold only that root.
- Excluded: main checkout, pinned Temp/company-wiki, all three managed Codex roots, cw-preb/r4b02-preb02, fc-802/fc-802-r3/fc-804/fc-805 and every other project/active consumer tree.

## Exact allowlist

| Absolute root | HEAD | Logical bytes |
|---|---|---:|
| C:/Users/郑曾波/AppData/Local/Temp/cw-b06-wt | ced354a24c02928a28cc94c34b18780f9766cf06 | 70271410 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1003-wik | 155e759c4c8cd0f63a58075e7820666c238f2b2d | 57081830 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1101-wik | f6eb58410e85b20aed738418cbaef6833803a4b6 | 57078968 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1203/base-wiki | a6937f34081cdc928704d511e0b011f71b061a90 | 57121737 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1203/result-wiki | 460d2730719acb6e4fdf59886c568c847d10d028 | 58731176 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/base-wiki | 460d2730719acb6e4fdf59886c568c847d10d028 | 58732670 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/layout/company-wiki | f03142cae67055b7895f3fedaa06e40fdfafcf06 | 132468047 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/r2/company-wiki | 925b3e8027f9c22c475656efae98142b976244e6 | 66924090 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/wiki-base | 925b3e8027f9c22c475656efae98142b976244e6 | 57153365 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/wiki-result | b93994ae27201563c6789d1f8242bf53295eda68 | 58776448 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/wiki-base | b93994ae27201563c6789d1f8242bf53295eda68 | 58069108 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/wiki-result | 304966d1579344cbf4b1c368c7ddea46b443f982 | 58081712 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-505 | 47a03117ada0d5b3fe33ba9ab62a6718a3efeaeb | 56626668 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703/company-wiki | 545a9861dd5b7c72669e053d05f6e7de1beae6f6 | 56497795 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703-r2/company-wiki | 85f45a30f8f07faa33148f4a8be2e4cfcb76c3dd | 56514908 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703-r3/company-wiki | d546558830fd594fcbb83eef7cba550d4b4bc1d2 | 56513474 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-704/company-wiki | c3fd9c413eb8f1309af21a2d67daa19aacabbd30 | 56570580 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-705/company-wiki | 6ada6fed17a66457b8aa624b5d5a41a49ddccb15 | 56614336 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-705-r2/company-wiki | f20a64f265c0472c16e19a3ddfa6d7e5d0b79e54 | 56612518 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-801/company-wiki | bf502af1ce5a1a944f3142befaf6a9b899d1f4ae | 56669271 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-802-r2/company-wiki | 74f8ec08d613dacaa68413736d364b3ce5bd75a1 | 56681653 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-803/company-wiki | 18a2792ca5e02e7960d694a8007e097a46c4179e | 56731779 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-r8-debug | 304966d1579344cbf4b1c368c7ddea46b443f982 | 58063379 |

## Execution

1. Root publishes this card and the audit before execution. Re-read this committed audit/card; do not expand the list.
2. Before each removal verify resolved absolute root is exactly allowlisted and Git-registered; HEAD unchanged and ancestor of master; no tracked/untracked changes; no reparse ancestor/descendant; known ignored classes only. Hold changed or unreadable roots individually.
3. Use ordinary git worktree remove <exact-path>, never --force, reset, recursive PowerShell deletion, branch deletion, restoration of empty trees, or broad prune. Git handles its own linked-worktree metadata.
4. Save per-root HEAD/check/removal outcome and absence/registration checks in independent results. Space benefit is removed logical bytes; filesystem free delta is a separate observation, not invented equality.
5. Root incorporates the result in PWF, commits/pushes it, and stops staging while the agent mutates shared worktree metadata. No new full suite: only existing baseline/source facts and per-root checks above.

## Managed roots

Use app archive_worktree only. UI already reports archived attachments, but all three physical roots and Git registrations still existed at 2026-10-03 follow-up. Do not count their 269 MB as freed until actual removal is observed; do not bypass the managed lifecycle with ordinary Git removal.

## Completion

The receipt names removed, changed/held and failed roots separately. Preserve excluded historical refs/small owner records. This batch is independent of N4 model/Worker integration and the B3 two-archive retirement.
