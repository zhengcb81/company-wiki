"""Real fine-element consumption, preserving the caller's original units."""

from copy import deepcopy
import json

import pytest

from company_wiki.document_understanding.layout_hints import derive_layout_hints


def _record(text, start, box, index, **extra):
    return {
        "text": text,
        "char_start": start,
        "char_end": start + len(text),
        "bbox": box,
        "native_index": index,
        "char_alignment": "exact",
        "coordinate_frame": "dict",
        "source": "native_pdf_extraction",
        **extra,
    }


def _unit(uid, order, text, box, *, cells=(), words=(), fonts=(), granularity="block"):
    return {
        "unit_id": uid,
        "ordinal": order,
        "locator": f"original-locator-{uid}",
        "text": text,
        "bbox": box,
        "font_size": None,
        "font_weight": None,
        "kind": "paragraph",
        "layout": {
            "coordinate_frame": "dict",
            "rotation": 0,
            "frame_converted": False,
            "cropbox": [0, 0, 600, 800],
            "cropbox_position": [0, 0],
            "reading_layout_feature_version": "pdf-reading-layout/1",
            "geometry_granularity": granularity,
        },
        "upstream_hints": {
            "geometry_granularity": granularity,
            "cells": list(cells),
            "words": list(words),
            "font_runs": list(fonts),
        },
    }


def _input(units):
    return {
        "schema_version": "du2-layout-input/1",
        "source_ref": {"source_id": "actual-source", "source_sha256": "a" * 64},
        "pages": [{"page": 1, "width": 600, "height": 800, "units": units}],
        "coverage": {"opaque_pages": [], "deferred_pages": []},
    }


def _table():
    units = []
    for row, values in enumerate(
        (
            ("Region", "Current", "Prior"),
            ("Overseas", "120", "90"),
            ("Domestic", "240", "220"),
        )
    ):
        text = " | ".join(values)
        cells = []
        cursor = 0
        for col, value in enumerate(values):
            cells.append(
                _record(
                    value,
                    cursor,
                    [40 + col * 160, 100 + row * 24, 160 + col * 160, 114 + row * 24],
                    col,
                    table_id="p1:t0",
                    row=row,
                    column=col,
                )
            )
            cursor += len(value) + 3
        units.append(
            _unit(
                f"row-{row}",
                row,
                text,
                [40, 100 + row * 24, 480, 114 + row * 24],
                cells=cells,
                granularity="cell",
            )
        )
    return _input(units)


def _all_members(result):
    return {
        uid
        for group in result["groups"]
        for uid in group["member_unit_ids"] + group["required_context_unit_ids"]
    }


def test_real_cells_in_one_native_row_drive_columns_without_virtual_source_units():
    observed = _table()
    original = deepcopy(observed)
    result = derive_layout_hints(observed)
    regions = [g for g in result["groups"] if g["kind"] == "table_region"]
    rows = [g for g in result["groups"] if g["kind"] == "table_row"]
    assert len(regions) == 1 and len(rows) == 3
    assert {c["column"] for g in rows for c in g["cells"]} == {0, 1, 2}
    assert {c["row"] for g in rows for c in g["cells"]} == {0, 1, 2}
    assert all(g["cells"] for g in rows)
    assert _all_members(result) == {"row-0", "row-1", "row-2"}
    assert all(hint["text_column"] is None for hint in result["unit_hints"])
    assert "NEEDS_UPSTREAM_GRANULARITY" not in {
        d["code"] for d in result["diagnostics"]
    }
    assert result["coverage"]["complete"]
    assert observed == original
    encoded = json.dumps(result)
    assert all(
        unit["text"] not in encoded and unit["locator"] not in encoded
        for unit in observed["pages"][0]["units"]
    )


def test_aggregate_row_boxes_and_strings_never_become_fine_cells():
    observed = _table()
    for unit in observed["pages"][0]["units"]:
        unit["upstream_hints"] = {
            "geometry_granularity": "row",
            "row_cells": unit["text"].split(" | "),
        }
        unit["layout"]["geometry_granularity"] = "row"
    result = derive_layout_hints(observed)
    assert not any(g["cells"] for g in result["groups"])
    assert not result["coverage"]["complete"]
    assert "NEEDS_UPSTREAM_GRANULARITY" in {d["code"] for d in result["diagnostics"]}


