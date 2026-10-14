"""Node A (RED first): fine-element ``unit_binding`` counterexamples.

Each test pins one behaviour the card requires: real source positions survive,
whole-row/whole-block boxes are never copied into fine cells, repeated text in
different blocks is not merged, mixed fonts bind to char ranges, rotation frames
are not silently mixed, and the projection infers no column lane / table relation.
"""

from __future__ import annotations

import pytest

import synth
from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot


def _meta(result, unit_id):
    return result["unit_metadata"][unit_id]


def _codes(result):
    return {d["code"] for d in result["diagnostics"]}


# ------------------------------------------------------------------ rotation frame


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rotation_frames_are_recorded_not_guessed(rotation):
    snapshot, units = synth.rotation_frame_case(rotation)
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-rot")
    layout = meta["layout"]
    assert layout["rotation"] == rotation
    assert layout["coordinate_frame"] == "dict"
    # physical size is NOT invented: the declared dict frame size is preserved
    assert layout["page_width"] == pytest.approx(595.0)
    assert layout["page_height"] == pytest.approx(842.0)
    # the binding's own real bbox survives unchanged
    assert layout["bbox"] == [70.0, 120.0, 200.0, 140.0]


def test_unknown_frame_is_partial_and_does_not_guess_size():
    snapshot, units = synth.unknown_frame_case()
    result = project_layout_snapshot(snapshot, units)
    assert result["coverage"]["complete"] is False
    assert "u-uf" in result["coverage"]["unknown_frame_unit_ids"]
    assert "UNKNOWN_COORDINATE_FRAME" in _codes(result)
    meta = _meta(result, "u-uf")
    # geometry still readable but frame is explicitly unknown, size not guessed
    assert meta["layout"]["coordinate_frame"] is None
    assert meta["layout"]["bbox"] == [70.0, 120.0, 200.0, 140.0]


# ------------------------------------------------------------------ font / text binding


def test_mixed_font_runs_bind_to_disjoint_char_ranges():
    snapshot, units = synth.mixed_fonts_case()
    result = project_layout_snapshot(snapshot, units)
    runs = _meta(result, "u-fonts")["upstream_hints"]["font_runs"]
    sizes = {r["font_size"] for r in runs}
    assert 14.0 in sizes and 10.0 in sizes
    for r in runs:
        assert r["char_start"] < r["char_end"]
        assert r.get("char_alignment") in {"exact", "relocated", "unknown"}
    # the unit's original text is preserved verbatim
    assert _meta(result, "u-fonts")["layout"] is not None


def test_cross_line_words_keep_distinct_y_offsets():
    snapshot, units = synth.cross_line_offset_case()
    result = project_layout_snapshot(snapshot, units)
    words = _meta(result, "u-cross")["upstream_hints"]["words"]
    assert len(words) == 5
    ys = {round(w["bbox"][1], 1) for w in words}
    assert len(ys) >= 2, "words on two lines must keep distinct y offsets"


def test_nfc_trim_misalignment_records_unknown_without_touching_text():
    snapshot, units = synth.nfc_trim_case()
    unit_text_before = units[0]["text"]
    result = project_layout_snapshot(snapshot, units)
    words = _meta(result, "u-nfc")["upstream_hints"]["words"]
    aligns = {w.get("char_alignment") for w in words}
    assert "relocated" in aligns, "the decomposed 'Café' re-aligns uniquely"
    assert "unknown" in aligns, "the ambiguous 'x' range must be reported unknown, not guessed"
    assert units[0]["text"] == unit_text_before
    # geometry survives even when char range is unknown
    assert all(len(w["bbox"]) == 4 for w in words)
    assert _meta(result, "u-nfc")["layout"]["bbox"] == [70.0, 100.0, 200.0, 120.0]


def test_repeated_text_in_two_blocks_is_not_merged():
    snapshot, units = synth.repeated_text_two_blocks_case()
    result = project_layout_snapshot(snapshot, units)
    # two distinct unit_metadata entries, each with its own real geometry
    assert "u-rep-1" in result["unit_metadata"]
    assert "u-rep-2" in result["unit_metadata"]
    w1 = _meta(result, "u-rep-1")["upstream_hints"]["words"][0]
    w2 = _meta(result, "u-rep-2")["upstream_hints"]["words"][0]
    assert w1["bbox"] == [70.0, 100.0, 130.0, 118.0]
    assert w2["bbox"] == [70.0, 300.0, 130.0, 318.0]
    assert w1["bbox"] != w2["bbox"], "identical text in different blocks keeps separate geometry"


# ------------------------------------------------------------------ bad / missing geometry


def test_missing_binding_bbox_and_inverted_element_bbox_are_diagnostics():
    snapshot, units = synth.missing_bad_bbox_case()
    result = project_layout_snapshot(snapshot, units)
    codes = _codes(result)
    assert "MISSING_BINDING_BBOX" in codes
    assert "BAD_ELEMENT_BBOX" in codes
    meta = _meta(result, "u-badbbox")
    assert meta["layout"]["bbox"] is None
    assert meta["upstream_hints"]["words"] == [], "no illegal bbox becomes fine geometry"


def test_wrong_page_and_missing_unit_are_specific_diagnostics():
    snapshot, units = synth.wrong_page_missing_unit_case()
    result = project_layout_snapshot(snapshot, units)
    codes = _codes(result)
    assert "WRONG_PAGE" in codes
    assert "MISSING_UNIT" in codes
    # the ghost unit is not a caller unit so it must not appear in unit_metadata
    assert "u-ghost" not in result["unit_metadata"]


# ------------------------------------------------------------------ granularity & no-inference


def test_row_cells_strings_are_not_fine_geometry():
    snapshot, units = synth.no_fine_cells_whole_row_case()
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-row")
    assert meta["upstream_hints"]["cells"] == []
    assert meta["upstream_hints"]["words"] == []
    assert meta["layout"]["granularity"] in {"row", "block", "table_region"}
    assert "NO_FINE_GEOMETRY" in _codes(result)


def test_real_cells_keep_row_col_table_id_and_fine_granularity():
    snapshot, units = synth.real_cells_granularity_case()
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-cells")
    assert meta["layout"]["granularity"] == "cell"
    cells = meta["upstream_hints"]["cells"]
    assert len(cells) == 3
    assert {(c["row"], c["column"]) for c in cells} == {(0, 0), (0, 1), (0, 2)}
    assert {c["table_id"] for c in cells} == {"p1:t0"}
    # each cell keeps its OWN bbox, never the parent row/block bbox
    parent = meta["layout"]["bbox"]
    for c in cells:
        assert c["bbox"] != parent


def test_projection_infers_no_column_lane_or_table_relation():
    snapshot, units = synth.two_column_units_case()
    result = project_layout_snapshot(snapshot, units)
    for meta in result["unit_metadata"].values():
        hints = meta["hints"]
        assert "column_lane" not in hints
        assert "text_column" not in hints
        assert "heading_level" not in hints
        assert "table_id" not in hints
        uh = meta["upstream_hints"]
        assert "relations" not in uh
        assert "header_for" not in repr(uh)


def test_frontend_without_geometry_stays_unknown():
    snapshot, units = synth.frontend_no_geometry_case()
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-html")
    assert meta["layout"]["bbox"] is None
    assert meta["layout"]["granularity"] == "unknown"
    assert meta["upstream_hints"]["words"] == []
    assert meta["upstream_hints"]["cells"] == []
    assert "NO_REAL_GEOMETRY" in _codes(result)
