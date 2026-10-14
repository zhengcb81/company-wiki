# Findings: DU3-GEOMETRY

## Scope / boundary
- Owned exactly 4 exclusive paths (all new; `git status` shows only these). Did NOT touch parser/normalization
  parent `__init__`, PDF/HTML/OCR/PPTX entries, observation_adapter, layout_hints/bridge, registry/selector/summary,
  source_catalog, automation, ROOT PWF, deps/CI/config, other worktrees. No new OCR backend / second PDF parser /
  file storage.

## Design decisions
- One public pure function `project_layout_snapshot`; it BINDS already-extracted fine geometry to existing units
  and never re-derives layout. layout_hints stays the single layout-relation engine (columns/headings/tables/
  relations); the projection infers no column_lane / section / continuation / header / footnote.
- `limits_identity` centralizes default caps (10000 units / 64 pages / 200000 fine elements / 1000000 work),
  tighten-only limits, WorkBudget, coordinate-frame reconciliation (dict/rect/rotation/transform), and STRICT
  NFC/trim char alignment. `metadata_projection` assembles the patch with per-unit atomic commit.
- Each fine element keeps its OWN real bbox + native-index/char-range basis + page/frame/source provenance. A whole
  row/block/table bbox is never copied into a cell. `row_cells` strings alone are not fine geometry. Repeated
  identical text in different blocks is never merged (keyed by real bbox/native index, not text equality).

## Key bug caught by real data
- `max_pages` is a COUNT cap (at most 64 pages), NOT a page-number ceiling. Real originals use high page numbers
  (e.g. p223/224); the first implementation wrongly skipped them (`page_no > 64`). Fixed to bound processed-page
  count; locked by synthetic `test_max_pages_is_a_count_not_a_page_number_ceiling`. This is why the real jinhe
  multi-column assertion initially failed.

## Real measurement (measurement oracle only, NOT recall)
- 金禾 multi-col table binds to real per-cell bboxes with up to 6 distinct columns at `cell` granularity.
- 中微 narrative page yields 0 cells (no fabricated table geometry) — word/block only.
- 恒锋 cross-page binds both pages; 世华 (new company) binds real cells. Miniso original absent on this host
  -> UNAVAILABLE (honest skip, never a real pass).
- All 4 originals preserved SHA-256 + mtime + size (4/4) — locked by opt-in test + c-real-snapshots.json.

## Bugs found by independent review (all fixed + regression-tested)
- `complete` could be True while `incomplete_pages` non-empty (frame-problem page with zero bindings) and while
  units on absent pages were unbound. Fixed: frame codes into PARTIAL_CODES + incomplete_pages/unbound folded
  into complete; explicit UNREAD_PAGE for units on pages the snapshot never covered.
- `max_units` lowered did NOT stop processing (only flagged). Fixed: only the first max_units units are bound;
  the rest deferred (consistent with max_pages / fine-element caps).
- Non-string `binding.unit_id` crashed with TypeError in `_diag`'s `sorted()`. Fixed: contract validates it as a
  non-empty string -> ValueError; `_diag` hardened with `key=str`.
- `MAX_TEXT_BYTES` was declared but never enforced. Fixed: enforced in native_probe span/table builders.
- Non-mapping fine elements / duplicate unit ids were silently dropped. Fixed: FINE_ELEMENT_INVALID / DUPLICATE_UNIT_ID.
- "relocated" char re-pins discarded the supplied range. Fixed: `char_start_supplied`/`char_end_supplied` retained.

## Honest unproven
- Not wired to production; does not claim dual-column order / fine table header / key business recall solved.
- Binding reliability != fine-column/table recall; no recall benchmark run.
- HTML/PPTX/OCR emit no coords today -> kept unknown, never fabricated.
- Coordinate frames handled declaratively; arbitrary affine conversion not implemented (unknown frame -> partial).
