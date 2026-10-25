"""An explicit single body lane needs measured page geometry, not no-gap alone."""
from __future__ import annotations

from copy import deepcopy

import pytest

from company_wiki.document_understanding.layout_bridge import apply_layout_hints
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.resource_budget import new_document_work_budget
from unit.document_understanding_selection.test_reading_native_list_ancestry import _source


def _observation():
    rows = [(page, f"Service line {index} expanded capacity for customer demand.", index,
             (90, y, 550, y + 25))
            for page in (1, 2) for index, y in enumerate((100, 260, 460, 680))]
    parsed = _source(rows, known_column=False)
    return build_observation(parsed.units, source_id=parsed.source_id,
        source_sha256=parsed.source_sha256, mime_type="application/pdf")


def _single_groups(layout):
    return [g for g in layout["groups"] if "observed_single_body_lane" in g["basis"]]


def test_measured_single_body_lane_preserves_frozen_numeric_column_hint_contract():
    observed = _observation()
    before = deepcopy(observed)
    mapped, layout = apply_layout_hints(observed, work_budget=new_document_work_budget())
    groups = _single_groups(layout)
    assert len(groups) == 2
    assert all(h["text_column"] is None for h in layout["unit_hints"])
    assert all(u["layout"]["column"] == "observed_single_body_lane" for u in mapped["units"])
    assert all(any(b.startswith("page_geometry_sha256:") for b in g["basis"]) for g in groups)
    assert {uid for g in groups for uid in g["member_unit_ids"]} == {u["unit_id"] for u in observed["units"]}
    assert observed == before
    assert apply_layout_hints(observed, work_budget=new_document_work_budget()) == (mapped, layout)


def test_separated_numeric_table_row_is_not_a_body_alignment_anchor():
    observed = _observation()
    # Coarse native PDF table rows can be paragraph units before table discovery.
    # Their numeric cells must not establish or poison the surrounding prose lane.
    row = deepcopy(observed["units"][0])
    row.update(unit_id="separate-native-value-row", ordinal=99, text="Other services\n(Other)\n120\n100\n20.0")
    row["layout"]["bbox"] = [140, 400, 550, 425]
    observed["units"].append(row)
    mapped, layout = apply_layout_hints(observed, work_budget=new_document_work_budget())
    assert len(_single_groups(layout)) == 2
    assert all(row["unit_id"] not in g["member_unit_ids"] for g in _single_groups(layout))
    assert next(u for u in mapped["units"] if u["unit_id"] == row["unit_id"])["layout"].get("column") is None


def test_nested_indentation_and_ragged_right_edges_can_share_a_measured_body_band():
    observed = _observation()
    for index, unit in enumerate(observed["units"]):
        unit["layout"]["bbox"][0] = (90, 115, 140, 90)[index % 4]
        unit["layout"]["bbox"][2] = (550, 535, 520, 545)[index % 4]
    _mapped, layout = apply_layout_hints(observed, work_budget=new_document_work_budget())
    assert len(_single_groups(layout)) == 2


@pytest.mark.parametrize("mode", ["missing_box", "unknown_frame", "mixed_rotation", "sparse",
    "duplicate_box", "narrow", "overlapping_columns", "staggered_overlapping_columns", "short_band"])
def test_no_gap_and_absent_column_are_not_positive_single_lane_evidence(mode):
    observed = _observation()
    units = observed["units"]
    if mode == "missing_box":
        units[0]["layout"].pop("bbox")
    elif mode == "unknown_frame":
        for unit in units:
            unit["layout"].pop("coordinate_frame")
    elif mode == "mixed_rotation":
        units[0]["layout"]["rotation"] = 90
    elif mode == "sparse":
        observed["units"] = [u for i, u in enumerate(units) if i % 4 < 3]
    elif mode == "duplicate_box":
        for unit in units:
            unit["layout"]["bbox"] = [90, 100, 550, 125]
    elif mode == "narrow":
        for unit in units:
            unit["layout"]["bbox"][2] = 250
    elif mode == "short_band":
        for index, unit in enumerate(units):
            unit["layout"]["bbox"] = [90, 100 + index % 4 * 30, 550, 125 + index % 4 * 30]
    elif mode == "staggered_overlapping_columns":
        for index, unit in enumerate(units):
            x = 60 if index % 2 == 0 else 270
            unit["layout"]["bbox"] = [x, 100 + index % 4 * 180, x + 310, 125 + index % 4 * 180]
    else:
        for index, unit in enumerate(units):
            unit["layout"]["bbox"] = ([90, 100 + index % 2 * 180, 280, 125 + index % 2 * 180]
                if index % 4 < 2 else [330, 100 + index % 2 * 180, 550, 125 + index % 2 * 180])
    mapped, layout = apply_layout_hints(observed, work_budget=new_document_work_budget())
    affected_pages = {u["page"] for u in units if "column" not in u["layout"]}
    # Page2 is unaffected by a deliberately damaged page1. It may have its own
    # witness; no document-global poisoning of valid local geometry is wanted.
    bad_pages = {1} if mode in {"missing_box", "mixed_rotation"} else affected_pages
    ids = {u["unit_id"] for u in units if u["page"] in bad_pages}
    assert not any(ids.intersection(g["member_unit_ids"]) for g in _single_groups(layout))
    assert not any(u["layout"].get("column") == "observed_single_body_lane"
                   for u in mapped["units"] if u["page"] in bad_pages)