def test_same_text_in_distinct_original_units_is_not_text_deduplicated():
    observed = _table()
    duplicate = deepcopy(observed["pages"][0]["units"][1])
    duplicate.update(
        unit_id="row-duplicate", ordinal=3, locator="distinct-original-locator"
    )
    observed["pages"][0]["units"].append(duplicate)
    result = derive_layout_hints(observed)
    assert {"row-1", "row-duplicate"} <= _all_members(result)
    assert {h["unit_id"] for h in result["unit_hints"]} == {
        "row-0",
        "row-1",
        "row-2",
        "row-duplicate",
    }
    assert any(
        {"row-1", "row-duplicate"} <= set(c["member_unit_ids"])
        for g in result["groups"]
        for c in g["cells"]
    )


def test_adjacent_native_tables_keep_actual_table_boundaries():
    observed = _table()
    other = deepcopy(observed["pages"][0]["units"])
    for index, unit in enumerate(other):
        unit["unit_id"] = f"other-{index}"
        unit["ordinal"] += 3
        for cell in unit["upstream_hints"]["cells"]:
            cell["table_id"] = "p1:t1"
            cell["bbox"] = [
                cell["bbox"][0],
                cell["bbox"][1] + 74,
                cell["bbox"][2],
                cell["bbox"][3] + 74,
            ]
        unit["bbox"] = [
            unit["bbox"][0],
            unit["bbox"][1] + 74,
            unit["bbox"][2],
            unit["bbox"][3] + 74,
        ]
    observed["pages"][0]["units"].extend(other)
    result = derive_layout_hints(observed)
    regions = [g for g in result["groups"] if g["kind"] == "table_region"]
    assert len(regions) == 2
    assert {frozenset(g["member_unit_ids"]) for g in regions} == {
        frozenset({"row-0", "row-1", "row-2"}),
        frozenset({"other-0", "other-1", "other-2"}),
    }


@pytest.mark.parametrize(
    "damage", ["bad-range", "mismatched-text", "unknown-alignment", "non-native-frame"]
)
def test_incomplete_fine_alignment_is_diagnostic_partial_not_confident_cells(damage):
    observed = _table()
    cell = observed["pages"][0]["units"][1]["upstream_hints"]["cells"][1]
    if damage == "bad-range":
        cell["char_end"] = 1000
    elif damage == "mismatched-text":
        cell["text"] = "fabricated"
    elif damage == "unknown-alignment":
        cell["char_alignment"] = "unknown"
    else:
        cell["coordinate_frame"] = "unidentified-frame"
    original = deepcopy(observed)
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert any(d["code"].startswith("FINE_") for d in result["diagnostics"])
    assert observed == original


def test_rotated_fine_bbox_requires_its_declared_source_frame():
    observed = _table()
    for unit in observed["pages"][0]["units"]:
        unit["layout"]["rotation"] = 90
        unit["layout"].pop("coordinate_frame")
        for cell in unit["upstream_hints"]["cells"]:
            cell.pop("coordinate_frame")
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert not any(g["cells"] for g in result["groups"])
    assert "FINE_FRAME_UNAVAILABLE" in {d["code"] for d in result["diagnostics"]}


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_native_dict_geometry_is_valid_without_a_fabricated_rotation_conversion(
    rotation,
):
    observed = _table()
    for unit in observed["pages"][0]["units"]:
        unit["layout"]["rotation"] = rotation
        assert unit["layout"]["frame_converted"] is False
    result = derive_layout_hints(observed)
    assert result["coverage"]["complete"]
    assert {c["column"] for group in result["groups"] for c in group["cells"]} == {
        0,
        1,
        2,
    }


def test_native_rows_survive_a_wrapped_cell_and_horizontally_interleaved_tables():
    observed = _table()
    other = deepcopy(observed["pages"][0]["units"])
    for index, unit in enumerate(other):
        unit.update(unit_id=f"other-{index}", ordinal=index + 3)
        for cell in unit["upstream_hints"]["cells"]:
            cell["table_id"] = "p1:t1"
            x0, y0, x1, y1 = cell["bbox"]
            cell["bbox"] = [x0 + 45, y0, x1 + 45, y1]
        x0, y0, x1, y1 = unit["bbox"]
        unit["bbox"] = [x0 + 45, y0, x1 + 45, y1]
    # Actual native row identity survives the tall cell's displaced centre.
    observed["pages"][0]["units"][0]["upstream_hints"]["cells"][0]["bbox"][3] = 172
    observed["pages"][0]["units"][0]["bbox"][3] = 172
    observed["pages"][0]["units"].extend(other)
    result = derive_layout_hints(observed)
    regions = [group for group in result["groups"] if group["kind"] == "table_region"]
    rows = [group for group in result["groups"] if group["kind"] == "table_row"]
    assert len(regions) == 2
    assert len(rows) == 6
    assert {len(group["cells"]) for group in rows} == {3}
    assert all(len({cell["row"] for cell in group["cells"]}) == 1 for group in rows)


