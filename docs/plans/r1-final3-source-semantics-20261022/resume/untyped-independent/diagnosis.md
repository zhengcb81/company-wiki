# Untyped numeric attribution diagnosis

Status: reproduced shared root cause, 6 public RED failures / 7 controls pass.

The real public selector selects six neutral Chinese, Traditional Chinese and English rows with two independently delimited numerical cells plus an explanatory change cell, but gives them `quality_flags=[]`. Their citation views treat the rows as support and their reading constraints omit the existing numeric-unknown warning. No `_understand` monkeypatch or direct private-admission replacement was used. The Chinese pipe variant was not selected and is explicitly not counted as a RED.

## Ownership and minimal repair

`narrative_reading._candidates` invokes the one shared table-purpose classifier only for `operating_table`; untyped source rows retain `paragraph/background` ownership. The final `select_reading_evidence` quality set also filters on `operating_table`, so incomplete literal value-cell structure escapes both paths.

Use one distinct pure observer in `document_normalization/table_shapes.py`, reusing `_is_value_cell`, to recognize two or more independently delimited original value cells with label/explanation material. Preserve `has_tabular_value_tail` as the existing stricter inferred-heading guard. The new observation only establishes unknown column/period/unit attribution. It never proves table membership or produces cells, headers or periods.

Apply that unknown observation at the existing final quality outlet, mapping original IDs into actual selected spans/carriers and keeping complete native bindings authoritative. Reuse `table_structure_ambiguous`, its existing `_context` warning and scoped compiler transport. No parser-global permanent flag, guessed cross-page header, keyword/account exclusion, new schema or additional approval is needed.

## Controls and bounded proof

Five prose/single-value controls remain selected without table flags. A hand-declared in-memory native table descriptor proves the existing shared native binder keeps value `47` bound to its exact row label/unit/period and emits it without ambiguity. No format parser or source read was called.

`execution.json` binds eight owner files before/after; bytes were stable. It records import-owner verification from inside pytest, requested and actual relocated temp paths and removal. The temporary test path and its relocated `cw-pytest-basetemp` generation were both verified absent. `public-red-observations.json` retains actual public reading contexts and source package ownership.

This is an engineering root-cause RED, not a claim that all annual targets, source selection or final summary have been accepted.
