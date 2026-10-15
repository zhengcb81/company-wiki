"""``du4-table-observation/1`` -> ``du4-table-bindings/1``.

Pure in-memory binder: it indexes the native slots and header references of one
table observation once, binds every value ``TextRef`` to a native column, the
real header path and the disclosed period, and reports per-value
``bound|ambiguous|unavailable``.  It never rewrites original strings, never
computes missing values, never converts currency/scale, never splits a merged
cell into invented columns and never guesses periods from bare year labels.

Structural errors (wrong schema, duplicate cell ids, illegal indices, refs
outside their unit) raise ``ValueError``; recoverable evidence problems become
per-item diagnostics.  All indexing and binding work is charged to the caller's
shared ``WorkBudget``; exhaustion keeps the already determined results and
returns an explicit ``partial`` status.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..layout_hints.contract import WorkBudget, WorkBudgetExceeded
from . import _labels, _periods

SCHEMA_IN = "du4-table-observation/1"
SCHEMA_OUT = "du4-table-bindings/1"

PRESENCE = frozenset({"present", "empty", "unavailable", "merged_unknown"})
PROVENANCE_KINDS = frozenset({"native_slot", "fine_geometry"})
CELL_KEYS = (
    "cell_id",
    "row",
    "column",
    "row_span",
    "column_span",
    "presence",
    "text_refs",
    "header_refs",
)
UNIT_KEYS = ("text", "parent_id", "role", "kind", "locator")
BINDING_STATES = frozenset({"bound", "ambiguous", "unavailable"})
BLOCKING_CODES = frozenset(
    {
        "slot_conflict",
        "header_period_conflict",
        "provenance_conflict",
        "cross_parent_ref",
        "cross_page_ref",
        "value_text_unavailable",
        "slot_value_conflict",
        "work_budget_exhausted",
        "observation_truncated",
    }
)


def _is_index(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _ref_tuple(ref: Mapping) -> tuple[str, int, int]:
    return (str(ref["unit_id"]), int(ref["char_start"]), int(ref["char_end"]))


def _ref_dict(ref: tuple[str, int, int]) -> dict:
    return {"unit_id": ref[0], "char_start": ref[1], "char_end": ref[2]}


def _validate_ref(ref: Any, unit_text: Mapping[str, str]) -> tuple[str, int, int]:
    if not isinstance(ref, Mapping):
        raise ValueError("text ref must be a mapping")
    unit_id = ref.get("unit_id")
    start = ref.get("char_start")
    end = ref.get("char_end")
    if not isinstance(unit_id, str) or unit_id not in unit_text:
        raise ValueError(f"text ref points at unknown unit {unit_id!r}")
    if not _is_index(start) or not _is_index(end):
        raise ValueError("text ref offsets must be non-negative integers")
    assert isinstance(start, int) and isinstance(end, int)
    if not (0 <= start < end <= len(unit_text[unit_id])):
        raise ValueError(f"text ref [{start}, {end}) is outside unit {unit_id!r}")
    return unit_id, start, end


class _Binder:
    def __init__(self, observation: Mapping, work_budget: WorkBudget) -> None:
        self.observation = observation
        self.budget = work_budget
        self.start_used = work_budget.used
        self.diagnostics: list[dict] = []
        self.columns_out: list[dict] = []
        self.measurements_out: list[dict] = []
        self.exhausted = False
        self.blocked = False
        self.unit_text: dict[str, str] = {}
        self.units_view: dict[str, Mapping] = {}
        self.cells: list[dict] = []
        self.label_refs: set[tuple[str, int, int]] = set()
        self.header_rows: set[int] = set()
        self.conflicted_cells: set[str] = set()
        self.provenance_conflict_cells: set[str] = set()
        self.column_paths: dict[int, list[tuple[str, int, int]]] = {}
        self.column_periods: dict[int, dict] = {}
        self.column_status: dict[int, str] = {}
        self.scope_parent: Any = None
        self.scope_page: Any = None

    # -- diagnostics ------------------------------------------------------
    def diag(self, code: str, **fields: Any) -> None:
        entry = {"code": code}
        entry.update({k: v for k, v in fields.items() if v is not None})
        self.diagnostics.append(entry)

    # -- validation & indexing -------------------------------------------
    def validate(self) -> None:
        obs = self.observation
        if obs.get("schema_version") != SCHEMA_IN:
            raise ValueError(f"unsupported observation schema: {obs.get('schema_version')!r}")
        scope = obs.get("scope")
        if not isinstance(scope, Mapping):
            raise ValueError("observation scope must be a mapping")
        if scope.get("parent_id") is None or scope.get("table_id") is None:
            raise ValueError("observation scope needs parent_id and table_id")
        self.scope_parent = scope.get("parent_id")
        self.scope_page = scope.get("page")
        units = obs.get("units")
        if not isinstance(units, Mapping):
            raise ValueError("observation units must be a mapping")
        cells = obs.get("cells")
        if isinstance(cells, (str, bytes)) or not isinstance(cells, Sequence):
            raise ValueError("observation cells must be a sequence")

        for unit_id, unit in units.items():
            self.budget.charge(1)
            if not isinstance(unit_id, str) or not isinstance(unit, Mapping):
                raise ValueError("units must map string ids to unit mappings")
            for key in UNIT_KEYS:
                if key not in unit:
                    raise ValueError(f"unit {unit_id!r} misses {key}")
            if not isinstance(unit["text"], str):
                raise ValueError(f"unit {unit_id!r} text must be a string")
            self.unit_text[unit_id] = unit["text"]
            self.units_view[unit_id] = unit

        header_rows = obs.get("header_rows")
        if header_rows is not None:
            if isinstance(header_rows, (str, bytes)) or not isinstance(header_rows, Sequence):
                raise ValueError("header_rows must be a sequence")
            for row in header_rows:
                if not _is_index(row) or isinstance(row, bool):
                    raise ValueError("header_rows entries must be non-negative integers")
                self.header_rows.add(int(row))

        seen_ids: set[str] = set()
        for raw in cells:
            self.budget.charge(1)
            if not isinstance(raw, Mapping):
                raise ValueError("each cell must be a mapping")
            for key in CELL_KEYS:
                if key not in raw:
                    raise ValueError(f"cell misses {key}")
            cell_id = raw["cell_id"]
            if not isinstance(cell_id, str) or not cell_id or cell_id in seen_ids:
                raise ValueError(f"duplicate or empty cell id {cell_id!r}")
            seen_ids.add(cell_id)
            if not _is_index(raw["row"]) or not _is_index(raw["column"]):
                raise ValueError(f"cell {cell_id!r} has illegal row/column")
            for key in ("row_span", "column_span"):
                span = raw[key]
                if span is not None and (not _is_index(span) or isinstance(span, bool) or span < 1):
                    raise ValueError(f"cell {cell_id!r} has illegal {key}")
            if raw["presence"] not in PRESENCE:
                raise ValueError(f"cell {cell_id!r} has unknown presence {raw['presence']!r}")
            if not isinstance(raw["text_refs"], list) or not isinstance(raw["header_refs"], list):
                raise ValueError(f"cell {cell_id!r} refs must be lists")
            text_refs = []
            for ref in raw["text_refs"]:
                self.budget.charge(1)
                text_refs.append(_validate_ref(ref, self.unit_text))
            header_refs = []
            for ref in raw["header_refs"]:
                self.budget.charge(1)
                header_refs.append(_validate_ref(ref, self.unit_text))
            self.cells.append(
                {
                    "cell_id": cell_id,
                    "row": int(raw["row"]),
                    "column": int(raw["column"]),
                    "row_span": raw["row_span"],
                    "column_span": raw["column_span"],
                    "presence": raw["presence"],
                    "text_refs": text_refs,
                    "header_refs": header_refs,
                }
            )

        provenance = obs.get("provenance")
        self.provenance: dict[str, list[Mapping]] = {}
        if provenance is not None:
            if isinstance(provenance, (str, bytes)) or not isinstance(provenance, Sequence):
                raise ValueError("provenance must be a sequence")
            for record in provenance:
                if not isinstance(record, Mapping):
                    raise ValueError("provenance records must be mappings")
                if record.get("kind") not in PROVENANCE_KINDS:
                    raise ValueError(f"unknown provenance kind {record.get('kind')!r}")
                cell_id = record.get("cell_id")
                if cell_id not in seen_ids:
                    raise ValueError(f"provenance points at unknown cell {cell_id!r}")
                self.provenance.setdefault(str(cell_id), []).append(record)

    # -- spans, occupancy, header paths ----------------------------------
    def index_slots(self) -> None:
        for cell in self.cells:
            self.budget.charge(1)
            if cell["presence"] in ("empty", "unavailable", "merged_unknown"):
                self.diag(f"slot_{cell['presence']}", cell_id=cell["cell_id"])
            for ref in cell["header_refs"]:
                self.label_refs.add(ref)
            eff_row_span = cell["row_span"]
            eff_col_span = cell["column_span"]
            cell["conflict"] = False
            for record in self.provenance.get(cell["cell_id"], []):
                has_row = "row_span" in record
                has_col = "column_span" in record
                if record["kind"] == "fine_geometry" and not has_row and not has_col:
                    self.diag(
                        "coarse_geometry_ignored",
                        cell_id=cell["cell_id"],
                        detail="bbox without layout span result cannot become a fine cell",
                    )
                    continue
                if "row" in record and int(record["row"]) != cell["row"]:
                    self.diag("provenance_conflict", cell_id=cell["cell_id"])
                    self.provenance_conflict_cells.add(cell["cell_id"])
                    continue
                if "column" in record and int(record["column"]) != cell["column"]:
                    self.diag("provenance_conflict", cell_id=cell["cell_id"])
                    self.provenance_conflict_cells.add(cell["cell_id"])
                    continue
                if has_row:
                    span = record["row_span"]
                    if span is not None and (not _is_index(span) or span < 1):
                        raise ValueError(f"cell {cell['cell_id']!r} has illegal provenance row_span")
                    if eff_row_span is not None and span is not None and eff_row_span != span:
                        self.diag("provenance_conflict", cell_id=cell["cell_id"])
                        self.provenance_conflict_cells.add(cell["cell_id"])
                    elif span is not None:
                        eff_row_span = int(span)
                if has_col:
                    span = record["column_span"]
                    if span is not None and (not _is_index(span) or span < 1):
                        raise ValueError(f"cell {cell['cell_id']!r} has illegal provenance column_span")
                    if eff_col_span is not None and span is not None and eff_col_span != span:
                        self.diag("provenance_conflict", cell_id=cell["cell_id"])
                        self.provenance_conflict_cells.add(cell["cell_id"])
                    elif span is not None:
                        eff_col_span = int(span)
            cell["eff_row_span"] = eff_row_span
            cell["eff_col_span"] = eff_col_span

        occupancy: dict[tuple[int, int], str] = {}
        for cell in self.cells:
            if cell["presence"] not in ("present", "empty"):
                continue
            row_span = cell["eff_row_span"] or 1
            col_span = cell["eff_col_span"] or 1
            for rr in range(cell["row"], cell["row"] + row_span):
                for cc in range(cell["column"], cell["column"] + col_span):
                    self.budget.charge(1)
                    other = occupancy.get((rr, cc))
                    if other is not None:
                        self.conflicted_cells.add(cell["cell_id"])
                        self.conflicted_cells.add(other)
                        cell["conflict"] = True
                        self.diag("slot_conflict", cell_id=cell["cell_id"], row=rr, column=cc)
                    else:
                        occupancy[(rr, cc)] = cell["cell_id"]
        if self.conflicted_cells:
            for cell in self.cells:
                if cell["cell_id"] in self.conflicted_cells:
                    cell["conflict"] = True

    def build_columns(self) -> None:
        max_col = -1
        covered: set[int] = set()
        for cell in self.cells:
            width = cell["eff_col_span"] or 1
            max_col = max(max_col, cell["column"] + width - 1)
            covered.update(range(cell["column"], cell["column"] + width))
        for native in range(0, max_col + 1):
            self.budget.charge(1)
            path: list[tuple[str, int, int]] = []
            header_cells = [
                cell
                for cell in self.cells
                if cell["row"] in self.header_rows
                and cell["column"] <= native < cell["column"] + (cell["eff_col_span"] or 1)
            ]
            header_cells.sort(key=lambda c: (c["row"], c["column"], c["cell_id"]))
            seen: set[tuple[str, int, int]] = set()
            for cell in header_cells:
                for ref in cell["text_refs"] + cell["header_refs"]:
                    if ref not in seen:
                        seen.add(ref)
                        path.append(ref)

            label_texts = [
                self.unit_text[uid][s:e] for uid, s, e in path
            ]
            period, conflicted = _periods.combine([_periods.parse_label(t) for t in label_texts])
            period["raw_label_refs"] = [_ref_dict(ref) for ref in path]
            self.column_paths[native] = path
            self.column_periods[native] = period
            if not path:
                self.column_status[native] = "unavailable"
                self.diag("no_header_path", native_column=native)
            elif conflicted:
                self.column_status[native] = "ambiguous"
                self.diag("header_period_conflict", native_column=native)
            else:
                self.column_status[native] = "bound"
                if period["kind"] == _periods.KIND_UNSPECIFIED:
                    self.diag("period_not_disclosed", native_column=native)
            if native not in covered:
                self.diag("column_without_cells", native_column=native)
            self.columns_out.append(
                {
                    "column_id": f"col-{native}",
                    "native_column": native,
                    "header_refs": [_ref_dict(ref) for ref in path],
                    "period": period,
                    "status": self.column_status[native],
                }
            )

    # -- measurements ------------------------------------------------------
    def bind_measurements(self) -> None:
        ordered = sorted(self.cells, key=lambda c: (c["row"], c["column"], c["cell_id"]))
        for cell in ordered:
            if cell["row"] in self.header_rows:
                continue
            if not cell["text_refs"]:
                if cell["presence"] == "present":
                    self.diag("value_text_unavailable", cell_id=cell["cell_id"])
                continue
            for ref in cell["text_refs"]:
                if ref in self.label_refs:
                    continue
                self.budget.charge(1)
                self.measurements_out.append(self._bind_one(cell, ref))

    def _bind_one(self, cell: Mapping, ref: tuple[str, int, int]) -> dict:
        uid, start, end = ref
        value_text = self.unit_text[uid][start:end]
        unit_row = self.units_view[uid]
        status = "bound"
        column_id: str | None = None
        period: dict | None = None

        def fail(new_status: str, code: str | None = None, **fields: Any) -> None:
            nonlocal status
            status = new_status
            if code is not None:
                self.diag(code, cell_id=cell["cell_id"], **fields)

        if not value_text.strip():
            fail("unavailable", "value_text_unavailable")
        elif cell["presence"] in ("empty", "unavailable"):
            fail("unavailable", "slot_value_conflict")
        elif cell["presence"] == "merged_unknown":
            fail("ambiguous", "merged_value_no_column")
        elif unit_row.get("parent_id") != self.scope_parent:
            fail("ambiguous", "cross_parent_ref")
        else:
            locator = unit_row.get("locator")
            loc_page = locator.get("page_number") if isinstance(locator, Mapping) else None
            if self.scope_page is not None and loc_page is not None and loc_page != self.scope_page:
                fail("ambiguous", "cross_page_ref")
        if status == "bound":
            col_span = cell["eff_col_span"]
            if col_span is not None and col_span != 1:
                fail("ambiguous", "multi_column_value")
        if status == "bound" and cell.get("conflict"):
            status = "ambiguous"
        if status == "bound" and cell["cell_id"] in self.provenance_conflict_cells:
            status = "ambiguous"

        native = cell["column"]
        if status != "bound":
            column_id = None
        else:
            column_id = f"col-{native}"
            col_state = self.column_status.get(native, "unavailable")
            if col_state == "ambiguous":
                fail("ambiguous", None)
            elif col_state == "unavailable":
                fail("ambiguous", "no_header_path")
            elif native in self.column_periods:
                period = self.column_periods[native]

        path = self.column_paths.get(native, [])
        path_set = set(path)
        row_label_refs = [
            r for r in cell["header_refs"] if r not in path_set
        ]
        row_texts = [self.unit_text[u][s:e] for u, s, e in row_label_refs]
        path_texts = [self.unit_text[u][s:e] for u, s, e in path]

        row_units: list[dict] = []
        row_scopes: list[dict] = []
        row_quals: list[dict] = []
        for r, text in zip(row_label_refs, row_texts):
            u_, s_, q_ = _labels.scan_label(_ref_dict(r), text)
            row_units.extend(u_)
            row_scopes.extend(s_)
            row_quals.extend(q_)
        path_units: list[dict] = []
        path_scopes: list[dict] = []
        path_quals: list[dict] = []
        for r, text in zip(path, path_texts):
            u_, s_, q_ = _labels.scan_label(_ref_dict(r), text)
            path_units.extend(u_)
            path_scopes.extend(s_)
            path_quals.extend(q_)
        cell_units = _labels.scan_value(_ref_dict(ref), value_text)

        unit_refs = cell_units or row_units or path_units
        scope_refs = _labels.dedupe(row_scopes + path_scopes)
        qualifier_refs = _labels.dedupe(row_quals + path_quals)

        period_out = None
        if period is not None:
            period_out = {
                **period,
                "raw_label_refs": [dict(r) for r in period["raw_label_refs"]],
            }
        return {
            "value_ref": _ref_dict(ref),
            "row_label_refs": [_ref_dict(r) for r in row_label_refs],
            "column_id": column_id,
            "period": period_out,
            "unit_refs": unit_refs,
            "scope_refs": scope_refs,
            "qualifier_refs": qualifier_refs,
            "binding_status": status,
        }

    # -- driver -------------------------------------------------------------
    def run(self) -> dict:
        try:
            self.validate()
            self.index_slots()
            self.build_columns()
            self.bind_measurements()
        except WorkBudgetExceeded:
            self.exhausted = True
            self.blocked = True
            self.diag("work_budget_exhausted")

        if self.scope_page is None:
            self.diag("page_not_observed")
        if bool(self.observation.get("truncated", False)):
            self.diag("observation_truncated")
            self.blocked = True

        counts = {"bound": 0, "ambiguous": 0, "unavailable": 0}
        for m in self.measurements_out:
            counts[m["binding_status"]] += 1
        blocking = self.exhausted or self.blocked or any(
            d["code"] in BLOCKING_CODES for d in self.diagnostics
        )
        if not blocking and self.measurements_out and counts["bound"] == len(self.measurements_out):
            status = "complete"
        elif not blocking and counts["bound"] == 0 and counts["ambiguous"] == 0:
            status = "unavailable"
        else:
            status = "partial"

        unbound = [
            m["value_ref"] for m in self.measurements_out if m["binding_status"] != "bound"
        ]
        scope = self.observation.get("scope")
        assert isinstance(scope, Mapping)
        return {
            "schema_version": SCHEMA_OUT,
            "scope": {
                "parent_id": scope.get("parent_id"),
                "table_id": scope.get("table_id"),
                "page": scope.get("page"),
            },
            "status": status,
            "columns": self.columns_out,
            "measurements": self.measurements_out,
            "unbound_value_refs": unbound,
            "diagnostics": self.diagnostics,
            "work_used": self.budget.used - self.start_used,
        }


def bind_operating_table(observation: Mapping, *, work_budget: WorkBudget) -> dict:
    return _Binder(observation, work_budget).run()