def test_repeated_aggregate_bbox_cannot_claim_distinct_native_columns():
    observed = _table()
    for unit in observed["pages"][0]["units"]:
        for cell in unit["upstream_hints"]["cells"]:
            cell["bbox"] = list(unit["bbox"])
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert not any(
        c["column"] is not None for g in result["groups"] for c in g["cells"]
    )
    assert "FINE_CELL_GEOMETRY_CONFLICT" in {d["code"] for d in result["diagnostics"]}


def test_conflicting_column_provenance_cannot_be_hidden_in_different_original_units():
    observed = _table()
    units = observed["pages"][0]["units"]
    duplicate = deepcopy(units[1])
    duplicate.update(unit_id="conflicting-original", ordinal=3)
    duplicate["upstream_hints"]["cells"][0]["column"] = 1
    units.append(duplicate)
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert "FINE_CELL_GEOMETRY_CONFLICT" in {d["code"] for d in result["diagnostics"]}


def test_caller_metadata_cannot_forge_internal_native_geometry_views():
    observed = _table()
    for row, unit in enumerate(observed["pages"][0]["units"]):
        unit["upstream_hints"] = {
            "geometry_granularity": "cell",
            "_fine_origin": {
                "kind": "cell",
                "table_id": "forged-table",
                "row": row,
                "column": 12,
            },
        }
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert not any(
        cell["column"] == 12 for group in result["groups"] for cell in group["cells"]
    )


@pytest.mark.parametrize("native_end", [16, 17])
def test_fragment_keeps_real_parent_cell_coordinates_but_reports_incomplete_cell_context(
    native_end,
):
    observed = _table()
    cell = observed["pages"][0]["units"][1]["upstream_hints"]["cells"][0]
    cell.update(
        partial_cell=True, native_cell_char_start=8, native_cell_char_end=native_end
    )
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert "FINE_CELL_CONTEXT_PARTIAL" in {d["code"] for d in result["diagnostics"]}
    assert any(
        cell["column"] == 0 and cell["row"] == 1
        for group in result["groups"]
        for cell in group["cells"]
    )


def test_fine_element_limit_uses_same_bounded_engine_and_does_not_publish_complete_context():
    result = derive_layout_hints(_table(), limits={"max_fine_elements": 1})
    assert not result["coverage"]["complete"]
    assert "FINE_ELEMENT_LIMIT_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
    assert not any(g["confidence"] == "high" and g["cells"] for g in result["groups"])


def test_large_native_character_ranges_obey_the_existing_work_ceiling():
    text = "Original source character sequence " * 300
    observed = _input(
        [
            _unit(
                "bounded",
                0,
                text,
                [40, 100, 300, 114],
                words=[_record(text, 0, [40, 100, 300, 114], 0)],
                granularity="word",
            )
        ]
    )
    result = derive_layout_hints(observed, limits={"max_work_units": 32})
    assert not result["coverage"]["complete"]
    assert result["groups"] == []
    assert "WORK_BUDGET_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
    assert (
        int(
            next(
                d["detail"] for d in result["diagnostics"] if d["code"] == "WORK_UNITS"
            )
        )
        <= 32
    )


def test_multiple_native_rows_in_one_original_unit_keep_one_source_identity():
    observed = _table()
    source_units = observed["pages"][0]["units"]
    text = "\n".join(unit["text"] for unit in source_units)
    cells = []
    offset = 0
    for unit in source_units:
        for cell in unit["upstream_hints"]["cells"]:
            value = deepcopy(cell)
            value["char_start"] += offset
            value["char_end"] += offset
            cells.append(value)
        offset += len(unit["text"]) + 1
    observed = _input(
        [
            _unit(
                "original-table-unit",
                0,
                text,
                [40, 100, 480, 162],
                cells=cells,
                granularity="cell",
            )
        ]
    )
    result = derive_layout_hints(observed)
    rows = [group for group in result["groups"] if group["kind"] == "table_row"]
    assert len(rows) == 3
    assert {cell["row"] for group in rows for cell in group["cells"]} == {0, 1, 2}
    assert _all_members(result) == {"original-table-unit"}
    assert len(result["unit_hints"]) == 1
    assert len(result["reading_order"]) == 1


