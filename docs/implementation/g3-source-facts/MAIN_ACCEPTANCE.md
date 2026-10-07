# MAIN acceptance — 2026-10-07

Worker delivery `3292eb55266a36e229ea913f77b6cc324fb2a725`. Reports are readonly observations and proposals, not applied production changes.

## Accepted facts and corrections to recommendations

- S05/S06 financing classification and identity, S07 identity are useful R2 metadata proposals. S07 published date remains unknown. S08 identity may be handled independently of its published-date conflict; the historical handoff's suggested conflict waiver is **not** adopted as a new permission requirement.
- S01–S04 retain their current status in this acceptance. The historical reason (missing source_url) requires re-evaluation under the current diagnostic-only rules; lack of URL or a historical review receipt is not itself a new permanent rejection. Future restoration uses the formal current source entry, keeps original IDs/SHA and records actual provenance. No invented receipts.
- S09 TXT can be assessed through the formal legacy source-registration path. No need to redownload or seek new authorization simply because an old provider receipt was never stored. Actual provenance remains legacy/unverified where unknown.
- Registered internal-copy logical upper bound **98,845,393B (94.3MiB)**, verified extra-copy bytes **36,191,979B (34.5MiB)**. Allocated/releasable bytes unknown; deleted bytes zero. MAIN recommends no object-storage migration now because the maximum possible benefit is small compared with reference migration cost and actual allocation is unknown. The worker's 256MiB recommendation threshold is **not** a new eligibility gate.

## Reusable tool wiring

`metadata_bound` no longer discovers a live repository via Git on import or assumes `.source_catalog/catalog.sqlite3`. Caller supplies `--database` and `--root-id` explicitly (database comes from current catalog configuration); default output is stdout with zero report-file writes. Optional `--output` cannot replace the input DB. SQLite uses encoded URI `mode=ro`, query_only and one read transaction; no catalog migrations, raw reads or subprocesses.

RED proved import-time Git discovery. New explicit-path/root, no-import-I/O, missing-input, output-collision and DB bytes/mtime tests are green with existing 55 responsible tests. Windows invalid `?` fixture filename was corrected to a valid `#` filename and URI escaping is exercised.

Worker reports/observation IDs are preserved as historical evidence. Applying metadata, restoring sources, TXT registration and R3 narrative processing remain MAIN follow-up; this acceptance performs none of those production actions.
