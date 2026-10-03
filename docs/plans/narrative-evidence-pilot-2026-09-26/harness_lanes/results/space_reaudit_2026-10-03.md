# Space re-audit / exact worktree candidates

UTC: 2026-10-03T11:31:06.712580+00:00; main HEAD bfc1baeaa94a03794652b628a92d15e5572f1878. Plan only: no deletion, reset, PWF mutation or commit.

## Space comparison

Three roots: **42,692,408,858 bytes / 39.760404 GiB**. This is exactly previous 45,748,203,875 - B1 deleted 3,055,796,224 + new intent/receipt 1,207. Companies/source_manifests are unchanged; the bak is absent. There is no observed data regrowth.

Whole readable project: 43,887,252,776 bytes / 40.873189 GiB. Other 33 worktrees: 1,985,538,310 bytes / 1.849177 GiB. Combined: 45,872,791,086 bytes, 45.87 decimal GB / 42.722366 GiB. Main scan excludes 24 ACL-inaccessible old tests (22 .rf-*, two .tmp-pytest-narrative-*); data roots have zero access errors. No reparse followed.

Companies total 25,198,502,813 bytes: PDF 15,130 files / 25,089,822,677 bytes; remaining 108,680,136 bytes include Word/Excel/HTM/news/sidecars, not all disposable. Two retained old derived archives total 11,406,183,129 bytes / 10.622836 GiB; they are not original PDF/TXT backups.

## Original 26 clean / no-unique candidate roots

Full machine-readable fields and per-item hold reasons are in the accompanying JSON. RF pinned Temp/company-wiki and all managed .codex trees are excluded from ordinary removal. Ignored data holds only its item. Current PWF task owner must freeze the final execution card before ordinary removals.

| Exact root | Exact HEAD | Bytes | Branch | Dirty / untracked | Ignored count | Disposition |
|---|---|---:|---|---|---:|---|
| C:/Users/郑曾波/.codex/worktrees/data-lake-reader/company-wiki | cba745ac7e398fc2ccd84c132aa5c4c47d8828eb | 125,485,516 | codex/narrative-gates-integration | 0 / 0 | 627 | managed_archive_by_root |
| C:/Users/郑曾波/.codex/worktrees/transcript-companion/company-wiki | ced354a24c02928a28cc94c34b18780f9766cf06 | 71,519,645 | codex/transcript-companion | 0 / 0 | 72 | managed_archive_by_root |
| C:/Users/郑曾波/AppData/Local/Temp/company-wiki | 2e674cca4b715fea492ad9071de3ee456ca61835 | 73,142,856 | detached | 0 / 0 | 77 | hold |
| C:/Users/郑曾波/AppData/Local/Temp/cw-b06-wt | ced354a24c02928a28cc94c34b18780f9766cf06 | 70,271,410 | r4b06-wip | 0 / 0 | 0 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1003-wik | 155e759c4c8cd0f63a58075e7820666c238f2b2d | 57,081,830 | detached | 0 / 0 | 5 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1101-wik | f6eb58410e85b20aed738418cbaef6833803a4b6 | 57,078,968 | detached | 0 / 0 | 0 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1203/base-wiki | a6937f34081cdc928704d511e0b011f71b061a90 | 57,121,737 | detached | 0 / 0 | 5 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1203/result-wiki | 460d2730719acb6e4fdf59886c568c847d10d028 | 58,731,176 | detached | 0 / 0 | 83 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/base-wiki | 460d2730719acb6e4fdf59886c568c847d10d028 | 58,732,670 | detached | 0 / 0 | 83 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/layout/company-wiki | f03142cae67055b7895f3fedaa06e40fdfafcf06 | 132,468,047 | detached | 0 / 0 | 2292 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1204/r2/company-wiki | 925b3e8027f9c22c475656efae98142b976244e6 | 66,924,090 | detached | 0 / 0 | 194 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/wiki-base | 925b3e8027f9c22c475656efae98142b976244e6 | 57,153,365 | detached | 0 / 0 | 5 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-1205/wiki-result | b93994ae27201563c6789d1f8242bf53295eda68 | 58,776,448 | detached | 0 / 0 | 83 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/wiki-base | b93994ae27201563c6789d1f8242bf53295eda68 | 58,069,108 | detached | 0 / 0 | 52 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-130x/wiki-result | 304966d1579344cbf4b1c368c7ddea46b443f982 | 58,081,712 | detached | 0 / 0 | 52 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-505 | 47a03117ada0d5b3fe33ba9ab62a6718a3efeaeb | 56,626,668 | detached | 0 / 0 | 10 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703/company-wiki | 545a9861dd5b7c72669e053d05f6e7de1beae6f6 | 56,497,795 | detached | 0 / 0 | 9 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703-r2/company-wiki | 85f45a30f8f07faa33148f4a8be2e4cfcb76c3dd | 56,514,908 | detached | 0 / 0 | 9 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-703-r3/company-wiki | d546558830fd594fcbb83eef7cba550d4b4bc1d2 | 56,513,474 | detached | 0 / 0 | 9 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-704/company-wiki | c3fd9c413eb8f1309af21a2d67daa19aacabbd30 | 56,570,580 | detached | 0 / 0 | 9 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-705/company-wiki | 6ada6fed17a66457b8aa624b5d5a41a49ddccb15 | 56,614,336 | detached | 0 / 0 | 10 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-705-r2/company-wiki | f20a64f265c0472c16e19a3ddfa6d7e5d0b79e54 | 56,612,518 | detached | 0 / 0 | 10 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-801/company-wiki | bf502af1ce5a1a944f3142befaf6a9b899d1f4ae | 56,669,271 | detached | 0 / 0 | 9 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-802-r2/company-wiki | 74f8ec08d613dacaa68413736d364b3ce5bd75a1 | 56,681,653 | detached | 0 / 0 | 0 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-803/company-wiki | 18a2792ca5e02e7960d694a8007e097a46c4179e | 56,731,779 | detached | 0 / 0 | 7 | planned_ordinary_remove |
| C:/Users/郑曾波/Projects/.fcap-review/fc-r8-debug | 304966d1579344cbf4b1c368c7ddea46b443f982 | 58,063,379 | detached | 0 / 0 | 46 | planned_ordinary_remove |

