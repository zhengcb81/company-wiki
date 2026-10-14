"""Fine-element ``unit_binding``: bind real extracted words/cells/fonts to a unit.

Every bound element keeps its OWN real bbox and its native index / char-range
basis.  A whole row/block/table bbox is never copied into a fine cell.  ``row_cells``
strings alone are not fine geometry.  Identical text in different blocks is never
merged.  Mixed font runs bind to their char ranges; an NFC/trim range that cannot
be strictly aligned is reported ``unknown`` without touching the unit text.
"""

from __future__ import annotations

from typing import Any, Mapping

from .contract import Binding
from .identity import Frame, WorkBudget, align_char_range, legal_bbox

# Granularity vocabulary: fine when real cells/words survive, coarse otherwise.
GRAN_FINE_CELL = "cell"
GRAN_FINE_WORD = "word"
GRAN_ROW = "row"
GRAN_BLOCK = "block"
GRAN_TABLE_REGION = "table_region"
GRAN_UNKNOWN = "unknown"

_COARSE_FROM_SOURCE = (("table", GRAN_TABLE_REGION), ("row", GRAN_ROW))


def _has_basis(item: Mapping[str, Any]) -> bool:
    if isinstance(item.get("native_index"), int) and not isinstance(item.get("native_index"), bool):
        return True
    return isinstance(item.get("char_start"), int) and isinstance(item.get("char_end"), int)


def _source_label(binding: Binding, kind: str) -> Any:
    if binding.source is not None:
        return binding.source
    return kind


def _element_provenance(
    *, kind: str, frame: Frame, page_no: Any, binding: Binding
) -> dict[str, Any]:
    return {
        "page": page_no,
        "coordinate_frame": frame.label,
        "source": _source_label(binding, kind),
    }


