"""Node A (RED first): ``du-layout-snapshot/1`` contract counterexamples.

Covers snapshot schema validation, limits that only tighten, the work budget
(zero / small ceilings stop real work), and strict input immutability.  The
projection is pure with respect to its inputs: it must never mutate the caller's
snapshot or units.
"""

from __future__ import annotations

import copy

import pytest

import synth
from company_wiki.document_normalization.layout_snapshots import (
    DEFAULT_LIMITS,
    PROJECTION_SCHEMA,
    SNAPSHOT_SCHEMA,
    project_layout_snapshot,
    resolve_limits,
)


def test_schema_constants_are_frozen():
    assert SNAPSHOT_SCHEMA == "du-layout-snapshot/1"
    assert PROJECTION_SCHEMA == "du-layout-projection/1"
    assert DEFAULT_LIMITS["max_units"] == 10000
    assert DEFAULT_LIMITS["max_pages"] == 64
    assert DEFAULT_LIMITS["max_fine_elements"] == 200000
    assert DEFAULT_LIMITS["max_work_units"] == 1000000


def test_reject_wrong_snapshot_schema():
    snapshot, units = synth.mixed_fonts_case()
    snapshot["schema_version"] = "du-layout-snapshot/99"
    with pytest.raises(ValueError):
        project_layout_snapshot(snapshot, units)


def test_reject_non_mapping_snapshot():
    _snapshot, units = synth.mixed_fonts_case()
    with pytest.raises(ValueError):
        project_layout_snapshot(["not", "a", "mapping"], units)


def test_limits_only_tighten_never_widen():
    resolved = resolve_limits({"max_units": 5})
    assert resolved["max_units"] == 5
    # an attempt to widen is clamped to the default ceiling
    widened = resolve_limits({"max_units": 10_000_000, "max_work_units": 999_999_999})
    assert widened["max_units"] == DEFAULT_LIMITS["max_units"]
    assert widened["max_work_units"] == DEFAULT_LIMITS["max_work_units"]


def test_reject_invalid_limits():
    with pytest.raises(ValueError):
        resolve_limits({"max_units": -1})
    with pytest.raises(ValueError):
        resolve_limits({"max_work_units": "big"})


def test_zero_work_budget_stops_immediately():
    snapshot, units = synth.large_case(20)
    result = project_layout_snapshot(snapshot, units, limits={"max_work_units": 0})
    codes = {d["code"] for d in result["diagnostics"]}
    assert "WORK_BUDGET_EXCEEDED" in codes
    assert result["coverage"]["complete"] is False
    # no binding may be published under a zero budget
    assert result["coverage"]["bound_unit_count"] == 0


def test_small_work_budget_yields_partial_not_complete():
    snapshot, units = synth.large_case(30)
    result = project_layout_snapshot(snapshot, units, limits={"max_work_units": 12})
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["bound_unit_count"] < 30
    assert "WORK_BUDGET_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
    # anything still bound must be a complete, non-half binding
    for meta in result["unit_metadata"].values():
        assert "layout" in meta and "upstream_hints" in meta


def test_normal_run_binds_every_unit_completely():
    snapshot, units = synth.large_case(30)
    result = project_layout_snapshot(snapshot, units)
    assert result["coverage"]["bound_unit_count"] == 30
    assert result["coverage"]["complete"] is True


def test_max_pages_is_a_count_not_a_page_number_ceiling():
    # real originals use high page numbers (e.g. 223) that must still bind
    snapshot, units = synth.rotation_frame_case(0)
    snapshot["pages"][0]["page"] = 223
    units[0]["page"] = 223
    result = project_layout_snapshot(snapshot, units)
    assert result["coverage"]["bound_unit_count"] == 1
    assert "PAGE_LIMIT_EXCEEDED" not in {d["code"] for d in result["diagnostics"]}


def test_max_pages_count_budget_stops_extra_pages():
    pages = []
    units = []
    for pno in (1, 2, 3):
        snap, un = synth.rotation_frame_case(0)
        page = snap["pages"][0]
        page["page"] = pno
        uid = f"u-{pno}"
        page["bindings"][0]["unit_id"] = uid
        units.append(dict(un[0], unit_id=uid, page=pno))
        pages.append(page)
    snapshot = {"schema_version": synth.SNAPSHOT_SCHEMA, "pages": pages}
    result = project_layout_snapshot(snapshot, units, limits={"max_pages": 1})
    assert "PAGE_LIMIT_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["bound_unit_count"] == 1  # only the first page binds


