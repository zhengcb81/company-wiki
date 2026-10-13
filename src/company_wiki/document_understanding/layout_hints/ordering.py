"""Per-page reading-order view.

The view is advisory only: it never renumbers or reorders the caller's units
and never drops text.  Units that carry no geometry are reported in a
diagnostic instead of being silently ordered by guesswork.
"""

from __future__ import annotations


def build_reading_order(page_bands_list, lane_layouts, diagnostics: list) -> tuple[list[dict], dict]:
    """Return (reading_order entries, global rank map unit_id -> rank)."""
    entries: list[dict] = []
    rank: dict = {}
    for page_bands, lanes in zip(page_bands_list, lane_layouts):
        ordered: list = []
        for band in page_bands.bands:
            ordered.extend(sorted(band.units, key=lambda u: (u.bbox[0], u.ordinal)))
        seen: set = set()
        sequence: list = []
        for unit in ordered:
            if unit.unit_id in seen:
                continue
            seen.add(unit.unit_id)
            sequence.append(unit)
        if not sequence:
            continue
        basis = ["band_wise"]
        if lanes and lanes.lanes:
            basis.append("lane_split")
        confidence = "medium" if lanes and lanes.lanes else "high"
        entries.append(
            {
                "page": page_bands.page.page_value,
                "ordered_unit_ids": [unit.unit_id for unit in sequence],
                "confidence": confidence,
                "basis": basis,
            }
        )
        for unit in sequence:
            rank[unit.unit_id] = len(rank)

    unorderable = []
    for page_bands in page_bands_list:
        for unit in page_bands.page.units:
            if unit.deferred:
                continue
            if unit.bbox is None and unit.unit_id not in rank:
                unorderable.append(unit.unit_id)
    if unorderable:
        diagnostics.append(
            {
                "code": "UNORDERABLE_UNIT",
                "unit_ids": sorted(unorderable),
                "detail": "unit carries no geometry; excluded from the reading-order view only",
            }
        )
    return entries, rank