def bind_binding(
    binding: Binding,
    *,
    unit_text: str,
    frame: Frame,
    page_no: Any,
    budget: WorkBudget,
    fine_state: dict[str, int],
) -> tuple[dict[str, list], str, list[dict]]:
    """Bind one binding's fine elements to its unit.

    Returns ``(fine_payload, granularity, diagnostics)``.  Charges ``budget`` per
    inspected element and enforces the ``fine_state['limit']`` element ceiling.
    Raises :class:`WorkBudgetExceeded` when the work budget is exhausted so the
    caller can drop the half-processed binding.
    """
    words_out: list[dict] = []
    cells_out: list[dict] = []
    runs_out: list[dict] = []
    diagnostics: list[dict] = []
    unit_ids = [binding.unit_id]

    def take_one() -> None:
        budget.charge(1)
        fine_state["used"] += 1
        if fine_state["used"] > fine_state["limit"]:
            raise _FineLimit()

    # ---- words ----
    for item in binding.words:
        take_one()
        if not isinstance(item, Mapping):
            diagnostics.append(
                {"code": "FINE_ELEMENT_INVALID", "unit_ids": unit_ids, "detail": "word is not a mapping"}
            )
            continue
        bbox = legal_bbox(item.get("bbox"))
        if bbox is None:
            diagnostics.append(
                {"code": "BAD_ELEMENT_BBOX", "unit_ids": unit_ids, "detail": "word has no legal bbox"}
            )
            continue
        if not _has_basis(item):
            diagnostics.append(
                {"code": "FINE_ELEMENT_NO_BASIS", "unit_ids": unit_ids, "detail": "word lacks native index or char range"}
            )
            continue
        start, end, alignment = align_char_range(
            item.get("text"), item.get("char_start"), item.get("char_end"), unit_text
        )
        words_out.append(
            {
                "text": item.get("text"),
                "bbox": list(bbox),
                "native_index": item.get("native_index"),
                "char_start": start,
                "char_end": end,
                "char_start_supplied": item.get("char_start"),
                "char_end_supplied": item.get("char_end"),
                "char_alignment": alignment,
                **_element_provenance(kind="word", frame=frame, page_no=page_no, binding=binding),
            }
        )

    # ---- cells ----
    for item in binding.cells:
        take_one()
        if not isinstance(item, Mapping):
            diagnostics.append(
                {"code": "FINE_ELEMENT_INVALID", "unit_ids": unit_ids, "detail": "cell is not a mapping"}
            )
            continue
        bbox = legal_bbox(item.get("bbox"))
        if bbox is None:
            diagnostics.append(
                {"code": "BAD_ELEMENT_BBOX", "unit_ids": unit_ids, "detail": "cell has no legal bbox"}
            )
            continue
        if not _has_basis(item):
            diagnostics.append(
                {"code": "FINE_ELEMENT_NO_BASIS", "unit_ids": unit_ids, "detail": "cell lacks native index or char range"}
            )
            continue
        start, end, alignment = align_char_range(
            item.get("text"), item.get("char_start"), item.get("char_end"), unit_text
        )
        cell_out = {
            "text": item.get("text"),
            "bbox": list(bbox),
            "native_index": item.get("native_index"),
            "char_start": start,
            "char_end": end,
            "char_start_supplied": item.get("char_start"),
            "char_end_supplied": item.get("char_end"),
            "char_alignment": alignment,
            **_element_provenance(kind="cell", frame=frame, page_no=page_no, binding=binding),
        }
        # real row/column/table identity is preserved exactly as extracted
        for key in ("row", "column", "table_id"):
            if key in item:
                cell_out[key] = item[key]
        cells_out.append(cell_out)

    # ---- font runs ----
    nfc_len = len(unit_text)
    for item in binding.font_runs:
        take_one()
        if not isinstance(item, Mapping):
            diagnostics.append(
                {"code": "FINE_ELEMENT_INVALID", "unit_ids": unit_ids, "detail": "font run is not a mapping"}
            )
            continue
        start = item.get("char_start")
        end = item.get("char_end")
        if not (isinstance(start, int) and isinstance(end, int)) or start >= end:
            diagnostics.append(
                {"code": "FINE_ELEMENT_NO_BASIS", "unit_ids": unit_ids, "detail": "font run lacks a valid char range"}
            )
            continue
        alignment = "exact" if 0 <= start and end <= nfc_len else "unknown"
        runs_out.append(
            {
                "char_start": start if alignment == "exact" else None,
                "char_end": end if alignment == "exact" else None,
                "char_start_supplied": start,
                "char_end_supplied": end,
                "font_size": item.get("font_size"),
                "font_weight": item.get("font_weight"),
                "font": item.get("font"),
                "char_alignment": alignment,
                **_element_provenance(kind="font_run", frame=frame, page_no=page_no, binding=binding),
            }
        )

    granularity = _resolve_granularity(binding, words_out, cells_out)
    if granularity in (GRAN_ROW, GRAN_BLOCK, GRAN_TABLE_REGION, GRAN_UNKNOWN):
        diagnostics.append(
            {
                "code": "NO_FINE_GEOMETRY" if granularity != GRAN_UNKNOWN else "NO_REAL_GEOMETRY",
                "unit_ids": unit_ids,
                "detail": "only coarse/no real geometry for this unit; no fine cells invented",
            }
        )
    return {"words": words_out, "cells": cells_out, "font_runs": runs_out}, granularity, diagnostics


def _resolve_granularity(binding: Binding, words_out: list, cells_out: list) -> str:
    if cells_out:
        return GRAN_FINE_CELL
    if words_out:
        return GRAN_FINE_WORD
    if binding.bbox is None:
        return GRAN_UNKNOWN
    if binding.row_cells:
        # whole-row bbox + row_cells strings: a real row, but NOT fine cell geometry
        return GRAN_ROW
    source = str(binding.source or "").lower()
    for token, gran in _COARSE_FROM_SOURCE:
        if token in source:
            return gran
    return GRAN_BLOCK


class _FineLimit(Exception):
    """Internal: the fine-element ceiling was reached mid-binding."""


__all__ = ["GRAN_FINE_CELL", "GRAN_FINE_WORD", "GRAN_UNKNOWN", "bind_binding"]
