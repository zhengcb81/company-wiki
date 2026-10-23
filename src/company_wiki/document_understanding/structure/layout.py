"""Reading order and layout evidence.

This module answers three questions the section stack and the semantic unit
builders both need, and it answers them only from evidence actually present in
the observation:

1. What order are the units really in (per page, per column)?
2. Which units are page furniture (running headers, TOC entries) rather than
   body text?
3. Do two units visually continue one another across a line or page break?

No layout value is ever guessed.  When ``layout`` is absent the functions
degrade to ordinal/adjacency evidence and report lower confidence.
"""

from __future__ import annotations

from company_wiki.document_normalization.form_fields import has_inline_form_response

from collections.abc import Sequence
from dataclasses import dataclass
import re

from .contract import ObservationUnit

# A running header/footer repeats with (nearly) identical text across pages.
MIN_RUNNING_HEADER_PAGES = 2

_TOC_LEADER = re.compile(r"[.．·]{3,}\s*\d{1,4}\s*$")
_TOC_ENTRY = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百]+[节章部分]|[一二三四五六七八九十]+[、.]|\d+(?:\.\d+)*[、.]?)\s*\S.*[.．·]{2,}\s*\d{1,4}\s*$"
)
_PAGE_NUMBER = re.compile(r"^\s*[-—–]?\s*\d{1,4}\s*[-—–]?\s*$")
_HEADING_NUMBER = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百零]+[节章编]|[一二三四五六七八九十]+[、．.]|"
    r"（[一二三四五六七八九十]+）|\([一二三四五六七八九十]+\)|"
    r"\d+(?:\.\d+){1,3}\s|\d+[、．.](?!\d)\s*\S|[IVXLC]+\.\s|Item\s+\d+[A-Z]?\.?\s)",
)
_FOOTNOTE_MARK = re.compile(r"^\s*(?:注\s*[:：]|\*|\(\d+\)|（\d+）)")

# Residual tolerance when two boxes are on different pages: only the *reading*
# continuity is being judged there, never geometry.
_COLUMN_OVERLAP_MIN = 0.5


@dataclass(frozen=True)
class Ordering:
    """Reading order plus the furniture sets discovered along the way."""

    ordered: tuple[ObservationUnit, ...]
    running_header_ids: frozenset[str]
    toc_ids: frozenset[str]
    page_numbers: frozenset[int]
    evidence: tuple[str, ...]


def _column_key(unit: ObservationUnit) -> int:
    if unit.column is not None:
        return unit.column
    return 0


def _within_page_key(unit: ObservationUnit) -> tuple[float, float, int]:
    """Sort inside one page: column lane first, then top-down, then left-right."""
    y0 = unit.y0
    x0 = unit.x0
    return (
        float("inf") if y0 is None else y0,
        float("inf") if x0 is None else x0,
        unit.ordinal,
    )


def order_units(units: Sequence[ObservationUnit]) -> Ordering:
    """Return a stable reading order and the furniture it detected.

    Pages are visited in ascending physical page order; units without a page
    keep their input ordinal relative to the page they follow.  Nothing is
    renumbered and no locator is rewritten.
    """
    evidence: list[str] = []
    if any(unit.bbox is not None for unit in units):
        evidence.append("layout_bbox")
    if any(unit.column is not None for unit in units):
        evidence.append("layout_column")
    if any(unit.heading_level is not None for unit in units):
        evidence.append("hints_heading_level")
    if any(unit.dom_path for unit in units):
        evidence.append("hints_dom_path")
    if not evidence:
        evidence.append("ordinal_only")

    paged: dict[int | None, list[ObservationUnit]] = {}
    page_order: list[int | None] = []
    for unit in units:
        if unit.page not in paged:
            paged[unit.page] = []
            page_order.append(unit.page)
        paged[unit.page].append(unit)

    ordered: list[ObservationUnit] = []
    for page in sorted(page_order, key=lambda value: (value is None, value or 0)):
        bucket = paged[page]
        if any(unit.column is not None for unit in bucket):
            bucket = sorted(
                bucket,
                key=lambda unit: (
                    _column_key(unit),
                    _within_page_key(unit),
                ),
            )
        else:
            bucket = sorted(bucket, key=lambda unit: _within_page_key(unit))
        ordered.extend(bucket)

    running = _running_furniture(ordered)
    toc = _toc_units(ordered)
    page_numbers = frozenset(
        unit.page
        for unit in ordered
        if unit.page is not None and _PAGE_NUMBER.match(unit.text)
    )
    return Ordering(
        ordered=tuple(ordered),
        running_header_ids=frozenset(running),
        toc_ids=frozenset(toc),
        page_numbers=page_numbers,
        evidence=tuple(evidence),
    )


