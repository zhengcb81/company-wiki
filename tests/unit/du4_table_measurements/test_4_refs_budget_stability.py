"""Contract tests: structural errors, conflicting slots, work budget,
immutability, determinism and the frozen output shape."""

from __future__ import annotations

import copy
import json

import pytest

from .builders import cell, diagnostic_codes, measurement_for, observation, text_ref, unit

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)
from company_wiki.document_understanding.table_measurements import bind_operating_table


def budget(n: int = 10_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


OUT_KEYS = {
    "schema_version",
    "scope",
    "status",
    "columns",
    "measurements",
    "unbound_value_refs",
    "diagnostics",
    "work_used",
}
COLUMN_KEYS = {"column_id", "native_column", "header_refs", "period", "status"}
MEASUREMENT_KEYS = {
    "value_ref",
    "row_label_refs",
    "column_id",
    "period",
    "unit_refs",
    "scope_refs",
    "qualifier_refs",
    "binding_status",
}
PERIOD_KEYS = {"kind", "raw_label_refs", "start", "end", "duration_months", "fiscal_label"}


def _simple_obs() -> dict:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    u_v = unit("u-v", "42")
    return observation(
        {"u-h": u_h, "u-v": u_v},
        [
            cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
            cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
            cell("v", 2, 1, presence="present", text_refs=[text_ref("u-v", u_v["text"], "42")]),
        ],
        header_rows=[0, 1],
    )


def test_output_shape_is_the_frozen_contract() -> None:
    obs = _simple_obs()
    result = bind_operating_table(obs, work_budget=budget())
    assert set(result) == OUT_KEYS
    assert result["schema_version"] == "du4-table-bindings/1"
    assert result["scope"] == obs["scope"]
    assert result["status"] in {"complete", "partial", "unavailable"}
    for c in result["columns"]:
        assert set(c) == COLUMN_KEYS
        assert set(c["period"]) == PERIOD_KEYS
    for m in result["measurements"]:
        assert set(m) == MEASUREMENT_KEYS
        assert m["binding_status"] in {"bound", "ambiguous", "unavailable"}
        if m["period"] is not None:
            assert set(m["period"]) == PERIOD_KEYS
    assert isinstance(result["work_used"], int)
    json.dumps(result)  # JSON-serializable


def test_unknown_schema_and_malformed_refs_raise_value_error() -> None:
    obs = _simple_obs()
    bad = copy.deepcopy(obs)
    bad["schema_version"] = "du4-table-observation/999"
    with pytest.raises(ValueError):
        bind_operating_table(bad, work_budget=budget())

    oob = copy.deepcopy(obs)
    oob["cells"][2]["text_refs"] = [{"unit_id": "u-v", "char_start": 0, "char_end": 99}]
    with pytest.raises(ValueError):
        bind_operating_table(oob, work_budget=budget())

    missing_unit = copy.deepcopy(obs)
    missing_unit["cells"][2]["text_refs"] = [{"unit_id": "nope", "char_start": 0, "char_end": 1}]
    with pytest.raises(ValueError):
        bind_operating_table(missing_unit, work_budget=budget())

    empty_range = copy.deepcopy(obs)
    empty_range["cells"][2]["text_refs"] = [{"unit_id": "u-v", "char_start": 1, "char_end": 1}]
    with pytest.raises(ValueError):
        bind_operating_table(empty_range, work_budget=budget())


def test_duplicate_cell_ids_and_illegal_indices_raise_value_error() -> None:
    obs = _simple_obs()
    dup = copy.deepcopy(obs)
    dup["cells"][2]["cell_id"] = "h0"
    with pytest.raises(ValueError):
        bind_operating_table(dup, work_budget=budget())

    neg = copy.deepcopy(obs)
    neg["cells"][2]["row"] = -1
    with pytest.raises(ValueError):
        bind_operating_table(neg, work_budget=budget())

    bad_span = copy.deepcopy(obs)
    bad_span["cells"][2]["column_span"] = 0
    with pytest.raises(ValueError):
        bind_operating_table(bad_span, work_budget=budget())

    bad_presence = copy.deepcopy(obs)
    bad_presence["cells"][2]["presence"] = "mystery"
    with pytest.raises(ValueError):
        bind_operating_table(bad_presence, work_budget=budget())

    bad_prov = copy.deepcopy(obs)
    bad_prov["provenance"] = [{"cell_id": "v", "kind": "photo"}]
    with pytest.raises(ValueError):
        bind_operating_table(bad_prov, work_budget=budget())

    bad_prov_cell = copy.deepcopy(obs)
    bad_prov_cell["provenance"] = [{"cell_id": "ghost", "kind": "native_slot", "column_span": 1}]
    with pytest.raises(ValueError):
        bind_operating_table(bad_prov_cell, work_budget=budget())


def test_conflicting_slots_are_diagnosed_not_merged() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    u_v = unit("u-v", "42 43")
    v1 = text_ref("u-v", u_v["text"], "42")
    v2 = text_ref("u-v", u_v["text"], "43")
    obs = observation(
        {"u-h": u_h, "u-v": u_v},
        [
            cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
            cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
            cell("a", 2, 1, presence="present", text_refs=[v1]),
            cell("b", 2, 1, presence="present", text_refs=[v2]),
        ],
        header_rows=[0, 1],
    )
    result = bind_operating_table(obs, work_budget=budget())
    assert "slot_conflict" in diagnostic_codes(result)
    statuses = sorted(m["binding_status"] for m in result["measurements"])
    assert statuses == ["ambiguous", "ambiguous"]


def test_input_is_never_modified_and_output_is_deterministic() -> None:
    obs = _simple_obs()
    snapshot = copy.deepcopy(obs)
    r1 = bind_operating_table(obs, work_budget=budget())
    assert obs == snapshot
    r2 = bind_operating_table(copy.deepcopy(obs), work_budget=budget())
    assert r1 == r2
    assert r1["work_used"] == r2["work_used"]


def test_zero_budget_returns_explicit_partial_without_work() -> None:
    obs = _simple_obs()
    b = WorkBudget(max_work_units=0)
    result = bind_operating_table(obs, work_budget=b)
    assert result["status"] == "partial"
    assert "work_budget_exhausted" in diagnostic_codes(result)
    assert result["work_used"] == 0
    assert b.used == 0


def test_small_budget_keeps_determined_results_and_reports_partial() -> None:
    obs = _simple_obs()
    b = WorkBudget(max_work_units=1)
    result = bind_operating_table(obs, work_budget=b)
    assert result["status"] == "partial"
    assert "work_budget_exhausted" in diagnostic_codes(result)
    assert result["work_used"] <= b.max_work_units
    for m in result["measurements"]:
        assert m["binding_status"] in {"bound", "ambiguous", "unavailable"}
    with pytest.raises(WorkBudgetExceeded):
        b.charge(1)  # the exhausted budget stays exhausted for the caller


def test_internal_diagnostics_are_named_not_silent() -> None:
    u_h = unit("u-h", "2024", kind="table_header")
    u_v = unit("u-v", "42")
    value = text_ref("u-v", u_v["text"], "42")
    obs = observation(
        {"u-h": u_h, "u-v": u_v},
        [
            cell("h1", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
            # present cell whose text was not retained: diagnosed, not bound
            cell("lost", 1, 3, presence="present", text_refs=[]),
            # empty slot carrying a contradictory ref: diagnosed, not zeroed
            cell("weird", 2, 1, presence="empty", text_refs=[value]),
            # gap at native column 2 between cells at 1 and 3
        ],
        header_rows=[0],
    )
    result = bind_operating_table(obs, work_budget=budget())
    codes = diagnostic_codes(result)
    assert "value_text_unavailable" in codes
    assert "slot_value_conflict" in codes
    assert "period_not_disclosed" in codes  # bare '2024' header discloses no period kind
    assert "column_without_cells" in codes  # native column 2 has no cells at all
    m = measurement_for(result, value)
    assert m["binding_status"] == "unavailable"


def test_work_is_bounded_linearly_on_large_inputs() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    units = {"u-h": u_h}
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
        cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
    ]
    n = 200
    for i in range(n):
        uid = f"u-{i}"
        units[uid] = unit(uid, f"{i}")
        cells.append(cell(f"v{i}", i + 2, 1, presence="present", text_refs=[text_ref(uid, str(i), str(i))]))
    obs = observation(units, cells, header_rows=[0, 1])
    b = WorkBudget(max_work_units=1_000_000)
    result = bind_operating_table(obs, work_budget=b)
    assert result["status"] == "complete"
    assert len(result["measurements"]) == n
    # linear bound on operations, not a wall-clock threshold
    assert result["work_used"] <= 30 * (len(cells) + n) + 100
    assert result["work_used"] == b.used


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
