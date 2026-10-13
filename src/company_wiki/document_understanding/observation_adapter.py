"""Production adapter: existing narrative units -> frozen ``du-input/1``.

This is ROOT-owned integration code.  It does not re-parse a document, does not
re-hash an original, does not rewrite a locator, and does not touch disk: it
projects the units the existing parser already produced onto the frozen
``du-input/1`` wire so the pure route/structure packages can consume them.

What it adds that the parser does not emit, and why each addition is derived
from evidence already present rather than guessed:

``heading_level``
    A PDF page arrives as ``pdf_text_block`` fragments with no level.  A
    numbered heading (``第三节 …`` / ``一、…`` / ``（一）…`` / ``Item 1.``) is
    real evidence in the text itself, so a level is assigned from that
    numbering.  Nothing is assigned when no numbering is present.

``column``
    The parser gives a ``bbox`` per block but no lane index.  Lanes are
    *measured*: blocks on a page are split at the page's widest sustained
    horizontal gutter, and a block belongs to the lane its left edge falls in.
    A page with no clear gutter gets ``None``, never a guessed ``0``.

``table_header`` / ``table_caption`` kinds and ``table_id``
    The parser already emits the header row as row 0 of a table and carries
    ``table_headers``/``row_cells`` on every row.  Row 0 is therefore the
    header, and ``(page, paragraph/table index)`` identifies the table.  A
    ``单位：`` / ``币种：`` caption is recognized from its own text.

Everything else is passed through unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

INPUT_SCHEMA_VERSION = "du-input/1"

# The parser writes this role for units lifted out of a Q&A page.
QA_SHADOW_ROLE = "qa_text_shadow"

_NUMBERED_HEADING = (
    # (regex, level)
    (r"^第[一二三四五六七八九十百零\d]+[节章编]\s*\S", 1),
    (r"^第[一二三四五六七八九十百零\d]+[部分篇]\s*\S", 1),
    (r"^(?:Item|ITEM)\s+\d+[A-Za-z]?\.?\s+\S", 1),
    (r"^[IVXLC]+\.\s+\S", 1),
    (r"^[一二三四五六七八九十]+[、．.]\s*\S", 2),
    (r"^（[一二三四五六七八九十]+）\s*\S", 3),
    (r"^\([一二三四五六七八九十]+\)\s*\S", 3),
    # A dotted outline number must be followed by a title word, not by a year
    # or a quantity: "1.2 经营情况" is a heading, "2020 年5 月" is prose.
    (r"^\d{1,2}(?:\.\d{1,2}){1,3}\s*[\u4e00-\u9fffA-Za-z]\S*", 3),
)

_HEADING_TERMINATOR = ("。", "；", ";", "：", ":")
_UNIT_CAPTION = ("单位：", "单位:", "币种：", "币种:", "单位: ", "人民币万元", "人民币元")

_MAX_HEADING_CHARS = 60


def _heading_level(text: str, metadata: Mapping[str, Any]) -> int | None:
    """Return a heading level only from evidence actually present.

    Two admissible sources, in order:

    1. An explicit HTML heading level carried through as ``heading_level``.
    2. A numbering scheme in the text itself, which is self-evident.

    A short block with a background colour is also accepted when the parser
    supplies ``heading_like``; the current PDF parser does not emit it, which is
    why an unnumbered paper heading such as ``Store Network`` stays a paragraph
    rather than being guessed into a section.  Guessing there would misfire on
    the equally short table fragments on the same page.
    """
    explicit = metadata.get("heading_level")
    if isinstance(explicit, int) and not isinstance(explicit, bool) and explicit > 0:
        return explicit
    if metadata.get("heading_like") is True:
        return 2

    stripped = text.strip()
    if not stripped or len(stripped) > _MAX_HEADING_CHARS or "\n" in stripped:
        return None
    if stripped.endswith(_HEADING_TERMINATOR):
        return None
    import re

    for pattern, level in _NUMBERED_HEADING:
        if re.match(pattern, stripped):
            return level
    return None


def _is_unit_caption(text: str) -> bool:
    stripped = text.strip().lstrip("（(")
    return stripped.startswith(_UNIT_CAPTION)


def _bbox_of(unit: Any) -> tuple[float, float, float, float] | None:
    value = unit.metadata.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        coords = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None
    x0, y0, x1, y1 = coords
    if x1 <= x0 or y1 <= y0:
        return None
    return coords  # type: ignore[return-value]


def _detect_gutter_x(
    blocks: Sequence[tuple[float, float, float, float]],
    page_width: float | None = None,
) -> float | None:
    """Find a two-column gutter, ignoring blocks that span the whole text area.

    A real filing page mixes narrow column blocks with full-width tables.  The
    tables straddle any gutter, so they are excluded from the measurement; the
    gutter is then the clear separation between the remaining left-edge and
    right-edge block groups.  Returning ``None`` is the honest answer for a
    single-column page.
    """
    if len(blocks) < 4:
        return None
    widths = sorted(x1 - x0 for x0, _y0, x1, _y1 in blocks)
    median_width = widths[len(widths) // 2]
    if median_width <= 0:
        return None
    # Text area is the union of all blocks; a block covering most of it spans
    # the columns rather than sitting in one.
    text_left = min(x0 for x0, _y0, _x1, _y1 in blocks)
    text_right = max(x1 for _x0, _y0, x1, _y1 in blocks)
    text_span = text_right - text_left
    if text_span <= 0:
        return None
    narrow = [
        (x0, x1)
        for x0, _y0, x1, _y1 in blocks
        if (x1 - x0) <= 0.75 * text_span and (x1 - x0) >= 0.10 * text_span
    ]
    if len(narrow) < 4:
        return None

    # Split the narrow blocks by their *left edge*, not by the page midpoint:
    # a page header sitting in the right half would otherwise pull the split.
    narrow.sort()
    best: tuple[float, float] | None = None
    for index in range(1, len(narrow)):
        left_group = narrow[:index]
        right_group = narrow[index:]
        if len(left_group) < 2 or len(right_group) < 2:
            continue
        left_right_edge = max(block[1] for block in left_group)
        right_left_edge = min(block[0] for block in right_group)
        if right_left_edge <= left_right_edge:
            continue
        clear_gap = right_left_edge - left_right_edge
        narrower = min(
            left_right_edge - min(block[0] for block in left_group),
            max(block[1] for block in right_group) - right_left_edge,
        )
        if narrower <= 0:
            continue
        # A real gutter separates the groups by a meaningful share of the
        # narrower column's width; a few points of kerning is not a boundary.
        if clear_gap < 0.08 * narrower:
            continue
        if best is None or clear_gap > best[0]:
            best = (clear_gap, (left_right_edge + right_left_edge) / 2)
    if best is None:
        return None
    del page_width
    return best[1]


def _lane_for(x0: float, x1: float, gutter: float, text_span: tuple[float, float]) -> int | None:
    """Assign a lane only to a block that sits clearly on one side.

    A block that straddles the gutter (a full-width table, a banner) belongs to
    neither lane and gets ``None`` rather than a guessed side.
    """
    if x0 < gutter <= x1:
        return None
    del text_span
    return 0 if x1 <= gutter else 1


def build_observation(
    units: Sequence[Any],
    *,
    source_id: str,
    source_sha256: str,
    title: str = "",
    declared_kind: str = "unknown",
    mime_type: str = "application/pdf",
    language: str | None = None,
    native_scan: str = "complete",
    opaque_pages: Sequence[int] = (),
    deferred_pages: Sequence[int] = (),
) -> dict[str, Any]:
    """Project existing narrative units onto the frozen ``du-input/1`` wire.

    The function is pure with respect to the inputs: units are read, never
    modified, and no locator, id or byte digest is recomputed.
    """
    if native_scan not in {"complete", "partial", "unavailable"}:
        native_scan = "unavailable"

    # Pass 1: geometry per page, so lanes can be measured before emission.
    by_page: dict[int, list[tuple[float, float, float, float]]] = {}
    page_spans: dict[int, tuple[float, float]] = {}
    for unit in units:
        page = unit.coordinates.page_number
        box = _bbox_of(unit)
        if page is None or box is None:
            continue
        by_page.setdefault(page, []).append(box)
    gutters: dict[int, float] = {}
    for page, boxes in by_page.items():
        text_left = min(box[0] for box in boxes)
        text_right = max(box[2] for box in boxes)
        page_spans[page] = (text_left, text_right)
        gutter = _detect_gutter_x(boxes)
        if gutter is not None:
            gutters[page] = gutter

    emitted: list[dict[str, Any]] = []
    for ordinal, unit in enumerate(units):
        coordinates = unit.coordinates
        page = coordinates.page_number
        metadata = unit.metadata
        box = _bbox_of(unit)

        layout: dict[str, Any] = {}
        if box is not None:
            layout["bbox"] = list(box)
            page_width = metadata.get("page_width")
            if isinstance(page_width, (int, float)):
                layout["page_width"] = float(page_width)
            page_height = metadata.get("page_height")
            if isinstance(page_height, (int, float)):
                layout["page_height"] = float(page_height)
        if page is not None and page in gutters and box is not None:
            lane = _lane_for(box[0], box[2], gutters[page], page_spans[page])
            if lane is not None:
                layout["column"] = lane

        hints: dict[str, Any] = {}
        level = _heading_level(unit.raw_text, metadata)
        if level is not None and unit.unit_kind in {"pdf_text_block", "html_heading"}:
            hints["heading_level"] = level
        if coordinates.table_index is not None:
            hints["table_id"] = f"p{page}:t{coordinates.table_index}"
        if coordinates.row_index is not None:
            hints["row"] = coordinates.row_index
        if coordinates.column_index is not None:
            hints["column"] = coordinates.column_index
        if metadata.get("qa_state"):
            hints["turn_id"] = str(metadata.get("qa_group_id") or "")
            hints["speaker"] = (
                "management"
                if "answer" in str(metadata.get("qa_state"))
                else "investor"
            )
        if unit.unit_kind == "html_heading" and isinstance(metadata.get("dom_path"), str):
            hints["dom_path"] = metadata["dom_path"]

        kind = _wire_kind(unit, coordinates)
        emitted.append(
            {
                "unit_id": unit.unit_id,
                "ordinal": ordinal,
                "locator": str(metadata.get("source_locator") or unit.unit_id),
                "page": page,
                "text": unit.raw_text,
                "kind": kind,
                "language": unit.language,
                "role": unit.source_role,
                "layout": layout,
                "hints": hints,
            }
        )

    resolved_language = language
    if resolved_language is None:
        resolved_language = next(
            (unit.language for unit in units if getattr(unit, "language", None)), "und"
        )

    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
        "metadata": {
            "title": title,
            "declared_kind": declared_kind,
            "mime_type": mime_type,
            "language": resolved_language,
        },
        "coverage": {
            "native_scan": native_scan,
            "opaque_pages": [int(page) for page in opaque_pages],
            "deferred_pages": [int(page) for page in deferred_pages],
        },
        "units": emitted,
    }


def _wire_kind(unit: Any, coordinates: Any) -> str:
    """Map a parser unit kind onto the frozen wire vocabulary."""
    if unit.unit_kind == "pdf_table_row":
        # Row 0 of an extracted table is its header; the parser already carries
        # the header cells on every row, so this is evidence, not a guess.
        if coordinates.row_index == 0:
            return "table_header"
        return "table_row"
    if unit.unit_kind == "pdf_table_header":
        return "table_header"
    if unit.unit_kind == "html_heading":
        return "heading"
    if unit.unit_kind == "html_footnote":
        return "footnote"
    if unit.unit_kind == "html_table_cell":
        return "table_row"
    if _is_unit_caption(unit.raw_text):
        return "table_caption"
    if unit.unit_kind == "pdf_text_block":
        if _heading_level(unit.raw_text, unit.metadata) is not None:
            return "heading"
        if unit.raw_text.lstrip().startswith(("注：", "注:", "Note:", "Note：")):
            return "footnote"
        return "paragraph"
    return "paragraph"


__all__ = ["INPUT_SCHEMA_VERSION", "QA_SHADOW_ROLE", "build_observation"]