# ---- fixes from independent review: no false-complete, unit cap really stops ----


def test_complete_never_true_when_incomplete_pages_present():
    # a frame-problem page with zero bindings must still forbid complete
    snapshot = {
        "schema_version": synth.SNAPSHOT_SCHEMA,
        "pages": [
            {"page": 1, "width": 595.0, "height": 842.0, "coordinate_frame": "mystery", "rotation": 0, "bindings": []}
        ],
    }
    result = project_layout_snapshot(snapshot, [])
    assert result["coverage"]["incomplete_pages"] == [1]
    assert result["coverage"]["complete"] is False


def test_unread_page_unit_is_reported_not_complete():
    unit = {"unit_id": "u9", "ordinal": 0, "page": 9, "locator": "loc", "text": "orphan", "kind": "paragraph", "role": "r", "parser": "p", "layout": {}}
    snapshot = {
        "schema_version": synth.SNAPSHOT_SCHEMA,
        "pages": [
            {"page": 1, "width": 595.0, "height": 842.0, "coordinate_frame": "dict", "rotation": 0, "bindings": []}
        ],
    }
    result = project_layout_snapshot(snapshot, [unit])
    assert "UNREAD_PAGE" in {d["code"] for d in result["diagnostics"]}
    assert "u9" in result["coverage"]["unread_page_unit_ids"]
    assert result["coverage"]["complete"] is False


def test_max_units_stops_processing():
    snapshot, units = synth.large_case(6)
    result = project_layout_snapshot(snapshot, units, limits={"max_units": 2})
    assert result["coverage"]["bound_unit_count"] == 2
    assert "UNIT_LIMIT_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
    assert result["coverage"]["complete"] is False


def test_non_string_binding_unit_id_raises_valueerror_not_typeerror():
    snapshot = {
        "schema_version": synth.SNAPSHOT_SCHEMA,
        "pages": [
            {
                "page": 1, "width": 595.0, "height": 842.0, "coordinate_frame": "dict", "rotation": 0,
                "bindings": [{"unit_id": 123, "bbox": [0.0, 0.0, 10.0, 10.0]}],
            }
        ],
    }
    with pytest.raises(ValueError):
        project_layout_snapshot(snapshot, [])


def test_duplicate_unit_ids_are_diagnostic():
    unit = {"unit_id": "u1", "ordinal": 0, "page": 1, "locator": "l", "text": "dup", "kind": "paragraph", "role": "r", "parser": "p", "layout": {}}
    snapshot = {
        "schema_version": synth.SNAPSHOT_SCHEMA,
        "pages": [
            {"page": 1, "width": 595.0, "height": 842.0, "coordinate_frame": "dict", "rotation": 0, "bindings": []}
        ],
    }
    result = project_layout_snapshot(snapshot, [unit, dict(unit)])
    assert "DUPLICATE_UNIT_ID" in {d["code"] for d in result["diagnostics"]}


def test_input_snapshot_and_units_are_not_mutated():
    snapshot, units = synth.mixed_fonts_case()
    snap_before = copy.deepcopy(snapshot)
    units_before = copy.deepcopy(units)
    project_layout_snapshot(snapshot, units)
    assert snapshot == snap_before
    assert units == units_before


def test_every_unit_is_a_target_and_unbound_units_stay_readable():
    snapshot, units = synth.wrong_page_missing_unit_case()
    result = project_layout_snapshot(snapshot, units)
    # all caller units are represented (bound, deferred, or explicitly unbound)
    seen = set(result["unit_metadata"]) | set(result["coverage"]["unbound_unit_ids"]) | set(
        result["coverage"]["deferred_unit_ids"]
    )
    assert seen == {u["unit_id"] for u in units}


def test_output_carries_feature_version_and_no_file_path():
    snapshot, units = synth.mixed_fonts_case()
    result = project_layout_snapshot(snapshot, units)
    assert result["feature_version"]
    flat = repr(result)
    assert ".pdf" not in flat.lower()
    assert "companies/" not in flat
