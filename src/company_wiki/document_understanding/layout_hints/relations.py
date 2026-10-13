"""Context relations (header/caption/footnote) and cross-page continuation.

Continuation is claimed only with explicit evidence: matching column geometry,
a repeated header, or both; the page gap is always preserved in the basis.
"""

from __future__ import annotations

from .geometry import ColumnSlot, unit_text
from .text_evidence import normalized_key


def slot_alignment_evidence(
    slots_a: list[ColumnSlot], slots_b: list[ColumnSlot], tolerance: float, budget
) -> list:
    """One-to-one aligned x-anchors; linear two-pointer walk, no all-pairs."""
    anchors_a = sorted((slot.bbox[0] + slot.bbox[2]) / 2.0 for slot in slots_a)
    anchors_b = sorted((slot.bbox[0] + slot.bbox[2]) / 2.0 for slot in slots_b)
    aligned = []
    a = b = 0
    while a < len(anchors_a) and b < len(anchors_b):
        budget.charge()
        delta = anchors_a[a] - anchors_b[b]
        if abs(delta) <= tolerance:
            aligned.append(anchors_a[a])
            a += 1
            b += 1
        elif delta < 0:
            a += 1
        else:
            b += 1
    return aligned


def repeated_header_evidence(
    header_texts_a: list[str], header_texts_b: list[str]
) -> float:
    keys_a = {normalized_key(text) for text in header_texts_a if text.strip()}
    keys_b = {normalized_key(text) for text in header_texts_b if text.strip()}
    if not keys_a or not keys_b:
        return 0.0
    shared = keys_a & keys_b
    return len(shared) / max(len(keys_a), len(keys_b))


def continuation_claim(
    prev: dict, current: dict, *, page_gap: int, budget
) -> dict | None:
    """Decide whether ``current`` continues the table ``prev``.

    ``prev``/``current`` describe one region each:
    {slots, header_texts, has_caption, bbox, page_width}.
    """
    if current.get("has_caption"):
        return None  # a titled table on the next page is a NEW table
    if not prev.get("slots") or not current.get("slots"):
        return None
    budget.charge()
    tolerance = max(6.0, 0.012 * (current.get("page_width") or 595.0))
    aligned = slot_alignment_evidence(
        prev["slots"], current["slots"], tolerance, budget
    )
    header_score = repeated_header_evidence(
        prev.get("header_texts", []), current.get("header_texts", [])
    )

    basis = [f"page_gap={page_gap}"]
    if header_score >= 0.5:
        basis.append("repeated_header")
    if len(aligned) >= 2:
        basis.append("column_alignment")
    if len(basis) == 1:
        return None
    if header_score >= 0.5 or len(aligned) >= 2:
        confidence = "high" if (header_score >= 0.5 and len(aligned) >= 2) else "medium"
    else:
        return None
    return {"kind": "continuation", "basis": basis, "confidence": confidence}


def unit_texts_of(units) -> list[str]:
    return [unit_text(unit) for unit in units]
