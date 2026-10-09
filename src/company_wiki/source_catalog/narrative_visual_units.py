"""Coordinate-aware OCR adjacency shared by grouping, completion and neighbors."""

from __future__ import annotations
from collections.abc import Sequence
import math
import re
from .narrative_document import NarrativeUnit

_UNRELIABLE = frozenset({"low_ocr_confidence", "locator_unstable"})


def is_ocr_unit(unit: NarrativeUnit) -> bool:
    return unit.unit_kind.endswith("_image_ocr_line")


def ocr_identity(unit: NarrativeUnit) -> tuple | None:
    """A line must have the actual replay carrier/config and pixel coordinates."""
    m = unit.metadata
    if not is_ocr_unit(unit) or _UNRELIABLE.intersection(unit.quality_flags):
        return None
    if (
        m.get("coordinate_space") != "image_pixels"
        or unit.coordinates.page_number is None
    ):
        return None
    for key in ("media_sha256", "ocr_fingerprint"):
        if not isinstance(m.get(key), str) or not re.fullmatch(r"[a-f0-9]{64}", m[key]):
            return None
    shape = m.get("shape_path")
    if not isinstance(shape, (str, list, tuple)) or not shape:
        return None
    if isinstance(shape, (list, tuple)) and any(
        not isinstance(v, (str, int)) for v in shape
    ):
        return None
    index = m.get("ocr_line_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        return None
    confidence = m.get("ocr_confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (float, int))
        or not math.isfinite(confidence)
    ):
        return None
    if not 0 <= confidence <= 1:
        return None
    if ocr_box(unit) is None:
        return None
    return (
        unit.source_id,
        unit.coordinates.page_number,
        unit.source_role,
        unit.language,
        unit.parser_name,
        unit.parser_version,
        m["media_sha256"],
        tuple(shape) if not isinstance(shape, str) else shape,
        m["ocr_fingerprint"],
        m.get("slide_id"),
        m["image_width"],
        m["image_height"],
    )


def ocr_box(unit: NarrativeUnit) -> tuple[float, float, float, float] | None:
    m = unit.metadata
    box = m.get("ocr_box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        values = tuple(float(v) for v in box)
        width, height = float(m["image_width"]), float(m["image_height"])
    except (TypeError, ValueError, KeyError):
        return None
    if not all(math.isfinite(v) for v in (*values, width, height)):
        return None
    x0, y0, x1, y1 = values
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        return None
    return values


def ocr_continues(left: NarrativeUnit, right: NarrativeUnit) -> bool:
    identity = ocr_identity(left)
    if identity is None or identity != ocr_identity(right):
        return False
    if right.metadata["ocr_line_index"] != left.metadata["ocr_line_index"] + 1:
        return False
    a, b = ocr_box(left), ocr_box(right)
    assert a is not None and b is not None
    h = max(a[3] - a[1], b[3] - b[1])
    gap = b[1] - a[3]
    overlap = min(a[2], b[2]) - max(a[0], b[0])
    narrow = min(a[2] - a[0], b[2] - b[0])
    return (
        b[1] > a[1] + 0.5 * min(a[3] - a[1], b[3] - b[1])
        and -0.1 * h <= gap <= 0.75 * h
        and abs(a[0] - b[0]) <= 1.5 * h
        and overlap / narrow >= 0.6
    )


def join_unit_text(members: Sequence[NarrativeUnit]) -> str:
    """Join only for classification; original replay units are never rewritten."""
    pieces = []
    for i, member in enumerate(members):
        if i:
            prior = members[i - 1]
            same_pdf_block = prior.metadata.get(
                "pdf_block"
            ) is not None and prior.metadata.get("pdf_block") == member.metadata.get(
                "pdf_block"
            )
            contiguous = (
                same_pdf_block
                and prior.metadata.get("block_char_end") is not None
                and prior.metadata.get("block_char_end")
                == member.metadata.get("block_char_start")
            )
            pieces.append("" if contiguous or member.language.startswith("zh") else " ")
        pieces.append(member.raw_text)
    return "".join(pieces)