def _running_furniture(units: Sequence[ObservationUnit]) -> set[str]:
    """Detect text that repeats on several pages in a page-edge band.

    A unit qualifies only when its normalised text appears on at least
    ``MIN_RUNNING_HEADER_PAGES`` distinct pages *and* either the parser called
    it a header/footer or its box sits in the top/bottom band of its page.
    """
    by_text: dict[str, list[ObservationUnit]] = {}
    for unit in units:
        text = " ".join(unit.text.split())
        if not text or len(text) > 120:
            continue
        by_text.setdefault(text, []).append(unit)

    furniture: set[str] = set()
    for text, group in by_text.items():
        pages = {unit.page for unit in group if unit.page is not None}
        if len(pages) < MIN_RUNNING_HEADER_PAGES and not any(
            unit.is_header_furniture for unit in group
        ):
            continue
        for unit in group:
            if unit.is_header_furniture:
                furniture.add(unit.unit_id)
                continue
            if unit.bbox is None or unit.page_height is None:
                continue
            height = unit.page_height
            if height <= 0:
                continue
            top_band = unit.y1 is not None and unit.y1 <= height * 0.12
            bottom_band = unit.y0 is not None and unit.y0 >= height * 0.88
            if len(pages) >= MIN_RUNNING_HEADER_PAGES and (top_band or bottom_band):
                furniture.add(unit.unit_id)
    return furniture


def _toc_units(units: Sequence[ObservationUnit]) -> set[str]:
    """Detect a table of contents by leader lines, not by the word 目录."""
    toc: set[str] = set()
    for unit in units:
        if unit.kind in {"toc_entry", "toc"}:
            toc.add(unit.unit_id)
            continue
        if _TOC_LEADER.search(unit.text) and _HEADING_NUMBER.match(unit.text):
            toc.add(unit.unit_id)
            continue
        if _TOC_ENTRY.match(unit.text):
            toc.add(unit.unit_id)
    touched_pages = {
        unit.page for unit in units if unit.unit_id in toc and unit.page is not None
    }
    if len(touched_pages) < 1:
        return toc
    # A page that is mostly TOC leaders is a contents page even if some entry
    # lost its numbering; add its leader-bearing siblings.
    for unit in units:
        if unit.unit_id in toc or unit.page not in touched_pages:
            continue
        if _TOC_LEADER.search(unit.text):
            toc.add(unit.unit_id)
    return toc


def is_heading(unit: ObservationUnit, *, toc_ids: frozenset[str] | None = None) -> bool:
    """A heading needs a positive signal; kind alone is not enough when TOC-erased."""
    if toc_ids and unit.unit_id in toc_ids:
        return False
    if unit.is_header_furniture:
        return False
    if unit.heading_level is not None:
        return True
    if unit.kind in {"heading", "html_heading"}:
        return True
    if unit.is_table_furniture:
        return False  # table values are not chapter numbering
    if has_inline_form_response(unit.text):
        return False
    if _HEADING_NUMBER.match(unit.text) and len(unit.text) <= 80:
        return not unit.text.rstrip().endswith(("。", "；", ";", "."))
    return False


def heading_depth(unit: ObservationUnit) -> int | None:
    """Return the heading depth, or ``None`` when no level evidence exists."""
    if unit.heading_level is not None and unit.heading_level > 0:
        return unit.heading_level
    if not _HEADING_NUMBER.match(unit.text):
        return None
    text = unit.text.lstrip()
    if re.match(r"^第[一二三四五六七八九十百零]+[节章编]", text):
        return 1
    if re.match(r"^[一二三四五六七八九十]+[、．.]", text):
        return 2
    if re.match(r"^（[一二三四五六七八九十]+）|^\([一二三四五六七八九十]+\)", text):
        return 3
    dotted = re.match(r"^(\d+(?:\.\d+){0,3})", text)
    if dotted:
        return min(6, dotted.group(1).count(".") + 1)
    if re.match(r"^(?:Item\s+\d+[A-Z]?\.?|[IVXLC]+\.)\s", text):
        return 1
    return None