Initial 26 total: 1,684,734,939 bytes. Minus RF pinned root: 25 roots / 1,611,592,083 bytes. Ready subset after classified per-item holds: 23 roots / 1,414,586,922 bytes.

All candidate companies copies have zero PDF/TXT original bytes; they are tracked legacy projections/static assets. Shared Git objects are counted once in main; worktree .git files only link to them.

## Explicit exclusions

| Exact root | Bytes | Reason |
|---|---:|---|
| C:/Users/郑曾波/.codex/worktrees/rf-state-audit/company-wiki | 72,492,226 | Unique historical documentation commits; preserve refs first. |
| C:/Users/郑曾波/AppData/Local/Temp/cw-preb | 72 | Empty .git-only root with tracked deletions; do not restore old files. |
| C:/Users/郑曾波/AppData/Local/Temp/r4b02-preb02 | 77 | Empty .git-only root with tracked deletions; do not restore old files. |
| C:/Users/郑曾波/Projects/.fcap-review/fc-802/company-wiki | 56,920,847 | Unique historical documentation commits; preserve refs first. |
| C:/Users/郑曾波/Projects/.fcap-review/fc-802-r3/company-wiki | 56,693,435 | Unique historical documentation commits; preserve refs first. |
| C:/Users/郑曾波/Projects/.fcap-review/fc-804/company-wiki | 56,785,249 | Untracked reviewer receipt/report; preserve small records first. |
| C:/Users/郑曾波/Projects/.fcap-review/fc-805/company-wiki | 57,911,465 | Untracked reviewer receipt/report; preserve small records first. |

Also exclude main checkout, consumer active roots and RF pinned Temp/company-wiki. The two .git-only Temp roots have tracked deletions and negligible bytes; do not recreate old files.

## Managed Codex attachments

Root confirmed all three .codex worktrees are managed artifacts attached to this chat. Use root-owned archive_worktree for transcript-companion/data-lake-reader/rf-state-audit; it preserves recoverable Git snapshots including unique audit commits. Never ordinary git remove these roots.

Ordinary candidate ceiling after pinned and managed exclusions: 23 roots / 1414586922 bytes; per-item ignored holds still apply.

Managed pre-archive check: each root has 40 fact-directory files, all Git tracked, including markdown news and the two source/provenance manifests (644 / 1,633 bytes). No unique ignored or untracked source inputs were found. data-lake-reader ignored entries are CodeGraph/mypy/pytest/ruff caches plus pyc; transcript-companion has pytest/ruff caches plus pyc; rf-state-audit has pyc only. Unknown ignored/reparse entries: zero. All ignored entries are disposable/rebuildable; snapshots retain tracked fact files and audit commits. rf-state-audit pyc appeared after initial inventory, so actual archive receipt determines the current space benefit.

## Ordinary ignored classification

All 23 ordinary roots were rechecked. Only known pytest/ruff/mypy/CodeGraph caches, Python pyc and five exact empty .ingested/ingested.db files were present. Each ingestion DB is 12,288 bytes with one table ingested(hash TEXT PRIMARY KEY, created_at TEXT) and zero rows. IngestedDB automatically creates this legacy MD5 processing-marker store; it has no document body/source manifest or unique original. Root permits these disposable classes; there are zero unknown ignored paths and no HEAD/status drift. Do not turn known caches into new holds.

## Execution rules

- Root must freeze exact cleanup card first. No deletion has occurred.
- Recheck each allowlisted HEAD/status/ignored/reparse/root registration and owner changes immediately before removing.
- Ordinary git worktree remove <exact-path> only. No force/reset/recursive PowerShell deletion/broad prune.
- Hold empty/unknown-ignored/unreadable/reparse/changed roots individually; known cache/pyc and exact verified empty ingested DB are permitted.
- Never restore empty .git-only old trees.

## Old derived archive retirement

- Current catalog retains all non-evidence fact tables; prepared receipt contains matching table row hashes.
- No cold archive runtime reader; EvidenceQuery uses source+locator/document, not span-ID-only lookup.
- Keep archive SHA/size and retirement receipts; use current source/location/document/retire-audit facts as tombstones.
- Update obsolete cold-snapshot diagnostic text/state and let completed B1 receipt remain inspectable after archive retirement.
- No full SQLite restore or default millions-of-IDs secondary ledger. Stream gzip ID/source/locator only if a concrete consumer needs it.

Independent retirement of both archives leaves three roots at 31,286,225,729 bytes / 29.137568 GiB. Further derived/index deletion has a theoretical ceiling 2.673886 GiB, not a proved all-deletable batch.

JSON SHA-256: a777462988bb406987f28cea8a03a8bdf11c6f2609568690378a3c290cdc69c1.
