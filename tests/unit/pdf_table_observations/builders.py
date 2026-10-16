"""Synthetic ``du-input/1`` / ``du2-layout-hints/1`` wire builders for the tests.

Everything here mirrors the REAL wire shapes the production parser/adapter emit
(``observation_adapter._FINE_LAYOUT_FIELDS``, ``layout_hints`` groups/relations);
nothing here is read by the component under test.  Row-unit texts and fine-cell
offsets are built exactly like ``PdfLayoutCollector._binding`` builds them for
``pdf_table_row`` units: the row text joins non-empty cells with ``" | "`` and
each cell's char range advances the cursor by ``len(text) + 3``.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def fine_cell(
    text: str,
    start: int,
    end: int,
    *,
    row: int,
    column: int,
    table_id: str,
    page: int = 1,
    alignment: str = "exact",
    frame: str | None = "dict",
    bbox: Sequence[float] = (70.0, 100.0, 120.0, 112.0),
    native_cell_char_start: int | None = None,
    native_cell_char_end: int | None = None,
    partial_cell: bool | None = None,
) -> dict:
    entry: dict[str, Any] = {
        "text": text,
        "bbox": list(bbox),
        "native_index": column,
        "char_start": start,
        "char_end": end,
        "char_start_supplied": start,
        "char_end_supplied": end,
        "char_alignment": alignment,
        "row": row,
        "column": column,
        "table_id": table_id,
        "page": page,
        "coordinate_frame": frame,
        "source": "cell",
    }
    if native_cell_char_start is not None:
        entry["native_cell_char_start"] = native_cell_char_start
    if native_cell_char_end is not None:
        entry["native_cell_char_end"] = native_cell_char_end
    if partial_cell is not None:
        entry["partial_cell"] = partial_cell
    return entry


def row_unit(
    unit_id: str,
    row_cells: Sequence[tuple[int, str]],
    *,
    row: int,
    table_id: str,
    page: int = 1,
    parent: str = "urn:company-wiki:source:sha256:aaaa",
    kind: str = "table_row",
    role: str = "company_filing",
    locator: str | None = None,
    cell_entries: Sequence[Mapping[str, Any]] | None = None,
) -> dict:
    """One ``pdf_table_row`` wire unit; ``row_cells`` are (column, text) slots."""
    ordered = sorted(row_cells, key=lambda item: item[0])
    text = " | ".join(value for _, value in ordered)
    entries: list[dict] = list(cell_entries) if cell_entries is not None else []
    if cell_entries is None:
        cursor = 0
        for column, value in ordered:
            start, end = cursor, cursor + len(value)
            cursor = end + 3
            entries.append(
                fine_cell(value, start, end, row=row, column=column, table_id=table_id, page=page)
            )
    return wire_unit(
        unit_id,
        text,
        page=page,
        parent=parent,
        kind=kind,
        role=role,
        locator=locator or f"loc:v1/page:{page}/table:{table_id}/row:{row}",
        table_id=table_id,
        row=row,
        cells=entries,
    )


def wire_unit(
    unit_id: str,
    text: str,
    *,
    page: int = 1,
    parent: str = "urn:company-wiki:source:sha256:aaaa",
    kind: str = "paragraph",
    role: str = "company_filing",
    locator: str = "loc:v1/page:1/paragraph:1",
    table_id: str | None = None,
    row: int | None = None,
    column: int | None = None,
    cells: Sequence[Mapping[str, Any]] | None = None,
    words: Sequence[Mapping[str, Any]] | None = None,
) -> dict:
    hints: dict[str, Any] = {"source_id": parent}
    if table_id is not None:
        hints["table_id"] = table_id
    if row is not None:
        hints["row"] = row
    if column is not None:
        hints["column"] = column
    if cells is not None:
        hints["cells"] = [dict(entry) for entry in cells]
    if words is not None:
        hints["words"] = [dict(entry) for entry in words]
    return {
        "unit_id": unit_id,
        "ordinal": 0,
        "locator": locator,
        "page": page,
        "text": text,
        "kind": kind,
        "language": "zh",
        "role": role,
        "layout": {"bbox": [60.0, 90.0, 420.0, 220.0]},
        "hints": hints,
    }


def caption_unit(
    unit_id: str,
    text: str,
    *,
    page: int = 1,
    parent: str = "urn:company-wiki:source:sha256:aaaa",
    kind: str = "table_caption",
) -> dict:
    return wire_unit(
        unit_id,
        text,
        page=page,
        parent=parent,
        kind=kind,
        locator=f"loc:v1/page:{page}/paragraph:{unit_id}",
    )


def observation(
    units: Sequence[Mapping[str, Any]],
    *,
    source_id: str = "urn:company-wiki:source:sha256:aaaa",
    source_sha256: str = "aaaa",
    schema_version: str = "du-input/1",
) -> dict:
    return {
        "schema_version": schema_version,
        "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
        "metadata": {"title": "", "declared_kind": "unknown", "mime_type": "application/pdf",
                     "language": "zh"},
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": [dict(unit, ordinal=index) for index, unit in enumerate(units)],
    }


def layout_hints(
    *,
    region_units: Sequence[str],
    header_units: Sequence[str] = (),
    data_rows: Sequence[Sequence[str]] = (),
    caption_units: Sequence[str] = (),
    footnote_units: Sequence[str] = (),
    schema_version: str = "du2-layout-hints/1",
) -> dict:
    """A minimal but wire-shaped ``du2-layout-hints/1`` with real relation kinds."""
    groups: list[dict] = []
    relations: list[dict] = []
    counter = [0]

    def add(kind, members, *, parent=None, basis, confidence="high"):
        counter[0] += 1
        group_id = f"g{counter[0]}"
        groups.append({
            "group_id": group_id,
            "kind": kind,
            "parent_table_id": parent,
            "member_unit_ids": list(members),
            "required_context_unit_ids": [],
            "cells": [],
            "confidence": confidence,
            "basis": list(basis),
        })
        return group_id

    region = add("table_region", region_units, basis=["column_alignment", "header_block"])
    if header_units:
        header_group = add("table_row", header_units, parent=region, basis=["header_row"])
        relations.append({
            "from_group_id": header_group,
            "to_group_id": region,
            "kind": "header_for",
            "confidence": "high",
            "basis": ["header_row_alignment"],
        })
    for row_members in data_rows:
        add("table_row", row_members, parent=region, basis=["visual_row"], confidence="medium")
    for members in caption_units:
        group = add("caption", [members], basis=["caption_context"])
        relations.append({
            "from_group_id": group,
            "to_group_id": region,
            "kind": "caption_for",
            "confidence": "high",
            "basis": ["adjacent_to_table_edge"],
        })
    for members in footnote_units:
        group = add("footnote", [members], parent=region, basis=["footnote_line"])
        relations.append({
            "from_group_id": group,
            "to_group_id": region,
            "kind": "footnote_for",
            "confidence": "high",
            "basis": ["adjacent_to_table_edge"],
        })
    return {
        "schema_version": schema_version,
        "feature_version": "du2-layout-hints/1",
        "source_ref": {"source_id": "urn:company-wiki:source:sha256:aaaa", "source_sha256": "aaaa"},
        "unit_hints": [],
        "groups": groups,
        "relations": sorted(
            relations,
            key=lambda item: (item["from_group_id"], item["to_group_id"], item["kind"]),
        ),
        "reading_order": [],
        "coverage": {"processed_unit_count": 0, "deferred_unit_ids": [], "complete": True},
        "diagnostics": [],
    }


def merge_layout_hints(*pieces: Mapping[str, Any]) -> dict:
    """Merge several wire-shaped hint dicts with globally unique group ids."""
    groups: list[dict] = []
    relations: list[dict] = []
    counter = 0
    for piece in pieces:
        id_map: dict[str, str] = {}
        for group in piece["groups"]:
            counter += 1
            new_id = f"g{counter}"
            id_map[group["group_id"]] = new_id
            groups.append(
                dict(
                    group,
                    group_id=new_id,
                    parent_table_id=id_map.get(group["parent_table_id"])
                    if group["parent_table_id"]
                    else None,
                )
            )
        for relation in piece["relations"]:
            relations.append(
                dict(
                    relation,
                    from_group_id=id_map[relation["from_group_id"]],
                    to_group_id=id_map[relation["to_group_id"]],
                )
            )
    return dict(pieces[0], groups=groups, relations=relations)


def real_pdf_bytes(*, pages: Sequence[Mapping[str, Any]] = ()) -> bytes:
    """A real (fitz-generated) PDF; ``pages`` rows give drawn table grids."""
    fitz = __import__("fitz")
    document = fitz.open()
    for page_spec in pages:
        page = document.new_page(width=600, height=800)
        grid = page_spec.get("grid") or []
        caption = page_spec.get("caption")
        top = 80.0
        if caption:
            page.insert_text((72, top), caption, fontsize=9)
            top += 24
        if grid:
            xs = page_spec.get("xs") or [72, 260, 420, 520]
            row_h = page_spec.get("row_height") or 30.0
            ys = [top + row_h * index for index in range(len(grid) + 1)]
            for x in xs:
                page.draw_line((x, ys[0]), (x, ys[-1]))
            for y in ys:
                page.draw_line((xs[0], y), (xs[-1], y))
            for row_index, row in enumerate(grid):
                for column, text in enumerate(row):
                    if text:
                        page.insert_text(
                            (xs[column] + 4, ys[row_index] + row_h * 0.66), text, fontsize=9
                        )
    data = document.tobytes()
    document.close()
    return data
