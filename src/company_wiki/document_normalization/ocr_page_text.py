"""Deterministic reading-order + bounded body text for one OCR page (P1).

Pure component (no IO, no model, no network).  Turns an already-produced
:class:`~company_wiki.document_normalization.local_ocr.ImageOCRResult` into the
frozen ``cwp-ocr-page-text/1`` document: column split, geometry-driven reading
order, per-line ``char_start/char_end`` ranges into ``text``, and an explicit
accepted/deferred decision for every input line.

Deferred lines are never silently dropped: they stay in ``lines`` with
``accepted=False`` and a ``defer_reasons`` entry, and are listed in
``deferred_line_indexes`` so downstream can report the loss honestly.

Judgement rules are exactly the seven in card section 5.1:

1. Column clustering: sort by ``x0``; start a new column when a line's left
   edge is at least ``column_gap_em * font_size`` past the current column's
   right edge.  More columns than ``max_columns`` -> ``partial`` and the
   overflow lines get ``column_overflow``.
2. Within a column, order by ``(round(y0/tolerance), x0)``; lines whose ``y0``
   differs by less than ``line_tolerance_em * font_size`` form one visual line
   and are concatenated by ascending ``x0`` (no separator, so char ranges stay
   contiguous).
3. Order ambiguity: two lines of one visual line whose x intervals contain one
   another with >50% overlap -> both ``ambiguous_order``.
4. Low confidence: ``confidence < min_confidence`` -> ``low_confidence`` (single
   threshold, never branched by company / document type).
5. Bad geometry: box outside the page or a non-finite ratio derived from
   ``font_size`` -> ``bbox_invalid``.
6. Budget: past ``max_lines`` or ``max_chars`` -> ``limit`` from that line on;
   line text is never truncated.
7. Determinism: two calls give byte-identical canonical JSON.

``font_size`` defaults to the median line height of the page; when no line can
establish that median (zero lines) the page reports ``status="unavailable"`` and
``reason="p1_page_empty"``.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any

from .local_ocr import ImageOCRResult

P1_PAGE_TEXT_SCHEMA = "cwp-ocr-page-text/1"
P1_PAGE_TEXT_VERSION = "1.0.0"

# Defer vocabulary (card section 5.1 per-line `defer_reasons`).
DEFER_BBOX_INVALID = "bbox_invalid"
DEFER_LOW_CONFIDENCE = "low_confidence"
DEFER_AMBIGUOUS_ORDER = "ambiguous_order"
DEFER_LIMIT = "limit"
DEFER_COLUMN_OVERFLOW = "column_overflow"

DEFER_REASONS = frozenset(
    {
        DEFER_BBOX_INVALID,
        DEFER_LOW_CONFIDENCE,
        DEFER_AMBIGUOUS_ORDER,
        DEFER_LIMIT,
        DEFER_COLUMN_OVERFLOW,
    }
)

# Canonical emit order for defer_reasons so output stays byte-deterministic.
_DEFER_ORDER = (
    DEFER_BBOX_INVALID,
    DEFER_LOW_CONFIDENCE,
    DEFER_AMBIGUOUS_ORDER,
    DEFER_LIMIT,
    DEFER_COLUMN_OVERFLOW,
)

# Diagnostic codes (INTERFACES section 3, P1 prefix).
CODE_BBOX_INVALID = "p1_bbox_invalid"
CODE_LOW_CONFIDENCE = "p1_line_confidence_low"
CODE_AMBIGUOUS_ORDER = "p1_order_ambiguous"
CODE_PAGE_LIMIT = "p1_page_limit"

REASON_PAGE_EMPTY = "p1_page_empty"

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class PageOrderLimits:
    """Per-call ordering budget (a call-scoped limit, not a shared object)."""

    max_lines: int = 2000
    max_chars: int = 20000
    max_columns: int = 4
    min_confidence: float = 0.60
    column_gap_em: float = 2.0
    line_tolerance_em: float = 0.60

    def __post_init__(self) -> None:
        for name in ("max_lines", "max_chars", "max_columns"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
        confidence = self.min_confidence
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise TypeError("min_confidence must be a number")
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("min_confidence must be finite in [0, 1]")
        if not math.isfinite(self.column_gap_em) or self.column_gap_em < 0:
            raise ValueError("column_gap_em must be finite and >= 0")
        if not math.isfinite(self.line_tolerance_em) or self.line_tolerance_em <= 0:
            raise ValueError("line_tolerance_em must be finite and > 0")


def _is_valid_box(box: list[float], width: int, height: int) -> bool:
    """Rule 5 geometry guard: finite, positive-area, inside the page."""
    if len(box) != 4:
        return False
    x0, y0, x1, y1 = box
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
        return False
    if x0 < 0 or y0 < 0:
        return False
    if x1 <= x0 or y1 <= y0:
        return False
    if x1 > width or y1 > height:
        return False
    return True


def _add_defer(record: dict[str, Any], reason: str) -> None:
    if reason not in record["_reason_set"]:
        record["_reason_set"].add(reason)
        record["_reasons"] = [r for r in _DEFER_ORDER if r in record["_reason_set"]]


def _line_doc(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "line_index": record["line_index"],
        "column_id": record["column_id"],
        "text": record["text"],
        "box": record["box"],
        "confidence": record["confidence"],
        "char_start": record["char_start"],
        "char_end": record["char_end"],
        "accepted": record["accepted"],
        "defer_reasons": list(record["_reasons"]),
    }


def _finalize(
    result: ImageOCRResult,
    *,
    records: list[dict[str, Any]],
    columns: list[dict[str, Any]],
    text: str,
    accepted_count: int,
    limits: PageOrderLimits,
    reason: str | None = None,
) -> dict[str, Any]:
    deferred = sorted(r["line_index"] for r in records if r["_reasons"])
    if accepted_count == 0:
        status = STATUS_UNAVAILABLE
    elif deferred:
        status = STATUS_PARTIAL
    else:
        status = STATUS_OK
    return {
        "schema_version": P1_PAGE_TEXT_SCHEMA,
        "page": {"width": int(result.width), "height": int(result.height)},
        "status": status,
        "columns": columns,
        "lines": [
            _line_doc(r) for r in sorted(records, key=lambda r: r["line_index"])
        ],
        "text": text,
        "deferred_line_indexes": deferred,
        "diagnostics": _build_diagnostics(records, limits),
        "work_used": {"lines": accepted_count, "chars": len(text)},
        "reason": reason,
    }


def order_page_lines(
    result: ImageOCRResult,
    *,
    limits: PageOrderLimits = PageOrderLimits(),
    font_size: float | None = None,
) -> dict[str, Any]:
    """Order one page's OCR lines into bounded, locatable body text.

    The input ``result`` (and its ``lines``) is read only and never mutated.
    """
    if not isinstance(result, ImageOCRResult):
        raise TypeError("result must be an ImageOCRResult")
    if not isinstance(limits, PageOrderLimits):
        raise TypeError("limits must be a PageOrderLimits")

    width = int(result.width)
    height = int(result.height)
    raw_lines = tuple(result.lines)

    if not raw_lines:
        return {
            "schema_version": P1_PAGE_TEXT_SCHEMA,
            "page": {"width": width, "height": height},
            "status": STATUS_UNAVAILABLE,
            "columns": [],
            "lines": [],
            "text": "",
            "deferred_line_indexes": [],
            "diagnostics": [],
            "work_used": {"lines": 0, "chars": 0},
            "reason": REASON_PAGE_EMPTY,
        }

    # --- em basis (rule 5 guards font_size-derived ratios) ----------------
    if font_size is None:
        em = float(
            statistics.median(line.box[3] - line.box[1] for line in raw_lines)
        )
    else:
        if isinstance(font_size, bool) or not isinstance(font_size, (int, float)):
            raise TypeError("font_size must be a number or None")
        em = float(font_size)

    if not math.isfinite(em) or em <= 0:
        return _all_deferred(result, DEFER_BBOX_INVALID)
    gap_threshold = limits.column_gap_em * em
    tolerance = limits.line_tolerance_em * em
    if not (math.isfinite(gap_threshold) and math.isfinite(tolerance)):
        return _all_deferred(result, DEFER_BBOX_INVALID)

    # --- per-line records; classify with rules 4 and 5 --------------------
    records: list[dict[str, Any]] = []
    for index, line in enumerate(raw_lines):
        box = [float(v) for v in line.box]
        confidence = float(line.confidence)
        record: dict[str, Any] = {
            "line_index": index,
            "text": line.text,
            "box": box,
            "confidence": confidence,
            "column_id": None,
            "char_start": None,
            "char_end": None,
            "accepted": False,
            "_reason_set": set(),
            "_reasons": [],
            "_in_reading_order": False,
        }
        if not _is_valid_box(box, width, height):
            _add_defer(record, DEFER_BBOX_INVALID)
        if confidence < limits.min_confidence:
            _add_defer(record, DEFER_LOW_CONFIDENCE)
        records.append(record)

    # --- rule 1: column clustering ----------------------------------------
    placeable = [r for r in records if DEFER_BBOX_INVALID not in r["_reason_set"]]
    clusters = _cluster_columns(placeable, tolerance, gap_threshold)
    overflow_clusters = clusters[limits.max_columns :]
    kept_clusters = clusters[: limits.max_columns]
    for cluster in overflow_clusters:
        for record in cluster:
            _add_defer(record, DEFER_COLUMN_OVERFLOW)

    # --- rule 2: within-column order, visual lines, rule 3 ambiguity -------
    reading_rows: list[list[dict[str, Any]]] = []
    columns_out: list[dict[str, Any]] = []
    for col_no, cluster in enumerate(kept_clusters):
        column_id = f"col-{col_no}"
        ordered = sorted(
            cluster,
            key=lambda r: (round(r["box"][1] / tolerance), r["box"][0], r["line_index"]),
        )
        visual_lines: list[list[dict[str, Any]]] = []
        for record in ordered:
            if visual_lines and abs(
                record["box"][1] - visual_lines[-1][0]["box"][1]
            ) < tolerance:
                visual_lines[-1].append(record)
            else:
                visual_lines.append([record])

        member_indexes: list[int] = []
        for visual in visual_lines:
            visual.sort(key=lambda r: (r["box"][0], r["line_index"]))
            _mark_ambiguous(visual)
            for record in visual:
                record["column_id"] = column_id
                record["_in_reading_order"] = True
                member_indexes.append(record["line_index"])
            reading_rows.append(visual)

        columns_out.append(
            {
                "column_id": column_id,
                "x0": min(r["box"][0] for r in cluster),
                "x1": max(r["box"][2] for r in cluster),
                "line_indexes": member_indexes,
            }
        )

    # --- rule 6 budgets + emit text (one pass keeps char ranges honest) ---
    text_parts: list[str] = []
    offset = 0
    accepted_count = 0
    limit_hit = False
    for visual in reading_rows:
        row_accepted = False
        for record in visual:
            # Rule 6: from the limit line onward *every* following line in
            # reading order gets `limit` (its earlier reasons are kept).
            if limit_hit:
                _add_defer(record, DEFER_LIMIT)
                continue
            if record["_reasons"]:
                continue
            separator = 0 if (accepted_count == 0 or row_accepted) else 1
            projected = offset + separator + len(record["text"])
            if accepted_count + 1 > limits.max_lines or projected > limits.max_chars:
                _add_defer(record, DEFER_LIMIT)
                limit_hit = True
                continue
            if separator:
                text_parts.append("\n")
                offset += 1
            record["char_start"] = offset
            record["char_end"] = offset + len(record["text"])
            offset += len(record["text"])
            text_parts.append(record["text"])
            record["accepted"] = True
            accepted_count += 1
            row_accepted = True

    return _finalize(
        result,
        records=records,
        columns=columns_out,
        text="".join(text_parts),
        accepted_count=accepted_count,
        limits=limits,
    )


def _all_deferred(result: ImageOCRResult, reason: str) -> dict[str, Any]:
    """Every input line deferred (unusable em basis): no body text at all."""
    records = []
    for index, line in enumerate(result.lines):
        record: dict[str, Any] = {
            "line_index": index,
            "text": line.text,
            "box": [float(v) for v in line.box],
            "confidence": float(line.confidence),
            "column_id": None,
            "char_start": None,
            "char_end": None,
            "accepted": False,
            "_reason_set": {reason},
            "_reasons": [reason],
            "_in_reading_order": False,
        }
        records.append(record)
    return _finalize(
        result,
        records=records,
        columns=[],
        text="",
        accepted_count=0,
        limits=PageOrderLimits(),
        reason=None,
    )


def _column_boundary_bands(
    records: list[dict[str, Any]], tolerance: float, gap_threshold: float
) -> list[tuple[float, float]]:
    """Rule 1: column boundaries derived from within-visual-row horizontal gaps.

    The gap is measured between adjacent lines *of the same visual row*, so a
    full-width header/footer row (a single line in its own row) can never push
    the running right edge out and swallow a body column.  That keeps card
    section 6 case 3's floor -- "if page-margin detection is not implemented,
    at least do not change the order of the other rows" -- true for multi-column
    pages without implementing page-margin detection.  Overlapping gaps from
    different rows are merged into one boundary band.
    """
    ordered = sorted(
        records,
        key=lambda r: (round(r["box"][1] / tolerance), r["box"][0], r["line_index"]),
    )
    rows: list[list[dict[str, Any]]] = []
    for record in ordered:
        if rows and abs(record["box"][1] - rows[-1][0]["box"][1]) < tolerance:
            rows[-1].append(record)
        else:
            rows.append([record])

    raw_gaps: list[tuple[float, float]] = []
    for row in rows:
        row_sorted = sorted(row, key=lambda r: (r["box"][0], r["line_index"]))
        for index in range(len(row_sorted) - 1):
            gap = row_sorted[index + 1]["box"][0] - row_sorted[index]["box"][2]
            if gap >= gap_threshold:
                raw_gaps.append((row_sorted[index]["box"][2], row_sorted[index + 1]["box"][0]))

    bands: list[tuple[float, float]] = []
    for left, right in sorted(raw_gaps):
        if bands and left <= bands[-1][1]:
            bands[-1] = (bands[-1][0], max(bands[-1][1], right))
        else:
            bands.append((left, right))
    return bands


def _cluster_columns(
    records: list[dict[str, Any]], tolerance: float, gap_threshold: float
) -> list[list[dict[str, Any]]]:
    """Rule 1: split x0-sorted lines at the merged row-gap boundary bands."""
    bands = _column_boundary_bands(records, tolerance, gap_threshold)
    ordered = sorted(
        records, key=lambda r: (r["box"][0], r["box"][2], r["line_index"])
    )
    clusters: list[list[dict[str, Any]]] = []
    current_col = -1
    for record in ordered:
        # bands are sorted by left edge and x0 is ascending, so this count is
        # non-decreasing and gives a stable left-to-right column index.
        column_index = sum(1 for band in bands if band[0] < record["box"][0])
        if column_index != current_col:
            clusters.append([])
            current_col = column_index
        clusters[-1].append(record)
    return clusters


def _mark_ambiguous(visual: list[dict[str, Any]]) -> None:
    """Rule 3: nested x intervals with >50% overlap defer both lines."""
    for i in range(len(visual)):
        for j in range(i + 1, len(visual)):
            a = visual[i]
            b = visual[j]
            ax0, _, ax1, _ = a["box"]
            bx0, _, bx1, _ = b["box"]
            crossing = (ax0 < bx0 and ax1 > bx1) or (bx0 < ax0 and bx1 > ax1)
            if not crossing:
                continue
            overlap = min(ax1, bx1) - max(ax0, bx0)
            smaller = min(ax1 - ax0, bx1 - bx0)
            if smaller > 0 and overlap > 0.5 * smaller:
                _add_defer(a, DEFER_AMBIGUOUS_ORDER)
                _add_defer(b, DEFER_AMBIGUOUS_ORDER)


def _build_diagnostics(
    records: list[dict[str, Any]], limits: PageOrderLimits
) -> list[dict[str, str]]:
    """One diagnostic per distinct P1 condition (INTERFACES section 3)."""
    def _count(reason: str) -> int:
        return sum(1 for r in records if reason in r["_reason_set"])

    bbox = _count(DEFER_BBOX_INVALID)
    low = _count(DEFER_LOW_CONFIDENCE)
    amb = _count(DEFER_AMBIGUOUS_ORDER)
    limit = _count(DEFER_LIMIT)
    overflow = _count(DEFER_COLUMN_OVERFLOW)

    diagnostics: list[dict[str, str]] = []
    if bbox:
        diagnostics.append(
            {
                "code": CODE_BBOX_INVALID,
                "detail": f"{bbox} line(s) with an out-of-bounds or non-finite box",
            }
        )
    if low:
        diagnostics.append(
            {
                "code": CODE_LOW_CONFIDENCE,
                "detail": f"{low} line(s) below min_confidence={limits.min_confidence}",
            }
        )
    if amb:
        diagnostics.append(
            {
                "code": CODE_AMBIGUOUS_ORDER,
                "detail": f"{amb} line(s) with nested x intervals in one visual line",
            }
        )
    if limit or overflow:
        diagnostics.append(
            {
                "code": CODE_PAGE_LIMIT,
                "detail": (
                    f"{limit} line(s) over the line/char budget, "
                    f"{overflow} line(s) beyond max_columns={limits.max_columns}"
                ),
            }
        )
    return diagnostics


__all__ = [
    "DEFER_REASONS",
    "P1_PAGE_TEXT_SCHEMA",
    "P1_PAGE_TEXT_VERSION",
    "PageOrderLimits",
    "order_page_lines",
]
