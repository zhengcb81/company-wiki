"""Synthetic ``du-layout-snapshot/1`` builders for DU3-GEOMETRY contract/binding nodes.

Test-side only.  Every builder returns an in-memory ``(snapshot, units)`` pair in the
frozen DU3/1 wire shapes so the projection can be exercised against the exact
counterexamples the card requires, without touching any original or the filesystem.

Nothing here is a parser: it fabricates already-extracted geometry payloads to
verify that ``project_layout_snapshot`` binds them truthfully or refuses to guess.
"""

from __future__ import annotations

from typing import Any

SNAPSHOT_SCHEMA = "du-layout-snapshot/1"


def _unit(
    unit_id: str,
    page: int,
    text: str,
    *,
    locator: str | None = None,
    page_width: float | None = None,
    page_height: float | None = None,
    ordinal: int = 0,
    role: str = "company_filing",
    parser: str = "cwp_document_normalization",
) -> dict[str, Any]:
    layout: dict[str, Any] = {}
    if page_width is not None:
        layout["page_width"] = page_width
    if page_height is not None:
        layout["page_height"] = page_height
    return {
        "unit_id": unit_id,
        "ordinal": ordinal,
        "page": page,
        "locator": locator if locator is not None else f"loc:v1/page:{page}",
        "text": text,
        "kind": "paragraph",
        "role": role,
        "parser": parser,
        "layout": layout,
    }


def _page(
    page: int,
    width: float,
    height: float,
    bindings: list,
    *,
    coordinate_frame: str = "dict",
    rotation: int = 0,
    **extra,
) -> dict[str, Any]:
    payload = {
        "page": page,
        "width": width,
        "height": height,
        "coordinate_frame": coordinate_frame,
        "rotation": rotation,
        "bindings": bindings,
    }
    payload.update(extra)
    return payload


def _binding(
    unit_id: str,
    bbox,
    *,
    words=None,
    cells=None,
    font_runs=None,
    source: str = "pdf_dict",
    **extra,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"unit_id": unit_id, "bbox": list(bbox), "source": source}
    if words is not None:
        payload["words"] = words
    if cells is not None:
        payload["cells"] = cells
    if font_runs is not None:
        payload["font_runs"] = font_runs
    payload.update(extra)
    return payload


def _word(text, bbox, *, native_index, char_start=None, char_end=None, **extra):
    w = {"text": text, "bbox": list(bbox), "native_index": native_index}
    if char_start is not None:
        w["char_start"] = char_start
    if char_end is not None:
        w["char_end"] = char_end
    w.update(extra)
    return w


def _cell(text, bbox, *, native_index=0, row=None, column=None, table_id=None, **extra):
    c = {"text": text, "bbox": list(bbox), "native_index": native_index}
    if row is not None:
        c["row"] = row
    if column is not None:
        c["column"] = column
    if table_id is not None:
        c["table_id"] = table_id
    c.update(extra)
    return c


def _font_run(char_start, char_end, *, font_size=None, font_weight=None, font=None):
    return {
        "char_start": char_start,
        "char_end": char_end,
        "font_size": font_size,
        "font_weight": font_weight,
        "font": font,
    }


# --------------------------------------------------------------------------- cases


def rotation_frame_case(rotation: int = 90):
    """Page dict (unrotated) size vs page.rect (rotated) size under a rotation.

    dict frame is the text frame (unrotated).  When rotation is 90/270 the rect
    dimensions are the SWAPPED dict dimensions.  The snapshot carries both so a
    naive same-coordinate association is a counterexample.
    """
    dict_w, dict_h = 595.0, 842.0
    if rotation in (90, 270):
        rect_w, rect_h = dict_h, dict_w
    else:
        rect_w, rect_h = dict_w, dict_h
    unit = _unit(
        "u-rot",
        1,
        "Rotated page body text",
        page_width=dict_w,
        page_height=dict_h,
    )
    binding = _binding(
        "u-rot",
        (70.0, 120.0, 200.0, 140.0),
        words=[_word("Rotated", (70.0, 120.0, 130.0, 140.0), native_index=0, char_start=0, char_end=7)],
        source="pdf_dict",
    )
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "pages": [
            _page(
                1,
                dict_w,
                dict_h,
                [binding],
                coordinate_frame="dict",
                rotation=rotation,
                # both frames declared so the mismatch is observable
                dict_width=dict_w,
                dict_height=dict_h,
                rect_width=rect_w,
                rect_height=rect_h,
            )
        ],
    }
    return snapshot, [unit]


def unknown_frame_case():
    """Page declares an unknown coordinate frame: must stay partial, size not guessed."""
    unit = _unit("u-uf", 1, "Unknown frame body", page_width=595.0, page_height=842.0)
    binding = _binding("u-uf", (70.0, 120.0, 200.0, 140.0), words=[
        _word("Unknown", (70.0, 120.0, 130.0, 140.0), native_index=0)
    ])
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "pages": [_page(1, 595.0, 842.0, [binding], coordinate_frame="mystery_frame", rotation=0)],
    }
    return snapshot, [unit]