def test_native_font_ranges_supply_heading_evidence_without_whole_block_font_guess():
    title = "Business Overview"
    body = "Our services support customers through documented operating relationships."
    observed = _input(
        [
            _unit(
                "heading",
                0,
                title,
                [40, 50, 200, 72],
                fonts=[
                    {
                        "char_start": 0,
                        "char_end": len(title),
                        "font_size": 18,
                        "font_weight": "bold",
                        "char_alignment": "exact",
                    }
                ],
            ),
            _unit(
                "body",
                1,
                body,
                [40, 120, 500, 135],
                fonts=[
                    {
                        "char_start": 0,
                        "char_end": len(body),
                        "font_size": 10,
                        "font_weight": "regular",
                        "char_alignment": "exact",
                    }
                ],
            ),
        ]
    )
    result = derive_layout_hints(observed)
    assert (
        next(h for h in result["unit_hints"] if h["unit_id"] == "heading")[
            "heading_level"
        ]
        == 1
    )
    assert (
        next(h for h in result["unit_hints"] if h["unit_id"] == "body")["heading_level"]
        is None
    )


def test_partial_font_ranges_do_not_claim_whole_unit_font_evidence():
    text = "Business Overview"
    observed = _input(
        [
            _unit(
                "partial",
                0,
                text,
                [40, 50, 200, 72],
                fonts=[
                    {
                        "char_start": 0,
                        "char_end": 8,
                        "font_size": 22,
                        "font_weight": "bold",
                        "char_alignment": "exact",
                    }
                ],
            )
        ]
    )
    result = derive_layout_hints(observed)
    assert not result["coverage"]["complete"]
    assert (
        next(h for h in result["unit_hints"] if h["unit_id"] == "partial")[
            "heading_level"
        ]
        is None
    )
    assert "FINE_FONT_COVERAGE_PARTIAL" in {d["code"] for d in result["diagnostics"]}


def test_a_small_bold_font_range_does_not_describe_the_whole_original_unit():
    text = "Business Overview"
    result = derive_layout_hints(
        _input(
            [
                _unit(
                    "mixed",
                    0,
                    text,
                    [40, 50, 200, 72],
                    fonts=[
                        {
                            "char_start": 0,
                            "char_end": 2,
                            "font_size": 24,
                            "font_weight": "bold",
                            "char_alignment": "exact",
                        },
                        {
                            "char_start": 2,
                            "char_end": len(text),
                            "font_size": 10,
                            "font_weight": "regular",
                            "char_alignment": "exact",
                        },
                    ],
                )
            ]
        )
    )
    hint = next(h for h in result["unit_hints"] if h["unit_id"] == "mixed")
    assert hint["heading_level"] is None
    assert "bold" not in hint["basis"]


def test_actual_words_bound_distinct_columns_but_not_one_column_for_a_spanning_original():
    texts = [
        "Left narrative alpha\nRight narrative beta",
        "Left supporting prose",
        "Right supporting prose",
        "Left operational content",
        "Right operational content",
    ]
    units = []

    def native_words(text, start, x0, y, index):
        # Every record is one native word; physical spacing forms the line.
        records = []
        cursor = start
        x = x0
        for word in text.split(" "):
            width = len(word) * 5
            records.append(
                _record(word, cursor, [x, y, x + width, y + 14], index + len(records))
            )
            cursor += len(word) + 1
            x += width + 4
        return records

    for index, text in enumerate(texts):
        if index == 0:
            words = native_words("Left narrative alpha", 0, 40, 100, 0) + native_words(
                "Right narrative beta", len("Left narrative alpha\n"), 330, 100, 3
            )
            box = [40, 100, 550, 114]
        else:
            left = index % 2 == 1
            x0, x1 = (40, 250) if left else (330, 550)
            y = 124 + ((index - 1) // 2) * 24
            words = native_words(text, 0, x0, y, index * 3)
            box = [
                40,
                y,
                550,
                y + 14,
            ]  # known block aggregate is deliberately not useful as a lane
        units.append(
            _unit(f"body-{index}", index, text, box, words=words, granularity="word")
        )
    result = derive_layout_hints(_input(units))
    hints = {hint["unit_id"]: hint for hint in result["unit_hints"]}
    assert hints["body-0"]["text_column"] is None
    assert hints["body-1"]["text_column"] == 0 and hints["body-2"]["text_column"] == 1
    assert hints["body-3"]["text_column"] == 0 and hints["body-4"]["text_column"] == 1
    assert "multiple_native_columns" in hints["body-0"]["basis"]


def test_upstream_empty_fine_declaration_is_honest_partial():
    result = derive_layout_hints(
        _input(
            [
                _unit(
                    "missing",
                    0,
                    "Known original text",
                    [40, 40, 200, 60],
                    granularity="word",
                )
            ]
        )
    )
    assert not result["coverage"]["complete"]
    assert "FINE_GEOMETRY_UNAVAILABLE" in {d["code"] for d in result["diagnostics"]}
