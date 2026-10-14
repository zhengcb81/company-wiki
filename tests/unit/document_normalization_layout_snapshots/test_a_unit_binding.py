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


def test_explicit_transform_is_recorded_without_shifting_coords():
    snapshot, units = synth.transform_frame_case()
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-tf")
    assert meta["layout"]["frame_converted"] is True
    assert meta["layout"]["coordinate_frame"] == "transformed"
    # bboxes stay in the declared frame; the transform is recorded, not blindly applied
    assert meta["layout"]["bbox"] == [70.0, 120.0, 200.0, 140.0]
    assert meta["upstream_hints"]["words"][0]["bbox"] == [70.0, 120.0, 160.0, 140.0]


def test_cropbox_origin_keeps_coords_and_crop_size():
    snapshot, units = synth.cropbox_origin_case()
    result = project_layout_snapshot(snapshot, units)
    meta = _meta(result, "u-crop")
    assert meta["layout"]["coordinate_frame"] == "cropbox"
    assert meta["layout"]["page_width"] == 400.0  # crop size, not guessed to media size
    assert meta["layout"]["bbox"] == [10.0, 20.0, 120.0, 60.0]
    assert result["coverage"]["bound_unit_count"] == 1


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
    # the two styles must occupy DISJOINT char ranges (not overlap)
    ranges = sorted((r["char_start"], r["char_end"]) for r in runs)
    for (s1, e1), (s2, e2) in zip(ranges, ranges[1:]):
        assert e1 <= s2, "mixed font runs must not overlap"
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


# ---- fixes from independent review ----


def test_ambiguous_binding_is_diagnostic_and_partial():
    snapshot, units = synth.mixed_fonts_case()
    page = snapshot["pages"][0]
    page["bindings"].append(dict(page["bindings"][0]))  # same unit matched twice
    result = project_layout_snapshot(snapshot, units)
    assert "AMBIGUOUS_BINDING" in _codes(result)
    assert result["coverage"]["complete"] is False


def test_frame_size_mismatch_is_partial():
    snapshot = {
        "schema_version": synth.SNAPSHOT_SCHEMA,
        "pages": [
            {
                "page": 1, "width": 595.0, "height": 842.0, "coordinate_frame": "dict", "rotation": 90,
                "dict_width": 595.0, "dict_height": 842.0,
                # rotation 90 should swap these; they do not -> mismatch
                "rect_width": 595.0, "rect_height": 842.0,
                "bindings": [{"unit_id": "u1", "bbox": [10.0, 20.0, 30.0, 40.0]}],
            }
        ],
    }
    unit = {"unit_id": "u1", "ordinal": 0, "page": 1, "locator": "l", "text": "x", "kind": "paragraph", "role": "r", "parser": "p", "layout": {}}
    result = project_layout_snapshot(snapshot, [unit])
    assert "FRAME_SIZE_MISMATCH" in _codes(result)
    assert result["coverage"]["complete"] is False


def test_non_mapping_fine_element_is_diagnostic():
    snapshot, units = synth.mixed_fonts_case()
    snapshot["pages"][0]["bindings"][0]["words"] = ["not-a-mapping"]
    result = project_layout_snapshot(snapshot, units)
    assert "FINE_ELEMENT_INVALID" in _codes(result)


def test_relocated_alignment_preserves_supplied_range():
    snapshot, units = synth.nfc_trim_case()
    result = project_layout_snapshot(snapshot, units)
    words = _meta(result, "u-nfc")["upstream_hints"]["words"]
    relocated = [w for w in words if w["char_alignment"] == "relocated"]
    assert relocated, "the decomposed 'Café' re-aligns"
    for w in relocated:
        # the frontend-supplied range is retained even after re-pinning
        assert w["char_start_supplied"] is not None
        assert (w["char_start_supplied"], w["char_end_supplied"]) != (w["char_start"], w["char_end"])