def transform_frame_case():
    """Explicit affine transform on the page: conversion is RECORDED, coords kept.

    The binding bboxes are already in the declared frame, so the projection records
    that a transform exists (``frame_converted``) but does NOT silently shift them.
    """
    unit = _unit("u-tf", 1, "Transformed page body", page_width=595.0, page_height=842.0)
    binding = _binding("u-tf", (70.0, 120.0, 200.0, 140.0), words=[
        _word("Transformed", (70.0, 120.0, 160.0, 140.0), native_index=0)
    ])
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "pages": [
            _page(
                1, 595.0, 842.0, [binding],
                coordinate_frame="transformed", rotation=0,
                transform=[1, 0, 0, 1, 10, 20],
            )
        ],
    }
    return snapshot, [unit]


def cropbox_origin_case():
    """Non-zero cropbox/origin: bbox coords are relative to the declared frame.

    The declared size is the crop size (not media size); coordinates are kept
    as-is and in-bounds is judged against the crop frame, never guessed.
    """
    unit = _unit("u-crop", 1, "Cropbox origin body", page_width=400.0, page_height=300.0)
    binding = _binding("u-crop", (10.0, 20.0, 120.0, 60.0), words=[
        _word("Cropbox", (10.0, 20.0, 80.0, 40.0), native_index=0)
    ])
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "pages": [_page(1, 400.0, 300.0, [binding], coordinate_frame="cropbox", rotation=0)],
    }
    return snapshot, [unit]


def mixed_fonts_case():
    """One unit with two font sizes/weights bound to disjoint char ranges."""
    text = "BoldHeader and regular body"
    unit = _unit("u-fonts", 1, text)
    binding = _binding(
        "u-fonts",
        (70.0, 100.0, 320.0, 130.0),
        font_runs=[
            _font_run(0, 10, font_size=14.0, font_weight="bold", font="Helvetica-Bold"),
            _font_run(15, len(text), font_size=10.0, font_weight="regular", font="Helvetica"),
        ],
        words=[
            _word("BoldHeader", (70.0, 100.0, 150.0, 118.0), native_index=0, char_start=0, char_end=10),
            _word("and", (155.0, 104.0, 180.0, 118.0), native_index=1, char_start=11, char_end=14),
            _word("regular", (185.0, 104.0, 235.0, 118.0), native_index=2, char_start=15, char_end=22),
            _word("body", (240.0, 104.0, 275.0, 118.0), native_index=3, char_start=23, char_end=27),
        ],
    )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def cross_line_offset_case():
    """Words on two visual lines inside one binding keep distinct y offsets."""
    text = "first line then second line"
    unit = _unit("u-cross", 1, text)
    binding = _binding(
        "u-cross",
        (70.0, 100.0, 320.0, 160.0),
        words=[
            _word("first", (70.0, 100.0, 110.0, 116.0), native_index=0, char_start=0, char_end=5),
            _word("line", (115.0, 100.0, 150.0, 116.0), native_index=1, char_start=6, char_end=10),
            _word("then", (70.0, 130.0, 105.0, 146.0), native_index=2, char_start=11, char_end=15),
            _word("second", (110.0, 130.0, 165.0, 146.0), native_index=3, char_start=16, char_end=22),
            _word("line", (170.0, 130.0, 205.0, 146.0), native_index=4, char_start=23, char_end=27),
        ],
    )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def nfc_trim_case():
    """Unit text is NFC/trimmed so one char range cannot strictly align.

    ``Cafe\\u0301`` (decomposed) normalizes to ``Café`` and relocates cleanly, but
    the raw ``x`` range is ambiguous because ``xx`` repeats in the unit text, so it
    must be reported ``unknown`` rather than pinned to a guessed offset.
    """
    unit = _unit("u-nfc", 1, "Café xx")
    binding = _binding(
        "u-nfc",
        (70.0, 100.0, 200.0, 120.0),
        # ranges refer to a raw string that no longer matches the unit text offsets
        words=[
            _word("Cafe\u0301", (70.0, 100.0, 130.0, 118.0), native_index=0, char_start=0, char_end=5),
            _word("x", (140.0, 100.0, 150.0, 118.0), native_index=1, char_start=1, char_end=2),
        ],
    )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def repeated_text_two_blocks_case():
    """Identical text in two different blocks must NOT merge into one binding/unit."""
    text = "营收"
    u1 = _unit("u-rep-1", 1, text, ordinal=0)
    u2 = _unit("u-rep-2", 1, text, ordinal=1)
    b1 = _binding("u-rep-1", (70.0, 100.0, 130.0, 118.0), words=[
        _word("营收", (70.0, 100.0, 130.0, 118.0), native_index=0)
    ], source="pdf_dict:block:3")
    b2 = _binding("u-rep-2", (70.0, 300.0, 130.0, 318.0), words=[
        _word("营收", (70.0, 300.0, 130.0, 318.0), native_index=0)
    ], source="pdf_dict:block:9")
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [b1, b2])]}
    return snapshot, [u1, u2]