def heading_label(unit: ObservationUnit) -> str:
    """Normalised heading text used only for comparison, never for output text."""
    text = unit.text.strip()
    text = _HEADING_NUMBER.sub("", text, count=1).strip()
    return " ".join(text.split()).casefold()


def same_column(left: ObservationUnit, right: ObservationUnit) -> bool:
    if left.column is None or right.column is None:
        return True
    return left.column == right.column


def visual_overlap(left: ObservationUnit, right: ObservationUnit) -> float | None:
    """Horizontal overlap ratio of two boxes, or ``None`` without geometry."""
    if left.bbox is None or right.bbox is None:
        return None
    overlap = min(left.bbox[2], right.bbox[2]) - max(left.bbox[0], right.bbox[0])
    narrower = min(left.bbox[2] - left.bbox[0], right.bbox[2] - right.bbox[0])
    if narrower <= 0:
        return None
    return overlap / narrower


def continues_visually(previous: ObservationUnit, current: ObservationUnit) -> bool:
    """True only with real geometry: same lane, tight vertical gap, aligned box."""
    if previous.bbox is None or current.bbox is None:
        return False
    if previous.page != current.page:
        return False
    if not same_column(previous, current):
        return False
    gap = current.bbox[1] - previous.bbox[3]
    if gap < -1.0 or gap > 16.0:
        return False
    overlap = visual_overlap(previous, current)
    return overlap is not None and overlap >= _COLUMN_OVERLAP_MIN


def looks_like_footnote(unit: ObservationUnit) -> bool:
    return unit.is_footnote or bool(_FOOTNOTE_MARK.match(unit.text))


def looks_like_footnote_marker(text: str) -> bool:
    return bool(_FOOTNOTE_MARK.match(text))


# --------------------------------------------------------------------------
# Language lanes
# --------------------------------------------------------------------------

_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_LATIN = re.compile(r"[A-Za-z]")
_DIGIT_OR_PUNCT = re.compile(r"[\d\s\W_]", re.UNICODE)


def script_of(text: str) -> str | None:
    """Return ``cjk``, ``latin`` or ``None`` from the text's own characters.

    The parsed ``language`` field is not usable for lane detection: a real HK
    annual report reports ``zh`` for its English column too.  The writing
    system actually present in the text is evidence that cannot be mislabelled
    that way.
    """
    cjk = len(_CJK.findall(text))
    latin = len(_LATIN.findall(text))
    if cjk == 0 and latin == 0:
        return None
    if cjk >= latin:
        return "cjk"
    return "latin"


def horizontal_gap(left: ObservationUnit, right: ObservationUnit) -> float | None:
    """Signed horizontal separation between two boxes on the same page."""
    if left.bbox is None or right.bbox is None:
        return None
    if left.bbox[2] <= right.bbox[0]:
        return right.bbox[0] - left.bbox[2]
    if right.bbox[2] <= left.bbox[0]:
        return left.bbox[0] - right.bbox[2]
    return None


def side_by_side(
    left: ObservationUnit, right: ObservationUnit, *, max_gap: float = 120.0
) -> bool:
    """True when two boxes sit in separate columns of the same page.

    Requires real geometry: same page, no horizontal overlap, and a positive
    gap no wider than a plausible gutter.
    """
    if left.page is None or right.page is None or left.page != right.page:
        return False
    if not same_column(left, right):
        return False
    gap = horizontal_gap(left, right)
    return gap is not None and 0 < gap <= max_gap


def vertically_aligned(
    left: ObservationUnit, right: ObservationUnit, *, tolerance: float = 24.0
) -> bool:
    """True when two boxes describe the same band of the page."""
    if left.bbox is None or right.bbox is None:
        return False
    return abs(left.bbox[1] - right.bbox[1]) <= tolerance


__all__ = [
    "MIN_RUNNING_HEADER_PAGES",
    "Ordering",
    "continues_visually",
    "heading_depth",
    "heading_label",
    "horizontal_gap",
    "is_heading",
    "looks_like_footnote",
    "looks_like_footnote_marker",
    "order_units",
    "same_column",
    "script_of",
    "side_by_side",
    "vertically_aligned",
    "visual_overlap",
]
