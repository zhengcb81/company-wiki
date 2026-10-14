"""Node B: metadata projection, budget integrity and layout_hints consumer regression.

Confirms the patch is locatable to real units with identity/text/role unchanged,
cell/row/table granularity is accurate, the budget truly stops, and the existing
``layout_hints`` engine still consumes the projected geometry as a read-only
consumer.  Also pins that this package copies none of layout_hints' geometry or
semantic algorithms (no column lane / group / relation inference).
"""

from __future__ import annotations

import copy

import pytest

import synth
from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot


def test_identity_and_text_survive_projection():
    snapshot, units = synth.real_cells_granularity_case()
    units_before = copy.deepcopy(units)
    result = project_layout_snapshot(snapshot, units)
    meta = result["unit_metadata"]["u-cells"]
    # the patch is locatable to the real unit and rewrites nothing
    src = units_before[0]
    assert meta["layout"]["page"] == src["page"]
    # no unit id, locator, text or role is rewritten into the geometry patch
    for key in ("locator", "role", "parser"):
        assert key not in meta["layout"]
        assert key not in meta["hints"]
    assert units == units_before


def test_granularity_refines_from_row_to_cell_only_with_real_bboxes():
    snap_row, u_row = synth.no_fine_cells_whole_row_case()
    res_row = project_layout_snapshot(snap_row, u_row)
    assert res_row["unit_metadata"]["u-row"]["layout"]["granularity"] != "cell"

    snap_cell, u_cell = synth.real_cells_granularity_case()
    res_cell = project_layout_snapshot(snap_cell, u_cell)
    assert res_cell["unit_metadata"]["u-cells"]["layout"]["granularity"] == "cell"


def test_work_units_are_reported_and_bounded():
    snapshot, units = synth.large_case(20)
    result = project_layout_snapshot(snapshot, units)
    work_diag = next(d for d in result["diagnostics"] if d["code"] == "WORK_UNITS")
    assert int(work_diag["detail"]) > 0
    # a tiny ceiling must actually reduce measured work
    small = project_layout_snapshot(snapshot, units, limits={"max_work_units": 5})
    small_work = next(d for d in small["diagnostics"] if d["code"] == "WORK_UNITS")
    assert int(small_work["detail"]) <= 5


def test_layout_hints_consumes_projected_geometry_readonly():
    """The shared engine reads the projection without this package reimplementing it."""
    layout_hints = pytest.importorskip(
        "company_wiki.document_understanding.layout_hints", reason="layout_hints is the read-only consumer"
    )
    snapshot, units = synth.real_cells_granularity_case()
    result = project_layout_snapshot(snapshot, units)
    meta = result["unit_metadata"]["u-cells"]

    # build the du2-layout-input/1 envelope the consumer already understands
    observation = {
        "schema_version": "du2-layout-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "0" * 64},
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": [
            {
                "page": meta["layout"]["page"],
                "width": meta["layout"]["page_width"],
                "height": meta["layout"]["page_height"],
                "units": [
                    {
                        "unit_id": "u-cells",
                        "ordinal": 0,
                        "locator": "loc:v1/page:1",
                        "text": units[0]["text"],
                        "bbox": meta["layout"]["bbox"],
                        "font_size": meta["layout"]["font_size"],
                        "font_weight": meta["layout"]["font_weight"],
                        "kind": "table_row",
                        "upstream_hints": {"geometry_granularity": meta["upstream_hints"]["geometry_granularity"]},
                    }
                ],
            }
        ],
    }
    hints = layout_hints.derive_layout_hints(observation)
    assert hints["schema_version"] == "du2-layout-hints/1"
    # fine granularity is visible to the consumer: no NEEDS_UPSTREAM_GRANULARITY
    assert "NEEDS_UPSTREAM_GRANULARITY" not in {d["code"] for d in hints["diagnostics"]}


def test_coarse_granularity_signals_needs_upstream_to_consumer():
    layout_hints = pytest.importorskip("company_wiki.document_understanding.layout_hints")
    snapshot, units = synth.no_fine_cells_whole_row_case()
    result = project_layout_snapshot(snapshot, units)
    meta = result["unit_metadata"]["u-row"]
    observation = {
        "schema_version": "du2-layout-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "0" * 64},
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": [
            {
                "page": meta["layout"]["page"],
                "width": meta["layout"]["page_width"],
                "height": meta["layout"]["page_height"],
                "units": [
                    {
                        "unit_id": "u-row",
                        "ordinal": 0,
                        "locator": "loc:v1/page:1",
                        "text": units[0]["text"],
                        "bbox": meta["layout"]["bbox"],
                        "font_size": None,
                        "font_weight": None,
                        "kind": "table_row",
                        "upstream_hints": {"geometry_granularity": meta["upstream_hints"]["geometry_granularity"]},
                    }
                ],
            }
        ],
    }
    hints = layout_hints.derive_layout_hints(observation)
    assert "NEEDS_UPSTREAM_GRANULARITY" in {d["code"] for d in hints["diagnostics"]}


def test_package_does_not_copy_layout_hints_algorithms():
    """The projection exposes no lane/group/relation inference of its own."""
    from company_wiki.document_normalization.layout_snapshots import projection, unit_binding, identity, contract

    for mod in (projection, unit_binding, identity, contract):
        src = mod.__file__
        text = open(src, encoding="utf8").read()
        # the package never imports layout_hints' geometry/semantic internals
        for forbidden in ("from ..document_understanding", "layout_hints.columns", "layout_hints.tables", "derive_layout_hints"):
            assert forbidden not in text, f"{mod.__name__} must not reimplement layout_hints"