def missing_bad_bbox_case():
    """Binding without bbox, and one element with an inverted bbox."""
    unit = _unit("u-badbbox", 1, "bad geometry unit")
    b_missing = _binding("u-badbbox", (None, None, None, None), words=[
        _word("bad", (50.0, 40.0, 20.0, 18.0), native_index=0),  # inverted bbox
    ])
    # force bbox to be explicitly missing
    b_missing["bbox"] = None
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [b_missing])]}
    return snapshot, [unit]


def wrong_page_missing_unit_case():
    """One binding points at a wrong page, another at a unit that does not exist."""
    u_present = _unit("u-present", 1, "present unit")
    b_wrong_page = _binding("u-present", (70.0, 100.0, 200.0, 120.0), words=[
        _word("present", (70.0, 100.0, 130.0, 118.0), native_index=0)
    ])
    b_ghost = _binding("u-ghost", (70.0, 400.0, 200.0, 420.0), words=[
        _word("ghost", (70.0, 400.0, 130.0, 418.0), native_index=0)
    ])
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA,
        "pages": [
            _page(1, 595.0, 842.0, [b_wrong_page]),  # unit is on page 1 -> ok
            _page(2, 595.0, 842.0, [b_ghost]),       # u-ghost does not exist
        ],
    }
    # move the present binding to page 2 to force WRONG_PAGE too
    snapshot["pages"][1]["bindings"] = [b_wrong_page, b_ghost]
    snapshot["pages"][0]["bindings"] = []
    return snapshot, [u_present]


def no_fine_cells_whole_row_case():
    """A whole-row bbox plus row_cells strings only -> NOT fine geometry."""
    text = "2023 | 3,926 | 4,386"
    unit = _unit("u-row", 1, text)
    binding = _binding(
        "u-row",
        (70.0, 100.0, 400.0, 118.0),
        source="pdf_table",
        # row_cells strings only: no per-cell bbox -> must NOT become fine cells
        row_cells=["2023", "3,926", "4,386"],
    )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def real_cells_granularity_case():
    """Real per-cell bboxes keep row/column/table_id and fine granularity."""
    text = "2023 3,926 4,386"
    unit = _unit("u-cells", 1, text)
    binding = _binding(
        "u-cells",
        (70.0, 100.0, 400.0, 118.0),
        source="pdf_table",
        cells=[
            _cell("2023", (70.0, 100.0, 130.0, 118.0), row=0, column=0, table_id="p1:t0", native_index=0),
            _cell("3,926", (180.0, 100.0, 250.0, 118.0), row=0, column=1, table_id="p1:t0", native_index=1),
            _cell("4,386", (300.0, 100.0, 370.0, 118.0), row=0, column=2, table_id="p1:t0", native_index=2),
        ],
    )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def frontend_no_geometry_case():
    """HTML/PPTX/OCR binding with only a DOM/shape path, no real coordinates."""
    unit = _unit(
        "u-html",
        1,
        "Paragraph with no geometry",
        parser="cwp_html",
    )
    binding = {
        "unit_id": "u-html",
        "bbox": None,
        "source": "html_dom",
        "dom_path": "0.3.2",
        # no words/cells/font_runs: front end did not provide boxes
    }
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [binding])]}
    return snapshot, [unit]


def two_column_units_case():
    """Two column-lane units on one page: projection must NOT infer column_lane."""
    left = _unit("u-left", 1, "Left column body text here", ordinal=0)
    right = _unit("u-right", 1, "Right column body text here", ordinal=1)
    b_left = _binding("u-left", (60.0, 100.0, 280.0, 400.0), words=[
        _word("Left", (60.0, 100.0, 100.0, 118.0), native_index=0)
    ])
    b_right = _binding("u-right", (315.0, 100.0, 535.0, 400.0), words=[
        _word("Right", (315.0, 100.0, 365.0, 118.0), native_index=0)
    ])
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 842.0, [b_left, b_right])]}
    return snapshot, [left, right]


def large_case(n_units: int = 30):
    """Programmatic many-unit case for budget behaviour (small-work ceilings)."""
    units = []
    bindings = []
    for i in range(n_units):
        uid = f"u-bulk-{i}"
        units.append(_unit(uid, 1, f"unit number {i} body", ordinal=i))
        bindings.append(
            _binding(
                uid,
                (60.0, 60.0 + i * 20.0, 300.0, 78.0 + i * 20.0),
                words=[
                    _word("unit", (60.0, 60.0 + i * 20.0, 100.0, 78.0 + i * 20.0), native_index=0),
                    _word(str(i), (105.0, 60.0 + i * 20.0, 125.0, 78.0 + i * 20.0), native_index=1),
                ],
            )
        )
    snapshot = {"schema_version": SNAPSHOT_SCHEMA, "pages": [_page(1, 595.0, 2000.0, bindings)]}
    return snapshot, [dict(u) for u in units]
