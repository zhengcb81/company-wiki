"""Heading evidence from font scale, weight and position.

Missing font evidence caps confidence: a short line alone is never a
high-confidence heading, and year/date lines are never headings at all.
"""

from __future__ import annotations

from .contract import Doc, Unit
from .geometry import band_height
from .text_evidence import (
    has_terminal_punctuation,
    heading_number_level,
    is_date_text,
    is_numeric_text,
    is_plain_sentence,
    is_year_text,
    normalize_ws,
)

HEADING_KINDS_SKIP = {"heading"}


def detect_repeated_furniture(doc: Doc) -> set:
    """Running headers/footers: same text near the edge on two or more pages."""
    positions: dict = {}
    for unit in doc.units:
        if unit.deferred or unit.bbox is None:
            continue
        if unit.page_height:
            top_edge = unit.page_height * 0.12
            bottom_edge = unit.page_height * 0.88
            near_edge = unit.bbox[3] <= top_edge or unit.bbox[1] >= bottom_edge
        else:
            near_edge = False
        if not near_edge:
            continue
        key = (normalize_ws(unit.text), unit.bbox[3] <= (unit.page_height or 0) * 0.12)
        positions.setdefault(key, []).append(unit)
    furniture: set = set()
    for units in positions.values():
        pages = {unit.page_index for unit in units}
        if len(pages) >= 2:
            furniture.update(unit.unit_id for unit in units)
    return furniture


def body_font_size(doc: Doc, excluded: set) -> float | None:
    sizes = []
    for unit in doc.units:
        if unit.deferred or unit.font_size is None or unit.unit_id in excluded:
            continue
        text = normalize_ws(unit.text)
        if len(text) < 12 or is_numeric_text(text):
            continue
        sizes.append(unit.font_size)
    if not sizes:
        return None
    sizes.sort()
    return sizes[len(sizes) // 2]


def _vertical_neighbors(unit: Unit, page_units: list[Unit]) -> tuple[float, float]:
    """Vertical clearance above/below within the unit's horizontal span."""
    above = 0.0
    below = 0.0
    box = unit.bbox
    span = max(box[2] - box[0], 1.0)
    gaps_above: list = []
    gaps_below: list = []
    for other in page_units:
        if other is unit or other.bbox is None:
            continue
        overlap = min(box[2], other.bbox[2]) - max(box[0], other.bbox[0])
        if overlap < 0.25 * span:
            continue
        if other.bbox[3] <= box[1]:
            gaps_above.append(box[1] - other.bbox[3])
        elif other.bbox[1] >= box[3]:
            gaps_below.append(other.bbox[1] - box[3])
    above = min(gaps_above) if gaps_above else float("inf")
    below = min(gaps_below) if gaps_below else float("inf")
    return above, below


def heading_evidence(unit: Unit, page_units: list[Unit], body_font: float | None) -> dict:
    """Return {level, confidence, basis} for one unit's heading claim."""
    text = normalize_ws(unit.text)
    basis: list = []
    if not text:
        return {"level": None, "confidence": "unknown", "basis": ["empty_text"]}

    if is_year_text(text):
        return {"level": None, "confidence": "low", "basis": ["year_like_text"]}
    if is_date_text(text):
        return {"level": None, "confidence": "low", "basis": ["date_like_text"]}
    if is_numeric_text(text):
        return {"level": None, "confidence": "low", "basis": ["numeric_text"]}
    if is_plain_sentence(text) or (has_terminal_punctuation(text) and len(text) >= 6):
        return {"level": None, "confidence": "low", "basis": ["sentence_like_text"]}

    score = 0.0
    font_evidence = False
    ratio = None
    if unit.font_size and body_font:
        ratio = unit.font_size / body_font
        if ratio >= 1.30:
            score += 2.0
            font_evidence = True
            basis.append("font_ratio_high")
        elif ratio >= 1.12:
            score += 1.0
            font_evidence = True
            basis.append("font_ratio_elevated")
    if unit.bold:
        score += 1.0
        basis.append("bold")
    numbered_level = heading_number_level(text)
    if numbered_level is not None:
        score += 2.0
        basis.append("numbered_heading")
    height = band_height(unit)
    if unit.bbox is None:
        isolated = False
        basis.append("missing_geometry")
    else:
        clearance_above, clearance_below = _vertical_neighbors(unit, page_units)
        isolated = clearance_above >= 0.5 * height and clearance_below >= 0.5 * height
    if isolated:
        score += 1.0
        basis.append("isolated")
    if len(text) <= 40:
        score += 0.5
        basis.append("short_text")
    if unit.font_size is None:
        basis.append("font_size_missing")

    if score < 2.5:
        return {"level": None, "confidence": "low" if score >= 1.5 else "unknown", "basis": basis or ["no_heading_evidence"]}

    if numbered_level is not None:
        level = numbered_level
    elif ratio is not None:
        level = 1 if ratio >= 1.5 else (2 if ratio >= 1.25 else 3)
    else:
        level = None

    if font_evidence and score >= 4.0 and (isolated or numbered_level is not None):
        confidence = "high"
    else:
        confidence = "medium" if (font_evidence or numbered_level is not None) else "low"
    if unit.font_size is None and confidence == "high":
        confidence = "medium"
    return {"level": level, "confidence": confidence, "basis": basis}
